@echo off

REM Buduj wersję online
pyinstaller app.spec --online-only

REM Buduj wersję pełną
pyinstaller app.spec