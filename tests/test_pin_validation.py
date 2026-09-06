#!/usr/bin/env python3
"""
Script de prueba para validar el sistema de PIN dinámico
Verifica que el endpoint de validación de PIN funcione correctamente
"""
import os
import sys
import re
import hmac
import hashlib
import struct
import time
import json
import requests

# Rutas
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', '.env')
BASE_URL = 'http://localhost:8000'

WINDOW_SECONDS = 300  # 5 minutos

def leer_secreto():
    """Lee DEV_PIN_SECRET del .env"""
    if not os.path.exists(ENV_PATH):
        print(f'[ERROR] No existe: {ENV_PATH}')
        return None
    try:
        with open(ENV_PATH, 'r', encoding='utf-8') as f:
            for linea in f:
                m = re.match(r'^DEV_PIN_SECRET=(.+)', linea.strip())
                if m:
                    return m.group(1).strip()
    except Exception as e:
        print(f'[ERROR] Leyendo .env: {e}')
    return None

def compute_pin(secreto, window_offset=0):
    """Calcula el PIN dinámico TOTP"""
    t = (int(time.time()) // WINDOW_SECONDS) + window_offset
    key = secreto.encode('utf-8')
    msg = struct.pack('>Q', t)
    h = hmac.new(key, msg, hashlib.sha256).digest()
    off = h[-1] & 0x0F
    code = struct.unpack('>I', h[off:off + 4])[0] & 0x7FFFFFFF
    return str(code % 1_000_000).zfill(6)

def main():
    print('\n' + '='*70)
    print('  PRUEBA DE VALIDACIÓN DE PIN DINÁMICO')
    print('='*70 + '\n')
    
    # 1. Leer secreto
    print('[1/4] Leyendo secreto DEV_PIN_SECRET...')
    secreto = leer_secreto()
    if not secreto:
        print('[ERROR] No se pudo leer el secreto del .env')
        return 1
    print(f'[OK]  Secreto leído: {secreto[:20]}...')
    
    # 2. Calcular PIN actual
    print('\n[2/4] Calculando PIN actual...')
    pin_actual = compute_pin(secreto, window_offset=0)
    print(f'[OK]  PIN actual: {pin_actual}')
    
    # 3. Verificar que el servidor esté disponible
    print('\n[3/4] Verificando conexión al servidor...')
    try:
        resp = requests.get(f'{BASE_URL}/', timeout=2)
        print(f'[OK]  Servidor respondiendo (HTTP {resp.status_code})')
    except Exception as e:
        print(f'[ERROR] No se puede conectar a {BASE_URL}: {e}')
        return 1
    
    # 4. Probar endpoint (aunque sin token de verdad fallará)
    print('\n[4/4] Probando endpoint /api/admin/verificar-codigo-mantenimiento...')
    try:
        payload = {'codigo': pin_actual}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer invalid_token'  # Token inválido pero vamos a ver si llega al endpoint
        }
        resp = requests.post(
            f'{BASE_URL}/api/admin/verificar-codigo-mantenimiento',
            json=payload,
            headers=headers,
            timeout=5
        )
        print(f'[OK]  Endpoint respondiendo (HTTP {resp.status_code})')
        print(f'      Respuesta: {resp.json()}')
    except requests.exceptions.JSONDecodeError:
        print(f'[?]   Respuesta no es JSON')
        print(f'      Texto: {resp.text[:200]}')
    except Exception as e:
        print(f'[ERROR] Error probando endpoint: {e}')
    
    print('\n' + '='*70)
    print('  PIN actual para prueba manual: ' + pin_actual)
    print('='*70 + '\n')
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
