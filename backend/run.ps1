# Script para iniciar el backend en Windows PowerShell

Write-Host "Instalando dependencias..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host ""
Write-Host "Creando archivo .env si no existe..." -ForegroundColor Green
if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Archivo .env creado - Editalo con tus credenciales" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Iniciando servidor Flask..." -ForegroundColor Green
python app.py
