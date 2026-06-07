#!/bin/sh
set -e
cd "$(dirname "$0")/.."
echo "[deploy] git pull"
git pull --ff-only
echo "[deploy] rebuild & up"
docker compose up -d --build
echo "[deploy] done"
docker compose logs --tail=20 web