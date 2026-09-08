# 📦 Guía de Instalación

Instruções paso a paso para instalar el Sistema de Control de Ingresos SENA.

---

## 📋 Tabla de Contenidos

- [Requisitos Previos](#requisitos-previos)
- [Instalación Rápida (Docker)](#instalación-rápida-docker)
- [Instalación Local](#instalación-local)
- [Configuración de Base de Datos](#configuración-de-base-de-datos)
- [Configuración de Email](#configuración-de-email)
- [Configuración de MQTT](#configuración-de-mqtt)
- [Verificación](#verificación)
- [Troubleshooting](#troubleshooting)

---

## ✅ Requisitos Previos

### Windows

- **Docker Desktop** (Windows 10/11)
  - Descargar: https://www.docker.com/products/docker-desktop
  - Requiere Hyper-V o WSL2
  
- **Git** 
  - Descargar: https://git-scm.com/download/win
  
- **PowerShell 7+** (Recomendado)
  - O usar PowerShell integrado de Windows

- **Espacio en disco:** 5GB mínimo

### Linux / Mac

```bash
# Debian/Ubuntu
sudo apt-get install docker.io docker-compose git python3 python3-pip

# macOS (con Homebrew)
brew install docker docker-compose git python3
```

---

## 🚀 Instalación Rápida (Docker)

### Paso 1: Clonar Repositorio

```bash
# Abrir PowerShell en carpeta destino
cd C:\Proyectos

# Clonar repo
git clone https://github.com/tu-usuario/sistema-ingresos-sena.git
cd sistema-ingresos-sena
```

### Paso 2: Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
copy .env.example .env

# Editar .env con valores reales
# (Abre con Notepad o VSCode)
```

**Valores importantes en .env:**

```bash
# Flask
FLASK_ENV=production
FLASK_APP=backend/app.py
SECRET_KEY=tu-clave-secreta-super-larga

# Database
DATABASE_URL=sqlite:///datos.db

# SMTP (para emails)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=tu-email@gmail.com
MAIL_PASSWORD=tu-contraseña-app

# MQTT
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=admin
MQTT_PASSWORD=mosquitto
```

### Paso 3: Ejecutar Setup Automático

```bash
# Como administrador en PowerShell
./DOCKER_SETUP.bat
```

**El script hará:**
1. ✅ Verifica Docker
2. ✅ Descarga imágenes
3. ✅ Crea contenedores
4. ✅ Inicializa base de datos
5. ✅ Inicia servicios

### Paso 4: Verificar Instalación

```bash
# Espera 30 segundos a que inicie
# Abre en navegador:

Frontend:     http://localhost
Backend API:  http://localhost:8000
Admin:        http://localhost/admin
API Docs:     http://localhost:8000/api/docs
```

**Credenciales de Demo:**
- Email: `admin@sena.edu.co`
- Password: `Admin@2024`

---

## 🛠️ Instalación Local

### Para Desarrollo

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/sistema-ingresos-sena.git
cd sistema-ingresos-sena

# 2. Crear entorno virtual
python -m venv .venv

# 3. Activar entorno
# Windows:
.\.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Copiar archivo de configuración
copy .env.example .env
# Editar .env con valores locales

# 6. Inicializar base de datos
python backend/init_db.py

# 7. Ejecutar backend
python backend/app.py
# El servidor estará en http://localhost:8000

# 8. En otra terminal (con .venv activado):
cd frontend
python -m http.server 8080
# Frontend en http://localhost:8080
```

---

## 🗄️ Configuración de Base de Datos

### Inicialización Automática

```bash
# Crear tablas automáticamente
python backend/init_db.py

# Generar datos de prueba
python backend/populate_data.py
```

### Migración Manual de Datos

```bash
# Si tienes datos en otro sistema
python backend/import_data.py --source old_system.csv
```

---

## 📧 Configuración de Email

### Con Gmail

1. **Habilitar acceso de app:**
   - Ve a https://myaccount.google.com/apppasswords
   - Selecciona "Mail" y "Windows Computer"
   - Copia contraseña de aplicación

2. **Actualizar .env:**
```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=tu-email@gmail.com
MAIL_PASSWORD=contraseña-app-generada
```

3. **Probar conexión:**
```bash
python backend/test_mail.py
```

### Con Otros Servidores SMTP

**Outlook:**
```bash
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USERNAME=tu-email@outlook.com
MAIL_PASSWORD=tu-contraseña
```

**Sendgrid:**
```bash
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USERNAME=apikey
MAIL_PASSWORD=tu-api-key
```

---

## 🔗 Configuración de MQTT

### Usando Broker Local (Mosquitto)

**En Docker (automático):**
```
El servicio MQTT se inicia automáticamente.
```

**En Windows Local:**

```bash
# 1. Descargar Mosquitto
# https://mosquitto.org/download/

# 2. Instalar
msiexec /i mosquitto-2.0.18-install-windows-x64.msi

# 3. Iniciar servicio
net start mosquitto

# 4. Actualizar .env
MQTT_BROKER=127.0.0.1
MQTT_PORT=1883
MQTT_USERNAME=admin
MQTT_PASSWORD=password
```

### Usando Broker en la Nube

```bash
# HiveMQ Cloud (gratuito)
MQTT_BROKER=<tu-cluster>.hivemq.cloud
MQTT_PORT=8883
MQTT_USERNAME=tu-usuario
MQTT_PASSWORD=tu-contraseña
```

---

## 🧪 Verificación

### Health Check

```bash
# Verificar servicios
python backend/verify_services.py
```

**Debe mostrar:**
```
✅ Backend API: ONLINE
✅ Database: CONNECTED
✅ MQTT Broker: CONNECTED
✅ Email Service: OK
✅ Storage: OK
```

### Tests Rápidos

```bash
# Tests unitarios
pytest tests/ -v

# Tests de seguridad
pytest tests/test_security.py -v

# Tests de integración MQTT
pytest tests/test_mqtt.py -v
```

---

## ❌ Troubleshooting

### Docker no inicia

**Problema:** Error al iniciar Docker Desktop

**Solución:**
```bash
# 1. Reiniciar Docker Desktop
# 2. Limpiar contenedores
docker system prune -a

# 3. Reconstruir
docker-compose up --build -d
```

---

### Puerto 80 en uso

**Problema:** Error "Address already in use"

**Solución Windows:**
```bash
# Encontrar qué usa el puerto 80
netstat -ano | findstr :80

# Matar proceso (reemplaza PID)
taskkill /PID 4116 /F

# O cambiar puerto en docker-compose.yml:
# ports:
#   - "8080:80"
```

---

### Base de datos no responde

**Problema:** "Failed to connect to SQLite"

**Solución:**
```bash
# 1. Eliminar BD antigua
rm instance/datos.db

# 2. Reinicializar
python backend/init_db.py

# 3. Verificar permisos
icacls instance\ /grant:r "%USERNAME%:(OI)(CI)F"
```

---

### No puedo conectar con MQTT

**Problema:** "Connection refused - MQTT Broker"

**Solución:**
```bash
# 1. Verificar MQTT está corriendo
docker ps | grep mosquitto

# 2. Si no está, reiniciar
docker-compose restart mosquitto

# 3. Probar conexión
python backend/test_mqtt_connection.py

# 4. Verificar credenciales en .env
```

---

### Frontend no carga

**Problema:** Página en blanco o error 404

**Solución:**
```bash
# 1. Verificar Nginx
docker-compose logs nginx

# 2. Reconstruir frontend
docker-compose build frontend

# 3. Reiniciar
docker-compose restart nginx

# 4. Limpiar cache navegador (Ctrl+F5)
```

---

### Login no funciona

**Problema:** "Usuario no encontrado" con admin@sena.edu.co

**Solución:**
```bash
# 1. Verificar usuario existe
python -c "from backend.models import Usuario; print(Usuario.query.filter_by(email='admin@sena.edu.co').first())"

# 2. Si no existe, crear
python backend/create_admin_user.py

# 3. Resetear contraseña
python backend/reset_password.py admin@sena.edu.co
```

---

### Permisos denegados en Linux

**Problema:** Permission denied al ejecutar scripts

**Solución:**
```bash
# Dar permisos ejecutables
chmod +x *.sh
chmod +x *.py

# O usar Python directamente
python script.py
```

---

## 🔄 Actualización del Proyecto

```bash
# Obtener últimos cambios
git pull origin develop

# Actualizar dependencias
pip install -r requirements.txt --upgrade

# Reiniciar servicios
docker-compose restart

# Ejecutar migraciones si aplica
python backend/migrate.py
```

---

## 🛡️ Post-Instalación

### 1. **Cambiar Contraseña Admin**

```bash
python backend/reset_password.py admin@sena.edu.co
```

### 2. **Habilitar Backups**

```bash
# En .env
BACKUP_ENABLED=true
BACKUP_INTERVAL=3600  # Cada hora
BACKUP_DESTINATION=/mnt/backups
```

### 3. **Configurar HTTPS**

```bash
# Generar certificados
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Usar en nginx.conf
ssl_certificate /etc/nginx/cert.pem;
ssl_certificate_key /etc/nginx/key.pem;
```

### 4. **Habilitar 2FA**

```bash
# En panel de administración:
Admin → Usuarios → Seleccionar usuario → Habilitar 2FA
```

---

## 📞 Soporte

Si tienes problemas:

1. **Consulta la documentación:** [docs/](docs/)
2. **Busca issues:** GitHub Issues
3. **Revisa logs:** 
   ```bash
   docker-compose logs backend
   docker-compose logs nginx
   ```

---

**Última actualización:** Enero 2025
