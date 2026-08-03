### All configurable environment variable must show up in this sample file in active or comment out status
### Setup tool `make env-*` uses this file to generate final .env file
### These are placeholders and setup tool should not be substituted with actual values in this lines.
### 所有可配置环境变量必须以启用或注释状态出现在此示例文件中
### `make env-*` 安装工具使用此文件生成最终 .env 文件
### 这些是占位符，安装工具不应将此文件中的占位符替换为实际值

### Target environment of this env file: host/compose (compose is for Dokcer or Kubernetes)
### 此 env 文件的目标环境：host（直接部署）或 compose（Docker/Kubernetes 部署）
LIGHTRAG_RUNTIME_TARGET=host

###########################
### Server Configuration
### 服务器配置
###########################
# 监听地址，0.0.0.0 表示监听所有网卡
HOST=0.0.0.0
# 服务监听端口
PORT=9621
# WebUI 页面标题
WEBUI_TITLE='My Graph KB'
# WebUI 页面描述
WEBUI_DESCRIPTION='Simple and Fast Graph Based RAG System'
# WORKERS=2                                            # Gunicorn Worker 进程数（多核服务器可适当增大）
### gunicorn worker timeout(as default LLM request timeout if LLM_TIMEOUT is not set)
### Gunicorn Worker 超时秒数（若未设置 LLM_TIMEOUT，同时作为 LLM 请求的默认超时）
# TIMEOUT=150
# CORS_ORIGINS=http://localhost:3000,http://localhost:8080  # 允许跨域访问的源地址，多个用逗号分隔

### Path Prefix Configuration (Optional)
### Used to host multiple LightRAG instances on one host behind a reverse
### proxy that routes by site prefix. Leave unset (or empty) for a
### single-instance deployment.
###
### - LIGHTRAG_API_PREFIX  : reverse-proxy prefix the upstream proxy strips
###                          before forwarding (passed to FastAPI as root_path).
###
### See docs/MultiSiteDeployment.md for end-to-end examples.
# LIGHTRAG_API_PREFIX=/site01

### Optional SSL Configuration
### 可选 SSL 配置
### Docker note: generated compose files mount staged certs at /app/data/certs/ inside the container
### Docker 注意：生成的 compose 文件会将证书挂载到容器内的 /app/data/certs/ 目录
# SSL=true                              # 是否启用 HTTPS
# SSL_CERTFILE=/path/to/cert.pem        # SSL 证书文件路径
# SSL_KEYFILE=/path/to/key.pem          # SSL 私钥文件路径

### Directory Configuration (defaults to current working directory)

### 目录配置（默认使用当前工作目录）
### Default value is ./inputs and ./rag_storage
### 默认值为 ./inputs 和 ./rag_storage
# INPUT_DIR=<absolute_path_for_doc_input_dir>   # 文档输入目录的绝对路径
# WORKING_DIR=<absolute_path_for_working_dir>   # 工作目录（存放缓存、向量库等数据）的绝对路径

### Default value is: ./inputs ./rag_storage
# INPUT_DIR=<absolute_path_for_doc_input_dir>
# WORKING_DIR=<absolute_path_for_working_dir>

### Tiktoken cache directory (Store cached files in this folder for offline deployment)
### Tiktoken 缓存目录（离线部署时将分词器缓存文件存放在此目录）
# TIKTOKEN_CACHE_DIR=/app/data/tiktoken

### Ollama Emulating Model and Tag
### Ollama 模拟模型名称和标签（用于 LightRAG 对外模拟 Ollama API 时的模型标识）
# OLLAMA_EMULATING_MODEL_NAME=lightrag   # 模拟的模型名称
# 模拟的模型标签
OLLAMA_EMULATING_MODEL_TAG=latest

### Max nodes for graph retrieval (Ensure WebUI local settings are also updated, which is limited to this value)
### 图检索返回的最大节点数（请同步更新 WebUI 本地设置，其上限受此值约束）
# MAX_GRAPH_NODES=1000

### Logging level
### 日志配置
# LOG_LEVEL=INFO                          # 日志级别：DEBUG / INFO / WARNING / ERROR
# VERBOSE=False                           # 是否输出详细日志
# LOG_MAX_BYTES=10485760                  # 单个日志文件最大字节数（默认 10MB）
# LOG_BACKUP_COUNT=5                      # 日志文件轮转保留数量
### Logfile location (defaults to current working directory)
### 日志文件存放目录（默认为当前工作目录）
# LOG_DIR=/path/to/log/directory
# LIGHTRAG_PERFORMANCE_TIMING_LOGS=false  # 是否启用性能计时日志

#####################################
### Login and API-Key Configuration
### 登录与 API 密钥配置
#####################################

AUTH_ACCOUNTS='rootbr:{bcrypt}$2b$12$49wuY5Mu.KQaRdARSYD5G.WprAb3BOqlhus6UPvguvxv5gSmm3USK'
TOKEN_SECRET=bori!098
TOKEN_EXPIRE_HOURS=48
# AUTH_ACCOUNTS='admin:admin123,user1:{bcrypt}$2b$12$S8Yu.gCbuAbNTJFB.231gegTwr5pgrFxc8H9kXQ4/sduFBHkhM8Ka'
# 用户账号配置，格式：用户名:密码（支持明文或 bcrypt 哈希），多账号用逗号分隔
# TOKEN_SECRET=lightrag-jwt-default-secret-key!  # JWT 签名密钥（生产环境务必修改为随机强密钥）
# JWT_ALGORITHM=HS256                            # JWT 签名算法
# TOKEN_EXPIRE_HOURS=48                          # 普通用户 Token 有效期（小时）
# GUEST_TOKEN_EXPIRE_HOURS=24                    # 访客 Token 有效期（小时）

### Token Auto-Renewal Configuration (Sliding Window Expiration)
### Token 自动续期配置（滑动窗口过期机制）
### Enable automatic token renewal to prevent active users from being logged out
### 启用自动续期可防止活跃用户被强制登出
### When enabled, tokens will be automatically renewed when remaining time < threshold
### 启用后，当 Token 剩余有效期 < 阈值时自动续期
# TOKEN_AUTO_RENEW=true                # 是否启用 Token 自动续期
### Token renewal threshold (0.0 - 1.0)
### Token 续期阈值（0.0 - 1.0）
### Renew token when remaining time < (total time * threshold)
### 当剩余时间 < (总时间 × 阈值) 时触发续期
### Default: 0.5 (renew when 50% time remaining)
### 默认：0.5（剩余 50% 有效期时续期）
### Examples:
###   0.5 = renew when 24h token has 12h left  （24h Token 剩余 12h 时续期）
###   0.25 = renew when 24h token has 6h left  （24h Token 剩余 6h 时续期）
# TOKEN_RENEW_THRESHOLD=0.5
### Note: Token renewal is automatically skipped for certain endpoints:
### 注意：以下端点会自动跳过 Token 续期：
###   - /health: Health check endpoint (no authentication required)  健康检查，无需认证
###   - /documents/paginated: Frequently polled by client (5-30s interval)  客户端频繁轮询（5-30s）
###   - /documents/pipeline_status: Very frequently polled by client (2s interval)  极频繁轮询（2s）
###   - Rate limit: Minimum 60 seconds between renewals for same user  同一用户两次续期最少间隔 60s

### API-Key to access LightRAG Server API
### 用于访问 LightRAG Server API 的密钥
### Use this key in HTTP requests with the 'X-API-Key' header
### 在 HTTP 请求头中使用 'X-API-Key' 携带此密钥
### Example: curl -H "X-API-Key: your-secure-api-key-here" http://localhost:9621/query
# LIGHTRAG_API_KEY=your-secure-api-key-here  # API 访问密钥（留空则不启用 API Key 认证）
# WHITELIST_PATHS=/health,/api/*             # 无需认证即可访问的路径白名单，多个用逗号分隔

######################################################################################
### Query Configuration
### 查询配置
###
### How to control the context length sent to LLM:
### 如何控制发送给 LLM 的上下文长度：
###    MAX_ENTITY_TOKENS + MAX_RELATION_TOKENS < MAX_TOTAL_TOKENS
###    Chunk_Tokens = MAX_TOTAL_TOKENS - Actual_Entity_Tokens - Actual_Relation_Tokens
###    （Chunk Token 数 = 总 Token 上限 - 实际实体 Token 数 - 实际关系 Token 数）
######################################################################################
# LLM response cache for query (Not valid for streaming response)
# 查询时是否启用 LLM 响应缓存（流式响应不支持缓存）
# ENABLE_LLM_CACHE=true
# COSINE_THRESHOLD=0.2     # 向量检索的余弦相似度阈值，低于此值的结果将被过滤
### Number of entities or relations retrieved from KG
### 从知识图谱检索的实体或关系数量上限
# TOP_K=40
### Maximum number or chunks for naive vector search
### naive 模式纯向量检索时返回的最大 chunk 数
# CHUNK_TOP_K=20
### control the actual entities send to LLM
### 控制发送给 LLM 的实体部分最大 Token 数
# MAX_ENTITY_TOKENS=6000
### control the actual relations send to LLM
### 控制发送给 LLM 的关系部分最大 Token 数
# MAX_RELATION_TOKENS=8000
### control the maximum tokens send to LLM (include entities, relations and chunks)
### 控制发送给 LLM 的总最大 Token 数（包含实体、关系和文本块）
# MAX_TOTAL_TOKENS=30000

### chunk selection strategies
### 文本块（chunk）选取策略
###     VECTOR: Pick KG chunks by vector similarity, delivered chunks to the LLM aligning more closely with naive retrieval
###     VECTOR：按向量相似度选取 KG 关联 chunk，结果与 naive 检索更接近
###     WEIGHT: Pick KG chunks by entity and chunk weight, delivered more solely KG related chunks to the LLM
###     WEIGHT：按实体和 chunk 权重选取，结果更专注于知识图谱相关内容
###     If reranking is enabled, the impact of chunk selection strategies will be diminished.
###     若启用重排序（reranking），chunk 选取策略的影响会减弱
# KG_CHUNK_PICK_METHOD=VECTOR

