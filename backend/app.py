import os
from dotenv import load_dotenv

# Cargar variables de entorno desde backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from flask import Flask, jsonify, send_from_directory, request, session
from flask_cors import CORS
from datetime import datetime
from models import db, Usuario
from config import config
from flask_socketio import SocketIO
from security_shield import (
    aplicar_headers_seguridad, 
    validar_configuracion_seguridad,
    log_evento_seguridad
)
from security_advanced import (
    EncriptadorDatos,
    AuditoriaAdministrativa,
    SesionSegura,
    PoliticaBloqueoCuenta
)

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, 'development'))
    
    # ═ Session Security Headers
    app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # No acceso desde JS
    app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'  # CSRF protection
    app.config['PERMANENT_SESSION_LIFETIME'] = 28800  # 8 horas
    
    # Inicializar encriptador de datos sensibles
    EncriptadorDatos.inicializar()
    
    # Inicializar SocketIO para actualizaciones en tiempo real
    socketio = SocketIO(app, 
                       cors_allowed_origins="*",
                       async_mode='threading',
                       transports=['websocket', 'polling'])
    
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    db.init_app(app)
    
    @app.before_request
    def before_request():
        db.session.expire_on_commit = False
    
    @app.after_request
    def agregar_cabeceras_seguridad(response):
        """Añade headers de seguridad HTTP recomendados por OWASP a todas las respuestas."""
        return aplicar_headers_seguridad(response)

    @app.before_request
    def validar_entrada():
        """Validaciones básicas en cada request para seguridad"""
        
        # Validar sesión si existe
        if 'usuario_id' in session:
            valida, msg = SesionSegura.validar_sesion()
            if not valida:
                SesionSegura.destruir_sesion()
                return jsonify({'error': msg}), 401
        
        # Log de request (eventos críticos)
        if request.method in ['POST', 'PUT', 'DELETE']:
            log_evento_seguridad(
                f'{request.method.upper()} {request.path}',
                usuario_id=None,
                detalles=f'IP: {request.remote_addr}'
            )

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()
    
    with app.app_context():
        db.create_all()
        _migrar_columna_vigilante_id()
        crear_admin_por_defecto()
        crear_vigilante_por_defecto()
    
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    @app.route('/api/status', methods=['GET'])
    def status():
        from models import Persona, RegistroAcceso
        
        try:
            total_personas = Persona.query.filter_by(deleted_at=None).count()
            total_accesos = RegistroAcceso.query.filter_by(deleted_at=None).count()
            total_usuarios = Usuario.query.filter_by(deleted_at=None).count()
            
            return jsonify({
                'status': 'ok',
                'timestamp': datetime.utcnow().isoformat(),
                'stats': {
                    'total_personas': total_personas,
                    'total_accesos': total_accesos,
                    'total_usuarios': total_usuarios
                }
            }), 200
        except Exception as e:
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    @app.route('/login', methods=['GET'])
    @app.route('/login.html', methods=['GET'])
    def serve_login():
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            return send_from_directory(os.path.join(parent_dir, 'frontend'), 'login.html')
        except Exception as e:
            return jsonify({'error': 'File not found', 'details': str(e)}), 404

    @app.route('/', methods=['GET'])
    @app.route('/ingreso', methods=['GET'])
    @app.route('/ingreso.html', methods=['GET'])
    def serve_ingreso():
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            resp = send_from_directory(os.path.join(parent_dir, 'frontend'), 'ingreso.html')
            resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            resp.headers['Pragma'] = 'no-cache'
            resp.headers['Expires'] = '0'
            return resp
        except Exception as e:
            return jsonify({'error': 'File not found', 'details': str(e)}), 404
    
    @app.route('/vigilancia', methods=['GET'])
    @app.route('/vigilancia.html', methods=['GET'])
    def serve_vigilancia():
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            return send_from_directory(os.path.join(parent_dir, 'frontend'), 'vigilancia.html')
        except Exception as e:
            return jsonify({'error': 'File not found', 'details': str(e)}), 404
    
    @app.route('/administracion', methods=['GET'])
    @app.route('/administracion.html', methods=['GET'])
    def serve_administracion():
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            return send_from_directory(os.path.join(parent_dir, 'frontend'), 'administracion.html')
        except Exception as e:
            return jsonify({'error': 'File not found', 'details': str(e)}), 404

    @app.route('/pago-resultado', methods=['GET'])
    def serve_pago_resultado():
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            return send_from_directory(os.path.join(parent_dir, 'frontend'), 'pago_resultado.html')
        except Exception as e:
            return jsonify({'error': 'File not found', 'details': str(e)}), 404
    
    @app.route('/frontend/<path:filename>', methods=['GET'])
    def serve_frontend(filename):
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            return send_from_directory(os.path.join(parent_dir, 'frontend'), filename)
        except Exception as e:
            return jsonify({'error': 'File not found', 'details': str(e)}), 404
    
    @app.route('/js/<path:filename>', methods=['GET'])
    def serve_js(filename):
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            return send_from_directory(os.path.join(parent_dir, 'js'), filename)
        except Exception as e:
            return jsonify({'error': 'File not found', 'details': str(e)}), 404
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request'}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized'}), 401
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    from routes import api_bp
    from db_viewer import db_viewer_bp
    from pagos import pagos_bp
    from websocket_handler import init_websocket, init_actualiza_continuo
    from scheduler import init_scheduler
    from sync_manager import init_sync_manager
    
    app.register_blueprint(api_bp)
    app.register_blueprint(db_viewer_bp)
    app.register_blueprint(pagos_bp)
    
    # Inicializar WebSocket y monitoreo continuo
    init_websocket(app, socketio)
    init_actualiza_continuo(app)
    
    # Exportación automática a Excel/USB cada hora + sync nube cada 5 min
    init_scheduler(app)

    # Sincronización local ↔ nube (sube respaldos pendientes cuando vuelve la conexión)
    init_sync_manager(app)

    # Registrar comandos CLI (flask usuario crear/listar/...)
    registrar_comandos(app)

    return app, socketio

