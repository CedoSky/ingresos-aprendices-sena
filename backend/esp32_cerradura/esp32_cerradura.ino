/*
 * ══════════════════════════════════════════════════════════════════════════════
 *  SENA — ESP32 CERRADURA ELÉCTRICA DE PRUEBA
 *  Firmware para abrir/cerrar una cerradura eléctrica desde el panel de
 *  vigilancia del sistema de Control de Accesos SENA.
 *
 *  CONEXIONES:
 *    GPIO5  → IN del módulo relé cerradura ambiente 203 (activo en LOW)
 *    GPIO33 → LED indicador de estado (salida)
 *    GPIO0  → Botón BOOT (prueba manual)
 *
 *  LIBRERÍAS NECESARIAS (instalar desde Arduino IDE → Library Manager):
 *    - WiFi          (incluida con ESP32 board)
 *    - WebServer     (incluida con ESP32 board)
 *    - HTTPClient    (incluida con ESP32 board)
 *    - ArduinoJson   (instalar: "ArduinoJson" by Benoit Blanchon)
 *
 *  CONFIGURACIÓN: ajusta las constantes en el bloque ─── CONFIGURAR AQUÍ ───
 * ══════════════════════════════════════════════════════════════════════════════
 */

#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ─── CONFIGURAR AQUÍ ──────────────────────────────────────────────────────────
const char* WIFI_SSID     = "iPhone de AMAT";          // ← Nombre de tu red WiFi
const char* WIFI_PASSWORD = "Enrique1092";         // ← Contraseña WiFi

// IP del servidor backend Flask (la PC donde corre el sistema)
const char* SERVIDOR_HOST = "172.20.10.4";        // IP de la PC en la red iPhone de AMAT
const int   SERVIDOR_PORT = 8000;                  // Puerto Flask

// Identificador único de este ESP32
const char* DEVICE_ID    = "esp32-cerradura-203";  // Identificador para ambiente 203
const char* DEVICE_KEY   = "prueba-esp32-2026";   // ← Misma clave que en vigilancia.html

// Hardware
const int RELAY_PIN = 5;    // GPIO5 — relé cerradura ambiente 203 (LOW = activado = ABIERTO)
const int LED_PIN   = 33;   // GPIO33 — LED indicador de estado
const int BTN_PIN   = 0;    // Botón BOOT para prueba manual

// NOTA: La cerradura se abre/cierra por comandos del servidor según lógica del vigilante.html
// No hay auto-cierre — el vigilante controla el ciclo completo de abrir/cerrar

// ─── ESTADO ───────────────────────────────────────────────────────────────────
bool             cerraduraAbierta = false;
unsigned long    tiempoApertura   = 0;
// CAMBIO: Removido tiempoAutoClose — la cerradura se cierra SOLO por comando del servidor/vigilante
unsigned long    ultimoPoll       = 0;
const unsigned long POLL_INTERVAL = 800; // ms entre polls al servidor

WebServer server(80);

// ─── HELPERS ──────────────────────────────────────────────────────────────────
void setRelay(bool abrir, int pin = RELAY_PIN) {
    // Relé activo-LOW: LOW = bobina energizada = cerradura ABIERTA
    // Si el pin es diferente al predeterminado, inicializarlo como salida
    if (pin != RELAY_PIN) {
        pinMode(pin, OUTPUT);
    }
    digitalWrite(pin, abrir ? LOW : HIGH);
    cerraduraAbierta = abrir;
    Serial.printf("[RELAY] GPIO%d → Cerradura %s\n", pin, abrir ? "ABIERTA" : "CERRADA");
}

void ledBlink(int veces, int ms) {
    for (int i = 0; i < veces; i++) {
        digitalWrite(LED_PIN, HIGH); delay(ms);
        digitalWrite(LED_PIN, LOW);  delay(ms);
    }
}

// Agrega cabeceras CORS para que el navegador pueda llamar directamente
void addCORS() {
    server.sendHeader("Access-Control-Allow-Origin",  "*");
    server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}

// ─── RUTAS HTTP ───────────────────────────────────────────────────────────────

// GET /ping — comprobación de conectividad
void handlePing() {
    addCORS();
    StaticJsonDocument<128> doc;
    doc["ok"]        = true;
    doc["device_id"] = DEVICE_ID;
    doc["cerradura"] = cerraduraAbierta ? "abierta" : "cerrada";
    doc["uptime_s"]  = millis() / 1000;
    String body;
    serializeJson(doc, body);
    server.send(200, "application/json", body);
}

// GET /estado — estado detallado
void handleEstado() {
    addCORS();
    StaticJsonDocument<256> doc;
    doc["device_id"]          = DEVICE_ID;
    doc["cerradura"]          = cerraduraAbierta ? "abierta" : "cerrada";
    doc["abierta"]            = cerraduraAbierta;
    doc["ms_desde_apertura"]  = cerraduraAbierta ? (unsigned long)(millis() - tiempoApertura) : 0;
    doc["uptime_s"]           = millis() / 1000;
    doc["wifi_rssi"]          = WiFi.RSSI();
    String body;
    serializeJson(doc, body);
    server.send(200, "application/json", body);
}

