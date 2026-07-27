"""판례 PDF에서 텍스트 레이어를 로컬 추출한다.

토큰 관점에서 텍스트 추출이 항상 이득은 아니다. Gemini는 PDF를 **페이지당 258토큰
정액**으로 계산하므로, 글자가 빽빽한 판결문은 PDF를 그대로 올리는 편이 싸다.
(실측: 44페이지 판결문 → PDF 11,353토큰 vs 추출 텍스트 26,055토큰)

반대로 글자가 성긴 PDF(표지·여백 많은 문서)는 텍스트가 싸다. 그래서 summarizer는
두 방식의 예상 토큰을 비교해 싼 쪽을 고른다. 텍스트 경로는 페이지 정액제가 없는
다른 공급자(Claude·OpenAI)나 PDF 입력을 못 받는 공급자(Groq·Cerebras)로
갈아탈 때도 그대로 쓰인다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

# 페이지당 이 글자 수에 못 미치면 텍스트 레이어가 없는 스캔본으로 판단한다.
# 일본 판결문은 한 면에 보통 600자 이상 들어간다.
MIN_CHARS_PER_PAGE = 150

# 모델에 보낼 최대 글자 수. 초과분은 잘라내고 안내 문구를 붙인다.
MAX_CHARS = 120_000

# Gemini의 PDF 과금 단위: 페이지당 258토큰 정액.
TOKENS_PER_PDF_PAGE = 258

# 일본어 판결문 실측 기준 글자→토큰 비율 (38,820자 → 26,055토큰).
CHARS_PER_TOKEN = 1.49


@dataclass
class ExtractedText:
    text: str
    pages: int
    truncated: bool

    @property
    def ok(self) -> bool:
        """텍스트 레이어를 제대로 뽑았는가 (스캔 이미지 PDF면 False)."""
        return bool(self.text) and self.pages > 0 and (
            len(self.text) / self.pages >= MIN_CHARS_PER_PAGE
        )

    @property
    def est_tokens(self) -> int:
        """이 텍스트를 그대로 보냈을 때의 예상 토큰 수."""
        return int(len(self.text) / CHARS_PER_TOKEN)

    @property
    def cheaper_than_pdf(self) -> bool:
        """PDF 원본 업로드(페이지당 258토큰)보다 텍스트가 싼가."""
        return self.ok and self.est_tokens < self.pages * TOKENS_PER_PDF_PAGE


def _clean(raw: str) -> str:
    # 세로쓰기·2단 조판 탓에 생기는 낱글자 줄바꿈과 과도한 공백을 정리한다.
    raw = raw.replace("　", " ")
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


def extract(pdf_path: Path) -> ExtractedText:
    """PDF에서 텍스트를 추출한다. 실패해도 예외를 던지지 않고 ok=False로 돌려준다."""
    try:
        reader = PdfReader(str(pdf_path))
        pages = [(p.extract_text() or "") for p in reader.pages]
    except Exception:
        return ExtractedText(text="", pages=0, truncated=False)

    text = _clean("\n\n".join(pages))
    truncated = len(text) > MAX_CHARS
    if truncated:
        text = text[:MAX_CHARS] + "\n\n(…이하 생략: 판결문이 길어 앞부분만 발췌했습니다)"

    return ExtractedText(text=text, pages=len(pages), truncated=truncated)
