"""
Utility functions for the LightRAG API.
"""

import os
import argparse
from typing import Optional, List, Tuple
import sys
import time
import logging
from ascii_colors import ASCIIColors
from .._version import __api_version__ as api_version
from .._version import __version__ as core_version
from lightrag.constants import (
    DEFAULT_FORCE_LLM_SUMMARY_ON_MERGE,
)
from lightrag.api.runtime_validation import validate_runtime_target_from_env_file
from fastapi import HTTPException, Security, Request, Response, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from starlette.status import HTTP_403_FORBIDDEN
from .auth import auth_handler
from .config import ollama_server_infos, global_args, get_env_value

logger = logging.getLogger("lightrag")

# ========== Token Renewal Rate Limiting ==========
# Cache to track last renewal time per user (username as key)
# Format: {username: last_renewal_timestamp}
_token_renewal_cache: dict[str, float] = {}
_RENEWAL_MIN_INTERVAL = 60  # Minimum 60 seconds between renewals for same user

# ========== Token Renewal Path Exclusions ==========
# Paths that should NOT trigger token auto-renewal
# - /health: Health check endpoint, no login required
# - /documents/paginated: Client polls this frequently (5-30s), renewal not needed
# - /documents/pipeline_status: Client polls this very frequently (2s), renewal not needed
_TOKEN_RENEWAL_SKIP_PATHS = [
    "/health",
    "/documents/paginated",
    "/documents/pipeline_status",
]


def check_env_file():
    """
    Check if .env file exists and handle user confirmation if needed.
    Returns True if should continue, False if should exit.
    """
    env_path = ".env"

    if not os.path.exists(env_path):
        warning_msg = "Warning: Startup directory must contain .env file for multi-instance support."
        #  含有 print 功能。
        ASCIIColors.yellow(warning_msg)

        # Check if running in interactive terminal
        if sys.stdin.isatty():
            response = input("Do you want to continue? (yes/NO): ")
            if response.lower() != "yes":
                ASCIIColors.red("Server startup cancelled")
                return False
        return True

    is_valid, error_message = validate_runtime_target_from_env_file(env_path)
    if not is_valid:
        # 无效
        for line in error_message.splitlines():
            ASCIIColors.red(line)
        return False

    # 有效
    return True


# Get whitelist paths from global_args, only once during initialization
whitelist_paths = global_args.whitelist_paths.split(",")

# Pre-compile path matching patterns
# 内容为 url:profix or url, 以逗号分隔，
# 支持前缀匹配（以 /* 结尾）和完全匹配。比如 /health, /docs/*, /public/* 等。
whitelist_patterns: List[Tuple[str, bool]] = []
for path in whitelist_paths:
    path = path.strip()
    if path:
        # If path ends with /*, match all paths with that prefix
        if path.endswith("/*"):
            prefix = path[:-2]
            whitelist_patterns.append((prefix, True))  # (prefix, is_prefix_match)
        else:
            whitelist_patterns.append((path, False))  # (exact_path, is_prefix_match)

# Global authentication configuration
auth_configured = bool(auth_handler.accounts)