### maximum number of related chunks per source entity or relation
### 每个实体或关系关联的最大 chunk 数
###     The chunk picker uses this value to determine the total number of chunks selected from KG(knowledge graph)
###     chunk 选取器用此值决定从知识图谱中选取的 chunk 总数
###     Higher values increase re-ranking time
###     值越大，重排序耗时越长
# RELATED_CHUNK_NUMBER=5

#########################################################
### Reranking configuration
### 重排序（Reranking）配置
### RERANK_BINDING type: null, cohere, jina, aliyun
### RERANK_BINDING 类型：null（不启用）/ cohere / jina / aliyun
### For rerank model deployed by vLLM use cohere binding
### vLLM 部署的重排序模型使用 cohere 类型
### If LightRAG deployed in Docker:
### 若 LightRAG 部署在 Docker 中：
###    uses host.docker.internal instead of localhost in RERANK_BINDING_HOST
###    RERANK_BINDING_HOST 中用 host.docker.internal 替代 localhost
#########################################################
RERANK_BINDING=null
# RERANK_BINDING=null                                    # 重排序服务类型，null 表示不启用
# RERANK_MODEL=BAAI/bge-reranker-v2-m3                # 重排序模型名称
# RERANK_BINDING_HOST=http://localhost:8000/rerank     # 重排序服务地址
# RERANK_BINDING_API_KEY=your_rerank_api_key_here      # 重排序服务 API 密钥

### rerank score chunk filter(set to 0.0 to keep all chunks, 0.6 or above if LLM is not strong enough)
### 重排序分数过滤阈值（设为 0.0 保留所有 chunk；LLM 能力较弱时建议设为 0.6 以上）
# MIN_RERANK_SCORE=0.0
### Enable rerank by default in query params when RERANK_BINDING is not null
### 当 RERANK_BINDING 不为 null 时，查询默认启用重排序
# RERANK_BY_DEFAULT=True

### Rerank concurrency and timeout (independent from base LLM settings)
### MAX_ASYNC_RERANK falls back to MAX_ASYNC when unset.
### RERANK_TIMEOUT has its own default (30s) since reranker calls are
### typically much shorter than full LLM generation.
# MAX_ASYNC_RERANK=4
# RERANK_TIMEOUT=30

### Cohere AI
# # RERANK_MODEL=rerank-v3.5
# # RERANK_BINDING_HOST=https://api.cohere.com/v2/rerank
# # RERANK_BINDING_API_KEY=your_rerank_api_key_here
### Cohere rerank chunking configuration (useful for models with token limits like ColBERT)
### Cohere 重排序分块配置（适用于有 token 限制的模型，如 ColBERT）
# RERANK_ENABLE_CHUNKING=true              # 是否启用重排序前分块
# RERANK_MAX_TOKENS_PER_DOC=480            # 每个文档分块的最大 token 数

### Aliyun Dashscope
### 阿里云 Dashscope 重排序服务
# # RERANK_MODEL=gte-rerank-v2
# # RERANK_BINDING_HOST=https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank
# # RERANK_BINDING_API_KEY=your_rerank_api_key_here

### Jina AI
### Jina AI 重排序服务
# # RERANK_MODEL=jina-reranker-v2-base-multilingual
# # RERANK_BINDING_HOST=https://api.jina.ai/v1/rerank
# # RERANK_BINDING_API_KEY=your_rerank_api_key_here

### For local deployment Embedding and Reranker with vLLM (OpenAI-compatible API)
### 使用 vLLM 本地部署 Embedding 和 Reranker（OpenAI 入口兼容）
### Wizard metadata used to preserve the chosen deployment provider across setup reruns
### 向导元数据，用于在多次配置向导运行间保留选择的部署方式
# LIGHTRAG_SETUP_EMBEDDING_PROVIDER=vllm
# LIGHTRAG_SETUP_RERANK_PROVIDER=vllm
# VLLM_EMBED_MODEL=BAAI/bge-m3               # vLLM Embedding 模型名称
# VLLM_EMBED_PORT=8001                       # vLLM Embedding 服务端口
# VLLM_EMBED_DEVICE=cpu                      # 运行设备：cpu 或 cuda
### VLLM_EMBED_API_KEY is passed as --api-key to vLLM; synced to EMBEDDING_BINDING_API_KEY; auto-generated if blank
### 传递给 vLLM --api-key 参数；同步到 EMBEDDING_BINDING_API_KEY；空白则自动生成
# VLLM_EMBED_API_KEY=
# VLLM_EMBED_EXTRA_ARGS=                     # vLLM Embedding 额外启动参数
# VLLM_RERANK_MODEL=BAAI/bge-reranker-v2-m3  # vLLM Reranker 模型名称
# VLLM_RERANK_PORT=8000                      # vLLM Reranker 服务端口
# VLLM_RERANK_DEVICE=cuda                    # 运行设备
### VLLM_RERANK_API_KEY is passed as --api-key to vLLM; synced to RERANK_BINDING_API_KEY; auto-generated if blank
### 传递给 vLLM --api-key 参数；同步到 RERANK_BINDING_API_KEY；空白则自动生成
# VLLM_RERANK_API_KEY=
### Use float16 for GPU mode. CPU mode uses the official vLLM CPU image.
### GPU 模式使用 float16；CPU 模式使用官方 vLLM CPU 镜像
# VLLM_USE_CPU=1                             # 设为 1 强制 CPU 模式
### Set to 1 for CPU mode, unset for GPU mode
# CUDA_VISIBLE_DEVICES=-1                    # -1 禁用 CUDA，指定 GPU ID 则启用对应 GPU
### Set to -1 to disable CUDA (CPU mode), or specific GPU IDs for GPU mode
# NVIDIA_VISIBLE_DEVICES=0                   # 对 Docker GPU 直通时指定 GPU ID
### Optional Docker runtime equivalent; generated GPU compose honors either variable.
# VLLM_RERANK_EXTRA_ARGS=                    # vLLM Reranker 额外启动参数

########################################
### Document processing configuration
### 文档处理配置
########################################

# 实体提取阶段是否启用 LLM 缓存（减少重复提取的 LLM 调用费用）
ENABLE_LLM_CACHE_FOR_EXTRACT=true

### Document processing output language: English, Chinese, French, German ...
### 文档处理输出语言：实体和关系描述将以此语言生成
SUMMARY_LANGUAGE=Chinese

### Enable JSON-structured output for entity extraction
### Default behavior: JSON output is disabled when ENTITY_EXTRACTION_USE_JSON is unset
### JSON output incurs higher latency but delivers improved reliability
ENTITY_EXTRACTION_USE_JSON=true

### Optional external YAML profile for entity type guidance and extraction examples
### Profiles are loaded from PROMPT_DIR/entity_type (PROMPT_DIR defaults to ./prompts).
### A reference template is shipped at prompts/samples/entity_type_prompt.sample.yml;
# ENTITY_TYPE_PROMPT_FILE=entity_type_prompt.yml
# PROMPT_DIR=<absolute_path_for_prompt_dir>

### Multimodal parsing/analyze integration
### Optional parser routing rules. Example for VLM & MinerU enabled configuration:
###     LIGHTRAG_PARSER=*:native-iteP,*:mineru-iteP,*:legacy-R
### Rules may be separated with commas or semicolons. Rules match file suffixes
### (pdf), not full names (*.pdf), and are checked left-to-right.
### If mineru/docling appears in LIGHTRAG_PARSER, the corresponding endpoint
### below must be configured before server startup.
### See docs/FileProcessingPipeline.md for detail
LIGHTRAG_PARSER=*:native-teP,*:legacy-R

### Async parser service protocol (optional)
### Configure these when using remote MinerU/Docling async services

### ---- MinerU shared parameters (both local and official modes) ----
### MinerU API protocol. Choose one active mode.
### - official: MinerU precision API v4. Requires MINERU_API_TOKEN.
### - local: self-hosted mineru-api / mineru-router base URL.
MINERU_API_MODE=local
# MINERU_POLL_INTERVAL_SECONDS=2
# MINERU_MAX_POLLS=180
# MINERU_LANGUAGE=ch
# MINERU_ENABLE_TABLE=true
# MINERU_ENABLE_FORMULA=true
# MINERU_PAGE_RANGES=
### MINERU_PAGE_RANGES semantics differ by mode:
### - official: forwarded verbatim, supports e.g. "1-3,5,7-9".
### - local:    only a single page ("3") or simple range ("1-10"); comma
###             lists are rejected at startup.
### When switching modes, double-check this constraint.

### ---- MinerU local-only (MINERU_API_MODE=local) ----
MINERU_LOCAL_ENDPOINT=http://127.0.0.1:8000
### MINERU_LOCAL_BACKEND: which mineru-api backend handles the parse.
###   Accepted values (per mineru-api POST /tasks form parameter `backend`):
###     hybrid-auto-engine - pipeline + VLM combo with auto-selected local
###                          engine (mineru-api's default). GPU required.
###     pipeline           - CPU-friendly traditional pipeline; no VLM step.
###     vlm-auto-engine    - VLM with auto-selected local inference engine
###                          (sglang-engine / vllm-engine if GPU is available);
###                          requires the matching engine extra preinstalled
###                          on the mineru-api side, plus model weights.
###   We ship `hybrid-auto-engine` -- requires the target mineru-api
###   deployment to have a GPU plus the matching inference engine
###   (sglang / vllm) and model weights installed. Switch to `pipeline`
###   for CPU-only deployments without those dependencies.
MINERU_LOCAL_BACKEND=hybrid-auto-engine
### MINERU_LOCAL_PARSE_METHOD: parsing strategy for the pipeline component.
###   Accepted values:
###     auto - auto-detect embedded text-layer vs OCR per page (default).
###     txt  - extract text from the embedded text layer only; fastest,
###            but yields empty output on scanned PDFs without a text layer.
###     ocr  - force OCR on every page regardless of text-layer quality;
###            slowest, reliable on scanned or low-quality PDFs.
###   Only consumed when MINERU_LOCAL_BACKEND is `pipeline` or
###   `hybrid-auto-engine` (the pipeline arm of the hybrid pipeline).
###   Pure VLM backends (`vlm-auto-engine`, `vlm-http-client`) ignore this
###   parameter -- the VLM model handles layout/OCR natively.
MINERU_LOCAL_PARSE_METHOD=auto
### MINERU_LOCAL_IMAGE_ANALYSIS: enable VLM image/chart analysis pass for
###   better caption an footnote recognition.
###   Only consumed by `vlm-auto-engine`, `vlm-http-client`,
###   `hybrid-auto-engine`, `hybrid-http-client`. The `pipeline` backend
###   silently drops this flag -- its `_process_pipeline` does not accept
###   the kwarg, so setting `false` under pipeline does NOT speed parsing
###   up; pipeline never invokes the VLM image pass to begin with.
###   Disable (`false`) on VLM / hybrid backends to skip the extra VLM
###   round, trading image / chart semantic descriptions for faster parsing
###   and lower GPU cost.
MINERU_LOCAL_IMAGE_ANALYSIS=true
# MINERU_LOCAL_START_PAGE_ID=0
# MINERU_LOCAL_END_PAGE_ID=99999

