@echo off
title KYNIKOS - configurar
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0configurar.ps1"
echo.
echo Pulsa una tecla para cerrar.
pause >nul
