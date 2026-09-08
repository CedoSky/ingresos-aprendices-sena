# Alternativas de Conexión de Cerradura - SIN ESP32

## Problema Actual
El ESP32 requiere:
- Codificación en Arduino
- Configuración WiFi
- Servidor HTTP embebido  
- Debugging remoto
- Hardware especializado

---

## OPCIÓN 1: **Relé WiFi Standalone (MÁS SIMPLE)** ✅

### Solución: Módulo Relé Inteligente con WiFi
- **Dispositivos recomendados:**
  - Sonoff Dual Relay (≈$20 USD)
  - Tuya Smart Relay 2CH (≈$15 USD)
  - Generic WiFi Smart Relay Module

### Ventajas:
✅ Viene pre-configurado (no requiere código)  
✅ Control vía app móvil o API REST directa  
✅ Compatible con MQTT y Webhook  
✅ No requiere programación Arduino  
✅ Solo conectar 3 cables (VCC, GND, Señal)  

### Integración en tu app:
```python
# En routes.py - Simplemente HTTP GET/POST
import requests

def abrir_cerradura_ambiente(ambiente, persona=None, usuario_id=None):
    """Solicita apertura al relé WiFi inteligente"""
    try:
        # Opción A: API REST simple
        response = requests.get(
            'http://192.168.1.100/cm?cmnd=Power1%20on',
            timeout=2
        )
        
        # Opción B: MQTT (si usas node-red intermedio)
        # publish_mqtt('home/cerradura/203', 'abrir')
        
        print(f"[CERRADURA] Relé activado en {ambiente}")
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo activar: {e}")
        return False
```

### Setup Físico:
```
Laptop ──WiFi──→ [Relé Inteligente] ──Cables──→ TRIAC → Cerradura
                      (IP local)
```

---

## OPCIÓN 2: **Arduino UNO + Módulo WiFi Shield**

### Hardware:
- Arduino UNO (≈$8-12)
- WiFi Shield + Antena (≈$20-25)
- Relé de 5V (≈$5)
- Total: ≈$35-40

### Ventaja vs ESP32:
✅ Código más simple y estable  
✅ Librería estándar `WiFi.h`  
✅ Menos problemas de compatibilidad  

### Desventaja:
❌ Requiere sigue siendo programación

---

## OPCIÓN 3: **Control Local Directo (SIN WiFi)**

### Concepto: Todos los dispositivos en MISMA RED local
```
Browser ─→ Flask App ─→ Relé USB directa/Paralelo
                        (mismo PC)
```

### Ventajas:
✅ 0% complejidad
✅ Cero latencia
✅ Sin dependencias WiFi
✅ Físicamente está aquí en la labTuya

### Cómo:
1. Conectar relé por **Puerto Serial USB** o **Puerto Paralelo**
2. Desde Python:
```python
import serial

def abrir_cerradura_ambiente(ambiente, ...):
    try:
        ser = serial.Serial('COM3', 9600)
        ser.write(b'OPEN\n')  # Comando simple
        ser.close()
        return True
    except:
        return False
```

3. Arduino recibe `OPEN` por serial → activa relé

---

## OPCIÓN 4: **MQTT + Node-RED (ARQUITECTURA LIGERA)**

### Setup:
```
Flask → MQTT Broker → Node-RED → Relé WiFi
        (Mosquitto)
```

### Ventajas:
✅ Escalable (agrega más dispositivos fácilmente)
✅ Desacoplado (mejor diseño)
✅ No requiere código complejo

### En Python:
```python
import paho.mqtt.client as mqtt

def abrir_cerradura_ambiente(ambiente, ...):
    client = mqtt.Client()
    client.connect('localhost', 1883)
    client.publish(f'home/cerradura/{ambiente}', 'OPEN')
    client.disconnect()
```

---

## OPCIÓN 5: **Sonoff + Switch Virtual (MÁS FÁCIL)**

### Setup:
1. Comprar Sonoff Dual Relay (≈$20)
2. Instalarlo físicamente en caja de control
3. Conectar a WiFi de la red local
4. Usar API:

```python
import requests

SONOFF_IP = "192.168.1.50"
SONOFF_DEVICE_ID = "1000ac58a6"  # De la app

def abrir_cerradura_ambiente(ambiente, ...):
    payload = {
        "deviceid": SONOFF_DEVICE_ID,
        "params": {"switch": "on"},
        "apikey": "tu-api-key"
    }
    requests.post(
        f'http://{SONOFF_IP}:8081/zeroconf/switch',
        json=payload
    )
```

---

## COMPARATIVA RÁPIDA

| Opción | Costo | Complejidad | Tiempo Setup | Recomendación |
|--------|-------|-------------|--------------|---------------|
| **Relé WiFi Inteligente** | $15-25 | ⭐ Muy baja | 5 min | 🏆 MEJOR |
| Serial USB | $5-10 | ⭐ Muy baja | 10 min | ✅ Muy buena |
| Arduino + Shield | $35-40 | ⭐⭐ Media | 30 min | ✅ Buena |
| MQTT | $20-30 | ⭐⭐⭐ Media | 45 min | ✅ Buena |
| ESP32 (actual) | $5-8 | ⭐⭐⭐⭐ Alta | 2-3 horas | ❌ Compleja |

---

## MI RECOMENDACIÓN 🎯

### **OPCIÓN 1: Relé WiFi Inteligente (Sonoff o equivalente)**

**Por qué:**
1. ✅ Conecta en 5 minutos
2. ✅ Solo 3 cables + WiFi
3. ✅ Cero código Arduino 
4. ✅ API REST súper simple
5. ✅ Compatible con app móvil gratis
6. ✅ Coste bajo ($20-25)
7. ✅ Soporte técnico disponible

**Pasos:**
```
1. Comprar Sonoff Dual Relay
2. Conectarlo a tu WiFi
3. Obtener su IP local (192.168.x.x)
4. En routes.py, reemplazar toda la lógica ESP32 por:
   requests.get(f'http://{IP}/cm?cmnd=Power1 on')
5. Listo. Se acabó.
```

### **OPCIÓN 2 (Si quieres lo más simple sin WiFi):**
Puerto Serial USB → Arduino → Relé
- Costo: $8-15
- Setup: 10 minutos
- Código Python: 5 líneas

---

## Archivos a ELIMINAR del proyecto:

```
❌ backend/esp32_cerradura/                (toda la carpeta)
❌ frontend/cerradura_local.html            (interfaz ESP32 local)
❌ js/ESP32CerraduraLocal.js               (librería JavaScript para ESP32)
❌ Secciones en routes.py:
   - esp32_registrar()
   - esp32_polling_comando()
   - esp32_ack()
   - _encolar_cmd_esp32()
   - _verificar_key_esp32()
```

---

## Próximos pasos:

¿Cuál opción te gustaría que implementemos?

- [ ] Opción 1: Relé WiFi Inteligente (Sonoff)
- [ ] Opción 2: Puerto Serial USB directo
- [ ] Opción 3: MQTT + simplificar
- [ ] Otro: Especificar
