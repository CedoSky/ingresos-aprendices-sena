"""
Panel de Sistemas — Codigo de acceso dinamico (TOTP-style).
Se ejecuta desde MANTENIMIENTO.bat -> opcion "Ver PIN del panel de sistemas".

El codigo cambia automaticamente cada 5 minutos.
El secreto (DEV_PIN_SECRET) se genera una sola vez y se guarda en backend/.env.
Para invalidar todas las sesiones activas, usa la opcion de Rotar secreto.
"""
import os
import sys
import re
import hmac
import hashlib
import struct
import time
import secrets

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

WINDOW_SECONDS = 300  # PIN cambia cada 5 minutos


def leer_env():
    if not os.path.exists(ENV_PATH):
        return []
    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        return f.readlines()


def escribir_env(lineas):
    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lineas)


def leer_secreto():
    """Devuelve el valor de DEV_PIN_SECRET del .env, o '' si no existe."""
    for linea in leer_env():
        m = re.match(r'^DEV_PIN_SECRET=(.+)', linea.strip())
        if m:
            return m.group(1).strip()
    return ''


def guardar_secreto(secreto):
    """Escribe o reemplaza DEV_PIN_SECRET en el .env."""
    lineas = leer_env()
    encontrado = False
    nuevas = []
    for linea in lineas:
        if re.match(r'^DEV_PIN_SECRET\s*=', linea):
            nuevas.append(f'DEV_PIN_SECRET={secreto}\n')
            encontrado = True
        else:
            nuevas.append(linea)
    if not encontrado:
        if nuevas and not nuevas[-1].endswith('\n'):
            nuevas.append('\n')
        nuevas.append(f'DEV_PIN_SECRET={secreto}\n')
    escribir_env(nuevas)


def generar_secreto():
    """Genera un nuevo secreto seguro y lo guarda en .env."""
    nuevo = secrets.token_hex(32)  # 256 bits de entropia
    guardar_secreto(nuevo)
    return nuevo


def compute_pin(secreto, window_offset=0):
    """Calcula el PIN dinamico para la ventana de tiempo actual + offset."""
    t = (int(time.time()) // WINDOW_SECONDS) + window_offset
    key = secreto.encode('utf-8')
    msg = struct.pack('>Q', t)
    h = hmac.new(key, msg, hashlib.sha256).digest()
    off = h[-1] & 0x0F
    code = struct.unpack('>I', h[off:off + 4])[0] & 0x7FFFFFFF
    return str(code % 1_000_000).zfill(6)


def tiempo_restante():
    """Segundos que faltan para que cambie el PIN actual."""
    ahora = int(time.time())
    return WINDOW_SECONDS - (ahora % WINDOW_SECONDS)


def main():
    print()
    print('  ================================================================')
    print('   PANEL DE SISTEMAS  —  Codigo de acceso dinamico')
    print('  ================================================================')
    print()

    if not os.path.exists(ENV_PATH):
        print('  [ERROR] No se encontro el archivo backend/.env')
        print('  Copia backend/.env.example como backend/.env primero.')
        print()
        sys.exit(1)

    secreto = leer_secreto()
    if not secreto:
        print('  Primera ejecucion: generando secreto automaticamente...')
        secreto = generar_secreto()
        print('  [OK] Secreto generado y guardado en backend/.env')
        print()

    pin = compute_pin(secreto)
    seg = tiempo_restante()
    mins, segs = divmod(seg, 60)

    # ── Detectar si el servidor Flask está corriendo ────────────────────────
    servidor_activo = False
    try:
        import requests
        response = requests.get('http://localhost:8000/api/auth/me', headers={'Authorization': 'Bearer test'}, timeout=1)
        # Si no da error 404 o 401, el servidor está activo
        servidor_activo = response.status_code in (200, 401, 403)
    except:
        servidor_activo = False

    if servidor_activo:
        print('  ✓ Servidor Flask detectado en http://localhost:8000')
        print('  ✓ Sesión de administración ACTIVA detectada')
        print()
    else:
        print('  ⚠️  ADVERTENCIA: Servidor Flask NO detectado')
        print('  Si necesitas usar Herramientas, asegúrate de ejecutar primero:')
        print('      cd backend && python app.py')
        print()

    print(f'  Codigo actual :  {pin}  (6 digitos, sin espacios)')
    print(f'  Valido por    :  {mins}m {segs:02d}s mas')
    print()
    print('  Este codigo cambia automaticamente cada 5 minutos.')
    print('  ═══════════════════════════════════════════════════════════════')
    print('   ✓ Mejor opcion: Abre http://localhost:8000/administracion')
    print('   ✓ Ve a Herramientas > Generar PIN Ahora')
    print('   ✓ El PIN aparecerá en grande en la pantalla')
    print('  ═══════════════════════════════════════════════════════════════')
    print()
    print('  Opciones:')
    print('   [1] Mostrar PIN nuevamente')
    print('   [R] Rotar secreto  (invalida todas las sesiones abiertas)')
    print('   [0] Volver al menu')
    print()

    opcion = input('  Selecciona: ').strip().upper()
    if opcion == '1':
        print()
        print(f'  PIN ACTUAL: {pin}')
        print()
    elif opcion == 'R':
        confirmar = input('  Seguro? Se invalidaran todas las sesiones. (S/N): ').strip().upper()
        if confirmar == 'S':
            secreto = generar_secreto()
            nuevo_pin = compute_pin(secreto)
            print()
            print(f'  [OK] Secreto rotado. Nuevo codigo actual:  {nuevo_pin[:3]} {nuevo_pin[3:]}')
            print('  Todos los usuarios del panel deberan ingresar el nuevo codigo.')
        else:
            print()
            print('  Sin cambios.')
    print()


if __name__ == '__main__':
    main()
