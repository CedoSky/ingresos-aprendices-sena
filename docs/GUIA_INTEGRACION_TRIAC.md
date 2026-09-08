# Guía de Integración ESP32 TRIAC — Sistema de Vigil ancia SENA

## 📋 Contenido
1. [Verificación Inicial](#verificación-inicial)
2. [Configuración del ESP32](#configuración-del-esp32)
3. [Configuración del Backend](#configuración-del-backend)
4. [Uso del Panel de Vigilancia](#uso-del-panel-de-vigilancia)
5. [Solución de Problemas](#solución-de-problemas)

---

## 🔍 Verificación Inicial

### Paso 1: Compilar y cargar el código Arduino al ESP32

1. **Requisitos:**
   - Arduino IDE o VS Code con extensión PlatformIO
   - Librerías instaladas: `WiFi`, `WebServer`, `ArduinoJson`

2. **Ubicación del código:**
   - Archivo: `Arduino/esp32_triac_control/esp32_triac_control.ino`
   - **NO usar** `esp32_triac_mqtt.ino` (versión MQTT antigua)

3. **Configuración WiFi:**
   ```cpp
   const char* ssid = "iPhone de AMAT";        // Tu red WiFi
   const char* password = "Enrique1092";       // Tu contraseña
   ```

4. **Subir el código:** 
   - Conecta el ESP32 vía USB
   - Compila y sube el sketch
   - Abre el monitor serial (115200 baud) para ver los logs

5. **Verificación:**
   ```
   ✓ WiFi conectado
   IP: 172.20.10.5 (ejemplo, varía según tu red)
   ✓ Servidor HTTP iniciado en puerto 80
   ```

### Paso 2: Verificar conectividad

1. **Test desde Python (Backend):**
   ```bash
   cd backend
   python test_triac_connection.py 172.20.10.5
   ```

2. **Test desde Navegador:**
   - Abre: `http://172.20.10.5/triac/estado`
   - Debes recibir JSON con el estado del ESP32

---

## ⚙️ Configuración del ESP32

### Desde la Página de Vigilancia

1. **Accede al Panel de Vigilancia:**
   - URL: `http://localhost:8000/frontend/vigilancia.html`
   - Login con usuario vigilante o administrador

2. **Localiza "Configuración ESP32 TRIAC" (panel morado):**
   ```
   ⚙️ Configuración ESP32 TRIAC
   ├─ IP del ESP32: [172.20.10.5] [💾 Guardar] [📡 Probar]
   └─ Estado: ✅ Conectado
   ```

3. **Pasos:**
   - Ingresa la IP que viste en el monitor serial del ESP32
   - Click en "📡 Probar" para verificar la conexión
   - Si aparece ✅ CONECTADO, haz click en "💾 Guardar"

---

## 🔧 Configuración del Backend

### Variables de Entorno

Opción 1: Variable de entorno del sistema
```bash
# Windows PowerShell
$env:ESP32_IP = "172.20.10.5"

# Linux/Mac
export ESP32_IP="172.20.10.5"
```

Opción 2: Archivo `.env` en `backend/`
```
ESP32_IP=172.20.10.5
```

Opción 3: Configuración dinámica (ya está implementada)
- Se configura desde la página de vigilancia
- Se almacena en memoria del servidor mientras esté corriendo

---

## 🎮 Uso del Panel de Vigilancia

### Control Manual del TRIAC (5 pulsos)

**Panel "TRIAC — Control de pulsos"** (verde):

```
⚡ TRIAC — Control de pulsos (5 × 3s ON + 10s OFF)
├─ Estado: ✅ Conectado
├─ [⚡ INICIAR CICLO] [⏹️ PARAR]
└─ Pulso actual: 1 / 5
   Estado: ON
```

**Uso:**
1. Click en "⚡ INICIAR CICLO"
2. Sistema enviará:
   - Pulso 1: 3 segundos ON, 10 segundos OFF
   - Pulso 2: 3 segundos ON, 10 segundos OFF
   - ... (total 5 pulsos)
   - Tiempo total: ~65 segundos

3. Durante ejecución:
   - Verde parpadeante = Activo
   - Muestra pulso actual
   - Click "⏹️ PARAR" para detener

4. Al completar:
   - Mensaje de confirmación
   - Panel regresa a estado "Parado"

### Indicadores de Estado

| Indicador | Significado |
|-----------|------------|
| 🟢 Pulsante | TRIAC activado (ON) |
| ⚪ Fijo | TRIAC desactivado (OFF) |
| 🔴 Rojo | Error o desconectado |
| ⏳ Amarillo | Esperando respuesta |

---

## 🐛 Solución de Problemas

### "❌ No se puede conectar al ESP32"

**Causas probables:**
1. **ESP32 no está encendido**
   - Verifica conexión USB/alimentación
   - Revisa el monitor serial

2. **IP incorrecta**
   - Abre el monitor serial del ESP32 (115200 baud)
   - Busca la línea: `IP: XXX.XXX.XXX.XXX`
   - Cópia esa IP exacta

3. **Red WiFi diferente**
   - El ESP32 debe estar en la MISMA red WiFi que el Backend
   - Este proyecto usa: **iPhone de AMAT** (Enrique1092)
   - Si cambias de red, actualiza las credenciales en el Arduino

4. **Firewall/Router**
   - Algunos routers bloquean conexiones entre dispositivos
   - Prueba sin VPN
   - Verifica que ambos dispositivos estén en la red principal

### "⏳ Timeout: ESP32 no responde"

- ESP32 está en línea pero no responde a HTTP
- **Solución:** 
  1. Reinicia el ESP32
  2. Verifica el monitor serial para errores
  3. Recarga el código Arduino

### "✨ Comando enviado pero TRIAC no se activa"

Posibles causas:
1. **Pin GPIO5 no está correctamente conectado al TRIAC**
   - Verifica el cableado en el esquemático
   - Prueba con un LED en GPIO5

2. **Firmware Arduino desactualizado**
   - Vuelve a cargar `esp32_triac_control.ino`

3. **Sistema no está en el ambiente 203**
   - El TRIAC está configurado para activarse SOLO cuando:
     - Ambiente contiene "203" (línea ~143 en routes.py)
     - O vigilante intenta abrir específicamente ambiente 203
   - Modifica si necesitas otros ambientes

### "❌ No tienes sesión activa"

- Necesitas estar logueado como vigilante o administrador
- Login en: `http://localhost:8000/frontend/vigilancia.html`
- Credenciales de prueba (si existen en BD):
  - Usuario: `vigilante@sena.edu.co`
  - Contraseña: (la que configuraste en instalación)

---

## 📊 Monitoreo y Logs

### Logs del ESP32

En el monitor serial del Arduino IDE (115200 baud):
```
⚡ Pulso 1 ON (3s)
⏹ Pulso 1 OFF
⚡ Pulso 2 ON (3s)
⏹ Pulso 2 OFF
...
✅ CICLO TRIAC COMPLETADO - 5 Pulsos ejecutados
```

### Logs del Backend (Python)

En la consola donde corre Flask:
```
[ESP32] Comando enviado: /triac/iniciar
[ESP32] Respuesta: {'ok': True, 'en_ciclo': True, ...}
```

### Registros en Base de Datos

- Auditoría: `logs/auditoria/`
- Cada activación del TRIAC se registra
- Query: `SELECT * FROM evento_seguridad WHERE evento LIKE '%TRIAC%'`

---

## 🚀 Flujo Completo de Prueba

1. **Verificar conectividad:**
   ```bash
   python backend/test_triac_connection.py 172.20.10.5
   ```

2. **Iniciar servidor:**
   ```bash
   cd backend
   python app.py
   ```

3. **Acceder a vigilancia:**
   - URL: `http://localhost:8000/frontend/vigilancia.html`

4. **Configurar IP:**
   - Ingresa la IP del ESP32 en el panel morado
   - Click "📡 Probar" → debe mostrar ✅ Conectado

5. **Ejecutar ciclo TRIAC:**
   - Click "⚡ INICIAR CICLO"
   - Observa los pulsos en tiempo real
   - TRIAC debe activarse en GPIO5

6. **Verificar en Arduino:**
   - Monitor serial debe mostrar los pulsos
   - LED en GPIO33 debería parpadear

---

## 📞 Soporte

**Si algo no funciona:**

1. Ejecuta el test de conexión:
   ```bash
   python backend/test_triac_connection.py [IP]
   ```

2. Revisar logs:
   - Consola de Flask
   - Monitor serial del ESP32
   - `backend/logs/auditoria/`

3. Verificar cableado:
   - GPIO5 → TRIAC
   - GPIO33 → LED indicador
   - GND común

4. Reiniciar:
   - Servidor Flask: `Ctrl+C` y ejecutar de nuevo
   - ESP32: Reset botón o desconectar/reconectar USB

---

**Última actualización:** 17/03/2026  
**Sistema completado:** ✅ HTTP directo a ESP32 (sin MQTT en versión actual)
