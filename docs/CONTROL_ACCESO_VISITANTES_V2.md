# 🔐 Control de Acceso a Visitantes — Implementación Completada v2

**Fecha**: 23/03/2026  
**Estado**: ✅ IMPLEMENTADO

---

## 📋 Requisitos

Los **VISITANTES** (terceros, personas no registradas en SENA) están **completamente aislados del sistema**:

1. ✅ **NO pueden acceder al panel de ingreso** (ingreso_sin_dispositivos.html)
2. ✅ **NO pueden registrarse a sí mismos** desde ningún lugar  
3. ✅ **NO pueden registrar entrada/salida** sin el vigilante
4. ✅ **SOLO el VIGILANTE los maneja** desde el panel de vigilancia

---

## 🔧 Cambios Implementados

### 1. **Bloqueo de Acceso a Panel de Ingreso** 🚫

#### Nuevo Endpoint: `GET /api/auth/validar-acceso-ingreso`

**Backend (routes.py):**
```python
@api_bp.route('/auth/validar-acceso-ingreso', methods=['GET'])
@token_required
def validar_acceso_ingreso(usuario_id):
    """
    Valida si el usuario puede acceder al panel de ingreso.
    RECHAZA visitantes.
    """
    usuario = Usuario.query.get(usuario_id)
    
    if usuario.rol.upper() == 'VISITANTE':
        return jsonify({
            'permitido': False,
            'error': 'Los visitantes no pueden acceder a este panel. 
                     Dirígete al vigilante para registrar tu entrada.'
        }), 403  # ← Rechazado
    
    return jsonify({
        'permitido': True,
        'rol': usuario.rol
    }), 200  # ← Autorizado
```

**Frontend (ingreso_sin_dispositivos.html):**
```javascript
window.addEventListener('load', async function() {
    // Validar que el usuario pueda acceder
    var respValidar = await fetch('/api/auth/validar-acceso-ingreso', {
        headers: { 'Authorization': 'Bearer ' + token }
    });
    
    if (!respValidar.ok && respValidar.status === 403) {
        // ⛔ Visitante detectado → Bloquear
        mostrarBloqueo('Los visitantes no pueden usar este panel');
        setTimeout(() => { window.location.href = '/login.html'; }, 5000);
        return;
    }
    
    // ✅ Usuario autorizado → Continuar
    cargarPersonasCache();
});
```

**Flujo:**
```
VISITANTE abre ingreso_sin_dispositivos.html
    ↓
[Carga página] → Valida acceso en backend
    ↓
GET /api/auth/validar-acceso-ingreso
    ↓
¿Rol = VISITANTE? SÍ
    ↓
Retorna: 403 Forbidden
    ↓
Frontend bloquea:
┌──────────────────────────────┐
│ ⛔ ACCESO DENEGADO            │
│                              │
│ Los visitantes no pueden     │
│ acceder a este panel.        │
│ Dirígete al vigilante.       │
│                              │
│ Redirigiendo... (5 seg)      │
└──────────────────────────────┘
```

---

### 2. **Validaciones en Registro de Visitantes**

#### Endpoint: `POST /api/personas` 
- ✅ Si eres vigilante: Creas visitante (201)
- ❌ Si NO eres vigilante: Rechazado (403)

#### Endpoint: `POST /api/registros-acceso`
- ✅ Si eres vigilante: Registras acceso de visitante (201)
- ❌ Si NO eres vigilante: Rechazado (403)

#### Endpoint: `POST /api/registros-acceso/manual`
- ✅ Si eres vigilante: Creas y registras visitante (201)
- ❌ Si NO eres vigilante: Rechazado (403)

#### Endpoint: `POST /api/registros-acceso-offline`
- ❌ Visitante NUNCA puede sincronizar: Rechazado (403)

---

## 📊 Matriz de Acceso

| Recurso | APRENDIZ | INSTRUCTOR | VIGILANTE | VISITANTE |
|---------|----------|-----------|----------|----------|
| **Panel Ingreso** | ✅ Sí | ✅ Sí | ✅ Sí | **❌ NO** |
| **Crear Visitante** | ❌ No | ❌ No | ✅ Sí | **❌ NO** |
| **Registrar Visitante** | ❌ No | ❌ No | ✅ Sí | **❌ NO** |
| **Propia Entrada/Salida** | ✅ Sí | ✅ Sí | ❌ No | **❌ NO** |
| **Syncro Offline** | ✅ Sí | ✅ Sí | ❌ No | **❌ NO** |