### ---- MinerU official-only (MINERU_API_MODE=official) ----
# MINERU_API_TOKEN=your-api-key
# MINERU_OFFICIAL_ENDPOINT=https://mineru.net
# MINERU_MODEL_VERSION=vlm
# MINERU_IS_OCR=false

### Force re-upload of file to MinerU on every retry after failure
### Disables caching of result outcomes
# LIGHTRAG_FORCE_REPARSE_MINERU=false

### Docling parser (docling-serve v1 / async API).
###
### Endpoint: base URL only — the client appends /v1/convert/file/async,
###     /v1/status/poll/{task_id}?wait=<DOCLING_POLL_INTERVAL_SECONDS>,
###     /v1/result/{task_id} itself.
### Pipeline shape (pipeline=standard, target_type=zip,
###     to_formats=[json,md], image_export_mode=referenced) is fixed in
###     code so the sidecar flow stays self-consistent — flipping any of
###     these would break the adapter and is therefore not exposed as env.
###
### OCR tunables:
### - DOCLING_DO_OCR: master switch; when false the engine relies only on
###     text-layer extraction.
### - DOCLING_FORCE_OCR: when true, OCR every page regardless of text-layer
###     quality (slower, useful for scanned PDFs with bad text layers).
### - DOCLING_OCR_ENGINE: explicit engine selection (DEPRECATED in the
###     docling-serve OpenAPI but still honored for older deployments).
### - DOCLING_OCR_PRESET: recommended replacement for DOCLING_OCR_ENGINE.
### - DOCLING_OCR_LANG: JSON array (e.g. ["en","zh"]) or comma-separated
###     list. Empty (default) lets the OCR engine pick its default.
### - DOCLING_DO_FORMULA_ENRICHMENT: when true, the code-formula model runs
###     and `texts[*].label="formula"` items carry LaTeX in `text`. Default
###     false because the model may not be present on every deployment;
###     adapter falls back to plain-text formulas when disabled.
###
### Polling budget (server-side long-poll; client does NOT add extra sleep):
### - DOCLING_POLL_INTERVAL_SECONDS: ``?wait=N`` value sent to
###     /v1/status/poll/{task_id}. Larger N = fewer round trips per parse;
###     bound by your reverse-proxy idle timeout. Default 5.
### - DOCLING_MAX_POLLS: max polling rounds before raising TimeoutError.
###     Worst-case wall-clock budget ≈
###     DOCLING_POLL_INTERVAL_SECONDS × DOCLING_MAX_POLLS. Default 240
###     (≈ 20 minutes at wait=5s); raise for very large PDFs.
###
### Bundle cache controls:
### - DOCLING_ENGINE_VERSION: recorded in <base>.docling_raw/_manifest.json.
###     Mismatch with the recorded value forces a cache miss → re-download.
###     Leave empty to skip this check.
### - LIGHTRAG_FORCE_REPARSE_DOCLING: when truthy ("1"/"true"), bypass the
###     docling raw cache and re-upload on every parse_docling call.
### - DOCLING_BBOX_ATTRIBUTES: override the doc-level bbox_attributes
###     written into <base>.blocks.jsonl meta. Default
###     {"origin":"LEFTBOTTOM"} matches docling's default coordinate system.
DOCLING_ENDPOINT=http://localhost:5001
DOCLING_DO_OCR=true
DOCLING_FORCE_OCR=true
DOCLING_DO_FORMULA_ENRICHMENT=false
# DOCLING_OCR_ENGINE=auto
# DOCLING_OCR_PRESET=auto
# DOCLING_OCR_LANG=
# DOCLING_POLL_INTERVAL_SECONDS=5
# DOCLING_MAX_POLLS=240
# DOCLING_BBOX_ATTRIBUTES={"origin":"LEFTBOTTOM"}
### Force re-upload of file to Docling on every retry after failure
### Disables caching of result outcomes
# LIGHTRAG_FORCE_REPARSE_DOCLING=false

### File upload size limit (in bytes)
### 文件上传大小限制（字节）
### Default: 104857600 (100MB)
### Set to 0 or None for unlimited upload size
### 设为 0 或 None 表示不限制上传大小
### Examples:
###   52428800  = 50MB
###   104857600 = 100MB (default)
###   209715200 = 200MB
### Note: If using Nginx as reverse proxy, also configure client_max_body_size
### 注意：若使用 Nginx 反向代理，还需配置 Nginx 的 client_max_body_size
# MAX_UPLOAD_SIZE=104857600

### Entity types that the LLM will attempt to recognize
### LLM 尝试识别的实体类型列表
# ENTITY_TYPES='["Person", "Creature", "Organization", "Location", "Event", "Concept", "Method", "Content", "Data", "Artifact", "NaturalObject"]'
### Chunk size for document splitting, 500~1500 is recommended
### 文档分块大小（Token 数），建议 500~1500
### Global chunk size, 500~1500 is recommended.
### Chunker inherits the global value here only when its own var is unset.
### Exception: P never inherits CHUNK_SIZE — it uses CHUNK_P_SIZE (default 2000).

# CHUNK_SIZE=1200
# CHUNK_OVERLAP_SIZE=100     # 相邻 chunk 重叠的 Token 数，用于保留上下文连贯性

### Fixed-token chunker (process_options=F, default) settings
###     CHUNK_F_SIZE: per-strategy chunk_token_size override; falls back to CHUNK_SIZE when unset
###     CHUNK_F_OVERLAP_SIZE: token overlap; falls back to CHUNK_OVERLAP_SIZE when unset
###     CHUNK_F_SPLIT_BY_CHARACTER: optional separator string; pre-segment before token windowing
###     CHUNK_F_SPLIT_BY_CHARACTER_ONLY: when true, raise on oversize segment instead of token re-split
# CHUNK_F_SIZE=1200
# CHUNK_F_OVERLAP_SIZE=100
# CHUNK_F_SPLIT_BY_CHARACTER=
# CHUNK_F_SPLIT_BY_CHARACTER_ONLY=false

### Recursive character chunker (process_options=R) settings
###     CHUNK_R_SIZE: per-strategy chunk_token_size override; falls back to CHUNK_SIZE when unset
###     CHUNK_R_OVERLAP_SIZE: token overlap between adjacent chunks; falls back to CHUNK_OVERLAP_SIZE when unset
###     CHUNK_R_SEPARATORS: JSON array of cascaded separators tried by RecursiveCharacterTextSplitter.
###       Default includes CJK sentence-ending punctuation so Chinese / mixed-language
###       documents split at semantic boundaries.  Order: paragraph (\n\n) > line (\n) >
###       Chinese sentence-end (。！？) > Chinese semi-clause (；，) > space > char.
###       English ".?!" are intentionally omitted (literal match would split "0.95" /
###       "e.g."); the English path falls through space / char as before.
# CHUNK_R_SIZE=1200
# CHUNK_R_OVERLAP_SIZE=100
# CHUNK_R_SEPARATORS=["\n\n","\n","。","！","？","；","，"," ",""]

### Semantic vector chunker (process_options=V) settings
###     CHUNK_V_SIZE: per-strategy chunk_token_size hard cap (oversized pieces are
###       re-split via R before being emitted); falls back to CHUNK_SIZE when unset
###     CHUNK_V_BREAKPOINT_THRESHOLD_TYPE: percentile | standard_deviation | interquartile | gradient
###     CHUNK_V_BREAKPOINT_THRESHOLD_AMOUNT: leave empty to use the LangChain per-type default (e.g. 95 for percentile)
###     CHUNK_V_BUFFER_SIZE: number of adjacent sentences combined when computing distances
###     CHUNK_V_SENTENCE_SPLIT_REGEX: regex fed to LangChain SemanticChunker for the
###       initial sentence split.  Default extends the upstream English-only pattern
###       with CJK sentence-end punctuation (。？！).  Override if you need a
###       different language mix.  Note: env value is the raw regex string, no JSON
###       quoting.
# CHUNK_V_SIZE=1200
# CHUNK_V_BREAKPOINT_THRESHOLD_TYPE=percentile
# CHUNK_V_BREAKPOINT_THRESHOLD_AMOUNT=
# CHUNK_V_BUFFER_SIZE=1
# CHUNK_V_SENTENCE_SPLIT_REGEX=(?<=[.?!])\s+|(?<=[。？！])

### Paragraph semantic chunker (process_options=P) settings
###     CHUNK_P_SIZE: per-strategy chunk_token_size override; defaults to 2000 when unset
###       (does NOT fall back to CHUNK_SIZE — paragraph-semantic merging needs more
###       headroom than the global default to keep related paragraphs together).
###     CHUNK_P_OVERLAP_SIZE: overlap for prose fallback and table-bridge context;
###                           falls back to CHUNK_OVERLAP_SIZE when unset
# CHUNK_P_SIZE=2000
# CHUNK_P_OVERLAP_SIZE=100

