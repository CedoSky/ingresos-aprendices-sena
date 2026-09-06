@echo off
title Mantenimiento - Sistema de Ingresos SENA
color 0B
cd /d "%~dp0"

set "BASE=%~dp0.."
set "BACKEND=%BASE%\backend"
set "PYTHON=%BASE%\.venv\Scripts\python.exe"
set "SCRIPT=%BACKEND%\mantenimiento_sistemas.py"

if not exist "%PYTHON%" (
    echo.
    echo  [ERROR] No se encontro el entorno virtual.
    echo  Ejecuta primero INSTALAR.bat
    pause
    exit /b 1
)

if not exist "%SCRIPT%" (
    echo.
    echo  [ERROR] No se encontro mantenimiento_sistemas.py en backend\
    echo  El archivo es necesario para las operaciones de mantenimiento.
    pause
    exit /b 1
)

:MENU
cls
echo.
echo  ================================================================
echo   MANTENIMIENTO - SISTEMA DE INGRESOS SENA
echo   Solo para personal de soporte tecnico / programadores
echo  ================================================================
echo.
echo   [1] Optimizar base de datos (VACUUM + ANALYZE)
echo   [2] Hacer copia de seguridad de la base de datos
echo   [3] Ver informacion del sistema y base de datos
echo   [4] Limpiar archivos de cache Python (__pycache__)
echo   [5] Verificar e instalar dependencias faltantes
echo   [6] Reparar base de datos (verificar integridad)
echo   [7] Ver logs del servidor
echo   [P] Ver PIN del panel de sistemas (codigo dinamico)
echo.
echo   [0] Salir
echo.
set /p OPCION= "  Selecciona una opcion: "

if "%OPCION%"=="1" goto :VACUUM
if "%OPCION%"=="2" goto :BACKUP
if "%OPCION%"=="3" goto :INFO
if "%OPCION%"=="4" goto :PYCACHE
if "%OPCION%"=="5" goto :DEPS
if "%OPCION%"=="6" goto :INTEGRIDAD
if "%OPCION%"=="7" goto :LOGS
if /i "%OPCION%"=="P" goto :PIN_SISTEMAS
if "%OPCION%"=="0" goto :FIN

echo  Opcion invalida.
timeout /t 2 /nobreak >nul
goto :MENU

:: ============================================================
:VACUUM
cls
echo.
cd /d "%BACKEND%"
"%PYTHON%" "%SCRIPT%" vacuum
echo.
pause
goto :MENU


:: ============================================================
:BACKUP
cls
echo.
cd /d "%BACKEND%"
"%PYTHON%" "%SCRIPT%" backup
echo.
pause
goto :MENU


:: ============================================================
:INFO
cls
echo.
cd /d "%BACKEND%"
"%PYTHON%" "%SCRIPT%" info
echo.
pause
goto :MENU


:: ============================================================
:PYCACHE
cls
echo.
cd /d "%BACKEND%"
"%PYTHON%" "%SCRIPT%" pycache
echo.
pause
goto :MENU


:: ============================================================
:DEPS
cls
echo.
cd /d "%BACKEND%"
"%PYTHON%" "%SCRIPT%" deps
echo.
pause
goto :MENU


:: ============================================================
:INTEGRIDAD
cls
echo.
cd /d "%BACKEND%"
"%PYTHON%" "%SCRIPT%" integridad
echo.
pause
goto :MENU


:: ============================================================
:LOGS
cls
echo.
cd /d "%BACKEND%"
"%PYTHON%" "%SCRIPT%" logs
echo.
pause
goto :MENU


:: ============================================================
:PIN_SISTEMAS
cls
echo.
echo  Mostrando codigo de acceso dinamico del panel de sistemas...
echo  (el secreto se guarda en backend\.env, nunca en el codigo fuente)
echo.
cd /d "%BACKEND%"
"%PYTHON%" gestionar_pin_sistemas.py

echo.
pause
goto :MENU


:: ============================================================
:FIN
echo.
echo  Hasta luego.
echo.
timeout /t 2 /nobreak >nul
