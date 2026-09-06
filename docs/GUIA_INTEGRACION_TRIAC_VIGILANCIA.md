# 🔌 Guía de Integración TRIAC en Página de Vigilancia

## 📋 Resumen
El control TRIAC ha sido integrado en la página del vigilante (`vigilancia.html`). La funcionalidad permite activar/desactivar el TRIAC desde la interfaz web con comunicación HTTP directa al ESP32.

---

## 🚀 Cómo Usar

### 1. **Acceder al Panel TRIAC**
- En la página de vigilancia, presiona el botón: **⚡ PRUEBA TRIAC** (en la barra superior)

### 2. **Configurar IP del ESP32**
- En el campo **"IP del ESP32"** ingresa la dirección IP de tu dispositivo
  - Ejemplo: `192.168.1.100` o `172.20.10.9`
- Presiona el botón **💾 Guardar**
- La IP se guardará en el navegador (localStorage) para futuras sesiones

### 3. **Enviar Comandos**

#### **▶️ INICIAR CICLO**
- Inicia una secuencia de 5 pulsos
- Cada pulso: 3 segundos ON + 10 segundos OFF
- Duración total: ~65 segundos
- El LED GPIO33 parpadeará indicando el estado

#### **⏹️ PARAR**
- Detiene el ciclo inmediatamente
- Apaga el TRIAC (GPIO5) y el LED

#### **📊 ESTADO**
- Consulta el estado actual del TRIAC
- Muestra: ciclo activo, pulsos restantes, estado del pin

### 4. **Ver Resultados**
Los comandos enviados y sus respuestas se mostrando en la sección "ÚLTIMO RESULTADO" con:
- Timestamp de la acción
- Estado: ✅ ÉXITO o ❌ ERROR
- JSON detallado de la respuesta del ESP32

---

## 🔧 Endpoints HTTP (ESP32)

El Arduino simplificado expone 3 endpoints:

```
GET http://[IP_DEL_ESP32]/triac/iniciar
GET http://[IP_DEL_ESP32]/triac/parar
GET http://[IP_DEL_ESP32]/triac/estado
```

### **Respusta de `/triac/iniciar`**
```json
{
  "ok": true,
  "ciclo_activo": true
}
```

### **Respuesta de `/triac/parar`**
```json
{
  "ok": true,
  "ciclo_activo": false
}
```

### **Respuesta de `/triac/estado`**
```json
{
  "ciclo_activo": false,
  "pulsos_restantes": 0,
  "en_pulso": false
}
```

---

## 📦 Código Arduino Integrado

**Archivo:** `Arduino/esp32_triac_control/esp32_triac_control.ino`

**Características:**
- ✅ WiFi: "iPhone de AMAT" / "Enrique1092" (hardcodeado)
- ✅ Sin dependencia ArduinoJson (string concatenation)
- ✅ Control por Serial: "1" = iniciar, "2" = parar
- ✅ Control por HTTP: 3 endpoints GET
- ✅ Máquina de estados para timing de pulsos
- ✅ ~150 líneas de código limpio

**GPIO Configuration:**
- `GPIO5`: PIN_TRIAC (salida al relé)
- `GPIO33`: PIN_LED (indicador visual)

**Comunicación Serial:**
```
Baud: 115200
Comandos: 1 = INICIAR, 2 = PARAR
```

---

## 🌐 Frontend (JavaScript)

**Archivo:** `frontend/vigilancia.html`

**Funciones Principales:**
- `_triacCargarIP()` - Carga IP guardada del localStorage
- `_triacGuardarIP(ip)` - Guarda IP en localStorage
- `pruebaTriacIniciar()` - Envía GET a `/triac/iniciar`
- `pruebaTriacParar()` - Envía GET a `/triac/parar`
- `pruebaTriacEstado()` - Envía GET a `/triac/estado`
- `_logPruebaTriac(msg)` - Registra resultado con timestamp

**Storage:**
- Key: `esp32_triac_ip`
- Persiste en localStorage del navegador

---

## ✅ Checklist de Instalación

- [ ] Arduino compilado y cargado en ESP32
- [ ] ESP32 conectado a WiFi "iPhone de AMAT"
- [ ] IP del ESP32 anotada (ej: 192.168.1.100)
- [ ] Página vigilancia.html cargada en navegador
- [ ] Presiona botón ⚡ PRUEBA TRIAC
- [ ] Ingresa IP y presiona 💾 Guardar
- [ ] Haz clic en ▶️ INICIAR CICLO
- [ ] Verifica que el LED GPIO33 parpadee
- [ ] Consulta estado con 📊 ESTADO

---

## 🔍 Troubleshooting

### ❌ Error: "IP del ESP32 no configurada"
**Solución:** Ingresa la IP en el campo de texto y presiona 💾 Guardar

### ❌ Error: "Connection refused" o "timeout"
**Causa posible:**
- ESP32 no está encendido
- IP ingresada es incorrecta
- ESP32 no está conectado a WiFi
**Solución:** Verifica IP con: `ping [IP_DEL_ESP32]`

### ❌ El TRIAC no responde
**Checklist:**
1. ¿El LED GPIO33 parpadea cuando envías comando?
2. ¿El serial monitor muestra mensajes del ESP32?
3. ¿El cable del TRIAC está conectado a GPIO5?
4. ¿El relé recibe alimentación?

### ✅ Para debuggear
Abre el Serial Monitor del Arduino IDE:
- Baud rate: 115200
- Deberías ver logs del ESP32
- Envía: "1" (iniciar) o "2" (parar)

---

## 📚 Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `Arduino/esp32_triac_control/esp32_triac_control.ino` | ✅ Simplificado (código nuevo) |
| `frontend/vigilancia.html` | ✅ Funciones JavaScript actualizadas |
| `frontend/vigilancia.html` | ✅ Modal TRIAC mejorado |

---

## 🎯 Próximos Pasos

1. **Backend Integration (Opcional):**
   - Agregar rutas Flask para persistir la IP
   - Endpoint: `POST /api/esp32/config`
   - Almacenar en base de datos

2. **Monitoring Automático:**
   - Polling periódico al estado del TRIAC
   - Mostrar luz indicadora en tiempo real
   - Logs de auditoría

3. **Seguridad:**
   - Requerir autenticación para control HTTP
   - Validación de tokens JWT
   - Registro de quién activó el TRIAC y cuándo

---

## 📞 Soporte

Para preguntas o problemas con la integración, verifica:
1. Logs del Serial Monitor del ESP32
2. Consola del navegador (F12 → Console)
3. Estado HTTP (F12 → Network)
4. Respuesta JSON del ESP32

**Código de prueba rápida en consola del navegador:**
```javascript
fetch('http://[IP_DEL_ESP32]/triac/estado')
  .then(r => r.json())
  .then(d => console.log(d))
```

---

**Integración completada:** ✅ 17 de Marzo 2026
