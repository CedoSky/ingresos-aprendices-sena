# 🔧 FIX: Personal de Aseo - Búsqueda y Registro

## ❌ Problema Reportado
Los usuarios de **Personal de Aseo** creados en la página de administración no se podían registrar en el panel del vigilante:
- El botón "Registrar Entrada" permanecía deshabilitado (opaco)
- La búsqueda no encontraba a la persona
- No se podía activar el acceso

## 🔍 Causa Identificada
El endpoint backend `/api/personas/buscar-por-documento` devolvía una estructura JSON **INCOMPATIBLE** con lo que esperaba el frontend. Además, había inconsistencia en el código frontend: algunos lugares esperaban la estructura antigua `{'nombre': ..., 'perfil': ...}` y otros la estructura con `{'persona': {...}}`.

### Respuesta INCORRECTA (anterior):
```json
{
  "found": true,
  "id": "uuid-aqui",
  "nombre": "Juan Pérez",
  "numero_doc": "1234567890",
  "perfil": "personal_aseo"
}
```

### Respuesta CORRECTA (actualizada):
```json
{
  "persona": {
    "id": "uuid-aqui",
    "nombre": "Juan Pérez",
    "numero_doc": "1234567890",
    "perfil": "personal_aseo",
    "email": "...",
    "telefono": "...",
    "especialidad": "...",
    "area": "..."
  }
}
```

### Por qué fallaba:
En `frontend/vigilancia.html` línea 2544 y 2559, el código verifica:
```javascript
if(!resp.ok || !data.persona){  // ← data.persona era UNDEFINED
    // Mostrar error y deshabilitar botones
    return;
}
var persona=data.persona;  // ← Fallaba aquí
```

## ✅ Soluciones Aplicadas

### 1. Backend - Respuesta Consistente
**Archivo**: `backend/routes.py` (líneas 548-578)

Actualizado el endpoint `/api/personas/buscar-por-documento` para:
- Devolver la estructura correcta con la clave `"persona"` 
- Incluir todos los campos necesarios (email, telefono, especialidad, area, etc)
- Proporcionar una respuesta consistente para todos los casos de uso

### 2. Frontend - Código Consistente
**Archivo**: `frontend/vigilancia.html`

Estandarizados dos lugares que accedían directamente a propiedades sin la envoltura `persona`:

**Línea ~1572 (Salida de Visitante)**:
```javascript
// ANTES (INCORRECTO):
var visitante=await searchResp.json();
if(visitante.perfil!=='visitante'){ ... }
msgEl.textContent='✅ ... '+visitante.nombre;

// DESPUÉS (CORRECTO):
var data=await searchResp.json();
var visitante=data.persona;  // ← Ahora accede a persona
if(visitante.perfil!=='visitante'){ ... }
msgEl.textContent='✅ ... '+visitante.nombre;
```

**Línea ~2465 (Entrada de Visitante - Modal)**:
```javascript
// ANTES (INCORRECTO):
if(resp.ok && visitante && visitante.nombre && visitante.perfil==='visitante'){ 
    document.getElementById('vis-salida-nombre').textContent=visitante.nombre;
}

// DESPUÉS (CORRECTO):  
if(resp.ok && data && data.persona && data.persona.nombre && data.persona.perfil==='visitante'){
    document.getElementById('vis-salida-nombre').textContent=data.persona.nombre;
}
```

## 🚀 Pruebas Después del Fix

### Paso 1: Reiniciar el servidor
```bash
# En la terminal donde corre el backend
# Presiona CTRL+C para detenerlo
# Luego reinicia con:
python backend/app.py
# O si usas run.bat desde backend/
```

### Paso 2: Limpiar caché del navegador
1. Abre DevTools: **F12** o **Ctrl+Shift+I**
2. Botón derecho en el botón "Actualizar" → **Vaciar caché y hacer recarga completa**

### Paso 3: Crear Personal de Aseo (Administración)
1. Abre `frontend/administracion.html`
2. Selecciona perfil: **🧹 Personal de Aseo**
3. Completa nombre y documento
4. Haz clic en "Registrar Persona Nueva"
5. Verifica que aparezca en la lista

### Paso 4: Buscar en Vigilancia
1. Abre `frontend/vigilancia.html` en otra pestaña
2. Haz clic en el botón **🧹 Aseo**
3. Ingresa el número de documento del personal
4. Presiona **Enter** o espera a que se autocomplete

