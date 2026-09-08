"""
Gestor de sincronización local ↔ destino de respaldo (USB o AWS S3).

Flujo:
  1. Cuando se crea un respaldo y el destino (USB/S3) no está disponible,
     los datos se guardan en pending_sync/ como archivos JSON.
  2. Un hilo en background verifica la conexión cada CHECK_INTERVAL segundos.
  3. Cuando el destino vuelve a estar disponible, sube todo lo pendiente
     automáticamente y registra cada respaldo en la tabla `respaldos`.
  4. Los archivos ya sincronizados se eliminan de pending_sync/.

Uso:
    from sync_manager import init_sync_manager, guardar_pendiente, contar_pendientes
    init_sync_manager(app)          # llamar una vez al arrancar la app
    guardar_pendiente(tipo, datos)  # llamar cuando el destino falla
"""

import os
import json
import threading
import time
from datetime import datetime

# ── Configuración ──────────────────────────────────────────────────────────────
PENDING_DIR = os.path.join(os.path.dirname(__file__), 'pending_sync')
CHECK_INTERVAL = 10800      # Verificar cada 3 horas
MAX_INTENTOS   = 10         # Descartar archivo después de N intentos fallidos

_app = None
_lock = threading.Lock()    # Protege acceso concurrente a pending_sync/


# ── Helpers de cola local ──────────────────────────────────────────────────────

def guardar_pendiente(tipo: str, datos: dict, descripcion: str = "", usuario_id=None) -> str:
    """
    Guarda una operación de respaldo de forma local cuando S3 no está disponible.

    Args:
        tipo:        Etiqueta del respaldo (ej: 'completo', 'incremental').
        datos:       Diccionario con los datos a sincronizar.
        descripcion: Texto libre para identificar el origen del respaldo.
        usuario_id:  ID del usuario que originó la operación.

    Returns:
        Ruta absoluta del archivo JSON creado.
    """
    os.makedirs(PENDING_DIR, exist_ok=True)

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    nombre    = f"pending_{tipo}_{timestamp}.json"
    ruta      = os.path.join(PENDING_DIR, nombre)

    item = {
        'tipo':        tipo,
        'datos':       datos,
        'descripcion': descripcion,
        'usuario_id':  usuario_id,
        'created_at':  datetime.utcnow().isoformat(),
        'intentos':    0
    }

    with _lock:
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(item, f, ensure_ascii=False, indent=2)

    print(f"[SYNC] En cola local: {nombre}")
    return ruta


def contar_pendientes() -> int:
    """Retorna cuántos respaldos están esperando ser sincronizados con la nube."""
    if not os.path.exists(PENDING_DIR):
        return 0
    with _lock:
        return len([f for f in os.listdir(PENDING_DIR)
                    if f.startswith('pending_') and f.endswith('.json')])


def listar_pendientes() -> list:
    """Retorna metadata de los archivos pendientes (sin datos voluminosos)."""
    resultado = []
    if not os.path.exists(PENDING_DIR):
        return resultado

    with _lock:
        archivos = sorted(
            [f for f in os.listdir(PENDING_DIR)
             if f.startswith('pending_') and f.endswith('.json')]
        )

    for nombre in archivos:
        ruta = os.path.join(PENDING_DIR, nombre)
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                item = json.load(f)
            resultado.append({
                'archivo':     nombre,
                'tipo':        item.get('tipo'),
                'descripcion': item.get('descripcion'),
                'created_at':  item.get('created_at'),
                'intentos':    item.get('intentos', 0)
            })
        except Exception:
            pass

    return resultado


# ── Motor de sincronización ────────────────────────────────────────────────────

