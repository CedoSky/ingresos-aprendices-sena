@echo off
title Verificacion de Instalacion - Sistema SENA
color 0E
cd /d "%~dp0"
set ERRORES=0
echo.
echo  ============================================================
echo   VERIFICANDO INSTALACION - SISTEMA DE INGRESOS SENA
echo  ============================================================
echo.
echo  [1] Verificando Python...
python --version
if errorlevel 1 (
    echo      [FALLO] Python NO esta instalado o no esta en el PATH.
    set /a ERRORES+=1
) else (
    echo      [OK]    Python detectado.
)
echo  [2] Verificando entorno virtual (.venv)...
if exist ".venv\Scripts\python.exe" (
    echo      [OK]    Entorno virtual encontrado.
) else (
    echo      [FALLO] Entorno virtual NO encontrado. Ejecuta INSTALAR.bat
    set /a ERRORES+=1
)
echo  [3] Verificando pip...
if exist ".venv\Scripts\pip.exe" (
    echo      [OK]    pip encontrado.
) else (
    echo      [FALLO] pip NO encontrado.
    set /a ERRORES+=1
)
echo  [4] Verificando paquetes instalados...
.venv\Scripts\python.exe -c "import flask"
if errorlevel 1 ( echo      [FALLO] flask - NO instalado ^& set /a ERRORES+=1 ) else echo      [OK]    flask - instalado
.venv\Scripts\python.exe -c "import flask_sqlalchemy"
if errorlevel 1 ( echo      [FALLO] flask_sqlalchemy - NO instalado ^& set /a ERRORES+=1 ) else echo      [OK]    flask_sqlalchemy - instalado
.venv\Scripts\python.exe -c "import flask_socketio"
if errorlevel 1 ( echo      [FALLO] flask_socketio - NO instalado ^& set /a ERRORES+=1 ) else echo      [OK]    flask_socketio - instalado
.venv\Scripts\python.exe -c "import flask_cors"
if errorlevel 1 ( echo      [FALLO] flask_cors - NO instalado ^& set /a ERRORES+=1 ) else echo      [OK]    flask_cors - instalado
.venv\Scripts\python.exe -c "import jwt"
if errorlevel 1 ( echo      [FALLO] jwt - NO instalado ^& set /a ERRORES+=1 ) else echo      [OK]    jwt - instalado
.venv\Scripts\python.exe -c "import sqlalchemy"
if errorlevel 1 ( echo      [FALLO] sqlalchemy - NO instalado ^& set /a ERRORES+=1 ) else echo      [OK]    sqlalchemy - instalado
.venv\Scripts\python.exe -c "import openpyxl"
if errorlevel 1 ( echo      [FALLO] openpyxl - NO instalado ^& set /a ERRORES+=1 ) else echo      [OK]    openpyxl - instalado
.venv\Scripts\python.exe -c "import werkzeug"
if errorlevel 1 ( echo      [FALLO] werkzeug - NO instalado ^& set /a ERRORES+=1 ) else echo      [OK]    werkzeug - instalado
echo  [5] Verificando archivos del proyecto...
if exist "backend\app.py" echo      [OK]    backend\app.py
if not exist "backend\app.py" ( echo      [FALLO] backend\app.py NO encontrado ^& set /a ERRORES+=1 )
if exist "backend\models.py" echo      [OK]    backend\models.py
if not exist "backend\models.py" ( echo      [FALLO] backend\models.py NO encontrado ^& set /a ERRORES+=1 )
if exist "backend\routes.py" echo      [OK]    backend\routes.py
if not exist "backend\routes.py" ( echo      [FALLO] backend\routes.py NO encontrado ^& set /a ERRORES+=1 )
if exist "backend\config.py" echo      [OK]    backend\config.py
if not exist "backend\config.py" ( echo      [FALLO] backend\config.py NO encontrado ^& set /a ERRORES+=1 )
if exist "frontend\ingreso.html" echo      [OK]    frontend\ingreso.html
if not exist "frontend\ingreso.html" ( echo      [FALLO] frontend\ingreso.html NO encontrado ^& set /a ERRORES+=1 )
if exist "frontend\vigilancia.html" echo      [OK]    frontend\vigilancia.html
if not exist "frontend\vigilancia.html" ( echo      [FALLO] frontend\vigilancia.html NO encontrado ^& set /a ERRORES+=1 )
if exist "frontend\administracion.html" echo      [OK]    frontend\administracion.html
if not exist "frontend\administracion.html" ( echo      [FALLO] frontend\administracion.html NO encontrado ^& set /a ERRORES+=1 )
echo  [6] Verificando base de datos...
if exist "backend\instance\sena.db" (
    echo      [OK]    Base de datos encontrada.
) else (
    echo      [AVISO] Base de datos no encontrada. Se creara al iniciar.
)
echo.
echo  ============================================================
if %ERRORES%==0 (
    color 0A
    echo   RESULTADO: TODO CORRECTO - Instalacion lista para usar.
    echo  ============================================================
    echo.
    echo   Ejecuta INICIAR.bat para arrancar el sistema.
) else (
    color 0C
    echo   RESULTADO: %ERRORES% PROBLEMA(S) ENCONTRADO(S)
    echo  ============================================================
    echo.
    echo   Ejecuta INSTALAR.bat y luego vuelve a verificar.
)
echo.
:FIN
echo  Presiona cualquier tecla para cerrar...
pause >nul
