#!/bin/sh
set -eu

exec python -m jobfit_api.worker
