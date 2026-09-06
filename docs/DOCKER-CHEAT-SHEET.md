# 🐳 DOCKER CHEAT SHEET — Referencia Rápida

## ⚙️ Configuración Inicial

```bash
# 1. Copiar .env
cp .env.docker .env

# 2. Editar con valores seguros
nano .env   # O notepad .env en Windows

# 3. Generar claves (ejecuta en Python)
python -c "import secrets; print(secrets.token_hex(32))"

# 4. Construir imagen
docker-compose build

# 5. Iniciar servicios
docker-compose up -d
```

---

## 🚀 Comandos Frecuentes

| Comando | Descripción |
|---------|-------------|
| `docker-compose up -d` | Iniciar servicios en background |
| `docker-compose down` | Detener servicios |
| `docker-compose ps` | Ver estado |
| `docker-compose logs -f api` | Ver logs en tiempo real |
| `docker-compose restart api` | Reiniciar API |
| `docker-compose exec api sh` | Entrar a shell del API |

---

## 🔍 Debugging

```bash
# Ver logs últimas 50 líneas
docker-compose logs --tail=50 api

# Ver logs con timestamp
docker-compose logs --timestamps -f api

# Ver estado completo
docker-compose exec api python -c "import sys; print(sys.version)"

# Verificar conectividad a BD
docker-compose exec api python -c "from backend.models import db; db.session.execute('SELECT 1')"

# Listar variables de entorno
docker-compose exec api env | grep DATABASE
```

---

## 📦 Base de Datos

```bash
# Conectar a PostgreSQL
docker-compose exec postgres psql -U sena_user -d sena_aprendices

# Comando SQL rápido
docker-compose exec postgres psql -U sena_user -d sena_aprendices -c "SELECT COUNT(*) FROM usuario;"

# Backup completo
docker-compose exec postgres pg_dump -U sena_user sena_aprendices > backup.sql

# Restaurar backup
cat backup.sql | docker-compose exec -T postgres psql -U sena_user sena_aprendices

# Limpiar BD (cuidado)
docker-compose exec postgres psql -U sena_user -d sena_aprendices -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

---

## 🧹 Cache/Redis

```bash
# Conectar a Redis
docker-compose exec redis redis-cli

# Tests en Redis CLI
> PING
> SET key "value"
> GET key
> FLUSHALL    # Limpiar TODO (⚠️)

# Ver memoria usada
docker-compose exec redis redis-cli INFO MEMORY
```

---

## 📝 Python/Flask

```bash
# Ejecutar comando Python
docker-compose exec api python manage.py migrate

# Instalar paquete nuevo
docker-compose exec api pip install nuevo_paquete

# Compilar requirements.txt
docker-compose exec api pip freeze > requirements.txt

# Ejecutar pruebas
docker-compose exec api python -m pytest tests/ -v

# Crear usuario admin
docker-compose exec api python -c "from models import User; User.create_admin('email@example.com', 'password')"
```

---

## 🌐 Nginx/Frontend

```bash
# Ver configuración Nginx
docker-compose exec web cat /etc/nginx/conf.d/default.conf

# Test configuración Nginx
docker-compose exec web nginx -t

# Recargar configuración (sin reiniciar)
docker-compose exec web nginx -s reload

# Ver logs de acceso
docker-compose exec web tail -f /var/log/nginx/access.log
```

---

## 🔐 Seguridad

```bash
# Cambiar contraseña PostgreSQL
docker-compose stop postgres
# Editar en docker-compose.yml
# docker-compose up -d

# Ver variables sensibles en contenedor (cuidado)
docker-compose exec api env | grep -E "SECRET|PASSWORD|KEY"

# Escanear vulnerabilidades en imagen
docker scan sena_api:latest
```

---

## 📊 Monitoreo

```bash
# Ver recursos en tiempo real
docker stats

# Historial de cambios
docker system df

# Eventos en vivo
docker events --filter type=container

# Inspeccionar volumen
docker volume inspect sena_postgres_data
```

---

## 🐛 Problemas Comunes

### Puerto en uso
```bash
# Windows PowerShell
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

### Volumen no sincroniza
```bash
docker-compose down
docker volume prune
docker-compose up
```

### PostgreSQL no inicia
```bash
docker-compose logs postgres
docker-compose down -v
docker-compose up
```

### API lento
```bash
docker stats api                    # Ver CPU/memoria
docker-compose logs api | tail -20  # Ver errores
```

---

## 🗂️ Estructura de Volúmenes

```bash
# Ver volúmenes
docker volume ls

# Localización física (Linux)
ls /var/lib/docker/volumes/

# Limpiar volúmenes huérfanos
docker volume prune

# Respaldar volumen
docker run --rm -v sena_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/db-backup.tar.gz -C /data .
```

---

## 🚢 Deploy Quick Reference

```bash
# Modo producción
FLASK_ENV=production docker-compose up -d

# Con logs de diagnóstico
docker-compose up --remove-orphans

# Limpiar antes de deploy
docker system prune -af

# Health check
curl http://localhost/health
curl http://localhost:8000/health
```

---

## 📞 Ayuda

```bash
# Ver versiones
docker-compose version
docker --version

# Help
docker-compose --help
docker-compose logs --help

# Documentación
https://docs.docker.com/
https://docs.docker.com/compose/
```

---

**Guarda este documento para acceso rápido: `docker-cheat-sheet.md`**
