@echo off
chcp 65001 >nul
title Kiri Web Dashboard Launcher
cd /d "%~dp0"
netstat -ano -p tcp | findstr ":7788 " | findstr "LISTENING" >nul
if %errorlevel%==0 (
    start "" "http://127.0.0.1:7788"
) else (
    start "Kiri Web Server" /min python kiri_web.py
)
