@echo off

pyinstaller gui.py --name SubtitleStudio --noconsole --icon assets/icon512.ico --add-data="assets;assets"
