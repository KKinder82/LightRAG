#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# This launcher uses LAN model services; do not inherit desktop proxy settings.
unset ALL_PROXY all_proxy HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
exec uv run --extra api --extra offline-llm lightrag-server --port 9621 --workspace space1