### Paso 5: Verificar Activación de Botones
✅ Debe suceder:
- ✓ El nombre y documento se muestran en la caja de información
- ✓ El botón "↓ Registrar Entrada" se activa (color verde completo, cursor normal)
- ✓ El botón "↑ Registrar Salida" se activa (color rojo completo, cursor normal)
- ✓ Los botones responden al click
- ✓ No hay mensaje de error

❌ Si no pasa: Revisa la consola del navegador (F12 → Console)

### Paso 6: Registrar Entrada
1. Con los botones activados, haz clic en "↓ Registrar Entrada"
2. **Esperado**: Mensaje en verde: "✅ Entrada registrada exitosamente"
3. Los campos se limpian automáticamente
4. En **"Personal de Aseo Activo"** debe aparecer la persona

### Paso 7: Registrar Salida
1. Opción A: Volver a buscar el documento y hacer clic en "↑ Registrar Salida"
2. Opción B: Hacer clic en "↑ Registrar Salida" desde la lista de "Personal de Aseo Activo"
3. **Esperado**: Mensaje verde: "✅ Salida registrada exitosamente"

### Paso 8: Prueba con Visitantes (Bonus)
Para verificar que la fix también funciona con visitantes:
1. Crea un visitante en la página del vigilante (botón "👤 Visitante")
2. Intenta registrar su entrada/salida
3. Debería funcionar correctamente también

## 📊 Verificación en Base de Datos (Opcional)

Para confirmar que los datos se guardan correctamente:
```sql
-- Buscar personal de aseo
SELECT id, nombre, numero_doc, perfil FROM personas WHERE perfil = 'personal_aseo';

-- Ver registros de acceso de personal de aseo
SELECT p.nombre, p.numero_doc, r.tipo, r.timestamp 
FROM registros_acceso r
JOIN personas p ON r.persona_id = p.id
WHERE p.perfil = 'personal_aseo'
ORDER BY r.timestamp DESC
LIMIT 10;
```

## 🐛 Troubleshooting

### El botón sigue deshabilitado
- [ ] Limpié caché con F12 → Vaciar caché y recarga?
- [ ] Reinicié el servidor Python?
- [ ] El documento está registrado en "Personal de Aseo" (no otro perfil)?
- [ ] En la BD, ¿el perfil es exactamente 'personal_aseo'?

### Error "Personal de aseo no encontrado"
- [ ] Verifica que esté registrado en administración
- [ ] Asegúrate que el perfil sea exactamente "🧹 Personal de Aseo"
- [ ] Intenta con otro documento de prueba
- [ ] Revisa la consola (F12) para ver si hay más detalles del error

### Error de conexión
- [ ] Verifica que el backend esté levantado (no debería haber error 503/504)
- [ ] Abre la consola del navegador (F12) para ver errores exactos del fetch
- [ ] Verifica que la URL sea correcta (localhost:5000 o tu servidor)

### El nombre no se muestra pero funciona
- [ ] Verifica que el usuario tenga el campo `nombre` completo en la administración
- [ ] Revisa que no sea NULL en la BD

## 📝 Campos Sincronizados
Ahora todos estos campos se devuelven en el endpoint:
- ✓ id
- ✓ nombre
- ✓ numero_doc
- ✓ tipo_doc  
- ✓ perfil
- ✓ email
- ✓ telefono
- ✓ especialidad
- ✓ area
- ✓ programa
- ✓ ficha

## 📋 Resumen de Cambios

| Componente | Cambio | Líneas |
|------------|--------|--------|
| `routes.py` | Endpoint devuelve estructura `{persona: {...}}` | 548-578 |
| `vigilancia.html` | Código de salida de visitante usar `data.persona` | ~1572 |
| `vigilancia.html` | Código de entrada visitante usar `data.persona` | ~2465 |
| `vigilancia.html` | Personal de Aseo espera `data.persona` | ✓ Ya estaba correcto |

---

**Última actualización**: 2026-04-05  
**Estado**: ✅ Corregido y lista para pruebas  
**Archivos Modificados**: 2 (routes.py, vigilancia.html)  
**Cambios Totales**: 3 (1 endpoint + 2 funciones JS)