### Number of summary segments or tokens to trigger LLM summary on entity/relation merge (at least 3 is recommended)
### 实体/关系合并时触发 LLM 摘要的描述条数阈值（建议至少为 3）
# FORCE_LLM_SUMMARY_ON_MERGE=8
### Max description token size to trigger LLM summary
### 触发 LLM 摘要的描述最大 Token 数阈值
# SUMMARY_MAX_TOKENS = 1200
### Recommended LLM summary output length in tokens
### LLM 摘要输出推荐长度（Token 数）
# SUMMARY_LENGTH_RECOMMENDED=600
### Maximum context size sent to LLM for description summary
### 发送给 LLM 进行描述摘要时的最大上下文 Token 数
# SUMMARY_CONTEXT_SIZE=12000
### Maximum token size allowed for entity extraction input context
### 实体提取输入内容允许的最大 Token 数
# MAX_EXTRACT_INPUT_TOKENS=20480

### Multimodal surrounding-context budget (per-half token cap for the
### `leading` / `trailing` text injected into VLM and extract prompts).
### Computed at analyze_multimodal entry; the two halves are independent
### so deployments can bias context forward or backward as needed.
# SURROUNDING_LEADING_MAX_TOKENS=2000
# SURROUNDING_TRAILING_MAX_TOKENS=2000

### Per-response cap on total entity+relationship rows/records emitted by the LLM
# MAX_EXTRACTION_RECORDS=100
### Per-response cap on entity rows/objects emitted by the LLM
# MAX_EXTRACTION_ENTITIES=40

### control the maximum chunk_ids stored in vector and graph db
### 控制向量库和图数据库中每个实体/关系存储的最大 chunk ID 数
# MAX_SOURCE_IDS_PER_ENTITY=300
# MAX_SOURCE_IDS_PER_RELATION=300
### control chunk_ids limitation method: FIFO, KEEP
### chunk ID 数量限制策略
###    FIFO: First in first out  先进先出（保留最新的）
###    KEEP: Keep oldest (less merge action and faster)  保留最旧的（合并操作少、速度更快）
# SOURCE_IDS_LIMIT_METHOD=FIFO

# Maximum number of file paths stored in entity/relation file_path field (For displayed only, does not affect query performance)
# 实体/关系的 file_path 字段中存储的最大文件路径数（仅用于显示，不影响查询性能）
### Maximum number of file paths stored in entity/relation file_path field
### For displayed only, does not affect query performance
# MAX_FILE_PATHS=100

### PDF decryption password for protected PDF files
### 加密 PDF 文件的解密密码
# PDF_DECRYPT_PASSWORD=your_pdf_password_here


###############################
### Concurrency Configuration
### 并发配置
###############################
### Max concurrency requests of LLM (for both query and document processing)
### LLM 最大并发请求数（包括查询和文档处理）
MAX_ASYNC=16
### LLM cache for entity/relation extract is enable by default
### Disabling it will prevent graph reconstruction after document deletion
# ENABLE_LLM_CACHE_FOR_EXTRACT=true

########################################
### Pipeline Concurrency Configuration
########################################
### Number of parallel processing documents(between 2~10, MAX_ASYNC/3 is recommended)
### 并行处理的文档数（2~10 之间，建议为 MAX_ASYNC/3）
MAX_PARALLEL_INSERT=2
### Optional per-stage document pipeline concurrency
# MAX_PARALLEL_PARSE_NATIVE=5
# MAX_PARALLEL_PARSE_MINERU=1
# MAX_PARALLEL_PARSE_DOCLING=1
# MAX_PARALLEL_ANALYZE=5
### Optional queue sizes for staged pipeline workers
# QUEUE_SIZE_DEFAULT=100
# QUEUE_SIZE_INSERT=4
### Max concurrency requests for Embedding
### Embedding 最大并发请求数
# EMBEDDING_FUNC_MAX_ASYNC=8

### Num of chunks send to Embedding in single request
### 每次 Embedding 请求发送的 chunk 数量（批处理大小）
# EMBEDDING_BATCH_NUM=10

###########################################################################
### LLM Configuration
### 大语言模型（LLM）配置
### LLM_BINDING type: openai, ollama, lollms, azure_openai, aws_bedrock, gemini
### LLM_BINDING 类型：openai / ollama / lollms / azure_openai / aws_bedrock / gemini
### LLM_BINDING_HOST: Service endpoint (left empty if using default endpoint provided by openai or gemini SDK)
### LLM_BINDING_HOST：服务地址（使用 OpenAI 或 Gemini SDK 默认端点时可留空）
### LLM_BINDING_API_KEY: api key

### Num of chunks send to Embedding in single request (default is 10)
EMBEDDING_BATCH_NUM=32

###########################################################################
### Gloabal LLM Configuration
###   LLM_BINDING type: openai, ollama, lollms, azure_openai, bedrock, gemini
###   LLM_BINDING_HOST: Service endpoint (left empty if using the provider SDK default endpoint)
###   LLM_BINDING_API_KEY: api key

### If LightRAG deployed in Docker:
### 若 LightRAG 部署在 Docker 中：
###    uses host.docker.internal instead of localhost in LLM_BINDING_HOST
###    LLM_BINDING_HOST 中用 host.docker.internal 替代 localhost
###########################################################################
### LLM request timeout setting for all llm (0 means no timeout for Ollma)
### LLM 请求超时秒数（0 表示 Ollama 不超时）
# LLM_TIMEOUT=180


LLM_BINDING=openai
# LLM_BINDING=openai                           # LLM 接入方式
LLM_BINDING_HOST=http://192.168.222.210:8000/v1
# LLM_BINDING_HOST=https://api.openai.com/v1   # LLM 服务地址
LLM_BINDING_API_KEY=bori-qwen3-2012
# LLM_BINDING_API_KEY=your_api_key             # LLM API 密钥
LLM_MODEL=Qwen3-32B
# LLM_MODEL=gpt-5-mini                         # 使用的模型名称

### use the following command to see all support options for OpenAI, azure_openai or OpenRouter
### 运行以下命令查看 OpenAI/azure_openai/OpenRouter 的全部支持选项：
### lightrag-server --llm-binding openai --help
### OpenAI Specific Parameters
### OpenAI 专属参数
# OPENAI_LLM_REASONING_EFFORT=minimal        # 推理力度（minimal/medium/high）
### OpenRouter Specific Parameters
### OpenRouter 专属参数
# OPENAI_LLM_EXTRA_BODY='{"reasoning": {"enabled": false}}'
### Qwen3 Specific Parameters deploy by vLLM
### Qwen3（vLLM 部署）专属参数
# OPENAI_LLM_EXTRA_BODY='{"chat_template_kwargs": {"enable_thinking": false}}'

### OpenAI Compatible API Specific Parameters
### OpenAI 兼容 API 专属参数
### Increased temperature values may mitigate infinite inference loops in certain LLM, such as Qwen3-30B.
### 增大 temperature 可缓解某些模型（如 Qwen3-30B）的无限推理循环
# OPENAI_LLM_TEMPERATURE=0.9
### Set the max_tokens to mitigate endless output of some LLM (less than LLM_TIMEOUT * llm_output_tokens/second, i.e. 9000 = 180s * 50 tokens/s)
### 设置 max_tokens 防止某些模型的无限输出（建议 < LLM_TIMEOUT × 输出速率）
### Typically, max_tokens does not include prompt content
### 通常 max_tokens 不包含 prompt 内容
### For vLLM/SGLang deployed models, or most of OpenAI compatible API provider
### 适用于 vLLM/SGLang 部署的模型及多数 OpenAI 化接口

# LLM_BINDING=openai
# LLM_BINDING_HOST=https://api.openai.com/v1
# LLM_BINDING_API_KEY=your_api_key
# LLM_MODEL=gpt-5.4-mini

### Max concurrency requests of LLM
MAX_ASYNC=16

###########################################################################
### Role-specific LLM/VLM overrides
### Available roles: EXTRACT, KEYWORD, QUERY, VLM
### If unset, each role falls back to gloabal LLM configuration above.
### For detail information, refer to:
###   docs/RoleSpecificLLMConfiguration.md
###   docs/RoleSpecificLLMConfiguration-zh.md
###########################################################################
KEYWORD_LLM_MODEL=Qwen3-32B
KEYWORD_MAX_ASYNC_LLM=4
# KEYWORD_LLM_TIMEOUT=180
# KEYWORD_LLM_BINDING=openai
# KEYWORD_LLM_BINDING_HOST=https://api.openai.com/v1
# KEYWORD_LLM_BINDING_API_KEY=your_api_key

QUERY_LLM_MODEL=Qwen3-32B
QUERY_MAX_ASYNC_LLM=4
# QUERY_LLM_TIMEOUT=180
# QUERY_LLM_BINDING=openai
# QUERY_LLM_BINDING_HOST=https://api.openai.com/v1
# QUERY_LLM_BINDING_API_KEY=your_api_key

# VLM_LLM_MODEL=gpt-5.4-mini
# VLM_MAX_ASYNC_LLM=4
# VLM_LLM_TIMEOUT=180
# VLM_LLM_BINDING=openai
# VLM_LLM_BINDING_HOST=https://api.example.com/v1
# VLM_LLM_BINDING_API_KEY=your_vlm_api_key

### Master switch for VLM multimodal analysis (i/t/e items).
### When false, multimodal item is skipped regardless of document process_options
### When true, VLM_LLM_BINDING (or the base LLM_BINDING) must be vision-capable
### lollms is rejected at startup
VLM_PROCESS_ENABLE=false
### Maximum image bytes sent to VLM (5242880=5MB)
VLM_MAX_IMAGE_BYTES=5242880

###########################################################################
### Provider sepecific LLM options
### Increasing the temperature setting may help mitigate infinite inference
###   loops during entity/elation extraction, particularly when using
###   models with more limited capabilities, such as Qwen3-30B
### Set a max output token limit to prevent endless output from certain LLMs,
###   which may trigger timeout errors during entity and relation extraction.
###        max_output_token < LLM_TIMEOUT * llm_tokens_per_second
###   i.e. max_output_token = 9000 = 180s * 50 tokens/s
### Sample commands to list all supported options specific LLM_BINDING:
###   lightrag-server --llm-binding openai  --help
###   lightrag-server --llm-binding bedrock --help
###   lightrag-server --llm-binding gemini  --help
###########################################################################
### OpenAI Specific Parameters (Openrouter of other OpenAI compatible API):
###     LLM_BINDING=openai
###     LLM_BINDING_HOST=https://openrouter.ai/api/v1
###     LLM_MODEL=google/gemini-2.5-flash
# OPENAI_LLM_TEMPERATURE=0.9
### For vLLM/SGLang and most of OpenAI compatible API provider

