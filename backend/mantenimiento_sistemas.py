"""
Herramientas de mantenimiento del sistema SENA.
Ejecutado desde MANTENIMIENTO.bat con un argumento:
  info        - Estado del sistema y base de datos
  vacuum      - Optimizar base de datos
  backup      - Copia de seguridad
  integridad  - Verificar integridad de la BD
  pycache     - Limpiar cache Python
  deps        - Verificar dependencias
  logs        - Ver logs del servidor
"""
import os
import sys
import sqlite3
import shutil
import platform
import subprocess
from datetime import datetime

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND    = os.path.dirname(os.path.abspath(__file__))
INSTANCIA  = os.path.join(BACKEND, 'instance')

PATRONES_DB = [
    os.path.join(INSTANCIA, 'sena.db'),
    os.path.join(BACKEND,   'sena.db'),
]

def encontrar_db():
    for p in PATRONES_DB:
        if os.path.exists(p):
            return p
    # Busqueda general
    for root, dirs, files in os.walk(BASE_DIR):
        # Excluir carpeta de respaldos para no confundir
        dirs[:] = [d for d in dirs if d not in ('RESPALDOS_USB', '.venv', '__pycache__')]
        for f in files:
            if f.endswith('.db'):
                return os.path.join(root, f)
    return None


def cmd_info():
    print()
    print('  ============================================================')
    print('   ESTADO DEL SISTEMA')
    print('  ============================================================')
    print()
    print(f'  Python      : {sys.version.split()[0]}  ({sys.executable})')
    print(f'  Plataforma  : {platform.system()} {platform.release()} ({platform.machine()})')
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        mem = round(proc.memory_info().rss / 1024 / 1024, 1)
        print(f'  Memoria proc: {mem} MB')
    except ImportError:
        pass
    print()

    db_path = encontrar_db()
    if db_path:
        tam = os.path.getsize(db_path)
        print(f'  Base de datos : {db_path}')
        print(f'  Tamano        : {tam/1024:.1f} KB  ({tam/1024/1024:.2f} MB)')
        print()
        conn = sqlite3.connect(db_path)
        tablas = [
            ('personas',              'Personas'),
            ('registros_acceso',      'Registros de acceso'),
            ('usuarios',              'Usuarios'),
            ('computadores',          'Computadores'),
            ('registros_inventario',  'Inventario'),
            ('edificios',             'Edificios'),
        ]
        print(f'  {"Tabla":<28} {"Activos":>8}  {"Total":>8}')
        print('  ' + '-' * 48)
        for tabla, nombre in tablas:
            try:
                total   = conn.execute(f'SELECT COUNT(*) FROM {tabla}').fetchone()[0]
                activos = conn.execute(f'SELECT COUNT(*) FROM {tabla} WHERE deleted_at IS NULL').fetchone()[0]
                print(f'  {nombre:<28} {activos:>8}  {total:>8}')
            except sqlite3.OperationalError:
                print(f'  {nombre:<28}  (tabla no encontrada)')
        conn.close()
        print()
    else:
        print('  [!] Base de datos no encontrada')
        print()

    print('  Paquetes instalados:')
    print('  ' + '-' * 48)
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'list', '--format=columns'],
        capture_output=True, text=True
    )
    for linea in result.stdout.splitlines():
        print('  ' + linea)
    print()


def cmd_vacuum():
    print()
    print('  ============================================================')
    print('   OPTIMIZAR BASE DE DATOS (VACUUM + ANALYZE)')
    print('  ============================================================')
    print()
    db_path = encontrar_db()
    if not db_path:
        print('  [ERROR] No se encontro la base de datos.')
        return
    antes = os.path.getsize(db_path)
    print(f'  Base de datos : {db_path}')
    print(f'  Tamano antes  : {antes/1024:.1f} KB')
    conn = sqlite3.connect(db_path)
    conn.execute('VACUUM')
    conn.execute('ANALYZE')
    conn.close()
    despues = os.path.getsize(db_path)
    ahorro  = antes - despues
    print(f'  Tamano despues: {despues/1024:.1f} KB')
    if ahorro > 0:
        print(f'  Espacio liberado: {ahorro/1024:.1f} KB')
    else:
        print(f'  La base de datos ya estaba optimizada.')
    print()
    print('  [OK] VACUUM y ANALYZE completados.')
    print()


