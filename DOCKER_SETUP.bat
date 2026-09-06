@echo off
REM ════════════════════════════════════════════════════════════════════════════
REM DOCKER_SETUP.bat — Instalación y ejecución
REM Sistema de Control de Ingresos SENA
REM ════════════════════════════════════════════════════════════════════════════

setlocal enabledelayedexpansion
chcp 65001 >nul
cls
color 0A

echo.
echo  INSTALACION Y EJECUCION DE DOCKER
echo  Sistema de Ingresos SENA
echo.

REM Verificar admin
net session >nul 2>&1
if errorlevel 1 (
    color 0C
    echo  ERROR: Ejecuta como administrador
    echo.
    pause
    exit /b 1
)

REM Verificar Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo  Docker no instalado. Descargalo desde:
    echo  https://www.docker.com/products/docker-desktop
    echo.
    echo  Instalalo, reinicia, y vuelve a ejecutar este script.
    echo.
    pause
    exit /b 1
)

REM Iniciar servicios
echo.
echo  Iniciando servicios...
docker-compose up -d

if errorlevel 1 (
    color 0C
    echo  ERROR al iniciar servicios
    pause
    exit /b 1
)

echo.
color 0A
echo  LISTO - Tu sistema esta en:
echo    Frontend: http://localhost
echo    Backend: http://localhost:8000
echo    Usuario: admin@sena.edu.co / admin123
echo.

pause
