"""이 앱의 공유용 주소를 알아낸다.

Streamlit은 실행 중인 페이지 주소를 st.context.url 로 알려준다. 다만 로컬에서
띄운 주소(localhost)는 남에게 보내도 열리지 않으므로 공유용으로 취급하지 않는다.
"""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", None, ""}


def normalize(raw: str | None, override: str | None = None) -> str | None:
    """공유해도 되는 주소면 정규화해서 돌려주고, 아니면 None.

    override(APP_URL)가 있으면 그것을 우선한다 — 커스텀 도메인을 쓰거나
    리버스 프록시 뒤에 있어 실제 접속 주소와 다를 때를 위한 탈출구.
    """
    if override and override.strip():
        return override.strip().rstrip("/")
    if not raw:
        return None

    p = urlparse(raw)
    if p.hostname in LOCAL_HOSTS:
        return None
    if p.scheme not in ("http", "https"):
        return None

    # 쿼리·프래그먼트에는 개인 상태가 담길 수 있으므로 떼어 낸다
    cleaned = urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), "", "", ""))
    return cleaned or None
