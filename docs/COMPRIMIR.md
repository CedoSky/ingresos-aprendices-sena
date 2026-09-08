# 📦 COMPRIMIR EL PROYECTO

Guía para comprimir correctamente el sistema SENA **CON Docker incluido**.

---

## 🎯 ¿Qué se Incluye en la Compresión?

✅ **INCLUIR (Todo esto debe ir):**
```
docker-compose.yml          ← IMPORTANTE
Dockerfile (backend)        ← IMPORTANTE  
Dockerfile.frontend         ← IMPORTANTE
.dockerignore
.env.docker                 ← Plantilla variables
docker/                     ← Configuración Nginx
backend/                    ← Código fuente
frontend/                   ← Interfaces HTML
Arduino/                    ← Código ESP32
scripts/                    ← Scripts utilities
tests/                      ← Pruebas
docs/                       ← Documentación
README.md
DOCKER_SETUP.md
setup-docker.bat
Makefile
```

❌ **EXCLUIR (No incluir):**
```
.venv/                      ← Entorno virtual (peso innecesario)
__pycache__/                ← Cache Python
.pytest_cache/              ← Cache pruebas
*.log                       ← Archivos log
instance/                   ← BD local (se regenera)
RESPALDOS_USB/              ← Respaldos locales
.git/                       ← Control de versiones
node_modules/               ← Si existe
.env                        ← Valores sensibles (usar .env.docker)
```

---

## 🚀 Pasos para Comprimir

### Paso 1: Limpiar Proyecto

Ejecuta este script antes de comprimir (elimina archivos innecesarios):

```batch
prepare-for-compression.bat
```

Esto limpia:
- `__pycache__/` — Cache Python
- `.pytest_cache/` — Cache de pruebas
- `*.log` — Archivos de log
- `node_modules/` — Dependencias Node (si existen)

**Resultado:** Reduce tamaño 50-70%

---

### Paso 2: Comprimir

#### Opción A: Windows (WinRAR o 7-Zip)

```powershell
# Click derecho en la carpeta
# → Enviar a → Carpeta comprimida (ZIP)
# O con 7-Zip: → 7-Zip → Agregar al archivo

# O por PowerShell:
Compress-Archive -Path "C:\Users\AMAT\...\ingresos aprendices 7" `
                 -DestinationPath "proyecto-sena.zip"
```

#### Opción B: Con 7-Zip (Más compresión)

```powershell
# Instalar si no tienes
choco install 7zip

# Comprimir
7z a proyecto-sena.7z "ruta\a\carpeta"
```

#### Opción C: PowerShell avanzado (excluyendo archivos)

```powershell
# Crear función
function Compress-SENA {
    $source = "C:\Users\AMAT\...\ingresos aprendices 7"
    $destination = "proyecto-sena.zip"
    
    $exclude = @('.venv', '__pycache__', '.pytest_cache', '*.log', 
                 'instance', 'RESPALDOS_USB', '.git', 'node_modules')
    
    Get-ChildItem $source -Recurse | 
        Where-Object { -not ($_.FullName -match ($exclude -join '|')) } |
        Compress-Archive -DestinationPath $destination -Force
}

Compress-SENA
```

---

## 📊 Tamaño Esperado

```
SIN limpiar:   300-500 MB  (mucho caché, .venv, etc)
LIMPIO:        50-100 MB   (solo código necesario + Docker config)
```

Al comprimir:
````
ZIP:           20-40 MB
7z:            10-20 MB
```

---

## 📋 Checklist Antes de Comprimir

- [ ] Ejecutaste `prepare-for-compression.bat`
- [ ] Verificaste que `docker-compose.yml` está presente
- [ ] Verificaste que `Dockerfile` y `Dockerfile.frontend` están presentes
- [ ] Copiaste `.env.docker` (para que recepción sepa quéconfigar)
- [ ] NO incluiste `.env` (solo `.env.docker`)
- [ ] NO incluiste `instance/` con BD local
- [ ] NO incluiste `.venv/` (está en .gitignore)
- [ ] Documentación incluida (DOCKER.md, DOCKER_SETUP.md)

---

## 🎯 Archivo Final

```
proyecto-sena.zip (o .7z)
│
├── docker-compose.yml          ✅
├── Dockerfile.frontend          ✅
├── .dockerignore                ✅
├── .env.docker                  ✅  ← Ellos copian a .env
├── setup-docker.bat             ✅
├── Makefile                     ✅
│
├── backend/
│   ├── Dockerfile              ✅
│   ├── app.py
│   ├── models.py
│   ├── requirements.txt         ✅
│   └── ...
│
├── frontend/
│   ├── login.html
│   ├── administracion.html
│   └── ...
│
├── docs/
│   ├── DOCKER.md               ✅
│   ├── DOCKER-CHEAT-SHEET.md   ✅
│   └── ...
│
└── README.md                    ✅
```

---

## 📤 Para Compartir

```bash
# 1. Limpiar
prepare-for-compression.bat

# 2. Comprimir
Compress-Archive -Path "carpeta" -DestinationPath "proyecto-sena.zip"

# 3. Enviar archivo proyecto-sena.zip

# Receptor descomprime y ejecuta:
docker-compose up -d
```

---

## ✅ Ya Está Todo Listo

El proyecto **YA TIENE TODO INCLUIDO**:
- ✅ Docker configurado
- ✅ Todos los archivos necesarios
- ✅ `.gitignore` actualizado
- ✅ Script de limpieza (`prepare-for-compression.bat`)
- ✅ Documentación completa

**Solo falta comprimir.**

---

## 🚀 Comando Rápido (Todo en Uno)

```powershell
# Limpiar y comprimir en un go
.\prepare-for-compression.bat; `
Compress-Archive -Path "." -DestinationPath "..\proyecto-sena.zip" -Force
```

---

## 📝 Nota Importante

`Docker está dentro del .zip`. Cuando el receptor lo descomprima y ejecute `docker-compose up -d`, Docker construirá las imágenes automáticamente.

**No necesita instalar nada más que Docker Desktop.**

---

** ¡Listo para compartir! 🎉**
