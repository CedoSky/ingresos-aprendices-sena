"""
MQTT Handler para comunicación con ESP32 TRIAC
Conecta al broker HiveMQ y maneja publicación/suscripción
"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime
import threading
import time

# Configuración MQTT
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_CMD = "sena/triac/comando"
MQTT_TOPIC_ESTADO = "sena/triac/estado"

# Cliente MQTT global
mqtt_client = None
ultimo_estado = {}

def init_mqtt():
    """Inicializa la conexión MQTT"""
    global mqtt_client
    
    mqtt_client = mqtt.Client(client_id="flask-sena-server")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    
    try:
        print(f"[MQTT] Conectando a broker: {MQTT_BROKER}:{MQTT_PORT}")
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()  # Iniciar bucle en background
        print("[MQTT] Cliente iniciado en background")
        return True
    except Exception as e:
        print(f"[MQTT] Error conectando: {e}")
        return False

def on_connect(client, userdata, flags, rc):
    """Callback cuando se conecta al broker"""
    if rc == 0:
        print(f"[MQTT] ✓ Conectado al broker")
        # Suscribirse al topic de estado
        client.subscribe(MQTT_TOPIC_ESTADO)
        print(f"[MQTT] Suscrito a: {MQTT_TOPIC_ESTADO}")
    else:
        print(f"[MQTT] ✗ Error de conexión: {rc}")

def on_disconnect(client, userdata, rc):
    """Callback cuando se desconecta del broker"""
    if rc != 0:
        print(f"[MQTT] Desconexión inesperada: {rc}")
    else:
        print(f"[MQTT] Desconectado correctamente")

def on_message(client, userdata, msg):
    """Callback cuando llega un mensaje MQTT"""
    global ultimo_estado
    
    try:
        payload = json.loads(msg.payload.decode())
        ultimo_estado = payload
        print(f"[MQTT] Estado recibido: {payload}")
    except json.JSONDecodeError:
        print(f"[MQTT] Error parsing JSON: {msg.payload}")

def enviar_comando_mqtt(comando):
    """
    Envía comando al ESP32 via MQTT
    comando: "iniciar", "parar", "estado"
    """
    global mqtt_client
    
    if mqtt_client is None or not mqtt_client.is_connected():
        return {'ok': False, 'error': 'MQTT no conectado'}
    
    try:
        mqtt_client.publish(MQTT_TOPIC_CMD, comando)
        print(f"[MQTT] Comando enviado: {comando}")
        return {'ok': True, 'comando': comando, 'timestamp': datetime.utcnow().isoformat()}
    except Exception as e:
        print(f"[MQTT] Error enviando comando: {e}")
        return {'ok': False, 'error': str(e)}

def obtener_estado_actual():
    """Obtiene el último estado conocido del ESP32"""
    global ultimo_estado
    return ultimo_estado if ultimo_estado else {'ciclo_activo': False, 'pulso': 0}