// GET /abrir?seg=15 — abre cerradura (llamado directo desde vigilancia.html)
void handleAbrir() {
    addCORS();
    if (server.method() == HTTP_OPTIONS) { server.send(200); return; }

    setRelay(true);
    tiempoApertura  = millis();
    ledBlink(2, 80);

    StaticJsonDocument<128> doc;
    doc["ok"]        = true;
    doc["device_id"] = DEVICE_ID;
    doc["accion"]    = "abierta";
    String body;
    serializeJson(doc, body);
    server.send(200, "application/json", body);
    Serial.println("[HTTP] /abrir — cerradura abierta por el servidor/vigilante");
}

// GET /cerrar — cierra cerradura
void handleCerrar() {
    addCORS();
    if (server.method() == HTTP_OPTIONS) { server.send(200); return; }

    setRelay(false);
    ledBlink(1, 200);

    StaticJsonDocument<128> doc;
    doc["ok"]        = true;
    doc["device_id"] = DEVICE_ID;
    doc["accion"]    = "cerrada";
    String body;
    serializeJson(doc, body);
    server.send(200, "application/json", body);
    Serial.println("[HTTP] /cerrar — cerradura cerrada por el servidor/vigilante");
}

// GET / — página de diagnóstico mínima
void handleRoot() {
    addCORS();
    String html = "<html><head><title>ESP32 Cerradura</title>"
        "<meta http-equiv='refresh' content='3'>"
        "<style>body{font-family:monospace;padding:20px;background:#0d1117;color:#c9d1d9}"
        "h2{color:#58a6ff}.ok{color:#3fb950}.err{color:#f85149}"
        "td{padding:4px 12px}</style></head><body>"
        "<h2>&#x1F513; ESP32 Cerradura — SENA</h2>"
        "<table>"
        "<tr><td>Device ID</td><td>" + String(DEVICE_ID) + "</td></tr>"
        "<tr><td>WiFi RSSI</td><td>" + String(WiFi.RSSI()) + " dBm</td></tr>"
        "<tr><td>IP local</td><td>" + WiFi.localIP().toString() + "</td></tr>"
        "<tr><td>Estado</td><td class='" + String(cerraduraAbierta ? "ok'>🔓 ABIERTA" : "err'>🔒 CERRADA") + "</td></tr>"
        "<tr><td>Uptime</td><td>" + String(millis()/1000) + " s</td></tr>"
        "</table>"
        "<br><a href='/abrir' style='color:#3fb950'>[ ABRIR ]</a> &nbsp;"
        "<a href='/cerrar' style='color:#f85149'>[ CERRAR ]</a> &nbsp;"
        "<a href='/estado' style='color:#58a6ff'>[ JSON ESTADO ]</a>"
        "</body></html>";
    server.send(200, "text/html", html);
}

// ─── POLLING AL SERVIDOR BACKEND ──────────────────────────────────────────────
void pollServidor() {
    if (WiFi.status() != WL_CONNECTED) return;

    String url = "http://" + String(SERVIDOR_HOST) + ":" + String(SERVIDOR_PORT)
               + "/api/esp32/comando/" + String(DEVICE_ID)
               + "?key=" + String(DEVICE_KEY);

    HTTPClient http;
    http.begin(url);
    http.setTimeout(2000);
    int code = http.GET();

    if (code == 200) {
        String payload = http.getString();
        StaticJsonDocument<256> doc;
        if (deserializeJson(doc, payload) == DeserializationError::Ok) {
            const char* cmd = doc["cmd"] | "ninguno";
            int seg = doc["segundos"] | 10;
            int pin = doc["pin"] | RELAY_PIN;  // pin enviado por servidor (GPIO5 para amb.203)

            if (strcmp(cmd, "abrir") == 0) {
                Serial.printf("[POLL] Comando del servidor: ABRIR en GPIO%d (ambiente 203)\n", pin);
                setRelay(true, pin);
                tiempoApertura  = millis();
                ledBlink(3, 60);
                enviarAck("abrir");
            } else if (strcmp(cmd, "cerrar") == 0) {
                Serial.printf("[POLL] Comando del servidor: CERRAR en GPIO%d (ambiente 203)\n", pin);
                setRelay(false, pin);
                ledBlink(1, 300);
                enviarAck("cerrar");
            }
        }
    } else if (code < 0) {
        Serial.printf("[POLL] Sin respuesta del servidor: %s\n", http.errorToString(code).c_str());
    }
    http.end();
}

