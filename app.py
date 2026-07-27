"""일본 판례 검색·요약 앱 (Streamlit).

한국어 검색어 → 일본어 키워드 변환(Gemini) → courts.go.jp 검색
→ 판례 선택 → PDF 다운로드 → 한국어 요약(Gemini, 무료 티어).
"""

import hmac
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src import courts_client, summarizer, translator

load_dotenv()

# Streamlit Cloud에서는 st.secrets로 키가 주입된다 → 환경변수로 복사
for _k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL", "APP_PASSWORD",
           "ALLOW_SERVER_API_KEY"):
    try:
        if _k not in os.environ and _k in st.secrets:
            os.environ[_k] = st.secrets[_k]
    except Exception:
        pass  # 로컬에 secrets.toml이 없으면 st.secrets 접근이 실패할 수 있음

DEVELOPER = "경희대학교 법학전문대학원 17기 전상훈 개발"

_ICON = Path(__file__).parent / "assets" / "icon.png"
_ICON_ICO = Path(__file__).parent / "assets" / "icon.ico"
st.set_page_config(
    page_title="일본 판례 검색",
    page_icon=str(_ICON) if _ICON.exists() else "⚖️",
    layout="wide",
    menu_items={
        "About": f"**일본 판례 검색 · 한국어 요약**\n\n{DEVELOPER}\n\n"
                 "일본 재판소 裁判例検索(courts.go.jp)의 판례를 검색해 원문 PDF를 "
                 "내려받고 한국어로 요약합니다. 요약은 참고용이며 법률 자문이 아닙니다."
    },
)
st.title("⚖️ 일본 판례 검색 · 한국어 요약")
st.caption("일본 재판소 裁判例検索(courts.go.jp)에서 판례를 찾아 원문 PDF를 내려받고 한국어로 요약합니다.")
st.caption(f"🏫 {DEVELOPER}")

_GUIDE = """\
##### 1. 사이드바에 API 키 입력
왼쪽 `🔑 Gemini API 키` 칸에 본인 키를 넣습니다. 키가 없으면
[Google AI Studio](https://aistudio.google.com/apikey)에서 **Create API key** 를 누르면
바로 발급됩니다. Google 계정만 있으면 되고 카드 등록은 필요 없습니다.
각자 자기 키를 쓰므로 무료 한도도 각자 따로 적용됩니다.

##### 2. 한국어로 검색어 입력
`부당해고 손해배상` 처럼 평소 쓰는 한국어 법률 용어를 그대로 넣으면 됩니다.
일본 판결문에서 실제로 쓰이는 일본어 용어로 바꿔 줍니다
(부당해고 → 解雇権濫用).

##### 3. 키워드 확인 후 검색
변환된 일본어 키워드는 **직접 고칠 수 있습니다**. 첫 단어가 핵심어이고
뒤에 붙는 단어는 검색 범위를 좁히는 조건입니다. 결과가 너무 적으면 뒤 단어를
지우고, 너무 많으면 단어를 추가해 보세요.

##### 4. 판례 선택 → 요약
목록에서 판례를 펼치고 `📥 PDF 다운로드 & 한국어 요약` 을 누르면
**사건 개요 / 쟁점 / 법원의 판단 / 결론(주문) / 한국법과의 시사점** 순서로
요약이 나옵니다. 원문 PDF도 따로 내려받을 수 있습니다.

---

**알아 두면 좋은 것**

- 요약은 판례당 1~2분 걸립니다. 긴 판결문일수록 오래 걸려요.
- 한 번 요약된 판례는 저장되어, 다음부터는 누가 열어도 즉시 표시됩니다
  (API 한도를 쓰지 않습니다).
- `📄 전문 PDF` 표시가 없는 판례는 재판소가 전문을 공개하지 않아 요약할 수 없습니다.
- 한도 초과(429) 안내가 뜨면 1분쯤 뒤에 다시 시도하세요.
- 요약은 참고용이며 법률 자문이 아닙니다. 인용 전 반드시 원문을 확인하세요.
"""

with st.expander("📖 사용법 (처음이신가요?)", expanded=not st.session_state.get("used_once")):
    st.markdown(_GUIDE)

# ── 바탕화면 설치 안내 ─────────────────────────────────────────────────────
# 브라우저의 설치 프롬프트는 web app manifest가 있어야 뜨는데 Streamlit은 이를
# 제공하지 않는다. 게다가 커스텀 컴포넌트는 iframe 안이라 최상위 페이지의 설치
# 이벤트에 접근할 수 없다. 그래서 버튼 대신 브라우저별 경로를 안내한다.
with st.expander("💻 바탕화면·홈 화면에 설치하기"):
    _t_win, _t_mac, _t_mobile = st.tabs(["Windows", "Mac", "휴대폰"])

    with _t_win:
        st.markdown(
            "**Edge**\n\n"
            "1. 우측 상단 `···` 클릭\n"
            "2. **앱** → **이 사이트를 앱으로 설치**\n"
            "3. 이름을 확인하고 **설치**\n\n"
            "**Chrome**\n\n"
            "1. 우측 상단 `⋮` 클릭\n"
            "2. **캐스트, 저장 및 공유** → **페이지를 앱으로 설치**\n\n"
            "메뉴 이름은 브라우저 버전마다 다릅니다. 위 항목이 안 보이면 메뉴에서 "
            "**앱**·**바로가기**·**도구 더보기** 안쪽을 찾아보세요.\n\n"
            "그래도 없으면 저장소를 받아 아래를 실행하면 같은 결과(주소창 없는 앱 창 + 아이콘)를 "
            "메뉴 없이 만들 수 있습니다.\n\n"
            "```powershell\n"
            "powershell -ExecutionPolicy Bypass -File tools\\create_shortcut.ps1 -Url \"이_앱_주소\"\n"
            "```\n\n"
            "---\n\n"
            "아이콘이 Streamlit 기본 로고로 뜨면, 바탕화면 바로가기 우클릭 → **속성** → "
            "**웹 문서** → **아이콘 변경** 에서 아래 `.ico` 파일을 지정하면 됩니다."
        )
    with _t_mac:
        st.markdown(
            "**Safari** — 메뉴 막대의 **파일** → **Dock에 추가**\n\n"
            "**Chrome** — 우측 상단 `⋮` → **캐스트, 저장 및 공유** → **페이지를 앱으로 설치**\n\n"
            "**Edge** — 우측 상단 `···` → **앱** → **이 사이트를 앱으로 설치**"
        )
    with _t_mobile:
        st.markdown(
            "**아이폰 (Safari)** — 하단 공유 버튼 `⬆️` → **홈 화면에 추가**\n\n"
            "**안드로이드 (Chrome)** — 우측 상단 `⋮` → **홈 화면에 추가**\n\n"
            "홈 화면 아이콘을 누르면 앱처럼 전체 화면으로 열립니다."
        )

    if _ICON_ICO.exists():
        st.download_button(
            "⬇️ 아이콘 파일 내려받기 (.ico)",
            data=_ICON_ICO.read_bytes(),
            file_name="japan-case-search.ico",
            mime="image/vnd.microsoft.icon",
            help="Windows 바로가기의 아이콘을 바꿀 때 사용합니다.",
        )

