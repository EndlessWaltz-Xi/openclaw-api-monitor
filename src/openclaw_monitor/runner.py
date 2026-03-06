"""
主循环：定期检测 OpenClaw API；一旦发现失败则进入「恢复监测」直到成功。
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from .checker import CheckResult, run_check
from .config import load_config

logger = logging.getLogger(__name__)


def setup_logging(log_level: str, log_output: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    if log_output == "stdout" or not log_output:
        handler: logging.Handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(log_output, encoding="utf-8")
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)


def run_command(cmd: str | None) -> None:
    if not cmd or not cmd.strip():
        return
    try:
        subprocess.run(
            cmd,
            shell=True,
            timeout=60,
            env=os.environ.copy(),
        )
    except Exception as e:
        logger.warning("Command failed: %s", e)


def run_once(config_path: str | None) -> bool:
    """执行一次检查并返回是否成功。用于验证可行性或配合 cron。"""
    cfg = load_config(config_path)
    setup_logging(cfg["log_level"], cfg["log_output"])
    result = run_check(
        base_url=cfg["base_url"],
        check_mode=cfg["check_mode"],
        timeout=int(cfg["timeout"]),
        failure_status_codes=list(cfg["failure_status_codes"]),
        failure_keywords=list(cfg["failure_keywords"]),
        chat_endpoint=cfg.get("chat_endpoint") or "/v1/chat/completions",
        chat_model=cfg.get("chat_model") or "openclaw:main",
        auth_token=cfg.get("auth_token"),
    )
    if result.ok:
        logger.info("Check OK: %s", result.reason)
        return True
    logger.warning("Check failed: %s", result.reason)
    if result.body_preview:
        logger.debug("Body: %s", result.body_preview[:300])
    return False


def main_loop() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw API Monitor")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check and exit (exit 0=OK, 1=failure). Use to verify setup.",
    )
    args = parser.parse_args()

    config_path = os.environ.get("OPENCLAW_MONITOR_CONFIG")
    if config_path and not Path(config_path).is_file():
        logger.warning("Config file not found: %s, using defaults", config_path)
    if args.once:
        ok = run_once(config_path)
        sys.exit(0 if ok else 1)

    cfg = load_config(config_path)

    setup_logging(cfg["log_level"], cfg["log_output"])

    base_url = cfg["base_url"]
    check_interval = int(cfg["check_interval"])
    recovery_interval = int(cfg["recovery_interval"])
    timeout = int(cfg["timeout"])
    failure_status_codes = list(cfg["failure_status_codes"])
    failure_keywords = list(cfg["failure_keywords"])
    check_mode = cfg["check_mode"]
    chat_endpoint = cfg.get("chat_endpoint") or "/v1/chat/completions"
    chat_model = cfg.get("chat_model") or "openclaw:main"
    auth_token = cfg.get("auth_token")
    on_failure_command = cfg.get("on_failure_command")
    on_recovery_command = cfg.get("on_recovery_command")

    in_recovery = False
    failure_reported = False

    logger.info(
        "OpenClaw API monitor started (base_url=%s, check_mode=%s, check_interval=%ss)",
        base_url,
        check_mode,
        check_interval,
    )

    while True:
        result = run_check(
            base_url=base_url,
            check_mode=check_mode,
            timeout=timeout,
            failure_status_codes=failure_status_codes,
            failure_keywords=failure_keywords,
            chat_endpoint=chat_endpoint,
            chat_model=chat_model,
            auth_token=auth_token,
        )

        if result.ok:
            if in_recovery:
                logger.info("API recovered: %s", result.reason)
                run_command(on_recovery_command)
                failure_reported = False
            in_recovery = False
            interval = check_interval
        else:
            if not in_recovery:
                logger.warning(
                    "API check failed (entering recovery watch): %s",
                    result.reason,
                    extra={"body_preview": result.body_preview},
                )
                if result.body_preview:
                    logger.debug("Response preview: %s", result.body_preview[:300])
                if not failure_reported:
                    run_command(on_failure_command)
                    failure_reported = True
            else:
                logger.debug("API still failing: %s", result.reason)
            in_recovery = True
            interval = recovery_interval

        time.sleep(interval)
