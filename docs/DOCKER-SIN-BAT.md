# 🔧 DOCKER SETUP SIN .BAT — Alternativas Directas

Si el `setup-docker.bat` tiene error o prefieres no usarlo, aquí están las formas directas:

---

## ✅ Opción 1: Método Manual (Más Control)

### Paso 1: Crear .env

```powershell
# Copiar template
Copy-Item .env.docker .env

# Editar valores (abrir en Notepad)
notepad .env
```

**Valores importantes a cambiar en .env:**
```
POSTGRES_PASSWORD=tu_contraseña_segura
SECRET_KEY=tu_clave_secreta_aqui
JWT_SECRET_KEY=tu_jwt_secreto_aqui
```

### Paso 2: Construir

```powershell
docker-compose build
```

Este paso:
- ✅ Descarga imagen base de Python
- ✅ Instala dependencias de requirements.txt
- ✅ Descarga Nginx base
- ✅ Prepara todo

Toma 5-10 minutos la primera vez.

### Paso 3: Iniciar

```powershell
docker-compose up -d
```

Este comando:
- ✅ Crea contenedores
- ✅ Inicia PostgreSQL
- ✅ Inicia Redis
- ✅ Inicia Flask
- ✅ Inicia Nginx

### Paso 4: Verificar

```powershell
# Ver estado
docker-compose ps

# Acceder a
http://localhost

# Ver logs (por si hay error)
docker-compose logs -f api
```

---

## ✅ Opción 2: Con Makefile (Recomendado)

Si tienes `make` instalado:

```powershell
# Setup automático
make setup

# Construir
make build

# Iniciar
make up

# Ver status
make status
```

---

## ✅ Opción 3: PowerShell Script (Sin .bat)

Copia esto en PowerShell:

```powershell
# SETUP DOCKER - Opción PowerShell

# 1. Crear .env
if (-not (Test-Path .env)) {
    Copy-Item .env.docker .env
    Write-Host "✓ .env creado. Por favor edita valores sensibles."
    notepad .env
}

# 2. Construir imagen
Write-Host "Construyendo imágenes Docker..." -ForegroundColor Cyan
docker-compose build

# 3. Iniciar servicios
Write-Host "Iniciando servicios..." -ForegroundColor Cyan
docker-compose up -d

# 4. Esperar y verificar
Start-Sleep -Seconds 5
Write-Host "`nVerificando servicios..." -ForegroundColor Green
docker-compose ps

Write-Host "`n✅ LISTO!" -ForegroundColor Green
Write-Host "Accede a: http://localhost" -ForegroundColor Yellow
```

Guarda como `setup-docker.ps1` y ejecuta:
```powershell
.\setup-docker.ps1
```

---

## ❌ Errores Comunes y Soluciones

### Error: "Docker command not found"
```
✓ Solución: Instala Docker Desktop
  https://www.docker.com/products/docker-desktop
```

### Error: "Port 80 already in use"
```
# Encuentra qué usa puerto 80
netstat -ano | findstr :80

# Mata el proceso
taskkill /PID <numero> /F

# O cambia puerto en .env
NGINX_PORT=8080
```

### Error: "Cannot connect to database"
```
# Espera más tiempo e intenta de nuevo
docker-compose down
docker-compose up -d
docker-compose logs postgres
```

### Error: "Out of disk space"
```
# Limpia Docker
docker system prune -a
docker volume prune
```

---

## 🚨 Si Aún Hay Error

Dime:
1. **¿Qué error exacto ves?** (copia el mensaje)
2. **¿En qué paso?** (build, up, después de iniciar, etc)
3. **¿Qué comando ejecutaste?**

Ejemplo:
```
Ejecuté: docker-compose up -d
Error: ERROR: The Compose file is invalid because:
services.postgres.image: image size too large
```

---

## 💡 Resumen

| Método | Dificultad | Recomendado |
|--------|-----------|-------------|
| Manual (Opción 1) | ⭐⭐⭐ | Máximo control |
| Makefile (Opción 2) | ⭐ | Si tienes make |
| PowerShell (Opción 3) | ⭐⭐ | Automático puro |
| setup-docker.bat | ⭐ | Originally intended |

**Elige UNA de las opciones anteriores** y prueba. Si hay error, dímelo.
