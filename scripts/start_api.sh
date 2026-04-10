#!/bin/sh
set -eu

PORT_VALUE="${PORT:-${API_PORT:-8000}}"

exec python -m uvicorn jobfit_api.main:app --host 0.0.0.0 --port "${PORT_VALUE}"
