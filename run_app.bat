@echo off
chcp 949 > nul
cd /d "%~dp0"
title 일본 판례 검색

if not exist ".venv\Scripts\streamlit.exe" (
  echo.
  echo [최초 실행] 필요한 프로그램을 설치합니다. 몇 분 걸립니다...
  echo.
  python -m venv .venv
  if errorlevel 1 goto :nopython
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -r requirements.txt
  if errorlevel 1 goto :failed
  echo.
  echo 설치가 끝났습니다.
  echo.
)

echo 앱을 시작합니다. 잠시 후 브라우저가 자동으로 열립니다.
echo 앱을 끄려면 이 검은 창을 닫으세요.
echo.
.venv\Scripts\streamlit run app.py
goto :eof

:nopython
echo.
echo [오류] Python을 찾을 수 없습니다.
echo https://www.python.org/downloads/ 에서 설치할 때
echo "Add Python to PATH" 를 체크했는지 확인하세요.
echo.
pause
goto :eof

:failed
echo.
echo [오류] 패키지 설치에 실패했습니다. 인터넷 연결을 확인하세요.
echo.
pause
