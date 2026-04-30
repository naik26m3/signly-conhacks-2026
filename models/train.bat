@echo off
cd /d "%~dp0"
".venv_directml\Scripts\python.exe" -m jupyter nbconvert --to script "letterClassifier.ipynb" --output-dir .
".venv_directml\Scripts\python.exe" letterClassifier.py
pause
