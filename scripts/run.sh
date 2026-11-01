#!/bin/bash
# Pose × Costume × Character — 一键启动
# 自动读取 .env、起服务、开浏览器

cd "$(dirname "$0")/.." || exit 1
ROOT="$(pwd)"

# 读取 .env
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

# 找 python
PY=""
for cand in \
    "$(command -v python3 2>/dev/null)" \
    "/opt/homebrew/bin/python3" \
    "/usr/local/bin/python3" \
    "/usr/bin/python3"
do
    [ -x "$cand" ] && { PY="$cand"; break; }
done

if [ -z "$PY" ]; then
    echo "❌ 找不到 python3"
    exit 1
fi

# 检查必填
if [ -z "$PCC_API_KEY" ]; then
    echo "❌ 缺少 PCC_API_KEY"
    echo "   请复制 .env.example 为 .env 并填写。"
    exit 1
fi

GALLERY="${PCC_GALLERY}"
if [ -z "$GALLERY" ]; then
    echo "❌ 缺少 PCC_GALLERY"
    echo "   请复制 .env.example 为 .env 并填写图库路径。"
    exit 1
fi
if [ ! -d "$GALLERY" ]; then
    echo "❌ 图库不存在: $GALLERY"
    exit 1
fi

PORT="${PCC_PORT:-8125}"

echo "════════════════════════════════════════════"
echo "  Pose × Costume × Character"
echo "════════════════════════════════════════════"
echo ""

# 端口已占用则直接开浏览器
if lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
    echo "ℹ️  服务已在运行"
    open "http://127.0.0.1:$PORT" 2>/dev/null || true
    echo "   http://127.0.0.1:$PORT"
    exit 0
fi

echo "启动服务…"
"$PY" scripts/server3in1.py &
SPID=$!

for _ in $(seq 1 20); do
    lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1 && break
    sleep 0.5
done

if ! lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
    echo "❌ 启动失败"
    kill $SPID 2>/dev/null
    exit 1
fi

echo ""
echo "✅ 已就绪  http://127.0.0.1:$PORT"
echo ""
open "http://127.0.0.1:$PORT" 2>/dev/null || true

trap "kill $SPID 2>/dev/null; exit 0" INT TERM
wait $SPID
