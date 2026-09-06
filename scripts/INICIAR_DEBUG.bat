@echo off
chcp 65001 >nul
title Sistema de Ingresos SENA - Servidor
color 0A
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo   SISTEMA DE INGRESOS SENA - SERVIDOR FLASK
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

setlocal enabledelayedexpansion
set "BASE=%~dp0.."
set "BACKEND=%BASE%\backend"
set "PYTHON=%BASE%\.venv\Scripts\python.exe"
set "PUERTO=8000"
set "PYTHONIOENCODING=utf-8"

:: Verificar entorno virtual
if not exist "%PYTHON%" (
    color 0C
    echo  [ERROR] No se encontro el entorno virtual en:
    echo  %PYTHON%
    echo.
    echo  Por favor ejecuta primero INSTALAR.bat
    pause
    exit /b 1
)

:: Verificar .env
if not exist "%BACKEND%\.env" (
    color 0C
    echo  [ERROR] No se encontro archivo de configuracion (.env)
    echo.
    echo  Copia backend\.env.example como backend\.env
    pause
    exit /b 1
)

echo  [OK] Entorno virtual configurado
echo  [OK] Archivo .env encontrado
echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo   INICIANDO SERVIDOR FLASK...
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

cd /d "%BACKEND%"

echo  Comando: "%PYTHON%" app.py
echo.
echo  ─────────────────────────────────────────────────────────────
echo.

"%PYTHON%" app.py

echo.
echo  ─────────────────────────────────────────────────────────────
echo.
color 0C
echo  [ALERTA] El servidor se detuvo.
echo.
echo  Si ves errores arriba, verifica:
echo.
echo   1. backend\.env - Variables de entorno correctas
echo   2. Que no haya otro proceso en puerto 8000
echo   3. La conexion a la base de datos
echo.
pause