def _subir_archivo_pendiente(nombre: str, storage) -> bool:
    """
    Intenta subir un archivo pendiente al destino configurado (USB/S3)
    y registrarlo en la BD.
    Retorna True si tuvo éxito, False en caso contrario.
    """
    from models import db, Respaldo

    ruta = os.path.join(PENDING_DIR, nombre)

    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            item = json.load(f)
    except Exception as e:
        print(f"[SYNC] [ERROR] No se pudo leer {nombre}: {e}")
        return False

    tipo        = item.get('tipo', 'completo')
    datos       = item.get('datos', {})
    descripcion = item.get('descripcion', '')
    usuario_id  = item.get('usuario_id')
    created_at  = item.get('created_at', datetime.utcnow().isoformat())

    # Construir nombre de archivo S3 basado en timestamp original
    ts_limpio  = created_at[:19].replace(':', '').replace('-', '').replace('T', '_')
    nombre_s3  = f"respaldo_{tipo}_{ts_limpio}_sync.json"

    resultado = storage.subir_respaldo(datos, nombre_s3, descripcion)

    if resultado['success']:
        # Registrar en BD local
        try:
            with _app.app_context():
                respaldo = Respaldo(
                    nombre_archivo=nombre_s3,
                    tipo=tipo,
                    s3_key=resultado['s3_key'],
                    tamaño_bytes=resultado.get('size'),
                    descripcion=f"[SYNC-OFFLINE] {descripcion}",
                    creado_por_id=usuario_id
                )
                db.session.add(respaldo)
                db.session.commit()
        except Exception as e:
            print(f"[SYNC] [AVISO] Subido pero no registrado en BD: {e}")

        # Eliminar archivo local ya sincronizado
        with _lock:
            try:
                os.remove(ruta)
            except OSError:
                pass

        print(f"[SYNC] [OK] Sincronizado: {nombre}")
        return True
    else:
        # Incrementar contador de intentos
        item['intentos'] = item.get('intentos', 0) + 1
        with _lock:
            try:
                with open(ruta, 'w', encoding='utf-8') as f:
                    json.dump(item, f, ensure_ascii=False, indent=2)
            except OSError:
                pass

        if item['intentos'] >= MAX_INTENTOS:
            print(f"[SYNC] [DESCARTADO] {nombre} tras {MAX_INTENTOS} intentos: {resultado.get('error')}")
            # Mover a subcarpeta de descartados en lugar de borrar
            fallidos_dir = os.path.join(PENDING_DIR, 'fallidos')
            os.makedirs(fallidos_dir, exist_ok=True)
            with _lock:
                try:
                    os.rename(ruta, os.path.join(fallidos_dir, nombre))
                except OSError:
                    pass
        else:
            print(f"[SYNC] [AVISO] Fallo {nombre} (intento {item['intentos']}): {resultado.get('error')}")

        return False


def procesar_pendientes(app=None) -> dict:
    """
    Procesa la cola de respaldos pendientes.
    Puede llamarse manualmente o desde el hilo en background.

    Returns:
        Dict con: {'verificados': int, 'exitosos': int, 'fallidos': int, 'cloud_ok': bool}
    """
    # Importación diferida para evitar import circular
    from cloud_storage import crear_storage_manager

    resultado = {'verificados': 0, 'exitosos': 0, 'fallidos': 0, 'cloud_ok': False}

    storage = crear_storage_manager()
    if not storage.verificar_conexion():
        print("[SYNC] [AVISO] Destino no disponible - respaldos en cola local")
        return resultado

    resultado['cloud_ok'] = True

    if not os.path.exists(PENDING_DIR):
        return resultado

    with _lock:
        pendientes = sorted([
            f for f in os.listdir(PENDING_DIR)
            if f.startswith('pending_') and f.endswith('.json')
        ])

    if not pendientes:
        return resultado

    print(f"[SYNC] Conexion restaurada - sincronizando {len(pendientes)} respaldo(s)...")

    for nombre in pendientes:
        resultado['verificados'] += 1
        if _subir_archivo_pendiente(nombre, storage):
            resultado['exitosos'] += 1
        else:
            resultado['fallidos'] += 1

    if resultado['exitosos']:
        print(f"[SYNC] [OK] Sincronizacion completa: {resultado['exitosos']}/{resultado['verificados']} subidos")

    return resultado


# ── Hilo en background ─────────────────────────────────────────────────────────

def _loop_sincronizacion():
    """Hilo daemon que verifica y sincroniza periódicamente."""
    time.sleep(30)  # Dar tiempo al arranque de la app
    print(f"[SYNC] Monitor iniciado (intervalo: {CHECK_INTERVAL // 60} min)")

    while True:
        try:
            if os.path.exists(PENDING_DIR):
                with _lock:
                    hay_pendientes = bool([
                        f for f in os.listdir(PENDING_DIR)
                        if f.startswith('pending_') and f.endswith('.json')
                    ])
                if hay_pendientes:
                    with _app.app_context():
                        procesar_pendientes()
        except Exception as e:
            print(f"[SYNC] [ERROR] Error en ciclo de sincronizacion: {e}")

        time.sleep(CHECK_INTERVAL)


# ── Inicialización ─────────────────────────────────────────────────────────────

def init_sync_manager(app):
    """
    Inicia el gestor de sincronización local↔nube en un hilo de background.
    Llamar una vez después de crear la app Flask.
    """
    global _app
    _app = app

    os.makedirs(PENDING_DIR, exist_ok=True)

    pendientes_al_inicio = contar_pendientes()
    if pendientes_al_inicio:
        print(f"[SYNC] [AVISO] {pendientes_al_inicio} respaldo(s) pendiente(s) de la sesion anterior")

    hilo = threading.Thread(
        target=_loop_sincronizacion,
        daemon=True,
        name="SyncManager"
    )
    hilo.start()
    print("[SYNC] Gestor de sincronizacion local<->nube iniciado")
