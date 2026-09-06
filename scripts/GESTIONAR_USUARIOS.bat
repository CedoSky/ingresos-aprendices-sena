@echo off
title Gestionar Usuarios - SENA
color 0B

set "BASE=%~dp0.."
if exist "C:\ingresos\backend\gestionar_usuarios.py" set "BASE=C:\ingresos"
set "BACKEND=%BASE%\backend"
set "PYTHON=%BASE%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [ERROR] No se encontro el entorno virtual. Ejecuta INSTALAR.bat primero.
    pause & exit /b 1
)

cd /d "%BACKEND%"
"%PYTHON%" gestionar_usuarios.py
pause
