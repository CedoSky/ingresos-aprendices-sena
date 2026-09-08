#include <WiFi.h>
#include <PubSubClient.h>

// ═══════════════════════════════════════════════━
// ESP32 TRIAC - CONTROL VÍA MQTT
// Broker: HiveMQ (gratuito, cloud)
// ═══════════════════════════════════════════════

// WiFi
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";

// MQTT Broker HiveMQ
const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;

// MQTT Topics
const char* topic_triac_cmd = "sena/triac/comando";      // Recibe: iniciar, parar
const char* topic_triac_estado = "sena/triac/estado";    // Publica: {ciclo_activo, pulso}

// GPIO
const int PIN_TRIAC = 5;      // GPIO5 - Control TRIAC
const int PIN_LED = 33;       // GPIO33 - LED indicador

WiFiClient espClient;
PubSubClient client(espClient);

// Variables de estado
bool cicloActivo = false;
int pulsoActual = 0;
unsigned long tiempoInicio = 0;
unsigned long tiempoPulso = 3000;      // 3s ON
unsigned long tiempoEspera = 10000;    // 10s OFF
int totalPulsos = 5;

void setup() {
    Serial.begin(115200);
    delay(100);
    
    pinMode(PIN_TRIAC, OUTPUT);
    pinMode(PIN_LED, OUTPUT);
    digitalWrite(PIN_TRIAC, LOW);
    digitalWrite(PIN_LED, LOW);
    
    Serial.println("\n\n");
    Serial.println("╔════════════════════════════════════════╗");
    Serial.println("║  ESP32 TRIAC CONTROL - MQTT MODE      ║");
    Serial.println("╚════════════════════════════════════════╝");
    
    conectarWiFi();
    setupMQTT();
}

void loop() {
    // Reconectar MQTT si necesario
    if (!client.connected()) {
        reconectarMQTT();
    }
    client.loop();
    
    // Procesar ciclo TRIAC si está activo
    if (cicloActivo) {
        procesarCicloTriac();
    }
    
    delay(100);
}

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
        Serial.println("\n✗ Fallo al conectar WiFi");
    }
}

void setupMQTT() {
    client.setServer(mqtt_server, mqtt_port);
    client.setCallback(callback_mqtt);
    reconectarMQTT();
}

void reconectarMQTT() {
    int intentos = 0;
    while (!client.connected() && intentos < 5) {
        Serial.print("Conectando MQTT...");
        
        if (client.connect("ESP32-TRIAC")) {
            Serial.println("✓ Conectado a MQTT");
            
            // Suscribirse a comandos
            client.subscribe(topic_triac_cmd);
            Serial.print("Suscrito a: ");
            Serial.println(topic_triac_cmd);
            
            // Publicar estado inicial
            publicarEstado();
        } else {
            Serial.print("✗ Error: ");
            Serial.println(client.state());
            delay(2000);
            intentos++;
        }
    }
}

void callback_mqtt(char* topic, byte* payload, unsigned int length) {
    // Convertir payload a string
    char mensaje[length + 1];
    memcpy(mensaje, payload, length);
    mensaje[length] = '\0';
    
    Serial.print("📨 Mensaje recibido en topic: ");
    Serial.println(topic);
    Serial.print("   Comando: ");
    Serial.println(mensaje);
    
    // Procesar comandos
    if (strcmp(mensaje, "iniciar") == 0) {
        iniciarCicloTriac();
    } 
    else if (strcmp(mensaje, "parar") == 0) {
        pararCicloTriac();
    }
    else if (strcmp(mensaje, "estado") == 0) {
        publicarEstado();
    }
}

void iniciarCicloTriac() {
    if (!cicloActivo) {
        Serial.println("⚡ INICIANDO CICLO TRIAC...");
        cicloActivo = true;
        pulsoActual = 1;
        tiempoInicio = millis();
        digitalWrite(PIN_LED, HIGH);
        
        publicarEstado();
    }
}

void pararCicloTriac() {
    Serial.println("⏹️  PARANDO CICLO TRIAC...");
    cicloActivo = false;
    pulsoActual = 0;
    digitalWrite(PIN_TRIAC, LOW);
    digitalWrite(PIN_LED, LOW);
    
    publicarEstado();
}

void procesarCicloTriac() {
    unsigned long tiempoTranscurrido = millis() - tiempoInicio;
    unsigned long cicloCompleto = tiempoPulso + tiempoEspera;
    
    // Determinar si está en ON o OFF en el ciclo actual
    bool debeEstarOn = (tiempoTranscurrido % cicloCompleto) < tiempoPulso;
    
    // Actualizar salida TRIAC
    digitalWrite(PIN_TRIAC, debeEstarOn ? HIGH : LOW);
    digitalWrite(PIN_LED, debeEstarOn ? HIGH : LOW);
    
    // Actualizar número de pulso
    int pulsoDeterminado = (tiempoTranscurrido / cicloCompleto) + 1;
    
    if (pulsoDeterminado != pulsoActual) {
        pulsoActual = pulsoDeterminado;
        Serial.print("💫 Pulso: ");
        Serial.print(pulsoActual);
        Serial.print("/");
        Serial.println(totalPulsos);
        publicarEstado();
    }
    
    // Detener cuando complete los 5 pulsos
    if (pulsoDeterminado > totalPulsos) {
        pararCicloTriac();
        Serial.println("✅ CICLO COMPLETADO - 5 PULSOS");
    }
}

void publicarEstado() {
    // Crear JSON de estado
    char payload[256];
    snprintf(payload, sizeof(payload),
        "{\"ciclo_activo\":%s,\"pulso\":%d,\"pulsos_total\":%d,\"gpio_triac\":%d,\"gpio_led\":%d}",
        cicloActivo ? "true" : "false",
        pulsoActual,
        totalPulsos,
        PIN_TRIAC,
        PIN_LED
    );
    
    // Publicar
    client.publish(topic_triac_estado, payload);
    
    Serial.print("📤 Estado publicado: ");
    Serial.println(payload);
}