def _migrar_columna_vigilante_id():
    """Agrega la columna vigilante_id a registros_acceso si no existe (migración SQLite)."""
    try:
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(db.engine)
        cols = [c['name'] for c in inspector.get_columns('registros_acceso')]
        if 'vigilante_id' not in cols:
            with db.engine.connect() as conn:
                conn.execute(db.text('ALTER TABLE registros_acceso ADD COLUMN vigilante_id VARCHAR(36) REFERENCES usuarios(id)'))
                conn.commit()
                print('[DB] Columna vigilante_id añadida a registros_acceso')
    except Exception as e:
        print(f'[DB] Migración vigilante_id: {e}')


def crear_admin_por_defecto():
    admin = Usuario.query.filter_by(email='admin@sena.edu.co').first()
    if not admin:
        from werkzeug.security import generate_password_hash
        import secrets
        password = os.getenv('ADMIN_PASSWORD')
        if not password:
            password = secrets.token_urlsafe(12)
            print('=' * 55)
            print(' USUARIO ADMIN CREADO AUTOMATICAMENTE')
            print(f'  Email   : admin@sena.edu.co')
            print(f'  Password: {password}')
            print(' Guarda esta contraseña — no se volverá a mostrar.')
            print('=' * 55)
        admin = Usuario(
            email='admin@sena.edu.co',
            password_hash=generate_password_hash(password),
            nombre='Administrador',
            rol='admin',
            activo=True
        )
        db.session.add(admin)
        db.session.commit()

def crear_vigilante_por_defecto():
    vigilante = Usuario.query.filter_by(email='vigilante@sena.edu.co').first()
    if not vigilante:
        from werkzeug.security import generate_password_hash
        import secrets
        password = os.getenv('VIGILANTE_PASSWORD')
        if not password:
            password = secrets.token_urlsafe(12)
            print('=' * 55)
            print(' USUARIO VIGILANTE CREADO AUTOMATICAMENTE')
            print(f'  Email   : vigilante@sena.edu.co')
            print(f'  Password: {password}')
            print(' Guarda esta contraseña — no se volverá a mostrar.')
            print('=' * 55)
        vigilante = Usuario(
            email='vigilante@sena.edu.co',
            password_hash=generate_password_hash(password),
            nombre='Vigilante',
            rol='vigilante',
            activo=True
        )
        db.session.add(vigilante)
        db.session.commit()

# ── Comandos CLI ──────────────────────────────────────────────
# Uso desde terminal (en la carpeta backend, con el venv activo):
#   flask usuario crear  --email x@sena.edu.co --password MiClave1 --rol admin
#   flask usuario listar
#   flask usuario cambiar-password --email x@sena.edu.co --password NuevaClave
#   flask usuario desactivar --email x@sena.edu.co

import click

