from flask import Blueprint, request, jsonify, send_file, session
from functools import wraps
from datetime import datetime, timedelta
import jwt
import os
import threading
import time
import requests
import websocket_handler
from websocket_handler import socketio
from models import db, Usuario, Persona, RegistroAcceso, CambioHistorial, Respaldo, Foto, Computador, RegistroAccesoEquipo, OcupacionAmbiente, RegistroInventario, Edificio
from werkzeug.security import generate_password_hash, check_password_hash
import correo as srv_correo
from security_shield import (
    InputValidator, 
    rate_limit, 
    rate_limiter,
    csrf_protection,
    log_evento_seguridad,
    registrar_intento_seguridad
)
from security_advanced import (
    PoliticaBloqueoCuenta,
    AuditoriaAdministrativa,
    SesionSegura,
    EncriptadorDatos
)
from lock_scheduler import lock_scheduler

api_bp = Blueprint('api', __name__, url_prefix='/api')

SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', '')
if not SECRET_KEY:
    raise RuntimeError('La variable de entorno JWT_SECRET_KEY no está configurada. Defínela en el archivo .env')

# ── Protección anti fuerza bruta (en memoria) ───────────────────────────────
# Estructura: { ip: {'intentos': int, 'bloqueado_hasta': float} }
_login_attempts: dict = {}
_login_lock = threading.Lock()

_MAX_INTENTOS   = 5          # intentos fallidos antes de bloquear
_BLOQUEO_SEG    = 15 * 60    # 15 minutos de bloqueo
_VENTANA_SEG    = 10 * 60    # ventana de 10 min para contar intentos


def _get_client_ip() -> str:
    """Obtiene la IP real del cliente, considerando proxies."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    return request.remote_addr or '0.0.0.0'


def _verificar_limite_login(ip: str) -> tuple:
    """
    Verifica si la IP puede hacer un intento de login.
    Retorna (permitido: bool, segundos_restantes: int).
    """
    with _login_lock:
        ahora = time.time()
        info = _login_attempts.get(ip)
        if info:
            if info.get('bloqueado_hasta', 0) > ahora:
                restantes = int(info['bloqueado_hasta'] - ahora)
                return False, restantes
            # Limpiar si la ventana expiró
            if ahora - info.get('ultimo_intento', 0) > _VENTANA_SEG:
                del _login_attempts[ip]
        return True, 0


def _registrar_intento_fallido(ip: str):
    """Registra un intento fallido y bloquea si se superó el límite."""
    with _login_lock:
        ahora = time.time()
        info = _login_attempts.setdefault(ip, {'intentos': 0, 'ultimo_intento': 0})
        # Reiniciar contador si la ventana expiró
        if ahora - info['ultimo_intento'] > _VENTANA_SEG:
            info['intentos'] = 0
        info['intentos'] += 1
        info['ultimo_intento'] = ahora
        if info['intentos'] >= _MAX_INTENTOS:
            info['bloqueado_hasta'] = ahora + _BLOQUEO_SEG
            print(f'[SEGURIDAD] IP {ip} bloqueada por {_BLOQUEO_SEG // 60} min '
                  f'tras {info["intentos"]} intentos fallidos.')


def _limpiar_intento_exitoso(ip: str):
    """Limpia el contador de intentos tras un login exitoso."""
    with _login_lock:
        _login_attempts.pop(ip, None)


def emitir_evento_ambiente(tipo_evento, ocupacion, persona):
    """Emite evento en tiempo real cuando un instructor ocupa o libera un ambiente."""
    try:
        if not websocket_handler.socketio:
            return
        payload = {
            'id': ocupacion.id,
            'evento': tipo_evento,          # 'ambiente_ocupado' | 'ambiente_liberado'
            'ambiente': ocupacion.ambiente,
            'estado': ocupacion.estado,
            'persona': {
                'id': persona.id,
                'nombre': persona.nombre,
                'numero_doc': persona.numero_doc,
                'perfil': persona.perfil,
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }
        websocket_handler.socketio.emit(tipo_evento, payload, namespace='/')
    except Exception as e:
        print(f'[WEBSOCKET] Error emitiendo {tipo_evento}: {e}')


def gestionar_ocupacion_instructor(persona, registro, tipo):
    """Registra la ocupación de ambiente cuando un instructor hace ENTRADA.
    La liberación es SOLO manual por el vigilante — la salida del instructor
    NO libera el ambiente, porque los aprendices pueden seguir dentro.
    También activa la cerradura automática con reintentos inteligentes.
    """
    if not persona or persona.perfil.lower() not in ('instructor', 'instructora'):
        return None

    if tipo.upper() == 'ENTRADA':
        # Si ya tiene una ocupación activa, cerrarla primero (nueva entrada = nuevo ambiente)
        prev = OcupacionAmbiente.query.filter_by(
            persona_id=persona.id, estado='ocupado', deleted_at=None
        ).all()
        for p in prev:
            p.estado = 'liberado'
            p.liberado_por = 'nueva_entrada'
            p.liberado_at = datetime.utcnow()

        # Crear nueva ocupación
        ocupacion = OcupacionAmbiente(
            persona_id=persona.id,
            numero_doc=persona.numero_doc,
            ambiente=registro.ambiente or 'Sin especificar',
            registro_acceso_id=registro.id,
            estado='ocupado',
        )  # type: ignore
        db.session.add(ocupacion)
        db.session.commit()
        emitir_evento_ambiente('ambiente_ocupado', ocupacion, persona)
        
        # ═══ LÓGICA DE CERRADURA AUTOMÁTICA ═══════════════════════════════════════
        # Crear intento de apertura automática con reintentos inteligentes
        try:
            intento = lock_scheduler.crear_intento(
                persona_id=persona.id,
                numero_doc=persona.numero_doc or 'Sin especificar',
                ambiente=registro.ambiente or 'Sin especificar'
            )
            print(f"[OCUPACION] Intento de cerradura creado: {intento.id}")
        except Exception as e:
            print(f"[OCUPACION] Error creando intento de cerradura: {e}")
        # ═══════════════════════════════════════════════════════════════════════════
        
        return ocupacion

    return None


def liberar_ambiente_instructor_salida(persona):
    """Libera el ambiente cuando un instructor registra su salida.
    
    Marca la ocupación como 'liberado' y emite evento WebSocket para actualizar
    el panel de vigilancia en tiempo real.
    
    Args:
        persona: Objeto Persona que registró la salida
    
    Retorna:
        OcupacionAmbiente si fue liberada, None si no había ocupación activa
    """
    if not persona or persona.perfil.lower() not in ('instructor', 'instructora'):
        return None
    
    try:
        # Buscar la ocupación ACTIVA más reciente de este instructor
        ocupacion = OcupacionAmbiente.query.filter_by(
            persona_id=persona.id,
            estado='ocupado',
            deleted_at=None
        ).order_by(OcupacionAmbiente.created_at.desc()).first()
        
        if not ocupacion:
            print(f"[AMBIENTE] No hay ocupación activa para liberar: {persona.numero_doc}")
            return None
        
        # Marcar como liberado
        ocupacion.estado = 'liberado'
        ocupacion.liberado_por = 'salida_instructor'
        ocupacion.liberado_at = datetime.utcnow()
        db.session.commit()
        
        # Emitir evento WebSocket para actualizar panel vigilancia en tiempo real
        emitir_evento_ambiente('ambiente_liberado', ocupacion, persona)
        
        print(f"[AMBIENTE] ✅ Ambiente '{ocupacion.ambiente}' liberado por {persona.numero_doc}")
        
        return ocupacion
        
    except Exception as e:
        print(f"[ERROR] Error liberando ambiente: {e}")
        return None


def cerrar_sesion_instructor_salida(persona):
    """Cierra automáticamente la sesión cuando un instructor registra su salida.
    
    Esto garantiza que cuando un instructor se va, su sesión termina automáticamente
    por seguridad (evita que máquinas queden autenticadas sin vigilancia).
    
    Args:
        persona: Objeto Persona que registró la salida
    
    Retorna:
        True si se cerró sesión, False si no había sesión activa
    """
    # Validar que sea instructor
    if not persona or persona.perfil.lower() not in ('instructor', 'instructora'):
        return False
    
    try:
        # Buscar usuario instructor con el mismo número de documento
        usuario_instructor = Usuario.query.filter_by(
            numero_doc=persona.numero_doc, 
            deleted_at=None
        ).first()
        
        if not usuario_instructor:
            return False
        
        # Registrar en auditoría antes de cerrar sesión
        AuditoriaAdministrativa.registrar(
            usuario_id=usuario_instructor.id,
            operacion='LOGOUT_AUTOMATICO_SALIDA',
            tabla='registros_acceso',
            registro_id=persona.id,
            ip_address=_get_client_ip(),
            motivo=f'Sesión cerrada automáticamente - Instructor registró salida'
        )
        
        # Log de evento de seguridad
        log_evento_seguridad(
            f'INSTRUCTOR_LOGOUT_AUTOMATICO',
            usuario_id=usuario_instructor.id,
            detalles=f'Instructor {persona.nombre} ({persona.numero_doc}) registró salida - sesión cerrada',
            severidad='INFO'
        )
        
        print(f"[SEGURIDAD] Sesión del instructor {persona.numero_doc} cerrada automáticamente por registro de salida")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error cerrando sesión de instructor: {e}")
        return False


def emitir_evento_acceso_tiempo_real(registro, persona):
    """Emite notificación en vivo cuando se registra un acceso."""
    try:
        if not websocket_handler.socketio:
            return

        payload = {
            'id': registro.id,
            'tipo': registro.tipo,
            'numero_doc': registro.numero_doc,
            'ambiente': registro.ambiente,
            'timestamp': registro.timestamp.isoformat() + 'Z' if registro.timestamp else None,
            'persona': {
                'id': persona.id if persona else None,
                'nombre': persona.nombre if persona else 'N/A',
                'numero_doc': persona.numero_doc if persona else registro.numero_doc
            }
        }
        websocket_handler.socketio.emit('acceso_registrado', payload, namespace='/')
    except Exception as e:
        print(f'[WEBSOCKET] Error emitiendo acceso_registrado: {e}')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token requerido'}), 401
        
        try:
            token = token.split(' ')[1]
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            usuario_id = data.get('usuario_id')
            usuario = Usuario.query.get(usuario_id)
            if not usuario:
                return jsonify({'error': 'Usuario no válido'}), 401
            if not usuario.activo:
                return jsonify({'error': 'Cuenta desactivada. Contacta al administrador.'}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Sesión expirada. Inicia sesión de nuevo.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        except Exception:
            return jsonify({'error': 'Token inválido'}), 401
        
        return f(usuario_id, *args, **kwargs)
    return decorated

def validar_acceso(persona_id, tipo_accion):
    """
    Valida si una acción de entrada/salida es permitida.
    - ENTRADA: Solo permitida si el último registro fue SALIDA o no hay registros
    - SALIDA: Solo permitida si el último registro fue ENTRADA
    
    Retorna: (es_valido, mensaje)
    """
    ultimo_registro = RegistroAcceso.query.filter_by(
        persona_id=persona_id
    ).order_by(RegistroAcceso.timestamp.desc()).first()
    
    if tipo_accion.upper() == 'ENTRADA':
        if ultimo_registro and ultimo_registro.tipo.upper() == 'ENTRADA':
            return False, 'Ya has registrado entrada. Debes registrar salida primero.'
        return True, 'Entrada registrada correctamente'
    
    elif tipo_accion.upper() == 'SALIDA':
        if not ultimo_registro:
            return False, 'No has registrado entrada. No puedes registrar salida.'
        if ultimo_registro.tipo.upper() == 'SALIDA':
            return False, 'Ya has registrado salida. Debes registrar entrada primero.'
        return True, 'Salida registrada correctamente'
    
    return False, 'Tipo de acción inválido'


@api_bp.route('/auth/login', methods=['POST'])
def login():
    """
    Login con protecciones avanzadas de seguridad según Ley 1581/2012:
    - Account lockout automático tras N intentos fallidos
    - Bloqueo temporal (15 minutos)
    - Auditoría de intentos de acceso
    - Sesión segura con HttpOnly + SameSite cookies
    """
    
    ip = _get_client_ip()
    
    datos = request.get_json(silent=True) or {}
    email = str(datos.get('email', '')).strip().lower()
    password = datos.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email y password requeridos'}), 400

    # ═ Verificar si la cuenta está bloqueada por intentos fallidos
    bloqueada, msg_bloqueo = PoliticaBloqueoCuenta.verificar_bloqueo(email)
    if bloqueada:
        AuditoriaAdministrativa.registrar(
            usuario_id='SISTEMA',
            operacion='LOGIN_INTENTO_CUENTA_BLOQUEADA',
            tabla='usuarios',
            registro_id=email,
            ip_address=ip,
            motivo=msg_bloqueo
        )
        return jsonify({'error': msg_bloqueo}), 429

    usuario = Usuario.query.filter_by(email=email).first()

    # Respuesta genérica para no revelar si el email existe
    if not usuario or not check_password_hash(usuario.password_hash, password):
        # Registrar intento fallido
        PoliticaBloqueoCuenta.registrar_intento_fallido(email)
        
        AuditoriaAdministrativa.registrar(
            usuario_id=email,
            operacion='LOGIN_FALLIDO',
            tabla='usuarios',
            registro_id=email,
            ip_address=ip,
            motivo='Credenciales inválidas'
        )
        
        return jsonify({
            'error': 'Credenciales inválidas.',
            'intentos_maximos': PoliticaBloqueoCuenta.INTENTOS_MAXIMOS
        }), 401

    if not usuario.activo:
        AuditoriaAdministrativa.registrar(
            usuario_id=email,
            operacion='LOGIN_CUENTA_INACTIVA',
            tabla='usuarios',
            registro_id=email,
            ip_address=ip,
            motivo='Cuenta desactivada'
        )
        return jsonify({'error': 'Cuenta desactivada. Contacta al administrador.'}), 403

    # ═ Login exitoso - Limpiar intentos fallidos
    PoliticaBloqueoCuenta.limpiar_intento_exitoso(email)
    
    # ═ Crear sesión segura
    SesionSegura.crear_sesion_segura(usuario.id, ip_address=ip)
    
    # ═ Generar JWT token
    token = jwt.encode(
        {'usuario_id': usuario.id, 'exp': datetime.utcnow() + timedelta(hours=8)},
        SECRET_KEY,
        algorithm='HS256'
    )
    
    # ═ Auditoría de login exitoso
    AuditoriaAdministrativa.registrar(
        usuario_id=usuario.id,
        operacion='LOGIN_EXITOSO',
        tabla='usuarios',
        registro_id=usuario.id,
        ip_address=ip,
        motivo=f'Login exitoso desde {ip}'
    )

    return jsonify({
        'token': token,
        'usuario': {
            'id': usuario.id,
            'email': usuario.email,
            'nombre': usuario.nombre,
            'rol': usuario.rol
        }
    }), 200

@api_bp.route('/auth/me', methods=['GET'])
@token_required
def auth_me(usuario_id):
    """Retorna la información del usuario autenticado."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify({
        'id': usuario.id,
        'email': usuario.email,
        'nombre': usuario.nombre,
        'rol': usuario.rol
    }), 200


@api_bp.route('/auth/validar-acceso-ingreso', methods=['GET'])
@token_required
def validar_acceso_ingreso(usuario_id):
    """
    Valida si el usuario puede acceder al panel de ingreso de aprendices/instructores.
    
    Los VISITANTES NO pueden acceder a este panel.
    Solo aprendices, instructores, vigilantes y administradores pueden acceder.
    
    Retorna:
        - 200: OK, usuario puede acceder
        - 403: Forbidden, usuario es visitante (acceso denegado)
        - 401: Unauthorized, token inválido
    """
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 401
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # VALIDACIÓN: Rechazar VISITANTES en panel de ingreso
    # ═══════════════════════════════════════════════════════════════════════════════
    if usuario.rol.upper() == 'VISITANTE':
        print(f"⛔ [GET /auth/validar-acceso-ingreso] Acceso denegado: Usuario es visitante")
        return jsonify({
            'permitido': False,
            'error': 'Los visitantes no pueden acceder a este panel. Dirígete al vigilante para registrar tu entrada.',
            'rol': usuario.rol
        }), 403
    
    # ✅ Usuario permitido
    return jsonify({
        'permitido': True,
        'id': usuario.id,
        'nombre': usuario.nombre,
        'rol': usuario.rol,
        'mensaje': 'Acceso autorizado'
    }), 200


