"""Gemini 모델 폴백 유틸.

최신 모델(gemini-flash-latest)은 수요가 몰리면 503 UNAVAILABLE을 반환할 수 있다.
그럴 때 자동으로 덜 혼잡한 예전 모델로 순서대로 재시도한다.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_FALLBACKS = ["gemini-3.1-flash-lite", "gemini-2.0-flash"]


def model_chain() -> list[str]:
    """시도할 모델 목록 (환경변수 GEMINI_MODEL이 있으면 그것을 최우선)."""
    primary = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
    chain = [primary] + [m for m in _FALLBACKS if m != primary]
    return chain


def _is_retryable(e: Exception) -> bool:
    msg = str(e)
    return "503" in msg or "UNAVAILABLE" in msg or "overloaded" in msg.lower()


def call_with_fallback(fn: Callable[[str], T]) -> tuple[str, T]:
    """fn(model_name)을 모델 체인 순서로 시도. (사용된 모델, 결과)를 반환.

    503/UNAVAILABLE(서버 혼잡)일 때만 다음 모델로 넘어간다.
    같은 모델을 1회 재시도(2초 대기) 후 다음 모델로 이동.
    """
    last: Exception | None = None
    for model in model_chain():
        for attempt in range(2):
            try:
                return model, fn(model)
            except Exception as e:
                if not _is_retryable(e):
                    raise
                last = e
                if attempt == 0:
                    time.sleep(2)
    raise RuntimeError(
        "모든 Gemini 모델이 혼잡 상태입니다(503). 몇 분 뒤 다시 시도해 주세요."
    ) from last
