#include <WiFi.h>
#include <WebServer.h>

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURACIÓN
// ═══════════════════════════════════════════════════════════════════════════════

#define PIN_TRIAC 23
#define PIN_LED 33

const char* ssid = "iPhone de AMAT";
const char* password = "Enrique1092";

WebServer server(80);

// ═══════════════════════════════════════════════════════════════════════════════
// VARIABLES DE ESTADO
// ═══════════════════════════════════════════════════════════════════════════════

bool cicloActivo = false;
int pulsosRestantes = 0;
bool enPulso = false;
unsigned long tiempoInicio = 0;

// ═══════════════════════════════════════════════════════════════════════════════
// SETUP
// ═══════════════════════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  pinMode(PIN_TRIAC, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_TRIAC, LOW);
  digitalWrite(PIN_LED, LOW);
  
  Serial.println("\n=== CONTROL TRIAC POR SERIAL/HTTP ===");
  Serial.println("Serial: 1=INICIAR, 2=PARAR");
  Serial.println("HTTP:   /triac/iniciar, /triac/parar, /triac/estado");
  Serial.println("======================================\n");
  
  // Conectar WiFi
  conectarWiFi();
  
  // Configurar endpoints HTTP
  server.on("/triac/iniciar", handleIniciar);
  server.on("/triac/parar", handleParar);
  server.on("/triac/estado", handleEstado);
  server.begin();
  
  Serial.println("✓ Servidor HTTP iniciado en puerto 80");
}

// ═══════════════════════════════════════════════════════════════════════════════
// LOOP
// ═══════════════════════════════════════════════════════════════════════════════

void loop() {
  server.handleClient();
  
  // Procesar comandos serial
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    
    if (comando == "1" && !cicloActivo) {
      iniciarCiclo();
    }
    else if (comando == "2") {
      pararCiclo();
    }
    else if (comando != "") {
      Serial.println("❌ Comando inválido. Usa: 1 (iniciar) o 2 (parar)");
    }
  }
  
  // Máquina de estados TRIAC
  if (cicloActivo) {
    maquinaEstados();
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONEXIÓN WIFI
// ═══════════════════════════════════════════════════════════════════════════════

void conectarWiFi() {
  Serial.print("Conectando a WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 20) {
    delay(500);
    Serial.print(".");
    intentos++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi conectado");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n✗ Error conectando a WiFi");
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONTROL TRIAC
// ═══════════════════════════════════════════════════════════════════════════════

void iniciarCiclo() {
  if (cicloActivo) return;
  
  cicloActivo = true;
  pulsosRestantes = 5;
  enPulso = true;
  tiempoInicio = millis();
  digitalWrite(PIN_TRIAC, HIGH);
  digitalWrite(PIN_LED, HIGH);
  Serial.println("🚀 CICLO INICIADO - Pulso 1/5 ON (3s)");
}

void pararCiclo() {
  cicloActivo = false;
  pulsosRestantes = 0;
  enPulso = false;
  digitalWrite(PIN_TRIAC, LOW);
  digitalWrite(PIN_LED, LOW);
  Serial.println("⏹️ CICLO PARADO MANUALMENTE");
}

void maquinaEstados() {
  unsigned long ahora = millis();
  
  if (enPulso) {
    // ON: 3 segundos
    if (ahora - tiempoInicio >= 3000UL) {
      digitalWrite(PIN_TRIAC, LOW);
      digitalWrite(PIN_LED, LOW);
      enPulso = false;
      tiempoInicio = ahora;
      Serial.println("⏳ Pulso OFF - Espera 10s (quedan " + String(pulsosRestantes) + ")");
    }
  } 
  else {
    // OFF: 10 segundos
    if (ahora - tiempoInicio >= 10000UL) {
      if (pulsosRestantes > 0) {
        digitalWrite(PIN_TRIAC, HIGH);
        digitalWrite(PIN_LED, HIGH);
        enPulso = true;
        pulsosRestantes--;
        tiempoInicio = ahora;
        Serial.println("🔥 Pulso " + String(6-pulsosRestantes) + "/5 ON (3s)");
      } else {
        cicloActivo = false;
        digitalWrite(PIN_TRIAC, LOW);
        digitalWrite(PIN_LED, LOW);
        Serial.println("✅ CICLO COMPLETADO - 5 pulsos terminados");
      }
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// MANEJADORES HTTP
// ═══════════════════════════════════════════════════════════════════════════════

void handleIniciar() {
  iniciarCiclo();
  server.send(200, "application/json", "{\"ok\": true, \"ciclo_activo\": " + String(cicloActivo ? "true" : "false") + "}");
}

void handleParar() {
  pararCiclo();
  server.send(200, "application/json", "{\"ok\": true, \"ciclo_activo\": " + String(cicloActivo ? "true" : "false") + "}");
}

void handleEstado() {
  String json = "{\"ciclo_activo\": " + String(cicloActivo ? "true" : "false") + 
                ", \"pulsos_restantes\": " + String(pulsosRestantes) + 
                ", \"en_pulso\": " + String(enPulso ? "true" : "false") + "}";
  server.send(200, "application/json", json);
}
