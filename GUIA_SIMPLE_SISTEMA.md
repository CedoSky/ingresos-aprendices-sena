# 🎯 Guía Simple - Sistema de Ingresos SENA

## 📱 PÁGINAS PRINCIPALES

```
┌─────────────────────────────────────────────────────────────────┐
│                    SISTEMA DE INGRESOS SENA                     │
└─────────────────────────────────────────────────────────────────┘

                              Usuario Accede
                                    │
                                    ▼
                        ┌──────────────────────┐
                        │   LOGIN.HTML         │
                        │ (Página de Entrada)  │
                        │ · Email              │
                        │ · Contraseña         │
                        │ · Botón: Ingresar    │
                        └──────────┬───────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
           ❌ Contraseña              ✅ Contraseña
           Incorrecta                 Correcta
                    │                             │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │   DASHBOARD.HTML     │
                        │ (Pantalla Principal) │
                        │ (Menú 6 opciones)    │
                        └──────────┬───────────┘
                                   │
                ┌──────────┬────────┼────────┬──────────┬──────────┐
                │          │        │        │          │          │
                ▼          ▼        ▼        ▼          ▼          ▼
            REGISTRO  BÚSQUEDA   ACCESO    ADMIN      PAGOS     REPORTES
            Personas   Personas   Control   Panel     Servicios  Excel
```

---

## 🖥️ PÁGINAS DEL FRONTEND

### 1️⃣ **LOGIN.HTML** 🔐
**¿Para qué sirve?**
- Primera página que ve el usuario
- Verifica si es administrador, vigilante o usuario

**¿Qué tiene?**
```
┌────────────────────────┐
│   LOGIN                │
├────────────────────────┤
│ 📧 Email               │
│    [________________]  │
│                        │
│ 🔑 Contraseña          │
│    [________________]  │
│                        │
│    [INGRESAR]          │
└────────────────────────┘
```

**Conecta con Backend:**
- **Envía:** Email + Contraseña
- **Recibe:** Token JWT (autorización)
- **Endpoint:** `POST /api/login`

---

### 2️⃣ **DASHBOARD.HTML** 📊
**¿Para qué sirve?**
- Menú principal después de loguear
- Muestra opciones según el rol del usuario

**¿Qué tiene?**
```
┌──────────────────────────────────────┐
│         DASHBOARD - BIENVENIDO        │
│         Usuario: admin@sena.edu.co    │
├──────────────────────────────────────┤
│                                      │
│  ┌─────────┐  ┌─────────┐           │
│  │ REGISTRO│  │ BÚSQUEDA│           │
│  │Personas │  │Personas │           │
│  └─────────┘  └─────────┘           │
│  ┌─────────┐  ┌─────────┐           │
│  │ CONTROL │  │  ADMIN  │           │
│  │ Acceso  │  │  Panel  │           │
│  └─────────┘  └─────────┘           │
│  ┌─────────┐  ┌─────────┐           │
│  │ PAGOS   │  │REPORTES │           │
│  │Servicios│  │  Excel  │           │
│  └─────────┘  └─────────┘           │
│                                      │
│                    [SALIR]           │
└──────────────────────────────────────┘
```

---

### 3️⃣ **REGISTRO DE PERSONAS** 👤

**¿Para qué sirve?**
- Agregar nuevas personas (aprendices, instructores, visitantes)

**¿Qué tiene?**
```
┌─────────────────────────────────────┐
│    REGISTRAR NUEVA PERSONA          │
├─────────────────────────────────────┤
│ Nombre:        [________________]    │
│ Tipo Doc:      [Cédula▼]            │
│ Número Doc:    [________________]    │
│ Email:         [________________]    │
│ Teléfono:      [________________]    │
│ Perfil:        [Aprendiz▼]          │
│ Programa:      [________________]    │
│ Foto:          [Subir Foto]         │
│                                      │
│     [GUARDAR]        [CANCELAR]     │
└─────────────────────────────────────┘
```