// ─── ENVIAR ACK AL SERVIDOR ───────────────────────────────────────────────────
void enviarAck(const char* cmd) {
    if (WiFi.status() != WL_CONNECTED) return;

    String url = "http://" + String(SERVIDOR_HOST) + ":" + String(SERVIDOR_PORT)
               + "/api/esp32/ack/" + String(DEVICE_ID)
               + "?key=" + String(DEVICE_KEY);

    HTTPClient http;
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(2000);

    StaticJsonDocument<128> doc;
    doc["cmd"]    = cmd;
    doc["estado"] = cerraduraAbierta ? "abierta" : "cerrada";
    String body;
    serializeJson(doc, body);

    http.POST(body);
    http.end();
}

// ─── REGISTRAR EN SERVIDOR ────────────────────────────────────────────────────
void registrarEnServidor() {
    if (WiFi.status() != WL_CONNECTED) return;

    String url = "http://" + String(SERVIDOR_HOST) + ":" + String(SERVIDOR_PORT)
               + "/api/esp32/registrar";

    HTTPClient http;
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(3000);

    StaticJsonDocument<256> doc;
    doc["device_id"] = DEVICE_ID;
    doc["key"]       = DEVICE_KEY;
    doc["ip"]        = WiFi.localIP().toString();
    doc["ambiente"]  = "203";     // Este ESP32 controla el ambiente 203
    doc["pin"]       = RELAY_PIN; // GPIO5
    String body;
    serializeJson(doc, body);

    int code = http.POST(body);
    if (code == 200) {
        Serial.println("[REG] Registrado exitosamente en el servidor.");
    } else {
        Serial.printf("[REG] Error al registrar: HTTP %d\n", code);
    }
    http.end();
}

// ─── SETUP ────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    Serial.println("\n\n[SENA] ESP32 Cerradura Eléctrica — Iniciando...");

    // Pines
    pinMode(RELAY_PIN, OUTPUT);
    pinMode(LED_PIN,   OUTPUT);
    pinMode(BTN_PIN,   INPUT_PULLUP);

    // Asegurar cerradura CERRADA al arrancar
    setRelay(false);
    digitalWrite(LED_PIN, LOW);

    // Conectar WiFi
    Serial.printf("[WIFI] Conectando a %s", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int intentos = 0;
    while (WiFi.status() != WL_CONNECTED && intentos < 30) {
        delay(500);
        Serial.print(".");
        intentos++;
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("[WIFI] ✅ Conectado! IP: %s\n", WiFi.localIP().toString().c_str());
        ledBlink(5, 80);
    } else {
        Serial.println("[WIFI] ❌ No se pudo conectar. Reiniciando en 5s...");
        delay(5000);
        ESP.restart();
    }

    // Rutas HTTP
    server.on("/",       HTTP_GET,     handleRoot);
    server.on("/ping",   HTTP_GET,     handlePing);
    server.on("/estado", HTTP_GET,     handleEstado);
    server.on("/abrir",  HTTP_GET,     handleAbrir);
    server.on("/cerrar", HTTP_GET,     handleCerrar);

    // Responder OPTIONS para CORS preflight
    server.onNotFound([](){
        if (server.method() == HTTP_OPTIONS) {
            server.sendHeader("Access-Control-Allow-Origin",  "*");
            server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
            server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
            server.send(200);
        } else {
            server.send(404, "text/plain", "No encontrado");
        }
    });

    server.begin();
    Serial.println("[HTTP] Servidor HTTP iniciado en puerto 80");
    Serial.printf("[HTTP] Abre en navegador: http://%s/\n", WiFi.localIP().toString().c_str());

    // Registrar en servidor backend
    delay(500);
    registrarEnServidor();

    Serial.println("[OK] Listo. Esperando comandos...");
}

// ─── LOOP ─────────────────────────────────────────────────────────────────────
void loop() {
    server.handleClient();

    // LED parpadeante cuando cerradura está abierta
    if (cerraduraAbierta) {
        static unsigned long lastBlink = 0;
        if (millis() - lastBlink > 400) {
            lastBlink = millis();
            digitalWrite(LED_PIN, !digitalRead(LED_PIN));
        }
    } else {
        digitalWrite(LED_PIN, LOW);
    }

    // Polling al servidor (cada POLL_INTERVAL ms)
    // El servidor controla cuándo abrir/cerrar según la lógica del vigilante
    if (millis() - ultimoPoll >= POLL_INTERVAL) {
        ultimoPoll = millis();
        pollServidor();
    }

    // Botón BOOT — prueba manual (press = alternar)
    static bool btnAnterior = HIGH;
    bool btnActual = digitalRead(BTN_PIN);
    if (btnAnterior == HIGH && btnActual == LOW) {
        Serial.println("[BTN] Botón presionado — alternando cerradura");
        if (cerraduraAbierta) {
            setRelay(false);
        } else {
            setRelay(true);
            tiempoApertura = millis();
        }
        delay(50);  // debounce
    }
    btnAnterior = btnActual;

    delay(5);
}