# OPENAI_LLM_MAX_TOKENS=9000
### For OpenAI o1-mini or newer modles utilizes max_completion_tokens instead of max_tokens
### OpenAI o1-mini 及更新模型使用 max_completion_tokens 替代 max_tokens
# OPENAI_LLM_MAX_COMPLETION_TOKENS=9000
### For OpenAI reason control
# OPENAI_LLM_REASONING_EFFORT=minimal
### For OpenRouter reasoning control
# OPENAI_LLM_EXTRA_BODY='{"reasoning": {"enabled": false}}'
### For Qwen3 reasoning control deploy by vLLM
# OPENAI_LLM_EXTRA_BODY='{"chat_template_kwargs": {"enable_thinking": false}}'


### Azure OpenAI example
### Azure OpenAI 配置示例
### Use deployment name as model name or set AZURE_OPENAI_DEPLOYMENT instead
### 使用部署名作为模型名，或单独设置 AZURE_OPENAI_DEPLOYMENT

### Azure OpenAI Specific Parameters:
###     LLM_BINDING=azure_openai
###     LLM_BINDING_HOST=https://xxxx.openai.azure.com/
###     LLM_BINDING_API_KEY=your_api_key
###     LLM_MODEL=my-gpt-mini-deployment
### You may use deployment name for LLM_MODEL or set AZURE_OPENAI_DEPLOYMENT instead
# AZURE_OPENAI_DEPLOYMEN=my—deplyment-name

# AZURE_OPENAI_API_VERSION=2024-08-01-preview


### Openrouter example
### OpenRouter 配置示例
# # LLM_BINDING=openai
# # LLM_BINDING_HOST=https://openrouter.ai/api/v1
# # LLM_BINDING_API_KEY=your_api_key
# # LLM_MODEL=google/gemini-2.5-flash

### Google Gemini example (AI Studio)
### Google Gemini 配置示例（AI Studio）
# # LLM_BINDING=gemini
# # LLM_BINDING_API_KEY=your_gemini_api_key
# # LLM_BINDING_HOST=https://generativelanguage.googleapis.com
# # LLM_MODEL=gemini-flash-latest

### use the following command to see all support options for OpenAI, azure_openai or OpenRouter
### lightrag-server --llm-binding gemini --help
### Gemini Specific Parameters
### Gemini 专属参数
# GEMINI_LLM_MAX_OUTPUT_TOKENS=9000          # 最大输出 Token 数
# GEMINI_LLM_TEMPERATURE=0.7                 # 采样温度
### Enable or disable thinking
### 是否启用思考模式（Thinking）
# GEMINI_LLM_THINKING_CONFIG='{"thinking_budget": -1, "include_thoughts": true}'
# # GEMINI_LLM_THINKING_CONFIG='{"thinking_budget": 0, "include_thoughts": false}'

### Google Vertex AI example
### Google Vertex AI 配置示例
### Vertex AI use GOOGLE_APPLICATION_CREDENTIALS instead of API-KEY for authentication
### Vertex AI 使用 GOOGLE_APPLICATION_CREDENTIALS 认证，而非 API-KEY
### LLM_BINDING_HOST=DEFAULT_GEMINI_ENDPOINT means select endpoit based on project and location automatically
### DEFAULT_GEMINI_ENDPOINT 表示根据 project 和 location 自动选择端点
# # LLM_BINDING=gemini
# # LM_BINDING_HOST=https://aiplatform.googleapis.com
### or use DEFAULT_GEMINI_ENDPOINT to select endpoint based on project and location automatically
# # LLM_BINDING_HOST=DEFAULT_GEMINI_ENDPOINT
# # LLM_MODEL=gemini-2.5-flash

### Google AI Studio Gemini Specific Parameters:
### DEFAULT_GEMINI_ENDPOINT means selecting endpoit by SDK automatically
###     LLM_BINDING=gemini
###     LLM_BINDING_HOST=DEFAULT_GEMINI_ENDPOINT
###     LLM_BINDING_API_KEY=your_gemini_api_key
###     LLM_MODEL=gemini-flash-latest
# GEMINI_LLM_TEMPERATURE=0.7
# GEMINI_LLM_MAX_OUTPUT_TOKENS=9000
### Enable or disable thinking
###     GEMINI_LLM_THINKING_CONFIG='{"thinking_budget": -1, "include_thoughts": true}'
###     GEMINI_LLM_THINKING_CONFIG='{"thinking_budget": 0, "include_thoughts": false}'
# GEMINI_LLM_THINKING_CONFIG='{"thinking_budget": 0, "include_thoughts": false}'

### Google Vertex AI Gemini Specific Parameters:
### Vertex AI use GOOGLE_APPLICATION_CREDENTIALS instead of API-KEY for authentication

# GOOGLE_GENAI_USE_VERTEXAI=true
# GOOGLE_CLOUD_PROJECT='your-project-id'     # GCP 项目 ID
# GOOGLE_CLOUD_LOCATION='us-central1'        # GCP 区域
# GOOGLE_APPLICATION_CREDENTIALS='/Users/xxxxx/your-service-account-credentials-file.json'  # 服务账号凭证文件


### Ollama example
### Ollama 配置示例
# # LLM_BINDING=ollama
# # LLM_BINDING_HOST=http://localhost:11434
# # LLM_MODEL=qwen3.5:9b

### use the following command to see all support options for Ollama LLM
### lightrag-server --llm-binding ollama --help
### Ollama Server Specific Parameters
### Ollama 专属参数
### OLLAMA_LLM_NUM_CTX must be provided, and should at least larger than MAX_TOTAL_TOKENS + 2000
### 必须设置，且应大于 MAX_TOTAL_TOKENS + 2000
# Ollama 模型上下文窗口大小
OLLAMA_LLM_NUM_CTX=32768
### Set the max_output_tokens to mitigate endless output of some LLM (less than LLM_TIMEOUT * llm_output_tokens/second, i.e. 9000 = 180s * 50 tokens/s)
### 限制输出 Token 数防止模型无限输出
# OLLAMA_LLM_NUM_PREDICT=9000
# OLLAMA_LLM_TEMPERATURE=0.85               # 采样温度
### Stop sequences for Ollama LLM
### Ollama 停止标识序列
# OLLAMA_LLM_STOP='["</s>", "<|EOT|>"]'

### Bedrock Specific Parameters
### AWS Bedrock 专属参数
### Bedrock uses AWS credentials from the environment / AWS credential chain.
### Bedrock 使用环境变量或 AWS 凭证链进行认证，不使用 LLM_BINDING_API_KEY
### It does not use LLM_BINDING_API_KEY.
# # LLM_BINDING=aws_bedrock
# # LLM_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
# AWS_ACCESS_KEY_ID=your_aws_access_key_id       # AWS 访问密钥 ID
# AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key  # AWS 秘密访问密钥
# AWS_SESSION_TOKEN=your_optional_aws_session_token  # AWS 会话 Token（临时凭证时需要）
# AWS_REGION=us-east-1                           # AWS 区域
# BEDROCK_LLM_TEMPERATURE=1.0                    # 采样温度

#######################################################################################
### Embedding Configuration (Should not be changed after the first file processed)
### Embedding 配置（首个文件入库后不应更改！更换模型必须清空向量数据）
### EMBEDDING_BINDING: ollama, openai, azure_openai, jina, lollms, aws_bedrock
### EMBEDDING_BINDING 类型：ollama / openai / azure_openai / jina / lollms / aws_bedrock

### Bedrock Specific Parameters:
###     LLM_BINDING=bedrock
###     LLM_BINDING_HOST=DEFAULT_BEDROCK_ENDPOINT
###     LLM_MODEL=us.amazon.nova-lite-v1:0
### Region is required for all three modes (Bedrock endpoints are regional).
# AWS_REGION=us-west-1
### Bedrock Authentication (choose ONE of the following three approaches):
### Bedrock API key (bearer token). Bedrock ignores LLM_BINDING_API_KEY;
### set AWS_BEARER_TOKEN_BEDROCK directly before startup. This is a
### process-level AWS SDK setting and cannot be overridden per role.
# AWS_BEARER_TOKEN_BEDROCK=your_bedrock_api_key
### SigV4 credentials (classic IAM user / STS / instance profile).
# AWS_ACCESS_KEY_ID=your_aws_access_key_id
# AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
# AWS_SESSION_TOKEN=your_optional_aws_session_token
### Ambient credentials (AWS SDK default credential chain).
### To use this mode, leave AWS_BEARER_TOKEN_BEDROCK, AWS_ACCESS_KEY_ID,
### AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN above commented out — the
### AWS SDK will then resolve credentials from ~/.aws/credentials, IAM role,
### instance profile, SSO, or environment variables outside .env.
### Activating any of the lines above forces that explicit mode and bypasses
### the credential chain.
# BEDROCK_LLM_TEMPERATURE=1.0
# BEDROCK_LLM_MAX_TOKENS=9000
# BEDROCK_LLM_TOP_P=1.0
# BEDROCK_LLM_STOP_SEQUENCES='["</s>"]'
### Bedrock model reasoning control
# BEDROCK_LLM_EXTRA_FIELDS='{"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}}'

### Ollama Specific Parameters:
###     LLM_BINDING=ollama
###     LLM_BINDING_HOST=http://localhost:11434
###     LLM_MODEL=qwen3.5:9b
### OLLAMA_LLM_NUM_CTX must be provided, and should at least larger than MAX_TOTAL_TOKENS + 2000
OLLAMA_LLM_NUM_CTX=32768
# OLLAMA_LLM_NUM_PREDICT=9000
# OLLAMA_LLM_TEMPERATURE=0.85
# OLLAMA_LLM_STOP='["</s>", "<|EOT|>"]'

#######################################################################################
### Embedding Configuration (Should not be changed after the first file processed)
### EMBEDDING_BINDING: ollama, openai, azure_openai, jina, lollms, bedrock

