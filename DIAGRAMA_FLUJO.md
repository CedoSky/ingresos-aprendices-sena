# 🎓 Sistema Control de Ingresos SENA
## Diagrama de Flujo y Arquitectura del Sistema

**Versión:** 6-WithSecurity  
**Estado:** ✅ Operacional y Endurecido  
**Fecha:** 8 de Abril de 2026

---

## 📋 Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Tecnologías Utilizadas](#tecnologías-utilizadas)
3. [Módulos Principales](#módulos-principales)
4. [Medidas de Seguridad](#medidas-de-seguridad-implementadas)
5. [Estructura de Base de Datos](#estructura-de-base-de-datos)
6. [Flujos de Procesos Clave](#flujos-de-procesos-clave)
7. [Endpoints API](#principales-endpoints-api)
8. [Integración IoT](#integración-iot-esp32)
9. [Despliegue](#despliegue-e-instalación)
10. [Estructura de Carpetas](#estructura-de-carpetas)

---

## Descripción General

El **Sistema de Control de Ingresos SENA** es una solución integral para gestionar acceso a la institución educativa SENA. Integra:

- **Control de acceso físico** mediante cerradura electromagnética
- **Gestión completa de personas** (aprendices, instructores, visitantes)
- **Administración de usuarios** con roles y permisos
- **Procesamiento de pagos** y gestión de créditos
- **Generación de reportes** avanzados en Excel
- **Sincronización en tiempo real** con WebSocket

### 🎯 Características Principales

| Feature | Descripción |
|---------|------------|
| **👤 Gestión de Personas** | Registro y búsqueda de aprendices, instructores y visitantes |
| **🚪 Control de Acceso** | Cerradura electromagnética con ESP32 TRIAC y MQTT |
| **🔐 Seguridad Avanzada** | JWT, Encriptación Fernet, Auditoría, Prevención fuerza bruta |
| **💰 Sistema de Pagos** | Procesamiento de pagos y gestión de créditos |
| **📈 Reportes** | Exportación Excel de registros y estadísticas |
| **🔄 Sincronización** | Sincronización real-time con WebSocket |

---

## Tecnologías Utilizadas

| Capa | Tecnología | Versión |
|------|-----------|---------|
| **Backend** | Flask | 3.1.3 |
| **ORM** | SQLAlchemy | 2.0.48 |
| **Frontend** | HTML5 / JavaScript | Moderno |
| **Base Datos** | SQLite (dev) / PostgreSQL (prod) | Compatible |
| **Autenticación** | JWT / Fernet | Avanzada |
| **Messaging** | MQTT / WebSocket | Real-time |
| **IoT** | ESP32 TRIAC | Control Acceso |
| **Containerización** | Docker / Docker Compose | Moderno |
| **Email** | SMTP / SendGrid | Notificaciones |

---

## Módulos Principales

| Módulo | Archivo Principal | Función |
|--------|-------------------|----------|
| **Autenticación** | routes.py, security_shield.py | Login seguro, JWT, prevención fuerza bruta |
| **Gestión Personas** | routes.py, validaciones.py | CRUD de personas |
| **Control Acceso** | routes.py, mqtt_handler.py | Registro acceso, control TRIAC |
| **Administración** | panel_routes.py, gestionar_usuarios.py | Gestión usuarios y seguridad |
| **Pagos** | pagos.py | Procesamiento pagos, créditos |
| **Reportes** | export_excel.py | Generación Excel |
| **Sincronización** | sync_manager.py, websocket_handler.py | Sincronización real-time |
| **Base Datos** | models.py | Modelos SQLAlchemy |

---

## Medidas de Seguridad Implementadas

### 🔑 Autenticación y Autorización

- ✅ **JWT (JSON Web Tokens)** para autenticación sin estado
- ✅ **Sesiones seguras** con cookies HTTP-only
- ✅ **Control de acceso basado en roles** (Admin, Vigilante)
- ✅ **Validación JWT** en cada endpoint protegido
- ✅ **CSRF protection** con tokens y SameSite=Strict

### 🛡️ Protección contra Ataques

- ✅ **Fuerza Bruta:** Bloqueo de 15 minutos tras 5 intentos fallidos
- ✅ **CSRF:** Tokens CSRF y validación SameSite=Strict
- ✅ **SQL Injection:** SQLAlchemy ORM con queries parametrizadas
- ✅ **XSS:** Validación de entrada y sanitización
- ✅ **Rate Limiting:** Limitación de tasa de solicitudes API

### 🔒 Encriptación y Datos Sensibles

- ✅ **Fernet encryption** para datos sensibles en reposo
- ✅ **Hashing bcrypt** para contraseñas
- ✅ **HTTPS/TLS** para datos en tránsito (en producción)
- ✅ **Almacenamiento seguro** de credenciales en .env
- ✅ **Encriptación de emails** y datos personales

### 📊 Auditoría y Monitoreo

- ✅ **Sistema de auditoría** administrativo completo
- ✅ **Registro de eventos** de seguridad y acceso
- ✅ **Validación de configuración** de seguridad
- ✅ **Headers HTTP** de seguridad OWASP recomendados
- ✅ **Logs detallados** de todos los accesos

---

## Estructura de Base de Datos

### Entidades Principales

| Entidad | Descripción | Campos Clave |
|---------|-------------|--------------|
| **Usuario** | Administradores y vigilantes | email, password_hash, rol, activo |
| **Persona** | Aprendices, instructores, visitantes | nombre, tipo_doc, numero_doc, perfil, programa |
| **RegistroAcceso** | Log de entradas/salidas | persona_id, entry_time, exit_time, motivo |
| **Foto** | Fotografías de personas | persona_id, ruta_archivo, tipo |
| **Pago** | Transacciones de pago | usuario_id, monto, estado, fecha |
| **AuditoriaEvento** | Eventos administrativos | usuario_id, tipo_evento, detalles, timestamp |
| **Computador** | Equipos en red | nombre, ip, mac, area, estado |
| **Respaldo** | Backups del sistema | ruta, fecha, tamaño, tipo |

### Relaciones

```
Usuario ──┬──> AuditoriaEvento
          ├──> Pago
          └──> RegistroAcceso

Persona ──┬──> RegistroAcceso
          ├──> Foto
          └──> Pago
```

---

## Flujos de Procesos Clave

### 1️⃣ Flujo de Autenticación

```
┌─────────────┐
│ Usuario     │
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ Página de Login      │ (frontend/login.html)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Validar Entrada      │ (InputValidator)
│ ¿Fuerza Bruta?       │
└──────┬───────────────┘
       │
       ├─ SÍ ──> [Bloquear 15 min] ──> [Fallo]
       │
       └─ NO ──> [Verificar Password] ──> [Hash bcrypt]
                      │
                      ├─ Incorrecto ──> [Fallo]
                      │
                      └─ Correcto ──┐
                                    │
                                    ▼
                         ┌────────────────────┐
                         │ Generar JWT Token  │ (routes.py)
                         └────────┬───────────┘
                                  │
                                  ▼
                         ┌────────────────────┐
                         │ Crear Sesión       │ (SesionSegura)
                         │ Secure Cookies     │
                         └────────┬───────────┘
                                  │
                                  ▼
                         ┌────────────────────┐
                         │ Log Auditoría      │ (AuditoriaAdministrativa)
                         └────────┬───────────┘
                                  │
                                  ▼
                         ┌────────────────────┐
                         │ Dashboard Principal│ ✅
                         └────────────────────┘
```

### 2️⃣ Flujo de Control de Acceso

```
┌─────────────────────┐
│ Solicitud de Acceso │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Validar Horario     │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ ¿En Blacklist?      │
└──────┬──────────────┘
       │
       ├─ SÍ ──> [Acceso Denegado] ──> [Log Seguridad]
       │
       └─ NO ──> [Consultar Persona en BD]
                      │
                      ▼
                 ┌────────────────────┐
                 │ Crear RegistroAcceso│
                 └────────┬───────────┘
                          │
                          ▼
                 ┌────────────────────┐
                 │ Publicar MQTT      │ (mqtt_handler.py)
                 │ Topic: control/acceso
                 └────────┬───────────┘
                          │
                          ▼
                 ┌────────────────────┐
                 │ ¿ESP32 Disponible? │
                 └────┬────────────┬──┘
                      │            │
              SÍ ──────┘            └─────── NO
                      │                       │
                      ▼                       ▼
          ┌──────────────────────┐ ┌──────────────────┐
          │ ESP32 Activa TRIAC   │ │ Opción Manual    │
          │ (esp32_triac...)     │ │ (Panel Físico)   │
          └──────────┬───────────┘ └────────┬─────────┘
                     │                      │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │ Cerradura Se Abre    │ (ABIERTA 3-5 seg)
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │ Registrar Acceso     │ (entry_time)
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │ Notificar WebSocket  │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │ ✅ Acceso Concedido  │
                     └──────────────────────┘
```

### 3️⃣ Flujo de Registro de Personas

```
┌────────────────┐
│ Formulario     │
└────────┬───────┘
         │
         ▼
┌────────────────────────┐
│ Validar Datos Formulario│ (validaciones.py)
│ - Documento único       │
│ - Formato correcto      │
│ - Campos obligatorios   │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ Encriptar Datos        │ (EncriptadorDatos)
│ - Números documentos   │
│ - Teléfonos, emails    │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ Guardar en BD          │ (SQLAlchemy ORM)
│ - Persona model        │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ Notificar WebSocket    │ (Tabla en tiempo real)
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ Log Auditoría          │ (AuditoriaAdministrativa)
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ ✅ Persona Registrada  │
└────────────────────────┘
```

### 4️⃣ Flujo de Administración (Panel Admin)

```
┌──────────────────┐
│ Panel Administración│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Validar PIN      │ (gestionar_pin_sistemas.py)
│ (6 dígitos)      │
└────────┬─────────┘
         │
         ├─ Validación OK ──┐
         │                  │
         └─ Fallido ──> [Error - Reintentar]
                            │
                            ▼
                   ┌────────────────────┐
                   │ Seleccionar Opción │
                   └────┬──────────┬───┬┘
                        │          │   └─ Backup/Restore
                        │          └───── Mantenimiento
                        └───────── Seguridad / Usuarios
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
    Usuarios           Seguridad          Backup
    ┌─────────┐        ┌──────────┐      ┌────────┐
    │ Crear    │        │ Cambiar  │      │ USB/   │
    │ Editar   │        │ PIN      │      │ Cloud  │
    │ Eliminar │        │ Config.  │      │ Restore│
    └────┬────┘        └────┬─────┘      └───┬────┘
         │                  │                 │
         ▼                  ▼                 ▼
    [Log Evento]      [Log Evento]      [Log Evento]
         │                  │                 │
         └──────────────────┼────────────────┘
                            │
                            ▼
                   ┌────────────────────┐
                   │ ✅ Acción Completada│
                   └────────────────────┘
```

---

## Principales Endpoints API

### Autenticación

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| **POST** | `/api/login` | Autenticación de usuario | ❌ No |
| **POST** | `/api/logout` | Cerrar sesión | ✅ Sí |
| **GET** | `/api/me` | Obtener datos usuario actual | ✅ Sí |

### Personas

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| **GET** | `/api/personas` | Obtener lista de personas | ✅ Sí |
| **POST** | `/api/personas` | Crear nueva persona | ✅ Sí |
| **GET** | `/api/personas/<id>` | Obtener persona por ID | ✅ Sí |
| **PUT** | `/api/personas/<id>` | Actualizar persona | ✅ Sí |
| **DELETE** | `/api/personas/<id>` | Eliminar persona (soft delete) | ✅ Sí |

### Registro de Acceso

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| **POST** | `/api/registros` | Registrar acceso | ✅ Sí |
| **GET** | `/api/registros` | Obtener registros | ✅ Sí |
| **GET** | `/api/registros/<id>` | Obtener registro por ID | ✅ Sí |

### Pagos

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| **POST** | `/api/pagos` | Procesar pago | ✅ Sí |
| **GET** | `/api/pagos` | Obtener pagos | ✅ Sí |

### Reportes

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| **GET** | `/api/reportes/acceso` | Reporte de acceso (Excel) | ✅ Sí |
| **GET** | `/api/reportes/personas` | Reporte de personas (Excel) | ✅ Sí |

### Administración (Panel Seguro)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| **GET** | `/panel/usuarios` | Obtener usuarios | ✅ Sí (Admin) |
| **POST** | `/panel/usuarios` | Crear usuario | ✅ Sí (Admin) |
| **PUT** | `/panel/usuarios/<id>` | Actualizar usuario | ✅ Sí (Admin) |
| **DELETE** | `/panel/usuarios/<id>` | Eliminar usuario | ✅ Sí (Admin) |
| **POST** | `/panel/seguridad/pin` | Cambiar PIN | ✅ Sí (Admin) |

### Sistema

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| **GET** | `/health` | Health check | ❌ No |
| **GET** | `/api/status` | Estado del sistema | ✅ Sí |

---

## Integración IoT (ESP32)

### Sistema de Comunicación MQTT

```
┌────────────────────────────────┐
│ Backend Flask (Python)         │
│ mqtt_handler.py                │
└────────────┬───────────────────┘
             │
             │ MQTT
             │ Broker: mosquitto:1883
             │ Quality of Service: 1
             │
             ▼
         ┌───────────┐
         │ Mosquitto │ (MQTT Broker)
         └─────┬─────┘
               │
               │ Subscribe: control/acceso
               │ Publish: control/resultado
               │
               ▼
    ┌──────────────────────┐
    │ ESP32 (Arduino IDE)  │
    │ esp32_triac_mqtt.ino │
    └──────────┬───────────┘
               │
               │ GPIO Signal
               │
               ▼
    ┌──────────────────────┐
    │ TRIAC Control        │
    │ (Electrodoméstico)   │
    └──────────┬───────────┘
               │
               │ AC Signal 110V/220V
               │
               ▼
    ┌──────────────────────┐
    │ Solenoide Cerradura  │ ⚡
    │ (3-5 segundos)       │
    └──────────────────────┘
```

### Mensaje MQTT

**Topic:** `control/acceso`

**Payload (JSON):**
```json
{
  "persona_id": "uuid-123",
  "nombre": "Juan García",
  "tipo_acceso": "entrada",
  "timestamp": "2026-04-08T14:30:45Z",
  "comando": "abrir",
  "duracion": 4
}
```

### Control TRIAC

| Parámetro | Valor | Descripción |
|-----------|-------|------------|
| **Voltaje** | 110V / 220V | Según instalación |
| **Corriente** | ~2A | Consumo solenoide |
| **Tiempo Apertura** | 3-5 seg | Duración cierre automático |
| **GPIO ESP32** | GPIO 26 | Pin de control TRIAC |

### Fallback Manual

Si el ESP32 no responde (offline):
- Panel físico con botón de apertura manual
- PIN de seguridad requerido
- Registro de apertura manual en log

---

## Despliegue e Instalación

### Opción 1: Docker (⭐ Recomendado)

**Requisitos:**
- Docker Desktop instalado y ejecutándose

**Instalación:**
```bash
# Desde la raíz del proyecto
DOCKER_SETUP.bat
```

**Acceso:**
- Frontend: http://localhost
- Backend: http://localhost:8000
- Mosquitto MQTT: localhost:1883

### Opción 2: Local en Windows

**Requisitos:**
- Python 3.11+
- pip
- Node.js (opcional para frontend avanzado)

**Instalación:**
```bash
# 1. Instalar dependencias
INSTALAR.bat

# 2. Iniciar sistema
INICIAR.bat

# O manualmente:
cd backend
python app.py
```

**Acceso:**
- Frontend: http://localhost:8000
- Backend API: http://localhost:8000/api

### Credenciales de Prueba

```
Email: admin@sena.edu.co
Contraseña: admin123
```

### Despliegue a Producción

Ver archivo `docs/DEPLOYMENT_GUIDE.md` para:
- Deploy a Heroku
- Deploy a Render
- Deploy a AWS
- Configuración SSL/TLS
- Configuración base de datos PostgreSQL

---

## Estructura de Carpetas

```
ingresos-aprendices-7/
│
├── 📂 backend/                    # API Flask (puerto 8000)
│   ├── app.py                    # Aplicación principal
│   ├── routes.py                 # Rutas API
│   ├── models.py                 # Modelos SQLAlchemy
│   ├── config.py                 # Configuración
│   ├── security_shield.py        # Seguridad básica
│   ├── security_advanced.py      # Seguridad avanzada
│   ├── mqtt_handler.py           # Comunicación MQTT
│   ├── websocket_handler.py      # WebSocket real-time
│   ├── panel_routes.py           # Rutas administración
│   ├── pagos.py                  # Sistema pagos
│   ├── export_excel.py           # Exportación reportes
│   ├── validaciones.py           # Validaciones de datos
│   ├── scheduler.py              # Tareas programadas
│   ├── sync_manager.py           # Sincronización BD
│   ├── correo.py                 # Servicio de email
│   ├── requirements.txt          # Dependencias Python
│   ├── Dockerfile                # Imagen Docker
│   └── instance/                 # BD SQLite
│
├── 📂 frontend/                   # Interfaz Web
│   ├── login.html                # Página de login
│   ├── administracion.html       # Panel administrator
│   ├── ingreso_sin_dispositivos.html
│   ├── panel-security.js         # JavaScript seguro
│   └── ...otros archivos HTML
│
├── 📂 Arduino/                    # Código ESP32
│   ├── esp32_triac_mqtt.ino      # Código principal
│   └── esp32_triac_control/      # Librería TRIAC
│
├── 📂 docs/                       # Documentación (19 archivos)
│   ├── SEGURIDAD.md              # Guía de seguridad
│   ├── DEPLOYMENT_GUIDE.md       # Guía despliegue
│   ├── REPORTE_FINAL_SEGURIDAD.md
│   ├── GUIA_INTEGRACION_TRIAC.md
│   └── ...más documentación
│
├── 📂 scripts/                    # Scripts útiles
│   ├── INICIAR.bat               # Inicio rápido
│   ├── INSTALAR.bat              # Instalación
│   ├── MANTENIMIENTO.bat         # Panel mantenimiento
│   ├── VERIFICAR_INSTALACION.bat
│   └── ...más scripts
│
├── 📂 tests/                      # Casos de prueba
│   ├── test_api_simple.py
│   ├── test_sesion.py
│   └── ...más tests
│
├── 📂 logs/                       # Archivos de log (runtime)
├── 📂 instance/                   # BD SQLite (runtime)
├── 📂 RESPALDOS_USB/              # Backups locales
│
├── docker-compose.yml            # Orquestación Docker
├── Dockerfile.frontend           # Docker para frontend (nginx)
├── requirements.txt              # Dependencias globales
├── runtime.txt                   # Versión Python
├── Procfile                      # Para Heroku/Render
├── render.yaml                   # Configuración Render
├── build.sh                      # Build script Linux
├── Makefile                      # Automatización make
├── README.md                     # Guide inicio rápido
└── .env.example                  # Template variables entorno
```

---

## Archivos Configuración Importantes

### `.env` (Variables de Entorno)

```bash
# Flask
FLASK_ENV=development
FLASK_APP=backend/app.py
SECRET_KEY=tu-clave-secreta-aqui

# Database
DATABASE_URL=sqlite:///instance/app.db

# JWT
JWT_SECRET_KEY=tu-jwt-secret-key

# MQTT
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USER=
MQTT_PASSWORD=

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=tu-email@gmail.com
SENDER_PASSWORD=tu-password

# Security
MAX_LOGIN_ATTEMPTS=5
LOCK_TIME_MINUTES=15
```

### `requirements.txt`

```
Flask==3.1.3
Flask-SQLAlchemy==3.1.1
Flask-CORS==4.0.0
Flask-SocketIO==5.3.5
SQLAlchemy==2.0.48
python-dotenv==1.0.0
PyJWT==2.8.1
cryptography==41.0.7
paho-mqtt==1.6.1
openpyxl==3.10.10
Werkzeug==3.0.1
```

---

## Checklist de Seguridad

- ✅ Autenticación JWT implementada
- ✅ Prevención de fuerza bruta (5 intentos + 15 min bloqueo)
- ✅ Encriptación bcrypt para contraseñas
- ✅ Encriptación Fernet para datos sensibles
- ✅ CSRF tokens y SameSite=Strict
- ✅ Headers de seguridad OWASP
- ✅ Rate limiting en API
- ✅ Validación de entrada en todos los campos
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ XSS prevention (sanitización)
- ✅ Sistema de auditoría completo
- ✅ Logs de seguridad detallados
- ✅ Sesiones HTTP-only y secure
- ✅ Variables sensibles en .env
- ✅ HTTPS ready (configuración SSL comentada)

---

## Guía de Troubleshooting

### Error: "Port 8000 already in use"

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID XXX /F

# Linux/Mac
lsof -i :8000
kill -9 PID
```

### Error: "Database locked"

Elimina archivos temporales:
```bash
rm instance/*.db-journal
```

### ESP32 no responde

1. Verifica conexión WiFi
2. Asegúrate que MQTT broker está corriendo
3. Revisa logs: `logs/mqtt.log`

### WebSocket no conecta

1. Verifica CORS en `config.py`
2. Reinicia servidor Flask
3. Borra caché del navegador

---

## Contacto y Soporte

- **Documentación:** Ver carpeta `docs/`
- **Issues:** Reportar en el sistema de tickets
- **Seguridad:** Contactar al equipo de DevSecOps

---

## Licencia

Propiedad intelectual de SENA. Uso exclusivo interno.

---

**Documento actualizado:** 8 de Abril de 2026  
**Versión:** 1.0 - Documentación Completa
