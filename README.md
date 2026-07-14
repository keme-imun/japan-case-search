# 일본 판례 검색 · 한국어 요약 (Japan Case Search)

한국어로 검색하면 Gemini가 일본어 법률 키워드로 변환해 일본 재판소
[裁判例検索](https://www.courts.go.jp/hanrei/search1/index.html)에서 판례를 찾고,
선택한 판례의 원문 PDF를 내려받아 한국어로 요약해 주는 Streamlit 앱입니다.
**Gemini API 무료 티어만 사용하므로 비용이 들지 않습니다.**

## 파이프라인

1. 한국어 검색어 → **Gemini**가 일본어 법률 검색 키워드로 변환 (JSON schema 강제)
2. courts.go.jp 검색 (`query1`=OR 핵심어, `query2+`=AND 절요어) 및 결과 파싱
3. 선택한 판례 PDF 다운로드 (`downloads/`)
4. **Gemini**가 PDF를 직접 읽고 한국어 요약 스트리밍 (사건 개요 / 쟁점 / 판단 / 주문 / 한국법 시사점)
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

모델은 `.env`의 `GEMINI_MODEL`로 바꿀 수 있습니다.

## 다른 컴퓨터에서 접속 (Streamlit Cloud 무료 배포)

이 앱을 인터넷에 올려 두면 다른 컴퓨터·휴대폰에서도 URL만으로 접속할 수 있습니다.

1. GitHub에 이 저장소를 푸시합니다.
2. https://share.streamlit.io 에 접속해 GitHub 계정을 연동합니다.
3. **"New app"** 을 눌러 저장소 / 브랜치(main) / 메인 파일(`app.py`)을 선택합니다.
4. **"Advanced settings"**(또는 배포 후 앱 설정)의 **Secrets** 칸에 아래 TOML을 붙여넣습니다.

   ```toml
   GEMINI_API_KEY = "AIza..."
   APP_PASSWORD = "원하는비밀번호"   # 선택: 설정하면 접속 시 비밀번호 요구
   ```

5. **Deploy** 를 누르면 몇 분 뒤 `https://<앱이름>.streamlit.app` 주소가 발급됩니다.

주의:

- 무료 인스턴스는 미사용 시 절전 모드로 들어가므로 첫 접속이 느릴 수 있습니다.
- `APP_PASSWORD` 를 설정하지 않으면 URL을 아는 누구나 내 Gemini 무료 한도를
  소모할 수 있으므로 설정을 권장합니다.
- `downloads`·`cache` 폴더는 서버 재시작 시 사라지지만 동작에는 문제가 없습니다.

## 무료 티어 주의사항

- Gemini Flash 무료 한도는 대략 분당 10회 / 하루 250회 수준입니다 (변동 가능).
  한도 초과(429) 시 잠시 기다렸다가 다시 시도하세요. 요약 캐시가 재호출을 줄여 줍니다.
- 무료 티어 입력 데이터는 Google 서비스 개선(학습)에 활용될 수 있습니다.
  이 앱이 보내는 것은 공개된 판례 원문이라 일반적으로 문제가 없지만, 민감한 자료는 넣지 마세요.
- courts.go.jp에 부담을 주지 않도록 요청 간 1초 지연을 둡니다.
- 일부 판례는 전문 PDF가 공개되지 않아 요약할 수 없습니다.
- 요약은 참고용이며 법률 자문이 아닙니다. 정확한 내용은 원문을 확인하세요.
