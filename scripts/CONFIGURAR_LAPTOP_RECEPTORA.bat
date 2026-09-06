@echo off
:: ================================================================
:: CONFIGURAR_LAPTOP_RECEPTORA.bat
:: Ejecutar SOLO en la laptop que RECIBIRA los respaldos
:: No requiere Python ni configuracion previa.
:: Ejecutar como Administrador.
:: ================================================================
title Laptop Receptora de Respaldos - SENA
color 0B
chcp 65001 >nul 2>&1

echo.
echo  ================================================================
echo   CONFIGURAR LAPTOP RECEPTORA DE RESPALDOS - SENA
echo   Esta laptop recibira copias de seguridad automaticas
echo  ================================================================
echo.

:: -- Verificar administrador ----------------------------------------
net session >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Debes ejecutar este archivo como ADMINISTRADOR.
    echo.
    echo  Cierra esta ventana, haz clic derecho en el archivo
    echo  y elige "Ejecutar como administrador".
    echo.
    pause
    exit /b 1
)
echo  [OK] Privilegios de administrador confirmados.
echo.

:: -- Paso 1: Crear carpeta de respaldos ----------------------------
set "CARPETA=C:\SENA_RESPALDOS"
echo  [1/4] Creando carpeta de respaldos...
if not exist "%CARPETA%" (
    mkdir "%CARPETA%"
    echo        Carpeta creada: %CARPETA%
) else (
    echo        La carpeta ya existe: %CARPETA%
)
echo.

:: -- Paso 2: Activar servicios necesarios --------------------------
echo  [2/4] Activando servicios de comparticion de archivos...
sc config LanmanServer      start= auto >nul 2>&1
sc start  LanmanServer             >nul 2>&1
sc config LanmanWorkstation start= auto >nul 2>&1
sc start  LanmanWorkstation        >nul 2>&1
net start "Server"                 >nul 2>&1
net start "Workstation"            >nul 2>&1
echo        Servicios activados.
echo.

:: -- Paso 3: Compartir la carpeta en la red ------------------------
echo  [3/4] Compartiendo carpeta SENA_RESPALDOS en la red...
net share SENA_RESPALDOS /delete >nul 2>&1
net share SENA_RESPALDOS="%CARPETA%" /GRANT:Everyone,FULL /UNLIMITED >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Intentando con PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-SmbShare -Name 'SENA_RESPALDOS' -Force -ErrorAction SilentlyContinue; New-SmbShare -Name 'SENA_RESPALDOS' -Path 'C:\SENA_RESPALDOS' -FullAccess 'Everyone' -ErrorAction SilentlyContinue" >nul 2>&1
)
echo        Carpeta compartida como: \\IP\SENA_RESPALDOS
echo.

:: -- Paso 4: Abrir Firewall ----------------------------------------
echo  [4/4] Configurando Firewall de Windows...
netsh advfirewall firewall set rule group="Compartir archivos e impresoras" new enable=Yes >nul 2>&1
netsh advfirewall firewall set rule group="File and Printer Sharing"         new enable=Yes >nul 2>&1
echo        Firewall configurado.
echo.

:: -- Detectar IP de esta laptop ------------------------------------
echo  ================================================================
echo   CONFIGURACION COMPLETADA
echo  ================================================================
echo.
echo  La IP de ESTA laptop (anotala para el siguiente paso):
echo.

:: Mostrar solo IPv4 de adaptadores activos usando ipconfig
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /i "Direcci" ^| findstr /i "IPv4"') do (
    set "IPLINEA=%%A"
    call :MOSTRAR_IP
)
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /i "IPv4"') do (
    set "IPLINEA=%%A"
    call :MOSTRAR_IP
)
goto :DESPUES_IP

:MOSTRAR_IP
set "IPLINEA=%IPLINEA: =%"
if not "%IPLINEA%"=="" (
    if not "%IPLINEA:~0,3%"=="127" (
        if not "%IPLINEA:~0,3%"=="169" (
            echo      ^>  %IPLINEA%
        )
    )
)
exit /b

:DESPUES_IP
echo.
echo  NOTA: Si ves varias IPs, usa la que empieza por 192.168. o 10.
echo  Si no aparecio ninguna, ejecuta en cmd:  ipconfig
echo.
echo  ================================================================
echo   SIGUIENTE PASO (en la laptop del servidor SENA):
echo  ================================================================
echo.
echo  1. Copia el archivo CONFIGURAR_RESPALDO_RED.bat al servidor SENA
echo  2. Ejecutalo como Administrador
echo  3. Cuando pregunte la IP, escribe la que aparece arriba
echo  4. El sistema guardara respaldos automaticamente aqui cada 3 horas
echo.
echo  Carpeta donde llegaran los respaldos: %CARPETA%
echo.
start "" explorer.exe "%CARPETA%"
echo  Presiona cualquier tecla para cerrar...
pause >nul
