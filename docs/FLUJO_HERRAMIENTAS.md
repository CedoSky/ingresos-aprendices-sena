# ⚠️ FLUJO CORRECTO: SISTEMA DE HERRAMIENTAS RESTRINGIDAS

## PRE-REQUISITOS
✅ Servidor Flask corriendo en http://localhost:8000
✅ Terminal/PowerShell abierta en la carpeta del proyecto

---

## PASO 1: INICIAR SESIÓN EN ADMINISTRACIÓN
1. Abre navegador → http://localhost:8000
2. Haz click en **"Panel de Administración"**
3. Login con:
   - **Email**: `admin@sena.edu.co`
   - **Contraseña**: `admin123`
4. ✅ Deberías ver el Panel con 8 pestañas

---

## PASO 2: ACCEDER A HERRAMIENTAS
1. En el panel, haz click en la pestaña **"Herramientas"** (última pestaña, ícono de llave inglesa 🔧)
2. Deberías ver:
   - Un **candado rojo 🔒** con "Acceso Restringido"  
   - Un campo de entrada para "Código de mantenimiento"
   - Botón "Desbloquear"

⚠️ Si ves "no hay sesión activa":
   → Significa que NO hiciste login correctamente
   → Vuelve a Paso 1 y asegúrate de estar logeado

---

## PASO 3: GENERAR PIN EN TERMINAL
1. Abre **PowerShell** o **CMD**
2. Navega a la carpeta del proyecto:
   ```powershell
   cd "c:\ruta\del\proyecto"
   ```
3. Ejecuta:
   ```batch
   MANTENIMIENTO.bat
   ```
4. Deberías ver un menú. Selecciona opción: **P**
5. El sistema mostrará algo como:
   ```
   ┌─────────────────────────────────────┐
   │ Codigo actual: 702574                │
   │ Válido por: 4 minutos 32 segundos   │
   └─────────────────────────────────────┘
   ```

⏰ **IMPORTANTE**: El código cambia cada 5 minutos y es único

---

## PASO 4: INGRESAR PIN EN LA PÁGINA
1. **Copia** el código de 6 dígitos (ej: 702574) de la terminal
2. Regresa a la página del navegador 
3. **Pega** el código en el campo "Código de mantenimiento"
4. Haz click en **"Desbloquear"**
5. ✅ Si es correcto, verás:
   - Las opciones de herramientas desbloqueadas
   - Botones para: Limpiar Registros, Restaurar BD, Optimizar, etc.

---

## 🚨 TROUBLESHOOTING

### "No hay sesión activa"
→ **Solución**: Primero haz login en administración (Paso 1)

### "No veo el campo de entrada"
→ **Solución**: Asegúrate de estar en administración logeado y en la pestaña "Herramientas"

### "PIN incorrecto" después de pegar
→ **Solución**: El PIN caduca en 5 minutos. Ejecuta MANTENIMIENTO.bat opción P de nuevo

### El servidor dice "No se puede conectar"
→ **Solución**: Asegúrate que Flask esté corriendo:
```powershell
cd backend
python app.py
```

---

## ⏱️ TIMINGS
- PIN válido: 5 minutos
- Después expira automáticamente
- Sistema registra cada intento en auditoría
- Sesión desbloqueada: Mientras el navegador no se cierre

---

**Versión**: 1.0 - Sistema PIN Dinámico TOTP
**Fecha**: Marzo 2026
