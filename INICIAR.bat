@echo off
title Sistema de Ingresos SENA
color 0A
echo.
echo  ============================================
echo   SISTEMA DE INGRESOS SENA - Iniciando...
echo  ============================================
echo.

set "BASE=%~dp0"
set "BACKEND=%BASE%backend"
set "PYTHON=%BASE%.venv\Scripts\python.exe"
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
curl -s --max-time 1 "http://localhost:%PUERTO%/health" >nul 2>&1
if not errorlevel 1 (
    echo  [OK] Servidor ya activo, abriendo paginas...
    goto ABRIR_PAGINAS
)

:: ── 2. Liberar puerto si esta ocupado ───────────────────────────────
echo  [1/4] Liberando puerto %PUERTO% si esta ocupado...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr /r ":%PUERTO%.*LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
)

:: ── 3. Arrancar Flask ────────────────────────────────────────────────
echo  [2/4] Iniciando servidor Flask en puerto %PUERTO%...
start "Servidor SENA - NO CERRAR" /min cmd /c "cd /d "%BACKEND%" && "%PYTHON%" app.py"

:: ── 4. Esperar que el servidor responda (via HTTP, sin netstat) ──────
echo  [3/4] Esperando que el servidor este listo...

set INTENTOS=0
:WAIT_LOOP
set /a INTENTOS+=1
if %INTENTOS% gtr 35 (
    echo.
    echo  [ERROR] El servidor no respondio en 35 segundos.
    echo  Revisa la ventana "Servidor SENA - NO CERRAR".
    pause
    exit /b 1
)

curl -s --max-time 1 "http://localhost:%PUERTO%/health" >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto WAIT_LOOP
)

:: ── 5. Abrir páginas ─────────────────────────────────────────
:ABRIR_PAGINAS
echo  [4/4] Abriendo paginas web...

start "" "http://localhost:%PUERTO%/ingreso"
timeout /t 1 /nobreak >nul
start "" "http://localhost:%PUERTO%/login"

echo.
echo  ============================================
echo   Sistema iniciado correctamente!
echo.
echo   [Quiosco]  http://localhost:%PUERTO%/ingreso
echo   [Personal] http://localhost:%PUERTO%/login
echo.
echo   Segun el rol se redirige automaticamente:
echo     Vigilante  -^>  /vigilancia
echo     Admin      -^>  /administracion
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