@echo off
title KYNIKOS - arrancar y validar
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kynikos.ps1" auto
echo.
echo ------------------------------------------------------------
echo Pulsa una tecla para cerrar.
pause >nul
