# 일본 판례 검색 · 한국어 요약 (Japan Case Search)

한국어로 검색하면 Gemini가 일본어 법률 키워드로 변환해 일본 재판소
[裁判例検索](https://www.courts.go.jp/hanrei/search1/index.html)에서 판례를 찾고,
선택한 판례의 원문 PDF를 내려받아 한국어로 요약해 주는 Streamlit 앱입니다.
**Gemini API 무료 티어만 사용하므로 비용이 들지 않습니다.**

## 파이프라인

1. 한국어 검색어 → **Gemini**가 일본어 법률 검색 키워드로 변환 (JSON schema 강제)
2. courts.go.jp 검색 (`query1`=OR 핵심어, `query2+`=AND 절요어) 및 결과 파싱
3. 선택한 판례 PDF 다운로드 (`downloads/`)
4. **Gemini**가 판결문을 읽고 한국어 요약 스트리밍 (사건 개요 / 쟁점 / 판단 / 주문 / 한국법 시사점)
   — PDF 원본 업로드와 로컬 텍스트 추출 중 토큰이 적게 드는 쪽을 자동 선택
5. 요약은 `cache/`에 저장되어 같은 판례 재조회 시 즉시 표시 (무료 한도 절약)

## 설치 및 실행

```powershell
# 1) 의존성 설치 (최초 1회)
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 2) 무료 API 키 설정
#    https://aistudio.google.com/apikey 에서 발급 (Google 계정만 필요, 카드 불필요)
copy .env.example .env   # 열어서 GEMINI_API_KEY 입력

# 3) 실행
.venv\Scripts\streamlit run app.py
```

## 파일 구성

- `app.py` — Streamlit UI
- `src/translator.py` — 한→일 키워드 변환 (Gemini, 기본 gemini-flash-latest)
- `src/courts_client.py` — courts.go.jp 검색·파싱·PDF 다운로드
- `src/summarizer.py` — PDF 한국어 요약 (Gemini, 스트리밍 + 캐시)
- `src/pdf_text.py` — PDF 로컬 텍스트 추출 및 입력 방식(PDF/텍스트) 토큰 비교

모델은 `.env`의 `GEMINI_MODEL`로 바꿀 수 있습니다.

### 입력 방식이 토큰에 미치는 영향

Gemini는 PDF를 **페이지당 258토큰 정액**으로 계산합니다. 그래서 글자가 빽빽한
판결문은 PDF를 그대로 올리는 편이 오히려 쌉니다.

| 44페이지 판결문 실측 | 토큰 |
|---|---|
| PDF 원본 업로드 | 11,353 |
| 로컬 추출 텍스트 (38,820자) | 26,055 |

`src/pdf_text.py`가 두 방식의 예상 토큰을 비교해 싼 쪽을 자동으로 고릅니다.
표지·여백이 많아 글자가 성긴 PDF에서는 텍스트 쪽이 선택됩니다.

## 다른 컴퓨터에서 접속 (Streamlit Cloud 무료 배포)

이 앱을 인터넷에 올려 두면 다른 컴퓨터·휴대폰에서도 URL만으로 접속할 수 있습니다.

1. GitHub에 이 저장소를 푸시합니다.
2. https://share.streamlit.io 에 접속해 GitHub 계정을 연동합니다.
3. **"New app"** 을 눌러 저장소 / 브랜치(main) / 메인 파일(`app.py`)을 선택합니다.
4. **"Advanced settings"**(또는 배포 후 앱 설정)의 **Secrets** 칸에 아래 TOML을 붙여넣습니다.

   ```toml
   REQUIRE_USER_API_KEY = "1"        # 접속자가 각자 자기 키를 입력하도록 강제
   APP_PASSWORD = "원하는비밀번호"   # 선택: 설정하면 접속 시 비밀번호 요구
   ```

5. **Deploy** 를 누르면 몇 분 뒤 `https://<앱이름>.streamlit.app` 주소가 발급됩니다.

주의:

- 무료 인스턴스는 미사용 시 절전 모드로 들어가므로 첫 접속이 느릴 수 있습니다.
- `downloads`·`cache` 폴더는 서버 재시작 시 사라지지만 동작에는 문제가 없습니다.

## 여러 사람에게 공유하기 (각자 자기 API 키 사용)

API 키를 나눠 주지 않아도 됩니다. 앱을 배포한 뒤 URL만 알려 주면, 접속한 사람이
**사이드바에 자기 Gemini 키를 입력해서** 자기 무료 한도로 사용합니다.

**배포하는 사람이 할 일**

Secrets에 `GEMINI_API_KEY`를 **넣지 말고**, 대신 `REQUIRE_USER_API_KEY = "1"` 을
넣습니다. 이 값이 설정되면 서버 키를 아예 무시하므로, 내 키가 실수로 남아 있어도
남이 내 한도를 쓰지 못합니다.

**쓰는 사람이 할 일**

1. [Google AI Studio](https://aistudio.google.com/apikey) 에서 **Create API key**
   (Google 계정만 있으면 되고 카드 등록 불필요)
2. 앱 왼쪽 사이드바에 `AIza...` 키를 붙여넣기

키는 브라우저 세션에만 남고 서버에 저장되지 않으며, 탭을 닫으면 사라집니다.
무료 한도는 각자의 Google 계정에 따로 적용되므로 서로 영향을 주지 않습니다.
`cache/` 의 요약은 공유되어, 누군가 이미 요약한 판례는 아무도 API를 쓰지 않고
바로 볼 수 있습니다.

> 키를 카카오톡 등으로 주고받지 않도록 안내해 주세요. 각자 발급이 원칙입니다.

## 무료 티어 주의사항

- Gemini Flash 무료 한도는 대략 분당 10회 / 하루 250회 수준입니다 (변동 가능).
  한도 초과(429) 시 잠시 기다렸다가 다시 시도하세요. 요약 캐시가 재호출을 줄여 줍니다.
- 무료 티어 입력 데이터는 Google 서비스 개선(학습)에 활용될 수 있습니다.
  이 앱이 보내는 것은 공개된 판례 원문이라 일반적으로 문제가 없지만, 민감한 자료는 넣지 마세요.
- courts.go.jp에 부담을 주지 않도록 요청 간 1초 지연을 둡니다.
- 일부 판례는 전문 PDF가 공개되지 않아 요약할 수 없습니다.
- 요약은 참고용이며 법률 자문이 아닙니다. 정확한 내용은 원문을 확인하세요.