---

## 🛡️ Capas de Seguridad

```
1️⃣ FRONTEND (ingreso_sin_dispositivos.html)
   └─ Valida token en load
   └─ Llama GET /api/auth/validar-acceso-ingreso
   └─ Si 403 → Bloquea UI + redirige

2️⃣ BACKEND (routes.py)
   ├─ POST /api/personas
   │  └─ ¿Perfil=visitante? → Solo vigilante
   ├─ POST /api/registros-acceso
   │  └─ ¿Persona.perfil=visitante? → Solo vigilante
   ├─ POST /api/registros-acceso/manual
   │  └─ ¿Visitante nuevo? → Solo vigilante
   └─ POST /api/registros-acceso-offline
      └─ ¿Visitante? → Rechazar siempre

3️⃣ BASE DE DATOS
   └─ persona.perfil = 'VISITANTE'
   └─ NO tiene Usuario para login
```

---

## 🧪 Casos de Prueba

### ✅ Caso 1: Aprendiz Accede Normalmente
```
1. Aprendiz abre ingreso_sin_dispositivos.html
2. Frontend: GET /api/auth/validar-acceso-ingreso
3. Backend retorna: 200 ✅ {"permitido": true}
4. Frontend: Carga página normalmente
5. Aprendiz puede registrar su entrada/salida
```

### ❌ Caso 2: Visitante Bloqueado en Acceso
```
1. Visitante abre ingreso_sin_dispositivos.html
2. Frontend: GET /api/auth/validar-acceso-ingreso
3. Backend retorna: 403 ❌ {"permitido": false, "error": "..."}
4. Frontend: Muestra panel de bloqueo
5. Frontend: Redirige a login en 5 segundos
```

### ✅ Caso 3: Vigilante Registra Visitante
```
1. Vigilante abre panel de vigilancia
2. Clic en "👤 Visitante"
3. Completa: Nombre, Documento, Motivo, etc.
4. Click "Registrar Entrada"
5. POST /api/personas → 201 ✅
6. POST /api/registros-acceso → 201 ✅
7. Visitante registrado con ENTRADA
```

---

## 📝 Archivos Modificados

1. **backend/routes.py**
   - ✅ Nuevo: GET /api/auth/validar-acceso-ingreso
   - ✅ Mejorado: POST /api/personas (validar perfil visitante)
   - ✅ Mejorado: POST /api/registros-acceso (validar perfil visitante)
   - ✅ Mejorado: POST /api/registros-acceso/manual (vigilante only)
   - ✅ Mejorado: POST /api/registros-acceso-offline (rechazar visitantes)

2. **frontend/ingreso_sin_dispositivos.html**
   - ✅ Validación en window.load
   - ✅ Bloqueo visual para visitantes
   - ✅ Redireccionamiento automático

---

## 🚀 Verificación Rápida

**Abrir navegador devtools y ejecutar:**
```javascript
// Test 1: Ver qué rol tenemos
var token = localStorage.getItem('sena_api_token');
fetch('/api/auth/me', {
    headers: { 'Authorization': 'Bearer ' + token }
}).then(r => r.json()).then(d => console.log(d));

// Test 2: Validar acceso a panel de ingreso
fetch('/api/auth/validar-acceso-ingreso', {
    headers: { 'Authorization': 'Bearer ' + token }
}).then(r => r.json()).then(d => console.log(d));
```

---

## ✅ Checklist de Implementación

- [x] Endpoint GET /api/auth/validar-acceso-ingreso creado
- [x] Validación en POST /api/personas
- [x] Validación en POST /api/registros-acceso
- [x] Validación en POST /api/registros-acceso/manual
- [x] Validación en POST /api/registros-acceso-offline
- [x] Frontend valida en load
- [x] Frontend bloquea visitantes
- [x] Frontend redirige automáticamente
- [x] Documentación completada

---

**Conclusión:** 

Los visitantes están **completamente herméticamente aislados**:
- ❌ No pueden usar panel de ingreso
- ❌ No pueden ni siquiera llegar a la pantalla
- ❌ Son bloqueados inmediatamente en load
- ❌ Solo el vigilante los maneja desde su panel

🔒 **Sistema Seguro**
