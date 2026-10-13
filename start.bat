@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 sponge_pet.py
) else (
    python sponge_pet.py
)
if errorlevel 1 pause