**Flujo:**
```
Usuario llena formulario
        │
        ▼
Presiona GUARDAR
        │
        ▼
Frontend valida datos (¿está todo?)
        │
        ├─ NO ──> Muestra error
        │
        └─ SÍ ──> Envía a Backend
                      │
                      ▼
                Backend guarda en BD
                      │
                      ▼
                ✅ Persona Registrada
```

**Conecta con Backend:**
- **Envía:** Nombre, documento, email, foto, etc.
- **Endpoint:** `POST /api/personas`

---

### 4️⃣ **BÚSQUEDA DE PERSONAS** 🔍

**¿Para qué sirve?**
- Buscar y filtrar personas registradas
- Ver detalles de cada persona

**¿Qué tiene?**
```
┌─────────────────────────────────────┐
│     BUSCAR PERSONAS                 │
├─────────────────────────────────────┤
│ Buscar: [________________] [BUSCAR] │
│ Filtro: [Todos▼] [Aprendiz▼]       │
├─────────────────────────────────────┤
│ TABLA:                              │
│ ┌───┬──────────┬────────┬────────┐  │
│ │ # │  Nombre  │  Doc   │ Perfil │  │
│ ├───┼──────────┼────────┼────────┤  │
│ │ 1 │ Juan G.  │123456  │Aprendiz│  │
│ │ 2 │ Maria P. │654321  │Instruc │  │
│ │ 3 │ Carlos M │111222  │Visitante  │
│ └───┴──────────┴────────┴────────┘  │
│                                      │
│ [Editar]  [Eliminar]  [Ver Foto]   │
└─────────────────────────────────────┘
```

**Conecta con Backend:**
- **Envía:** Criterios de búsqueda
- **Recibe:** Lista de personas
- **Endpoint:** `GET /api/personas`

---

### 5️⃣ **CONTROL DE ACCESO** 🚪

**¿Para qué sirve?**
- Registrar cuando alguien entra o sale
- Controlar apertura de cerradura

**¿Qué tiene?**
```
┌──────────────────────────────────────┐
│     CONTROL DE ACCESO                │
├──────────────────────────────────────┤
│ Seleccionar Persona:                 │
│ [Buscar...        _____________]     │
│                                      │
│ ┌────────────────────────────────┐   │
│ │ Juan García                    │   │
│ │ Cédula: 123456                 │   │
│ │ Programa: Mantenimiento        │   │
│ └────────────────────────────────┘   │
│                                      │
│      ┌──────────────────┐            │
│      │ Tipo: [ENTRADA▼] │            │
│      └──────────────────┘            │
│                                      │
│  ┌────────────┐  ┌────────────┐     │
│  │ [ABRIR]    │  │ [CANCELAR] │     │
│  │ Cerradura  │  │            │     │
│  └────────────┘  └────────────┘     │
│                                      │
│ 🟢 Estado: Cerradura ABIERTA         │
│ Tiempo: 00:04 seg (cierre automático)│
└──────────────────────────────────────┘
```

**Flujo:**
```
1. Usuario selecciona persona
2. Elige ENTRADA o SALIDA
3. Presiona ABRIR
4. Frontend envía a Backend
5. Backend publica en MQTT
6. ESP32 activa TRIAC
7. ⚡ CERRADURA SE ABRE 3-5 seg
8. Se registra automáticamente
```

**Conecta con Backend:**
- **Envía:** ID Persona, tipo (entrada/salida)
- **Endpoint:** `POST /api/registros`

---

### 6️⃣ **PANEL DE ADMINISTRACIÓN** ⚙️

**¿Para qué sirve?**
- Solo para administradores
- Gestionar usuarios, seguridad, backups

**Requiere PIN** (6 dígitos)

