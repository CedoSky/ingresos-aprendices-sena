#!/usr/bin/env python3
"""Test rápido de conexión ESP32 y endpoints TRIAC"""
import requests
import json
import sys

ESP32_IP = "172.20.10.9"
FLASK_URL = "http://localhost:8000"
TOKEN = "test_token"  # Deberías usar un token real

print(f"\n═══════════════════════════════════════════════════════")
print(f"TEST CONEXIÓN ESP32 Y ENDPOINTS TRIAC")
print(f"═══════════════════════════════════════════════════════\n")

# Test 1: Ping a ESP32
print(f"[1] Intentando conectar a ESP32 en {ESP32_IP}...")
try:
    r = requests.get(f"http://{ESP32_IP}/", timeout=3)
    print(f"    ✅ ESP32 RESPONDE (HTTP {r.status_code})")
except requests.exceptions.ConnectionError:
    print(f"    ❌ NO SE PUEDE CONECTAR a ESP32")
    print(f"       - Verificar que ESP32 está encendido")
    print(f"       - Verificar IP: 172.20.10.9 está correcta")
    print(f"       - Verificar WiFi conectada")
except requests.exceptions.Timeout:
    print(f"    ❌ TIMEOUT - ESP32 no responde en 3 segundos")

# Test 2: Verificar que servidor Flask corre
print(f"\n[2] Verificando que servidor Flask está activo...")
try:
    r = requests.get(f"{FLASK_URL}/health", timeout=2)
    if r.status_code == 200:
        print(f"    ✅ SERVIDOR FLASK ACTIVO")
    else:
        print(f"    ❌ Servidor responde con código {r.status_code}")
except:
    print(f"    ❌ NO SE PUEDE CONECTAR a Flask")
    print(f"       - Ejecuta: python backend/app.py")

# Test 3: Verificar ruta /api/vigilancia/triac/iniciar
print(f"\n[3] Verificando endpoint /api/vigilancia/triac/iniciar...")
try:
    r = requests.post(
        f"{FLASK_URL}/api/vigilancia/triac/iniciar",
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=2
    )
    print(f"    Status: {r.status_code}")
    print(f"    Respuesta: {r.text[:100]}")
    if r.status_code == 401:
        print(f"    → Esperado (token inválido)")
    elif r.status_code == 404:
        print(f"    ❌ ENDPOINT NO ENCONTRADO - El servidor no reconoce la ruta")
    elif r.status_code == 200:
        print(f"    ✅ ENDPOINT FUNCIONA")
except Exception as e:
    print(f"    ❌ Error: {e}")

print(f"\n═══════════════════════════════════════════════════════\n")
