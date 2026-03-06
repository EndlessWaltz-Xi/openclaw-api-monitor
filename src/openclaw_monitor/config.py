"""加载 YAML 配置，提供默认值与校验。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

DEFAULT_CONFIG = {
    "base_url": "http://127.0.0.1:18789",
    "auth_token": None,
    "check_mode": "chat",
    "chat_endpoint": "/v1/chat/completions",
    "chat_model": "openclaw:main",
    "check_interval": 60,
    "recovery_interval": 30,
    "timeout": 30,
    "failure_status_codes": [429, 500, 502, 503, 504],
    "failure_keywords": [
        "rate limit", "rate_limit", "quota", "token", "limit exceeded",
        "too many requests", "insufficient_quota", "context_length", "max_tokens",
        "overloaded", "capacity", "服务繁忙", "请求过于频繁", "配额", "限流",
    ],
    "on_failure_command": None,
    "on_recovery_command": None,
    "log_level": "INFO",
    "log_output": "stdout",
}


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        path = os.environ.get("OPENCLAW_MONITOR_CONFIG", "config.yaml")
    path = Path(path)
    if not path.is_file():
        return dict(DEFAULT_CONFIG)

    if yaml is None:
        raise RuntimeError("PyYAML is required. Install with: pip install PyYAML")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    out = dict(DEFAULT_CONFIG)
    for key, value in data.items():
        if key in out and value is not None:
            out[key] = value
    return out