**¿Qué tiene?**
```
┌──────────────────────────────────────┐
│  PANEL DE ADMINISTRACIÓN             │
├──────────────────────────────────────┤
│ 🔐 Ingrese PIN:  [______] [OK]       │
│                                      │
│ (Después de PIN correcto...)         │
│                                      │
│ ┌────────────────────────────────┐   │
│ │ 👥 GESTIONAR USUARIOS          │   │
│ │ · Crear usuario                │   │
│ │ · Editar usuario               │   │
│ │ · Eliminar usuario             │   │
│ └────────────────────────────────┘   │
│                                      │
│ ┌────────────────────────────────┐   │
│ │ 🔒 SEGURIDAD                   │   │
│ │ · Cambiar PIN                  │   │
│ │ · Ver logs de acceso           │   │
│ │ · Configurar horarios          │   │
│ └────────────────────────────────┘   │
│                                      │
│ ┌────────────────────────────────┐   │
│ │ 💾 BACKUP                      │   │
│ │ · Backup a USB                 │   │
│ │ · Backup a Cloud               │   │
│ │ · Restaurar datos              │   │
│ └────────────────────────────────┘   │
│                                      │
│ ┌────────────────────────────────┐   │
│ │ 🔧 MANTENIMIENTO               │   │
│ │ · Ver logs                     │   │
│ │ · Limpiar base de datos        │   │
│ │ · Reiniciar sistema            │   │
│ └────────────────────────────────┘   │
└──────────────────────────────────────┘
```

**Secciones:**

#### A) **Gestionar Usuarios**
```
┌──────────────────────────────────┐
│ CREAR NUEVO USUARIO              │
├──────────────────────────────────┤
│ Nombre:      [________________]   │
│ Email:       [________________]   │
│ Contraseña:  [________________]   │
│ Rol:         [Admin▼]            │
│ Activo:      [✓] Sí              │
│              [GUARDAR] [CANCELAR] │
└──────────────────────────────────┘
```

#### B) **Cambiar PIN**
```
┌──────────────────────────────┐
│ CAMBIAR PIN                  │
├──────────────────────────────┤
│ PIN Actual:   [______]       │
│ PIN Nuevo:    [______]       │
│ Confirmar:    [______]       │
│               [OK] [CANCELAR]│
└──────────────────────────────┘
```

#### C) **Hacer Backup**
```
┌──────────────────────────────┐
│ HACER BACKUP                 │
├──────────────────────────────┤
│ Seleccionar destino:         │
│ ○ USB                        │
│ ○ Cloud (Google Drive)       │
│                              │
│ [HACER BACKUP]               │
│ 📊 Progreso: ████░░░░ 60%   │
│ ✅ Backup completado         │
└──────────────────────────────┘
```

---

### 7️⃣ **PAGOS Y SERVICIOS** 💰

**¿Para qué sirve?**
- Procesar pagos de servicios
- Agregar créditos a cuentas

**¿Qué tiene?**
```
┌──────────────────────────────────┐
│   PAGOS Y SERVICIOS              │
├──────────────────────────────────┤
│ Seleccionar Persona:             │
│ [Buscar..._________________]     │
│                                  │
│ Servicios Disponibles:           │
│ ☐ Cafetería          $10.000     │
│ ☐ Biblioteca         $5.000      │
│ ☐ Laboratorio        $15.000     │
│ ☐ Transporte         $20.000     │
│                                  │
│ Total a Pagar: $50.000           │
│                                  │
│ ┌────────────────────────────┐   │
│ │ Método de Pago:            │   │
│ │ ○ Tarjeta                  │   │
│ │ ○ Transferencia            │   │
│ │ ○ Efectivo                 │   │
│ └────────────────────────────┘   │
│                                  │
│     [PROCESAR PAGO]              │
│                                  │
│ ✅ Pago Realizado con Éxito      │
│ Comprobante #: 2024001           │
└──────────────────────────────────┘
```

---

### 8️⃣ **REPORTES EXCEL** 📈

**¿Para qué sirve?**
- Descargar datos en Excel
- Análisis offline

