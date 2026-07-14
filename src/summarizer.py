"""판례 PDF → 한국어 요약 (Gemini 무료 티어, 스트리밍)."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from pathlib import Path

from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-flash-latest"
CACHE_DIR = Path("cache")


def _model() -> str:
    return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)


_SYSTEM = """\
당신은 일본 판례를 한국 법률가에게 설명하는 한일 비교법 전문가입니다.
첨부된 일본 판결문 PDF를 읽고 아래 구조의 한국어 요약을 작성하세요.
법률 용어는 한국어 번역 뒤에 일본어 원어를 괄호로 병기하세요. 예: 해고권 남용(解雇権濫用)

## 사건 개요
당사자, 사실관계를 3~5문장으로.

## 쟁점
번호를 붙여 나열.

## 법원의 판단
쟁점별 판단 논리. 핵심 판시 부분은 원문을 인용하고 한국어 번역 병기.

## 결론 (주문)
청구 인용/기각 여부와 주문 내용.

## 한국법과의 시사점
유사한 한국 법제·판례 경향과 비교해 1~2단락.
"""


def _cache_path(pdf_path: Path) -> Path:
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]
    return CACHE_DIR / f"summary-{pdf_path.stem}-{_model()}-{digest}.json"


def get_cached_summary(pdf_path: Path) -> str | None:
    p = _cache_path(pdf_path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))["summary"]
    return None


def summarize_pdf(
    pdf_path: Path,
    case_label: str = "",
    client: genai.Client | None = None,
) -> Iterator[str]:
    """PDF를 요약하며 텍스트 조각을 스트리밍으로 yield. 완료 시 캐시에 저장."""
    client = client or genai.Client()  # GEMINI_API_KEY 환경변수 사용

    contents = [
        types.Part.from_bytes(data=pdf_path.read_bytes(), mime_type="application/pdf"),
        f"다음 일본 판례를 요약해 주세요. {case_label}".strip(),
    ]

    chunks: list[str] = []
    stream = client.models.generate_content_stream(
        model=_model(),
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=_SYSTEM),
    )
    for chunk in stream:
        if chunk.text:
            chunks.append(chunk.text)
            yield chunk.text

    summary = "".join(chunks)
    if summary.strip():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(pdf_path).write_text(
            json.dumps({"case": case_label, "model": _model(), "summary": summary},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
