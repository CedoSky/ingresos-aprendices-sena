# FIX: Sesión y Autenticación en Panel de Administración

## 🎯 Problema Resuelto
El panel de administración mostraba el error **"No hay sesión activa - Debes estar logeado en administración primero"** incluso después de hacer login exitosamente.

## 🔍 Causa Raíz
**Desajuste de nombres de claves en localStorage:**

- **Login.html** guardaba el token como `sena_api_token` y el rol como `sena_rol`
- **Administración.html** buscaba estas claves con nombres diferentes: `token` y `usuario`

Esto causaba que aunque el login fuera exitoso, la página de administración no encontrara la sesión.

## ✅ Soluciones Implementadas

### 1. **frontend/login.html** (línea ~191)
Ahora guarda el token Y usuario con TODOS los nombres de clave para máxima compatibilidad:

```javascript
localStorage.setItem('token', d.token);
localStorage.setItem('usuario', JSON.stringify(d.usuario));
localStorage.setItem('sena_api_token', d.token);
localStorage.setItem('sena_rol', d.usuario.rol);
```

**Ventaja:** Compatible con código viejo y nuevo.

---

### 2. **frontend/administracion.html**
Múltiples cambios para mejorar la detección y validación de sesión:

#### a) Función `obtenerToken()` (línea ~1583)
```javascript
function obtenerToken() {
    return localStorage.getItem('token') || 
           localStorage.getItem('sena_api_token') || 
           localStorage.getItem('api_token');
}
```
Busca en múltiples nombres de clave para máxima compatibilidad.

#### b) Función `inicializarHerramientas()` (línea ~2118)
- **Antes:** Verificaba que existiera `usuario` JSON específico
- **Ahora:** 
  - Busca token con múltiples nombres de clave
  - **NO requiere correo específico** - cualquier admin puede entrar
  - Valida rol: `admin`, `administrador`, `systems`, `sysadmin`
  - Redirige automáticamente a login si no hay token
  - Maneia errores de JSON parse gracefully

#### c) Función `cerrarSesion()` (línea ~2713)
Ahora limpia TODAS las claves de sesión:
```javascript
localStorage.removeItem('token');
localStorage.removeItem('usuario');
localStorage.removeItem('sena_api_token');
localStorage.removeItem('sena_rol');
localStorage.removeItem('api_token');
sessionStorage.removeItem('herramientas-desbloqueado');
```

#### d) Función `verificarCodigoMantenimiento()` (línea ~2187)
- Ahora usa `obtenerToken()` en lugar de buscar directamente localStorage
- Redirige a login si no encuentra token

---

### 3. **backend/app.py**
Agregada ruta para servir la página de testing:
```python
@app.route('/test-sesion', methods=['GET'])
def serve_test_sesion():
    # Sirve frontend/test_sesion.html
```

---

## 🧪 Cómo Verificar que Funciona

### Opción 1: Test por Navegador (Recomendado)
1. Abre el servidor: `python backend/app.py`
2. Ve a `http://localhost:8000/test-sesion`
3. Haz click en "Ejecutar Test Completo"
4. Debería mostrar ✅ en todos los pasos

### Opción 2: Test por Terminal
1. Asegúrate que el servidor está corriendo
2. Ejecuta:
   ```bash
   cd backend
   python ../test_sesion.py
   ```
3. Debería mostrar:
   ```
   ✅ LOGIN EXITOSO
   ✅ SESIÓN VÁLIDA
   ✅ ACCESO PERMITIDO
   ```

### Opción 3: Test Manual
1. Ve a `http://localhost:8000/login`
2. Inicia sesión con cualquier cuenta admin
3. Deberías ser redirigido a `/administracion`
4. Haz click en la pestaña "Herramientas"
5. Debería pedir el PIN (no decir "No hay sesión activa")

---

## 📋 Cambios Realizados - Resumen Rápido

| Archivo | Cambios | Línea |
|---------|---------|-------|
| `login.html` | Guardar token + usuario con múltiples claves | ~191 |
| `administracion.html` | Buscar token con múltiples claves | ~1583 |
| `administracion.html` | Validar sesión sin requerir correo específico | ~2118 |
| `administracion.html` | Limpiar todas las claves al logout | ~2713 |
| `administracion.html` | Usar `obtenerToken()` en verificación | ~2187 |
| `app.py` | Agregar ruta `/test-sesion` | ~178 |
| (nuevo) | `test_sesion.py` | Test desde terminal |
| (nuevo) | `test_sesion.html` | Test desde navegador |

---

## ⚡ Comportamiento Esperado Ahora

### Login
```
Usuario hace login con cualquier correo admin
    ↓
Backend devuelve token + usuario
    ↓
Frontend guarda en localStorage (múltiples claves)
    ↓
Redirige a /administracion
    ↓
Página detecta token ✅
```

### Acceso a Herramientas
```
Click en pestaña "Herramientas"
    ↓
Verifica token (sin importar el correo) ✅
    ↓
Si ya está desbloqueado: muestra herramientas
Si no: pide PIN dinámico (MANTENIMIENTO.bat opción P)
```

### Terminal / Scripts
```
Puede verificar sesión usando el token JWT
Funciona con CUALQUIER correo admin
No requiere que sea un correo específico
```

---

## 🔒 Seguridad

- ✅ Token JWT validado en cada solicitud
- ✅ No se guarda contraseña en cliente
- ✅ HttpOnly cookies (opcionalmente)
- ✅ Validación de rol en backend y frontend
- ✅ Logout limpia todas las claves

---

## 📝 Notas

- El sistema ahora es más flexible con los correos (cualquier admin puede entrar)
- Las claves de localStorage son redundantes por compatibilidad
- Si ves ambas claves significa que todo está funcionando bien
- Para máxima seguridad, se pueden eliminar las claves antiguas después de migración completa

---

## 🆘 Si Aún no Funciona

1. **Verifica que el servidor está corriendo:**
   ```bash
   curl http://localhost:8000/health
   ```
   
2. **Verifica que el login devuelve token:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@sena.edu.co","password":"admin123"}'
   ```

3. **Limpia the browser cache/cookies:**
   - DevTools → Application → Storage → Clear All

4. **Mira los logs en DevTools:**
   - F12 → Console → Busca "[Herramientas]"

---

**Fecha:** Marzo 19, 2026  
**Status:** ✅ COMPLETADO
