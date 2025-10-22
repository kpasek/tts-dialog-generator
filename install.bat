@echo off
setlocal enabledelayedexpansion

REM ---------------------------------------------
REM Ustawienia
REM ---------------------------------------------
set REPO_URL=https://github.com/kpasek/tts-dialog-generator.git
set REPO_DIR=tts-dialog-generator
set PYTHON_VERSION=3.11
set VENV_DIR=.venv


echo =============================================
echo   Instalator TTS Dialog Generator
echo =============================================

REM ---------------------------------------------
REM Sprawdzenie czy git jest dostępny
REM ---------------------------------------------
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [BŁĄD] Git nie jest zainstalowany lub nie jest w PATH.
    pause
    exit /b 1
)

REM ---------------------------------------------
REM Klonowanie lub aktualizacja repozytorium
REM ---------------------------------------------
if exist "%REPO_DIR%\.git" (
    echo [INFO] Repozytorium istnieje, aktualizacja...
    cd "%REPO_DIR%"
    git pull
) else (
    echo [INFO] Klonowanie repozytorium...
    git clone "%REPO_URL%"
    cd "%REPO_DIR%"
)

REM ---------------------------------------------
REM Sprawdzenie Pythona
REM ---------------------------------------------
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [BŁĄD] Python nie jest zainstalowany lub nie jest w PATH.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version') do set PYVER=%%v
echo [INFO] Wykryto Pythona w wersji %PYVER%

REM ---------------------------------------------
REM Tworzenie środowiska wirtualnego jeśli brak
REM ---------------------------------------------
if not exist "%VENV_DIR%\Scripts\activate" (
    echo [INFO] Tworzenie środowiska wirtualnego (%PYTHON_VERSION%)...
    python -m venv "%VENV_DIR%"
) else (
    echo [INFO] Wirtualne środowisko już istnieje.
)

REM ---------------------------------------------
REM Aktywacja środowiska i instalacja zależności
REM ---------------------------------------------
echo [INFO] Aktywacja środowiska...
call "%VENV_DIR%\Scripts\activate.bat"

echo [INFO] Instalacja zależności z requirements.txt...
pip install --upgrade pip
pip install -r requirements.txt


REM ---------------------------------------------
REM Uruchomienie build.bat
REM ---------------------------------------------
if exist "build.bat" (
    echo [INFO] Uruchamianie build.bat...
    call build.bat
) else (
    echo [UWAGA] Nie znaleziono pliku build.bat
)

echo.
echo =============================================
echo  Instalacja zakończona pomyślnie!
echo =============================================

pause
endlocal
