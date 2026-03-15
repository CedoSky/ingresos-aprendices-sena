"""
Exportación automática a Excel/USB cada hora.
Sincronización de respaldos locales con la nube cada 5 minutos.
Ambos corren en hilos de fondo — completamente transparentes para el usuario.
"""

import threading
import time
import os
from datetime import datetime


# Intervalo en segundos (3600 = 1 hora)
INTERVALO_HORAS = 3600

# Intervalo de verificación de sincronización (3 horas)
INTERVALO_SYNC = 10800


def _exportar(app):
    """Ejecuta la exportación y loguea el resultado."""
    try:
        from export_excel import exportar_todo_excel
        _, nombre, usb_ok, ruta = exportar_todo_excel(app)
        destino = f"USB -> {ruta}" if usb_ok else f"local -> {ruta}"
        print(f"[SCHEDULER] [OK] Excel exportado: {nombre}  |  {destino}")
    except Exception as e:
        print(f"[SCHEDULER] [ERROR] Exportacion automatica: {e}")


def _sincronizar(app):
    """Intenta subir a la nube cualquier respaldo pendiente."""
    try:
        from sync_manager import procesar_pendientes, contar_pendientes
        if contar_pendientes() > 0:
            with app.app_context():
                r = procesar_pendientes(app)
                if r.get('exitosos'):
                    print(f"[SCHEDULER] [SYNC] {r['exitosos']} respaldo(s) subido(s)")
    except Exception as e:
        print(f"[SCHEDULER] [ERROR] Sincronizacion automatica: {e}")


def init_scheduler(app):
    """
    Lanza dos hilos en background:
      1. ExcelScheduler — exporta a Excel/USB cada hora.
      2. SyncScheduler  — revisa y sube respaldos pendientes cada 5 min.
    La primera ejecución de cada uno ocurre poco después del arranque.
    """

    # ── Hilo de exportación Excel ──────────────────────────────────────────────
    def loop_excel():
        time.sleep(60)
        print(f"[SCHEDULER] Exportacion automatica iniciada - cada {INTERVALO_HORAS // 3600}h")
        _exportar(app)
        while True:
            time.sleep(INTERVALO_HORAS)
            _exportar(app)

    threading.Thread(target=loop_excel, daemon=True, name="ExcelScheduler").start()

    # ── Hilo de sincronización con la nube ─────────────────────────────────────
    def loop_sync():
        time.sleep(90)   # Arrancar un poco después que Excel para no saturar
        print(f"[SCHEDULER] Sincronizacion nube iniciada - cada {INTERVALO_SYNC // 3600}h")
        _sincronizar(app)
        while True:
            time.sleep(INTERVALO_SYNC)
            _sincronizar(app)

    threading.Thread(target=loop_sync, daemon=True, name="SyncScheduler").start()

