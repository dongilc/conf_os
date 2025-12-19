@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Conference OS - Backend (Conda)

REM ==============================
REM 사용자 설정 영역
REM ==============================
set ENV_NAME=conf_os
set PYTHON_VERSION=3.11

echo ==================================================
echo  Conference OS Backend 실행 (Conda)
echo  가상환경: %ENV_NAME%
echo ==================================================
echo.

cd /d "%~dp0"

REM ------------------------------
REM [1/3] Conda 환경 활성화
REM ------------------------------
echo [1/3] Conda 가상환경 활성화 중...
call conda activate %ENV_NAME%
if errorlevel 1 (
    echo.
    echo [ERROR] conda activate 실패
    echo - 일반 CMD에서는 activate가 안 될 수 있습니다.
    echo - Anaconda Prompt에서 실행하세요.
    pause
    exit /b 1
)
echo [OK] 가상환경 활성화 완료
echo.

REM ------------------------------
REM [2/3] requirements 설치
REM ------------------------------
echo [2/3] 패키지 설치 중...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] 패키지 설치 실패
    pause
    exit /b 1
)
echo [OK] 패키지 설치 완료
echo.

REM ------------------------------
REM [3/3] 서버 실행
REM ------------------------------
echo [3/3] FastAPI 서버 실행
echo ------------------------------------------
echo  - Swagger: http://127.0.0.1:8000/docs
echo  - 종료: Ctrl + C
echo ------------------------------------------
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
set EXITCODE=%errorlevel%

echo.
echo ==================================================
echo  서버 종료됨 (exit code=%EXITCODE%)
echo ==================================================
pause
exit /b %EXITCODE%
