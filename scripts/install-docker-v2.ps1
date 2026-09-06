param()

Write-Host "`nINSTALADOR AUTOMATICO DE DOCKER`n" -ForegroundColor Cyan

Write-Host "[1/3] Verificando si Docker esta instalado..." -ForegroundColor Cyan

$dockerExists = $false
$checkDocker = docker --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK Docker encontrado: $checkDocker" -ForegroundColor Green
    $dockerExists = $true
} else {
    Write-Host "  Docker no encontrado" -ForegroundColor Yellow
}

if ($dockerExists) {
    Write-Host "`nOK Docker ya esta instalado.`n" -ForegroundColor Green
    exit 0
}

Write-Host "[2/3] Verificando permisos de administrador..." -ForegroundColor Cyan

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "`nERROR: Se requieren permisos de administrador`n" -ForegroundColor Red
    exit 1
}

Write-Host "  OK Permisos confirmados" -ForegroundColor Green

Write-Host "`n[3/3] Instalando Docker Desktop..." -ForegroundColor Cyan

$chocoExists = $false
$checkChoco = choco --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK Chocolatey encontrado" -ForegroundColor Green
    $chocoExists = $true
} else {
    Write-Host "  Instalando Chocolatey..." -ForegroundColor Yellow
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    $chocoExists = $?
}

if (-not $chocoExists) {
    Write-Host "  ERROR al instalar Chocolatey`n" -ForegroundColor Red
    exit 1
}

Write-Host "  Descargando Docker Desktop..."
Write-Host "  Esto puede tardar 10-20 minutos, espera sin cerrar PowerShell`n"

choco install docker-desktop -y --force --no-progress

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n  OK Docker Desktop instalado correctamente" -ForegroundColor Green
} else {
    Write-Host "`n  ADVERTENCIA: Docker podria necesitar reinicio" -ForegroundColor Yellow
}

Write-Host "`nINSTALACION COMPLETADA`n" -ForegroundColor Green

Write-Host "Proximos pasos:`n" -ForegroundColor Cyan
Write-Host "  1. Docker Desktop se abrira automaticamente"
Write-Host "  2. Espera a que este listo (veras el icono en la bandeja)"
Write-Host "  3. Si necesita reinicio, reinicia Windows"
Write-Host "  4. Luego abre PowerShell y ejecuta:`n"
Write-Host "     docker-compose up -d`n" -ForegroundColor Yellow

Write-Host "Tu sistema estara disponible en:"
Write-Host "  Frontend: http://localhost"
Write-Host "  Backend: http://localhost:8000`n"