### EMBEDDING_BINDING_HOST: Service endpoint (left empty if using default endpoint provided by openai or gemini SDK)
### EMBEDDING_BINDING_HOST：服务地址（使用 OpenAI 或 Gemini SDK 默认端点时可留空）
### EMBEDDING_BINDING_API_KEY: api key
### If LightRAG deployed in Docker:
### 若 LightRAG 部署在 Docker 中：EMBEDDING_BINDING_HOST 中用 host.docker.internal 替代 localhost
### Control whether to send embedding_dim parameter to embedding API
### 是否向 Embedding API 发送 embedding_dim 参数
###    For OpenAI: Set EMBEDDING_SEND_DIM=true to enable dynamic dimension adjustment
###    OpenAI：设为 true 启用动态维度调整
###    For OpenAI: Set EMBEDDING_SEND_DIM=false (default) to disable sending dimension parameter
###    OpenAI：默认 false，不发送维度参数
###    For Gemini: Allways set EMBEDDING_SEND_DIM=true
###    Gemini：必须设为 true
### Control whether to use base64 encoding format for embeddings (improves performance for OpenAI)
### 是否使用 base64 格式返回嵌入向量（提升 OpenAI 性能）
###    For OpenAI: Set EMBEDDING_USE_BASE64=true (default) to use base64 encoding
###    OpenAI：默认 true，使用 base64 格式
###    For Yandex Cloud and other providers that don't support it: Set EMBEDDING_USE_BASE64=false
###    Yandex Cloud 等不支持 base64 的提供商：设为 false
#######################################################################################
# EMBEDDING_TIMEOUT=30                        # Embedding 请求超时秒数

### OpenAI compatible embedding

### OpenAI 入口兼容的 Embedding 服务
EMBEDDING_BINDING=ollama
# EMBEDDING_BINDING=openai                      # Embedding 接入方式
EMBEDDING_BINDING_HOST=http://192.168.93.19:11434
# EMBEDDING_BINDING_HOST=https://api.openai.com/v1  # Embedding 服务地址
# Embedding API 密钥
EMBEDDING_BINDING_API_KEY=your_api_key
EMBEDDING_MODEL=qwen3-embedding:0.6b
# EMBEDDING_MODEL=text-embedding-3-large        # Embedding 模型名称
EMBEDDING_DIM=1024
# EMBEDDING_DIM=3072                            # Embedding 向量维度
# Embedding 单次请求最大 Token 数
EMBEDDING_TOKEN_LIMIT=8192
# 是否向服务端发送维度参数
EMBEDDING_SEND_DIM=false
# EMBEDDING_USE_BASE64=true                   # 是否使用 base64 格式返回向量

### Optional for Azure Embedding
### Azure Embedding 配置示例
### Use deployment name as model name or set AZURE_EMBEDDING_DEPLOYMENT instead
### 使用部署名作为模型名，或单独设置 AZURE_EMBEDDING_DEPLOYMENT
# # EMBEDDING_BINDING=azure_openai
# # EMBEDDING_BINDING_HOST=https://xxxx.openai.azure.com/
# # EMBEDDING_API_KEY=your_api_key
# # EMBEDDING_MODEL==my-text-embedding-3-large-deployment
# # EMBEDDING_DIM=3072
# AZURE_EMBEDDING_API_VERSION=2024-08-01-preview

### Gemini embedding
### Gemini Embedding 配置示例
# # EMBEDDING_BINDING=gemini
# # EMBEDDING_MODEL=gemini-embedding-001
# # EMBEDDING_DIM=1536
# # EMBEDDING_TOKEN_LIMIT=2048
# # EMBEDDING_BINDING_HOST=https://generativelanguage.googleapis.com
# # EMBEDDING_BINDING_API_KEY=your_api_key
### Gemini embedding requires sending dimension to server
### Gemini Embedding 必须向服务端发送维度参数
# # EMBEDDING_SEND_DIM=true

### Ollama embedding
### Ollama Embedding 配置示例
# # EMBEDDING_BINDING=ollama
# # EMBEDDING_BINDING_HOST=http://localhost:11434
# # EMBEDDING_BINDING_API_KEY=your_api_key
# # EMBEDDING_MODEL=qwen3-embedding:4b
# # EMBEDDING_DIM=2560
### Optional for Ollama embedding
# Ollama Embedding 模型上下文窗口大小
OLLAMA_EMBEDDING_NUM_CTX=8192
### use the following command to see all support options for Ollama embedding
### lightrag-server --embedding-binding ollama --help

### Bedrock embedding
### AWS Bedrock Embedding 配置示例
### Bedrock uses AWS credentials from the environment / AWS credential chain.
### Bedrock 使用环境变量或 AWS 凭证链认证，不使用 EMBEDDING_BINDING_API_KEY
### It does not use EMBEDDING_BINDING_API_KEY.
# # EMBEDDING_BINDING=aws_bedrock
# # EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
# # EMBEDDING_DIM=1024
# AWS_ACCESS_KEY_ID=your_aws_access_key_id
# AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
# AWS_SESSION_TOKEN=your_optional_aws_session_token
# AWS_REGION=us-east-1

### Jina AI Embedding
### Jina AI Embedding 配置示例
# # EMBEDDING_BINDING=jina
# # EMBEDDING_BINDING_HOST=https://api.jina.ai/v1/embeddings
# # EMBEDDING_MODEL=jina-embeddings-v4
# # EMBEDDING_DIM=2048
# # EMBEDDING_BINDING_API_KEY=your_api_key

# EMBEDDING_BINDING=openai
# EMBEDDING_BINDING_HOST=https://api.openai.com/v1
EMBEDDING_BINDING_API_KEY=your_api_key
# EMBEDDING_MODEL=text-embedding-3-large
# EMBEDDING_DIM=3072
EMBEDDING_TOKEN_LIMIT=8192
EMBEDDING_SEND_DIM=false
EMBEDDING_USE_BASE64=true

### Optional: asymmetric embeddings (query/document behavior split)
### Leave EMBEDDING_ASYMMETRIC unset or set false to keep symmetric behavior.
### Set true only when the selected embedding backend supports asymmetric mode.
# EMBEDDING_ASYMMETRIC=true
### Provider-task bindings such as Jina/Gemini/VoyageAI use provider parameters
### and should not configure the prefix variables below.
### Prefix-based models such as BGE/E5/GTE require both prefix variables.
### Wrap non-empty values with quotes if there are trailing spaces.
# EMBEDDING_DOCUMENT_PREFIX="search_document: "
### Use NO_PREFIX for a side that should intentionally have no prefix.
###     EMBEDDING_DOCUMENT_PREFIX=NO_PREFIX
# EMBEDDING_QUERY_PREFIX="search_query: "

###########################################################################
### Provider sepecific Embedding options
### Increasing the temperature setting may help mitigate infinite inference
###   loops during entity/elation extraction, particularly when using
###   models with more limited capabilities, such as Qwen3-30B
### Set a max output token limit to prevent endless output from certain LLMs,
###   which may trigger timeout errors during entity and relation extraction.
###        max_output_token < LLM_TIMEOUT * llm_tokens_per_second
###   i.e. max_output_token = 9000 = 180s * 50 tokens/s
### Sample commands to list all supported options specific EMBEDDING_BINDING:
###   lightrag-server --embedding-binding openai --help
###   lightrag-server --embedding-binding ollama --help
###   lightrag-server --embedding-binding bedrock --help
###########################################################################
### Azure Embedding Specific Parameters:
### Use deployment name as model name or set AZURE_EMBEDDING_DEPLOYMENT instead
###     EMBEDDING_BINDING=azure_openai
###     EMBEDDING_BINDING_HOST=https://xxxx.openai.azure.com/
###     EMBEDDING_API_KEY=your_api_key
###     EMBEDDING_MODEL==my-text-embedding-3-large-deployment
###     EMBEDDING_DIM=3072
# AZURE_EMBEDDING_API_VERSION=2024-08-01-preview

### Ollama Embedding Specific Parameters:
###     EMBEDDING_BINDING=ollama
###     EMBEDDING_BINDING_HOST=http://localhost:11434
###     EMBEDDING_BINDING_API_KEY=your_api_key
###     EMBEDDING_MODEL=qwen3-embedding:4b
###     EMBEDDING_DIM=2560
### Ollama should set num_ctx option inaddition to EMBEDDING_TOKEN_LIMIT
OLLAMA_EMBEDDING_NUM_CTX=8192

### Gemini Embedding Specific Parameters:
### DEFAULT_GEMINI_ENDPOINT means selecting endpoit by SDK automatically
### Gemini embedding requires sending dimension to server
###     EMBEDDING_BINDING=gemini
###     EMBEDDING_BINDING_HOST=DEFAULT_GEMINI_ENDPOINT
###     EMBEDDING_BINDING_API_KEY=your_api_key
###     EMBEDDING_MODEL=gemini-embedding-001
###     EMBEDDING_DIM=1536
###     EMBEDDING_TOKEN_LIMIT=2048
###     EMBEDDING_SEND_DIM=true

### Bedrock Embedding Specific Parameters:
###     EMBEDDING_BINDING=bedrock
###     EMBEDDING_BINDING_HOST=DEFAULT_BEDROCK_ENDPOINT
###     EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
###     EMBEDDING_DIM=1024
### Share the same region and authentication settings as LLMs, no reconfiguration here
###     AWS_REGION=us-west-1
###     AWS_BEARER_TOKEN_BEDROCK=your_bedrock_api_key
###     AWS_ACCESS_KEY_ID=your_aws_access_key_id
###     AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
###     AWS_SESSION_TOKEN=your_optional_aws_session_token

### Jina AI Embedding Specific Parameters:
###     EMBEDDING_BINDING=jina
###     EMBEDDING_BINDING_HOST=https://api.jina.ai/v1/embeddings
###     EMBEDDING_MODEL=jina-embeddings-v4
###     EMBEDDING_DIM=2048
###     EMBEDDING_BINDING_API_KEY=your_api_key


