# 🔐 Control de Acceso a Visitantes — Implementación Completada

**Fecha**: 23/03/2026  
**Estado**: ✅ IMPLEMENTADO

---

## 📋 Requisito

Los **VISITANTES** (terceros, personas no registradas en SENA) **NO pueden** registrar su propia entrada ni salida desde el panel de ingreso de aprendices.

Únicamente el **VIGILANTE** (desde el panel de vigilancia) puede:
- Registrar la entrada de un visitante
- Registrar la salida de un visitante

---

## 🔧 Cambios Implementados

### 1. **Backend** — Validaciones en Routes

#### Endpoint: `POST /api/personas`
**Validación Agregada:**
```python
if perfil_solicitado.upper() == 'VISITANTE':
    usuario_actual = Usuario.query.get(usuario_id)
    if not usuario_actual or usuario_actual.rol != 'vigilante':
        return jsonify({
            'error': 'No tienes permiso para registrar visitantes. 
                     Solo los vigilantes pueden registrar visitantes 
                     desde el panel de vigilancia.'
        }), 403
```

**Comportamiento:**
- ✅ Vigilante registra un visitante → **Éxito (201)**
- ❌ Aprendiz intenta registrar un visitante → **Rechazado (403)**
- ❌ Instructor intenta registrar un visitante → **Rechazado (403)**

---

#### Endpoint: `POST /api/registros-acceso`
**Validación Agregada:**
```python
if persona.perfil.upper() == 'VISITANTE':
    usuario_actual = Usuario.query.get(usuario_id)
    if not usuario_actual or usuario_actual.rol != 'vigilante':
        return jsonify({
            'error': 'No tienes permiso para registrar acceso de visitantes. 
                     Solo los vigilantes pueden hacerlo desde el panel de vigilancia.'
        }), 403
```

**Comportamiento:**
- Si alguien intenta registrar entrada/salida de un visitante sin ser vigilante → **Rechazado (403)**
- Solo el vigilante puede registrar acceso de visitantes

---

#### Endpoint: `POST /api/registros-acceso/manual`
**Validación Agregada:**
```python
# Si la persona NO EXISTE (sería visitante) → Solo vigilante
if not persona and not usuario_actual.rol == 'vigilante':
    return jsonify({'error': '...'}, 403)

# Si la persona EXISTS y es VISITANTE → Solo vigilante
if persona.perfil.upper() == 'VISITANTE' and usuario_actual.rol != 'vigilante':
    return jsonify({'error': '...'}, 403)
```

**Comportamiento:**
- Vigilante crea y registra visitante nuevo → **Éxito (201)**
- Aprendiz intenta crear/registrar visitante nuevo → **Rechazado (403)**

---

#### Endpoint: `POST /api/registros-acceso-offline`
**Validación Agregada:**
```python
if not persona and nombre:  # Sería visitante nuevo
    return jsonify({
        'error': 'No se puede sincronizar registro de visitante. 
                 Los visitantes deben ser registrados por el vigilante...'
    }), 403

if persona.perfil.upper() == 'VISITANTE':  # Visitante existente
    return jsonify({
        'error': 'Los visitantes no pueden registrar acceso desde 
                 aplicaciones offline...'
    }), 403
```

**Comportamiento:**
- ❌ Un visitante NO puede registrarse en modo offline
- ❌ Sincronización de visitante desde offline → **Siempre Rechazado (403)**

---

### 2. **Frontend** — Mensajes de Error Mejorados

#### En `vigilancia.html` - Función `guardarVisitante()`
```javascript
if(!respPersona.ok){
    if(respPersona.status === 403){
        msgEl.textContent='⛔ Acceso Denegado: Solo los vigilantes pueden 
                           registrar visitantes. Por favor, dirígete al 
                           panel del vigilante.';
    } else {
        msgEl.textContent='❌ '+(dataPersona.error||'Error al registrar visitante');
    }
}
```

**Resultado Visual:**
- Cuando alguien sin permisos intenta registrar visitante → Mensaje claro explicando la restricción

---

## 🧪 Pruebas

Se creó un archivo de prueba completo: `test_visitante_registro.py`

**Ejecutar:**
```bash
cd backend
python test_visitante_registro.py
```

**Pruebas Incluidas:**
1. ✅ Vigilante puede registrar visitante
2. ❌ Aprendiz NO puede registrar visitante
3. ❌ Aprendiz NO puede registrar acceso de visitante
4. ❌ Aprendiz NO puede crear visitante manual
5. ❌ Visitante NO puede sincronizar offline

---

## 📊 Flujo Correcto de Visitantes

```
┌─────────────────────────────────────────────────────────────┐
│                    VISITANTE LLEGA                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📍 PANEL DE INGRESO (Aprendices)                         │
│     └─► ❌ Visitante NO puede registrarse aquí            │
│                                                             │
│  👤 PANEL DE VIGILANCIA                                    │
│     ├─► VIGILANTE registra ENTRADA del visitante          │
│     │   • Nombre, Documento, Motivo, etc.                 │
│     │   • ✅ Visitante entra al edificio                  │
│     │                                                      │
│     └─► VIGILANTE registra SALIDA del visitante           │
│         • ✅ Visitante sale del edificio                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 Perfiles del Sistema

| Perfil | Panel Acceso | Puede Registrar Visitantes | Puede Acceder a Registros |
|--------|-------|---------------------------|---------------------------|
| **APRENDIZ** | Sí ✅ | No ❌ | Solo propios |
| **INSTRUCTOR** | Sí ✅ | No ❌ | De su clase |
| **VIGILANTE** | Sí ✅ | **Sí ✅** | Todos |
| **ADMINISTRADOR** | No | No | Todos |
| **VISITANTE** | **No ❌** | N/A | No |

---

## 🛡️ Seguridad

✅ **Implementado:**
- Solo vigilantes pueden crear registros de visitantes
- Solo vigilantes pueden registrar acceso de visitantes
- Validación en all entry points (POST, manual, offline)
- Mensajes de error claros y amigables
- Logging de intentos denegados

---

## 📝 Archivos Modificados

1. **backend/routes.py**
   - Validación en `POST /api/personas`
   - Validación en `POST /api/registros-acceso`
   - Validación en `POST /api/registros-acceso/manual`
   - Validación en `POST /api/registros-acceso-offline`

2. **frontend/vigilancia.html**
   - Mejora de mensajes de error en `guardarVisitante()`

3. **test_visitante_registro.py** (NUEVO)
   - Suite completa de pruebas

---

## ✅ Verificación

Para verificar que todo funciona:

```bash
# 1. Iniciar servidor
cd backend
python app.py

# 2. En otra terminal, ejecutar pruebas
cd backend
python test_visitante_registro.py

# 3. En navegador, intentar registrar visitante desde panel de aprendices
# → Deberá mostrar error 403 de acceso denegado
```

---

**Conclusión:** Los visitantes ahora están completamente separados del sistema de auto-registro. Solo el vigilante puede manejar sus entradas y salidas desde el panel de vigilancia. 🔒