# ── 비밀번호 잠금 (선택): APP_PASSWORD가 설정된 경우에만 인증 요구 ──────────
_app_password = os.environ.get("APP_PASSWORD")
if _app_password:
    if not st.session_state.get("authed"):
        pw = st.text_input("접속 비밀번호", type="password")
        if st.button("확인"):
            if hmac.compare_digest(pw, _app_password):
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        st.stop()

# ── API 키: 기본은 "접속자가 각자 자기 키를 입력" ──────────────────────────
# 서버에 설정된 키를 쓰려면 ALLOW_SERVER_API_KEY=1 을 명시해야 한다. 기본을 이렇게
# 잡은 이유는, 배포 설정에 키를 남겨 둔 채 플래그를 깜빡하면 접속자 전원이 배포자의
# 무료 한도를 소모하기 때문이다. 안전한 쪽이 기본이어야 한다.
# (혼자 쓰는 로컬에서는 .env 에 ALLOW_SERVER_API_KEY=1 을 넣어 두면 편하다)
_allow_server_key = os.environ.get("ALLOW_SERVER_API_KEY", "").strip().lower() in (
    "1", "true", "yes"
)
if _allow_server_key:
    _server_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
else:
    # 환경변수에 남겨 두면 api_key를 넘기지 않는 코드 경로가 생겼을 때 배포자의 키가
    # 조용히 쓰인다. 아예 지워서 폴백 자체를 없앤다.
    for _k in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        os.environ.pop(_k, None)
    _server_key = None

with st.sidebar:
    st.header("🔑 Gemini API 키")
    _entered = st.text_input(
        "본인의 API 키",
        type="password",
        key="user_api_key",
        placeholder="AIza... 또는 AQ.A...",
        help="입력한 키는 이 브라우저 세션에만 보관되며 서버에 저장되지 않습니다.",
    ).strip()

    if _entered:
        st.success("개인 키를 사용합니다.")
    elif _server_key:
        st.info("서버에 설정된 키를 사용합니다.")

    st.markdown(
        "1. [Google AI Studio](https://aistudio.google.com/apikey) 접속 (Google 계정만 있으면 됨)\n"
        "2. **Create API key** → 생성된 키 복사 (`AIza...` 또는 `AQ.A...` 로 시작)\n"
        "3. 위 칸에 붙여넣기\n\n"
        "카드 등록 없이 **무료**이고, 무료 한도는 각자의 계정에 따로 적용됩니다."
    )

api_key = _entered or _server_key

if not api_key:
    st.info(
        "👈 왼쪽 사이드바에 **본인의 Gemini API 키**를 입력하면 사용할 수 있습니다.\n\n"
        "각자 자기 키를 쓰기 때문에 무료 한도도 각자 따로 적용됩니다."
    )
    st.stop()


def _friendly_llm_error(e: Exception) -> str:
    msg = str(e)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return "무료 티어 사용량 한도에 도달했습니다. 1분 정도 기다렸다가 다시 시도해 주세요. (분당/일일 무료 한도)"
    if "503" in msg or "UNAVAILABLE" in msg:
        return "Gemini 서버가 혼잡합니다. 예비 모델까지 모두 혼잡한 상태이니 몇 분 뒤 다시 시도해 주세요."
    if "API key not valid" in msg or "API_KEY_INVALID" in msg or "PERMISSION_DENIED" in msg:
        return "API 키가 올바르지 않습니다. 사이드바에서 키를 다시 확인해 주세요."
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
    ss.used_once = True  # 한 번 써 본 뒤로는 사용법을 접어 둔다
    with st.spinner("일본어 법률 키워드로 변환 중... (Gemini)"):
        try:
            ss.translation = translator.translate_query(korean_query.strip(), api_key=api_key)
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
                                st.write_stream(
                                    summarizer.summarize_pdf(pdf_path, case_label, api_key=api_key)
                                )
                        except Exception as e:
                            st.error(f"요약 실패: {_friendly_llm_error(e)}")

# ── 푸터 ──────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"{DEVELOPER} · 판례 출처 [일본 재판소 裁判例検索](https://www.courts.go.jp/hanrei/search1/index.html)"
    " · 요약은 참고용이며 법률 자문이 아닙니다."
)
