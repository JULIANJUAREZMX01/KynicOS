@echo off
title KYNIKOS - configurar
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kynikos.ps1" configurar
echo.
echo ------------------------------------------------------------
echo Pulsa una tecla para cerrar.
pause >nul
