"""courts.go.jp 재판례 검색 사이트 클라이언트.

검색 결과는 서버가 같은 URL(index.html)에 렌더링해서 돌려준다:
  GET https://www.courts.go.jp/hanrei/search1/index.html?query1=<OR 키워드>&query2=<AND 키워드>&offset=N
- query1: 스페이스 구분 = OR 검색
- query2, query3: 절요(AND) 키워드
- offset: 페이지네이션 (30건 단위), sort: 1=판결일 내림차순
결과 행: table.search-result-table > tr
  th  > a[href=./../{id}/detail{N}/index.html]  (재판례 구분)
  td  > p(사건번호+사건명), p(판결일+법원명)
  td.file-col > a[href=./../../assets/hanrei/hanrei-pdf-{id}.pdf]
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://www.courts.go.jp"
ALLOWED_HOST = "www.courts.go.jp"
SEARCH_URL = f"{BASE}/hanrei/search1/index.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JapanCaseSearch/0.1 (personal research tool)",
    "Accept-Language": "ja,en;q=0.8",
}
REQUEST_DELAY_SEC = 1.0  # 사이트 부하 방지

_last_request_at = 0.0


def _check_url(url: str) -> None:
    """courts.go.jp의 https 주소인지 확인한다.

    링크는 원격 HTML에서 뽑아 오므로, 사이트가 변조되거나 중간에서 조작되면
    임의의 주소를 가리킬 수 있다. 그대로 요청하면 서버가 내부망 주소를 대신
    긁어 주는 통로가 되므로(SSRF), 목적지를 재판소 사이트로 못박는다.
    """
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != ALLOWED_HOST:
        raise ValueError(f"허용되지 않은 주소로의 요청을 차단했습니다: {url}")


def _polite_get(url: str, **kwargs) -> requests.Response:
    global _last_request_at
    _check_url(url)
    wait = REQUEST_DELAY_SEC - (time.time() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    resp = requests.get(url, headers=HEADERS, timeout=30, **kwargs)
    _last_request_at = time.time()
    _check_url(resp.url)  # 리다이렉트로 외부 호스트에 끌려가지 않았는지 확인
    resp.raise_for_status()
    return resp


@dataclass
class CaseResult:
    case_id: str            # 예: "94051"
    category: str           # 예: "下級裁裁判例", "最高裁判例"
    case_number: str        # 예: "令和4(ワ)410"
    case_name: str          # 예: "損害賠償等請求事件"
    judge_date: str         # 예: "令和7年3月25日"
    court: str              # 예: "横浜地方裁判所"
    detail_url: str
    pdf_url: str | None     # 전문 미공개 판례는 None


@dataclass
class SearchResult:
    total: int
    offset: int
    cases: list[CaseResult] = field(default_factory=list)


def search(keywords: list[str], offset: int = 0, sort: int = 1) -> SearchResult:
    """일본어 키워드로 판례를 검색한다.

    keywords[0] → query1 (필수), keywords[1:] → query2, query3 (AND 절요, 최대 2개).
    """
    if not keywords:
        raise ValueError("검색 키워드가 비어 있습니다")
    params: dict[str, str | int] = {"query1": keywords[0], "sort": sort, "offset": offset}
    for i, kw in enumerate(keywords[1:3], start=2):
        params[f"query{i}"] = kw

    resp = _polite_get(SEARCH_URL, params=params)
    return _parse_results(resp.text, offset)


def _parse_results(html: str, offset: int) -> SearchResult:
    soup = BeautifulSoup(html, "html.parser")

    total = 0
    m = re.search(r"(\d+)件中\s*\d+～\d+件を表示", html)
    if m:
        total = int(m.group(1))
    elif re.search(r"全文検索件数:\s*(\d+)", html):
        total = int(re.search(r"全文検索件数:\s*(\d+)", html).group(1))

    result = SearchResult(total=total, offset=offset)
    table = soup.select_one("table.search-result-table")
    if table is None:
        return result

    for tr in table.select("tr"):
        th_link = tr.select_one("th a[href]")
        tds = tr.select("td")
        if th_link is None or not tds:
            continue

        detail_href = th_link["href"]
        id_match = re.search(r"/(\d+)/detail\d+/", detail_href)
        case_id = id_match.group(1) if id_match else ""
        detail_url = requests.compat.urljoin(SEARCH_URL, detail_href)

        paragraphs = [
            re.sub(r"\s+", " ", p.get_text(" ", strip=True)).strip()
            for p in tds[0].select("p")
        ]
        paragraphs = [p for p in paragraphs if p]

        case_number, case_name, judge_date, court = "", "", "", ""
        if paragraphs:
            # 첫 p: "令和4(ワ)410 損害賠償等請求事件"
            parts = paragraphs[0].split(None, 1)
            case_number = parts[0]
            case_name = parts[1] if len(parts) > 1 else ""
        if len(paragraphs) > 1:
            # 둘째 p: "令和7年3月25日 横浜地方裁判所 ..."
            parts = paragraphs[1].split(None, 1)
            judge_date = parts[0]
            court = parts[1] if len(parts) > 1 else ""

        pdf_url = None
        pdf_link = tr.select_one("td.file-col a[href*='.pdf']")
        if pdf_link:
            pdf_url = requests.compat.urljoin(SEARCH_URL, pdf_link["href"])

        result.cases.append(
            CaseResult(
                case_id=case_id,
                category=th_link.get_text(strip=True),
                case_number=case_number,
                case_name=case_name,
                judge_date=judge_date,
                court=court,
                detail_url=detail_url,
                pdf_url=pdf_url,
            )
        )
    return result


def download_pdf(case: CaseResult, dest_dir: str | Path = "downloads") -> Path:
    """판례 전문 PDF를 다운로드하고 저장 경로를 반환한다."""
    if not case.pdf_url:
        raise ValueError(f"이 판례({case.case_number})는 전문 PDF가 공개되어 있지 않습니다")
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    # case_id는 원격 HTML에서 정규식으로 뽑으므로 파싱 실패 시 빈 문자열이 된다.
    # 그대로 쓰면 서로 다른 판례가 모두 "hanrei-.pdf"가 되어, 아래 캐시 분기에서
    # 남의 판결문을 이 사건의 것으로 반환하게 된다. 숫자 id일 때만 신뢰한다.
    if re.fullmatch(r"\d+", case.case_id or ""):
        stem = f"hanrei-{case.case_id}"
    else:
        stem = "hanrei-" + hashlib.sha256(case.pdf_url.encode()).hexdigest()[:16]
    path = dest / f"{stem}.pdf"
    if path.exists() and path.stat().st_size > 0:
        return path
    resp = _polite_get(case.pdf_url)
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("PDF가 아닌 응답을 받았습니다 (사이트 구조 변경 가능성)")
    path.write_bytes(resp.content)
    return path
