@echo off
REM 8.3: launcher mo tu toast (protocol aidesktop:cleanup).
REM Mo Bot Panel va nhay thang toi banner Don 1 cham.
cd /d D:\tool
start "" pythonw -m tools.ui.bot_panel --cleanup
