@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0panel_windows.ps1" %*
