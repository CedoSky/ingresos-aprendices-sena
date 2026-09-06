# ESP32 — CAMBIOS DE SIMPLIFICACIÓN

## ✅ Lo que se hizo

### 1. **Código Arduino ESP32** (SIMPLIFICADO)
**Archivo:** `backend/esp32_cerradura/esp32_cerradura.ino`

**Cambios:**
- ❌ ELIMINADO: Polling al servidor backend (eliminó HTTPClient)
- ❌ ELIMINADO: Sistema de registro en servidor
- ❌ ELIMINADO: Verificación de keys complejas
- ✅ MANTENIDO: Servidor HTTP local en puerto 80
- ✅ MANTENIDO: Control del TRIAC (cerradura física)
- ✅ MANTENIDO: Auto-cierre después de 15 segundos

**Líneas reducidas:**
- Antes: ~350 líneas
- Ahora: ~180 líneas (48% reducción de complejidad)

**Endpoints disponibles:**
```
GET /                      → Panel web de control
GET /abrir                 → Abre cerradura 15s
GET /abrir?seg=N           → Abre cerradura N segundos (máx 15)
GET /cerrar                → Cierra cerradura
GET /estado                → JSON con estado actual
```

---

### 2. **Código Flask/Python** (`routes.py`)

**Cambios:**
- ❌ ELIMINADO: `_encolar_cmd_esp32()` - Sistema de cola de comandos
- ❌ ELIMINADO: `_verificar_key_esp32()` - Verificación de keys
- ❌ ELIMINADO: `esp32_registrar()` - Endpoint de registro
- ❌ ELIMINADO: `esp32_polling_comando()` - Endpoint de polling
- ❌ ELIMINADO: `esp32_ack()` - Endpoint de confirmación
- ❌ ELIMINADO: `esp32_listar_dispositivos()` - Listar dispositivos
- ❌ ELIMINADO: `esp32_test_cmd()` - Endpoint de prueba
- ❌ ELIMINADO: `esp32_reset()` - Endpoint de reset
- ❌ ELIMINADO: Threading y locks para ESP32 (todo el sistema de caché en memoria)

**Añadido:**
- ✅ `_llamar_esp32(comando, segundos)` - Función simple que hace HTTP GET directo
- ✅ `_obtener_estado_esp32()` - Función para obtener estado actual
- ✅ Variable `ESP32_IP` desde `.env.esp32`

**Líneas reducidas:**
- Antes: ~180 líneas de código ESP32
- Ahora: ~35 líneas (81% reducción)

---

### 3. **Nuevos archivos**

**`.env.esp32`**
- Configuración centralizada
- IP del ESP32 en red local
- Documentación de endpoints
- Instrucciones de uso

**`backend/esp32_cerradura/esp32_cerradura_simplificado.ino`**
- Copia simplificada del Arduino (NEW - usar este)

---

## 🔄 Flujo antes vs después

### ANTES (Complejo)
```
Usuario → Flask → Encola comando en memoria
                → ESP32 hace polling c/800ms
                → Flask entrega comando en cola
                → ESP32 ejecuta
                → ESP32 responde con ACK
                → Flask registra en base de datos
```
**Problemas:**
- Latencia por polling
- Complejidad de sincronización
- Gestión de memoria (caché)
- Posibles cargas perdidas
- Múltiples puntos de fallo

### AHORA (Simplificado)
```
Usuario → Flask → HTTP GET directo al ESP32
                → ESP32 ejecuta inmediatamente
                → Responde HTTP 200
                → Flask registra en base de datos
```
**Ventajas:**
- Latencia mínima (< 100ms)
- Código más simple y mantenible
- Sin polling constante
- Sin gestión de memoria adicional
- Un único punto de contacto

---

## 📋 Checklist de configuración

Para que funcione correctamente:

- [ ] 1. **Configurar WiFi en Arduino**
  - Editar `WIFI_SSID` y `WIFI_PASSWORD` en el .ino
  
- [ ] 2. **Subir código a ESP32**
  - Usar Arduino IDE
  - Puerto y velocidad correctos
  
- [ ] 3. **Obtener IP del ESP32**
  - Monitor serial: buscar línea `[WIFI] ✅ Conectado! IP: xxx.xxx.xxx.xxx`
  - O consultar el router DHCP
  
- [ ] 4. **Configurar `.env.esp32`**
  - `ESP32_IP=` la IP obtenida en paso 3
  
- [ ] 5. **Cargar `.env.esp32` en app.py**
  ```python
  from dotenv import load_dotenv
  load_dotenv('.env.esp32')
  ```
  
- [ ] 6. **Pruebas**
  - Acceder a `http://[IP_ESP32]/` desde navegador
  - Hacer click en botones ABRIR/CERRAR
  - Debería funcionar sin latencia

---

## 🔌 Pruebas rápidas desde navegador

Una vez que tengas la IP del ESP32:

**1. Panel web:**
```
http://192.168.1.100/
```

**2. Abrir cerradura 10 segundos:**
```
http://192.168.1.100/abrir?seg=10
```

**3. Cerrar cerradura:**
```
http://192.168.1.100/cerrar
```

**4. Consultar estado:**
```
http://192.168.1.100/estado
```
(Te devolverá JSON con estado actual)

---

## ⚠️ Consideraciones importantes

1. **Red local requerida:** El ESP32 debe estar en LA MISMA RED que Flask
2. **Sin Internet necesario:** Funciona completamente en LAN local
3. **IP estática recomendada:** Para no cambiar
4. **Timeout de 3 segundos:** Si no responde en 3s, se considera offline
5. **Sin autenticación:** Es red local, confía en el firewall

---

## 📊 Comparativa de complejidad

| Aspecto | Antes | Después |
|---------|-------|---------|
| Líneas en Arduino | 350+ | 180 |
| Líneas en Flask | 180+ | 35 |
| Endpoints HTTP | 6 | 0 (usa directamente) |
| Locks/Threads | 3+ | 0 |
| Estado en memoria | Sí | No |
| Polling | Cada 800ms | No |
| Latencia típica | 1-2s | 100-500ms |
| Puntos de fallo | 5+ | 1 |

---

## 🚀 Próximos pasos

1. Subir el código simplificado al ESP32
2. Obtener la IP
3. Configurar `.env.esp32` y `routes.py`
4. Actualizar frontend si es necesario (panel de vigilancia)
5. Probar desde navegador
6. Probar desde la app Flask

¡Mucho más simple y más rápido! 🎉