def cmd_backup():
    print()
    print('  ============================================================')
    print('   COPIA DE SEGURIDAD')
    print('  ============================================================')
    print()
    db_path = encontrar_db()
    if not db_path:
        print('  [ERROR] No se encontro la base de datos.')
        return
    ts   = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest_dir = os.path.join(BASE_DIR, 'RESPALDOS_USB', f'backup_manual_{ts}')
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, 'sena.db')
    shutil.copy2(db_path, dest)
    tam = os.path.getsize(dest)
    print(f'  Origen  : {db_path}')
    print(f'  Destino : {dest}')
    print(f'  Tamano  : {tam/1024:.1f} KB')
    print()
    print('  [OK] Copia de seguridad creada correctamente.')
    print()


def cmd_integridad():
    print()
    print('  ============================================================')
    print('   VERIFICAR INTEGRIDAD DE LA BASE DE DATOS')
    print('  ============================================================')
    print()
    db_path = encontrar_db()
    if not db_path:
        print('  [ERROR] No se encontro la base de datos.')
        return
    print(f'  Verificando: {db_path}')
    conn = sqlite3.connect(db_path)
    resultado  = conn.execute('PRAGMA integrity_check').fetchall()
    fk_errores = conn.execute('PRAGMA foreign_key_check').fetchall()
    conn.close()
    print()
    if resultado and resultado[0][0] == 'ok':
        print('  [OK] Integridad: correcta')
    else:
        print('  [ATENCION] Problemas de integridad:')
        for r in resultado:
            print(f'    - {r[0]}')
    if fk_errores:
        print(f'  [ATENCION] {len(fk_errores)} errores de clave foranea detectados.')
    else:
        print('  [OK] Claves foraneas: correctas')
    print()


def cmd_pycache():
    print()
    print('  ============================================================')
    print('   LIMPIAR CACHE DE PYTHON')
    print('  ============================================================')
    print()
    eliminados = 0
    for root, dirs, files in os.walk(BACKEND):
        if '__pycache__' in dirs:
            ruta = os.path.join(root, '__pycache__')
            shutil.rmtree(ruta, ignore_errors=True)
            print(f'  Eliminado: {ruta}')
            eliminados += 1
        for f in files:
            if f.endswith('.pyc'):
                ruta = os.path.join(root, f)
                os.remove(ruta)
                print(f'  Eliminado: {ruta}')
                eliminados += 1
    print()
    if eliminados:
        print(f'  [OK] {eliminados} elementos de cache eliminados.')
    else:
        print('  [OK] No habia cache que limpiar.')
    print()


def cmd_deps():
    print()
    print('  ============================================================')
    print('   VERIFICAR E INSTALAR DEPENDENCIAS')
    print('  ============================================================')
    print()
    req = os.path.join(BACKEND, 'requirements.txt')
    if not os.path.exists(req):
        print('  [ERROR] No se encontro requirements.txt')
        return
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req, '--upgrade'])
    print()
    print('  [OK] Dependencias verificadas.')
    print()


def cmd_logs():
    print()
    print('  ============================================================')
    print('   LOGS DEL SERVIDOR')
    print('  ============================================================')
    print()
    posibles = [
        os.path.join(BACKEND, 'sena.log'),
        os.path.join(BACKEND, 'error.log'),
        os.path.join(BACKEND, 'app.log'),
    ]
    log_path = next((p for p in posibles if os.path.exists(p)), None)
    if not log_path:
        print('  No se encontro ningun archivo de log.')
        print('  Configura logging en backend/app.py para registrar errores.')
        print()
        return
    print(f'  Archivo: {log_path}')
    print('  ' + '-' * 56)
    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        lineas = f.readlines()
    ultimas = lineas[-80:] if len(lineas) > 80 else lineas
    for linea in ultimas:
        print(linea, end='')
    print()
    print(f'  ({len(lineas)} lineas totales, mostrando ultimas {len(ultimas)})')
    print()


COMANDOS = {
    'info':        cmd_info,
    'vacuum':      cmd_vacuum,
    'backup':      cmd_backup,
    'integridad':  cmd_integridad,
    'pycache':     cmd_pycache,
    'deps':        cmd_deps,
    'logs':        cmd_logs,
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in COMANDOS:
        print(f'Uso: python mantenimiento_sistemas.py [{"|".join(COMANDOS)}]')
        sys.exit(1)
    COMANDOS[sys.argv[1]]()
