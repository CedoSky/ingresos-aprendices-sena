@echo off
chcp 65001 >nul
title SISTEMA SENA - Servidor Flask
color 0A
setlocal enabledelayedexpansion

set "BASE=%~dp0.."
set "BACKEND=%BASE%\backend"
set "PYTHON=%BASE%\.venv\Scripts\python.exe"
set "PUERTO=8000"
set "HOST=127.0.0.1"

cls
echo.
echo  ╔═══════════════════════════════════════════════════════════════╗
echo   SISTEMA DE INGRESOS SENA - Servidor
echo   Puerto: %PUERTO%
echo  ╚═══════════════════════════════════════════════════════════════╝
echo.

:: Validaciones
if not exist "%PYTHON%" (
    color 0C
    echo  [ERROR] Entorno virtual no encontrado
    pause
    exit /b 1
)

if not exist "%BACKEND%\.env" (
    color 0C
    echo  [ERROR] Falta backend\.env
    pause
    exit /b 1
)

:: Matar procesos anteriores en el puerto
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /r ":%PUERTO%"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo  [1/3] Configuracion validada
echo  [2/3] Puerto %PUERTO% liberado
echo  [3/3] Iniciando servidor...
echo.
echo  URL: http://localhost:%PUERTO%/ingreso
echo  Usuario: vigilante / admin
echo.
echo  Presiona CTRL+C para detener
echo  ────────────────────────────────────────
echo.

cd /d "%BACKEND%"
"%PYTHON%" app.py 2>&1

echo.
echo  ────────────────────────────────────────
color 0C
echo  Servidor detenido.
timeout /t 2 >nul