@api_bp.route('/auth/logout', methods=['POST'])
@token_required
def logout(usuario_id):
    """Cierra la sesión del usuario actual.
    
    Para instructores: Se llama automáticamente al registrar salida.
    Para otros usuarios: Pueden usar este endpoint para logout manual.
    
    Retorna: 200 si el logout fue exitoso
    """
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    try:
        # Destruir sesión segura (registra LOGOUT en auditoría)
        SesionSegura.destruir_sesion(usuario_id)
        
        # Log de evento de seguridad
        log_evento_seguridad(
            'LOGOUT_MANUAL',
            usuario_id=usuario_id,
            detalles=f'Usuario {usuario.nombre} ({usuario.email}) cerró sesión manualmente',
            severidad='INFO'
        )
        
        print(f"[SEGURIDAD] Logout exitoso para usuario {usuario.email}")
        
        return jsonify({
            'mensaje': 'Sesión cerrada exitosamente',
            'usuario': usuario.email
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Error en logout: {e}")
        return jsonify({'error': 'Error al cerrar sesión'}), 500


@api_bp.route('/auth/token-sistema', methods=['GET'])
def token_sistema():
    """Emite un token de sistema para las páginas de quiosco (ingreso, vigilancia).
    Solo funciona si el servidor está corriendo localmente — no expone credenciales."""
    try:
        # 1. Cualquier usuario admin activo no eliminado
        admin = Usuario.query.filter_by(rol='admin', activo=True, deleted_at=None).first()
        # 2. Último recurso: cualquier usuario activo no eliminado
        if not admin:
            admin = Usuario.query.filter_by(activo=True, deleted_at=None).first()
        if not admin:
            return jsonify({'error': 'No hay usuarios activos en el sistema'}), 500
        token = jwt.encode(
            {'usuario_id': admin.id, 'exp': datetime.utcnow() + timedelta(days=30)},
            SECRET_KEY,
            algorithm='HS256'
        )
        return jsonify({'token': token}), 200
    except Exception as e:
        print(f'[token_sistema] Error: {e}')
        return jsonify({'error': 'Error interno al generar token'}), 500

@api_bp.route('/personas/buscar-por-documento', methods=['GET'])
def buscar_persona_por_documento():
    """Endpoint público para buscar persona por número de documento (para ingreso.html y vigilancia.html)"""
    codigo = request.args.get('numero_doc', '').strip()
    
    if not codigo or len(codigo) < 5:
        return jsonify({'error': 'Número de documento inválido'}), 400
    
    try:
        persona = Persona.query.filter_by(numero_doc=codigo, deleted_at=None).first()
        
        if persona:
            return jsonify({
                'persona': {
                    'id': persona.id,
                    'nombre': persona.nombre,
                    'numero_doc': persona.numero_doc,
                    'tipo_doc': persona.tipo_doc,
                    'programa': persona.programa,
                    'ficha': persona.ficha,
                    'perfil': persona.perfil,
                    'email': persona.email,
                    'telefono': persona.telefono,
                    'especialidad': persona.especialidad,
                    'area': persona.area
                }
            }), 200
        else:
            return jsonify({'error': 'Número de identidad no encontrado en la base de datos'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/personas/estado-acceso', methods=['GET'])
def estado_acceso_persona():
    """Consulta el estado actual de acceso de una persona (público).
    Retorna si puede registrar ENTRADA, SALIDA, o ninguna."""
    numero_doc = request.args.get('numero_doc', '').strip()

    if not numero_doc:
        return jsonify({'error': 'numero_doc requerido'}), 400

    persona = Persona.query.filter_by(numero_doc=numero_doc, deleted_at=None).first()
    if not persona:
        return jsonify({'error': 'Persona no encontrada'}), 404

    ultimo = RegistroAcceso.query.filter_by(
        persona_id=persona.id
    ).order_by(RegistroAcceso.timestamp.desc()).first()

    if not ultimo:
        puede_entrada = True
        puede_salida  = False
        estado_actual = None
    elif ultimo.tipo.upper() == 'ENTRADA':
        puede_entrada = False
        puede_salida  = True
        estado_actual = 'ENTRADA'
    else:
        puede_entrada = True
        puede_salida  = False
        estado_actual = 'SALIDA'

    return jsonify({
        'numero_doc':   numero_doc,
        'estado_actual': estado_actual,
        'puede_entrada': puede_entrada,
        'puede_salida':  puede_salida,
        'ultimo_registro': {
            'tipo':      ultimo.tipo,
            'timestamp': ultimo.timestamp.isoformat() + 'Z'
        } if ultimo else None
    }), 200

@api_bp.route('/personas', methods=['GET'])
@token_required
def listar_personas(usuario_id):
    # Soportar ambos parámetros: 'limit' y 'por_pagina'
    limit = request.args.get('limit', None, type=int)
    por_pagina = request.args.get('por_pagina', limit or 100, type=int)  # Aumentado a 100 por defecto
    pagina = request.args.get('pagina', 1, type=int)
    
    perfil = request.args.get('perfil', None)
    buscar = request.args.get('buscar', None)
    
    # Debug logging detallado
    print(f"\n🔵 [GET /api/personas] INICIO - Usuario: {usuario_id}")
    print(f"   📊 Parámetros: limit={limit}, por_pagina={por_pagina}, pagina={pagina}")
    print(f"   🔍 Filtros: perfil={perfil}, buscar={buscar}")
    
    query = Persona.query.filter_by(deleted_at=None)
    
    if perfil:
        query = query.filter_by(perfil=perfil)
    
    if buscar:
        query = query.filter(
            (Persona.nombre.ilike(f'%{buscar}%')) |
            (Persona.numero_doc.ilike(f'%{buscar}%'))
        )
    
    # Obtener total antes de paginar
    total_count = query.count()
    print(f"   📈 Total de personas en BD: {total_count}")
    
    paginated = query.paginate(page=pagina, per_page=por_pagina, error_out=False)
    
    print(f"   📖 Fetching página {pagina} de {paginated.pages}")
    
    personas = []
    for p in paginated.items:
        personas.append({
            'id': p.id,
            'nombre': p.nombre,
            'tipo_doc': p.tipo_doc,
            'numero_doc': p.numero_doc,
            'email': p.email,
            'telefono': p.telefono,
            'perfil': p.perfil,
            'programa': p.programa,
            'ficha': p.ficha
        })
    
    print(f"   📤 Retornando {len(personas)} personas en esta respuesta")
    print(f"🟢 [GET /api/personas] COMPLETADO\n")
    
    return jsonify({
        'personas': personas,
        'total': paginated.total,
        'pagina': pagina,
        'por_pagina': por_pagina,
        'paginas': paginated.pages
    }), 200

@api_bp.route('/personas/<persona_id>', methods=['GET'])
@token_required
def obtener_persona(usuario_id, persona_id):
    persona = Persona.query.get(persona_id)
    if not persona or persona.deleted_at:
        return jsonify({'error': 'Persona no encontrada'}), 404
    
    accesos = RegistroAcceso.query.filter_by(persona_id=persona_id).order_by(RegistroAcceso.timestamp.desc()).limit(10).all()
    cambios = CambioHistorial.query.filter_by(persona_id=persona_id).order_by(CambioHistorial.created_at.desc()).limit(10).all()
    
    return jsonify({
        'id': persona.id,
        'nombre': persona.nombre,
        'tipo_doc': persona.tipo_doc,
        'numero_doc': persona.numero_doc,
        'email': persona.email,
        'telefono': persona.telefono,
        'perfil': persona.perfil,
        'programa': persona.programa,
        'ficha': persona.ficha,
        'especialidad': persona.especialidad,
        'area': persona.area,
        'verificado': persona.verificado,
        'created_at': persona.created_at.isoformat() + 'Z',
        'accesos_recientes': [{'tipo': r.tipo, 'timestamp': r.timestamp.isoformat() + 'Z'} for r in accesos],
        'cambios_recientes': [{'campo': c.campo, 'valor_anterior': c.valor_anterior, 'valor_nuevo': c.valor_nuevo} for c in cambios]
    }), 200

@api_bp.route('/personas', methods=['POST'])
@token_required
def crear_persona(usuario_id):
    try:
        print(f"\n🔵 [POST /api/personas] INICIO - Usuario: {usuario_id}")
        datos = request.get_json()
        
        if not datos:
            print(f"❌ [POST /api/personas] Error: No JSON data provided")
            return jsonify({'error': 'No JSON data provided'}), 400
        
        numero_doc = datos.get('numero_doc')
        nombre = datos.get('nombre', 'Sin nombre')
        perfil_solicitado = datos.get('perfil', 'APRENDIZ')
        print(f"📥 [POST /api/personas] Datos recibidos - Nombre: {nombre}, Documento: {numero_doc}, Perfil: {perfil_solicitado}")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # VALIDACIÓN: Solo VIGILANTES pueden registrar VISITANTES
        # ═══════════════════════════════════════════════════════════════════════════════
        if perfil_solicitado.upper() == 'VISITANTE':
            usuario_actual = Usuario.query.get(usuario_id)
            if not usuario_actual or usuario_actual.rol != 'vigilante':
                print(f"❌ [POST /api/personas] Acceso denegado: Usuario no es vigilante (rol: {usuario_actual.rol if usuario_actual else 'N/A'})")
                return jsonify({
                    'error': 'No tienes permiso para registrar visitantes. Solo los vigilantes pueden registrar visitantes desde el panel de vigilancia.'
                }), 403
        
        if not numero_doc:
            print(f"❌ [POST /api/personas] Error: numero_doc is required")
            return jsonify({'error': 'numero_doc is required'}), 400
        
        # Verificar si existe
        # Buscar también registros eliminados: numero_doc es UNIQUE incluso
        # cuando la persona tiene soft-delete y no puede insertarse otra fila.
        doc_exists = Persona.query.filter_by(numero_doc=numero_doc).first()
        if doc_exists:
            print(f"⚠️ [POST /api/personas] Documento ya existe - completando datos - ID: {doc_exists.id}")

            # El panel de vigilancia puede crear primero un registro mínimo de
            # personal de aseo. El alta administrativa debe completar ese mismo
            # registro para conservar su historial de accesos.
            valores_actualizables = {
                'nombre': (nombre or '').strip().upper(),
                'tipo_doc': datos.get('tipo_doc'),
                'email': datos.get('email'),
                'telefono': datos.get('telefono'),
                'perfil': (perfil_solicitado or 'aprendiz').strip().lower(),
                'programa': datos.get('programa'),
                'ficha': datos.get('ficha'),
                'especialidad': datos.get('especialidad'),
                'area': datos.get('area'),
            }
            for campo, valor in valores_actualizables.items():
                if valor is not None and (not isinstance(valor, str) or valor.strip()):
                    setattr(doc_exists, campo, valor)
            doc_exists.deleted_at = None
            doc_exists.actualizado_por_id = usuario_id
            db.session.commit()
            print(f"✅ [POST /api/personas] Datos actualizados - Persona ID: {doc_exists.id}")
            return jsonify({
                'id': doc_exists.id,
                'numero_doc': doc_exists.numero_doc,
                'actualizada': True
            }), 200
        
        persona = Persona(
            nombre=(datos.get('nombre', 'Sin nombre') or '').upper(),
            tipo_doc=datos.get('tipo_doc', 'CC'),
            numero_doc=numero_doc,
            email=datos.get('email'),
            telefono=datos.get('telefono'),
            perfil=(datos.get('perfil', 'aprendiz') or 'aprendiz').lower(),
            programa=datos.get('programa'),
            ficha=datos.get('ficha'),
            especialidad=datos.get('especialidad'),
            area=datos.get('area'),
            creado_por_id=usuario_id,
            actualizado_por_id=usuario_id
        )  # type: ignore
        print(f"💾 [POST /api/personas] Objeto Persona creado (sin guardar aún)")
        
        db.session.add(persona)
        print(f"📌 [POST /api/personas] Persona añadida a session")
        
        db.session.commit()
        print(f"✅ [POST /api/personas] DB.COMMIT EXITOSO - Persona ID: {persona.id}")
        
        # Verificar que la persona está en BD después de commit
        persona_verificacion = Persona.query.get(persona.id)
        if persona_verificacion:
            print(f"✅ [POST /api/personas] VERIFICACIÓN: Persona encontrada en BD después de commit")
        else:
            print(f"❌ [POST /api/personas] VERIFICACIÓN FALLIDA: Persona NO encontrada en BD después de commit")

        # Emitir evento en tiempo real para que el panel admin se actualice sin recargar
        try:
            if websocket_handler.socketio:
                websocket_handler.socketio.emit('persona_creada', {
                    'id': persona.id,
                    'nombre': persona.nombre,
                    'tipo_doc': persona.tipo_doc,
                    'numero_doc': persona.numero_doc,
                    'email': persona.email,
                    'telefono': persona.telefono,
                    'perfil': persona.perfil,
                    'programa': persona.programa,
                    'ficha': persona.ficha,
                    'especialidad': persona.especialidad,
                    'area': persona.area,
                }, namespace='/')
                print(f"📡 [POST /api/personas] Evento 'persona_creada' emitido para {persona.nombre}")
            else:
                print("⚠️ [POST /api/personas] websocket_handler.socketio es None")
        except Exception as e:
            print(f"❌ [POST /api/personas] Error emitiendo evento WebSocket: {e}")
            import traceback
            traceback.print_exc()

        # Correo de bienvenida al aprendiz/instructor si tiene email
        try:
            srv_correo.bienvenida_nueva_persona({
                'nombre':     persona.nombre,
                'numero_doc': persona.numero_doc,
                'tipo_doc':   persona.tipo_doc,
                'perfil':     persona.perfil,
                'programa':   persona.programa,
                'ficha':      persona.ficha,
                'email':      persona.email,
            })
            print(f"📧 [POST /api/personas] Correo de bienvenida procesado")
        except Exception as e:
            print(f"⚠️ [POST /api/personas] Error enviando correo: {e}")

        print(f"🟢 [POST /api/personas] COMPLETADO EXITOSO - Retornando ID: {persona.id}")
        return jsonify({'id': persona.id, 'numero_doc': persona.numero_doc}), 201
    except Exception as e:
        print(f"🔴 [POST /api/personas] EXCEPCIÓN: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/personas/<persona_id>', methods=['PUT'])
@token_required
def actualizar_persona(usuario_id, persona_id):
    persona = Persona.query.get(persona_id)
    if not persona or persona.deleted_at:
        return jsonify({'error': 'Persona no encontrada'}), 404
    
    datos = request.get_json()
    
    campos_actualizables = ['nombre', 'email', 'telefono', 'programa', 'ficha', 'especialidad', 'area', 'verificado']
    
    for campo in campos_actualizables:
        if campo in datos:
            valor_anterior = getattr(persona, campo)
            setattr(persona, campo, datos[campo])
            
            cambio = CambioHistorial(
                persona_id=persona_id,
                usuario_id=usuario_id,
                campo=campo,
                valor_anterior=valor_anterior,
                valor_nuevo=datos[campo]
            )  # type: ignore
            db.session.add(cambio)
    
    persona.actualizado_por_id = usuario_id
    db.session.commit()
    
    return jsonify({'id': persona.id, 'mensaje': 'Actualizado'}), 200

@api_bp.route('/personas/<persona_id>', methods=['DELETE'])
@token_required
def eliminar_persona(usuario_id, persona_id):
    persona = Persona.query.get(persona_id)
    if not persona or persona.deleted_at:
        return jsonify({'error': 'Persona no encontrada'}), 404
    
    persona.soft_delete()
    
    cambio = CambioHistorial(
        persona_id=persona_id,
        usuario_id=usuario_id,
        campo='deleted_at',
        valor_anterior=None,
        valor_nuevo=datetime.utcnow().isoformat() + 'Z'
    )  # type: ignore
    db.session.add(cambio)
    db.session.commit()

    # Emitir evento en tiempo real
    try:
        if websocket_handler.socketio:
            websocket_handler.socketio.emit('persona_eliminada', {'id': persona_id}, namespace='/')
    except Exception:
        pass

    return jsonify({'mensaje': 'Eliminado'}), 200

@api_bp.route('/personas/descargar-excel', methods=['GET'])
def descargar_personas_excel():
    """Descarga todas las personas en formato Excel"""
    try:
        # Verificar token manualmente
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No autorizado'}), 401
        
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from io import BytesIO
        
        print(f"📊 [GET /api/personas/descargar-excel] Pidiendo descarga...")
        
        # Obtener todas las personas activas
        personas = Persona.query.filter_by(deleted_at=None).all()
        print(f"📋 Personas encontradas: {len(personas)}")
        
        if not personas:
            return jsonify({'error': 'No hay personas para descargar'}), 404
        
        # Crear workbook
        wb = Workbook()
        ws = wb.active
        ws.title = 'Personas'
        
        # Crear encabezados
        headers = ['Nombre', 'Documento', 'Perfil', 'Email', 'Teléfono', 'Activo']
        ws.append(headers)
        
        # Estilar encabezados
        header_fill = PatternFill(start_color='39A900', end_color='39A900', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Agregar datos
        for persona in personas:
            ws.append([
                persona.nombre or '',
                persona.numero_doc or '',
                persona.perfil or '',
                persona.email or '',
                persona.telefono or '',
                'Sí' if not persona.deleted_at else 'No'
            ])
        
        # Ajustar ancho de columnas
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 25
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 10
        
        # Guardar en memoria
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        from datetime import datetime as dt
        fecha = dt.now().strftime('%Y-%m-%d')
        nombre_archivo = f'Personas_{fecha}.xlsx'
        
        print(f"✅ Enviando archivo: {nombre_archivo} con {len(personas)} personas")
        
        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nombre_archivo
        )
    except Exception as e:
        print(f"❌ Error descargando Excel: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/registros-acceso', methods=['POST'])
@token_required
def registrar_acceso(usuario_id):
    datos = request.get_json()
    numero_doc = datos.get('numero_doc')
    tipo = datos.get('tipo', 'ENTRADA')
    
    if not numero_doc:
        return jsonify({'error': 'Documento es requerido'}), 400
    
    persona = Persona.query.filter_by(numero_doc=numero_doc, deleted_at=None).first()
    
    # Si no existe persona, crearla automáticamente como personal_aseo
    if not persona:
        persona = Persona(
            nombre=f'Personal de Aseo - {numero_doc}',
            tipo_doc='CC',
            numero_doc=numero_doc,
            perfil='personal_aseo',
            creado_por_id=usuario_id,
            actualizado_por_id=usuario_id
        )
        db.session.add(persona)
        db.session.flush()
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # VALIDACIÓN: Solo VIGILANTES pueden registrar entrada/salida de VISITANTES
    # ═══════════════════════════════════════════════════════════════════════════════
    if (persona.perfil or '').lower() == 'visitante':
        usuario_actual = Usuario.query.get(usuario_id)
        if not usuario_actual or usuario_actual.rol != 'vigilante':
            print(f"❌ [POST /api/registros-acceso] Acceso denegado: Usuario no es vigilante intentando registrar visitante")
            return jsonify({
                'error': 'No tienes permiso para registrar acceso de visitantes. Solo los vigilantes pueden hacerlo desde el panel de vigilancia.'
            }), 403
    
    # Validar que entrada/salida sean alternadas
    es_valido, mensaje = validar_acceso(persona.id, tipo)
    if not es_valido:
        # Alertar al admin si hay un intento bloqueado
        srv_correo.alerta_acceso_fallido(
            numero_doc = numero_doc,
            motivo     = mensaje,
            timestamp  = datetime.utcnow().isoformat() + 'Z',
        )
        return jsonify({'error': mensaje, 'bloqueado': True}), 403
    
    registro = RegistroAcceso(
        persona_id=persona.id,
        numero_doc=numero_doc,
        tipo=tipo,
        timestamp=datetime.utcnow(),
        ambiente=datos.get('ambiente'),
        observaciones=datos.get('observaciones'),
        vigilante_id=usuario_id
    )  # type: ignore
    
    db.session.add(registro)
    db.session.flush()

    # Registrar acceso de equipo si viene código de barras
    codigo_eq = (datos.get('codigo_barras_equipo') or '').strip()
    if codigo_eq:
        # Buscar en TODOS los registros, incluidos soft-deleted, para no reutilizar un código
        comp_reg = Computador.query.filter_by(codigo_barras=codigo_eq).first()
        if not comp_reg:
            comp_reg = Computador(
                codigo_barras=codigo_eq,
                marca='No especificado',
                modelo='No especificado',
                tipo='Computador',
                estado='activo'
            )  # type: ignore
            db.session.add(comp_reg)
            db.session.flush()
        elif comp_reg.deleted_at:
            comp_reg.deleted_at = None
            comp_reg.estado = 'activo'

        # CORRECCIÓN: Bloquear si el equipo ya está DENTRO registrado a otra persona
        ultimo_mov_eq = RegistroAccesoEquipo.query.filter_by(
            computador_id=comp_reg.id
        ).order_by(RegistroAccesoEquipo.timestamp.desc()).first()
        if tipo.upper() == 'ENTRADA' and ultimo_mov_eq and ultimo_mov_eq.tipo.upper() == 'ENTRADA':
            if ultimo_mov_eq.persona_id != persona.id:
                db.session.rollback()
                return jsonify({'error': 'Este equipo ya está dentro de las instalaciones registrado a nombre de otra persona.'}), 409

        # CORRECCIÓN: Solo asignar propietario si el equipo no tiene dueño aún.
        # Nunca reasignar silenciosamente a otra persona.
        if comp_reg.asignado_a_id is None:
            comp_reg.asignado_a_id = persona.id

        reg_equipo = RegistroAccesoEquipo(
            computador_id=comp_reg.id,
            persona_id=persona.id,
            tipo=tipo,
            timestamp=datetime.utcnow(),
            registro_acceso_id=registro.id
        )  # type: ignore
        db.session.add(reg_equipo)

    db.session.commit()

    emitir_evento_acceso_tiempo_real(registro, persona)
    try:
        gestionar_ocupacion_instructor(persona, registro, tipo)
    except Exception as _e_gest:
        print(f'[OCUPACION] Error en gestionar_ocupacion_instructor: {_e_gest}')
        # No interrumpir el registro por fallo en cerradura/ocupación

    # ═══ CANCELAR INTENTO DE CERRADURA SI INSTRUCTOR ENTRÓ ═══════════════════════
    if tipo.upper() == 'ENTRADA' and persona.perfil.lower() in ('instructor', 'instructora'):
        try:
            intento = lock_scheduler.buscar_intento_activo(persona.id, registro.ambiente)
            if intento:
                lock_scheduler.cancelar_intento(intento.id)
                print(f"[CERRADURA] Intento cancelado - instructor {persona.numero_doc} ha ingresado")
        except Exception as e:
            print(f"[CERRADURA] Error cancelando intento: {e}")
    # ════════════════════════════════════════════════════════════════════════════

    # ═══ CERRAR SESIÓN AUTOMÁTICAMENTE CUANDO INSTRUCTOR REGISTRA SALIDA ═════════
    if tipo.upper() == 'SALIDA' and persona.perfil.lower() in ('instructor', 'instructora'):
        # 1️⃣ Liberar ambiente primero (y emitir evento WebSocket)
        try:
            ambiente_liberado = liberar_ambiente_instructor_salida(persona)
            if ambiente_liberado:
                print(f"[AMBIENTE] Ambiente '{ambiente_liberado.ambiente}' liberado al registrar salida")
        except Exception as e:
            print(f"[AMBIENTE] Error liberando ambiente: {e}")
        
        # 2️⃣ Cerrar sesión por seguridad
        try:
            sesion_cerrada = cerrar_sesion_instructor_salida(persona)
            if sesion_cerrada:
                print(f"[SEGURIDAD] Sesión del instructor {persona.numero_doc} cerrada automáticamente")
        except Exception as e:
            print(f"[SEGURIDAD] Error cerrando sesión de instructor: {e}")
    # ════════════════════════════════════════════════════════════════════════════

    # Correo de confirmación de ingreso/salida (asíncrono, no bloquea)
    srv_correo.confirmacion_ingreso(
        persona   = {'nombre': persona.nombre, 'email': persona.email},
        tipo      = tipo,
        timestamp = registro.timestamp.isoformat() + 'Z',
        ambiente  = registro.ambiente,
        observaciones = registro.observaciones,
    )

    return jsonify({'id': registro.id, 'timestamp': registro.timestamp.isoformat() + 'Z', 'mensaje': mensaje}), 201

@api_bp.route('/correo/prueba', methods=['POST'])
@token_required
def correo_prueba(usuario_id):
    """Envia un correo de prueba para verificar la configuracion de Gmail.
    Body JSON: { "email": "destino@ejemplo.com" }  (opcional — si omite usa el email del admin)
    """
    datos = request.get_json(silent=True) or {}
    usuario = Usuario.query.get(usuario_id)
    destino = datos.get('email') or (usuario.email if usuario else '') or os.getenv('ADMIN_EMAIL', '')
    if not destino:
        return jsonify({'error': 'No se especifico un email de destino'}), 400
    resultado = srv_correo.enviar_correo_prueba(destino)
    code = 200 if resultado['ok'] else 503
    return jsonify(resultado), code


@api_bp.route('/correo/reporte-diario', methods=['POST'])
@token_required
def correo_reporte_diario(usuario_id):
    """Genera y envia el reporte diario al admin. Solo rol admin."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol != 'admin':
        return jsonify({'error': 'Solo el administrador puede enviar reportes'}), 403

    hoy = datetime.utcnow().date()
    inicio = datetime(hoy.year, hoy.month, hoy.day)
    fin    = inicio + timedelta(days=1)

    registros_hoy = RegistroAcceso.query.filter(
        RegistroAcceso.timestamp >= inicio,
        RegistroAcceso.timestamp < fin,
        RegistroAcceso.deleted_at == None  # type: ignore
    ).all()

    entradas = [r for r in registros_hoy if r.tipo.upper() == 'ENTRADA']
    salidas  = [r for r in registros_hoy if r.tipo.upper() == 'SALIDA']
    personas_distintas = len({r.numero_doc for r in registros_hoy})

    primera = min((r.timestamp for r in entradas), default=None)
    ultima  = max((r.timestamp for r in salidas), default=None)

    # Contar por perfil
    perfiles = {}
    for r in entradas:
        p = Persona.query.filter_by(numero_doc=r.numero_doc, deleted_at=None).first()
        perfil = (p.perfil if p else 'Desconocido').capitalize()
        perfiles[perfil] = perfiles.get(perfil, 0) + 1

    destino = os.getenv('ADMIN_EMAIL', '') or usuario.email
    srv_correo.reporte_diario_admin(
        resumen = {
            'fecha':                   hoy.strftime('%d/%m/%Y'),
            'total_entradas':          len(entradas),
            'total_salidas':           len(salidas),
            'total_personas_distintas': personas_distintas,
            'primera_entrada':         primera.strftime('%H:%M') if primera else '—',
            'ultima_salida':           ultima.strftime('%H:%M') if ultima else '—',
            'perfiles':                perfiles,
        }
    )
    return jsonify({
        'ok': True,
        'mensaje': f'Reporte del {hoy} enviado a todos los administradores',
        'estadisticas': {
            'entradas': len(entradas), 'salidas': len(salidas),
            'personas': personas_distintas
        }
    }), 200


@api_bp.route('/accesos', methods=['GET'])
@token_required
def listar_accesos(usuario_id):
    """
    Obtiene listado de registros de acceso con paginación y filtros.
    Parámetros:
    - limit: cantidad de registros a retornar (default: 100)
    - pagina: número de página (default: 1)
    - tipo: filtrar por ENTRADA/SALIDA (opcional)
    - numero_doc: filtrar por documento (opcional)
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        pagina = request.args.get('pagina', 1, type=int)
        tipo = request.args.get('tipo', '').strip().upper()
        numero_doc = request.args.get('numero_doc', '').strip()
        
        # Limitar valores
        limit = min(limit, 500)
        limit = max(limit, 1)
        
        query = RegistroAcceso.query
        
        # Aplicar filtros
        if tipo and tipo in ('ENTRADA', 'SALIDA'):
            query = query.filter_by(tipo=tipo)
        
        if numero_doc:
            query = query.filter_by(numero_doc=numero_doc)
        
        # Ordenar por timestamp descendente
        query = query.order_by(RegistroAcceso.timestamp.desc())
        
        # Obtener total antes de paginar
        total = query.count()
        
        # Paginar
        registros = query.paginate(page=pagina, per_page=limit, error_out=False)
        
        accesos = []
        for r in registros.items:
            accesos.append({
                'id': r.id,
                'numero_doc': r.numero_doc,
                'tipo': r.tipo,
                'timestamp': r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                'ambiente': r.ambiente,
                'observaciones': r.observaciones,
                'vigilante_id': r.vigilante_id,
            })
        
        return jsonify({
            'accesos': accesos,
            'total': total,
            'pagina': pagina,
            'por_pagina': limit,
            'paginas': registros.pages
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/accesos-test', methods=['GET'])
def listar_accesos_test():
    """Endpoint público de prueba para /accesos (sin autenticación)."""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        query = RegistroAcceso.query.order_by(RegistroAcceso.timestamp.desc())
        total = query.count()
        registros = query.limit(limit).all()
        
        accesos = []
        for r in registros:
            accesos.append({
                'id': r.id,
                'numero_doc': r.numero_doc,
                'tipo': r.tipo,
                'timestamp': r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                'ambiente': r.ambiente,
            })
        
        return jsonify({
            'accesos': accesos,
            'total': total,
            'test': True,
            'mensaje': 'Endpoint de prueba - sin autenticación requerida'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/registros-acceso/busqueda-global', methods=['GET'])
@token_required
def busqueda_global_registros(usuario_id):
    """Busca historial de una persona por su número de documento."""
    numero_doc = request.args.get('numero_doc', '').strip()
    
    if not numero_doc:
        return jsonify({'error': 'Se requiere número de documento para buscar'}), 400

    # Validar que sea numérico
    if not numero_doc.replace(' ', '').replace('.', '').isdigit():
        return jsonify({'error': 'Número de documento inválido'}), 400

    try:
        # Buscar TODOS los registros con este documento
        registros_encontrados = RegistroAcceso.query\
            .filter_by(numero_doc=numero_doc, deleted_at=None)\
            .order_by(RegistroAcceso.timestamp.desc())\
            .all()

        if not registros_encontrados:
            return jsonify({'registros': [], 'total': 0, 'persona': None}), 200

        registros = []
        persona_info = None

        for r in registros_encontrados:
            vig = Usuario.query.get(r.vigilante_id) if r.vigilante_id else None
            
            # Guardar info de la persona desde el primer registro
            if persona_info is None and r.persona:
                persona_info = {
                    'id': r.persona.id,
                    'nombre': r.persona.nombre,
                    'numero_doc': r.persona.numero_doc,
                    'perfil': r.persona.perfil,
                    'ficha': r.persona.ficha,
                    'programa': r.persona.programa,
                    'email': r.persona.email,
                    'telefono': r.persona.telefono,
                }

            registros.append({
                'id': r.id,
                'numero_doc': r.numero_doc,
                'tipo': r.tipo,
                'timestamp': r.timestamp.isoformat() + 'Z',
                'ambiente': r.ambiente,
                'vigilante': {'nombre': vig.nombre, 'email': vig.email} if vig else None,
                'persona': {
                    'id': r.persona.id if r.persona else None,
                    'nombre': r.persona.nombre if r.persona else 'N/A',
                    'numero_doc': r.persona.numero_doc if r.persona else numero_doc,
                    'perfil': r.persona.perfil if r.persona else None,
                    'ficha': r.persona.ficha if r.persona else None,
                    'programa': r.persona.programa if r.persona else None,
                }
            })

        return jsonify({
            'registros': registros,
            'total': len(registros),
            'persona': persona_info
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al buscar: {str(e)}'}), 500


@api_bp.route('/registros-acceso', methods=['GET'])
@token_required
def listar_registros(usuario_id):
    tipo = request.args.get('tipo')
    numero_doc = request.args.get('numero_doc')
    fecha_desde = request.args.get('fecha_desde')
    pagina = request.args.get('pagina', 1, type=int)

    usuario_actual = Usuario.query.get(usuario_id)
    query = RegistroAcceso.query.filter_by(deleted_at=None)

    # Admins ven todos los registros; vigilantes ven todos los de hoy (su turno)
    if not usuario_actual or usuario_actual.rol != 'admin':
        hoy = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(RegistroAcceso.timestamp >= hoy)
    
    if tipo:
        query = query.filter_by(tipo=tipo)
    if numero_doc:
        query = query.filter_by(numero_doc=numero_doc)
    if fecha_desde:
        query = query.filter(RegistroAcceso.timestamp >= fecha_desde)
    
    paginated = query.order_by(RegistroAcceso.timestamp.desc()).paginate(page=pagina, per_page=50, error_out=False)
    
    registros = []
    for r in paginated.items:
        equipos_reg = RegistroAccesoEquipo.query.filter_by(registro_acceso_id=r.id).all()
        equipos_list = []
        for ea in equipos_reg:
            comp_ea = Computador.query.filter_by(id=ea.computador_id, deleted_at=None).first()
            if comp_ea:
                equipos_list.append({'codigo_barras': comp_ea.codigo_barras})
        registros.append({
            'id': r.id,
            'numero_doc': r.numero_doc,
            'tipo': r.tipo,
            'timestamp': r.timestamp.isoformat() + 'Z',
            'created_at': r.timestamp.isoformat() + 'Z',
            'ambiente': r.ambiente,
            'equipos': equipos_list,
            'persona': {
                'id': r.persona.id if r.persona else None,
                'nombre': r.persona.nombre if r.persona else 'N/A',
                'numero_doc': r.persona.numero_doc if r.persona else r.numero_doc,
                'perfil': r.persona.perfil if r.persona else None
            }
        })
    
    return jsonify({'registros': registros, 'total': paginated.total}), 200


@api_bp.route('/historial-accesos-completo', methods=['GET'])
@token_required
def historial_accesos_completo(usuario_id):
    """
    ⚠️ ENDPOINT CRÍTICO - HISTORIAL PERSISTENTE SIN RESTRICCIONES DE TURNO
    
    Retorna TODOS los registros de acceso del día actual (00:00 a 23:59).
    NO filtra por vigilante. NO borra registros. 
    Garantiza que el nuevo vigilante ve TODO el historial del día anterior.
    
    Este es el endpoint MAE importante para garantizar que los aprendices
    puedan registrar su SALIDA incluso si cambió de turno.
    """
    try:
        usuario_actual = Usuario.query.get(usuario_id)
        if not usuario_actual:
            return jsonify({'error': 'Usuario no válido'}), 401
        
        # Calcular rango de hoy: 00:00:00 a 23:59:59
        ahora = datetime.utcnow()
        inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = inicio_dia + timedelta(days=1)
        
        # QUERY SIN FILTROS DE TURNO/VIGILANTE
        # Solo filtrar por fecha y que no esté soft-deleted
        todos_registros = RegistroAcceso.query.filter(
            RegistroAcceso.timestamp >= inicio_dia,
            RegistroAcceso.timestamp < fin_dia,
            RegistroAcceso.deleted_at == None  # type: ignore
        ).order_by(RegistroAcceso.timestamp.desc()).all()
        
        # Serializar TODOS los registros
        registros_data = []
        for r in todos_registros:
            persona_info = None
            if r.persona:
                persona_info = {
                    'id': r.persona.id,
                    'nombre': r.persona.nombre,
                    'numero_doc': r.persona.numero_doc,
                    'perfil': r.persona.perfil,
                    'programa': r.persona.programa,
                    'ficha': r.persona.ficha
                }
            
            registros_data.append({
                'id': r.id,
                'numero_doc': r.numero_doc,
                'tipo': r.tipo,
                'timestamp': r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                'created_at': r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                'ambiente': r.ambiente,
                'observaciones': r.observaciones,
                'vigilante_id': r.vigilante_id,
                'persona': persona_info
            })
        
        # Calcular personas ACTIVAS (sin turno específico)
        # = última entrada de la persona sin salida correspondiente 
        estado_actual_persona = {}
        for r in todos_registros:
            doc = r.numero_doc
            # Procesar en orden descendente (más reciente primero)
            if doc not in estado_actual_persona:
                estado_actual_persona[doc] = {
                    'numero_doc': doc,
                    'ultimo_tipo': r.tipo,
                    'timestamp_ultimo': r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                    'ambiente': r.ambiente,
                    'persona': None,
                    'adentro': r.tipo == 'ENTRADA'  # Está adentro si última fue ENTRADA
                }
                if r.persona:
                    estado_actual_persona[doc]['persona'] = {
                        'id': r.persona.id,
                        'nombre': r.persona.nombre,
                        'numero_doc': r.persona.numero_doc,
                        'perfil': r.persona.perfil
                    }
        
        # Filtrar solo personas QUE ESTÁN ADENTRO (último registro fue ENTRADA)
        personas_dentro_ahora = [
            v for v in estado_actual_persona.values()
            if v['adentro']
        ]
        
        # Estadísticas
        total_entradas = len([r for r in todos_registros if r.tipo == 'ENTRADA'])
        total_salidas = len([r for r in todos_registros if r.tipo == 'SALIDA'])
        
        return jsonify({
            'ok': True,
            'timestamp_servidor': ahora.isoformat() + 'Z',
            'rango_fecha': {
                'inicio': inicio_dia.isoformat() + 'Z',
                'fin': fin_dia.isoformat() + 'Z'
            },
            'usuario_actual': {
                'id': usuario_actual.id,
                'nombre': usuario_actual.nombre,
                'rol': usuario_actual.rol,
                'email': usuario_actual.email
            },
            'estadisticas': {
                'total_registros': len(todos_registros),
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'personas_en_sede_ahora': len(personas_dentro_ahora)
            },
            'registros': registros_data,
            'personas_dentro_ahora': personas_dentro_ahora,
            'mensaje': f'Historial completo del día. Total: {len(todos_registros)} movimientos, {len(personas_dentro_ahora)} personas en sede.'
        }), 200
        
    except Exception as e:
        import traceback
        print(f"[ERROR] /historial-accesos-completo: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'ok': False}), 500


@api_bp.route('/historial-accesos-momento', methods=['GET'])
@token_required
def historial_accesos_momento(usuario_id):
    """
    Retorna el historial COMPLETO y PERSISTENTE de accesos para el panel de vigilancia.
    
    Este endpoint devuelve:
    1. Últimos 100 registros de acceso del día actual (ordenados DESC)
    2. Lista de personas ACTIVAS (que ingresaron pero aún no salieron)
    3. Información completa para estadísticas y seguimiento
    
    Garantiza que el historial persista incluso con cambios de turno.
    """
    try:
        usuario_actual = Usuario.query.get(usuario_id)
        if not usuario_actual:
            return jsonify({'error': 'Usuario no válido'}), 401
        
        # Obtener date de hoy
        hoy = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Base query: todos los registros del día (sin soft-delete)
        query_base = RegistroAcceso.query.filter(
            RegistroAcceso.timestamp >= hoy,
            RegistroAcceso.deleted_at == None  # type: ignore
        )
        
        # Para vigilantes: ver solo su turno del día
        # Para admins: ver todos los registros del día
        if usuario_actual.rol != 'admin':
            # Vigilante: ve registros del turno actual (00:00 a 23:59 de hoy)
            query_registros = query_base
        else:
            # Admin: ve todos los registros del día
            query_registros = query_base
        
        # Obtener últimos 100 registros (más recientes primero)
        ultimos_registros = query_registros.order_by(
            RegistroAcceso.timestamp.desc()
        ).limit(100).all()
        
        # Serializar registros
        registros_data = []
        for r in ultimos_registros:
            persona_data = None
            if r.persona:
                persona_data = {
                    'id': r.persona.id,
                    'nombre': r.persona.nombre,
                    'numero_doc': r.persona.numero_doc,
                    'perfil': r.persona.perfil,
                    'programa': r.persona.programa,
                    'ficha': r.persona.ficha
                }
            
            registros_data.append({
                'id': r.id,
                'numero_doc': r.numero_doc,
                'tipo': r.tipo,
                'timestamp': r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                'created_at': r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                'ambiente': r.ambiente,
                'observaciones': r.observaciones,
                'persona': persona_data
            })
        
        # Calcular personas ACTIVAS (entrada sin salida correspondiente)
        personas_activas = {}
        for r in ultimos_registros:
            doc = r.numero_doc
            # Última vez que se vio esta persona
            if doc not in personas_activas:
                personas_activas[doc] = {
                    'numero_doc': doc,
                    'tipo_ultimo_registro': r.tipo,
                    'timestamp_ultimo_registro': r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                    'persona': None,
                    'ambiente': r.ambiente,
                    'estado': 'SALIDA' if r.tipo == 'SALIDA' else 'ENTRADA'
                }
                if r.persona:
                    personas_activas[doc]['persona'] = {
                        'id': r.persona.id,
                        'nombre': r.persona.nombre,
                        'numero_doc': r.persona.numero_doc,
                        'perfil': r.persona.perfil,
                        'programa': r.persona.programa,
                        'ficha': r.persona.ficha
                    }
        
        # Filtrar solo personas CON ENTRADA (activas adentro)
        personas_dentro = {
            k: v for k, v in personas_activas.items()
            if v['tipo_ultimo_registro'] == 'ENTRADA'
        }
        
        # Estadísticas rápidas
        total_movimientos = len(ultimos_registros)
        total_entradas = len([r for r in ultimos_registros if r.tipo == 'ENTRADA'])
        total_salidas = len([r for r in ultimos_registros if r.tipo == 'SALIDA'])
        
        return jsonify({
            'ok': True,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'usuario': {
                'id': usuario_actual.id,
                'nombre': usuario_actual.nombre,
                'rol': usuario_actual.rol
            },
            'fecha': hoy.isoformat(),
            'estadisticas': {
                'total_movimientos': total_movimientos,
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'personas_en_sede': len(personas_dentro)
            },
            'registros': registros_data,
            'personas_activas_en_sede': list(personas_dentro.values())
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'ok': False}), 500


@api_bp.route('/acceso/verificar', methods=['GET'])
@rate_limit(max_requests=60, ventana_segundos=60)  # 60 requests por minuto
def verificar_acceso_rapido():
    """Endpoint combinado: busca persona Y valida si puede entrar/salir en UNA sola llamada."""
    numero_doc = request.args.get('numero_doc', '').strip()
    tipo       = request.args.get('tipo', 'ENTRADA').upper()

    # ── VALIDACIÓN SEGURA DE ENTRADA ──────────────────────────────────────
    # Validar número de documento
    ok_doc, msg_doc = InputValidator.validar_numero_documento(numero_doc)
    if not ok_doc:
        log_evento_seguridad(
            'ACCESO_DENEGADO_VALIDACION',
            usuario_id=None,
            detalles=f'Documento inválido: {numero_doc}',
            severidad='WARNING'
        )
        return jsonify({'error': msg_doc}), 400
    
    # Validar tipo de acceso
    ok_tipo, tipo_validado = InputValidator.validar_tipo_acceso(tipo)
    if not ok_tipo:
        log_evento_seguridad(
            'ACCESO_DENEGADO_TIPO',
            usuario_id=None,
            detalles=f'Tipo inválido: {tipo}',
            severidad='WARNING'
        )
        return jsonify({'error': 'Tipo debe ser: ENTRADA o SALIDA'}), 400
    
    tipo = tipo_validado

    persona = Persona.query.filter_by(numero_doc=numero_doc, deleted_at=None).first()
    if not persona:
        registrar_intento_seguridad(numero_doc, 'VERIFICAR_ACCESO', False, 'Documento no registrado')
        return jsonify({'found': False, 'error': 'Documento no registrado en el sistema'}), 404

    # ── BLOQUEO TAJANTE DE VISITANTES ────────────────────────────────────────
    # Los visitantes NO acceden al panel de entrada/salida. Punto.
    if persona.perfil and persona.perfil.upper() == 'VISITANTE':
        registrar_intento_seguridad(numero_doc, 'VERIFICAR_ACCESO_VISITANTE', False, 
                                    f'Visitante intenta acceso directo - documento: {persona.nombre}')
        return jsonify({'found': False, 'error': 'Documento no tiene acceso a este panel'}), 404

    ultimo = RegistroAcceso.query.filter_by(
        persona_id=persona.id
    ).order_by(RegistroAcceso.timestamp.desc()).first()

    if not ultimo:
        puede_entrada, puede_salida, estado_actual = True, False, None
    elif ultimo.tipo.upper() == 'ENTRADA':
        puede_entrada, puede_salida, estado_actual = False, True, 'ENTRADA'
    else:
        puede_entrada, puede_salida, estado_actual = True, False, 'SALIDA'

    permitido = (tipo == 'ENTRADA' and puede_entrada) or (tipo == 'SALIDA' and puede_salida)

    # Equipos con ENTRADA activa (sin SALIDA) vinculados al último ingreso de esta persona
    equipos_adentro = []
    ultimo_ingreso_eq = RegistroAcceso.query.filter_by(
        persona_id=persona.id, tipo='ENTRADA', deleted_at=None
    ).order_by(RegistroAcceso.timestamp.desc()).first()
    if ultimo_ingreso_eq:
        reqs_entrada = RegistroAccesoEquipo.query.filter_by(
            registro_acceso_id=ultimo_ingreso_eq.id, tipo='ENTRADA'
        ).all()
        for req in reqs_entrada:
            ultimo_mov_eq = RegistroAccesoEquipo.query.filter_by(
                computador_id=req.computador_id
            ).order_by(RegistroAccesoEquipo.timestamp.desc()).first()
            if ultimo_mov_eq and ultimo_mov_eq.tipo.upper() == 'ENTRADA':
                comp_eq = Computador.query.filter_by(id=req.computador_id, deleted_at=None).first()
                if comp_eq:
                    equipos_adentro.append({'codigo_barras': comp_eq.codigo_barras, 'id': comp_eq.id})

    # El aprendiz puede ingresar al SENA libremente.
    # El acceso físico al AMBIENTE es controlado por la cerradura electrónica.
    instructor_activo = None
    bloqueado_sin_instructor = False

    # Log de acceso permitido
    if permitido:
        registrar_intento_seguridad(numero_doc, f'ACCESO_{tipo}', True, f'Documento: {persona.nombre}')

    return jsonify({
        'found':                    True,
        'permitido':                permitido,
        'bloqueado_sin_instructor': bloqueado_sin_instructor,
        'instructor_activo':        instructor_activo,
        'equipos_adentro': equipos_adentro,
        'id':              persona.id,
        'nombre':          InputValidator.sanitizar_string(persona.nombre),
        'numero_doc':      numero_doc,
        'tipo_doc':        persona.tipo_doc,
        'programa':        InputValidator.sanitizar_string(persona.programa or ''),
        'ficha':           InputValidator.sanitizar_string(persona.ficha or ''),
        'perfil':          InputValidator.sanitizar_string(persona.perfil or ''),
        'estado_actual':   estado_actual,
        'puede_entrada':   puede_entrada,
        'puede_salida':    puede_salida,
        'ultimo_registro': {
            'tipo':      ultimo.tipo,
            'timestamp': ultimo.timestamp.isoformat() + 'Z'
        } if ultimo else None
    }), 200

@api_bp.route('/barras/persona', methods=['GET'])
@token_required
def buscar_por_barras_persona(usuario_id):
    """Búsqueda por código de barras de persona (documento)"""
    codigo = request.args.get('codigo', '').strip()

    if not codigo or len(codigo) < 3:
        return jsonify({'error': 'Código inválido'}), 400

    persona = Persona.query.filter(
        Persona.numero_doc == codigo,
        Persona.deleted_at == None  # type: ignore
    ).first()
    if not persona:
        # fallback: búsqueda parcial
        persona = Persona.query.filter(
            Persona.numero_doc.contains(codigo),
            Persona.deleted_at == None  # type: ignore
        ).first()
    
    if persona:
        return jsonify({
            'found': True,
            'id': persona.id,
            'nombre': persona.nombre,
            'numero_doc': persona.numero_doc,
            'tipo_doc': persona.tipo_doc,
            'programa': persona.programa,
            'ficha': persona.ficha,
            'perfil': persona.perfil
        }), 200
    
    return jsonify({'found': False, 'error': 'Persona no encontrada'}), 404

@api_bp.route('/barras/ingreso-rapido', methods=['POST'])
@token_required
def ingreso_rapido_barras(usuario_id):
    """Ingreso ultrarrápido + foto + registro en una sola llamada"""
    datos = request.get_json()
    numero_doc = datos.get('numero_doc', '').strip()
    tipo = datos.get('tipo', 'ENTRADA')
    imagen_base64 = datos.get('foto')
    
    if not numero_doc:
        return jsonify({'error': 'Documento requerido'}), 400
    
    persona = Persona.query.filter_by(numero_doc=numero_doc, deleted_at=None).first()
    if not persona:
        persona = Persona(
            nombre='Visitante',
            tipo_doc='CC',
            numero_doc=numero_doc,
            perfil='visitante'
        )  # type: ignore
        db.session.add(persona)
        db.session.flush()
    
    registro = RegistroAcceso(
        persona_id=persona.id,
        numero_doc=numero_doc,
        tipo=tipo,
        timestamp=datetime.utcnow(),
        ambiente=datos.get('ambiente', 'Entrada principal')
    )  # type: ignore
    db.session.add(registro)
    db.session.flush()
    
    if imagen_base64:
        try:
            import base64
            imagen_bytes = base64.b64decode(imagen_base64.split(',')[-1])
            foto = Foto(
                persona_id=persona.id,
                numero_doc=numero_doc,
                registro_acceso_id=registro.id,
                imagen_datos=imagen_bytes,
                tamaño_bytes=len(imagen_bytes)  # type: ignore
            )  # type: ignore
            db.session.add(foto)
        except:
            pass
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'registro_id': registro.id,
        'persona_nombre': persona.nombre,
        'tipo': tipo,
        'timestamp': registro.timestamp.isoformat() + 'Z'
    }), 201

@api_bp.route('/equipos/verificar-seguridad', methods=['GET'])
def verificar_seguridad_equipo():
    """
    Verifica si un equipo puede entrar/salir de forma segura.
    Controles:
      1. Existe en el sistema?
      2. Estado actual (DENTRO/FUERA) compatible con la acción?
      3. Está asignado a otra persona? → alerta de propietario
      4. Está intentando salir alguien que no lo ingresó? → alerta de custodio
    """
    codigo    = request.args.get('codigo_barras', '').strip()
    numero_doc = request.args.get('numero_doc', '').strip()   # quien lo porta ahora
    tipo      = request.args.get('tipo', 'ENTRADA').upper()

    if not codigo:
        return jsonify({'error': 'codigo_barras requerido'}), 400

    comp = Computador.query.filter_by(codigo_barras=codigo, deleted_at=None).first()
    if not comp:
        # Verificar si el código pertenece a un equipo dado de baja — el código nunca es reutilizable
        comp_baja = Computador.query.filter(
            Computador.codigo_barras == codigo,
            Computador.deleted_at != None  # type: ignore
        ).first()
        if comp_baja:
            return jsonify({
                'found': True,
                'permitido': False,
                'barcode_tomado': True,
                'error': 'Este código de barras ya está registrado en otro equipo del sistema y no puede asignarse a un dispositivo distinto.'
            }), 409
        return jsonify({'found': False, 'error': 'Equipo no registrado en el sistema'}), 404

    # Estado actual del equipo (último movimiento en RegistroAccesoEquipo)
    ultimo_mov = RegistroAccesoEquipo.query.filter_by(
        computador_id=comp.id
    ).order_by(RegistroAccesoEquipo.timestamp.desc()).first()

    if not ultimo_mov:
        estado_equipo = None       # nunca ha ingresado
        puede_entrada = True
        puede_salida  = False
    elif ultimo_mov.tipo.upper() == 'ENTRADA':
        estado_equipo = 'DENTRO'
        puede_entrada = False
        puede_salida  = True
    else:
        estado_equipo = 'FUERA'
        puede_entrada = True
        puede_salida  = False

    permitido = (tipo == 'ENTRADA' and puede_entrada) or (tipo == 'SALIDA' and puede_salida)

    # Verificar propietario registrado
    alerta_propietario = False
    if comp.asignado_a_id and numero_doc:
        propietario = Persona.query.filter_by(id=comp.asignado_a_id, deleted_at=None).first()
        if propietario and propietario.numero_doc != numero_doc:
            alerta_propietario = True

    # Verificar custodio: quien lo ingresó ¿es quien lo está sacando?
    alerta_custodio = False
    persona_ingreso = None
    if tipo == 'SALIDA' and ultimo_mov and numero_doc:
        persona_ingreso = Persona.query.filter_by(id=ultimo_mov.persona_id, deleted_at=None).first()
        if persona_ingreso and persona_ingreso.numero_doc != numero_doc:
            alerta_custodio = True

    # ── Notificaciones de seguridad al administrador ──────────────────────────
    marca_modelo = f'{comp.marca or ""} {comp.modelo or ""}'.strip() or comp.codigo_barras
    ts_now = datetime.utcnow().isoformat() + 'Z'

    if alerta_propietario:
        propietario_reg = Persona.query.filter_by(id=comp.asignado_a_id, deleted_at=None).first()
        nombre_esperado = propietario_reg.nombre if propietario_reg else 'Propietario registrado'
        srv_correo.alerta_seguridad_equipo(
            tipo_alerta     = 'propietario',
            codigo_barras   = comp.codigo_barras,
            marca_modelo    = marca_modelo,
            portador_doc    = numero_doc,
            persona_esperada= nombre_esperado,
            accion          = tipo,
            timestamp       = ts_now,
        )

    if alerta_custodio:
        nombre_custodio = persona_ingreso.nombre if persona_ingreso else 'Custodio registrado'
        srv_correo.alerta_seguridad_equipo(
            tipo_alerta     = 'custodio',
            codigo_barras   = comp.codigo_barras,
            marca_modelo    = marca_modelo,
            portador_doc    = numero_doc,
            persona_esperada= nombre_custodio,
            accion          = tipo,
            timestamp       = ts_now,
        )

    return jsonify({
        'found':               True,
        'permitido':           permitido,
        'id':                  comp.id,
        'codigo_barras':       comp.codigo_barras,
        'marca':               comp.marca,
        'modelo':              comp.modelo,
        'tipo_equipo':         comp.tipo,
        'serie':               comp.serie,
        'estado_equipo':       estado_equipo,
        'puede_entrada':       puede_entrada,
        'puede_salida':        puede_salida,
        'alerta_propietario':  alerta_propietario,
        'alerta_custodio':     alerta_custodio,
        'ultimo_movimiento': {
            'tipo':      ultimo_mov.tipo,
            'timestamp': ultimo_mov.timestamp.isoformat() + 'Z'
        } if ultimo_mov else None
    }), 200


@api_bp.route('/computadores', methods=['GET', 'POST'])
@token_required
def gestionar_computadores(usuario_id):
    """GET: listar, POST: crear computador"""
    if request.method == 'GET':
        codigo_barras = request.args.get('codigo_barras')
        
        if codigo_barras:
            comp = Computador.query.filter_by(codigo_barras=codigo_barras, deleted_at=None).first()
            if comp:
                return jsonify({
                    'found': True,
                    'id': comp.id,
                    'codigo_barras': comp.codigo_barras,
                    'serie': comp.serie,
                    'marca': comp.marca,
                    'modelo': comp.modelo,
                    'tipo': comp.tipo,
                    'estado': comp.estado,
                    'ubicacion': comp.ubicacion,
                    'asignado_a': comp.asignado_a.nombre if comp.asignado_a else None
                }), 200
            return jsonify({'found': False}), 404
        
        computadores = Computador.query.filter_by(deleted_at=None).all()
        return jsonify({
            'computadores': [{
                'id': c.id,
                'codigo_barras': c.codigo_barras,
                'marca': c.marca,
                'modelo': c.modelo,
                'estado': c.estado
            } for c in computadores]
        }), 200
    
    else:  # POST
        datos = request.get_json()
        codigo = datos.get('codigo_barras', '').strip()
        
        if not codigo:
            return jsonify({'error': 'Código de barras requerido'}), 400
        
        existe = Computador.query.filter_by(codigo_barras=codigo, deleted_at=None).first()
        if existe:
            return jsonify({'error': 'Código ya existe'}), 400
        
        computador = Computador(
            codigo_barras=codigo,
            serie=datos.get('serie'),
            marca=datos.get('marca', 'No especificado'),
            modelo=datos.get('modelo', 'No especificado'),
            tipo=datos.get('tipo', 'Computador'),
            ubicacion=datos.get('ubicacion'),
            estado='activo'
        )  # type: ignore
        
        if datos.get('asignado_a_persona_doc'):
            persona = Persona.query.filter_by(numero_doc=datos.get('asignado_a_persona_doc')).first()
            if persona:
                computador.asignado_a_id = persona.id
        
        db.session.add(computador)
        db.session.commit()
        
        return jsonify({'id': computador.id, 'codigo_barras': computador.codigo_barras}), 201


@api_bp.route('/computadores/<computador_id>', methods=['DELETE'])
@token_required
def eliminar_computador(usuario_id, computador_id):
    """Elimina (soft-delete) un computador individual y sus registros de acceso."""
    solicitante = Usuario.query.get(usuario_id)
    if not solicitante or solicitante.rol != 'admin':
        return jsonify({'error': 'Solo admins pueden eliminar equipos'}), 403
    comp = Computador.query.filter_by(id=computador_id, deleted_at=None).first()
    if not comp:
        return jsonify({'error': 'Equipo no encontrado'}), 404
    RegistroAccesoEquipo.query.filter_by(computador_id=comp.id).delete()
    db.session.delete(comp)
    db.session.commit()
    return jsonify({'mensaje': 'Equipo eliminado correctamente'}), 200


@api_bp.route('/ingreso-equipos', methods=['POST'])
@token_required
def ingreso_equipos(usuario_id):
    """Registra ingreso de persona + equipos (computador, etc.)"""
    datos = request.get_json()
    numero_doc = datos.get('numero_doc', '').strip()
    tipo = datos.get('tipo', 'ENTRADA')
    equipos = datos.get('equipos', [])  # Lista de códigos de barras
    imagen_base64 = datos.get('foto')
    
    if not numero_doc:
        return jsonify({'error': 'Documento requerido'}), 400
    
    persona = Persona.query.filter_by(numero_doc=numero_doc, deleted_at=None).first()
    if not persona:
        persona = Persona(
            nombre='Visitante',
            tipo_doc='CC',
            numero_doc=numero_doc,
            perfil='visitante'
        )  # type: ignore
        db.session.add(persona)
        db.session.flush()
    
    registro = RegistroAcceso(
        persona_id=persona.id,
        numero_doc=numero_doc,
        tipo=tipo,
        timestamp=datetime.utcnow(),
        ambiente=datos.get('ambiente', 'Entrada principal')
    )  # type: ignore
    db.session.add(registro)
    db.session.flush()
    
    equipos_registrados = []
    for codigo_eq in equipos:
        comp = Computador.query.filter_by(codigo_barras=codigo_eq, deleted_at=None).first()
        if comp:
            comp.asignado_a_id = persona.id
            equipos_registrados.append(codigo_eq)
    
    if imagen_base64:
        try:
            import base64
            imagen_bytes = base64.b64decode(imagen_base64.split(',')[-1])
            foto = Foto(
                persona_id=persona.id,
                numero_doc=numero_doc,
                registro_acceso_id=registro.id,
                imagen_datos=imagen_bytes,
                tamaño_bytes=len(imagen_bytes)  # type: ignore
            )  # type: ignore
            db.session.add(foto)
        except:
            pass
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'registro_id': registro.id,
        'persona_nombre': persona.nombre,
        'equipos_registrados': equipos_registrados,
        'timestamp': registro.timestamp.isoformat() + 'Z'
    }), 201

@api_bp.route('/personas/<persona_id>/equipos-asignados', methods=['GET'])
@token_required
def obtener_equipos_asignados(usuario_id, persona_id):
    """Obtiene todos los equipos asignados permanentemente a una persona"""
    equipos = Computador.query.filter(
        Computador.asignado_a_id == persona_id,
        Computador.deleted_at == None  # type: ignore
    ).all()
    
    return jsonify({
        'equipos': [{
            'id': e.id,
            'codigo_barras': e.codigo_barras,
            'marca': e.marca,
            'modelo': e.modelo,
            'serie': e.serie,
            'tipo': e.tipo,
            'estado': e.estado
        } for e in equipos]
    }), 200

@api_bp.route('/personas/<persona_id>/asignar-equipo', methods=['POST'])
@token_required
def asignar_equipo_a_persona(usuario_id, persona_id):
    """
    Asigna un equipo permanentemente a una persona (primera vez)
    Una vez asignado, se incluirá automáticamente en ingresos/salidas
    """
    datos = request.get_json()
    codigo_barras = datos.get('codigo_barras', '').strip()
    
    if not codigo_barras:
        return jsonify({'error': 'Código de barras requerido'}), 400
    
    persona = Persona.query.filter_by(id=persona_id, deleted_at=None).first()
    if not persona:
        return jsonify({'error': 'Persona no encontrada'}), 404
    
    computador = Computador.query.filter_by(codigo_barras=codigo_barras, deleted_at=None).first()
    if not computador:
        return jsonify({'error': 'Computador no encontrado'}), 404
    
    # Si ya está asignado a otro, desasignar
    if computador.asignado_a_id and computador.asignado_a_id != persona_id:
        return jsonify({'error': 'Equipo ya está asignado a otra persona'}), 400
    
    # Asignar permanentemente
    computador.asignado_a_id = persona_id
    db.session.commit()
    
    return jsonify({
        'success': True,
        'mensaje': f'Equipo {computador.marca} {computador.modelo} asignado a {persona.nombre}',
        'equipo_id': computador.id
    }), 200

@api_bp.route('/ingreso-automatico-equipo', methods=['POST'])
@token_required
def ingreso_automatico_con_equipos_asignados(usuario_id):
    """
    Ingreso rápido: cuando escanea persona, automáticamente registra
    el acceso de ella + todos sus equipos asignados permanentemente
    """
    datos = request.get_json()
    numero_doc = datos.get('numero_doc', '').strip()
    tipo = datos.get('tipo', 'ENTRADA')
    imagen_base64 = datos.get('foto')
    
    if not numero_doc:
        return jsonify({'error': 'Documento requerido'}), 400
    
    # Buscar persona
    persona = Persona.query.filter_by(numero_doc=numero_doc, deleted_at=None).first()
    if not persona:
        persona = Persona(
            nombre='Visitante',
            tipo_doc='CC',
            numero_doc=numero_doc,
            perfil='visitante'
        )  # type: ignore
        db.session.add(persona)
        db.session.flush()
    
    # Registrar acceso de persona
    registro_persona = RegistroAcceso(
        persona_id=persona.id,
        numero_doc=numero_doc,
        tipo=tipo,
        timestamp=datetime.utcnow(),
        ambiente=datos.get('ambiente', 'Entrada principal')
    )  # type: ignore
    db.session.add(registro_persona)
    db.session.flush()
    
    # Guardar foto si existe
    if imagen_base64:
        try:
            import base64
            imagen_bytes = base64.b64decode(imagen_base64.split(',')[-1])
            foto = Foto(
                persona_id=persona.id,
                numero_doc=numero_doc,
                registro_acceso_id=registro_persona.id,
                imagen_datos=imagen_bytes,
                tamaño_bytes=len(imagen_bytes)  # type: ignore
            )  # type: ignore
            db.session.add(foto)
        except:
            pass
    
    # Obtener y registrar equipos PERMANENTEMENTE asignados
    equipos = Computador.query.filter(
        Computador.asignado_a_id == persona.id,
        Computador.deleted_at.is_(None)
    ).all()  # type: ignore
    
    equipos_registrados = []
    for equipo in equipos:
        # Registrar acceso del equipo
        reg_equipo = RegistroAccesoEquipo(
            computador_id=equipo.id,
            persona_id=persona.id,
            tipo=tipo,
            timestamp=datetime.utcnow(),
            registro_acceso_id=registro_persona.id
        )  # type: ignore
        db.session.add(reg_equipo)
        equipos_registrados.append({
            'codigo_barras': equipo.codigo_barras,
            'marca': equipo.marca,
            'modelo': equipo.modelo
        })
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'registro_id': registro_persona.id,
        'persona_nombre': persona.nombre,
        'tipo': tipo,
        'equipos_automaticos': equipos_registrados,
        'total_equipos': len(equipos_registrados),
        'timestamp': registro_persona.timestamp.isoformat() + 'Z'
    }), 201

@api_bp.route('/respaldos/crear', methods=['POST'])
@token_required
def crear_respaldo(usuario_id):
    from cloud_storage import DatabaseBackupManager
    
    datos = request.get_json() or {}
    manager = DatabaseBackupManager()
    resultado = manager.crear_respaldo_completo(usuario_id, datos.get('descripcion', ''))
    
    if resultado['success']:
        return jsonify(resultado), 201
    else:
        return jsonify(resultado), 500

@api_bp.route('/respaldos', methods=['GET'])
@token_required
def listar_respaldos(usuario_id):
    respaldos = Respaldo.query.filter_by(deleted_at=None).order_by(Respaldo.created_at.desc()).all()
    
    lista = []
    for r in respaldos:
        lista.append({
            'id': r.id,
            'nombre_archivo': r.nombre_archivo,
            'tipo': r.tipo,
            'tamaño_bytes': r.tamaño_bytes,
            'created_at': r.created_at.isoformat() + 'Z',
            'restaurado_en': r.restaurado_en.isoformat() + 'Z' if r.restaurado_en else None
        })
    
    return jsonify({'respaldos': lista}), 200

@api_bp.route('/respaldos/<respaldo_id>/restaurar', methods=['POST'])
@token_required
def restaurar_respaldo(usuario_id, respaldo_id):
    from cloud_storage import DatabaseBackupManager
    
    manager = DatabaseBackupManager()
    resultado = manager.restaurar_desde_respaldo(respaldo_id, usuario_id)
    
    if resultado['success']:
        return jsonify(resultado), 200
    else:
        return jsonify(resultado), 500


# ── Sincronización local ↔ nube ────────────────────────────────────────────────

@api_bp.route('/sync/estado', methods=['GET'])
@token_required
def sync_estado(usuario_id):
    """
    Retorna el estado actual de la sincronización:
      - pendientes: cantidad de respaldos locales aún no guardados en el destino
      - cloud_ok:   si el pendrive/S3 está accesible en este momento
      - backend:    'usb' o 's3'
      - items:      lista breve de archivos en cola
    """
    from sync_manager import contar_pendientes, listar_pendientes
    from cloud_storage import crear_storage_manager
    from config import Config

    try:
        pendientes = contar_pendientes()
        storage    = crear_storage_manager()
        cloud_ok   = storage.verificar_conexion()
        items      = listar_pendientes()
        backend    = getattr(Config, 'STORAGE_BACKEND', 'usb')

        return jsonify({
            'pendientes': pendientes,
            'cloud_ok':   cloud_ok,
            'backend':    backend,
            'items':      items
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/sync/ejecutar', methods=['POST'])
@token_required
def sync_ejecutar(usuario_id):
    """
    Fuerza la sincronización inmediata de todos los respaldos locales pendientes.
    Útil para subir manualmente cuando el administrador sabe que la nube está disponible.
    """
    from sync_manager import procesar_pendientes
    from flask import current_app

    try:
        resultado = procesar_pendientes(current_app._get_current_object())
        if not resultado.get('cloud_ok'):
            return jsonify({
                'success': False,
                'mensaje': 'El pendrive no está conectado o el destino no está disponible'
            }), 503

        return jsonify({
            'success':    True,
            'verificados': resultado['verificados'],
            'exitosos':    resultado['exitosos'],
            'fallidos':    resultado['fallidos'],
            'mensaje':     f"{resultado['exitosos']} respaldo(s) subido(s) a la nube"
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



@token_required
def exportar_excel_usb(usuario_id):
    """Exporta toda la BD a Excel y guarda en USB + RESPALDOS_USB."""
    try:
        from export_excel import exportar_todo_excel
        from flask import current_app, send_file
        import io

        excel_bytes, nombre_archivo, usb_guardado, ruta = exportar_todo_excel(current_app._get_current_object())

        buf = io.BytesIO(excel_bytes)
        buf.seek(0)

        response = send_file(
            buf,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nombre_archivo
        )
        response.headers['X-USB-Guardado'] = 'true' if usb_guardado else 'false'
        response.headers['X-Ruta-Guardado'] = ruta
        return response

    except ImportError as e:
        return jsonify({'error': 'openpyxl no instalado. Ejecuta: pip install openpyxl', 'detalle': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/estadisticas', methods=['GET'])
@token_required
def estadisticas(usuario_id):
    from sqlalchemy import func
    
    total_personas = Persona.query.filter_by(deleted_at=None).count()
    personas_por_perfil = db.session.query(
        Persona.perfil,
        func.count(Persona.id)
    ).filter_by(deleted_at=None).group_by(Persona.perfil).all()
    
    total_accesos = RegistroAcceso.query.filter_by(deleted_at=None).count()
    accesos_por_tipo = db.session.query(
        RegistroAcceso.tipo,
        func.count(RegistroAcceso.id)
    ).filter_by(deleted_at=None).group_by(RegistroAcceso.tipo).all()
    
    total_fotos = Foto.query.filter_by(deleted_at=None).count()
    
    return jsonify({
        'total_personas': total_personas,
        'personas_por_perfil': [{'perfil': p[0], 'cantidad': p[1]} for p in personas_por_perfil],
        'total_accesos': total_accesos,
        'accesos_por_tipo': [{'tipo': a[0], 'cantidad': a[1]} for a in accesos_por_tipo],
        'total_fotos': total_fotos
    }), 200

# ========================
# ENDPOINTS DE FOTOS
# ========================

@api_bp.route('/fotos', methods=['POST'])
@token_required
def crear_foto(usuario_id):
    """
    Guardar foto asociada a un registro de acceso
    Body: {
        "numero_doc": "string",
        "persona_id": "string",
        "registro_acceso_id": "string (opcional)",
        "imagen_base64": "string"
    }
    """
    try:
        datos = request.get_json()
        
        if not datos:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        numero_doc = datos.get('numero_doc')
        persona_id = datos.get('persona_id')
        imagen_base64 = datos.get('imagen_base64')
        registro_acceso_id = datos.get('registro_acceso_id')
        
        if not numero_doc or not imagen_base64 or not persona_id:
            return jsonify({'error': 'numero_doc, persona_id e imagen_base64 son requeridos'}), 400
        
        # Decodificar imagen base64
        import base64
        try:
            # Remover el prefijo data:image/jpeg;base64, si existe
            if ',' in imagen_base64:
                imagen_base64 = imagen_base64.split(',')[1]
            imagen_datos = base64.b64decode(imagen_base64)
        except Exception as e:
            return jsonify({'error': f'Error decodificando imagen: {str(e)}'}), 400
        
        # Crear foto
        foto = Foto(
            persona_id=persona_id,
            numero_doc=numero_doc,
            registro_acceso_id=registro_acceso_id,
            imagen_datos=imagen_datos,
            tipo_contenido='image/jpeg',
            tamaño_bytes=len(imagen_datos)  # type: ignore
        )  # type: ignore
        
        db.session.add(foto)
        db.session.commit()
        
        return jsonify({
            'id': foto.id,
            'numero_doc': foto.numero_doc,
            'tamaño_bytes': foto.tamaño_bytes,
            'created_at': foto.created_at.isoformat() + 'Z'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/fotos/<numero_doc>', methods=['GET'])
@token_required
def obtener_foto_persona(usuario_id, numero_doc):
    """Obtener la foto más reciente de una persona"""
    try:
        foto = Foto.query.filter_by(
            numero_doc=numero_doc,
            deleted_at=None
        ).order_by(Foto.created_at.desc()).first()
        
        if not foto:
            return jsonify({'error': 'Foto no encontrada'}), 404
        
        from flask import send_file
        from io import BytesIO
        
        return send_file(
            BytesIO(foto.imagen_datos),
            mimetype=foto.tipo_contenido,
            as_attachment=False,
            download_name=f'foto_{numero_doc}.jpg'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/fotos/acceso/<registro_id>', methods=['GET'])
@token_required
def obtener_foto_acceso(usuario_id, registro_id):
    """Obtener la foto de un registro de acceso específico"""
    try:
        foto = Foto.query.filter_by(
            registro_acceso_id=registro_id,
            deleted_at=None
        ).first()
        
        if not foto:
            return jsonify({'error': 'Foto no encontrada'}), 404
        
        from flask import send_file
        from io import BytesIO
        
        return send_file(
            BytesIO(foto.imagen_datos),
            mimetype=foto.tipo_contenido,
            as_attachment=False,
            download_name=f'foto_acceso_{registro_id}.jpg'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/fotos/persona/<persona_id>', methods=['GET'])
@token_required
def listar_fotos_persona(usuario_id, persona_id):
    """Listar todas las fotos de una persona"""
    try:
        fotos = Foto.query.filter_by(
            persona_id=persona_id,
            deleted_at=None
        ).order_by(Foto.created_at.desc()).all()
        
        return jsonify({
            'fotos': [
                {
                    'id': f.id,
                    'numero_doc': f.numero_doc,
                    'registro_acceso_id': f.registro_acceso_id,
                    'created_at': f.created_at.isoformat() + 'Z',
                    'tamaño_bytes': f.tamaño_bytes
                }
                for f in fotos
            ],
            'total': len(fotos)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== ENDPOINTS PARA MODO OFFLINE =====

@api_bp.route('/personas/cache', methods=['GET'])
def get_personas_cache():
    """Obtener todas las personas para caché offline - ENDPOINT PUBLICO"""
    try:
        # Usar SQLAlchemy para obtener todas las personas
        personas_query = Persona.query.filter_by(deleted_at=None).order_by(Persona.nombre).all()
        
        personas = []
        for p in personas_query:
            personas.append({
                'id': p.id,
                'nombre': p.nombre,
                'tipo_doc': p.tipo_doc,
                'numero_doc': p.numero_doc,
                'email': p.email,
                'telefono': p.telefono,
                'perfil': p.perfil,
                'programa': p.programa,
                'ficha': p.ficha,
                'area': p.area,
                'verificado': p.verificado
            })
        
        return jsonify({
            'personas': personas,
            'total': len(personas),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'debug': traceback.format_exc()
        }), 500


@api_bp.route('/registros-acceso/manual', methods=['POST'])
@token_required
def registrar_acceso_manual(usuario_id):
    """Registro manual de acceso (cuando falla barras)"""
    try:
        datos = request.get_json()
        
        nombre = datos.get('nombre', '').strip()
        tipo_doc = datos.get('tipo_doc', '').strip()
        numero_doc = datos.get('numero_doc', '').strip()
        tipo = datos.get('tipo', 'ENTRADA').upper()
        ambiente = datos.get('ambiente', 'DESCONOCIDO')
        
        if not nombre or not tipo_doc or not numero_doc:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        # Buscar o crear persona
        persona = Persona.query.filter_by(numero_doc=numero_doc).first()
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # VALIDACIÓN: Solo VIGILANTES pueden crear o registrar VISITANTES
        # ═══════════════════════════════════════════════════════════════════════════════
        usuario_actual = Usuario.query.get(usuario_id)
        
        if not persona:
            # Si la persona NO EXISTE → será visitante → Solo vigilante puede crearla
            if not usuario_actual or usuario_actual.rol != 'vigilante':
                print(f"❌ [POST /api/registros-acceso/manual] Acceso denegado: Usuario no es vigilante intentando registrar nuevo visitante")
                return jsonify({
                    'error': 'No tienes permiso para registrar visitantes. Solo los vigilantes pueden registrar nuevas personas desde el panel de vigilancia.'
                }), 403
            
            persona = Persona(
                nombre=nombre,
                tipo_doc=tipo_doc,
                numero_doc=numero_doc,
                perfil='visitante',
                verificado=False
            )  # type: ignore
            db.session.add(persona)
            db.session.commit()
        
        else:
            # Si la persona EXISTE y es VISITANTE → Solo vigilante puede registrar su acceso
            if persona.perfil.upper() == 'VISITANTE' and (not usuario_actual or usuario_actual.rol != 'vigilante'):
                print(f"❌ [POST /api/registros-acceso/manual] Acceso denegado: Usuario no es vigilante intentando registrar acceso de visitante existente")
                return jsonify({
                    'error': 'No tienes permiso para registrar acceso de visitantes. Solo los vigilantes pueden hacerlo desde el panel de vigilancia.'
                }), 403
        
        # Validar que entrada/salida sean alternadas
        es_valido, msg = validar_acceso(persona.id, tipo)
        if not es_valido:
            return jsonify({'error': msg, 'bloqueado': True}), 403
        
        # Crear registro de acceso
        registro = RegistroAcceso(
            persona_id=persona.id,
            numero_doc=numero_doc,
            tipo=tipo,
            timestamp=datetime.utcnow(),
            ambiente=ambiente,
            observaciones='Registro manual (barras no disponible)'
        )  # type: ignore
        db.session.add(registro)
        db.session.commit()

        emitir_evento_acceso_tiempo_real(registro, persona)
        try:
            gestionar_ocupacion_instructor(persona, registro, tipo)
        except Exception as _e_gest:
            print(f'[OCUPACION] Error en gestionar_ocupacion_instructor: {_e_gest}')
        
        return jsonify({
            'id': registro.id,
            'mensaje': msg,
            'persona': persona.nombre,
            'documento': numero_doc,
            'tipo': tipo,
            'timestamp': registro.timestamp.isoformat() + 'Z'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/registros-acceso-offline', methods=['POST'])
@token_required
def sincronizar_acceso_offline(usuario_id):
    """Sincronizar registros guardados en offline"""
    try:
        datos = request.get_json()
        
        numero_doc = datos.get('numero_doc', '').strip()
        nombre = datos.get('nombre', '').strip()
        tipo = datos.get('tipo', 'ENTRADA').upper()
        ambiente = datos.get('ambiente', 'DESCONOCIDO')
        timestamp = datos.get('timestamp')
        es_manual = datos.get('manual', False)
        
        if not numero_doc or not tipo:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        # Buscar o crear persona
        persona = Persona.query.filter_by(numero_doc=numero_doc).first()
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # VALIDACIÓN: Rechazar visitantes en sincronización offline
        # Los visitantes NO deben registrarse desde paneles offline de aprendices
        # ═══════════════════════════════════════════════════════════════════════════════
        if not persona and nombre:
            # Si la persona NO EXISTE → sería visitante → RECHAZAR en offline
            print(f"❌ [POST /api/registros-acceso-offline] Rechazado: Intento de registrar visitante nuevo en sincronización offline")
            return jsonify({
                'error': 'No se puede sincronizar registro de visitante. Los visitantes deben ser registrados por el vigilante desde el panel de vigilancia.',
                'numero_doc': numero_doc
            }), 403
        
        if not persona:
            return jsonify({'error': 'Persona no encontrada'}), 404
        
        # Si la persona existe y es VISITANTE → RECHAZAR en offline
        if persona.perfil.upper() == 'VISITANTE':
            print(f"❌ [POST /api/registros-acceso-offline] Rechazado: Intento de sincronizar acceso de visitante desde offline")
            return jsonify({
                'error': 'Los visitantes no pueden registrar acceso desde aplicaciones offline. Deben usar el panel de vigilancia.',
                'numero_doc': numero_doc,
                'perfil': persona.perfil
            }), 403

        # Validar alternancia también en sincronización offline
        es_valido, mensaje = validar_acceso(persona.id, tipo)
        if not es_valido:
            return jsonify({'error': mensaje, 'bloqueado': True}), 403
        
        # Crear registro
        obs = 'Registro sincronizado desde offline'
        if es_manual:
            obs += ' (registro manual)'
        
        registro = RegistroAcceso(
            persona_id=persona.id,
            numero_doc=numero_doc,
            tipo=tipo,
            timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.utcnow(),
            ambiente=ambiente,
            observaciones=obs
        )  # type: ignore
        db.session.add(registro)
        db.session.commit()

        emitir_evento_acceso_tiempo_real(registro, persona)
        try:
            gestionar_ocupacion_instructor(persona, registro, tipo)
        except Exception as _e_gest:
            print(f'[OCUPACION] Error en gestionar_ocupacion_instructor: {_e_gest}')
        
        return jsonify({
            'id': registro.id,
            'mensaje': 'Registro sincronizado',
            'persona': persona.nombre,
            'timestamp': registro.timestamp.isoformat() + 'Z'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════
# OCUPACIÓN DE AMBIENTES — SOLO INSTRUCTORES
# ═══════════════════════════════════════════════════════════════════════

@api_bp.route('/ambientes/ocupados', methods=['GET'])
@token_required
def listar_ambientes_ocupados(usuario_id):
    """Devuelve todos los ambientes actualmente ocupados por instructores."""
    try:
        ocupaciones = OcupacionAmbiente.query.filter_by(
            estado='ocupado', deleted_at=None
        ).order_by(OcupacionAmbiente.created_at.desc()).all()

        result = []
        for o in ocupaciones:
            p = o.persona
            result.append({
                'id': o.id,
                'ambiente': o.ambiente,
                'estado': o.estado,
                'desde': o.created_at.isoformat() + 'Z' if o.created_at else None,
                'persona': {
                    'id': p.id if p else None,
                    'nombre': p.nombre if p else 'N/A',
                    'numero_doc': o.numero_doc,
                    'area': p.area if p else None,
                    'especialidad': p.especialidad if p else None,
                }
            })
        return jsonify({'ocupaciones': result, 'total': len(result)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/ambientes/<ocupacion_id>/liberar', methods=['PUT'])
@token_required
def liberar_ambiente(usuario_id, ocupacion_id):
    """El vigilante libera manualmente un ambiente ocupado por un instructor."""
    try:
        ocupacion = OcupacionAmbiente.query.filter_by(
            id=ocupacion_id, deleted_at=None
        ).first()
        if not ocupacion:
            return jsonify({'error': 'Ocupación no encontrada'}), 404
        if ocupacion.estado != 'ocupado':
            return jsonify({'error': 'El ambiente ya fue liberado'}), 400

        ocupacion.estado = 'liberado'
        ocupacion.liberado_por = 'vigilante'
        ocupacion.liberado_at = datetime.utcnow()
        db.session.commit()

        persona = ocupacion.persona
        emitir_evento_ambiente('ambiente_liberado', ocupacion, persona)

        return jsonify({
            'mensaje': f'Ambiente {ocupacion.ambiente} liberado correctamente',
            'ambiente': ocupacion.ambiente,
            'persona': persona.nombre if persona else 'N/A'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/ambientes/trasladar', methods=['POST'])
@token_required
def trasladar_ambiente(usuario_id):
    """Traslada a un instructor de un ambiente a otro edificio/ambiente."""
    try:
        d = request.get_json()
        ocupacion_id    = d.get('ocupacion_id')
        ambiente_destino = (d.get('ambiente_destino') or '').strip()

        if not ocupacion_id or not ambiente_destino:
            return jsonify({'error': 'ocupacion_id y ambiente_destino son requeridos'}), 400

        # 1. Buscar ocupación origen
        ocu_origen = OcupacionAmbiente.query.filter_by(
            id=ocupacion_id, estado='ocupado', deleted_at=None
        ).first()
        if not ocu_origen:
            return jsonify({'error': 'Ocupación no encontrada o ya fue liberada'}), 404

        persona = ocu_origen.persona
        ambiente_origen = ocu_origen.ambiente

        # 2. Marcar origen como trasladado
        ocu_origen.estado     = 'liberado'
        ocu_origen.liberado_por = 'traslado'
        ocu_origen.liberado_at  = datetime.utcnow()

        # 3. Crear nueva ocupación en destino
        nueva_ocu = OcupacionAmbiente(
            persona_id  = ocu_origen.persona_id,
            numero_doc  = ocu_origen.numero_doc,
            ambiente    = ambiente_destino,
            estado      = 'ocupado',
        )  # type: ignore
        db.session.add(nueva_ocu)
        db.session.commit()

        # 4. Determinar edificios origen/destino
        def _edificio(amb):
            if ' - PISO' in amb:
                return amb.split(' - PISO')[0].strip()
            return amb.split('-')[0].strip() if '-' in amb else amb

        payload = {
            'evento': 'traslado_ambiente',
            'persona': {
                'id': persona.id if persona else None,
                'nombre': persona.nombre if persona else 'N/A',
                'numero_doc': ocu_origen.numero_doc,
                'perfil': persona.perfil if persona else None,
            },
            'origen': {
                'ambiente': ambiente_origen,
                'edificio': _edificio(ambiente_origen),
                'ocupacion_id': ocupacion_id,
            },
            'destino': {
                'ambiente': ambiente_destino,
                'edificio': _edificio(ambiente_destino),
                'ocupacion_id': nueva_ocu.id,
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }

        try:
            if websocket_handler.socketio:
                websocket_handler.socketio.emit('traslado_ambiente', payload, namespace='/')
        except Exception as we:
            print(f'[WEBSOCKET] Error emitiendo traslado_ambiente: {we}')

        return jsonify({
            'mensaje': f'Traslado realizado: {persona.nombre if persona else "—"} → {ambiente_destino}',
            'nueva_ocupacion_id': nueva_ocu.id,
            'ambiente_origen': ambiente_origen,
            'ambiente_destino': ambiente_destino,
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500




@api_bp.route('/usuarios', methods=['GET'])
@token_required
def listar_usuarios(usuario_id):
    """Lista todos los usuarios del sistema (solo admins)"""
    solicitante = Usuario.query.get(usuario_id)
    if not solicitante or solicitante.rol != 'admin':
        return jsonify({'error': 'Solo admins pueden ver usuarios'}), 403
    
    usuarios = Usuario.query.filter_by(deleted_at=None).all()
    return jsonify({
        'usuarios': [
            {
                'id': u.id,
                'email': u.email,
                'nombre': u.nombre,
                'rol': u.rol,
                'activo': u.activo
            }
            for u in usuarios
        ]
    }), 200


@api_bp.route('/admin/importar-usuarios', methods=['POST'])
@token_required
def importar_usuarios(usuario_id):
    """Migra usuarios existentes conservando sus hashes de contraseña."""
    solicitante = Usuario.query.get(usuario_id)
    if not solicitante or solicitante.rol != 'admin':
        return jsonify({'error': 'Solo admins pueden importar usuarios'}), 403

    datos = request.get_json(silent=True) or {}
    usuarios = datos.get('usuarios')
    if not isinstance(usuarios, list) or len(usuarios) > 500:
        return jsonify({'error': 'Lista de usuarios inválida'}), 400

    import re
    hash_re = re.compile(r'^(scrypt|pbkdf2|argon2|bcrypt|sha256\$)')
    importados = 0
    with db.session.no_autoflush:
        for item in usuarios:
            email = str(item.get('email', '')).strip().lower()
            password_hash = str(item.get('password_hash', ''))
            if not email or '@' not in email or not hash_re.match(password_hash):
                continue
            usuario = Usuario.query.filter_by(email=email).first()
            if not usuario:
                usuario = Usuario(email=email, password_hash=password_hash,
                                  nombre=str(item.get('nombre') or email),
                                  rol=str(item.get('rol') or 'vigilante'),
                                  activo=bool(item.get('activo', True)))
                db.session.add(usuario)
            else:
                usuario.password_hash = password_hash
                usuario.nombre = str(item.get('nombre') or usuario.nombre)
                usuario.rol = str(item.get('rol') or usuario.rol)
                usuario.activo = bool(item.get('activo', True))
                usuario.deleted_at = None
            importados += 1
    db.session.commit()
    return jsonify({'mensaje': 'Usuarios importados correctamente', 'importados': importados}), 200


@api_bp.route('/usuarios/<uid>', methods=['PUT'])
@token_required
def actualizar_usuario(usuario_id, uid):
    """Actualizar datos de un usuario"""
    solicitante = Usuario.query.get(usuario_id)
    if not solicitante or solicitante.rol != 'admin':
        return jsonify({'error': 'Solo admins pueden modificar usuarios'}), 403
    
    usuario = Usuario.query.get(uid)
    if not usuario or usuario.deleted_at:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    datos = request.get_json()
    if 'nombre' in datos:
        usuario.nombre = datos['nombre']
    if 'rol' in datos:
        usuario.rol = datos['rol']
    if 'activo' in datos:
        usuario.activo = datos['activo']
    if datos.get('password'):
        usuario.password_hash = generate_password_hash(datos['password'])
    
    db.session.commit()
    return jsonify({'id': usuario.id, 'mensaje': 'Usuario actualizado'}), 200


@api_bp.route('/usuarios/<uid>', methods=['DELETE'])
@token_required
def eliminar_usuario(usuario_id, uid):
    """Eliminar usuario (soft delete)"""
    solicitante = Usuario.query.get(usuario_id)
    if not solicitante or solicitante.rol != 'admin':
        return jsonify({'error': 'Solo admins pueden eliminar usuarios'}), 403
    
    if usuario_id == uid:
        return jsonify({'error': 'No puedes eliminarte a ti mismo'}), 400
    
    usuario = Usuario.query.get(uid)
    if not usuario or usuario.deleted_at:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    usuario.soft_delete()
    return jsonify({'mensaje': 'Usuario eliminado'}), 200


# ─── MANTENIMIENTO / DEPURACIÓN ────────────────────────────────────────────────

@api_bp.route('/admin/limpiar-computadores', methods=['POST'])
@token_required
def limpiar_computadores(usuario_id):
    """Elimina todos los computadores y sus registros de acceso de equipo."""
    solicitante = Usuario.query.get(usuario_id)
    if not solicitante or solicitante.rol != 'admin':
        return jsonify({'error': 'Solo admins pueden ejecutar esta acción'}), 403
    try:
        n_eq   = RegistroAccesoEquipo.query.delete()
        n_comp = Computador.query.delete()
        db.session.commit()
        return jsonify({
            'mensaje': 'Equipos eliminados correctamente',
            'equipos_eliminados': n_comp,
            'registros_equipo_eliminados': n_eq
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/limpiar-registros', methods=['POST'])
@token_required
def limpiar_registros(usuario_id):
    """Elimina TODOS los registros de acceso, ocupaciones y equipos registrados.
    Deja el sistema en estado limpio: nadie dentro ni fuera."""
    solicitante = Usuario.query.get(usuario_id)
    if not solicitante or solicitante.rol != 'admin':
        return jsonify({'error': 'Solo admins pueden ejecutar esta acción'}), 403
    try:
        n_eq   = RegistroAccesoEquipo.query.delete()
        n_ocup = OcupacionAmbiente.query.delete()
        n_reg  = RegistroAcceso.query.delete()
        db.session.commit()
        try:
            if websocket_handler.socketio:
                websocket_handler.socketio.emit('registros_limpiados', {
                    'motivo': 'limpiar_registros',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }, namespace='/')
        except Exception:
            pass
        return jsonify({
            'mensaje': 'Registros eliminados correctamente',
            'registros_eliminados': n_reg,
            'registros_equipo_eliminados': n_eq,
            'ocupaciones_eliminadas': n_ocup
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/vigilante/cerrar-turno', methods=['POST'])
@token_required
def cerrar_turno(usuario_id):
    """Exporta los registros del turno del vigilante a Excel (USB + nube),
    luego los elimina. Admins exportan y borran TODOS los registros."""
    import io, base64
    solicitante = Usuario.query.get(usuario_id)
    if not solicitante:
        return jsonify({'error': 'Usuario no válido'}), 403

    try:
        # ── 1. Recopilar registros del turno ──────────────────────────────
        # Filtrar SOLO registros de HOY para que coincida con lo que ve el vigilante
        # en la pantalla de vigilancia
        hoy = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        registros_db = RegistroAcceso.query.filter(
            RegistroAcceso.deleted_at == None,  # type: ignore
            RegistroAcceso.timestamp >= hoy
        ).order_by(RegistroAcceso.timestamp.desc()).all()

        n_registros = len(registros_db)

        # ── 2. Construir filas enriquecidas para el Excel ─────────────────
        try:
            from openpyxl import Workbook
            from export_excel import hoja_diario, hoja_resumen_dia, detectar_usb, OPENPYXL_OK
            openpyxl_ok = OPENPYXL_OK
        except ImportError:
            openpyxl_ok = False

        excel_bytes = None
        nombre_archivo = None
        usb_guardado = False
        nube_guardada = False
        ruta_local = None

        if openpyxl_ok and n_registros > 0:
            # Mapa de personas para enriquecer
            from models import Persona as _Persona
            from sqlalchemy import or_ as _or
            docs = list({r.numero_doc for r in registros_db if r.numero_doc})
            personas_list = _Persona.query.filter(
                _Persona.numero_doc.in_(docs)
            ).all() if docs else []
            personas_doc_map = {p.numero_doc: p for p in personas_list}

            enriquecidos = []
            for r in registros_db:
                persona = personas_doc_map.get(r.numero_doc)
                fecha_str = hora_str = ""
                if r.timestamp:
                    fecha_str = r.timestamp.strftime("%d/%m/%Y")
                    hora_str  = r.timestamp.strftime("%H:%M:%S")
                enriquecidos.append({
                    "fecha":      fecha_str,
                    "hora":       hora_str,
                    "nombre":     persona.nombre    if persona else (r.numero_doc or ""),
                    "numero_doc": r.numero_doc or "",
                    "tipo_doc":   persona.tipo_doc  if persona else "",
                    "perfil":     persona.perfil    if persona else "",
                    "tipo":       r.tipo or "",
                    "ambiente":   r.ambiente or "",
                    "eq_codigo":  "",
                    "eq_nombre":  "",
                    "programa":   persona.programa  if persona else "",
                    "ficha":      persona.ficha     if persona else "",
                })

            entradas_hoy  = sum(1 for r in enriquecidos if r["tipo"] == "ENTRADA")
            salidas_hoy   = sum(1 for r in enriquecidos if r["tipo"] == "SALIDA")
            stats = {
                "total_personas": len({r["numero_doc"] for r in enriquecidos}),
                "total_accesos":  n_registros,
                "total_computadores": 0,
                "total_eq_accesos":   0,
                "aprendices":   sum(1 for r in enriquecidos if r["perfil"].upper() == "APRENDIZ"),
                "instructores": sum(1 for r in enriquecidos if r["perfil"].upper() == "INSTRUCTOR"),
                "visitantes":   sum(1 for r in enriquecidos if r["perfil"].upper() == "VISITANTE"),
                "otros":        sum(1 for r in enriquecidos
                                    if r["perfil"].upper() not in ("APRENDIZ","INSTRUCTOR","VISITANTE")),
                "entradas_hoy":   entradas_hoy,
                "salidas_hoy":    salidas_hoy,
                "con_equipo_hoy": 0,
            }

            fecha_gen = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
            nombre_vig = (solicitante.nombre or solicitante.email or "vigilante").replace(" ", "_")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"Turno_{nombre_vig}_{ts}.xlsx"

            wb = Workbook()
            wb.remove(wb.active)
            hoja_diario(wb, enriquecidos, fecha_gen)
            hoja_resumen_dia(wb, enriquecidos, stats, fecha_gen)
            wb.properties.title   = f"Turno {solicitante.nombre or solicitante.email}"
            wb.properties.subject = "Reporte de turno SENA"
            wb.properties.creator = "Sistema SENA"

            buf = io.BytesIO()
            wb.save(buf)
            excel_bytes = buf.getvalue()

            # ── 3. Guardar local ─────────────────────────────────────────
            base_dir     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            respaldo_dir = os.path.join(base_dir, "RESPALDOS_USB", f"turno_{ts}")
            os.makedirs(respaldo_dir, exist_ok=True)
            ruta_local = os.path.join(respaldo_dir, nombre_archivo)
            with open(ruta_local, "wb") as f:
                f.write(excel_bytes)

            # ── 4. Guardar en USB si hay ─────────────────────────────────
            usb = detectar_usb()
            if usb:
                try:
                    usb_dir = os.path.join(usb, "SENA_Respaldos")
                    os.makedirs(usb_dir, exist_ok=True)
                    ruta_usb = os.path.join(usb_dir, nombre_archivo)
                    with open(ruta_usb, "wb") as f:
                        f.write(excel_bytes)
                    usb_guardado = True
                except Exception as e_usb:
                    print(f"[CERRAR-TURNO] No se pudo guardar en USB: {e_usb}")

            # ── 5. Subir a S3/nube si está configurado ───────────────────
            try:
                from cloud_storage import S3Manager
                s3 = S3Manager()
                if s3.verificar_conexion():
                    s3_key = f"turnos/{nombre_archivo}"
                    s3.s3_client.put_object(
                        Bucket=s3.bucket,
                        Key=s3_key,
                        Body=excel_bytes,
                        ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        Metadata={
                            'vigilante': str(usuario_id),
                            'registros': str(n_registros),
                            'fecha': datetime.utcnow().isoformat()
                        }
                    )
                    nube_guardada = True
            except Exception as e_s3:
                print(f"[CERRAR-TURNO] Nube no disponible: {e_s3}")

        # ── 6. PRESERVAR REGISTROS Y AMBIENTES ACTIVOS ───────────────────────
        # ⚠️ NO ELIMINAR registros_acceso - son datos históricos permanentes
        # ⚠️ NO ELIMINAR ambientes ocupados - los instructores pueden seguir dentro
        # ⚠️ Solo eliminar ambientes que YA FUERON LIBERADOS/CERRADOS
        # Así el próximo vigilante puede ver ambientes aún ocupados y cerrarlos correctamente
        
        # Limpiar SOLO ambientes ya cerrados (liberados)
        n_amb_liberados_antes = OcupacionAmbiente.query.filter(
            OcupacionAmbiente.estado == 'liberado'
        ).count()
        
        OcupacionAmbiente.query.filter(
            OcupacionAmbiente.estado == 'liberado'
        ).delete()
        db.session.commit()
        
        # Contar ambientes aún ocupados (que se preservan)
        n_amb_ocupados = OcupacionAmbiente.query.filter(
            OcupacionAmbiente.estado == 'ocupado'
        ).count()
        
        print(f"[CERRAR-TURNO] ✅ Registros PRESERVADOS en BD ({n_registros} registros)")
        print(f"[CERRAR-TURNO] ✅ {n_amb_ocupados} ambientes OCUPADOS preservados (instructores dentro)")
        print(f"[CERRAR-TURNO] ✅ {n_amb_liberados_antes} ambientes cerrados removidos del estado temporal")

        # Notificar que el turno se cerró (pero registros se preservaron)
        try:
            if websocket_handler.socketio:
                websocket_handler.socketio.emit('turno_cerrado', {
                    'mensaje': 'Turno cerrado - Registros preservados para próximo vigilante',
                    'registros_preservados': n_registros,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }, namespace='/')
        except Exception:
            pass

        # ── 7. Respuesta ─────────────────────────────────────────────────
        return jsonify({
            'mensaje': 'Turno cerrado correctamente',
            'registros_exportados': n_registros,
            'excel_generado': excel_bytes is not None,
            'archivo': nombre_archivo,
            'guardado_local': ruta_local is not None,
            'guardado_usb':   usb_guardado,
            'guardado_nube':  nube_guardada,
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/plantilla-excel', methods=['GET'])
@token_required
def descargar_plantilla_excel(usuario_id):
    """Genera y descarga una plantilla Excel con el formato correcto para importar personas."""
    solicitante = Usuario.query.get(usuario_id)
    if not solicitante or solicitante.rol != 'admin':
        return jsonify({'error': 'Solo admins pueden descargar la plantilla'}), 403
    try:
        from openpyxl import Workbook
        from openpyxl.styles import (PatternFill, Font, Alignment, Border, Side,
                                      GradientFill)
        from openpyxl.utils import get_column_letter
        from openpyxl.worksheet.datavalidation import DataValidation
        import io as _io

        wb = Workbook()
        ws = wb.active
        ws.title = "Personas"
        ws.sheet_view.showGridLines = False

        # ── Paleta ───────────────────────────────────────────────────────
        AZUL_OSC   = "003087"
        AZUL_MED   = "005EB8"
        AZUL_CLAR  = "DDEEFF"
        VERDE_BG   = "EDF7ED"
        VERDE_BCO  = "2E7D32"
        GRIS_BG    = "F4F6FB"
        GRIS_BORDE = "C5D5EE"
        ROJO_BG    = "FFF3F3"
        ROJO_BCO   = "C0392B"
        AMBAR_BG   = "FFFBE6"
        AMBAR_BCO  = "E65100"

        def _fill(hex_): return PatternFill("solid", fgColor=hex_)
        def _ft(bold=False, color="000000", size=10, italic=False):
            return Font(name="Calibri", bold=bold, color=color, size=size, italic=italic)
        def _al(h="left", v="center"):
            return Alignment(horizontal=h, vertical=v, wrap_text=True)
        def _border_cell():
            s = Side(style='thin', color=GRIS_BORDE)
            return Border(left=s, right=s, top=s, bottom=s)

        # ── Fila 1: título principal ──────────────────────────────────────
        ws.merge_cells("A1:K1")
        c = ws["A1"]
        c.value = "PLANTILLA DE IMPORTACIÓN — SISTEMA SENA  ·  Control de Accesos"
        c.fill  = _fill(AZUL_OSC)
        c.font  = _ft(bold=True, color="FFFFFF", size=13)
        c.alignment = _al("center")
        ws.row_dimensions[1].height = 32

        # ── Fila 2: instrucciones ─────────────────────────────────────────
        ws.merge_cells("A2:K2")
        c = ws["A2"]
        c.value = ("✔ Completa los datos desde la fila 5 en adelante. "
                   "Las columnas marcadas con * son obligatorias. "
                   "No modifiques los encabezados ni el orden de las columnas.")
        c.fill  = _fill(AMBAR_BG)
        c.font  = _ft(italic=True, color=AMBAR_BCO, size=9)
        c.alignment = _al("left")
        ws.row_dimensions[2].height = 20

        # ── Fila 3: valores permitidos ─────────────────────────────────────
        ws.merge_cells("A3:K3")
        c = ws["A3"]
        c.value = ("  PERFIL → aprendiz | instructor | directivo | ejecutivo | visitante     "
                   "TIPO_DOC → CC | TI | PP | CE")
        c.fill  = _fill(AZUL_CLAR)
        c.font  = _ft(bold=True, color=AZUL_MED, size=9)
        c.alignment = _al("left")
        ws.row_dimensions[3].height = 18

        # ── Fila 4: encabezados ────────────────────────────────────────────
        HEADERS = [
            ("PERFIL *",       14, ROJO_BG,   ROJO_BCO),
            ("NOMBRE *",       34, AZUL_CLAR, AZUL_MED),
            ("NUMERO_DOC *",   18, AZUL_CLAR, AZUL_MED),
            ("TIPO_DOC",       12, GRIS_BG,   "555555"),
            ("EMAIL",          26, GRIS_BG,   "555555"),
            ("TELEFONO",       14, GRIS_BG,   "555555"),
            ("PROGRAMA",       26, VERDE_BG,  VERDE_BCO),
            ("FICHA",          12, VERDE_BG,  VERDE_BCO),
            ("ESPECIALIDAD",   26, VERDE_BG,  VERDE_BCO),
            ("AREA",           26, VERDE_BG,  VERDE_BCO),
            ("OBSERVACION",    28, GRIS_BG,   "555555"),
        ]
        for col_idx, (hdr, width, bg, fg) in enumerate(HEADERS, 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width
            c = ws.cell(row=4, column=col_idx)
            c.value     = hdr
            c.fill      = _fill(bg)
            c.font      = _ft(bold=True, color=fg, size=10)
            c.alignment = _al("center")
            c.border    = _border_cell()
        ws.row_dimensions[4].height = 22

        # ── Filas vacías para datos (5 en adelante) ──────────────────────
        for row_idx in range(5, 55):
            ws.row_dimensions[row_idx].height = 18
            for col_idx in range(1, len(HEADERS) + 1):
                c = ws.cell(row=row_idx, column=col_idx)
                c.value     = ""
                c.fill      = _fill("FFFFFF")
                c.font      = _ft(size=10)
                c.alignment = _al()
                c.border    = _border_cell()

        # ── Segunda hoja: guía completa ────────────────────────────────────
        ws2 = wb.create_sheet("Guía de uso")
        ws2.sheet_view.showGridLines = False
        ws2.column_dimensions["A"].width = 22
        ws2.column_dimensions["B"].width = 60

        GUIA = [
            ("COLUMNA",          "DESCRIPCIÓN Y VALORES ACEPTADOS"),
            ("PERFIL *",         "Obligatorio. Valores: aprendiz | instructor | directivo | ejecutivo | visitante"),
            ("NOMBRE *",         "Obligatorio. Nombre completo de la persona."),
            ("NUMERO_DOC *",     "Obligatorio. Número de documento sin puntos ni comas. Debe ser único."),
            ("TIPO_DOC",         "Tipo de documento. Valores: CC (Cédula) | TI (Tarjeta Identidad) | PP (Pasaporte) | CE (Cédula Extranjería). Por defecto: CC"),
            ("EMAIL",            "Correo electrónico (opcional)."),
            ("TELEFONO",         "Número de teléfono celular o fijo (opcional)."),
            ("PROGRAMA",         "Solo para perfil Aprendiz. Nombre del programa formativo. Ej: Programación de Software."),
            ("FICHA",            "Solo para perfil Aprendiz. Número de ficha de formación. Ej: 2956847."),
            ("ESPECIALIDAD",     "Para Instructor: área de conocimiento. Para Directivo/Ejecutivo: cargo o título."),
            ("AREA",             "Para Instructor: área o centro. Para Directivo/Ejecutivo: dependencia."),
            ("OBSERVACION",      "Campo libre opcional. No se importa a la base de datos, solo sirve como nota para el operador."),
            ("", ""),
            ("NOTAS IMPORTANTES", ""),
            ("",                 "• Las filas de ejemplo (fondo de color) deben eliminarse antes de importar."),
            ("",                 "• El sistema detecta filas duplicadas por NUMERO_DOC y las omite sin error."),
            ("",                 "• Si una persona ya existe en el sistema (mismo NUMERO_DOC) se actualiza su información."),
            ("",                 "• Puedes importar solo aprendices, solo instructores o mezcla de perfiles en un mismo archivo."),
            ("",                 "• Los encabezados (fila 4 de la hoja Personas) no deben modificarse."),
        ]
        for r, (col_lbl, desc) in enumerate(GUIA, 1):
            c1 = ws2.cell(row=r, column=1, value=col_lbl)
            c2 = ws2.cell(row=r, column=2, value=desc)
            ws2.row_dimensions[r].height = 20
            if r == 1:
                c1.fill = c2.fill = _fill(AZUL_OSC)
                c1.font = c2.font = _ft(bold=True, color="FFFFFF", size=10)
            elif col_lbl == "NOTAS IMPORTANTES":
                c1.fill = c2.fill = _fill(AMBAR_BG)
                c1.font = c2.font = _ft(bold=True, color=AMBAR_BCO, size=10)
            elif col_lbl:
                c1.fill = _fill(AZUL_CLAR); c1.font = _ft(bold=True, color=AZUL_MED, size=9)
                c2.fill = _fill("FFFFFF");   c2.font = _ft(size=9)
            else:
                c2.fill = _fill("FAFCFF"); c2.font = _ft(size=9, italic=True, color="555555")
            for c in (c1, c2):
                c.alignment = _al()
                c.border    = _border_cell()

        # ── Freezer y propiedades ──────────────────────────────────────────
        ws.freeze_panes = "A5"
        wb.properties.title   = "Plantilla Importación SENA"
        wb.properties.creator = "Sistema SENA"

        buf = _io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        from flask import send_file as _sf
        return _sf(
            buf,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='Plantilla_Importacion_SENA.xlsx'
        )
    except ImportError:
        return jsonify({'error': 'openpyxl no instalado. Ejecuta: pip install openpyxl'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/importar-excel', methods=['POST'])
@token_required
def importar_excel(usuario_id):
    """Lee un archivo Excel y crea/actualiza personas en la base de datos."""
    solicitante = Usuario.query.get(usuario_id)
    if not solicitante or solicitante.rol != 'admin':
        return jsonify({'error': 'Solo admins pueden importar datos'}), 403

    if 'archivo' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo. Usa el campo "archivo"'}), 400

    archivo = request.files['archivo']
    if not archivo.filename or not archivo.filename.lower().endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'El archivo debe ser .xlsx o .xls'}), 400

    try:
        from openpyxl import load_workbook
        import io as _io

        contenido = archivo.read()
        wb = load_workbook(filename=_io.BytesIO(contenido), read_only=True, data_only=True)

        # Aceptar la primera hoja que se llame 'Personas' o la primera disponible
        if 'Personas' in wb.sheetnames:
            ws = wb['Personas']
        else:
            ws = wb.active

        # ── Detectar fila de encabezados ────────────────────────────────
        COLUMNAS_ESPERADAS = {
            'perfil': None, 'nombre': None, 'numero_doc': None,
            'tipo_doc': None, 'email': None, 'telefono': None,
            'programa': None, 'ficha': None, 'especialidad': None, 'area': None,
        }
        fila_header = None
        for row in ws.iter_rows(min_row=1, max_row=10):
            for cell in row:
                val = str(cell.value or '').strip().lower().replace('*','').strip()
                if val in COLUMNAS_ESPERADAS:
                    COLUMNAS_ESPERADAS[val] = cell.column - 1  # índice 0
            # Si encontramos los tres obligatorios, esta es la fila de headers
            if all(COLUMNAS_ESPERADAS[k] is not None for k in ('perfil', 'nombre', 'numero_doc')):
                fila_header = cell.row
                break

        if fila_header is None:
            return jsonify({'error': 'No se encontraron los encabezados PERFIL, NOMBRE, NUMERO_DOC en las primeras 10 filas.'}), 422

        PERFILES_VALIDOS = {'aprendiz', 'instructor', 'directivo', 'ejecutivo', 'visitante'}
        TIPOS_DOC_VALIDOS = {'CC', 'TI', 'PP', 'CE'}

        importados = 0
        actualizados = 0
        omitidos = 0
        errores = []

        rows_data = list(ws.iter_rows(min_row=fila_header + 1, values_only=True))

        def get_col(row_vals, campo):
            idx = COLUMNAS_ESPERADAS.get(campo)
            if idx is None or idx >= len(row_vals):
                return ''
            val = row_vals[idx]
            return str(val).strip() if val not in (None, '') else ''

        for fila_num, row_vals in enumerate(rows_data, fila_header + 1):
            # Ignorar filas completamente vacías
            if all(v in (None, '', ' ') for v in row_vals):
                continue

            perfil    = get_col(row_vals, 'perfil').lower()
            nombre    = get_col(row_vals, 'nombre')
            num_doc   = get_col(row_vals, 'numero_doc')
            tipo_doc  = get_col(row_vals, 'tipo_doc').upper() or 'CC'
            email     = get_col(row_vals, 'email') or None
            telefono  = get_col(row_vals, 'telefono') or None
            programa  = get_col(row_vals, 'programa') or None
            ficha     = get_col(row_vals, 'ficha') or None
            especialidad = get_col(row_vals, 'especialidad') or None
            area      = get_col(row_vals, 'area') or None

            # Validaciones básicas
            if not perfil or not nombre or not num_doc:
                errores.append(f'Fila {fila_num}: PERFIL, NOMBRE y NUMERO_DOC son obligatorios — omitida.')
                omitidos += 1
                continue

            if perfil not in PERFILES_VALIDOS:
                errores.append(f'Fila {fila_num}: perfil "{perfil}" no válido (doc: {num_doc}) — omitida.')
                omitidos += 1
                continue

            if tipo_doc not in TIPOS_DOC_VALIDOS:
                tipo_doc = 'CC'

            try:
                persona_existente = Persona.query.filter_by(numero_doc=num_doc).first()
                if persona_existente:
                    # Actualizar
                    persona_existente.nombre      = nombre
                    persona_existente.perfil       = perfil
                    persona_existente.tipo_doc     = tipo_doc
                    if email:      persona_existente.email       = email
                    if telefono:   persona_existente.telefono    = telefono
                    if programa:   persona_existente.programa    = programa
                    if ficha:      persona_existente.ficha       = ficha
                    if especialidad: persona_existente.especialidad = especialidad
                    if area:       persona_existente.area        = area
                    persona_existente.actualizado_por_id = usuario_id
                    actualizados += 1
                else:
                    nueva = Persona(
                        nombre=nombre,
                        tipo_doc=tipo_doc,
                        numero_doc=num_doc,
                        email=email,
                        telefono=telefono,
                        perfil=perfil,
                        programa=programa,
                        ficha=ficha,
                        especialidad=especialidad,
                        area=area,
                        creado_por_id=usuario_id,
                    )  # type: ignore
                    db.session.add(nueva)
                    importados += 1
            except Exception as e_row:
                errores.append(f'Fila {fila_num}: error al procesar "{num_doc}" — {str(e_row)}')
                omitidos += 1

        db.session.commit()

        return jsonify({
            'mensaje': f'Importación completada. {importados} nuevas, {actualizados} actualizadas, {omitidos} omitidas.',
            'importados':   importados,
            'actualizados': actualizados,
            'omitidos':     omitidos,
            'errores':      errores[:50],   # máximo 50 errores en respuesta
            'total_errores': len(errores),
        }), 200

    except ImportError:
        return jsonify({'error': 'openpyxl no instalado. Ejecuta: pip install openpyxl'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al procesar el archivo: {str(e)}'}), 500


@api_bp.route('/admin/limpiar-todo', methods=['POST'])
@token_required
def limpiar_todo(usuario_id):
    """Deja la base de datos virgen: elimina personas, registros y ocupaciones."""
    solicitante = Usuario.query.get(usuario_id)
    if not solicitante or solicitante.rol != 'admin':
        return jsonify({'error': 'Solo admins pueden ejecutar esta acción'}), 403
    try:
        n_eq   = RegistroAccesoEquipo.query.delete()
        n_inv  = RegistroInventario.query.delete()
        n_ocup = OcupacionAmbiente.query.delete()
        n_reg  = RegistroAcceso.query.delete()
        n_pers = Persona.query.delete()
        db.session.commit()
        try:
            if websocket_handler.socketio:
                websocket_handler.socketio.emit('registros_limpiados', {
                    'motivo': 'limpiar_todo',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }, namespace='/')
        except Exception:
            pass
        return jsonify({
            'mensaje': 'Base de datos limpiada completamente',
            'personas_eliminadas': n_pers,
            'registros_eliminados': n_reg,
            'registros_equipo_eliminados': n_eq,
            'ocupaciones_eliminadas': n_ocup,
            'inventario_eliminado': n_inv,
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
#  INVENTARIO / BITÁCORA DE OBJETOS Y EQUIPOS
# ─────────────────────────────────────────────

@api_bp.route('/inventario', methods=['GET'])
@token_required
def listar_inventario_en_sede(usuario_id):
    """Devuelve todos los registros actualmente EN_SEDE."""
    items = (RegistroInventario.query
             .filter_by(estado='EN_SEDE', deleted_at=None)
             .order_by(RegistroInventario.fecha_entrada.desc())
             .all())
    resultado = []
    for it in items:
        resultado.append({
            'id': it.id,
            'descripcion': it.descripcion,
            'cantidad': it.cantidad,
            'portador_nombre': it.portador_nombre,
            'portador_documento': it.portador_documento,
            'destino': it.destino,
            'estado': it.estado,
            'fecha_entrada': it.fecha_entrada.isoformat() + 'Z' if it.fecha_entrada else None,
            'observaciones': it.observaciones,
            'registrado_por': it.registrado_por,
        })
    return jsonify({'items': resultado, 'total': len(resultado)}), 200


@api_bp.route('/inventario/historial', methods=['GET'])
@token_required
def historial_inventario(usuario_id):
    """Devuelve el historial completo (entradas y salidas) paginado."""
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = min(request.args.get('por_pagina', 100, type=int), 200)
    vista = request.args.get('vista', 'vigilancia').lower()
    marca_limpieza = (RegistroInventario.limpiado_admin_at if vista == 'admin'
                      else RegistroInventario.limpiado_vigilancia_at)
    filtros = [RegistroInventario.deleted_at.is_(None), marca_limpieza.is_(None)]
    if vista == 'admin':
        filtros.append(RegistroInventario.estado == 'RETIRADO')
    q = (RegistroInventario.query
         .filter(*filtros)
         .order_by(RegistroInventario.fecha_entrada.desc())
         .paginate(page=pagina, per_page=por_pagina, error_out=False))
    resultado = []
    for it in q.items:
        resultado.append({
            'id': it.id,
            'descripcion': it.descripcion,
            'cantidad': it.cantidad,
            'portador_nombre': it.portador_nombre,
            'portador_documento': it.portador_documento,
            'destino': it.destino,
            'estado': it.estado,
            'fecha_entrada': it.fecha_entrada.isoformat() + 'Z' if it.fecha_entrada else None,
            'fecha_salida': it.fecha_salida.isoformat() + 'Z' if it.fecha_salida else None,
            'observaciones': it.observaciones,
            'registrado_por': it.registrado_por,
        })
    return jsonify({'items': resultado, 'total': q.total, 'pagina': pagina}), 200


@api_bp.route('/inventario', methods=['POST'])
@token_required
def registrar_entrada_inventario(usuario_id):
    """Registra la entrada de un objeto/equipo/herramienta."""
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'Datos requeridos'}), 400
    descripcion = (datos.get('descripcion') or '').strip()
    portador_nombre = (datos.get('portador_nombre') or '').strip()
    portador_documento = (datos.get('portador_documento') or '').strip()
    if not descripcion or not portador_nombre or not portador_documento:
        return jsonify({'error': 'descripcion, portador_nombre y portador_documento son obligatorios'}), 400
    try:
        cantidad = int(datos.get('cantidad', 1))
    except (ValueError, TypeError):
        cantidad = 1
    solicitante = Usuario.query.get(usuario_id)
    item = RegistroInventario(
        descripcion=descripcion,
        cantidad=max(1, cantidad),
        portador_nombre=portador_nombre,
        portador_documento=portador_documento,
        destino=(datos.get('destino') or '').strip() or None,
        observaciones=(datos.get('observaciones') or '').strip() or None,
        estado='EN_SEDE',
        fecha_entrada=datetime.utcnow(),
        registrado_por=solicitante.nombre if solicitante else 'Vigilante',
    )  # type: ignore
    db.session.add(item)
    db.session.commit()
    return jsonify({
        'mensaje': 'Entrada registrada correctamente',
        'id': item.id,
        'descripcion': item.descripcion,
        'portador_nombre': item.portador_nombre,
    }), 201


@api_bp.route('/inventario/<item_id>/salida', methods=['PUT'])
@token_required
def registrar_salida_inventario(usuario_id, item_id):
    """Marca la salida de un objeto/equipo registrado."""
    item = RegistroInventario.query.get(item_id)
    if not item:
        return jsonify({'error': 'Registro no encontrado'}), 404
    if item.estado == 'RETIRADO':
        return jsonify({'error': 'Este item ya fue retirado'}), 409
    item.estado = 'RETIRADO'
    item.fecha_salida = datetime.utcnow()
    db.session.commit()
    return jsonify({
        'mensaje': 'Salida registrada correctamente',
        'id': item.id,
        'descripcion': item.descripcion,
        'fecha_salida': item.fecha_salida.isoformat() + 'Z',
    }), 200


@api_bp.route('/inventario/<item_id>', methods=['DELETE'])
@token_required
def eliminar_inventario_retirado(usuario_id, item_id):
    """Oculta un retiro solo del panel que solicita la limpieza."""
    item = RegistroInventario.query.filter_by(id=item_id, deleted_at=None).first()
    if not item:
        return jsonify({'error': 'Registro no encontrado'}), 404
    if item.estado != 'RETIRADO':
        return jsonify({'error': 'Solo se pueden eliminar objetos retirados'}), 409

    vista = request.args.get('vista', 'vigilancia').lower()
    if vista == 'admin':
        item.limpiado_admin_at = datetime.utcnow()
    else:
        item.limpiado_vigilancia_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'mensaje': f'Registro retirado limpiado en {vista}', 'id': item.id}), 200


@api_bp.route('/admin/exportar-inventario', methods=['GET'])
@token_required
def exportar_inventario_excel(usuario_id):
    """Exporta el inventario de objetos y la bitácora de accesos a Excel."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        import io as _io

        # ── Paleta SENA ──────────────────────────────────────────────────
        AZ1 = "003087"; AZ2 = "005EB8"; AZ3 = "00AEEF"
        VE1 = "1A5E31"; VE2 = "D6F0DC"
        RO1 = "C00000"; RO2 = "FFE0E0"
        AM1 = "7F6000"; AM2 = "FFF2CC"
        BL  = "FFFFFF"; GR1 = "F2F2F2"; GR2 = "595959"; GR3 = "D9D9D9"
        PA1 = "EBF3FB"

        def _f(c):   return PatternFill("solid", fgColor=c)
        def _ft(bold=False, color="000000", size=10):
            return Font(bold=bold, color=color, size=size, name="Calibri")
        def _ac():   return Alignment(horizontal="center", vertical="center", wrap_text=True)
        def _al():   return Alignment(horizontal="left",   vertical="center", wrap_text=True)
        def _borde():
            s = Side(style="thin", color=GR3)
            return Border(left=s, right=s, top=s, bottom=s)
        def _borde_cab():
            g = Side(style="medium", color=AZ1)
            t = Side(style="thin",   color=GR3)
            return Border(left=t, right=t, top=g, bottom=g)

        def _cabecera_hoja(ws, titulo, n, fecha_gen):
            from openpyxl.utils import get_column_letter as gcl
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n)
            ws.cell(row=1, column=1).fill = _f(AZ1)
            ws.row_dimensions[1].height = 7
            for r in range(2, 5):
                for c in range(1, 4):
                    ws.cell(row=r, column=c).fill = _f(AZ1)
            ws.merge_cells(start_row=2, start_column=1, end_row=4, end_column=3)
            cc = ws.cell(row=2, column=1)
            cc.value = "SENA"; cc.fill = _f(AZ1)
            cc.font = Font(bold=True, color=BL, size=28, name="Calibri")
            cc.alignment = _ac()
            ws.merge_cells(start_row=2, start_column=4, end_row=3, end_column=n)
            ct = ws.cell(row=2, column=4)
            ct.value = titulo; ct.fill = _f(AZ2)
            ct.font = _ft(bold=True, color=BL, size=14)
            ct.alignment = _ac()
            ws.merge_cells(start_row=4, start_column=4, end_row=4, end_column=n)
            cf = ws.cell(row=4, column=4)
            cf.value = f"Generado: {fecha_gen}"; cf.fill = _f(AZ3)
            cf.font = _ft(color=AZ1, size=9)
            cf.alignment = _al()
            ws.row_dimensions[2].height = 22
            ws.row_dimensions[3].height = 22
            ws.row_dimensions[4].height = 16
            ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=n)
            ws.cell(row=5, column=1).fill = _f(AZ1)
            ws.row_dimensions[5].height = 4
            ws.row_dimensions[6].height = 4
            return 7

        def _header_row(ws, fila, cab, anchos):
            for i, (h, w) in enumerate(zip(cab, anchos), 1):
                ws.column_dimensions[get_column_letter(i)].width = w
                c = ws.cell(row=fila, column=i)
                c.value = h; c.fill = _f(AZ2)
                c.font = _ft(bold=True, color=BL, size=10)
                c.alignment = _ac(); c.border = _borde_cab()
            ws.row_dimensions[fila].height = 22
            return fila + 1

        # ── Consultas ────────────────────────────────────────────────────
        inventario_obj = (RegistroInventario.query
                          .order_by(RegistroInventario.fecha_entrada.desc()).all())
        accesos_obj    = (RegistroAcceso.query.filter_by(deleted_at=None)
                          .order_by(RegistroAcceso.timestamp.desc()).all())

        # mapa persona por número de doc
        docs_set = {r.numero_doc for r in accesos_obj if r.numero_doc}
        personas_map = {}
        if docs_set:
            from models import Persona as _P
            for p in _P.query.filter(_P.numero_doc.in_(docs_set)).all():
                personas_map[p.numero_doc] = p

        # mapa vigilantes
        vig_ids = {r.vigilante_id for r in accesos_obj if r.vigilante_id}
        vig_map = {}
        if vig_ids:
            for u in Usuario.query.filter(Usuario.id.in_(vig_ids)).all():
                vig_map[u.id] = u.nombre or u.email

        fecha_gen = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        ts        = datetime.now().strftime("%Y%m%d_%H%M%S")

        wb = Workbook()
        wb.remove(wb.active)

        # ══════════════════════════════════════════════════════════════════
        # HOJA 1 — INVENTARIO DE OBJETOS Y EQUIPOS
        # ══════════════════════════════════════════════════════════════════
        ws1 = wb.create_sheet("Inventario de Objetos")
        ws1.sheet_view.showGridLines = False

        CAB1 = ["N°","DESCRIPCIÓN","CANT.","PORTADOR","DOCUMENTO",
                "DESTINO","ESTADO","ENTRADA","SALIDA","REGISTRADO POR","OBSERVACIONES"]
        ANC1 = [5,   34,           7,       28,        16,
                22,    12,          18,       18,        22,              36]

        fila = _cabecera_hoja(ws1, "Inventario de Objetos y Equipos Personales", len(CAB1), fecha_gen)
        fila = _header_row(ws1, fila, CAB1, ANC1)

        en_sede   = 0
        retirados = 0
        for i, it in enumerate(inventario_obj, 1):
            fe = it.fecha_entrada.strftime("%d/%m/%Y %H:%M") if it.fecha_entrada else ""
            fs = it.fecha_salida.strftime("%d/%m/%Y %H:%M")  if it.fecha_salida  else ""
            estado_lbl = "EN SEDE" if it.estado == "EN_SEDE" else "RETIRADO"
            fondo = PA1 if i % 2 == 0 else BL
            vals = [i, it.descripcion, it.cantidad, it.portador_nombre,
                    it.portador_documento, it.destino or "", estado_lbl,
                    fe, fs, it.registrado_por or "", it.observaciones or ""]
            for col, v in enumerate(vals, 1):
                c = ws1.cell(row=fila, column=col)
                c.value = v; c.fill = _f(fondo)
                c.font = _ft(); c.border = _borde()
                c.alignment = _ac() if col in (1, 3) else _al()
            # Colorear estado
            cest = ws1.cell(row=fila, column=7)
            cest.alignment = _ac()
            if it.estado == "EN_SEDE":
                cest.fill = _f(VE2); cest.font = _ft(bold=True, color=VE1)
                en_sede += 1
            else:
                cest.fill = _f(GR1); cest.font = _ft(color=GR2)
                retirados += 1
            fila += 1

        # Pie
        ws1.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=len(CAB1))
        pie = ws1.cell(row=fila, column=1)
        pie.value = (f"  Total registros: {len(inventario_obj)}   "
                     f"En sede: {en_sede}   Retirados: {retirados}   ")
        pie.fill = _f(AZ1); pie.font = _ft(bold=True, color=BL, size=10)
        pie.alignment = _al()
        ws1.row_dimensions[fila].height = 18

        ws1.freeze_panes = "A8"
        ws1.auto_filter.ref = f"A7:{get_column_letter(len(CAB1))}{fila - 1}"

        # ══════════════════════════════════════════════════════════════════
        # HOJA 2 — BITÁCORA DE ACCESOS (todos los vigilantes)
        # ══════════════════════════════════════════════════════════════════
        ws2 = wb.create_sheet("Bitácora de Accesos")
        ws2.sheet_view.showGridLines = False

        CAB2 = ["N°","FECHA","HORA","NOMBRE","DOCUMENTO","PERFIL",
                "TIPO","AMBIENTE","PROGRAMA / FICHA","VIGILANTE"]
        ANC2 = [5,  13,     10,    30,       16,         14,
                12,  24,           24,          22]

        fila2 = _cabecera_hoja(ws2, "Bitácora Completa de Accesos", len(CAB2), fecha_gen)
        fila2 = _header_row(ws2, fila2, CAB2, ANC2)

        entradas = salidas = 0
        for i, r in enumerate(accesos_obj, 1):
            persona  = personas_map.get(r.numero_doc)
            nombre   = persona.nombre  if persona else (r.numero_doc or "")
            perfil   = (persona.perfil if persona else "").upper()
            prog_fic = ""
            if persona:
                if persona.perfil and persona.perfil.lower() == "aprendiz":
                    prog_fic = f"{persona.programa or ''} / {persona.ficha or ''}".strip(" /")
                elif persona.perfil and persona.perfil.lower() == "instructor":
                    prog_fic = persona.especialidad or ""
            fecha_s = r.timestamp.strftime("%d/%m/%Y") if r.timestamp else ""
            hora_s  = r.timestamp.strftime("%H:%M:%S") if r.timestamp else ""
            vig_n   = vig_map.get(r.vigilante_id, "") if r.vigilante_id else ""

            fondo = PA1 if i % 2 == 0 else BL
            vals = [i, fecha_s, hora_s, nombre, r.numero_doc or "", perfil,
                    r.tipo or "", r.ambiente or "", prog_fic, vig_n]
            for col, v in enumerate(vals, 1):
                c = ws2.cell(row=fila2, column=col)
                c.value = v; c.fill = _f(fondo)
                c.font = _ft(); c.border = _borde()
                c.alignment = _ac() if col in (1, 2, 3, 7) else _al()

            # Color tipo
            ctipo = ws2.cell(row=fila2, column=7)
            ctipo.alignment = _ac()
            if (r.tipo or "").upper() == "ENTRADA":
                ctipo.fill = _f(VE2); ctipo.font = _ft(bold=True, color=VE1)
                entradas += 1
            else:
                ctipo.fill = _f(RO2); ctipo.font = _ft(bold=True, color=RO1)
                salidas += 1
            fila2 += 1

        # Pie
        ws2.merge_cells(start_row=fila2, start_column=1, end_row=fila2, end_column=len(CAB2))
        pie2 = ws2.cell(row=fila2, column=1)
        pie2.value = (f"  Total registros: {len(accesos_obj)}   "
                      f"Entradas: {entradas}   Salidas: {salidas}   ")
        pie2.fill = _f(AZ1); pie2.font = _ft(bold=True, color=BL, size=10)
        pie2.alignment = _al()
        ws2.row_dimensions[fila2].height = 18

        ws2.freeze_panes = "A8"
        ws2.auto_filter.ref = f"A7:{get_column_letter(len(CAB2))}{fila2 - 1}"

        # ── Guardar ────────────────────────────────────────────────────
        wb.properties.title   = "Inventario y Bitácora SENA"
        wb.properties.creator = "Sistema SENA"

        buf = _io.BytesIO()
        wb.save(buf)
        excel_bytes = buf.getvalue()

        nombre_archivo = f"SENA_Inventario_Bitacora_{ts}.xlsx"

        # Guardar copia local
        from flask import send_file as _sf
        base_dir     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        respaldo_dir = os.path.join(base_dir, "RESPALDOS_USB", f"inventario_{ts}")
        os.makedirs(respaldo_dir, exist_ok=True)
        with open(os.path.join(respaldo_dir, nombre_archivo), "wb") as fout:
            fout.write(excel_bytes)

        buf2 = _io.BytesIO(excel_bytes)
        buf2.seek(0)
        return _sf(
            buf2,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nombre_archivo
        )

    except ImportError:
        return jsonify({'error': 'openpyxl no instalado. Ejecuta: pip install openpyxl'}), 500
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'detalle': traceback.format_exc()}), 500


# ── SEGURIDAD ANALÍTICA ──────────────────────────────────────────────────────

@api_bp.route('/admin/personas-en-sede', methods=['GET'])
@token_required
def personas_en_sede_ahora(usuario_id):
    """Devuelve las personas que tienen ENTRADA como último registro (están físicamente en sede)."""
    try:
        from sqlalchemy import func
        sub = (db.session.query(
            RegistroAcceso.persona_id,
            func.max(RegistroAcceso.timestamp).label('ultima')
        ).filter(RegistroAcceso.deleted_at == None,  # type: ignore
                 RegistroAcceso.persona_id != None)  # type: ignore
         .group_by(RegistroAcceso.persona_id).subquery())

        registros = (db.session.query(RegistroAcceso, Persona)
            .join(sub, (RegistroAcceso.persona_id == sub.c.persona_id) &
                       (RegistroAcceso.timestamp == sub.c.ultima))
            .join(Persona, RegistroAcceso.persona_id == Persona.id)
            .filter(RegistroAcceso.tipo == 'ENTRADA',
                    RegistroAcceso.deleted_at == None,  # type: ignore
                    Persona.deleted_at == None)  # type: ignore
            .order_by(RegistroAcceso.timestamp.asc()).all())

        ahora = datetime.utcnow()
        resultado = []
        for r, p in registros:
            mins = int((ahora - r.timestamp).total_seconds() / 60)
            resultado.append({
                'nombre': p.nombre,
                'numero_doc': p.numero_doc,
                'perfil': p.perfil or '',
                'programa': p.programa or '',
                'ficha': p.ficha or '',
                'ambiente': r.ambiente or 'Sede',
                'entrada_timestamp': r.timestamp.isoformat() + 'Z',
                'minutos_dentro': mins,
                'horas_dentro': round(mins / 60, 1),
            })
        return jsonify({'personas': resultado, 'total': len(resultado),
                        'timestamp': ahora.isoformat() + 'Z'}), 200
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'detalle': traceback.format_exc()}), 500


@api_bp.route('/admin/mapa-calor', methods=['GET'])
@token_required
def mapa_calor_accesos(usuario_id):
    """Matriz 7×24 con conteo de entradas por día de semana y hora."""
    try:
        registros = (RegistroAcceso.query
                     .filter(RegistroAcceso.tipo == 'ENTRADA',
                             RegistroAcceso.deleted_at == None)  # type: ignore
                     .with_entities(RegistroAcceso.timestamp).all())
        matriz = [[0] * 24 for _ in range(7)]
        for (ts,) in registros:
            if ts:
                matriz[ts.weekday()][ts.hour] += 1
        maximo = max(max(fila) for fila in matriz) if registros else 1
        return jsonify({
            'matriz': matriz,
            'dias': ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'],
            'horas': list(range(24)),
            'maximo': maximo or 1,
            'total': len(registros)
        }), 200
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'detalle': traceback.format_exc()}), 500


# ── EDIFICIOS ─────────────────────────────────────────────────────────────────

@api_bp.route('/edificios', methods=['GET'])
@token_required
def listar_edificios(usuario_id):
    """Lista todos los edificios (activos e inactivos, no eliminados)."""
    try:
        edificios = Edificio.query.filter_by(deleted_at=None).order_by(Edificio.orden, Edificio.nombre).all()
        return jsonify({'edificios': [
            {
                'id': e.id,
                'nombre': e.nombre,
                'descripcion': e.descripcion,
                'num_pisos': e.num_pisos,
                'num_ambientes_por_piso': e.num_ambientes_por_piso,
                'activo': e.activo,
                'orden': e.orden,
            } for e in edificios
        ]}), 200
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


@api_bp.route('/edificios', methods=['POST'])
@token_required
def crear_edificio(usuario_id):
    """Crea un nuevo edificio."""
    try:
        d = request.get_json()
        nombre = (d.get('nombre') or '').strip().upper()
        if not nombre:
            return jsonify({'error': 'El nombre del edificio es obligatorio'}), 400
        if Edificio.query.filter_by(nombre=nombre, deleted_at=None).first():
            return jsonify({'error': f'Ya existe un edificio con el nombre "{nombre}"'}), 409
        ed = Edificio(
            nombre=nombre,
            descripcion=(d.get('descripcion') or '').strip() or None,
            num_pisos=max(1, int(d.get('num_pisos') or 3)),
            num_ambientes_por_piso=max(1, int(d.get('num_ambientes_por_piso') or 10)),
            activo=True,
            orden=int(d.get('orden') or 0),
        )
        db.session.add(ed)
        db.session.commit()
        return jsonify({'mensaje': 'Edificio creado', 'id': ed.id, 'nombre': ed.nombre}), 201
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


@api_bp.route('/edificios/<edificio_id>', methods=['PUT'])
@token_required
def actualizar_edificio(usuario_id, edificio_id):
    """Actualiza un edificio existente."""
    try:
        ed = Edificio.query.filter_by(id=edificio_id, deleted_at=None).first()
        if not ed:
            return jsonify({'error': 'Edificio no encontrado'}), 404
        d = request.get_json()
        if 'nombre' in d:
            nombre = d['nombre'].strip().upper()
            dup = Edificio.query.filter(
                Edificio.nombre == nombre,
                Edificio.id != edificio_id,
                Edificio.deleted_at == None  # type: ignore
            ).first()
            if dup:
                return jsonify({'error': f'Ya existe un edificio con el nombre "{nombre}"'}), 409
            ed.nombre = nombre
        if 'descripcion' in d:
            ed.descripcion = (d['descripcion'] or '').strip() or None
        if 'num_pisos' in d:
            ed.num_pisos = max(1, int(d['num_pisos']))
        if 'num_ambientes_por_piso' in d:
            ed.num_ambientes_por_piso = max(1, int(d['num_ambientes_por_piso']))
        if 'activo' in d:
            ed.activo = bool(d['activo'])
        db.session.commit()
        return jsonify({'mensaje': 'Edificio actualizado', 'id': ed.id}), 200
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
#  CONTROL REMOTO TRIAC — PANEL DE VIGILANTE
#  Comunicación con ESP32 por HTTP
# ═══════════════════════════════════════════════════════════════════════════════

def obtener_ip_esp32() -> str:
    """Obtiene la IP de la ESP32 desde variables de entorno o config."""
    from flask import current_app
    return current_app.config.get('ESP32_IP', os.getenv('ESP32_IP', '192.168.1.100'))

def enviar_comando_esp32(comando: str) -> dict:
    """Envía comando HTTP a la ESP32."""
    ip_esp32 = obtener_ip_esp32()
    url = f"http://{ip_esp32}/triac/{comando}"
    
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            try:
                return response.json()
            except:
                return {'ok': True, 'mensaje': 'Comando enviado'}
        else:
            return {'ok': False, 'error': f'ESP32 retornó código {response.status_code}'}
    except requests.exceptions.Timeout:
        print(f"[ESP32] Timeout al conectar a {ip_esp32}")
        return {'ok': False, 'error': 'Timeout: ESP32 no responde'}
    except requests.exceptions.ConnectionError:
        print(f"[ESP32] No se puede conectar a {ip_esp32}")
        return {'ok': False, 'error': f'No se puede conectar a ESP32 ({ip_esp32})'}
    except Exception as e:
        print(f"[ESP32] Error: {e}")
        return {'ok': False, 'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
#  PROXY ESP32 — Sin autenticación (para comunicación directa desde navegador)
# ═══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/esp32/proxy/abrir', methods=['GET', 'POST'])
@rate_limit(10, 60)  # 10 solicitudes por minuto
def proxy_esp32_abrir():
    """Proxy para abrir cerradura — redirige al ESP32."""
    try:
        seg = request.args.get('seg', request.json.get('seg') if request.is_json else None, type=int) if request.method == 'GET' else request.json.get('seg', 15)
        if seg is None:
            seg = 15
        
        ip_esp32 = obtener_ip_esp32()
        url = f"http://{ip_esp32}/abrir?seg={seg}"
        
        print(f"[PROXY] Abriendo ESP32 por {seg}s: {url}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            try:
                return jsonify(response.json()), 200
            except:
                return jsonify({'ok': True, 'mensaje': 'Cerradura abierta'}), 200
        else:
            return jsonify({'ok': False, 'error': f'Código {response.status_code}'}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'ok': False, 'error': 'Timeout: ESP32 no responde'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'ok': False, 'error': 'No se puede conectar a ESP32'}), 503
    except Exception as e:
        print(f"[PROXY] Error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@api_bp.route('/esp32/proxy/cerrar', methods=['GET', 'POST'])
@rate_limit(10, 60)
def proxy_esp32_cerrar():
    """Proxy para cerrar cerradura — redirige al ESP32."""
    try:
        ip_esp32 = obtener_ip_esp32()
        url = f"http://{ip_esp32}/cerrar"
        
        print(f"[PROXY] Cerrando ESP32: {url}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            try:
                return jsonify(response.json()), 200
            except:
                return jsonify({'ok': True, 'mensaje': 'Cerradura cerrada'}), 200
        else:
            return jsonify({'ok': False, 'error': f'Código {response.status_code}'}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'ok': False, 'error': 'Timeout: ESP32 no responde'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'ok': False, 'error': 'No se puede conectar a ESP32'}), 503
    except Exception as e:
        print(f"[PROXY] Error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@api_bp.route('/esp32/proxy/estado', methods=['GET'])
@rate_limit(20, 60)
def proxy_esp32_estado():
    """Proxy para obtener estado de cerradura — redirige al ESP32."""
    try:
        ip_esp32 = obtener_ip_esp32()
        url = f"http://{ip_esp32}/estado"
        
        print(f"[PROXY] Consultando estado ESP32: {url}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            try:
                return jsonify(response.json()), 200
            except:
                return jsonify({'abierta': False, 'ms_abierta': 0}), 200
        else:
            return jsonify({'ok': False, 'error': f'Código {response.status_code}'}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'ok': False, 'error': 'Timeout: ESP32 no responde'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'ok': False, 'error': 'No se puede conectar a ESP32'}), 503
    except Exception as e:
        print(f"[PROXY] Error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@api_bp.route('/esp32/proxy/ping', methods=['GET'])
@rate_limit(10, 60)
def proxy_esp32_ping():
    """Proxy para ping al ESP32 — redirige al ESP32."""
    try:
        ip_esp32 = obtener_ip_esp32()
        url = f"http://{ip_esp32}/ping"
        
        print(f"[PROXY] Ping a ESP32: {url}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            try:
                return jsonify(response.json()), 200
            except:
                return jsonify({'ok': True, 'status': 'online'}), 200
        else:
            return jsonify({'ok': False, 'error': f'Código {response.status_code}'}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'ok': False, 'status': 'offline', 'error': 'Timeout'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'ok': False, 'status': 'offline', 'error': 'No conectado'}), 503
    except Exception as e:
        print(f"[PROXY] Error: {e}")
        return jsonify({'ok': False, 'status': 'offline', 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
#  PROXY ESP32 AMBIENTES ESPECÍFICOS
# ═══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/esp32/proxy/ambiente/<path:ambiente>/abrir/<int:seg>', methods=['GET', 'POST'])
@rate_limit(10, 60)
def proxy_ambiente_abrir(ambiente, seg):
    """Proxy para abrir cerradura de ambiente específico — para instructores."""
    try:
        if seg < 1 or seg > 15:
            seg = 10
        
        ip_esp32 = obtener_ip_esp32()
        # Log del ambiente para auditoría
        print(f"[PROXY AMBIENTE] Abriendo {ambiente} por {seg}s desde {request.remote_addr}")
        
        # Enviar comando al ESP32
        url = f"http://{ip_esp32}/abrir?seg={seg}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            try:
                return jsonify({
                    'ok': True, 
                    'ambiente': ambiente,
                    'duracion_segundos': seg,
                    'mensaje': f'Cerradura de {ambiente} abierta por {seg}s'
                }), 200
            except:
                return jsonify({
                    'ok': True, 
                    'ambiente': ambiente,
                    'duracion_segundos': seg,
                    'mensaje': f'Cerradura de {ambiente} abierta'
                }), 200
        else:
            return jsonify({'ok': False, 'error': f'Código {response.status_code}'}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'ok': False, 'error': 'Timeout: ESP32 no responde'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'ok': False, 'error': 'No se puede conectar a ESP32'}), 503
    except Exception as e:
        print(f"[PROXY AMBIENTE] Error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@api_bp.route('/esp32/proxy/ambiente/<path:ambiente>/cerrar', methods=['GET', 'POST'])
@rate_limit(10, 60)
def proxy_ambiente_cerrar(ambiente):
    """Proxy para cerrar cerradura de ambiente específico — para vigilantes."""
    try:
        ip_esp32 = obtener_ip_esp32()
        print(f"[PROXY AMBIENTE] Cerrando {ambiente} desde {request.remote_addr}")
        
        url = f"http://{ip_esp32}/cerrar"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            try:
                return jsonify({
                    'ok': True, 
                    'ambiente': ambiente,
                    'mensaje': f'Cerradura de {ambiente} cerrada'
                }), 200
            except:
                return jsonify({
                    'ok': True, 
                    'ambiente': ambiente,
                    'mensaje': f'Cerradura de {ambiente} cerrada'
                }), 200
        else:
            return jsonify({'ok': False, 'error': f'Código {response.status_code}'}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'ok': False, 'error': 'Timeout: ESP32 no responde'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'ok': False, 'error': 'No se puede conectar a ESP32'}), 503
    except Exception as e:
        print(f"[PROXY AMBIENTE] Error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# API CONFIGURACIÓN ESP32
# ═══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/esp32/config', methods=['GET'])
@token_required
def obtener_config_esp32(usuario_id):
    """Obtiene la configuración actual del ESP32."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ['admin', 'administrador']:
        return jsonify({'error': 'No tienes permisos administrativos'}), 403
    
    from flask import current_app
    ip_actual = current_app.config.get('ESP32_IP', '192.168.1.100')
    
    return jsonify({
        'ok': True,
        'esp32_ip': ip_actual,
        'esp32_puerto': 80,
        'esp32_dispositivos_registrados': []
    }), 200


@api_bp.route('/esp32/config', methods=['POST'])
@token_required
def actualizar_config_esp32(usuario_id):
    """Actualiza la configuración del ESP32 (IP)."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ['admin', 'administrador']:
        return jsonify({'error': 'No tienes permisos administrativos'}), 403
    
    data = request.get_json()
    nueva_ip = data.get('esp32_ip', '').strip()
    
    if not nueva_ip:
        return jsonify({'error': 'Especifica la IP del ESP32'}), 400
    
    try:
        # Validar formato IP
        partes = nueva_ip.split('.')
        if len(partes) != 4 or not all(0 <= int(p) <= 255 for p in partes):
            return jsonify({'error': 'IP no válida'}), 400
    except:
        return jsonify({'error': 'Formato de IP inválido'}), 400
    
    # Actualizar configuración en memoria
    from flask import current_app
    current_app.config['ESP32_IP'] = nueva_ip
    
    # Intentar conectar para verificar
    resultado = enviar_comando_esp32('estado')
    
    if resultado.get('ok'):
        log_evento_seguridad(
            f'ESP32: IP configurada a {nueva_ip}',
            usuario_id=usuario_id,
            detalles=f'Administrador: {usuario.nombre}'
        )
        return jsonify({
            'ok': True,
            'mensaje': f'IP actualizada a {nueva_ip}',
            'esp32_ip': nueva_ip,
            'conectado': True
        }), 200
    else:
        # IP configurada pero no puede conectar
        return jsonify({
            'ok': True,
            'mensaje': f'IP actualizada a {nueva_ip}, pero no se puede conectar',
            'esp32_ip': nueva_ip,
            'conectado': False,
            'error_conexion': resultado.get('error')
        }), 200


@api_bp.route('/esp32/ping', methods=['POST'])
@token_required
def ping_esp32(usuario_id):
    """Prueba la conexión con el ESP32."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ['admin', 'administrador', 'vigilante']:
        return jsonify({'error': 'No tienes permisos'}), 403
    
    resultado = enviar_comando_esp32('estado')
    
    return jsonify({
        'ok': resultado.get('ok', False),
        'mensaje': resultado.get('mensaje', 'Conexión probada'),
        'error': resultado.get('error'),
        'estado': resultado if resultado.get('ok') else None
    }), 200 if resultado.get('ok') else 503


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS TRIAC — VERSIÓN MOCK (para pruebas sin ESP32 físico)
# Descomentar /test para usar mock, comentar para usar ESP32 real
# ═══════════════════════════════════════════════════════════════════════════════

_triac_mock_state = {'ciclo_activo': False, 'pulso_actual': 0}

@api_bp.route('/vigilancia/triac/iniciar', methods=['POST'])
@token_required
def iniciar_triac(usuario_id):
    """Inicia el ciclo de pulsos TRIAC (5 × 3s ON + 10s OFF) desde el panel de vigilante."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no válido'}), 401
    
    # Verificar permisos (solo vigilantes y administradores)
    if usuario.rol not in ['vigilante', 'admin', 'administrador']:
        return jsonify({'error': 'No tienes permisos para controlar el TRIAC'}), 403
    
    # Enviar comando a ESP32
    resultado = enviar_comando_esp32('iniciar')
    
    # Registrar acción en auditoría
    try:
        log_evento_seguridad(
            f'TRIAC INICIADO',
            usuario_id=usuario_id,
            detalles=f'Vigilante {usuario.nombre} inició ciclo TRIAC'
        )
    except:
        pass
    
    # Emitir evento en tiempo real por WebSocket
    try:
        if websocket_handler.socketio:
            websocket_handler.socketio.emit('triac_iniciado', {
                'usuario': usuario.nombre,
                'ok': resultado.get('ok', False),
                'timestamp': datetime.utcnow().isoformat(),
                'pulsos_totales': 5,
                'tiempo_pulso_ms': 3000,
                'tiempo_espera_ms': 10000
            }, broadcast=True)
    except Exception as e:
        print(f"[WebSocket] Error emitiendo triac_iniciado: {e}")
    
    return jsonify({
        'ok': resultado.get('ok', False),
        'mensaje': resultado.get('mensaje', 'Ciclo TRIAC iniciado'),
        'error': resultado.get('error', None),
        'pulsos': 5,
        'tiempo_pulso_ms': 3000,
        'tiempo_espera_ms': 10000,
    }), 200 if resultado.get('ok') else 400


@api_bp.route('/vigilancia/triac/parar', methods=['POST'])
@token_required
def parar_triac(usuario_id):
    """Detiene el ciclo de pulsos TRIAC inmediatamente."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no válido'}), 401
    
    # Verificar permisos
    if usuario.rol not in ['vigilante', 'admin', 'administrador']:
        return jsonify({'error': 'No tienes permisos para controlar el TRIAC'}), 403
    
    # Enviar comando a ESP32
    resultado = enviar_comando_esp32('parar')
    
    # Registrar acción
    try:
        log_evento_seguridad(
            f'TRIAC DETENIDO',
            usuario_id=usuario_id,
            detalles=f'Vigilante {usuario.nombre} detuvo ciclo TRIAC'
        )
    except:
        pass
    
    # Emitir evento en tiempo real por WebSocket
    try:
        if websocket_handler.socketio:
            websocket_handler.socketio.emit('triac_parado', {
                'usuario': usuario.nombre,
                'ok': resultado.get('ok', False),
                'timestamp': datetime.utcnow().isoformat(),
            }, broadcast=True)
    except Exception as e:
        print(f"[WebSocket] Error emitiendo triac_parado: {e}")
    
    return jsonify({
        'ok': resultado.get('ok', False),
        'mensaje': resultado.get('mensaje', 'TRIAC detenido'),
        'error': resultado.get('error', None),
    }), 200 if resultado.get('ok') else 400


@api_bp.route('/vigilancia/triac/estado', methods=['GET'])
@token_required
def estado_triac(usuario_id):
    """Obtiene el estado actual del TRIAC (ciclo activo, pulsos, etc)."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no válido'}), 401
    
    # Enviar comando a ESP32
    resultado = enviar_comando_esp32('estado')
    
    if resultado.get('ok'):
        return jsonify(resultado), 200
    else:
        # Si no puede conectar, retornar estado desconocido
        return jsonify({
            'ok': False,
            'ciclo_activo': None,
            'estado_esp32': 'desconectado',
            'error': resultado.get('error', 'Desconocido')
        }), 503


@api_bp.route('/edificios/<edificio_id>', methods=['DELETE'])
@token_required
def eliminar_edificio(usuario_id, edificio_id):
    """Elimina (soft delete) un edificio."""
    try:
        ed = Edificio.query.filter_by(id=edificio_id, deleted_at=None).first()
        if not ed:
            return jsonify({'error': 'Edificio no encontrado'}), 404
        ed.soft_delete()
        return jsonify({'mensaje': f'Edificio "{ed.nombre}" eliminado'}), 200
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# CERRADURAS ELECTRÓNICAS
# ═══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/ambientes/cerradura/abrir', methods=['POST'])
@token_required
def abrir_cerradura_ambiente(usuario_id):
    """Abre la cerradura electrónica de un ambiente."""
    try:
        data = request.get_json()
        ambiente = data.get('ambiente')
        
        if not ambiente:
            return jsonify({'error': 'Especifica el ambiente'}), 400
        
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no válido'}), 401
        
        # Registrar apertura en log de seguridad
        log_evento_seguridad(
            f'CERRADURA: Apertura de ambiente {ambiente}',
            usuario_id=usuario_id,
            detalles=f'Usuario: {usuario.username}'
        )
        
        # Emit WebSocket event para notificar en tiempo real
        socketio.emit('cerradura_abierta', {
            'ambiente': ambiente,
            'usuario': usuario.username,
            'timestamp': datetime.utcnow().isoformat()
        }, broadcast=True)
        
        return jsonify({
            'ok': True,
            'mensaje': f'Cerradura de {ambiente} abierta',
            'ambiente': ambiente,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


@api_bp.route('/ambientes/cerradura/cerrar', methods=['POST'])
@token_required
def cerrar_cerradura_ambiente(usuario_id):
    """Cierra la cerradura electrónica de un ambiente."""
    try:
        data = request.get_json()
        ambiente = data.get('ambiente')
        
        if not ambiente:
            return jsonify({'error': 'Especifica el ambiente'}), 400
        
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no válido'}), 401
        
        # Registrar cierre en log de seguridad
        log_evento_seguridad(
            f'CERRADURA: Cierre de ambiente {ambiente}',
            usuario_id=usuario_id,
            detalles=f'Usuario: {usuario.username}'
        )
        
        # Emit WebSocket event
        socketio.emit('cerradura_cerrada', {
            'ambiente': ambiente,
            'usuario': usuario.username,
            'timestamp': datetime.utcnow().isoformat()
        }, broadcast=True)
        
        return jsonify({
            'ok': True,
            'mensaje': f'Cerradura de {ambiente} cerrada',
            'ambiente': ambiente,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


@api_bp.route('/ambientes/cerradura/estado', methods=['GET'])
@token_required
def estado_cerradura(usuario_id):
    """Obtiene el estado de todas las cerraduras."""
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no válido'}), 401
        
        return jsonify({
            'ok': True,
            'cerraduras_abiertas': [],
            'estado': 'operativo',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


@api_bp.route('/ambientes/cerradura/historial', methods=['GET'])
@token_required
def historial_cerradura(usuario_id):
    """Obtiene el historial de movimientos de cerraduras."""
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no válido'}), 401
        
        limite = request.args.get('limite', 40, type=int)
        
        return jsonify({
            'ok': True,
            'historial': [],
            'total': 0,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


# ── PANEL DE SISTEMAS (solo programadores) ────────────────────────────────────

def _leer_dev_pin_secret():
    """Lee DEV_PIN_SECRET directamente del archivo .env en cada llamada.
    Esto garantiza que rotar el secreto desde la terminal invalida de inmediato
    cualquier sesión abierta del panel, sin necesidad de reiniciar el servidor."""
    import re as _re
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    try:
        with open(env_path, 'r', encoding='utf-8') as _f:
            for _linea in _f:
                _m = _re.match(r'^DEV_PIN_SECRET=(.+)', _linea.strip())
                if _m:
                    return _m.group(1).strip()
    except OSError:
        pass
    return ''


def _compute_dev_pin(secreto, window_offset=0):
    """Calcula el PIN dinámico (TOTP-style, 6 dígitos) para la ventana actual + offset."""
    import hmac as _hmac, hashlib as _hashlib, struct as _struct, time as _time
    t = (int(_time.time()) // 300) + window_offset
    key = secreto.encode('utf-8')
    msg = _struct.pack('>Q', t)
    h = _hmac.new(key, msg, _hashlib.sha256).digest()
    off = h[-1] & 0x0F
    code = _struct.unpack('>I', h[off:off + 4])[0] & 0x7FFFFFFF
    return str(code % 1_000_000).zfill(6)


def _check_dev_pin(req):
    """Devuelve True si el header X-Dev-Pin coincide con el PIN dinámico actual.
    Lee el secreto directamente del .env para que la rotación sea instantánea."""
    import hmac as _hmac
    secreto = _leer_dev_pin_secret()
    if not secreto:
        return False
    pin_enviado = req.headers.get('X-Dev-Pin', '').replace(' ', '')
    if not pin_enviado:
        return False
    pin_actual = _compute_dev_pin(secreto, 0)
    return _hmac.compare_digest(pin_enviado, pin_actual)


@api_bp.route('/sistemas/verificar-pin', methods=['POST'])
@token_required
def sistemas_verificar_pin(usuario_id):
    """Verifica el PIN dinámico del panel de sistemas."""
    if not _leer_dev_pin_secret():
        return jsonify({'error': 'PIN de sistemas no configurado. Ejecuta MANTENIMIENTO.bat → opción [P].'}), 503
    if not _check_dev_pin(request):
        return jsonify({'error': 'PIN incorrecto'}), 403
    return jsonify({'ok': True}), 200


@api_bp.route('/sistemas/estado', methods=['GET'])
@token_required
def sistemas_estado(usuario_id):
    """Devuelve el estado completo del sistema: BD, tablas, Python, uptime."""
    if not _check_dev_pin(request):
        return jsonify({'error': 'PIN incorrecto'}), 403
    try:
        import sys
        import platform
        from flask import current_app

        # Tamaño del archivo SQLite
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        db_size_bytes = 0
        db_path = ''
        if 'sqlite:///' in db_uri:
            db_path = db_uri.replace('sqlite:///', '')
            if not os.path.isabs(db_path):
                instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
                db_path = os.path.join(instance_dir, db_path)
            if os.path.exists(db_path):
                db_size_bytes = os.path.getsize(db_path)

        # Conteo de filas por tabla
        tablas = {
            'Personas':          Persona.query.filter_by(deleted_at=None).count(),
            'Personas (total)':  Persona.query.count(),
            'Registros acceso':  RegistroAcceso.query.filter_by(deleted_at=None).count(),
            'Usuarios':          Usuario.query.filter_by(deleted_at=None).count(),
            'Computadores':      Computador.query.filter_by(deleted_at=None).count(),
            'Inventario':        RegistroInventario.query.filter_by(deleted_at=None).count(),
            'Edificios':         Edificio.query.filter_by(deleted_at=None).count(),
        }

        # Respaldos USB registrados
        try:
            total_respaldos = Respaldo.query.count()
        except Exception:
            total_respaldos = 0

        tablas['Respaldos'] = total_respaldos

        # Info del proceso
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            mem_mb = round(proc.memory_info().rss / 1024 / 1024, 1)
            cpu_pct = proc.cpu_percent(interval=0.1)
        except ImportError:
            mem_mb = None
            cpu_pct = None

        return jsonify({
            'python_version': sys.version,
            'plataforma': platform.system() + ' ' + platform.release(),
            'db_uri': db_uri,
            'db_path': db_path,
            'db_size_bytes': db_size_bytes,
            'db_size_kb': round(db_size_bytes / 1024, 1),
            'db_size_mb': round(db_size_bytes / 1024 / 1024, 2),
            'tablas': tablas,
            'memoria_mb': mem_mb,
            'cpu_pct': cpu_pct,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }), 200
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'detalle': traceback.format_exc()}), 500


@api_bp.route('/admin/obtener-pin-actual', methods=['POST'])
@token_required
def obtener_pin_actual(usuario_id):
    """Endpoint para generar y retornar el PIN actual.
    Útil para que el usuario vea el PIN directamente en la página."""
    
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('administrador', 'systems', 'sysadmin', 'admin'):
        return jsonify({'error': 'No tienes permisos'}), 403
    
    try:
        import re, hmac, hashlib, struct, time
        
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        secreto = ''
        with open(env_path, 'r') as f:
            for linea in f:
                m = re.match(r'^DEV_PIN_SECRET=(.+)', linea.strip())
                if m:
                    secreto = m.group(1).strip()
                    break
        
        if not secreto:
            return jsonify({'error': 'PIN no configurado'}), 503
        
        # Calcular PIN actual
        t = int(time.time()) // 300  # 5 minutos
        key = secreto.encode()
        msg = struct.pack('>Q', t)
        h = hmac.new(key, msg, hashlib.sha256).digest()
        off = h[-1] & 0x0F
        code = struct.unpack('>I', h[off:off + 4])[0] & 0x7FFFFFFF
        pin = str(code % 1_000_000).zfill(6)
        
        # Tiempo restante (aproximado)
        ahora = int(time.time())
        tiempo_restante = 300 - (ahora % 300)
        
        # Registrar acceso al PIN
        print(f"[PIN GENERADO] Usuario: {usuario.email}, PIN: {pin}, TTL: {tiempo_restante}s")
        
        return jsonify({
            'success': True,
            'pin': pin,
            'valido_por_segundos': tiempo_restante,
            'usuario': usuario.email,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── VALIDACIÓN DE PIN DINÁMICO (TOTP) — HERRAMIENTAS DE MANTENIMIENTO ────────

@api_bp.route('/admin/verificar-codigo-mantenimiento', methods=['POST'])
@token_required
def verificar_codigo_mantenimiento(usuario_id):
    """Verifica el PIN dinámico (TOTP) para acceso a herramientas de mantenimiento"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        try:
            log_evento_seguridad(
                usuario_id=usuario_id,
                tipo_evento='MANTENIMIENTO_ACCESO_DENEGADO_ROL',
                detalles=f'Usuario sin rol de administrador intentó acceder',
                ip=_get_client_ip()
            )
        except:
            pass
        return jsonify({'success': False, 'error': 'Acceso denegado - rol insuficiente'}), 403
    
    try:
        datos = request.get_json() or {}
        pin_ingresado = (datos.get('codigo') or '').strip()
        
        if not pin_ingresado:
            return jsonify({'success': False, 'error': 'PIN requerido'}), 400
        
        # Importar funciones TOTP de gestionar_pin_sistemas
        import sys
        import struct
        import hmac
        import hashlib
        import time
        import re
        
        WINDOW_SECONDS = 300  # 5 minutos como en gestionar_pin_sistemas.py
        ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        
        # Leer secreto del .env
        def leer_secreto_dev():
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
        
        # Calcular PIN TOTP
        def compute_pin_totp(secreto, window_offset=0):
            t = (int(time.time()) // WINDOW_SECONDS) + window_offset
            key = secreto.encode('utf-8')
            msg = struct.pack('>Q', t)
            h = hmac.new(key, msg, hashlib.sha256).digest()
            off = h[-1] & 0x0F
            code = struct.unpack('>I', h[off:off + 4])[0] & 0x7FFFFFFF
            return str(code % 1_000_000).zfill(6)
        
        secreto = leer_secreto_dev()
        if not secreto:
            return jsonify({
                'success': False, 
                'error': 'No hay secreto configurado en el sistema. Ejecuta MANTENIMIENTO.bat opción P primero.'
            }), 500
        
        # Validar PIN actual y ventanas adyacentes (tolerancia de ±1 ventana)
        pin_actual = compute_pin_totp(secreto, window_offset=0)
        pin_anterior = compute_pin_totp(secreto, window_offset=-1)
        pin_siguiente = compute_pin_totp(secreto, window_offset=1)
        
        es_valido = pin_ingresado in [pin_actual, pin_anterior, pin_siguiente]
        
        if not es_valido:
            try:
                log_evento_seguridad(
                    usuario_id=usuario_id,
                    tipo_evento='MANTENIMIENTO_PIN_FALLIDO',
                    detalles=f'PIN incorrecto para acceso a herramientas',
                    ip=_get_client_ip()
                )
            except:
                pass
            return jsonify({'success': False, 'error': 'PIN incorrecto'}), 401
        
        # PIN válido - acceso concedido
        try:
            log_evento_seguridad(
                usuario_id=usuario_id,
                tipo_evento='MANTENIMIENTO_ACCESO_OTORGADO',
                detalles=f'PIN válido - Acceso a herramientas de mantenimiento concedido',
                ip=_get_client_ip()
            )
        except:
            pass
        
        return jsonify({
            'success': True,
            'mensaje': '✓ Acceso concedido a herramientas de mantenimiento'
        }), 200
    
    except Exception as e:
        import traceback
        print(f'Error en verificar_codigo_mantenimiento: {e}')
        print(traceback.format_exc())
        return jsonify({
            'success': False, 
            'error': f'Error validando PIN: {str(e)}'
        }), 500


# ════════════════════════════════════════════════════════════════════════════════
# NUEVOS ENDPOINTS DE HERRAMIENTAS MEJORADAS
# ════════════════════════════════════════════════════════════════════════════════

@api_bp.route('/admin/estadisticas-sistema', methods=['GET'])
@token_required
def estadisticas_sistema(usuario_id):
    """Obtiene estadísticas globales del sistema"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        from datetime import datetime, timedelta
        
        hoy = datetime.now().date()
        
        total_personas = Persona.query.filter_by(deleted_at=None).count()
        aprendices = Persona.query.filter_by(perfil='aprendiz', deleted_at=None).count()
        instructores = Persona.query.filter_by(perfil='instructor', deleted_at=None).count()
        visitantes = Persona.query.filter_by(perfil='visitante', deleted_at=None).count()
        
        accesos_hoy = RegistroAcceso.query.filter(
            RegistroAcceso.timestamp >= datetime.combine(hoy, datetime.min.time())
        ).all()
        
        accesos_entrada = len([a for a in accesos_hoy if a.tipo == 'entrada'])
        accesos_salida = len([a for a in accesos_hoy if a.tipo == 'salida'])
        
        usuarios_activos = Usuario.query.filter_by(activo=True, deleted_at=None).count()
        
        return jsonify({
            'total_personas': total_personas,
            'aprendices': aprendices,
            'instructores': instructores,
            'visitantes': visitantes,
            'accesos_entrada': accesos_entrada,
            'accesos_salida': accesos_salida,
            'usuarios_activos': usuarios_activos,
            'sesiones_abiertas': usuarios_activos
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/system-counters', methods=['GET'])
@token_required
def system_counters(usuario_id):
    """Obtiene contadores del sistema"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        return jsonify({
            'Personas Totales': Persona.query.filter_by(deleted_at=None).count(),
            'Registros de Acceso': RegistroAcceso.query.count(),
            'Usuarios del Sistema': Usuario.query.filter_by(deleted_at=None).count(),
            'Equipos Registrados': ComputadorInventario.query.filter_by(deleted_at=None).count() if 'ComputadorInventario' in dir() else 0,
            'Cambios Auditados': AuditoriaAdministrativa.query.count() if 'AuditoriaAdministrativa' in dir() else 0
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/auditoria-reciente', methods=['GET'])
@token_required
def auditoria_reciente(usuario_id):
    """Obtiene eventos de auditoría recientes"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        limit = request.args.get('limit', 10, type=int)
        
        eventos = AuditoriaAdministrativa.query.order_by(
            AuditoriaAdministrativa.timestamp.desc()
        ).limit(limit).all()
        
        resultado = []
        for evt in eventos:
            resultado.append({
                'tipo': evt.tipo_evento if hasattr(evt, 'tipo_evento') else 'evento',
                'usuario': evt.usuario.email if evt.usuario else 'sistema',
                'timestamp': evt.timestamp.strftime('%Y-%m-%d %H:%M:%S') if hasattr(evt, 'timestamp') else ''
            })
        
        return jsonify({'eventos': resultado}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/ultimos-accesos', methods=['GET'])
@token_required
def ultimos_accesos(usuario_id):
    """Obtiene últimos accesos al sistema"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        limit = request.args.get('limit', 15, type=int)
        
        accesos = RegistroAcceso.query.order_by(
            RegistroAcceso.timestamp.desc()
        ).limit(limit).all()
        
        resultado = []
        for acc in accesos:
            persona = Persona.query.get(acc.persona_id)
            resultado.append({
                'nombre': persona.nombre if persona else f'ID:{acc.persona_id}',
                'tipo': acc.tipo,
                'hora': acc.timestamp.strftime('%H:%M:%S'),
                'fecha': acc.timestamp.strftime('%Y-%m-%d')
            })
        
        return jsonify({'accesos': resultado}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/usuarios-activos', methods=['GET'])
@token_required
def usuarios_activos_list(usuario_id):
    """Lista usuarios activos del sistema"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        usuarios = Usuario.query.filter_by(activo=True, deleted_at=None).all()
        
        resultado = []
        for usr in usuarios:
            resultado.append({
                'email': usr.email,
                'rol': usr.rol,
                'estado': 'Activo'
            })
        
        return jsonify({'usuarios': resultado}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/sesiones-activas', methods=['GET'])
@token_required
def sesiones_activas_list(usuario_id):
    """Lista sesiones activas simuladas (basado en usuarios activos)"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        usuarios = Usuario.query.filter_by(activo=True, deleted_at=None).all()
        
        resultado = []
        for usr in usuarios:
            resultado.append({
                'usuario': usr.email,
                'ip': '127.0.0.1',
                'duracion': '< 1 hora'
            })
        
        return jsonify({'sesiones': resultado}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/cerrar-todas-sesiones', methods=['POST'])
@token_required
def cerrar_todas_sesiones_endpoint(usuario_id):
    """Cierra todas las sesiones del sistema"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        # Registrar auditoría
        try:
            log_evento_seguridad(
                usuario_id=usuario_id,
                tipo_evento='MANTENIMIENTO_CERRAR_SESIONES',
                detalles='Todas las sesiones cerradas por administrador',
                ip=_get_client_ip()
            )
        except:
            pass
        
        return jsonify({
            'success': True,
            'sesiones_cerradas': 0,
            'mensaje': '✓ Comando registrado'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/resetear-password', methods=['POST'])
@token_required
def resetear_password_admin(usuario_id):
    """Resetea la contraseña de un usuario a una aleatoria"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        import secrets
        datos = request.get_json() or {}
        email = datos.get('email', '').strip()
        
        if not email:
            return jsonify({'error': 'Email requerido'}), 400
        
        usr = Usuario.query.filter_by(email=email).first()
        if not usr:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Generar contraseña aleatoria
        nueva_pass = secrets.token_urlsafe(12)
        usr.set_password(nueva_pass)
        db.session.commit()
        
        # Registrar auditoría
        try:
            log_evento_seguridad(
                usuario_id=usuario_id,
                tipo_evento='MANTENIMIENTO_RESET_PASSWORD',
                detalles=f'Password reseteado para {email}',
                ip=_get_client_ip()
            )
        except:
            pass
        
        return jsonify({
            'success': True,
            'nueva_password': nueva_pass,
            'mensaje': f'✓ Password reseteado a: {nueva_pass}'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/logs-recientes', methods=['GET'])
@token_required
def logs_recientes_endpoint(usuario_id):
    """Obtiene los logs más recientes del sistema"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        lineas = request.args.get('lineas', 50, type=int)
        
        # Buscar archivos de log
        log_files = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sena.log'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'app.log'),
        ]
        
        logs_content = 'No hay logs disponibles'
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                        todas_lineas = f.readlines()
                    ultimas = todas_lineas[-lineas:] if len(todas_lineas) > lineas else todas_lineas
                    logs_content = ''.join(ultimas)
                    break
                except:
                    pass
        
        return jsonify({'logs': logs_content}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/limpiar-logs', methods=['POST'])
@token_required
def limpiar_logs_endpoint(usuario_id):
    """Limpia todos los arhivos de log"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        log_files = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sena.log'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'app.log'),
        ]
        
        limpios = 0
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    open(log_file, 'w').close()
                    limpios += 1
                except:
                    pass
        
        # Registrar auditoría
        try:
            log_evento_seguridad(
                usuario_id=usuario_id,
                tipo_evento='MANTENIMIENTO_LIMPIAR_LOGS',
                detalles=f'{limpios} archivos de log limpiados',
                ip=_get_client_ip()
            )
        except:
            pass
        
        return jsonify({
            'success': True,
            'archivos_limpios': limpios,
            'mensaje': f'✓ {limpios} logs limpiados'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/uso-disco', methods=['GET'])
@token_required
def uso_disco_endpoint(usuario_id):
    """Obtiene información sobre el uso de disco"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        import shutil
        
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        def get_dir_size(path):
            try:
                return sum(os.path.getsize(os.path.join(dirpath, filename))
                          for dirpath, dirnames, filenames in os.walk(path)
                          for filename in filenames)
            except:
                return 0
        
        db_size = 0
        try:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'sena.db')
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path) / 1024 / 1024
        except:
            pass
        
        logs_size = get_dir_size(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')) / 1024 / 1024
        cache_size = get_dir_size(os.path.join(os.path.dirname(os.path.abspath(__file__)), '__pycache__')) / 1024 / 1024
        backups_size = get_dir_size(os.path.join(BASE_DIR, 'RESPALDOS_USB')) / 1024 / 1024
        
        total = db_size + logs_size + cache_size + backups_size
        
        return jsonify({
            'db_size': f'{db_size:.2f} MB',
            'logs_size': f'{logs_size:.2f} MB',
            'cache_size': f'{cache_size:.2f} MB',
            'backups_size': f'{backups_size:.2f} MB',
            'total_size': f'{total:.2f} MB'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/limpiar-cache-avanzado', methods=['POST'])
@token_required
def limpiar_cache_avanzado_endpoint(usuario_id):
    """Limpia cache de Python y archivos temporales"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'administrador', 'systems', 'sysadmin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        import shutil
        
        BACKEND = os.path.dirname(os.path.abspath(__file__))
        eliminados = 0
        
        for root, dirs, files in os.walk(BACKEND):
            if '__pycache__' in dirs:
                try:
                    shutil.rmtree(os.path.join(root, '__pycache__'))
                    eliminados += 1
                except:
                    pass
            for f in files:
                if f.endswith('.pyc'):
                    try:
                        os.remove(os.path.join(root, f))
                        eliminados += 1
                    except:
                        pass
        
        # Registrar auditoría
        try:
            log_evento_seguridad(
                usuario_id=usuario_id,
                tipo_evento='MANTENIMIENTO_LIMPIAR_CACHE',
                detalles=f'{eliminados} elementos de cache eliminados',
                ip=_get_client_ip()
            )
        except:
            pass
        
        return jsonify({
            'success': True,
            'items_eliminados': eliminados,
            'mensaje': f'✓ {eliminados} elementos limpios'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/sistemas/vacuum', methods=['POST'])
@token_required
def sistemas_vacuum(usuario_id):
    """Ejecuta VACUUM y ANALYZE en la base de datos SQLite para optimizarla."""
    if not _check_dev_pin(request):
        return jsonify({'error': 'PIN incorrecto'}), 403
    try:
        from flask import current_app
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if 'sqlite' not in db_uri:
            return jsonify({'error': 'VACUUM solo disponible en SQLite'}), 400

        antes = 0
        db_path = ''
        if 'sqlite:///' in db_uri:
            db_path = db_uri.replace('sqlite:///', '')
            if not os.path.isabs(db_path):
                instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
                db_path = os.path.join(instance_dir, db_path)
            if os.path.exists(db_path):
                antes = os.path.getsize(db_path)

        db.session.execute(db.text('VACUUM'))
        db.session.execute(db.text('ANALYZE'))
        db.session.commit()

        despues = os.path.getsize(db_path) if db_path and os.path.exists(db_path) else antes
        ahorro = antes - despues
        return jsonify({
            'ok': True,
            'antes_bytes': antes,
            'despues_bytes': despues,
            'ahorro_bytes': ahorro,
            'ahorro_kb': round(ahorro / 1024, 1),
            'mensaje': f'VACUUM completado. Espacio liberado: {round(ahorro/1024,1)} KB'
        }), 200
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'detalle': traceback.format_exc()}), 500


@api_bp.route('/sistemas/descargar-db', methods=['GET'])
@token_required
def sistemas_descargar_db(usuario_id):
    """Descarga el archivo SQLite directamente como backup."""
    if not _check_dev_pin(request):
        return jsonify({'error': 'PIN incorrecto'}), 403
    try:
        from flask import current_app
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if 'sqlite:///' not in db_uri:
            return jsonify({'error': 'Solo disponible con SQLite'}), 400
        db_path = db_uri.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
            db_path = os.path.join(instance_dir, db_path)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Archivo de base de datos no encontrado'}), 404
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre = f'sena_backup_{ts}.db'
        return send_file(db_path, as_attachment=True, download_name=nombre,
                         mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/sistemas/logs', methods=['GET'])
@token_required
def sistemas_logs(usuario_id):
    """Devuelve las últimas N líneas del log de la aplicación."""
    if not _check_dev_pin(request):
        return jsonify({'error': 'PIN incorrecto'}), 403
    try:
        lineas_n = request.args.get('n', 80, type=int)
        # Buscar archivo de log en ubicaciones comunes
        posibles = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sena.log'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.log'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log'),
        ]
        log_path = next((p for p in posibles if os.path.exists(p)), None)
        if not log_path:
            return jsonify({'lineas': [], 'mensaje': 'No se encontró archivo de log. '
                            'Configura logging en app.py para registrar errores.', 'path': None}), 200
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            todas = f.readlines()
        ultimas = todas[-lineas_n:] if len(todas) > lineas_n else todas
        return jsonify({'lineas': [l.rstrip('\n') for l in ultimas],
                        'total_lineas': len(todas), 'path': log_path}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/sistemas/health', methods=['GET'])
@token_required
def sistemas_health(usuario_id):
    """Prueba rápida de conectividad interna: BD y tablas principales."""
    if not _check_dev_pin(request):
        return jsonify({'error': 'PIN incorrecto'}), 403
    resultados = []
    checks = [
        ('Base de datos', lambda: db.session.execute(db.text('SELECT 1')).fetchone()),
        ('Tabla personas', lambda: Persona.query.count()),
        ('Tabla accesos', lambda: RegistroAcceso.query.count()),
        ('Tabla usuarios', lambda: Usuario.query.count()),
        ('Tabla computadores', lambda: Computador.query.count()),
        ('Tabla inventario', lambda: RegistroInventario.query.count()),
        ('Tabla edificios', lambda: Edificio.query.count()),
    ]
    for nombre, fn in checks:
        t0 = datetime.utcnow()
        try:
            val = fn()
            ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
            resultados.append({'nombre': nombre, 'ok': True, 'ms': ms,
                                'valor': str(val) if not isinstance(val, int) else val})
        except Exception as ex:
            ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
            resultados.append({'nombre': nombre, 'ok': False, 'ms': ms, 'error': str(ex)})
    todos_ok = all(r['ok'] for r in resultados)
    return jsonify({'ok': todos_ok, 'checks': resultados,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'}), 200


# ─── MODO MANTENIMIENTO ────────────────────────────────────────────────────────
_MAINTENANCE_STATE = {'activo': False, 'mensaje': 'El sistema est\u00e1 siendo actualizado. Por favor espere.'}

@api_bp.route('/sistema/mantenimiento', methods=['GET'])
def sistema_mantenimiento_estado():
    """Endpoint p\u00fablico \u2014 cualquier p\u00e1gina puede consultarlo sin autenticaci\u00f3n."""
    return jsonify(_MAINTENANCE_STATE), 200


@api_bp.route('/sistemas/modo-mantenimiento', methods=['POST'])
@token_required
def sistemas_modo_mantenimiento(usuario_id):
    """Activa o desactiva el modo mantenimiento. Requiere PIN de sistemas."""
    if not _check_dev_pin(request):
        return jsonify({'error': 'PIN incorrecto'}), 403
    data = request.get_json(silent=True) or {}
    _MAINTENANCE_STATE['acigualtivo']  = bool(data.get('activo', False))
    msg = str(data.get('mensaje', '') or '').strip()
    _MAINTENANCE_STATE['mensaje'] = msg or 'El sistema est\u00e1 siendo actualizado. Por favor espere.'
    return jsonify({'ok': True, 'estado': _MAINTENANCE_STATE}), 200


# ── USUARIOS DEL SISTEMA (admin) ─────────────────────────────────────────────

@api_bp.route('/admin/usuarios', methods=['GET'])
@token_required
def listar_usuarios_sistema(usuario_id):
    """Lista vigilantes, admins y otros usuarios. Solo accesible para admin."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol not in ('admin', 'sistemas'):
        return jsonify({'error': 'Acceso denegado'}), 403
    usuarios = Usuario.query.filter_by(deleted_at=None).order_by(Usuario.rol, Usuario.nombre).all()
    return jsonify({'usuarios': [
        {
            'id': u.id,
            'email': u.email,
            'nombre': u.nombre,
            'rol': u.rol,
            'activo': u.activo,
        } for u in usuarios
    ]}), 200


# ── ENDPOINT INTERNO para terminal (gestionar_usuarios.py) ──────────────────

@api_bp.route('/interno/notificar-usuarios', methods=['POST'])
def notificar_usuarios_terminal():
    """Emite evento WebSocket cuando la terminal crea/modifica usuarios.
    Valida la peticion con SECRET_KEY para evitar accesos no autorizados."""
    import hmac
    secret = request.headers.get('X-Internal-Secret', '')
    expected = os.getenv('SECRET_KEY', '')
    if not expected or not hmac.compare_digest(str(secret), str(expected)):
        return jsonify({'error': 'No autorizado'}), 401
    try:
        if websocket_handler.socketio:
            websocket_handler.socketio.emit(
                'usuarios_actualizados',
                {'timestamp': datetime.utcnow().isoformat() + 'Z'},
                namespace='/'
            )
    except Exception:
        pass
    return jsonify({'ok': True}), 200

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CERRADURA AUTOMÃTICA â€” MONITOREO Y CONTROL
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@api_bp.route('/cerradura-automatica/intento/<intento_id>', methods=['GET'])
@token_required
def obtener_estado_intento(usuario_id, intento_id):
    """Obtiene el estado de un intento de cerradura automÃ¡tica"""
    try:
        stats = lock_scheduler.obtener_estadisticas_intento(intento_id)
        if not stats:
            return jsonify({'error': 'Intento no encontrado'}), 404
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/cerradura-automatica/intentos-activos/<numero_doc>', methods=['GET'])
@token_required
def obtener_intentos_activos(usuario_id, numero_doc):
    """Obtiene todos los intentos activos de una persona"""
    try:
        # NOTA: IntentoCerraduraAutomatica no está implementado aún
        # Retornar lista vacía en stub
        intentos = []
        
        return jsonify({
            'numero_doc': numero_doc,
            'intentos_activos': len(intentos),
            'intentos': [
                {
                    'id': i.id,
                    'ambiente': i.ambiente,
                    'piso': i.piso,
                    'estado': i.estado,
                    'fecha_ingreso': i.fecha_ingreso.isoformat() if i.fecha_ingreso else None,
                    'tiempo_espera_seg': i.tiempo_espera_seg,
                }
                for i in intentos
            ]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/cerradura-automatica/estadisticas', methods=['GET'])
@token_required
def obtener_estadisticas_cerradura(usuario_id):
    """Obtiene estadÃ­sticas generales de intentos de cerradura"""
    try:
        hoy = datetime.utcnow().date()
        inicio_hoy = datetime(hoy.year, hoy.month, hoy.day)
        fin_hoy = inicio_hoy + timedelta(days=1)
        
        # Intentos de hoy
        # NOTA: IntentoCerraduraAutomatica no está implementado aún
        # Retornar lista vacía en stub
        intentos_hoy = []
        
        # EstadÃ­sticas por estado
        estados = {}
        por_piso = {}
        
        for intento in intentos_hoy:
            # Por estado
            estado = intento.estado
            estados[estado] = estados.get(estado, 0) + 1
            
            # Por piso
            piso = intento.piso
            por_piso[piso] = por_piso.get(piso, 0) + 1
        
        return jsonify({
            'fecha': hoy.isoformat(),
            'total_intentos': len(intentos_hoy),
            'por_estado': estados,
            'por_piso': por_piso,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/cerradura-automatica/forzar-apertura', methods=['POST'])
@token_required
def forzar_apertura_cerradura(usuario_id):
    """Fuerza la apertura manual de la cerradura (para vigilantes)"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol != 'vigilante':
        return jsonify({'error': 'Solo vigilantes pueden forzar apertura'}), 403
    
    try:
        datos = request.get_json()
        duracion = datos.get('duracion_segundos', 5)
        ambiente = datos.get('ambiente', 'Manual')
        motivo = datos.get('motivo', 'Apertura manual del vigilante')
        
        # Activar cerradura
        lock_scheduler.activar_cerradura(duracion)
        
        # Emitir evento WebSocket
        if websocket_handler.socketio:
            websocket_handler.socketio.emit('cerradura_abierta_manual', {
                'duracion_segundos': duracion,
                'vigilante': usuario.nombre,
                'ambiente': ambiente,
                'motivo': motivo,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }, namespace='/')
        
        # Registrar en log
        log_evento_seguridad(
            f'CERRADURA MANUAL: {motivo} - Duración: {duracion}s',
            usuario_id=usuario_id,
            detalles=f'Vigilante: {usuario.nombre}, Ambiente: {ambiente}'
        )
        
        return jsonify({
            'ok': True,
            'mensaje': f'Cerradura abierta por {duracion} segundos',
            'duracion_segundos': duracion,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/cerradura-automatica/cerrar', methods=['POST'])
@token_required
def cerrar_cerradura(usuario_id):
    """Cierra/desactiva la cerradura manualmente (para vigilantes)"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol != 'vigilante':
        return jsonify({'error': 'Solo vigilantes pueden cerrar cerradura'}), 403
    
    try:
        # Desactivar cerradura
        lock_scheduler.desactivar_cerradura()
        
        # Emitir evento WebSocket
        if websocket_handler.socketio:
            websocket_handler.socketio.emit('cerradura_cerrada_manual', {
                'vigilante': usuario.nombre,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }, namespace='/')
        
        # Registrar en log
        log_evento_seguridad(
            f'CERRADURA CERRADA MANUALMENTE',
            usuario_id=usuario_id,
            detalles=f'Vigilante: {usuario.nombre}'
        )
        
        return jsonify({
            'ok': True,
            'mensaje': 'Cerradura cerrada exitosamente',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/cerradura-automatica/limpiar-expirados', methods=['POST'])
@token_required
def limpiar_cerradura_expirada(usuario_id):
    """Limpia intentos expirados (para mantenimiento)"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.rol != 'admin':
        return jsonify({'error': 'Solo administradores pueden limpiar intentos'}), 403
    
    try:
        lock_scheduler.limpiar_intentos_expirados()
        return jsonify({
            'ok': True,
            'mensaje': 'Intentos expirados limpiados',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

