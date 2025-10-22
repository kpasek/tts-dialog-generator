#!/bin/bash

# Buduj wersję online
pyinstaller app.spec --online-only

# Buduj wersję pełną
pyinstaller app.spec