**¿Qué tiene?**
```
┌──────────────────────────────────┐
│   GENERAR REPORTES               │
├──────────────────────────────────┤
│ Tipo de Reporte:                 │
│ ☑ Registro de Acceso             │
│ ☐ Listar Personas                │
│ ☐ Pagos Realizados               │
│ ☐ Auditoría Sistema              │
│                                  │
│ Rango de Fechas:                 │
│ De: [dd/mm/yyyy]                 │
│ A:  [dd/mm/yyyy]                 │
│                                  │
│ Filtros:                         │
│ ☑ Solo entrada (no salida)       │
│ ☑ Excluir visitantes             │
│                                  │
│     [DESCARGAR EXCEL]            │
│                                  │
│ 📥 Descargando: Reporte.xlsx     │
│ ✅ Descarga completada           │
└──────────────────────────────────┘
```

---

## 🔧 BACKEND - CÓMO FUNCIONA

```
┌────────────────────────────────────────┐
│         FLASK BACKEND                  │
│     (Servidor en localhost:8000)       │
└────────────────────────────────────────┘
           │
           │ Recibe peticiones del Frontend
           │
           ▼
    ┌──────────────────┐
    │  routes.py       │ ◄─── Define qué hace cada URL
    │ (/api/personas)  │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────────────────────┐
    │  Verificar Seguridad             │
    │  · ¿Token JWT válido?            │
    │  · ¿Usuario autorizado?          │
    │  · ¿Datos válidos?               │
    └────────┬─────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────┐
    │  Procesar la Solicitud           │
    │  · Validar datos                 │
    │  · Aplicar lógica de negocio     │
    │  · Encriptar datos sensibles     │
    └────────┬─────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────┐
    │  models.py - BASE DE DATOS       │
    │  · Guardar en BD                 │
    │  · Consultar datos               │
    │  · Actualizar registros          │
    └────────┬─────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────┐
    │  Responder al Frontend           │
    │  · Enviar JSON con datos         │
    │  · Con confirmación (✅ o ❌)    │
    └────────┬─────────────────────────┘
             │
             ▼
    Frontend recibe la respuesta
```

### 📂 Archivos Backend Principales

| Archivo | ¿Qué hace? |
|---------|-----------|
| **app.py** | Inicia el servidor Flask |
| **routes.py** | Define todas las URLs y qué hacen (`/api/personas`, `/api/login`, etc.) |
| **models.py** | Define la estructura de BD (Usuarios, Personas, Registros) |
| **security_shield.py** | Verifica tokens, valida datos, previene ataques |
| **mqtt_handler.py** | Se comunica con ESP32 para abrir cerradura |
| **websocket_handler.py** | Actualiza pantalla en TIEMPO REAL |
| **pagos.py** | Procesa pagos |
| **export_excel.py** | Genera reportes en Excel |
| **validaciones.py** | Valida que los datos sean correctos |

---

## 🔄 FLUJO COMPLETO - Ejemplo: Registrar Acceso

```
┌─────────────────┐
│ Usuario en Tab. │
│ Selecciona:     │
│ - Pedro García  │
│ - Tipo: ENTRADA │
│ Presiona: ABRIR │
└────────┬────────┘
         │
         ▼
    ┌─────────────────────────────┐
    │ FRONTEND (navegador)        │
    │ Valida: ¿hay persona?       │
    └────────┬────────────────────┘
             │
             ├─ NO ──> Muestra: "Selecciona persona"
             │
             └─ SÍ ──> Envía al Backend
                            │
                            ▼
                    ┌────────────────────┐
                    │ BACKEND (Flask)    │
                    │ routes.py          │
                    │ POST /api/registros│
                    └────────┬───────────┘
                             │
                             ▼
                    ┌────────────────────┐
                    │ Verifica JWT       │
                    │ ¿Usuario válido?   │
                    └────────┬───────────┘
                             │
                             ORilla
                             │
                             ▼
                    ┌────────────────────┐
                    │ Busca persona en BD│
                    │ Valida datos       │
                    └────────┬───────────┘
                             │
                             ▼
                    ┌────────────────────┐
                    │ Crea registro      │
                    │ Guarda en BD       │
                    │ entry_time = NOW   │
                    └────────┬───────────┘
                             │
                             ▼
                    ┌────────────────────┐
                    │ MQTT Handler       │
                    │ Publica mensaje en │
                    │ Topic: control/    │
                    │        acceso      │
                    └────────┬───────────┘
                             │
                    ┌────────┴──────────┐
                    │                   │
                    ▼                   ▼
            ┌──────────────┐     ┌─────────────┐
            │ MOSQUITTO    │     │ Respuesta   │
            │ (Broker MQTT)│     │ al Frontend │
            └──────┬───────┘     └─────┬───────┘
                   │                   │
                   ▼                   ▼
        ┌──────────────────┐   "✅ Acceso registrado"
        │ ESP32 Arduino    │   "Cerradura abierta"
        │ Recibe mensaje   │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Activa GPIO 26   │
        │ (Pin TRIAC)      │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ ⚡ TRIAC Activa  │
        │ 110V AC          │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Solenoide abre   │
        │ cerradura 3-5 seg│
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ 🔓 PUERTA ABIERTA│
        └──────────────────┘
        
        ✅ SE REGISTRÓ TODO AUTOMÁTICAMENTE
```

