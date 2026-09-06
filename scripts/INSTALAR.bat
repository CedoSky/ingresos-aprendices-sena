@echo off
chcp 65001 >nul 2>&1
title Instalador - Sistema de Ingresos SENA
color 0B
cd /d "%~dp0"

set "BASE=%~dp0.."
set "VENV=%BASE%\.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "BACKEND=%BASE%\backend"
set "REQ=%BACKEND%\requirements.txt"
set "CMD_PYTHON="
set "PIP_FLAGS=--trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --default-timeout 120 --retries 3"

echo.
echo  ============================================================
echo   INSTALADOR - SISTEMA DE INGRESOS SENA
echo  ============================================================
echo.
echo  Ubicacion detectada: %BASE%
echo.

:: --- Verificar que el proyecto este completo --------------------
if not exist "%BACKEND%\" goto :ERR_BACKEND
if not exist "%REQ%"       goto :ERR_REQ
echo  [OK] Estructura del proyecto verificada.
echo.

:: ============================================================
:: PASO 0: Habilitar rutas largas en Windows
:: ============================================================
echo  [0/5] Habilitando rutas largas en Windows...
reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f >nul 2>&1
echo        Listo.

:: ============================================================
:: PASO 1: Detectar Python instalado
:: ============================================================
echo.
echo  [1/5] Buscando Python en el sistema...
python --version >nul 2>&1
if not errorlevel 1 set "CMD_PYTHON=python" & goto :PYTHON_OK
py --version >nul 2>&1
if not errorlevel 1 set "CMD_PYTHON=py"     & goto :PYTHON_OK
goto :ERR_PYTHON

:PYTHON_OK
%CMD_PYTHON% --version
echo        Python encontrado.

:: ============================================================
:: PASO 2: Crear o reparar el entorno virtual
:: ============================================================
echo.
echo  [2/5] Preparando entorno virtual .venv...
if not exist "%PYTHON%" goto :CREAR_VENV
"%PYTHON%" -c "import sys" >nul 2>&1
if not errorlevel 1 goto :VENV_OK
echo  Entorno virtual danado, recreando...
rmdir /s /q "%VENV%" >nul 2>&1

:CREAR_VENV
%CMD_PYTHON% -m venv "%VENV%"
if errorlevel 1 goto :ERR_VENV

:VENV_OK
echo        Entorno virtual listo.

:: ============================================================
:: PASO 3: Asegurar pip actualizado
:: ============================================================
echo.
echo  [3/5] Actualizando pip...
"%PYTHON%" -m ensurepip --upgrade >nul 2>&1
"%PYTHON%" -m pip install --upgrade pip setuptools wheel %PIP_FLAGS% >nul 2>&1
echo        Pip listo.

:: ============================================================
:: PASO 4: Instalar dependencias del proyecto
:: ============================================================
echo.
echo  [4/5] Instalando dependencias del proyecto...
echo        Puede tardar varios minutos la primera vez.
echo.
"%PYTHON%" -m pip install -r "%REQ%" %PIP_FLAGS%
if errorlevel 1 goto :ERR_DEPS
echo.
echo        Dependencias instaladas correctamente.

:: ============================================================
:: PASO 5: Inicializar base de datos
:: ============================================================
echo.
echo  [5/5] Inicializando base de datos...
if exist "%BACKEND%\instance\sena.db" goto :DB_EXISTE
if not exist "%BACKEND%\instance\" mkdir "%BACKEND%\instance"
"%PYTHON%" "%BACKEND%\init_db.py"
if errorlevel 1 goto :DB_AVISO
echo        Base de datos creada correctamente.
goto :EXITO

:DB_EXISTE
echo        La base de datos ya existe.
goto :EXITO

:DB_AVISO
echo  [AVISO] No se pudo inicializar la BD. Vuelve a ejecutar INSTALAR.bat.

:EXITO
echo.
echo  ============================================================
echo   INSTALACION COMPLETADA - Ahora ejecuta INICIAR.bat
echo  ============================================================
echo.
goto :FIN

:: ============================================================
:: BLOQUES DE ERROR
:: ============================================================

:ERR_BACKEND
echo  [ERROR] No se encontro la carpeta del proyecto.
echo.
echo  Ruta esperada:  %BACKEND%
echo.
echo  SOLUCION: Copia TODA la carpeta del proyecto
echo  al equipo. No copies solo INSTALAR.bat.
echo.
goto :FIN

:ERR_REQ
echo  [ERROR] No se encontro requirements.txt
echo.
echo  Ruta esperada:  %REQ%
echo.
echo  SOLUCION: El proyecto esta incompleto.
echo  Copia la carpeta entera del proyecto.
echo.
goto :FIN

:ERR_PYTHON
echo.
echo  [ERROR] Python no esta instalado o no esta en el PATH.
echo.
echo  Descarga Python 3.10 o superior desde:
echo    https://www.python.org/downloads/
echo.
echo  Al instalar, marca: Add Python to PATH
echo.
goto :FIN

:ERR_VENV
echo.
echo  [ERROR] No se pudo crear el entorno virtual .venv
echo.
echo  Verifica que Python este bien instalado y
echo  vuelve a ejecutar INSTALAR.bat
echo.
goto :FIN

:ERR_DEPS
echo.
echo  [ERROR] Fallo la instalacion de dependencias.
echo.
echo  Soluciones posibles:
echo    1. Sin internet    - conectate e intenta de nuevo
echo    2. Proxy SENA      - pide a sistemas abrir pypi.org
echo    3. Antivirus       - desactivalo temporalmente
echo    4. Python antiguo  - instala v3.10 o superior
echo.
goto :FIN

:FIN
echo  Presiona cualquier tecla para cerrar...
pause >nul