# 🐳 INSTALACIÓN Y EJECUCIÓN CON DOCKER

## ⚡ TL;DR (Lo más rápido)

```bash
# 1. Si no tienes Docker instalado:
INSTALAR_DOCKER.bat

# 2. Cuando termine, abre Docker Desktop desde Inicio
# (Espera que esté listo - verás el ícono en la bandeja)

# 3. Luego ejecuta:
INICIAR_DOCKER.bat

# Listo. Tu sistema funciona en http://localhost
```

---

## 📋 GUÍA PASO A PASO

### Paso 1: Instalar Docker

**Opción A - Automática (RECOMENDADO):**

1. Abre **cmd.exe o PowerShell como administrador**:
   - Click derecho en cmd/PowerShell
   - Selecciona "Ejecutar como administrador"

2. Navega a tu carpeta del proyecto:
   ```bash
   cd "C:\ruta\a\tu\proyecto"
   ```

3. Ejecuta:
   ```bash
   INSTALAR_DOCKER.bat
   ```

4. **Espera a que termine** (10-20 minutos)

**Opción B - Manual:**

- Descarga desde: https://www.docker.com/products/docker-desktop
- Ejecuta el instalador
- Reinicia Windows
- Docker Desktop se abre automáticamente

---

### Paso 2: Iniciar Docker Desktop

Después de instalar, **Docker Desktop debe estar corriendo**:

1. Abre desde Inicio → "Docker Desktop"
2. Verifica que esté listo (ícono en la bandeja superior)
3. Espera 30 segundos

---

### Paso 3: Ejecutar el Sistema

Abre cmd/PowerShell y ejecuta:

```bash
INICIAR_DOCKER.bat
```

Esto:
- ✅ Inicia PostgreSQL (base de datos)
- ✅ Inicia Redis (caché)
- ✅ Inicia Backend (API en puerto 8000)
- ✅ Inicia Frontend (Nginx en puerto 80)

---

## 🌐 Acceso al Sistema

Una vez corriendo, accede a:

| Servicio | URL | Usuario | Contraseña |
|----------|-----|---------|-----------|
| **Frontend** | http://localhost | admin | (login) |
| **Backend** | http://localhost:8000 | - | - |
| **API Docs** | http://localhost:8000/docs | - | - |
| **Base de datos** | localhost:5432 | sena_user | sena_secure_password_2026 |

Credenciales de prueba:
- **Email**: admin@sena.edu.co
- **Contraseña**: admin123

---

## 🛑 Detener el Sistema

Para parar todos los servicios:

```bash
docker-compose down
```

Para parar y eliminar volúmenes (borra datos):

```bash
docker-compose down -v
```

---

## 🔍 Comandos Útiles

```bash
# Ver estado de los servicios
docker-compose ps

# Ver logs
docker-compose logs -f backend

# Reiniciar un servicio
docker-compose restart backend

# Entrar a la base de datos
docker-compose exec postgres psql -U sena_user -d sena_aprendices

# Limpiar todo
docker-compose down -v
docker system prune -a
```

---

## 🆘 Problemas Comunes

### "Docker no está instalado"
→ Ejecuta: `INSTALAR_DOCKER.bat` (como administrador)

### "Port 80 already in use"
→ Otro programa usa el puerto. Soluciones:
1. Detén el programa (normalmente es Skype, IIS, etc)
2. O cambia en `docker-compose.yml`:
   ```yaml
   ports:
     - "8080:80"  # En lugar de "80:80"
   ```

### "Docker Daemon not running"
→ Abre Docker Desktop desde Inicio y espera que esté listo

### "Permisos denegados"
→ Ejecuta como administrador (click derecho)

---

## 📦 Lo que incluye

El `docker-compose.yml` inicia:

- **PostgreSQL 16** — Base de datos principal
- **Redis 7** — Cache y sesiones
- **Flask + Gunicorn** — Backend API
- **Nginx** — Frontend + Reverse Proxy

Todos en una red privada, comunicados automáticamente.

---

## ✨ Ventajas de esta configuración

- ✅ **Reproducible** — Funciona igual en cualquier PC
- ✅ **Aislado** — No afecta tu sistema
- ✅ **Escalable** — Fácil de desplegar a producción
- ✅ **Versionado** — Control total en Git
- ✅ **Rápido** — Contenedores livianos

---

## 📚 Más información

- Documentación oficial: https://docs.docker.com/
- Guía de Docker Compose: https://docs.docker.com/compose/
- Estado del proyecto: [Estado actual de desarrollo]

---

**¿Preguntas?** Avísame si hay problema en cualquier paso.