---

## 📊 RELACIÓN FRONTEND ↔ BACKEND

```
                    FRONTEND                    BACKEND
                  (Navegador)                  (Servidor)
                       │                            │
    Usuario             │                            │
    entra app ──────►   │                            │
                        │                            │
                        │  1️⃣ POST /api/login      │
                 Envía email + pas ────────────────►│
                        │                            │
                        │  Verifica en BD            │
                        │  Encripta contraseña       │
                        │◄──────── JWT Token ────────│
                        │                            │
    Guarda token        │                            │
    en navegador        │                            │
                        │                            │
                        │  2️⃣ GET /api/personas    │
                 Solicita lista ──────────────────► │
                 (incluye JWT)                       │
                        │                            │
                        │  Consulta BD              │
                        │  Filtra datos             │
                        │◄───── JSON con datos ─────│
                        │                            │
    Muestra tabla       │                            │
    de personas         │                            │
                        │                            │
                        │  3️⃣ POST /api/registros │
                 Abre puerta ──────────────────────►│
                 (incluye JWT)                       │
                        │                            │
                        │  Publica MQTT ┐ ┐ ┐      │
                        │  ESP32 abre   │ │ │      │
                        │◄──── Confirmación ────────│
                        │                            │
    Actualiza           │                            │
    pantalla ✅ OK      │                            │
    (tiempo real)       │                            │
```

---

## 🎯 RESUMEN SIMPLE

| Elemento | Qué es | Dónde vive |
|----------|--------|-----------|
| **Frontend** | Pantallas, botones, formularios | Navegador (Chrome, Edge, etc.) |
| **Backend** | Servidor que procesa datos | Computadora (localhost:8000) |
| **BD** | Donde se guardan datos | Archivo `instance/app.db` |
| **MQTT** | Comunica con ESP32 | Puerto 1883 |
| **ESP32** | Placa Arduino que abre la puerta | Conectada por WiFi |

### 📱 Lo que ve el Usuario (Frontend):
```
Login → Dashboard → Elegir opción → Ver resultado
```

### 🔧 Lo que hace el Backend por detrás:
```
Recibe petición → Verifica seguridad → Procesa datos → 
Consulta/Modifica BD → Responde al Frontend
```

### ⚡ Cuando presiona ABRIR:
```
Frontend dice "abre" → Backend recibe → 
Publica en MQTT → ESP32 recibe → 
Activa TRIAC → Cerradura abre 🔓
```

---

## 🔐 DATOS FLUYEN SEGURO

```
Usuario escribe contraseña
             ↓
Frontend NO envía texto plano
Frontend ENCRIPTA datos
             ↓
Protección: HTTPS (en producción)
             ↓
Backend recibe datos encriptados
Backend DESENCRIPTA
Backend VALIDA
Backend PROCESA
             ↓
BD guarda datos ENCRIPTADOS
No se ve en texto plano
             ↓
Respuesta ENCRIPTADA al Frontend
```

---

**¡Así de simple funciona todo el sistema!**
