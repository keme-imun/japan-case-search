"""한국어 검색어 → 일본 판례 검색용 일본어 키워드 변환 (Gemini 무료 티어)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from google import genai
from google.genai import types

from .gemini_util import call_with_fallback


_SYSTEM = """\
당신은 한국 법률가가 일본 판례를 검색하도록 돕는 한일 법률용어 전문가입니다.
사용자가 입력한 한국어 검색어를 일본 재판소 판례검색 시스템(裁判例検索)에서
실제로 잘 검색되는 일본어 법률 용어로 변환하세요.

규칙:
- 단순 직역이 아니라 일본 판결문에서 실제 쓰이는 법률 용어를 선택 (예: 부당해고 → 解雇権濫用 또는 不当解雇)
- keywords는 중요도 순으로 1~3개. 첫 키워드가 핵심 쟁점, 나머지는 검색 범위를 좁히는 보조어
- 각 키워드는 짧은 단일 용어(복합어 가능)로, 문장이 아니어야 함
"""

_SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "일본어 검색 키워드, 중요도 순 1~3개",
        },
        "explanation": {
            "type": "string",
            "description": "선택한 일본어 용어에 대한 한국어 설명 (1~2문장)",
        },
    },
    "required": ["keywords", "explanation"],
}


@dataclass
class TranslationResult:
    keywords: list[str]
    explanation: str


def translate_query(korean_query: str, client: genai.Client | None = None) -> TranslationResult:
    client = client or genai.Client()  # GEMINI_API_KEY 환경변수 사용
    _, response = call_with_fallback(
        lambda model: client.models.generate_content(
            model=model,
            contents=korean_query,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM,
                response_mime_type="application/json",
                response_schema=_SCHEMA,
            ),
        )
    )
    data = json.loads(response.text)
    keywords = [k.strip() for k in data["keywords"] if k.strip()][:3]
    if not keywords:
        raise ValueError("일본어 키워드 변환에 실패했습니다")
    return TranslationResult(keywords=keywords, explanation=data.get("explanation", ""))