# 获取合并的用户认证依赖项
def get_combined_auth_dependency(api_key: Optional[str] = None):
    """
    Create a combined authentication dependency that implements authentication logic
    based on API key, OAuth2 token, and whitelist paths.

    Args:
        api_key (Optional[str]): API key for validation

    Returns:
        Callable: A dependency function that implements the authentication logic
    """
    # Use global whitelist_patterns and auth_configured variables
    # whitelist_patterns and auth_configured are already initialized at module level

    # Only calculate api_key_configured as it depends on the function parameter
    api_key_configured = bool(api_key)

    # Create security dependencies with proper descriptions for Swagger UI
    oauth2_scheme = OAuth2PasswordBearer(
        tokenUrl="login", auto_error=False, description="OAuth2 Password Authentication"
    )

    # If API key is configured, create an API key header security
    api_key_header = None
    if api_key_configured:
        api_key_header = APIKeyHeader(
            name="X-API-Key", auto_error=False, description="API Key Authentication"
        )


    async def combined_dependency(
        request: Request,
        response: Response,  # Added: needed to return new token via response header
        token: str = Security(oauth2_scheme),
        api_key_header_value: Optional[str] = None if api_key_header is None else Security(api_key_header),
    ):
        # 认证逻辑实现：

        # 1. Check if path is in whitelist
        path = request.url.path
        for pattern, is_prefix in whitelist_patterns:
            # whitelist：<pattern>/* =>is_prefix：true
            # 白名单路径匹配：如果配置项以 /* 结尾，则匹配所有以该路径为前缀的请求；否则，要求完全匹配。
            if (is_prefix and path.startswith(pattern)) \
               or ( not is_prefix and path == pattern):
                # 匹配成功，立即返回，允许访问 
                return  # Whitelist path, allow access

        # 2. Validate token first if provided in the request (Ensure 401 error if token is invalid)
        if token:
            # 验证 token 的有效性，如果无效，立即返回 401 错误；如果有效，根据配置决定是否允许访问（比如是否接受 guest 角色的 token）
            try:
                token_info = auth_handler.validate_token(token)

                # ========== Token Auto-Renewal Logic ==========
                from lightrag.api.config import global_args
                from datetime import datetime, timezone

                if global_args.token_auto_renew:
                    # Check if current path should skip token renewal
                    skip_renewal = any(
                        path == skip_path or path.startswith(skip_path + "/")
                        for skip_path in _TOKEN_RENEWAL_SKIP_PATHS
                    )

                    if skip_renewal:
                        logger.debug(f"Token auto-renewal skipped for path: {path}")
                    else:
                        try:
                            expire_time = token_info.get("exp")
                            if expire_time:
                                # Calculate remaining time ratio
                                now = datetime.now(timezone.utc)
                                remaining_seconds = (expire_time - now).total_seconds()

                                # Get original token expiration duration
                                role = token_info.get("role", "user")
                                total_hours = (
                                    auth_handler.guest_expire_hours
                                    if role == "guest"
                                    else auth_handler.expire_hours
                                ) # 小时
                                total_seconds = total_hours * 3600 # 转换为秒

                                # Issue new token if remaining time < threshold
                                if (
                                    remaining_seconds
                                    < total_seconds * global_args.token_renew_threshold
                                ):
                                    # ========== Rate Limiting Check ==========
                                    username = token_info["username"]
                                    current_time = time.time()
                                    # 根据 username 获取上次续期时间，如果距离上次续期时间过短，则跳过续期，避免频繁续期导致性能问题或安全风险。
                                    last_renewal = _token_renewal_cache.get(username, 0)
                                    time_since_last_renewal = (
                                        current_time - last_renewal
                                    )

                                    # Only renew if enough time has passed since last renewal
                                    if time_since_last_renewal >= _RENEWAL_MIN_INTERVAL:
                                        # 生成新 token 并通过响应头返回给客户端，同时更新续期缓存中的时间戳。
                                        new_token = auth_handler.create_token(
                                            username=username,
                                            role=role,
                                            metadata=token_info.get("metadata", {}),
                                        )
                                        # Return new token via response header
                                        # 通过响应头返回新 token，客户端可以选择是否使用这个新 token 进行后续请求，以实现无缝续期体验。
                                        response.headers["X-New-Token"] = new_token

                                        # Update renewal cache
                                        # 缓冲续期时间戳，记录上次续期时间，单位为秒。
                                        _token_renewal_cache[username] = current_time

                                        # Optional: log renewal
                                        logger.info(
                                            f"Token auto-renewed for user {username} "
                                            f"(role: {role}, remaining: {remaining_seconds:.0f}s)"
                                        )
                                    else:
                                        # Log skip due to rate limit
                                        logger.debug(
                                            f"Token renewal skipped for {username} "
                                            f"(rate limit: last renewal {time_since_last_renewal:.0f}s ago)"
                                        )
                                    # ========== End of Rate Limiting Check ==========
                        except Exception as e:
                            # Renewal failure should not affect normal request, just log
                            logger.warning(f"Token auto-renew failed: {e}")
                # ========== End of Token Auto-Renewal Logic ==========

                # Accept guest token if no auth is configured
                if not auth_configured and token_info.get("role") == "guest":
                    # 没有配置认证时，接受 guest 角色的 token，允许访问
                    return
                # Accept non-guest token if auth is configured
                if auth_configured and token_info.get("role") != "guest":
                    # 配置了认证时，接受非 guest 角色的 token，允许访问
                    return

                # Token validation failed, immediately return 401 error
                # token 验证失败，立即返回 401 错误，拒绝访问
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token. Please login again.",
                )
            except HTTPException as e:
                # If already a 401 error, re-raise it
                if e.status_code == status.HTTP_401_UNAUTHORIZED:
                    raise
                # For other exceptions, continue processing

        # 3. Acept all request if no API protection needed
        if not auth_configured and not api_key_configured:
            # 没有配置认证且没有配置 API key，接受所有请求，允许访问
            return

        # 4. Validate API key if provided and API-Key authentication is configured
        if (
            api_key_configured
            and api_key_header_value
            and api_key_header_value == api_key
        ):
            # API key 验证成功，允许访问
            return  # API key validation successful

        ### Authentication failed ####

        # if password authentication is configured but not provided, ensure 401 error if auth_configured
        if auth_configured and not token:
            # 配置了密码认证但请求中没有提供 token，确保返回 401 错误，提示用户需要登录认证。
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No credentials provided. Please login.",
            )

        # if api key is provided but validation failed
        if api_key_header_value:
            # 提供了 API key 但验证失败，返回 403 错误，提示 API key 无效。
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Invalid API Key",
            )

        # if api_key_configured but not provided
        if api_key_configured and not api_key_header_value:
            # 配置了 API key 认证但请求中没有提供 API key，返回 403 错误，提示需要 API key。
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="API Key required",
            )

        # Otherwise: refuse access and return 403 error
        # 其他情况， 拒绝访问，返回 403 错误，提示需要 API key 或登录认证。
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="API Key required or login authentication required.",
        )

    return combined_dependency


