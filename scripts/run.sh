#!/usr/bin/env bash
# 在项目根目录运行监控（优先使用当前目录 config.yaml）
set -e
cd "$(dirname "$0")/.."
export OPENCLAW_MONITOR_CONFIG="${OPENCLAW_MONITOR_CONFIG:-$(pwd)/config.yaml}"
if command -v openclaw-monitor &>/dev/null; then
  exec openclaw-monitor
fi
exec python3 -m openclaw_monitor
