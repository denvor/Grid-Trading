#!/usr/bin/env bash
# 启动网格交易测算工具
# 用法: ./start.sh [--port 5000] [--debug]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 解析参数
PORT=5000
DEBUG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port) PORT="$2"; shift 2 ;;
        --debug) DEBUG="--debug"; shift ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "错误：未找到 venv/，请先运行: python3 -m venv venv && pip install -r requirements.txt"
    exit 1
fi

# 启动 Flask（监听 0.0.0.0，便于局域网访问）
echo "启动网格交易测算工具 → http://0.0.0.0:${PORT}"
exec flask --app app run --host=0.0.0.0 --port="$PORT" $DEBUG
