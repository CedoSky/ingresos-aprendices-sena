# ════════════════════════════════════════════════════════════════════════════
# INSTALADOR AUTOMÁTICO DE DOCKER
# Sistema de Control de Ingresos SENA
# ════════════════════════════════════════════════════════════════════════════

Write-Host "`n╔════════════════════════════════════════════════════════════════╗"
Write-Host "  INSTALADOR AUTOMÁTICO DE DOCKER"
Write-Host "╚════════════════════════════════════════════════════════════════╝`n"

# ─────────────────────────────────────────────────────────────────────────────
# PASO 1: Verificar si Docker ya está instalado
# ─────────────────────────────────────────────────────────────────────────────

Write-Host "[1/3] Verificando si Docker está instalado..." -ForegroundColor Cyan

$dockerExists = $false
$dockerVersion = ""

# Intentar obtener versión de Docker
$checkDocker = docker --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Docker encontrado: $checkDocker" -ForegroundColor Green
    $dockerExists = $true
} else {
    Write-Host "  ✗ Docker no encontrado" -ForegroundColor Yellow
}

if ($dockerExists) {
    Write-Host "`n✓ Docker ya está instalado.`n" -ForegroundColor Green
    exit 0
}

# ─────────────────────────────────────────────────────────────────────────────
# PASO 2: Verificar permisos de administrador
# ─────────────────────────────────────────────────────────────────────────────

Write-Host "[2/3] Verificando permisos de administrador..." -ForegroundColor Cyan

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "`n  ✗ ERROR: Se requieren permisos de administrador" -ForegroundColor Red
    Write-Host "`n  Solución: Ejecuta este script como Administrador" -ForegroundColor Yellow
    Write-Host "`n  1. Click derecho en PowerShell"
    Write-Host "  2. Selecciona 'Ejecutar como administrador'"
    Write-Host "  3. Ejecuta de nuevo este script`n"
    exit 1
}

Write-Host "  ✓ Permisos de administrador confirmados" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────────────
# PASO 3: Instalar Chocolatey e Docker
# ─────────────────────────────────────────────────────────────────────────────

Write-Host "`n[3/3] Instalando Docker Desktop..." -ForegroundColor Cyan

# Verificar Chocolatey
$chocoExists = $false
$checkChoco = choco --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Chocolatey encontrado" -ForegroundColor Green
    $chocoExists = $true
} else {
    Write-Host "  Instalando Chocolatey..." -ForegroundColor Yellow
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    $chocoExists = $?
}

if (-not $chocoExists) {
    Write-Host "  ✗ Error al instalar Chocolatey`n" -ForegroundColor Red
    Write-Host "  Descarga Docker manualmente desde: https://www.docker.com/products/docker-desktop`n"
    exit 1
}

# Instalar Docker
Write-Host "  Descargando Docker Desktop..."
Write-Host "  (Esta operación puede tardar 5-15 minutos, espera sin cerrar PowerShell)`n"

choco install docker-desktop -y --force --no-progress

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n  ✓ Docker Desktop instalado correctamente" -ForegroundColor Green
} else {
    Write-Host "`n  ⚠ Docker instalado, pero puede necesitar verificationación" -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────────────────────────────────
# PASO FINAL: Mensaje de éxito
# ─────────────────────────────────────────────────────────────────────────────

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ✓ INSTALACIÓN COMPLETADA" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "Próximos pasos:`n" -ForegroundColor Cyan
Write-Host "  1. Docker Desktop se abrirá automáticamente"
Write-Host "  2. Espera a que esté listo (verás el ícono en la bandeja)"
Write-Host "  3. Si necesita reinicio, reinicia Windows"
Write-Host "  4. Luego abre PowerShell y ejecuta:`n"
Write-Host "     docker-compose up -d`n" -ForegroundColor Yellow

Write-Host "Tu sistema estará corriendo en:"
Write-Host "  Frontend: http://localhost"
Write-Host "  Backend: http://localhost:8000"
