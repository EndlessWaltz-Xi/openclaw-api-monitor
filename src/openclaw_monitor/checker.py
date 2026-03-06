"""
对 OpenClaw 网关进行健康检查，并判断是否为「大模型 API 调用失败」。
失败原因包括：API 限流、tokens 限制、配额、上游 5xx 等。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    ok: bool
    status_code: int | None
    reason: str
    body_preview: str = ""


def _normalize_text(s: str) -> str:
    return s.lower().strip()


def _body_contains_failure(body: str, keywords: list[str]) -> tuple[bool, str]:
    if not body or not keywords:
        return False, ""
    normalized = _normalize_text(body)
    for kw in keywords:
        if _normalize_text(kw) in normalized:
            return True, kw
    return False, ""


def check_ping(base_url: str, timeout: int, **kwargs: Any) -> CheckResult:
    """仅请求根路径，不触发大模型调用。"""
    url = base_url.rstrip("/") + "/"
    try:
        r = requests.get(url, timeout=timeout, **kwargs)
        if r.status_code >= 400:
            return CheckResult(
                ok=False,
                status_code=r.status_code,
                reason=f"HTTP {r.status_code}",
                body_preview=(r.text or "")[:500],
            )
        return CheckResult(ok=True, status_code=r.status_code, reason="ok")
    except requests.RequestException as e:
        return CheckResult(
            ok=False,
            status_code=None,
            reason=str(e),
            body_preview="",
        )


def check_chat(
    base_url: str,
    endpoint: str,
    model: str,
    timeout: int,
    failure_status_codes: list[int],
    failure_keywords: list[str],
    auth_token: str | None = None,
    **kwargs: Any,
) -> CheckResult:
    """发送最小 chat completions 请求，根据状态码与响应体判断是否为大模型 API 失败。"""
    url = base_url.rstrip("/") + endpoint
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=timeout, **kwargs)
        response_text = (r.text or "")[:2000]

        if r.status_code in failure_status_codes:
            hit, kw = _body_contains_failure(response_text, failure_keywords)
            detail = f" (keyword: {kw})" if hit else ""
            return CheckResult(
                ok=False,
                status_code=r.status_code,
                reason=f"HTTP {r.status_code}{detail}",
                body_preview=response_text[:500],
            )

        if r.status_code >= 400:
            hit, kw = _body_contains_failure(response_text, failure_keywords)
            detail = f", keyword: {kw}" if hit else ""
            return CheckResult(
                ok=False,
                status_code=r.status_code,
                reason=f"HTTP {r.status_code}{detail}",
                body_preview=response_text[:500],
            )

        # 2xx 但 body 里可能有错误信息（如流式或包装错误）
        hit, kw = _body_contains_failure(response_text, failure_keywords)
        if hit:
            return CheckResult(
                ok=False,
                status_code=r.status_code,
                reason=f"Success status but failure keyword in body: {kw}",
                body_preview=response_text[:500],
            )

        return CheckResult(ok=True, status_code=r.status_code, reason="ok")
    except requests.RequestException as e:
        return CheckResult(
            ok=False,
            status_code=None,
            reason=str(e),
            body_preview="",
        )


def run_check(
    base_url: str,
    check_mode: str,
    timeout: int,
    failure_status_codes: list[int],
    failure_keywords: list[str],
    chat_endpoint: str = "/v1/chat/completions",
    chat_model: str = "openclaw:main",
    auth_token: str | None = None,
) -> CheckResult:
    if check_mode == "ping":
        return check_ping(base_url, timeout=timeout)
    if check_mode == "chat":
        return check_chat(
            base_url=base_url,
            endpoint=chat_endpoint,
            model=chat_model,
            timeout=timeout,
            failure_status_codes=failure_status_codes,
            failure_keywords=failure_keywords,
            auth_token=auth_token,
        )
    return CheckResult(
        ok=False,
        status_code=None,
        reason=f"Unknown check_mode: {check_mode}",
    )
