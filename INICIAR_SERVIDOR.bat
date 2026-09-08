@echo off
REM Cambiar a la carpeta del proyecto
cd /d "c:\Users\AMAT\Desktop\ingreso de aprendices\prubas\ingresos aprendices\backup version vs code\ingresos aprendices 6 backup final\ingresos aprendices 7 backup final"

REM Activar venv
call .venv\Scripts\activate.bat

REM Cambiar a carpeta backend
cd backend

REM Reiniciar base de datos si es necesario
python init_db.py

REM Iniciar servidor
echo.
echo ========================================
echo  Iniciando servidor Flask...
echo ========================================
echo.
python app.py

pause
