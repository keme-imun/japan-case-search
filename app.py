"""일본 판례 검색·요약 앱 (Streamlit).

한국어 검색어 → 일본어 키워드 변환(Gemini) → courts.go.jp 검색
→ 판례 선택 → PDF 다운로드 → 한국어 요약(Gemini, 무료 티어).
"""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src import courts_client, summarizer, translator

load_dotenv()

# Streamlit Cloud에서는 st.secrets로 키가 주입된다 → 환경변수로 복사
for _k in ("GEMINI_API_KEY", "GEMINI_MODEL", "APP_PASSWORD"):
    try:
        if _k not in os.environ and _k in st.secrets:
            os.environ[_k] = st.secrets[_k]
    except Exception:
        pass  # 로컬에 secrets.toml이 없으면 st.secrets 접근이 실패할 수 있음

st.set_page_config(page_title="일본 판례 검색", page_icon="⚖️", layout="wide")
st.title("⚖️ 일본 판례 검색 · 한국어 요약")
st.caption("일본 재판소 裁判例検索(courts.go.jp)에서 판례를 찾아 원문 PDF를 내려받고 한국어로 요약합니다.")

# ── 비밀번호 잠금 (선택): APP_PASSWORD가 설정된 경우에만 인증 요구 ──────────
_app_password = os.environ.get("APP_PASSWORD")
if _app_password:
    if not st.session_state.get("authed"):
        pw = st.text_input("접속 비밀번호", type="password")
        if st.button("확인"):
            if pw == _app_password:
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        st.stop()

if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    st.error(
        "GEMINI_API_KEY가 설정되어 있지 않습니다.\n\n"
        "1. https://aistudio.google.com/apikey 에서 **무료** API 키를 발급받으세요 (카드 등록 불필요)\n"
        "2. 프로젝트 폴더의 `.env` 파일에 `GEMINI_API_KEY=AIza...` 를 입력하세요"
    )
    st.stop()


def _friendly_llm_error(e: Exception) -> str:
    msg = str(e)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return "무료 티어 사용량 한도에 도달했습니다. 1분 정도 기다렸다가 다시 시도해 주세요. (분당/일일 무료 한도)"
    if "503" in msg or "UNAVAILABLE" in msg:
        return "Gemini 서버가 혼잡합니다. 예비 모델까지 모두 혼잡한 상태이니 몇 분 뒤 다시 시도해 주세요."
    return msg

ss = st.session_state
ss.setdefault("translation", None)   # TranslationResult
ss.setdefault("search_result", None) # SearchResult
ss.setdefault("offset", 0)

# ── ① 한국어 검색어 입력 → 일본어 키워드 변환 ──────────────────────────────
with st.form("query-form"):
    korean_query = st.text_input(
        "한국어 검색어", placeholder="예: 부당해고 손해배상, 저작권 침해, 임대차 보증금 반환"
    )
    submitted = st.form_submit_button("일본어 키워드로 변환", type="primary")

if submitted and korean_query.strip():
    with st.spinner("일본어 법률 키워드로 변환 중... (Gemini)"):
        try:
            ss.translation = translator.translate_query(korean_query.strip())
            ss.search_result = None
            ss.offset = 0
        except Exception as e:
            st.error(f"키워드 변환 실패: {_friendly_llm_error(e)}")

# ── ② 키워드 확인/수정 → 검색 ──────────────────────────────────────────────
if ss.translation:
    st.info(f"💡 {ss.translation.explanation}")
    edited = st.text_input(
        "일본어 검색 키워드 (스페이스 구분, 수정 가능 — 첫 단어가 핵심어, 이후는 AND 절요어)",
        value=" ".join(ss.translation.keywords),
        key="keywords-input",
    )
    if st.button("🔍 courts.go.jp 판례 검색"):
        keywords = edited.split()
        if keywords:
            with st.spinner("일본 재판소 사이트에서 검색 중..."):
                try:
                    ss.search_result = courts_client.search(keywords, offset=0)
                    ss.offset = 0
                except Exception as e:
                    st.error(f"검색 실패: {e}")

# ── ③ 검색 결과 목록 → 판례 선택 ──────────────────────────────────────────
result = ss.search_result
if result is not None:
    if result.total == 0 or not result.cases:
        st.warning("검색 결과가 없습니다. 키워드를 줄이거나 다른 용어로 시도해 보세요.")
    else:
        st.subheader(f"검색 결과 {result.total}건 (표시: {result.offset + 1}~{result.offset + len(result.cases)}건)")

        col_prev, col_next, _ = st.columns([1, 1, 6])
        keywords = ss.get("keywords-input", "").split()
        if col_prev.button("← 이전 30건", disabled=result.offset <= 0):
            ss.offset = max(0, result.offset - 30)
            ss.search_result = courts_client.search(keywords, offset=ss.offset)
            st.rerun()
        if col_next.button("다음 30건 →", disabled=result.offset + 30 >= result.total):
            ss.offset = result.offset + 30
            ss.search_result = courts_client.search(keywords, offset=ss.offset)
            st.rerun()

        for case in result.cases:
            pdf_badge = "📄 전문 PDF" if case.pdf_url else "PDF 미공개"
            with st.expander(
                f"**{case.judge_date}** · {case.court} · {case.case_number} {case.case_name} — {pdf_badge}"
            ):
                st.markdown(
                    f"- 구분: {case.category}\n"
                    f"- 사건번호: {case.case_number}\n"
                    f"- 상세 페이지: [{case.detail_url}]({case.detail_url})"
                )
                if not case.pdf_url:
                    st.warning("이 판례는 전문 PDF가 공개되어 있지 않아 요약할 수 없습니다.")
                    continue

                if st.button("📥 PDF 다운로드 & 한국어 요약", key=f"sum-{case.case_id}"):
                    ss[f"do-summarize-{case.case_id}"] = True

                if ss.get(f"do-summarize-{case.case_id}"):
                    try:
                        with st.spinner("PDF 다운로드 중..."):
                            pdf_path = courts_client.download_pdf(case)
                    except Exception as e:
                        st.error(f"PDF 다운로드 실패: {e}")
                        continue

                    st.download_button(
                        "💾 원문 PDF 저장",
                        data=pdf_path.read_bytes(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        key=f"dl-{case.case_id}",
                    )

                    case_label = f"{case.court} {case.judge_date} {case.case_number} {case.case_name}"
                    cached = summarizer.get_cached_summary(pdf_path)
                    st.markdown("### 📝 한국어 요약")
                    if cached:
                        st.markdown(cached)
                        st.caption("(캐시된 요약)")
                    else:
                        try:
                            with st.spinner("Gemini가 판결문을 읽고 요약 중... (1~2분 걸릴 수 있음)"):
                                st.write_stream(summarizer.summarize_pdf(pdf_path, case_label))
                        except Exception as e:
                            st.error(f"요약 실패: {_friendly_llm_error(e)}")
