"""
Gestion de usuarios SENA - ejecutado desde GESTIONAR_USUARIOS.bat
Usa una app Flask minima, sin scheduler ni websockets, sin logs en pantalla.
"""
import os, sys, logging, warnings

# Silenciar TODO antes de importar nada
logging.disable(logging.CRITICAL)
warnings.filterwarnings('ignore')
os.environ.setdefault('FLASK_ENV', 'development')

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from flask import Flask
from models import db, Usuario
from werkzeug.security import generate_password_hash
import getpass
import urllib.request
import random
import time
import requests
from validaciones import (
    validar_formato_email,
    validar_dominio_email,
    validar_contrasena,
    validar_nombre,
    describir_politica_contrasena,
)

# App minima: solo BD, sin rutas, sin scheduler, sin websocket
def crear_app_minima():
    app = Flask(__name__)
    # Usar siempre SQLite local (igual que DevelopmentConfig)
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'sena.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    db.init_app(app)
    with app.app_context():
        db.create_all()
    return app

app = crear_app_minima()

# ─────────────────────────────────────────
def _notificar_servidor():
    """Sincroniza las cuentas locales con la base cloud y avisa al servidor local."""
    try:
        cloud_url = os.getenv('CLOUD_URL', '').rstrip('/')
        cloud_email = os.getenv('CLOUD_ADMIN_EMAIL', 'admin@sena.edu.co')
        cloud_password = os.getenv('CLOUD_ADMIN_PASSWORD') or os.getenv('ADMIN_PASSWORD')
        if cloud_url and cloud_password:
            with app.app_context():
                usuarios = Usuario.query.filter_by(deleted_at=None).all()
                payload = {'usuarios': [
                    {'email': u.email, 'nombre': u.nombre, 'rol': u.rol,
                     'activo': bool(u.activo), 'password_hash': u.password_hash}
                    for u in usuarios
                ]}
            login = requests.post(f'{cloud_url}/api/auth/login',
                                  json={'email': cloud_email, 'password': cloud_password}, timeout=30)
            login.raise_for_status()
            token = login.json()['token']
            sync = requests.post(f'{cloud_url}/api/admin/importar-usuarios',
                                 json=payload,
                                 headers={'Authorization': f'Bearer {token}'}, timeout=30)
            sync.raise_for_status()
            print(f'  [CLOUD] {sync.json().get("importados", 0)} usuarios sincronizados.')
    except Exception as e:
        print(f'  [CLOUD] No se pudo sincronizar: {e}')
    try:
        secret = os.getenv('SECRET_KEY', '')
        req = urllib.request.Request(
            'http://localhost:8000/api/interno/notificar-usuarios',
            data=b'{}',
            headers={'Content-Type': 'application/json', 'X-Internal-Secret': secret},
            method='POST'
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # El servidor puede no estar corriendo; no es crítico

def listar():
    with app.app_context():
        usuarios = Usuario.query.filter_by(deleted_at=None).order_by(Usuario.rol).all()
        if not usuarios:
            print('\n  (sin usuarios)\n')
            return
        print(f'\n  {"EMAIL":<35} {"ROL":<10} {"NOMBRE":<25} ACTIVO')
        print('  ' + '-' * 78)
        for u in usuarios:
            activo = 'Si' if u.activo else 'No'
            print(f'  {u.email:<35} {u.rol:<10} {u.nombre:<25} {activo}')
        print()

def crear():
    print('\n--- Crear usuario ---')

    # ── Email ──────────────────────────────────────────────────────────────
    email = input('  Email            : ').strip().lower()
    ok_fmt, msg_fmt = validar_formato_email(email)
    if not ok_fmt:
        print(f'  [ERROR] {msg_fmt}')
        return

    print('  Verificando dominio...')
    ok_dom, msg_dom = validar_dominio_email(email, verbose=True)
    if not ok_dom:
        print(f'  [ERROR] {msg_dom}')
        return
    elif msg_dom:
        print(f'  [!] {msg_dom}')

    with app.app_context():
        existente = Usuario.query.filter_by(email=email).first()
        if existente:
            if existente.deleted_at is not None:
                # Fue eliminado antes — reactivarlo en vez de duplicar
                resp = input(f'  Este correo existía antes y fue eliminado. ¿Reactivar ese usuario? (s/N): ').strip().lower()
                if resp != 's':
                    return
                # Se continúa y se sobreescribe más abajo
            else:
                print(f'  [ERROR] Ya existe un usuario activo con email "{email}"')
                return

    # ── Nombre ─────────────────────────────────────────────────────────────
    nombre = input('  Nombre completo  : ').strip()
    ok_nom, msg_nom = validar_nombre(nombre)
    if not ok_nom:
        print(f'  [ERROR] {msg_nom}')
        return

    # ── Verificación de correo por código ──────────────────────────────────
    import sys as _sys
    # Importar aquí para no depender del servidor corriendo
    _backend_dir = os.path.dirname(__file__)
    if _backend_dir not in _sys.path:
        _sys.path.insert(0, _backend_dir)
    try:
        import correo as _correo
        if _correo._configurado():
            codigo = str(random.randint(100000, 999999))
            expira = time.time() + 600  # 10 minutos
            print(f'\n  Enviando código de verificación a {email}...')
            enviado = _correo.enviar_codigo_verificacion(email, codigo, nombre)
            if enviado:
                print('  Código enviado. Revisa tu bandeja de entrada (o spam).')
                intentos = 3
                verificado = False
                while intentos > 0:
                    ingresado = input(f'  Ingresa el código de 6 dígitos ({intentos} intento(s)): ').strip()
                    if time.time() > expira:
                        print('  [ERROR] El código expiró. Vuelve a iniciar el proceso.')
                        return
                    if ingresado == codigo:
                        verificado = True
                        print('  [OK] Correo verificado correctamente.')
                        break
                    intentos -= 1
                    if intentos > 0:
                        print(f'  [ERROR] Código incorrecto.')
                if not verificado:
                    print('  [ERROR] Demasiados intentos fallidos. Operación cancelada.')
                    return
            else:
                print('  [!] No se pudo enviar el código (revisa la configuración de correo en .env).')
                resp = input('  ¿Continuar sin verificar el correo? (s/N): ').strip().lower()
                if resp != 's':
                    return
        else:
            print('  [!] Correo no configurado en .env — se omite verificación.')
    except Exception as e:
        print(f'  [!] Verificación de correo omitida: {e}')

    # ── Contraseña ──────────────────────────────────────────────────────────
    print(f'\n  {describir_politica_contrasena().replace(chr(10), chr(10)+"  ")}')
    while True:
        pwd = getpass.getpass('  Contrasena       : ')
        if not pwd:
            print('  [ERROR] La contrasena no puede estar vacia.')
            continue
        ok_pwd, errores_pwd = validar_contrasena(pwd)
        if not ok_pwd:
            print('  [ERROR] La contraseña no cumple los requisitos:')
            for e in errores_pwd:
                print(f'    - {e}')
            reintentar = input('  ¿Intentar de nuevo? (S/n): ').strip().lower()
            if reintentar == 'n':
                return
            continue
        pwd2 = getpass.getpass('  Repetir          : ')
        if pwd != pwd2:
            print('  [ERROR] Las contrasenas no coinciden.')
            continue
        break

    # ── Rol ────────────────────────────────────────────────────────────────
    rol = input('  Rol (admin/vigilante/sistemas) [vigilante]: ').strip() or 'vigilante'
    if rol not in ('admin', 'vigilante', 'sistemas'):
        print('  [ERROR] Rol invalido. Usa admin, vigilante o sistemas.')
        return

    with app.app_context():
        existente = Usuario.query.filter_by(email=email).first()
        if existente and existente.deleted_at is not None:
            # Reactivar registro eliminado con los nuevos datos
            from werkzeug.security import generate_password_hash as _gph
            existente.deleted_at = None
            existente.activo = True
            existente.nombre = nombre
            existente.rol = rol
            existente.password_hash = _gph(pwd)
            db.session.commit()
        else:
            u = Usuario(
                email=email,
                password_hash=generate_password_hash(pwd),
                nombre=nombre,
                rol=rol,
                activo=True
            )
            db.session.add(u)
            db.session.commit()
        print(f'\n  [OK] Usuario creado: {email}  rol={rol}\n')
        _notificar_servidor()

def cambiar_password():
    print('\n--- Cambiar contrasena ---')
    email = input('  Email del usuario: ').strip()
    with app.app_context():
        u = Usuario.query.filter_by(email=email, deleted_at=None).first()
        if not u:
            print(f'\n  [ERROR] No se encontro usuario con email "{email}"\n')
            return

    print(f'\n  {describir_politica_contrasena().replace(chr(10), chr(10)+"  ")}')
    while True:
        pwd = getpass.getpass('  Nueva contrasena : ')
        if not pwd:
            print('  [ERROR] La contrasena no puede estar vacia.')
            continue
        ok_pwd, errores_pwd = validar_contrasena(pwd)
        if not ok_pwd:
            print('  [ERROR] La contraseña no cumple los requisitos:')
            for e in errores_pwd:
                print(f'    - {e}')
            reintentar = input('  ¿Intentar de nuevo? (S/n): ').strip().lower()
            if reintentar == 'n':
                return
            continue
        pwd2 = getpass.getpass('  Repetir          : ')
        if pwd != pwd2:
            print('  [ERROR] Las contrasenas no coinciden.')
            continue
        break

    with app.app_context():
        u = Usuario.query.filter_by(email=email, deleted_at=None).first()
        u.password_hash = generate_password_hash(pwd)
        db.session.commit()
        print(f'\n  [OK] Contrasena actualizada para {email}\n')
        _notificar_servidor()

def desactivar():
    print('\n--- Desactivar / Reactivar usuario ---')
    with app.app_context():
        usuarios = Usuario.query.filter_by(deleted_at=None).order_by(Usuario.rol, Usuario.nombre).all()
        if not usuarios:
            print('\n  (sin usuarios registrados)\n')
            return

        # Mostrar lista numerada con estado visual
        print(f'\n  {"#":<4} {"NOMBRE":<28} {"ROL":<12} {"EMAIL":<35} ESTADO')
        print('  ' + '-' * 90)
        for i, u in enumerate(usuarios, start=1):
            estado = '[ ACTIVO ]' if u.activo else '[desactiv]'
            print(f'  {i:<4} {u.nombre:<28} {u.rol:<12} {u.email:<35} {estado}')
        print()

        # Selección por número
        while True:
            entrada = input('  Elige el número del usuario (o 0 para cancelar): ').strip()
            if entrada == '0':
                print('  Operación cancelada.\n')
                return
            if entrada.isdigit() and 1 <= int(entrada) <= len(usuarios):
                u = usuarios[int(entrada) - 1]
                break
            print(f'  [ERROR] Número inválido. Ingresa entre 1 y {len(usuarios)}.')

        # Mostrar resumen del usuario seleccionado
        estado_actual = 'ACTIVO' if u.activo else 'DESACTIVADO'
        accion = 'DESACTIVAR' if u.activo else 'REACTIVAR'
        print(f'\n  Usuario seleccionado:')
        print(f'    Nombre : {u.nombre}')
        print(f'    Email  : {u.email}')
        print(f'    Rol    : {u.rol}')
        print(f'    Estado : {estado_actual}')
        print(f'\n  Acción a realizar: {accion}')

        # Confirmación
        confirmacion = input(f'\n  ¿Confirmas {accion.lower()} a "{u.nombre}"? (s/N): ').strip().lower()
        if confirmacion != 's':
            print('  Operación cancelada.\n')
            return

        # Aplicar cambio
        u.activo = not u.activo
        db.session.commit()
        nuevo_estado = 'activado' if u.activo else 'desactivado'
        print(f'\n  [OK] Usuario "{u.nombre}" ({u.email}) {nuevo_estado} correctamente.\n')
        _notificar_servidor()

def eliminar():
    with app.app_context():
        while True:
            os.system('cls')
            print('\n--- Eliminar usuario(s) ---')
            usuarios = Usuario.query.filter_by(deleted_at=None).order_by(Usuario.rol, Usuario.nombre).all()
            if not usuarios:
                print('\n  (no hay usuarios registrados)\n')
                return

            # Mostrar lista numerada
            print(f'\n  {"#":<4} {"NOMBRE":<28} {"ROL":<12} {"EMAIL":<35} ESTADO')
            print('  ' + '-' * 90)
            for i, u in enumerate(usuarios, start=1):
                estado = '[ ACTIVO ]' if u.activo else '[desactiv]'
                print(f'  {i:<4} {u.nombre:<28} {u.rol:<12} {u.email:<35} {estado}')
            print()
            print('  Opciones: número = eliminar ese usuario | T = eliminar TODOS | 0 = salir')
            print()

            entrada = input('  Elige: ').strip()

            # Salir
            if entrada == '0':
                print('  Listo.\n')
                return

            # Eliminar TODOS
            if entrada.upper() == 'T':
                print(f'\n  Se eliminarán los {len(usuarios)} usuario(s) listados arriba.')
                print('  Esta acción es IRREVERSIBLE.')
                c1 = input('  ¿Estás seguro? (s/N): ').strip().lower()
                if c1 != 's':
                    print('  Cancelado.\n')
                    continue
                c2 = input('  Escribe  CONFIRMAR  para continuar: ').strip()
                if c2 != 'CONFIRMAR':
                    print('  Texto incorrecto — cancelado.\n')
                    continue
                from datetime import datetime
                ahora = datetime.utcnow()
                for u in usuarios:
                    u.deleted_at = ahora
                    u.activo = False
                db.session.commit()
                print(f'\n  [OK] {len(usuarios)} usuario(s) eliminado(s).\n')
                _notificar_servidor()
                return

            # Eliminar uno por número
            if entrada.isdigit() and 1 <= int(entrada) <= len(usuarios):
                u = usuarios[int(entrada) - 1]
                print(f'\n  Vas a eliminar: {u.nombre}  |  {u.rol}  |  {u.email}')
                confirmacion = input('  ¿Confirmas? (s/N): ').strip().lower()
                if confirmacion != 's':
                    print('  Cancelado.\n')
                    continue
                from datetime import datetime
                u.deleted_at = datetime.utcnow()
                u.activo = False
                db.session.commit()
                print(f'  [OK] "{u.nombre}" eliminado.\n')
                _notificar_servidor()
                continue  # vuelve al listado actualizado

            print(f'  [ERROR] Entrada inválida. Ingresa un número entre 1 y {len(usuarios)}, T para todos, o 0 para salir.')


def eliminar_todos():
    print('\n--- Eliminar TODOS los usuarios ---')
    with app.app_context():
        usuarios = Usuario.query.filter_by(deleted_at=None).order_by(Usuario.rol, Usuario.nombre).all()
        if not usuarios:
            print('\n  (no hay usuarios registrados)\n')
            return

        print(f'\n  Se eliminarán PERMANENTEMENTE los siguientes {len(usuarios)} usuario(s):')
        print(f'\n  {"#":<4} {"NOMBRE":<28} {"ROL":<12} {"EMAIL"}')
        print('  ' + '-' * 80)
        for i, u in enumerate(usuarios, start=1):
            print(f'  {i:<4} {u.nombre:<28} {u.rol:<12} {u.email}')
        print()

        c1 = input('  ¿Eliminar TODOS? (s/N): ').strip().lower()
        if c1 != 's':
            print('  Cancelado.\n')
            return

        print('  Esta acción es IRREVERSIBLE.')
        c2 = input('  Escribe  CONFIRMAR  para continuar: ').strip()
        if c2 != 'CONFIRMAR':
            print('  Texto incorrecto — cancelado.\n')
            return

        from datetime import datetime
        ahora = datetime.utcnow()
        for u in usuarios:
            u.deleted_at = ahora
            u.activo = False
        db.session.commit()
        print(f'\n  [OK] {len(usuarios)} usuario(s) eliminado(s).\n')
        _notificar_servidor()


OPCIONES = {
    '1': ('Crear nuevo usuario',            crear),
    '2': ('Listar usuarios',                listar),
    '3': ('Cambiar contrasena',             cambiar_password),
    '4': ('Desactivar / Reactivar usuario', desactivar),
    '5': ('Eliminar usuario individual',    eliminar),
    '6': ('Eliminar TODOS los usuarios',    eliminar_todos),
}

if __name__ == '__main__':
    if len(sys.argv) > 1:
        opc = sys.argv[1].strip()
        if opc in OPCIONES:
            OPCIONES[opc][1]()
        sys.exit(0)

    while True:
        os.system('cls')
        print('\n  ============================================')
        print('   GESTION DE USUARIOS - SENA')
        print('  ============================================')
        for k, (label, _) in OPCIONES.items():
            print(f'   {k}. {label}')
        print('   7. Salir')
        print()
        opc = input('  Elige una opcion (1-7): ').strip()
        if opc in OPCIONES:
            OPCIONES[opc][1]()
            input('\n  Presiona ENTER para volver al menu...')
        elif opc == '7':
            sys.exit(0)
        else:
            print('  Opcion invalida.')
            input('  Presiona ENTER para continuar...')