def display_splash_screen(args: argparse.Namespace) -> None:
    """
    Display a colorful splash screen showing LightRAG server configuration

    Args:
        args: Parsed command line arguments
    """
    # Banner
    # Banner
    top_border =    "╔══════════════════════════════════════════════════════════════╗"
    bottom_border = "╚══════════════════════════════════════════════════════════════╝"
    width = len(top_border) - 4  # width inside the borders

    line1_text = f"LightRAG Server v{core_version}/{api_version}"
    line2_text = "Fast, Lightweight RAG Server Implementation"

    line1 = f"║ {line1_text.center(width)} ║"
    line2 = f"║ {line2_text.center(width)} ║"

    banner = f"""
    {top_border}
    {line1}
    {line2}
    {bottom_border}
    """
    ASCIIColors.cyan(banner)

    # Server Configuration
    ASCIIColors.magenta("\n📡 Server Configuration:")
    ASCIIColors.white("    ├─ Host: ", end="")
    ASCIIColors.yellow(f"{args.host}")
    ASCIIColors.white("    ├─ Port: ", end="")
    ASCIIColors.yellow(f"{args.port}")
    ASCIIColors.white("    ├─ Workers: ", end="")
    ASCIIColors.yellow(f"{args.workers}")
    ASCIIColors.white("    ├─ Timeout: ", end="")
    ASCIIColors.yellow(f"{args.timeout}")
    ASCIIColors.white("    ├─ CORS Origins: ", end="")
    ASCIIColors.yellow(f"{args.cors_origins}")
    ASCIIColors.white("    ├─ SSL Enabled: ", end="")
    ASCIIColors.yellow(f"{args.ssl}")
    if args.ssl:
        ASCIIColors.white("    ├─ SSL Cert: ", end="")
        ASCIIColors.yellow(f"{args.ssl_certfile}")
        ASCIIColors.white("    ├─ SSL Key: ", end="")
        ASCIIColors.yellow(f"{args.ssl_keyfile}")
    ASCIIColors.white("    ├─ Ollama Emulating Model: ", end="")
    ASCIIColors.yellow(f"{ollama_server_infos.LIGHTRAG_MODEL}")
    ASCIIColors.white("    ├─ Log Level: ", end="")
    ASCIIColors.yellow(f"{args.log_level}")
    ASCIIColors.white("    ├─ Verbose Debug: ", end="")
    ASCIIColors.yellow(f"{args.verbose}")
    ASCIIColors.white("    ├─ API Key: ", end="")
    ASCIIColors.yellow("Set" if args.key else "Not Set")
    ASCIIColors.white("    └─ JWT Auth: ", end="")
    ASCIIColors.yellow("Enabled" if args.auth_accounts else "Disabled")

    # Directory Configuration
    ASCIIColors.magenta("\n📂 Directory Configuration:")
    ASCIIColors.white("    ├─ Working Directory: ", end="")
    ASCIIColors.yellow(f"{args.working_dir}")
    ASCIIColors.white("    └─ Input Directory: ", end="")
    ASCIIColors.yellow(f"{args.input_dir}")

    # LLM Configuration
    ASCIIColors.magenta("\n🤖 LLM Configuration:")
    ASCIIColors.white("    ├─ Binding: ", end="")
    ASCIIColors.yellow(f"{args.llm_binding}")
    ASCIIColors.white("    ├─ Host: ", end="")
    ASCIIColors.yellow(f"{args.llm_binding_host}")
    ASCIIColors.white("    ├─ Model: ", end="")
    ASCIIColors.yellow(f"{args.llm_model}")
    ASCIIColors.white("    ├─ Max Async for LLM: ", end="")
    ASCIIColors.yellow(f"{args.max_async}")
    ASCIIColors.white("    ├─ Summary Context Size: ", end="")
    ASCIIColors.yellow(f"{args.summary_context_size}")
    ASCIIColors.white("    ├─ LLM Cache Enabled: ", end="")
    ASCIIColors.yellow(f"{args.enable_llm_cache}")
    ASCIIColors.white("    └─ LLM Cache for Extraction Enabled: ", end="")
    ASCIIColors.yellow(f"{args.enable_llm_cache_for_extract}")

    # Embedding Configuration
    ASCIIColors.magenta("\n📊 Embedding Configuration:")
    ASCIIColors.white("    ├─ Binding: ", end="")
    ASCIIColors.yellow(f"{args.embedding_binding}")
    ASCIIColors.white("    ├─ Host: ", end="")
    ASCIIColors.yellow(f"{args.embedding_binding_host}")
    ASCIIColors.white("    ├─ Model: ", end="")
    ASCIIColors.yellow(f"{args.embedding_model}")
    ASCIIColors.white("    └─ Dimensions: ", end="")
    ASCIIColors.yellow(f"{args.embedding_dim}")

    # RAG Configuration
    ASCIIColors.magenta("\n⚙️ RAG Configuration:")
    ASCIIColors.white("    ├─ Summary Language: ", end="")
    ASCIIColors.yellow(f"{args.summary_language}")
    ASCIIColors.white("    ├─ Entity Types: ", end="")
    ASCIIColors.yellow(f"{args.entity_types}")
    ASCIIColors.white("    ├─ Max Parallel Insert: ", end="")
    ASCIIColors.yellow(f"{args.max_parallel_insert}")
    ASCIIColors.white("    ├─ Chunk Size: ", end="")
    ASCIIColors.yellow(f"{args.chunk_size}")
    ASCIIColors.white("    ├─ Chunk Overlap Size: ", end="")
    ASCIIColors.yellow(f"{args.chunk_overlap_size}")
    ASCIIColors.white("    ├─ Cosine Threshold: ", end="")
    ASCIIColors.yellow(f"{args.cosine_threshold}")
    ASCIIColors.white("    ├─ Top-K: ", end="")
    ASCIIColors.yellow(f"{args.top_k}")
    ASCIIColors.white("    └─ Force LLM Summary on Merge: ", end="")
    ASCIIColors.yellow(
        f"{get_env_value('FORCE_LLM_SUMMARY_ON_MERGE', DEFAULT_FORCE_LLM_SUMMARY_ON_MERGE, int)}"
    )

    # System Configuration
    ASCIIColors.magenta("\n💾 Storage Configuration:")
    ASCIIColors.white("    ├─ KV Storage: ", end="")
    ASCIIColors.yellow(f"{args.kv_storage}")
    ASCIIColors.white("    ├─ Vector Storage: ", end="")
    ASCIIColors.yellow(f"{args.vector_storage}")
    ASCIIColors.white("    ├─ Graph Storage: ", end="")
    ASCIIColors.yellow(f"{args.graph_storage}")
    ASCIIColors.white("    ├─ Document Status Storage: ", end="")
    ASCIIColors.yellow(f"{args.doc_status_storage}")
    ASCIIColors.white("    └─ Workspace: ", end="")
    ASCIIColors.yellow(f"{args.workspace if args.workspace else '-'}")

    # Server Status
    ASCIIColors.green("\n✨ Server starting up...\n")

    # Server Access Information
    protocol = "https" if args.ssl else "http"
    if args.host == "0.0.0.0":
        ASCIIColors.magenta("\n🌐 Server Access Information:")
        ASCIIColors.white("    ├─ WebUI (local): ", end="")
        ASCIIColors.yellow(f"{protocol}://localhost:{args.port}")
        ASCIIColors.white("    ├─ Remote Access: ", end="")
        ASCIIColors.yellow(f"{protocol}://<your-ip-address>:{args.port}")
        ASCIIColors.white("    ├─ API Documentation (local): ", end="")
        ASCIIColors.yellow(f"{protocol}://localhost:{args.port}/docs")
        ASCIIColors.white("    └─ Alternative Documentation (local): ", end="")
        ASCIIColors.yellow(f"{protocol}://localhost:{args.port}/redoc")

        ASCIIColors.magenta("\n📝 Note:")
        ASCIIColors.cyan("""    Since the server is running on 0.0.0.0:
    - Use 'localhost' or '127.0.0.1' for local access
    - Use your machine's IP address for remote access
    - To find your IP address:
      • Windows: Run 'ipconfig' in terminal
      • Linux/Mac: Run 'ifconfig' or 'ip addr' in terminal
    """)
    else:
        base_url = f"{protocol}://{args.host}:{args.port}"
        ASCIIColors.magenta("\n🌐 Server Access Information:")
        ASCIIColors.white("    ├─ WebUI (local): ", end="")
        ASCIIColors.yellow(f"{base_url}")
        ASCIIColors.white("    ├─ API Documentation: ", end="")
        ASCIIColors.yellow(f"{base_url}/docs")
        ASCIIColors.white("    └─ Alternative Documentation: ", end="")
        ASCIIColors.yellow(f"{base_url}/redoc")

    # Security Notice
    if args.key:
        ASCIIColors.yellow("\n⚠️  Security Notice:")
        ASCIIColors.white("""    API Key authentication is enabled.
    Make sure to include the X-API-Key header in all your requests.
    """)
    if args.auth_accounts:
        ASCIIColors.yellow("\n⚠️  Security Notice:")
        ASCIIColors.white("""    JWT authentication is enabled.
    Make sure to login before making the request, and include the 'Authorization' in the header.
    """)

    # Ensure splash output flush to system log
    sys.stdout.flush()
