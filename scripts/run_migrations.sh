#!/bin/sh
set -eu

exec python -m alembic upgrade head
