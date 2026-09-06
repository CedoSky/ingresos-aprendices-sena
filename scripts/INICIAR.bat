@echo off
title Sistema de Ingresos SENA
color 0A
echo.
echo  ============================================
echo   SISTEMA DE INGRESOS SENA - Iniciando...
echo  ============================================
echo.

set "BASE=%~dp0.."
if exist "C:\ingresos\backend\app.py" set "BASE=C:\ingresos"
set "BACKEND=%BASE%\backend"
set "PYTHON=%BASE%\.venv\Scripts\python.exe"
set "PUERTO=8000"
set "PYTHONIOENCODING=utf-8"

:: ── Verificaciones previas ────────────────────────────────────────
if not exist "%PYTHON%" (
    echo  [ERROR] No se encontro el entorno virtual.
    echo  Ejecuta primero INSTALAR.bat
    pause
    exit /b 1
)

if not exist "%BACKEND%\.env" (
    echo  [ERROR] No se encontro backend\.env
    echo  Copia backend\.env.example como backend\.env
    pause
    exit /b 1
)

:: ── 1. Verificar si el servidor ya esta corriendo ──────────────────
curl -s --max-time 1 "http://localhost:%PUERTO%/login" >nul 2>&1
if not errorlevel 1 (
    echo  [OK] Servidor ya activo, abriendo paginas...
    goto ABRIR_PAGINAS
)

:: ── 2. Liberar puerto si esta ocupado ───────────────────────────────
echo  [1/3] Liberando puerto %PUERTO% si esta ocupado...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr /r ":%PUERTO%.*LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
)

:: ── 3. Arrancar Flask en background y abrir navegador ────────────────
echo  [2/3] Iniciando servidor Flask en puerto %PUERTO%...
start "Servidor SENA - NO CERRAR" /min cmd /c "cd /d "%BACKEND%" && "%PYTHON%" app.py"

echo  [3/3] Esperando que Flask arranque (10 segundos)...
timeout /t 10 /nobreak >nul

:: ── 5. Abrir páginas ─────────────────────────────────────────
:ABRIR_PAGINAS
echo  [4/4] Abriendo paginas web...
echo.

:: Abrir navegador con login e ingreso simultaneamente
echo.
echo   Abriendo navegador...
echo    - http://localhost:%PUERTO%/login (Autenticacion)
echo    - http://localhost:%PUERTO%/ingreso_sin_dispositivos (Ingreso)
echo.
start "" "http://localhost:%PUERTO%/login"
start "" "http://localhost:%PUERTO%/ingreso_sin_dispositivos"

echo.
echo  ============================================
echo   Sistema iniciado correctamente!
echo.
echo   PAGINAS ABIERTAS AUTOMATICAMENTE:
echo   [1] Login                http://localhost:%PUERTO%/login
echo   [2] Ingreso              http://localhost:%PUERTO%/ingreso_sin_dispositivos
echo.
echo   Otras paginas disponibles:
echo   [Vigilancia]             http://localhost:%PUERTO%/vigilancia
echo   [Administracion]         http://localhost:%PUERTO%/administracion
echo.
echo   Flujo de uso:
echo     1. Copia tu numero de documento en la pagina de INGRESO
echo     2. Selecciona el ambiente donde entras/sales
echo     3. El sistema registra automaticamente
echo.
echo   Presiona cualquier tecla para DETENER TODO
echo  ============================================
echo.
pause >nul

:: ── Detener servidor ──────────────────────────────────────────
echo.
echo  Deteniendo servidor...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr /r ":%PUERTO%.*LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
)
echo  Servidor detenido. Hasta luego!
timeout /t 2 /nobreak >nul