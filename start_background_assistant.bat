@echo off
REM Tro ly nen (Phase 8): quet dinh ky read-only + toast khi co van de moi.
REM Khong tu xoa/move file. Dong cua so de dung.
cd /d D:\tool

REM Mac dinh quet moi 60 phut. Doi so phut bang cach truyen tham so, vd: 30
set INTERVAL=%1
if "%INTERVAL%"=="" set INTERVAL=60

py -c "from tools.automation.background_assistant import run_background_assistant_loop; run_background_assistant_loop(interval_minutes=%INTERVAL%)"
