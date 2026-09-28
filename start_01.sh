#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
exec uv run --extra api --extra offline-llm lightrag-server --port 9621 --workspace space1