def registrar_comandos(app):
    @app.cli.group()
    def usuario():
        """Gestión de usuarios del sistema."""
        pass

    @usuario.command('crear')
    @click.option('--email', prompt='Email', help='Correo del usuario')
    @click.option('--password', prompt='Contraseña', hide_input=True,
                  confirmation_prompt=True, help='Contraseña')
    @click.option('--nombre', default='', help='Nombre completo')
    @click.option('--rol', type=click.Choice(['admin', 'vigilante', 'sistemas']),
                  prompt='Rol (admin/vigilante/sistemas)', default='vigilante',
                  help='Rol del usuario')
    def crear_usuario(email, password, nombre, rol):
        """Crea un nuevo usuario."""
        from werkzeug.security import generate_password_hash
        from validaciones import (
            validar_formato_email, validar_dominio_email,
            validar_contrasena, validar_nombre, describir_politica_contrasena
        )

        email = email.strip().lower()
        ok_fmt, msg_fmt = validar_formato_email(email)
        if not ok_fmt:
            click.secho(f'[ERROR] {msg_fmt}', fg='red')
            return
        ok_dom, msg_dom = validar_dominio_email(email)
        if not ok_dom:
            click.secho(f'[ADVERTENCIA] {msg_dom}', fg='yellow')
        elif msg_dom:
            click.secho(f'[INFO] {msg_dom}', fg='cyan')

        if nombre:
            from validaciones import validar_nombre
            ok_nom, msg_nom = validar_nombre(nombre)
            if not ok_nom:
                click.secho(f'[ERROR] {msg_nom}', fg='red')
                return

        ok_pwd, errores_pwd = validar_contrasena(password)
        if not ok_pwd:
            click.secho('[ERROR] La contraseña no cumple los requisitos de seguridad:', fg='red')
            for e in errores_pwd:
                click.secho(f'  - {e}', fg='red')
            click.secho(describir_politica_contrasena(), fg='yellow')
            return

        if Usuario.query.filter_by(email=email).first():
            click.secho(f'[ERROR] Ya existe un usuario con email {email}', fg='red')
            return
        u = Usuario(
            email=email,
            password_hash=generate_password_hash(password),
            nombre=nombre or email.split('@')[0],
            rol=rol,
            activo=True
        )
        db.session.add(u)
        db.session.commit()
        click.secho(f'[OK] Usuario creado: {email}  rol={rol}', fg='green')

    @usuario.command('listar')
    def listar_usuarios():
        """Lista todos los usuarios activos."""
        usuarios = Usuario.query.filter_by(deleted_at=None).order_by(Usuario.rol).all()
        if not usuarios:
            click.echo('No hay usuarios.')
            return
        click.echo(f'\n{"EMAIL":<35} {"ROL":<10} {"NOMBRE":<25} ACTIVO')
        click.echo('-' * 80)
        for u in usuarios:
            activo = 'Si' if u.activo else 'No'
            click.echo(f'{u.email:<35} {u.rol:<10} {u.nombre:<25} {activo}')
        click.echo()

    @usuario.command('cambiar-password')
    @click.option('--email', prompt='Email del usuario')
    @click.option('--password', prompt='Nueva contraseña', hide_input=True,
                  confirmation_prompt=True)
    def cambiar_password(email, password):
        """Cambia la contraseña de un usuario."""
        from werkzeug.security import generate_password_hash
        from validaciones import validar_contrasena, describir_politica_contrasena
        u = Usuario.query.filter_by(email=email, deleted_at=None).first()
        if not u:
            click.secho(f'[ERROR] No se encontró usuario con email {email}', fg='red')
            return
        ok_pwd, errores_pwd = validar_contrasena(password)
        if not ok_pwd:
            click.secho('[ERROR] La contraseña no cumple los requisitos de seguridad:', fg='red')
            for e in errores_pwd:
                click.secho(f'  - {e}', fg='red')
            click.secho(describir_politica_contrasena(), fg='yellow')
            return
        u.password_hash = generate_password_hash(password)
        db.session.commit()
        click.secho(f'[OK] Contraseña actualizada para {email}', fg='green')

    @usuario.command('desactivar')
    @click.option('--email', prompt='Email del usuario')
    def desactivar_usuario(email):
        """Desactiva un usuario (no lo elimina)."""
        u = Usuario.query.filter_by(email=email, deleted_at=None).first()
        if not u:
            click.secho(f'[ERROR] No se encontró usuario con email {email}', fg='red')
            return
        u.activo = False
        db.session.commit()
        click.secho(f'[OK] Usuario {email} desactivado', fg='yellow')


if __name__ == '__main__':
    app, socketio = create_app()
    registrar_comandos(app)
    # use_reloader=False evita que el proceso arranque el doble (mucho más rápido)
    socketio.run(app, debug=False, use_reloader=False, host='0.0.0.0', port=8000)
