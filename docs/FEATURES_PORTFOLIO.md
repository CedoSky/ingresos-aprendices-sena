# 🎯 Características Detalladas

Documentación completa de todas las características del Sistema de Control de Ingresos SENA.

---

## 📑 Contenido

- [Autenticación y Seguridad](#autenticación-y-seguridad)
- [Gestión de Usuarios](#gestión-de-usuarios)
- [Control de Acceso](#control-de-acceso)
- [Reportes y Auditoría](#reportes-y-auditoría)
- [Integración IoT](#integración-iot)
- [Sincronización en la Nube](#sincronización-en-la-nube)

---

## 🔐 Autenticación y Seguridad

### Autenticación JWT

**Flujo de Login:**

1. Usuario ingresa email y contraseña
2. Sistema valida credenciales contra BD
3. Si válidas → Genera JWT con expiración de 24h
4. Cliente guarda token en localStorage
5. Próximas requests incluyen token en header

**Token JWT contiene:**
```json
{
  "user_id": 1,
  "email": "usuario@sena.edu.co",
  "rol": "administrador",
  "exp": 1704067200,
  "iat": 1703980800
}
```

**Validación:**
- ✅ Token firmado con SECRET_KEY
- ✅ Expiración controlada
- ✅ Verificación en cada request
- ✅ Renovación automática

---

### Encriptación de Datos Sensibles

**Algoritmo:** Fernet (symmetric encryption)

**Datos encriptados:**
- Contraseñas (hash + salt)
- Números de identificación
- Teléfonos
- Direcciones

**Implementación:**
```python
from cryptography.fernet import Fernet

cipher = Fernet(ENCRYPTION_KEY)
datos_encriptados = cipher.encrypt(datos_sensibles.encode())
datos_desencriptados = cipher.decrypt(datos_encriptados).decode()
```

---

### Protección contra Ataques

| Ataque | Mitigación |
|--------|-----------|
| **SQL Injection** | Parametrized queries (SQLAlchemy ORM) |
| **XSS** | Bleach sanitization, CSP headers |
| **CSRF** | SameSite cookies, CSRF tokens |
| **Brute Force** | Rate limiting, bloqueo temporal |
| **Session Hijacking** | HTTPOnly cookies, Secure flag |

---

## 👥 Gestión de Usuarios

### Creación de Usuarios

**Roles disponibles:**
- `super_admin` - Acceso total
- `admin` - Gestión de usuarios y reportes
- `operador` - Registrar entradas/salidas
- `visitante` - Solo acceso limitado

**Datos requeridos:**
```json
{
  "email": "usuario@sena.edu.co",
  "nombre": "Juan Pérez",
  "rol": "operador",
  "documento": "1023456789",
  "telefono": "3001234567",
  "departamento": "Seguridad"
}
```

**Sistema de contraseñas:**
- Generación automática con 12 caracteres
- Requiere cambio en primer login
- Hash con algoritmo PBKDF2 + salt

---

### Gestión de Permisos

**Permisos por rol:**

```
┌──────────────┬─────────┬────────┬─────────┬────────────┐
│ Acción       │ Admin   │ Op     │ Visitor │ SuperAdmin │
├──────────────┼─────────┼────────┼─────────┼────────────┤
│ Ver Registro │ ✅      │ ✅     │ ❌      │ ✅         │
│ Crear Usuario│ ❌      │ ❌     │ ❌      │ ✅         │
│ Abrir Puerta │ ✅      │ ✅     │ ❌      │ ✅         │
│ Ver Auditoría│ ✅      │ ❌     │ ❌      │ ✅         │
│ Exportar     │ ✅      │ ❌     │ ❌      │ ✅         │
└──────────────┴─────────┴────────┴─────────┴────────────┘
```

---

### Bloqueo de Seguridad

**Activado después de:**
- 5 intentos fallidos de login
- Bloqueo temporal: 30 minutos
- Desbloqueo manual por super_admin

**Registro de intentos:**
```python
# En BD
{
  usuario_id: 123,
  intentos_fallidos: 5,
  bloqueado: true,
  fecha_bloqueo: "2024-01-15 10:30:00",
  razon: "Intentos fallidos"
}
```

---

## 🏠 Control de Acceso

### Registro de Entradas/Salidas

**Campos registrados:**

```
{
  "usuario_id": 1,
  "tipo": "entrada",  # entrada | salida
  "fecha_hora": "2024-01-15T08:30:45Z",
  "ip_origen": "192.168.1.100",
  "dispositivo": "Chrome - Windows",
  "locacion": "Puerta Principal",
  "notas": "Opcional"
}
```

**Búsqueda y Filtrado:**

```python
# Por rango de fechas
GET /api/registros?desde=2024-01-01&hasta=2024-01-31

# Por usuario
GET /api/registros?usuario_id=5

# Por tipo
GET /api/registros?tipo=entrada

# Combinado
GET /api/registros?usuario_id=5&tipo=salida&desde=2024-01-01
```

---

### Gestión de Visitantes

**Funcionalidades:**

1. **Crear Permiso Temporal**
   ```
   Visitante: Juan Pérez
   Documento: 1087654321
   Fecha entrada: 2024-01-20
   Hora entrada: 08:00
   Hora salida: 12:00
   Propósito: Reunión administrativa
   ```

2. **Control Automático**
   - Acceso solo en rango permitido
   - Notificación cuando expira
   - Registro automático de entrada/salida

3. **Restricciones**
   - No puede abrir puertas
   - Solo acceso a áreas comunes
   - Requiere acompañante

---

## 📊 Reportes y Auditoría

### Reportes Disponibles

**1. Reporte de Asistencia**
- Rango de fechas
- Por usuario o departamento
- Estadísticas: puntualidad, faltas
- Exporta a Excel

**2. Reporte de Acceso**
- Entradas/salidas por fecha
- Excepciones y anomalías
- Gráficos de flujo
- Análisis de picos

**3. Reporte de Seguridad**
- Intentos fallidos
- Usuarios bloqueados
- Cambios de permisos
- Auditoría administrativa

---

### Auditoría Completa

**Eventos registrados:**

```
- LOGIN_EXITOSO
- LOGIN_FALLIDO
- LOGOUT
- CREAR_USUARIO
- MODIFICAR_USUARIO
- ELIMINAR_USUARIO
- CAMBIAR_PERMISO
- ABRIR_PUERTA
- CERRAR_PUERTA
- EXPORTAR_DATOS
- RESTAURAR_BACKUP
```

**Ejemplo registro:**
```json
{
  "id": 1,
  "usuario_id": 1,
  "accion": "CREAR_USUARIO",
  "detalles": "Creó usuario: juan@sena.edu.co",
  "ip_origen": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2024-01-15T10:45:30Z",
  "estado": "exitoso",
  "cambios": {
    "email": "juan@sena.edu.co",
    "rol": "operador"
  }
}
```

---

### Exportación de Datos

**Formatos soportados:**

1. **Excel (.xlsx)**
   - Reportes formateados
   - Múltiples hojas
   - Gráficos
   - Filtros automáticos

2. **CSV**
   - Datos crudos
   - Importable a otros sistemas
   - Pequeño tamaño

3. **PDF**
   - Reportes formales
   - Imprimibles
   - Con firma digital

---

## 🤖 Integración IoT

### Control de Puertas (ESP32 + MQTT)

**Componentes:**
- ESP32 microcontrolador
- TRIAC para cerradura eléctrica
- Sensor de estado
- Botón de emergencia

**Protocolo MQTT:**

```
Publicar (Backend → ESP32):
  cmd/puerta1/open      → Abrir puerta
  cmd/puerta1/close     → Cerrar puerta
  cmd/puerta1/config    → Configuración

Suscribir (ESP32 → Backend):
  device/puerta1/state     → Estado actual
  device/puerta1/sensor    → Datos sensor
  device/puerta1/battery   → Nivel batería
```

---

### Estados de Puerta

```
Estado: CERRADA
├─ Botón abrir
│  └─ Estado: ABRIENDO (5 segundos)
│     └─ Completado
│        └─ Estado: ABIERTA
│
├─ Botón cerrar
│  └─ Estado: CERRANDO (3 segundos)
│     └─ Completado
│        └─ Estado: CERRADA
│
└─ Botón emergencia
   └─ Estado: BLOQUEADA
      └─ Requiere intervención manual
```

---

### Monitoreo en Tiempo Real

**Dashboard en vivo:**
- Estado de cada puerta
- Última acción
- Batería ESP32
- Conexión MQTT
- Alertas de anomalías

---

## ☁️ Sincronización en la Nube

### Respaldos Automáticos

**Frecuencia:**
- Cada 1 hora
- Al fin de día completo
- Antes de cambios críticos

**Destinos:**
- Dropbox (automático)
- Google Drive (opcional)
- USB local

**Contenido:**
- Base de datos completa
- Configuración
- Archivos de log
- Certificados

---

### Restauración

**Opciones:**

1. **Restaurar última versión**
   ```bash
   python backend/restore_from_usb.py
   ```

2. **Restaurar fecha específica**
   ```bash
   python backend/restore_from_usb.py --date 2024-01-15
   ```

3. **Restaurar desde cloud**
   ```bash
   python backend/cloud_storage.py --restore
   ```

---

### Sincronización de Personas

**Datos sincronizados:**
- Usuarios nuevos
- Cambios de rol
- Permisos modificados
- Usuarios inactivos

**Conflictos:**
- Versión local vs cloud
- Resolución automática
- Notificación a admin

---

## 📈 Análisis y Estadísticas

### Dashboard Ejecutivo

**KPIs principales:**
- Total de registros hoy
- Usuarios activos
- Promedio tiempo atención
- Puertas con problemas
- Último backup exitoso

**Gráficos:**
- Flujo de personas por hora
- Asistencia por departamento
- Tendencias semanales
- Comparación con período anterior

---

### Alertas Automáticas

**Alertas críticas:**
- ❌ Conexión MQTT perdida
- ❌ Base de datos no disponible
- ❌ Disco lleno
- ❌ Backup fallido
- ⚠️ Múltiples intentos fallidos

**Notificaciones:**
- Email al admin
- SMS (opcional)
- Dashboard visible

---

## 🔄 Sincronización de Datos

### En Tiempo Real

- Entradas/salidas registradas al instante
- Estado de puertas actualizado
- Permisos aplicados inmediatamente

### Bajo Demanda

- Sincronizar con cloud
- Importar datos de otro sistema
- Forzar actualización de BD

---

**Última actualización:** Enero 2025
