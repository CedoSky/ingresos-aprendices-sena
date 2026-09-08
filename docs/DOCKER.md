# 🐳 DOCKER — Sistema de Ingresos SENA

Guía completa para ejecutar el sistema completo con Docker.

## 📋 Requisitos Previos

- **Docker:** 20.10+ ([descargar](https://www.docker.com/products/docker-desktop))
- **Docker Compose:** 1.29+ (incluido en Docker Desktop)
- **Git:** Para clonar el repositorio

### Verificar instalación

```bash
docker --version
docker-compose --version
```

---

## 🚀 Inicio Rápido

### 1. Configurar Variables de Entorno

```bash
# Copiar template de .env
cp .env.docker .env

# Editar .env con tus valores (importante para producción)
nano .env
```

**Cambios mínimos requeridos en .env:**
- `POSTGRES_PASSWORD` — Contraseña segura para BD
- `SECRET_KEY` — Clave secreta para Flask
- `JWT_SECRET_KEY` — Clave para JWT tokens

Generar claves seguras:
```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
```

### 2. Construir Imagen Docker

```bash
# Construir (puede tomar 10-15 minutos la primera vez)
docker-compose build

# O usar Makefile (si tienes instalado)
make build
```

### 3. Iniciar Servicios

```bash
# Iniciar en background
docker-compose up -d

# O ver logs en consola (ctrl+c para salir)
docker-compose up
```

### 4. Verificar que Todo Funciona

```bash
# Ver estado
docker-compose ps

# Verificar salud
docker-compose exec api curl http://localhost:8000/health
```

### 5. Acceder a la Aplicación

- **Frontend:** http://localhost
- **Backend API:** http://localhost:8000
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

**Credenciales por defecto:**
- Email: `admin@sena.edu.co`
- Password: `admin123`

---

## 🔧 Comandos Útiles

### Gestión de Servicios

```bash
# Ver estado de todos los servicios
docker-compose ps

# Detener servicios
docker-compose down

# Reiniciar servicios
docker-compose restart

# Ver logs en tiempo real
docker-compose logs -f api

# Ver logs de un servicio específico
docker-compose logs -f api        # Backend
docker-compose logs -f web        # Frontend/Nginx
docker-compose logs -f postgres   # Base de datos
docker-compose logs -f redis      # Cache
```

### Acceso a Contenedores

```bash
# Shell del API
docker-compose exec api sh

# PostgreSQL CLI
docker-compose exec postgres psql -U sena_user -d sena_aprendices

# Redis CLI
docker-compose exec redis redis-cli

# Nginx shell
docker-compose exec web sh
```

### Base de Datos

```bash
# Hacer backup
docker-compose exec postgres pg_dump -U sena_user sena_aprendices > backup.sql

# Restaurar backup
cat backup.sql | docker-compose exec -T postgres psql -U sena_user sena_aprendices

# Acceder a la BD
docker-compose exec postgres psql -U sena_user -d sena_aprendices
```

### Python/Flask

```bash
# Ejecutar migraciones
docker-compose exec api flask db migrate
docker-compose exec api flask db upgrade

# Crear usuario administrador
docker-compose exec api python -c "from backend.models import User; User.create_default_admin()"

# Ejecutar pruebas
docker-compose exec api python -m pytest tests/

# Instalar paquete nuevo
docker-compose exec api pip install nuevo_paquete
```

### Limpieza

```bash
# Detener y eliminar contenedores (mantiene volúmenes)
docker-compose down

# Eliminar TODO incluyendo datos (⚠️ DESTRUCTIVO)
docker-compose down -v

# Limpiar imágenes no usadas
docker system prune -f

# Reconstruir sin cache
docker-compose build --no-cache
```

---

## 📊 Estructura de Servicios

```
┌─────────────────────────────────────────────────────┐
│                    NGINX (Puerto 80)                 │
│  Reverse Proxy + Frontend Estático (login, admin)   │
└────────────────┬────────────────────────────────────┘
                 │
                 ├─────────────────────────┬────────────────┐
                 ▼                         │                ▼
┌──────────────────────────────┐     ┌──────────────┐  ┌──────────────┐
│     Flask API (8000)         │     │   PostgreSQL │  │    Redis     │
│ - Autenticación JWT          │     │   (Base BD)  │  │   (Cache)    │
│ - SocketIO (tiempo real)     │     │              │  │              │
│ - Endpoints REST             │     └──────────────┘  └──────────────┘
│ - Seguridad integral         │
└──────────────────────────────┘
         │
         ▼
   ┌──────────────┐
   │   ESP32      │
   │ (Cerraduras) │
   └──────────────┘
```

---

## 🔒 Seguridad en Docker

### Variables Sensibles

**NUNCA** incluyas passwords en el código. Usa `.env`:

```bash
# ❌ MALO
docker-compose up -e POSTGRES_PASSWORD=12345

# ✅ BUENO
# Coloca en .env
POSTGRES_PASSWORD=your_secure_password_here
docker-compose up
```

### Redes Aisladas

El compose usa una red interna (`sena_network`):
- Los contenedores se comunican entre sí de forma segura
- El frontend es el único accesible desde afuera

### Volúmenes Seguros

```bash
# Ver volúmenes en uso
docker volume ls

# Inspeccionar volumen específico
docker volume inspect sena_postgres_data
```

---

## 📈 Escalado en Producción

### Para Producción con High Availability:

1. **Usar Docker Swarm o Kubernetes**
2. **Múltiples replicas del API**
3. **Load Balancer (HAProxy, Traefik)**
4. **PostgreSQL replicado**
5. **Certificados SSL/TLS**

Ejemplo con Traefik (simplificado):

```yaml
# docker-compose.prod.yml
version: '3.9'

services:
  traefik:
    image: traefik:v2.10
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"

  api:
    # ... config similar pero con labels de Traefik
    labels:
      - "traefik.http.routers.api.rule=Host(`api.sena.edu.co`)"
      - "traefik.http.services.api.loadbalancer.server.port=8000"
```

---

## 🐛 Troubleshooting

### Problema: "Port already in use"

```bash
# Solución: Buscar qué proceso usa el puerto
lsof -i :8000    # Linux/Mac
netstat -ano | findstr :8000  # Windows

# O cambiar puerto en .env
FLASK_PORT=8001
NGINX_PORT=8080
```

### Problema: "Cannot connect to database"

```bash
# Verificar que postgres está corriendo
docker-compose ps postgres

# Ver logs
docker-compose logs postgres

# Reconstruir
docker-compose down -v
docker-compose up
```

### Problema: "Out of disk space"

```bash
# Limpiar imágenes/contenedores no usados
docker system prune -a

# Ver uso de espacio
docker system df
```

### Problema: Los cambios en el código no se reflejan

```bash
# Asegúrate de que el código está en un volumen
# En docker-compose.yml: volumes: - ./backend:/app

# Reiniciar el contenedor
docker-compose restart api
```

---

## 📚 Recursos Adicionales

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

## 💡 Tips & Tricks

### Usar Makefile (si tienes make instalado)

```bash
make help          # Ver todos los comandos
make up            # Iniciar
make logs-api      # Ver logs del API
make shell-api     # Entrar a shell
make clean         # Limpiar todo
```

### Monitorar en tiempo real

```bash
# En una terminal
docker-compose logs -f api

# En otra terminal
docker stats
```

### Ejecutar comando único

```bash
docker-compose exec api python -c "print('Hola desde Docker')"
```

### Ver recursos usados

```bash
docker stats --no-stream
```

---

## 📝 Licencia y Contacto

Sistema SENA © 2026
Para soporte: dev@sena.edu.co
