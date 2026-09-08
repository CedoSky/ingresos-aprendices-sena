# ═════════════════════════════════════════════════════════════════════════════
# SINCRONIZACIÓN WiFi — ESP32 + Flask
# ═════════════════════════════════════════════════════════════════════════════

## 🎯 Objetivo

Asegurar que **ESP32 y Flask usen la MISMA red WiFi** sin discrepancias.

---

## 📝 Cómo sincronizar

### **Paso 1: Editar `.env.esp32` (CENTRALIZADOR)**

Archivo: `proyeto_root/.env.esp32`

```bash
# RED WiFi compartida (MISMA para ESP32 y Flask)
WIFI_SSID=iPhone de AMAT
WIFI_PASSWORD=Enrique1092

# IP del ESP32 (después de conectarlo)
ESP32_IP=192.168.1.100

# ...resto de config
```

**⚠️ IMPORTANTE:** Cambiar solo 1 lugar (aquí).

---

### **Paso 2: Editar Arduino (SINCRONIZAR con .env.esp32)**

Archivo: `backend/esp32_cerradura/esp32_cerradura_simplificado.ino`

```cpp
// ════════════════════ CONFIGURACIÓN ════════════════════
// ⚠️  SINCRONIZAR CON .env.esp32 (backend/../.env.esp32)
const char* WIFI_SSID     = "iPhone de AMAT";      // ← IGUAL que .env.esp32
const char* WIFI_PASSWORD = "Enrique1092";         // ← IGUAL que .env.esp32
```

**Regla:** Los valores aquí DEBEN ser idénticos a los del `.env.esp32`

---

### **Paso 3: Verificar que Flask carga correctamente**

`backend/app.py` ya incluye:

```python
# Cargar variables de entorno (en orden de prioridad)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))       # backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.esp32'))  # .env.esp32
```

Esto significa que `.env.esp32` **sobrescribe** valores de `backend/.env` si existen.

**Log de startup (busca esto al iniciar):**
```
[ESP32] Configurado para red WiFi: "iPhone de AMAT" → IP local: 192.168.1.100
```

---

## 🔄 Flujo de sincronización

```
┌─────────────────────────────────────────┐
│       .env.esp32  (FUENTE ÚNICA)        │
│  WIFI_SSID="iPhone de AMAT"             │
│  WIFI_PASSWORD="Enrique1092"            │
└──────────┬──────────────────────────────┘
           │
      ┌────┴────┐
      │          │
      ↓          ↓
┌──────────┐  ┌──────────────────┐
│ Arduino  │  │ Flask/routes.py  │
│ Copia    │  │ Lee (automático) │
│ manual   │  │ desde .env.esp32 │
└──────────┘  └──────────────────┘
```

---

## ✅ Verificación rapida

### **1. Chequear que Arduino lee correctamente:**

Monitor serial → Busca:
```
[WIFI] Conectando a iPhone de AMAT...
[WIFI] ✅ Conectado! IP: 192.168.1.XXX
```

### **2. Chequear que Flask lee correctamente:**

Logs al iniciar → Busca:
```
[ESP32] Configurado para red WiFi: "iPhone de AMAT" → IP local: 192.168.1.100
```

### **3. Chequear que pueden comunicarse:**

Terminal/Browser:
```bash
curl http://192.168.1.100/estado
# Debería retornar JSON

# Desde Python:
python -c "import requests; print(requests.get('http://192.168.1.100/estado').json())"
```

---

## 🚨 Solución de problemas

### **Problema: "El ESP32 no se conecta a WiFi"**

**Solución:**
- Verifica que `WIFI_SSID` y `WIFI_PASSWORD` en Arduino sean exactamente iguales a `.env.esp32`
- No hay espacios extra ni mayúsculas diferentes
- Si cambias la WiFi, actualiza AMBOS archivos

### **Problema: "Flask no encuentra al ESP32"**

**Solución:**
- Verifica `ESP32_IP` en `.env.esp32`
- Asegúrate de que el ESP32 tenga esa IP en monitor serial
- Ambos deben estar en la MISMA red local
- Ping: `ping 192.168.1.100` (o tu IP)

### **Problema: "Las credenciales WiFi son incorrectas"**

**Solución:**
1. Obtén SSID exacto y password desde:
   - Panel de router/móvil
   - Monitor serial del ESP32 (si intenta conectak)
2. Actualiza `.env.esp32`
3. Copia exactamente al Arduino
4. Recompila y sube

---

## 📋 Checklist de sincronización

- [ ] `.env.esp32` contiene `WIFI_SSID` y `WIFI_PASSWORD` correctos
- [ ] Arduino tiene los MISMOS valores (`WIFI_SSID` y `WIFI_PASSWORD`)
- [ ] Monitor serial muestra `[WIFI] ✅ Conectado!` con la IP
- [ ] `.env.esp32` tiene `ESP32_IP` = IP del serial
- [ ] `backend/app.py` carga `.env.esp32`
- [ ] Logs de Flask muestran `[ESP32] Configurado para red WiFi: ...`
- [ ] `curl http://ESP32_IP/estado` retorna JSON

---

## 📝 Archivo de referencia rápida

**Cuando cambies WiFi:**

1. Obtén nuevo SSID y password
2. Edita `.env.esp32`:
   ```
   WIFI_SSID=Nueva-Red
   WIFI_PASSWORD=nueva-contraseña
   ```
3. Edita Arduino:
   ```cpp
   const char* WIFI_SSID = "Nueva-Red";
   const char* WIFI_PASSWORD = "nueva-contraseña";
   ```
4. Recompila y sube Arduino
5. Obtén nueva IP del monitor serial
6. Actualiza `.env.esp32`: `ESP32_IP=192.168.1.XXX`
7. Reinicia Flask

¡Listo! Sincronizado. 🎉
