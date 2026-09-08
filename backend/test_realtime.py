#!/usr/bin/env python
"""
Script para probar conexiones WebSocket en tiempo real
"""
import time
import socketio
import threading

# Crear cliente de Socket.IO
sio = socketio.Client()

# Variables para rastrear eventos
eventos_recibidos = []

@sio.event
def connect():
    print("✓ Conectado al servidor WebSocket")
    sio.emit('request_personas')
    print("  Enviando solicitud de personas...")

@sio.event
def disconnect():
    print("✗ Desconectado del servidor")

@sio.on('personas_data')
def on_personas_data(data):
    print(f"✓ Recibidos datos de personas: {len(data.get('personas', []))} personas")
    eventos_recibidos.append(('personas_data', len(data.get('personas', []))))

@sio.on('personas_updated')
def on_personas_updated(data):
    print(f"✓ Actualización en tiempo real: {len(data.get('personas', []))} personas")
    eventos_recibidos.append(('personas_updated', len(data.get('personas', []))))

@sio.on('stats_data')
def on_stats_data(data):
    print(f"✓ Recibidas estadísticas: {data}")

try:
    print("Conectando a websocket://localhost:8000...")
    sio.connect('http://localhost:8000', 
                transports=['websocket', 'polling'],
                wait_timeout=10)
    
    print("\nEsperando eventos por 5 segundos...")
    time.sleep(5)
    
    print("\nEventos recibidos:")
    for evento, dato in eventos_recibidos:
        print(f"  - {evento}: {dato}")
    
    if not eventos_recibidos:
        print("  (ninguno - posible problema de conexión)")
    
    sio.disconnect()
    print("\nConexión cerrada.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
