@echo off
:: ================================================================
:: CONFIGURAR_RESPALDO_RED.bat
:: Ejecutar en la laptop del SERVIDOR SENA (donde corre el sistema)
:: Configura el respaldo automatico hacia otra laptop en la red
:: ================================================================
title Configurar Respaldo en Red - SENA
color 0A
chcp 65001 >nul 2>&1
cd /d "%~dp0"

set "BASE=%~dp0"
set "BACKEND=%BASE%backend"
set "ENV_FILE=%BACKEND%\.env"
set "PYTHON=%BASE%.venv\Scripts\python.exe"
set "TMPSCRIPT=%TEMP%\sena_config_red.py"
set "TMPBACKUP=%TEMP%\sena_backup_prueba.py"

echo.
echo  ================================================================
echo   CONFIGURAR RESPALDO EN RED - SENA
echo   Vincula el servidor con la laptop receptora de respaldos
echo  ================================================================
echo.

:: -- Verificar .venv -----------------------------------------------
if not exist "%PYTHON%" (
    echo  [ERROR] No se encontro el entorno virtual en:
    echo         %BASE%.venv\
    echo.
    echo  Ejecuta primero INSTALAR.bat
    echo.
    pause
    exit /b 1
)
echo  [OK] Entorno virtual encontrado.

:: -- Verificar .env ------------------------------------------------
if not exist "%ENV_FILE%" (
    echo  [ERROR] No se encontro el archivo de configuracion:
    echo         %ENV_FILE%
    echo.
    pause
    exit /b 1
)
echo  [OK] Archivo .env encontrado.
echo.

:: -- Solicitar IP --------------------------------------------------
echo  ================================================================
echo   DATOS DE LA LAPTOP RECEPTORA
echo  ================================================================
echo.
echo  Escribe la IP de la laptop receptora de respaldos.
echo  (La que muestra CONFIGURAR_LAPTOP_RECEPTORA.bat al final)
echo.
set /p "IP_REMOTA=  IP de la laptop receptora: "

if "%IP_REMOTA%"=="" (
    echo.
    echo  [ERROR] Debes ingresar una IP.
    pause
    exit /b 1
)
echo.

:: -- Verificar ping ------------------------------------------------
echo  Verificando conexion con %IP_REMOTA%...
ping -n 1 -w 3000 %IP_REMOTA% >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ADVERTENCIA] No se pudo hacer ping a %IP_REMOTA%
    echo  Puede ser que el firewall bloquee ping pero la carpeta si sea accesible.
    echo.
    echo  Continuar de todas formas? (S/N)
    set /p "CONTINUAR=  Respuesta: "
    if /i not "%CONTINUAR%"=="S" (
        echo  Cancelado.
        pause
        exit /b 0
    )
) else (
    echo  [OK] Conexion con %IP_REMOTA% verificada.
)
echo.

:: -- Actualizar .env via Python ------------------------------------
echo  Actualizando configuracion del sistema...

(
echo import re, sys
echo env = r'%ENV_FILE%'
echo ip  = '%IP_REMOTA%'
echo network_path = r'\\\\' + ip + r'\\SENA_RESPALDOS'
echo
echo with open(env, 'r', encoding='utf-8'^) as f:
echo     lines = f.readlines(^)
echo
echo vars_nuevas = {
echo     'STORAGE_BACKEND':    'network',
echo     'NETWORK_BACKUP_PATH': network_path,
echo }
echo
echo resultado = []
echo claves_usadas = set(^)
echo for line in lines:
echo     m = re.match(r'^([A-Z_]+)=', line^)
echo     if m and m.group(1^) in vars_nuevas:
echo         resultado.append(f"{m.group(1^)}={vars_nuevas[m.group(1^)]}\n"^)
echo         claves_usadas.add(m.group(1^)^)
echo     else:
echo         resultado.append(line^)
echo
echo for k, v in vars_nuevas.items(^):
echo     if k not in claves_usadas:
echo         resultado.append(f"{k}={v}\n"^)
echo
echo with open(env, 'w', encoding='utf-8'^) as f:
echo     f.writelines(resultado^)
echo print('OK'  ^)
) > "%TMPSCRIPT%"

"%PYTHON%" "%TMPSCRIPT%"
if errorlevel 1 (
    echo  [ERROR] No se pudo actualizar .env
    del "%TMPSCRIPT%" >nul 2>&1
    pause
    exit /b 1
)
del "%TMPSCRIPT%" >nul 2>&1
echo  [OK] Configuracion guardada:
echo        STORAGE_BACKEND = network
echo        NETWORK_BACKUP_PATH = \\%IP_REMOTA%\SENA_RESPALDOS
echo.

:: -- Prueba de escritura SMB ----------------------------------------
echo  Probando acceso a la carpeta compartida...
set "RUTA_RED=\\%IP_REMOTA%\SENA_RESPALDOS"
echo test > "%RUTA_RED%\test_conexion.txt" 2>nul
if exist "%RUTA_RED%\test_conexion.txt" (
    del "%RUTA_RED%\test_conexion.txt" >nul 2>&1
    echo  [OK] Escritura en %RUTA_RED% exitosa.
) else (
    echo  [ADVERTENCIA] No se pudo escribir en %RUTA_RED%
    echo.
    echo  Posibles causas:
    echo    - La laptop receptora no tiene CONFIGURAR_LAPTOP_RECEPTORA.bat ejecutado
    echo    - El Firewall bloquea el acceso
    echo    - La carpeta no esta compartida correctamente
    echo.
    echo  Continuar de todas formas? (S/N)
    set /p "CONT2=  Respuesta: "
    if /i not "%CONT2%"=="S" (
        echo  Cancelado.
        pause
        exit /b 0
    )
)
echo.

:: -- Primer respaldo de prueba --------------------------------------
echo  Ejecutando primer respaldo de prueba...

(
echo import sys, os
echo sys.path.insert(0, r'%BACKEND%'^)
echo os.chdir(r'%BACKEND%'^)
echo from dotenv import load_dotenv
echo load_dotenv(r'%ENV_FILE%'^)
echo from cloud_storage import DatabaseBackupManager
echo mgr = DatabaseBackupManager(^)
echo ok, msg = mgr.crear_respaldo_completo(^)
echo print('RESULTADO:', 'OK' if ok else 'FALLO', '-', msg^)
echo sys.exit(0 if ok else 1^)
) > "%TMPBACKUP%"

"%PYTHON%" "%TMPBACKUP%"
set "BACKUP_OK=%errorlevel%"
del "%TMPBACKUP%" >nul 2>&1

echo.
if "%BACKUP_OK%"=="0" (
    echo  [OK] Primer respaldo completado correctamente.
) else (
    echo  [ADVERTENCIA] El respaldo de prueba reporto un error.
    echo  Revisa que el sistema este correctamente instalado.
)

:: -- Resumen final --------------------------------------------------
echo.
echo  ================================================================
echo   CONFIGURACION COMPLETADA
echo  ================================================================
echo.
echo  El servidor SENA guardara respaldos automaticamente en:
echo    %RUTA_RED%
echo.
echo  Los respaldos se ejecutan cada 3 horas mientras el sistema
echo  este en funcionamiento (INICIAR.bat).
echo.
echo  Si la laptop receptora no esta disponible, los datos se
echo  guardan localmente y se sincronizan cuando vuelva a conectarse.
echo.
echo  Presiona cualquier tecla para cerrar...
pause >nul