####################################################################
### WORKSPACE sets workspace name for all storage types
### WORKSPACE 为所有存储类型设置工作区名称
### for the purpose of isolating data from LightRAG instances.
### 用于隔离不同 LightRAG 实例的数据
### Valid workspace name constraints: a-z, A-Z, 0-9, and _
### 有效工作区名称规则：小写字母、大写字母、数字和下划线
####################################################################
# WORKSPACE=

############################
### Data storage selection
### 存储后端选择
############################
### Default storage: JSON/Nano/NetworkX (Recommended for test deployment)
### 默认存储：JSON/Nano/NetworkX（推荐用于测试部署）
LIGHTRAG_KV_STORAGE=JsonKVStorage
# LIGHTRAG_KV_STORAGE=JsonKVStorage           # KV 存储后端
LIGHTRAG_DOC_STATUS_STORAGE=JsonDocStatusStorage
# LIGHTRAG_DOC_STATUS_STORAGE=JsonDocStatusStorage  # 文档状态存储后端
LIGHTRAG_GRAPH_STORAGE=NetworkXStorage
# LIGHTRAG_GRAPH_STORAGE=NetworkXStorage      # 图数据库存储后端
LIGHTRAG_VECTOR_STORAGE=NanoVectorDBStorage
# LIGHTRAG_VECTOR_STORAGE=NanoVectorDBStorage # 向量数据库存储后端

### Wizard metadata used to preserve env-storage Docker deployment defaults across setup reruns
### 向导元数据，用于在多次配置向导运行间保留 Docker 部署默认选项
# LIGHTRAG_SETUP_POSTGRES_DEPLOYMENT=docker
# LIGHTRAG_SETUP_NEO4J_DEPLOYMENT=docker
# LIGHTRAG_SETUP_MONGODB_DEPLOYMENT=docker
# LIGHTRAG_SETUP_MONGODB_DEPLOYMENT=atlas-capable
# LIGHTRAG_SETUP_REDIS_DEPLOYMENT=docker
# LIGHTRAG_SETUP_MILVUS_DEPLOYMENT=docker
# LIGHTRAG_SETUP_QDRANT_DEPLOYMENT=docker
# LIGHTRAG_SETUP_MEMGRAPH_DEPLOYMENT=docker
# LIGHTRAG_SETUP_OPENSEARCH_DEPLOYMENT=docker

### PostgreSQL Configuration
### PostgreSQL 数据库配置
# 数据库主机地址
POSTGRES_HOST=localhost
# 数据库端口
POSTGRES_PORT=5432
# 数据库用户名
POSTGRES_USER=your_username
# 数据库密码
POSTGRES_PASSWORD='your_password'
# 数据库名称
POSTGRES_DATABASE=rag
# 连接池最大连接数
POSTGRES_MAX_CONNECTIONS=25
### DB specific workspace should not be set, keep for compatible only
### 数据库级工作区不应设置，仅保留用于展示兼容
# POSTGRES_WORKSPACE=forced_workspace_name

### Use HNSW_HALFVEC for large embeddings (2000+ dim).
### 超过 2000 维向量建议使用 HNSW_HALFVEC 索引
### Requires pgvector extension >= 0.7.0.
### 需要 pgvector 的版本 >= 0.7.0
### Vector storage type: HNSW, HNSW_HALFVEC, IVFFlat, VCHORDRQ
### 向量索引类型：HNSW / HNSW_HALFVEC / IVFFlat / VCHORDRQ
# 向量索引类型
POSTGRES_VECTOR_INDEX_TYPE=HNSW
# HNSW 每节点最大连接数
POSTGRES_HNSW_M=16
# HNSW 搜索时动态候选列表大小
POSTGRES_HNSW_EF=200
# IVFFlat 索引第元数量
POSTGRES_IVFFLAT_LISTS=100
# VCHORDRQ 构建选项
POSTGRES_VCHORDRQ_BUILD_OPTIONS=
# VCHORDRQ 探测数
POSTGRES_VCHORDRQ_PROBES=
# VCHORDRQ epsilon 参数
POSTGRES_VCHORDRQ_EPSILON=1.9

### PostgreSQL Connection Retry Configuration (Network Robustness)
### PostgreSQL 连接重试配置（网络鲁棒性）
### NEW DEFAULTS (v1.4.10+): Optimized for HA deployments with ~30s switchover time
### v1.4.10+ 新默认将0：为切换时间约30s 的高可用场景优化
### These defaults provide out-of-the-box support for PostgreSQL High Availability setups
### 这些默认将开筱支持 PostgreSQL 高可用部署
###
### Number of retry attempts (1-100, default: 10)
### 重试次数（1-100，默认 10）
###   - Default 10 attempts allows ~225s total retry time (sufficient for most HA scenarios)
###   - 默认 10 次允许约 225s 总重试时间，足够应对大多数高可用场景
###   - For extreme cases: increase up to 20-50
### Initial retry backoff in seconds (0.1-300.0, default: 3.0)
### 初始重试间隔（秒）
### Maximum retry backoff in seconds (must be >= backoff, max: 600.0, default: 30.0)
### 最大重试间隔（秒）
### Connection pool close timeout in seconds (1.0-30.0, default: 5.0)
### 连接池关闭超时（秒）
# POSTGRES_CONNECTION_RETRIES=10
# POSTGRES_CONNECTION_RETRY_BACKOFF=3.0
# POSTGRES_CONNECTION_RETRY_BACKOFF_MAX=30.0
# POSTGRES_POOL_CLOSE_TIMEOUT=5.0

### PostgreSQL SSL Configuration (Optional)
### PostgreSQL SSL 配置（可选）
# POSTGRES_SSL_MODE=require                  # SSL 模式：disable/allow/prefer/require/verify-ca/verify-full
# POSTGRES_SSL_CERT=/path/to/client-cert.pem # 客户端证书文件
# POSTGRES_SSL_KEY=/path/to/client-key.pem   # 客户端私钥文件
# POSTGRES_SSL_ROOT_CERT=/path/to/ca-cert.pem  # CA 根证书文件
# POSTGRES_SSL_CRL=/path/to/crl.pem          # 证书吐销列表文件

### PostgreSQL Server Settings (for Supabase Supavisor)
### PostgreSQL 服务器附加设置（适用于 Supabase Supavisor）
# Use this to pass extra options to the PostgreSQL connection string.
# 用于向 PostgreSQL 连接字符串传递额外选项
# For Supabase, you might need to set it like this:
# POSTGRES_SERVER_SETTINGS='options=reference%3D[project-ref]'

# Default is 100 set to 0 to disable
# 默认 100，设为 0 禁用语句缓存
# POSTGRES_STATEMENT_CACHE_SIZE=100

### Neo4j Configuration
### Neo4j 图数据库配置
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io  # Neo4j 连接 URI
NEO4J_USERNAME=neo4j                              # 用户名
NEO4J_PASSWORD='your_password'                   # 密码
NEO4J_DATABASE=neo4j                             # 数据库名称
NEO4J_MAX_CONNECTION_POOL_SIZE=100               # 连接池最大连接数
NEO4J_CONNECTION_TIMEOUT=30                      # 连接超时（秒）
NEO4J_CONNECTION_ACQUISITION_TIMEOUT=30          # 连接获取超时（秒）
NEO4J_MAX_TRANSACTION_RETRY_TIME=30              # 事务最大重试时间（秒）
NEO4J_MAX_CONNECTION_LIFETIME=300                # 连接最长生命周期（秒）
NEO4J_LIVENESS_CHECK_TIMEOUT=30                  # 连接存活检查超时（秒）
NEO4J_KEEP_ALIVE=true                            # 是否启用连接保活
### DB specific workspace should not be set, keep for compatible only
# NEO4J_WORKSPACE=forced_workspace_name

### MongoDB Configuration
### MongoDB 配置
# For MongoVectorDBStorage, MONGO_URI must point to a MongoDB endpoint with
# 使用 MongoVectorDBStorage 时，MONGO_URI 必须指向支持 Atlas Search / Vector Search 的端点
# Atlas Search / Vector Search support, such as MongoDB Atlas or Atlas local.
# MongoDB 连接 URI
MONGO_URI=mongodb://localhost:27017/
# 数据库名称
MONGO_DATABASE=LightRAG
### DB specific workspace should not be set, keep for compatible only
# MONGODB_WORKSPACE=forced_workspace_name

# Community/local Docker MongoDB example for KV, graph, or doc-status storage only:
# 社区/本地 Docker MongoDB 示例（仅适用于 KV、图、文档状态存储，不支持向量存储）：
# MONGO_URI=mongodb://localhost:27017/

### OpenSearch Configuration
### OpenSearch 配置（可用于所有存储类型：KV、向量、图、文档状态）
### OpenSearch can be used for all storage types: KV, Vector, Graph, DocStatus
### Connection settings (comma-separated host:port entries; do not include http:// or https://)
### 连接设置（逗号分隔的 host:port，不包含 http:// 或 https://）
### This setup wizard supports authenticated OpenSearch clusters only.
### 此配置向导仅支持需要认证的 OpenSearch 集群
### OPENSEARCH_USE_SSL controls whether those hosts are reached over TLS.
### OPENSEARCH_USE_SSL 控制是否通过 TLS 连接
# OpenSearch 节点地址
OPENSEARCH_HOSTS=localhost:9200
# 用户名
OPENSEARCH_USER=admin
# 密码
OPENSEARCH_PASSWORD=LightRAG2026_!@
# 是否启用 SSL
OPENSEARCH_USE_SSL=true
# 是否验证 SSL 证书
OPENSEARCH_VERIFY_CERTS=false
# OPENSEARCH_TIMEOUT=30                       # 请求超时（秒）
# OPENSEARCH_MAX_RETRIES=3                    # 最大重试次数
### Index Settings (for 3-AZ Amazon OpenSearch Service, set replicas to 2)
### 索引设置（三可用区 Amazon OpenSearch 建议 replicas=2）
# OPENSEARCH_NUMBER_OF_SHARDS=1              # 分片数
# OPENSEARCH_NUMBER_OF_REPLICAS=0            # 副本数
### k-NN Settings for Vector Storage (HNSW algorithm)
### 向量存储 k-NN 配置（HNSW 算法）
# OPENSEARCH_KNN_EF_CONSTRUCTION=200         # 构建时动态候选列表大小
# OPENSEARCH_KNN_M=16                        # 每节点最大连接数
# OPENSEARCH_KNN_EF_SEARCH=100              # 搜索时动态候选列表大小
### PPL graphlookup for server-side graph traversal (auto-detected if not set)
### 服务端图遍历的 PPL graphlookup（未设置则自动检测）
# OPENSEARCH_USE_PPL_GRAPHLOOKUP=true
### DB specific workspace should not be set, keep for compatible only
# OPENSEARCH_WORKSPACE=forced_workspace_name

