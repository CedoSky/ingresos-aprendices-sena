#!/usr/bin/env python3
"""
Script para probar validación de PIN con login válido
"""
import os
import sys
import re
import hmac
import hashlib
import struct
import time
import requests

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', '.env')
BASE_URL = 'http://localhost:8000'
WINDOW_SECONDS = 300

def leer_secreto():
    if not os.path.exists(ENV_PATH):
        return None
    try:
        with open(ENV_PATH, 'r', encoding='utf-8') as f:
            for linea in f:
                m = re.match(r'^DEV_PIN_SECRET=(.+)', linea.strip())
                if m:
                    return m.group(1).strip()
    except:
        pass
    return None

def compute_pin(secreto, window_offset=0):
    t = (int(time.time()) // WINDOW_SECONDS) + window_offset
    key = secreto.encode('utf-8')
    msg = struct.pack('>Q', t)
    h = hmac.new(key, msg, hashlib.sha256).digest()
    off = h[-1] & 0x0F
    code = struct.unpack('>I', h[off:off + 4])[0] & 0x7FFFFFFF
    return str(code % 1_000_000).zfill(6)

def main():
    print('\n╔════════════════════════════════════════════════════════════════╗')
    print('║     PRUEBA COMPLETA: LOGIN + VALIDACIÓN DE PIN                ║')
    print('╚════════════════════════════════════════════════════════════════╝\n')
    
    # 1. Leer secreto
    print('[1/4] Leyendo DEV_PIN_SECRET...')
    secreto = leer_secreto()
    if not secreto:
        print('[✗]  No se pudo leer el secreto')
        return 1
    print(f'[✓]  Secreto: {secreto[:30]}...')
    
    # 2. Calcular PIN
    print(f'\n[2/4] Calculando PIN actual...')
    pin = compute_pin(secreto)
    print(f'[✓]  PIN: {pin}')
    
    # 3. Hacer login
    print(f'\n[3/4] Haciendo login...')
    try:
        resp = requests.post(
            f'{BASE_URL}/api/auth/login',
            json={'email': 'admin@sena.edu.co', 'password': 'admin123'},
            timeout=5
        )
        if resp.status_code != 200:
            print(f'[✗]  Login falló: HTTP {resp.status_code}')
            print(f'     {resp.text[:200]}')
            return 1
        data = resp.json()
        token = data.get('token')
        if not token:
            print(f'[✗]  No se recibió token en respuesta')
            return 1
        print(f'[✓]  Login exitoso, token obtenido')
    except Exception as e:
        print(f'[✗]  Error en login: {e}')
        return 1
    
    # 4. Llamar al endpoint con token y PIN
    print(f'\n[4/4] Validando PIN en el endpoint...')
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        resp = requests.post(
            f'{BASE_URL}/api/admin/verificar-codigo-mantenimiento',
            json={'codigo': pin},
            headers=headers,
            timeout=5
        )
        print(f'[✓]  Respuesta: HTTP {resp.status_code}')
        data = resp.json()
        print(f'     {json.dumps(data, indent=2)}')
        
        if data.get('success'):
            print(f'\n╔════════════════════════════════════════════════════════════════╗')
            print(f'║ ✓ PIN ES VÁLIDO - SISTEMA FUNCIONANDO CORRECTAMENTE           ║')
            print(f'╚════════════════════════════════════════════════════════════════╝\n')
            return 0
        else:
            print(f'\n[!]  El servidor validó pero devolvió success=false')
            return 1
    except Exception as e:
        print(f'[✗]  Error: {e}')
        return 1

if __name__ == '__main__':
    import json
    sys.exit(main())
