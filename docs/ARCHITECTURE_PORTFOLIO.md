# 🏗️ Arquitectura del Sistema

Este documento describe la arquitectura técnica del Sistema de Control de Ingresos SENA de manera detallada.

---

## 📑 Contenido

- [Visión General](#visión-general)
- [Componentes Principales](#componentes-principales)
- [Flujo de Datos](#flujo-de-datos)
- [Capas de la Aplicación](#capas-de-la-aplicación)
- [Patrones de Diseño](#patrones-de-diseño)
- [Seguridad](#seguridad)
- [Performance](#performance)

---

## 🔭 Visión General

### Stack Tecnológico

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENTE (Browser)                       │
│         HTML5 + CSS3 + JavaScript Vanilla                    │
│         WebSockets + Fetch API + LocalStorage                │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WebSocket
        ┌──────────────▼──────────────┐
        │      Nginx Reverse Proxy    │ Port 80
        └──────────────┬──────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │ REST API                WebSocket    │
    │ :8000/api              :8000/ws      │
    │                                      │
    │      Flask Application               │
    │  - Routes                            │
    │  - Middleware                        │
    │  - Error Handling                    │
    │                                      │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │  SQLAlchemy ORM Layer                │
    │  - Models                            │
    │  - Query Builder                     │
    │  - Relationship Mapping              │
    └──────────────────┬──────────────────┘
                       │
            ┌──────────▼──────────┐
            │   SQLite Database   │
            │   datos.db          │
            └─────────────────────┘

┌──────────────────────────────────────┐
│     MQTT Broker (Mosquitto)          │
│     Port 1883                        │
│  - Subscribe: sensor/+/status        │
│  - Publish: device/+/command         │
└──────────────────────────────────────┘
         │                    │
    ┌────▼─────┐        ┌─────▼────┐
    │ ESP32 #1  │        │ ESP32 #2  │
    │ Door 1    │        │ Door 2    │
    │ TRIAC     │        │ TRIAC     │
    └───────────┘        └───────────┘
```

---

## 🔧 Componentes Principales

### 1. **Frontend (Cliente Web)**

#### Características:
- HTML5 semántico
- CSS3 responsivo (mobile-first)
- JavaScript Vanilla (sin dependencias)
- WebSockets para real-time
- LocalStorage para datos locales

#### Archivos Principales:
```
frontend/
├── index.html          # Dashboard principal
├── admin.html          # Panel administrativo
├── login.html          # Formulario login
├── js/
│   ├── app.js         # Aplicación principal
│   ├── auth.js        # Manejo autenticación
│   ├── websocket.js   # Conexión WebSocket
│   ├── api.js         # Wrapper API REST
│   └── utils.js       # Funciones auxiliares
└── css/
    ├── styles.css     # Estilos globales
    ├── responsive.css # Media queries
    └── admin.css      # Estilos admin
```

#### Flujo Cliente:
```javascript
1. Cargar página → Verificar token en localStorage
2. Si existe → Conectar WebSocket
3. Escuchar cambios en tiempo real
4. Enviar eventos → API REST
5. Actualizar UI en base a respuestas
```

---

### 2. **Backend (API REST + WebSocket)**

#### Stack:
- **Framework:** Flask 3.0+
- **ORM:** SQLAlchemy 2.0+
- **WebSocket:** Flask-SocketIO
- **Validación:** Bleach + Custom validators

#### Estructura:
```
backend/
├── app.py                 # Punto de entrada
├── models.py             # Modelos SQLAlchemy
├── routes.py             # Rutas HTTP
├── websocket_handler.py  # Manejador WebSocket
├── mqtt_handler.py       # Integración MQTT
├── security_advanced.py  # Encriptación/Auditoría
├── config.py             # Configuración
└── requirements.txt      # Dependencias
```

#### Rutas Principales:

**Autenticación:**
```
POST /api/login              - Iniciar sesión
POST /api/logout             - Cerrar sesión
POST /api/refresh-token      - Renovar JWT
GET  /api/me                 - Datos usuario actual
```

**Usuarios:**
```
GET    /api/usuarios         - Listar
POST   /api/usuarios         - Crear
PUT    /api/usuarios/<id>    - Actualizar
DELETE /api/usuarios/<id>    - Eliminar
GET    /api/usuarios/<id>    - Obtener uno
```

**Registros:**
```
GET    /api/registros        - Listar
POST   /api/registros        - Crear entrada
GET    /api/registros/<id>   - Obtener
POST   /api/registros/export - Exportar Excel
```

**Control de Puertas:**
```
POST /api/puertas/abrir      - Enviar comando abrir
POST /api/puertas/cerrar     - Enviar comando cerrar
GET  /api/puertas/estado     - Estado actual
```

---

### 3. **Base de Datos**

#### Modelos:

**Usuario**
```
┌─────────────────────┐
│ Usuario             │
├─────────────────────┤
│ id (PK)            │
│ email (UNIQUE)     │
│ password (hash)    │
│ nombre             │
│ rol                │
│ activo             │
│ fecha_creacion     │
│ ultima_conexion    │
│ intentos_fallidos  │
│ bloqueado          │
└─────────────────────┘
     1 │
       │ N
       ├─→ Registro (entradas/salidas)
       ├─→ EventoAuditoria (acciones admin)
       └─→ Sesion
```

**Registro**
```
┌─────────────────────┐
│ Registro            │
├─────────────────────┤
│ id (PK)            │
│ usuario_id (FK)    │
│ tipo (entrada|sal) │
│ fecha_hora         │
│ ip_origen          │
│ dispositivo        │
│ locacion           │
└─────────────────────┘
```

**Índices:**
- `idx_registro_usuario_fecha` - Queries frecuentes
- `idx_usuario_email` - Login
- `idx_auditoria_fecha` - Búsquedas históricas

---

### 4. **IoT / Hardware (ESP32)**

#### Protocolo: MQTT

**Tópicos:**
```
device/puerta1/state        ← Estado puerta 1
device/puerta2/state        ← Estado puerta 2
cmd/puerta1/open            → Comando abrir puerta 1
cmd/puerta2/close           → Comando cerrar puerta 2
sensor/puerta1/battery      ← Nivel batería
```

#### Flujo Control:
```
1. Usuario hace clic "Abrir puerta"
   ↓
2. Backend valida permisos
   ↓
3. Backend publica a MQTT: cmd/puerta1/open
   ↓
4. ESP32 recibe mensaje
   ↓
5. ESP32 activa TRIAC (abre cerradura)
   ↓
6. ESP32 publica estado: device/puerta1/state = "open"
   ↓
7. Backend escucha y actualiza BD
   ↓
8. WebSocket notifica clientes conectados
```

---

## 🌊 Flujo de Datos Principales

### 1. Autenticación

```
Cliente                  Backend                 BD
   │                        │                    │
   ├─ POST /login ──────────>│                    │
   │   {email, pass}         │                    │
   │                        ├─ Validar ──────────>│
   │                        │ SELECT User ...    │
   │                    <─────┤ User found       <─┤
   │                        │                    │
   │                        ├─ Hash password     │
   │                        ├─ Generar JWT       │
   │                        ├─ Crear Sesión     │
   │  <─────────────────────┤                    │
   │  {token, user}          │                    │
   │                        │                    │
   └─ Guardar token         │                    │
     en localStorage
```

### 2. Crear Registro (Entrada)

```
Cliente                  Backend                 BD
   │                        │                    │
   ├─ POST /registros ─────>│                    │
   │  {tipo: entrada}        │                    │
   │                        ├─ Verificar JWT     │
   │                        ├─ Validar datos     │
   │                        ├─ INSERT Registro ─>│
   │                        │ COMMIT             │
   │  <────────────────────┤                    <─┤
   │  {id, timestamp}        │                    │
   │                        │                    │
   │         (WebSocket)     │                    │
   │<───────────────────────┤                    │
   │ evento: nuevo_registro  │                    │
```

### 3. Control de Puerta (ESP32)

```
Cliente      Backend         MQTT Broker        ESP32
   │            │                │                │
   ├─GET ───────>│                │                │
   │  /puertas   │                │                │
   │             ├─ Publica ─────>│                │
   │             │ cmd/door/open  ├─ Notifica ───>│
   │             │                │                ├─ Activa TRIAC
   │             │                │                ├─ Publica estado
   │             │<─ Suscribe ────┤<───────────────┤
   │             │ device/door/st │                │
   │             ├─ UPDATE BD     │                │
   │<────────────┤ {estado}       │                │
   │ {ok}        │                │                │
```

---

## 🏛️ Capas de la Aplicación

### Capa de Presentación (Frontend)

**Responsabilidades:**
- Renderizar interfaz
- Capturar eventos de usuario
- Validación UI
- Almacenamiento local

**Tecnologías:**
- HTML5, CSS3, JS Vanilla
- WebSockets para real-time
- Fetch API para HTTP

---

### Capa de Aplicación (Backend)

**Responsabilidades:**
- Recibir requests HTTP
- Validar datos
- Ejecutar lógica de negocio
- Retornar respuestas JSON

**Middleware:**
```python
@app.before_request
├─ Validar JWT token
├─ Verificar permisos
├─ Rate limiting
└─ Logging

@app.after_request
├─ Agregar headers de seguridad
├─ CORS headers
└─ Logging
```

---

### Capa de Datos (ORM)

**Responsabilidades:**
- Mapear tablas a clases Python
- Generar queries SQL
- Manejar relaciones
- Validar en BD

**ORM: SQLAlchemy**
```python
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    registros = db.relationship('Registro', backref='usuario')
```

---

### Capa de Integración (IoT)

**Responsabilidades:**
- Publicar/suscribirse a MQTT
- Convertir comandos a mensajes
- Sincronizar estado

**MQTT Handler:**
```python
class MQTTHandler:
    def conectar(self)
    def publicar_comando(self, puerta, comando)
    def suscribir_estado(self, puerta)
    def manejar_mensaje(self, msg)
```

---

## 🎨 Patrones de Diseño

### 1. **MVC (Model-View-Controller)**

```
Model (models.py)
    ├─ Usuario
    ├─ Registro
    ├─ EventoAuditoria
    └─ Sesion

View (frontend/HTML)
    ├─ index.html
    ├─ admin.html
    └─ login.html

Controller (routes.py)
    ├─ @app.route('/login')
    ├─ @app.route('/usuarios')
    └─ @app.route('/registros')
```

### 2. **Repository Pattern**

```python
class UsuarioRepository:
    def encontrar_por_email(email)
    def crear(datos)
    def actualizar(id, datos)
    def obtener_todos()
```

### 3. **Service Layer**

```python
class UsuarioService:
    def login(email, password)
    def crear_usuario(datos)
    def cambiar_contraseña(usuario_id, antigua, nueva)
```

### 4. **Factory Pattern**

```python
class ConexionFactory:
    def crear_mqtt_handler()
    def crear_base_datos()
```

---

## 🔐 Seguridad en Capas

### Capa 1: Entrada (Input Validation)

```python
# Bleach para sanitizar HTML
email = bleach.clean(request.json['email'])

# Regex para validar formato
if not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
    return {'error': 'Email inválido'}, 400
```

### Capa 2: Autenticación

```python
# JWT con expiración
token = jwt.encode(
    {
        'user_id': usuario.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    },
    SECRET_KEY
)

# Verificar token en cada request
@app.before_request
def verificar_token():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    payload = jwt.decode(token, SECRET_KEY)
```

### Capa 3: Encriptación

```python
from cryptography.fernet import Fernet

# Encriptar datos sensibles
cipher = Fernet(ENCRYPTION_KEY)
datos_encriptados = cipher.encrypt(datos.encode())
```

### Capa 4: Auditoría

```python
# Registrar todas las acciones administrativas
EventoAuditoria.create(
    usuario_id=usuario.id,
    accion='CREATE_USER',
    detalles=str(datos),
    ip_origen=request.remote_addr
)
```

---

## ⚡ Performance

### Optimizaciones Implementadas

1. **Database Indexing:**
   ```sql
   CREATE INDEX idx_registro_usuario_fecha 
   ON registros(usuario_id, fecha_hora DESC);
   ```

2. **Query Optimization:**
   ```python
   # Bad: N+1 query
   usuarios = Usuario.query.all()
   for usuario in usuarios:
       print(usuario.registros)  # Query por cada usuario

   # Good: Eager loading
   usuarios = Usuario.query.options(
       joinedload(Usuario.registros)
   ).all()
   ```

3. **Caching:**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def obtener_configuracion():
       return db.session.query(Config).first()
   ```

4. **Connection Pooling:**
   ```python
   SQLALCHEMY_ENGINE_OPTIONS = {
       'pool_size': 10,
       'pool_recycle': 3600,
       'pool_pre_ping': True
   }
   ```

---

## 📊 Monitoreo

### Logs

```
logs/
├── app.log          # Todas las acciones
├── error.log        # Solo errores
├── security.log     # Eventos seguridad
└── mqtt.log         # Eventos MQTT
```

### Métricas Clave

- Requests por segundo
- Tiempo promedio respuesta
- Errores por tipo
- Usuarios activos
- Conexiones MQTT

---

## 🔄 Escalabilidad Futura

### Mejoras Posibles

1. **Database:**
   - Migrar a PostgreSQL
   - Implementar replicación
   - Cache layer (Redis)

2. **Backend:**
   - Microservicios
   - Message queue (RabbitMQ)
   - Load balancing

3. **Frontend:**
   - Progressive Web App (PWA)
   - Service Workers
   - Offline-first

---

**Última actualización:** Enero 2025