### Milvus Configuration
### Milvus 向量数据库配置
# Milvus 服务地址
MILVUS_URI=http://localhost:19530
# 数据库名称
MILVUS_DB_NAME=lightrag
# MILVUS_DEVICE=cpu                          # 计算设备：cpu 或 cuda
# MILVUS_USER=root                           # 用户名
# MILVUS_PASSWORD=your_password              # 密码
# MILVUS_TOKEN=your_token                    # 认证 Token
# Required for the bundled Docker Milvus stack; may come from .env or exported shell variables.
# 捆绑 Docker Milvus 堆栈的 MinIO 凭证配置
# MINIO_ACCESS_KEY_ID=minioadmin
# MINIO_SECRET_ACCESS_KEY=minioadmin
### DB specific workspace should not be set, keep for compatible only
# MILVUS_WORKSPACE=forced_workspace_name

### Milvus Vector Index Configuration
### Milvus 向量索引配置
### Index type: AUTOINDEX (default), HNSW, HNSW_SQ, HNSW_PQ, IVF_FLAT, IVF_SQ8, DISKANN
### 索引类型：AUTOINDEX（默认）/ HNSW / HNSW_SQ / HNSW_PQ / IVF_FLAT / IVF_SQ8 / DISKANN
# MILVUS_INDEX_TYPE=AUTOINDEX

### Metric type: COSINE (default), L2, IP
### 距离度量类型：COSINE（余弦相似度，默认）/ L2（欧氏距离）/ IP（内积）
# MILVUS_METRIC_TYPE=COSINE

### HNSW / HNSW_SQ / HNSW_PQ Parameters (aligned with Milvus 2.4+ defaults)
### HNSW 系列索引参数
### M: Maximum number of connections per node [2-2048], default 16
### M：每节点最大连接数 [2-2048]，默认 16
# MILVUS_HNSW_M=16
### efConstruction: Size of dynamic candidate list during build [8-512], default 360
### efConstruction：构建时动态候选列表大小 [8-512]，默认 360
# MILVUS_HNSW_EF_CONSTRUCTION=360
### ef: Size of dynamic candidate list during search, default 200
### ef：搜索时动态候选列表大小，默认 200
# MILVUS_HNSW_EF=200

### HNSW_SQ Specific Parameters (requires Milvus 2.6.8+)
### HNSW_SQ 专属参数（需要 Milvus 2.6.8+）
### sq_type: Scalar quantization type - SQ4U, SQ6, SQ8 (default), BF16, FP16
### 标量量化类型
# MILVUS_HNSW_SQ_TYPE=SQ8
### refine: Enable refinement step for higher precision, default false
### 是否启用精度增强步骤
# MILVUS_HNSW_SQ_REFINE=false
### refine_type: Refinement precision (must be higher than sq_type) - SQ6, SQ8, BF16, FP16, FP32
### 增强精度类型（必须高于 sq_type）
# MILVUS_HNSW_SQ_REFINE_TYPE=FP32
### refine_k: Refinement expansion factor, default 10
### 增强扩展因子
# MILVUS_HNSW_SQ_REFINE_K=10

### IVF_FLAT / IVF_SQ8 Parameters
### IVF 索引参数
### nlist: Number of cluster units [1-65536], recommended sqrt(n) for n>1M, default 1024
### nlist：聚类数 [1-65536]，n>100万时建议 sqrt(n)，默认 1024
# MILVUS_IVF_NLIST=1024
### nprobe: Number of units to query [1-nlist], default 16
### nprobe：搜索时探测的聚类数 [1-nlist]，默认 16
# MILVUS_IVF_NPROBE=16

### Qdrant
### Qdrant 向量数据库配置
# Qdrant 服务地址
QDRANT_URL=http://localhost:6333
# QDRANT_DEVICE=cpu                          # 运行设备
# QDRANT_API_KEY=your-api-key                # API 密钥
### Qdrant upsert batching (enabled by default)
### Qdrant 批量写入配置（默认启用）
### Split large upserts by estimated JSON payload size and point count
### 按 JSON 负载大小和点数将大批量拆分提交
### Default 16MB keeps safe headroom below common 32MB gateway/request limits
### 默认 16MB 确保小于常见网关/请求的 32MB 限制
# QDRANT_UPSERT_MAX_PAYLOAD_BYTES=16777216   # 每批最大 JSON 负载大小（字节）
# QDRANT_UPSERT_MAX_POINTS_PER_BATCH=128     # 每批最大点数
### DB specific workspace should not be set, keep for compatible only
# QDRANT_WORKSPACE=forced_workspace_name

### Redis
### Redis 缓存配置
# Redis 连接 URI
REDIS_URI=redis://localhost:6379
# Socket 超时（秒）
REDIS_SOCKET_TIMEOUT=30
# 连接超时（秒）
REDIS_CONNECT_TIMEOUT=10
# 连接池最大连接数
REDIS_MAX_CONNECTIONS=100
# 连接失败重试次数
REDIS_RETRY_ATTEMPTS=3
### DB specific workspace should not be set, keep for compatible only
# REDIS_WORKSPACE=forced_workspace_name

### Memgraph Configuration
### Memgraph 图数据库配置
# Memgraph Bolt 协议地址
MEMGRAPH_URI=bolt://localhost:7687
# 用户名（留空表示无认证）
MEMGRAPH_USERNAME=
# 密码
MEMGRAPH_PASSWORD=
# 数据库名称
MEMGRAPH_DATABASE=memgraph
### DB specific workspace should not be set, keep for compatible only
# MEMGRAPH_WORKSPACE=forced_workspace_name

###########################################################
### Langfuse Observability Configuration
### Langfuse 可观测性配置（用于追踪 LLM 调用链路和性能）
### Only works with LLM provided by OpenAI compatible API
### 仅适用于 OpenAI 兼容接口提供的 LLM
### Install with: pip install lightrag-hku[observability]
### Sign up at: https://cloud.langfuse.com or self-host
###########################################################
# LANGFUSE_SECRET_KEY=''          # Langfuse 密钥
# LANGFUSE_PUBLIC_KEY=''          # Langfuse 公开密钥
# LANGFUSE_HOST='https://cloud.langfuse.com'  # Langfuse 服务地址
# LANGFUSE_ENABLE_TRACE=true      # 是否启用追踪

############################
### Evaluation Configuration
### RAG 质量评估配置
############################
### RAGAS evaluation models (used for RAG quality assessment)
### RAGAS 评估模型（用于评估 RAG 检索质量）
### ⚠️ IMPORTANT: Both LLM and Embedding endpoints MUST be OpenAI-compatible
### ⚠️ 重要：LLM 和 Embedding 端点必须均为 OpenAI 入口兴容格式
### Default uses OpenAI models for evaluation
### 默认使用 OpenAI 模型进行评估

### LLM Configuration for Evaluation
### 评估使用的 LLM 配置
# EVAL_LLM_MODEL=gpt-4o-mini                        # 评估用 LLM 模型
### API key for LLM evaluation (fallback to OPENAI_API_KEY if not set)
### 评估 LLM API 密钥（未设置时回退到 OPENAI_API_KEY）
# EVAL_LLM_BINDING_API_KEY=your_api_key
### Custom OpenAI-compatible endpoint for LLM evaluation (optional)
### 评估 LLM 的自定义 OpenAI 入口（可选）
# EVAL_LLM_BINDING_HOST=https://api.openai.com/v1

### Embedding Configuration for Evaluation
### 评估使用的 Embedding 配置
# EVAL_EMBEDDING_MODEL=text-embedding-3-large       # 评估用 Embedding 模型
### API key for embeddings (fallback: EVAL_LLM_BINDING_API_KEY -> OPENAI_API_KEY)
### Embedding API 密钥（回退顺序：EVAL_LLM_BINDING_API_KEY → OPENAI_API_KEY）
# EVAL_EMBEDDING_BINDING_API_KEY=your_embedding_api_key
### Custom OpenAI-compatible endpoint for embeddings (fallback: EVAL_LLM_BINDING_HOST)
### 评估 Embedding 的自定义端点（回退到 EVAL_LLM_BINDING_HOST）
# EVAL_EMBEDDING_BINDING_HOST=https://api.openai.com/v1

### Performance Tuning
### 评估性能调优
### Number of concurrent test case evaluations
### 并发评估数，较小的值可减少 API 限流错误但会增加评估时间
### Lower values reduce API rate limit issues but increase evaluation time
# EVAL_MAX_CONCURRENT=2
### TOP_K query parameter of LightRAG (default: 10)
### LightRAG 查询的 TOP_K 参数
### Number of entities or relations retrieved from KG
# EVAL_QUERY_TOP_K=10
### LLM request retry and timeout settings for evaluation
### 评估时 LLM 请求重试和超时设置
# EVAL_LLM_MAX_RETRIES=5
# EVAL_LLM_TIMEOUT=180

##########################################################################
### ----- Preserved custom environment variables from previous .env  -----
### ----- Comments in this session will persist across regenerations -----
### (This must be the final session; ensure the preceding lines unchanged)
##########################################################################
### The "make env*" wizard will leave the following lines unchanged
### You may add additional env vars or commnets here for your own purpose
##########################################################################

### AWS Bedrock
# LLM_BINDING=bedrock
# LLM_BINDING_HOST=DEFAULT_BEDROCK_ENDPOINT
# LLM_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0
# KEYWORD_LLM_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0
# QUERY_LLM_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0
# VLM_LLM_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0

### ----- Extra setting from previous .env -----
