#!/bin/bash

python -m nuitka gui.py --standalone --enable-plugin=tk-inter --include-data-dir=assets=assets --output-filename=SubtitleStudio.exe