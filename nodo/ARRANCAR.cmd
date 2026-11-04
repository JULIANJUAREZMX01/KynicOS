@echo off
title KYNIKOS - arrancar y validar
cd /d "%~dp0.."

echo Ejecutando el arranque del nodo KYNIKOS...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0arrancar-y-validar.ps1"

echo.
echo ------------------------------------------------------------
echo Cuando termine, este recuadro se queda abierto para que leas.
echo Pulsa una tecla para cerrar.
pause >nul
