"""판례 PDF → 한국어 요약 (Gemini 무료 티어, 스트리밍)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

from google import genai
from google.genai import types

from . import pdf_text
from .gemini_util import call_with_fallback, make_client

CACHE_DIR = Path("cache")


_SYSTEM = """\
당신은 일본 판례를 한국 법률가에게 설명하는 한일 비교법 전문가입니다.
주어진 일본 판결문을 읽고 아래 구조의 한국어 요약을 작성하세요.
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


def _digest(pdf_path: Path) -> str:
    return hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]


def get_cached_summary(pdf_path: Path) -> str | None:
    # 어떤 모델로 만든 요약이든 같은 PDF면 재사용 (폴백으로 모델이 바뀔 수 있으므로 glob)
    for p in CACHE_DIR.glob(f"summary-{pdf_path.stem}-*-{_digest(pdf_path)}.json"):
        return json.loads(p.read_text(encoding="utf-8"))["summary"]
    return None


def summarize_pdf(
    pdf_path: Path,
    case_label: str = "",
    client: genai.Client | None = None,
    api_key: str | None = None,
) -> Iterator[str]:
    """PDF를 요약하며 텍스트 조각을 스트리밍으로 yield. 완료 시 캐시에 저장.

    입력 방식은 토큰이 적게 드는 쪽으로 자동 선택한다. Gemini는 PDF를 페이지당
    258토큰 정액으로 계산하므로 글자가 빽빽한 판결문은 PDF가 싸고, 성긴 문서는
    로컬 추출 텍스트가 싸다. 스캔 이미지 PDF는 추출이 안 되므로 항상 PDF를 쓴다.
    """
    client = client or make_client(api_key)

    extracted = pdf_text.extract(pdf_path)
    if extracted.cheaper_than_pdf:
        mode = "text"
        contents = [
            f"다음 일본 판례를 요약해 주세요. {case_label}".strip(),
            "\n\n--- 판결문 원문 ---\n" + extracted.text,
        ]
    else:
        # 글자가 빽빽하거나(정액제가 유리) 스캔본이라 추출 실패 → PDF 원본 업로드
        mode = "pdf"
        contents = [
            types.Part.from_bytes(data=pdf_path.read_bytes(), mime_type="application/pdf"),
            f"다음 일본 판례를 요약해 주세요. {case_label}".strip(),
        ]

    def _start(model: str):
        # 스트림을 열고 첫 청크까지 받아본다 — 503은 대부분 이 시점에 발생하므로
        # 여기서 실패하면 call_with_fallback이 다음 모델로 넘어간다.
        stream = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=_SYSTEM),
        )
        it = iter(stream)
        first = next(it, None)
        return first, it

    used_model, (first, it) = call_with_fallback(_start)

    chunks: list[str] = []

    def _emit(chunk):
        if chunk is not None and chunk.text:
            chunks.append(chunk.text)
            return chunk.text
        return None

    if (t := _emit(first)) is not None:
        yield t
    for chunk in it:
        if (t := _emit(chunk)) is not None:
            yield t

    summary = "".join(chunks)
    if summary.strip():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        out = CACHE_DIR / f"summary-{pdf_path.stem}-{used_model}-{mode}-{_digest(pdf_path)}.json"
        out.write_text(
            json.dumps({"case": case_label, "model": used_model, "mode": mode, "summary": summary},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
