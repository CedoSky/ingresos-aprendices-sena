from flask import Blueprint, request, jsonify, send_file, session
from functools import wraps
from datetime import datetime, timedelta
import jwt
import os
import threading
import time
import websocket_handler
from models import db, Usuario, Persona, RegistroAcceso, CambioHistorial, Respaldo, Foto, Computador, RegistroAccesoEquipo, OcupacionAmbiente, RegistroInventario, Edificio, AperturaAmbiente
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

api_bp = Blueprint('api', __name__, url_prefix='/api')

SECRET_KEY = os.getenv('JWT_SECRET_KEY')
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
        )
        db.session.add(ocupacion)
        db.session.commit()
        emitir_evento_ambiente('ambiente_ocupado', ocupacion, persona)
        # Auto-abrir cerradura al registrar entrada del instructor.
        # Duración según piso: 1-2 → 2 min, 3-4 → 4 min, 5+ → 6 min
        _nombre_amb = registro.ambiente or 'Sin especificar'
        import re as _re
        _m = _re.search(r'PISO\s+(\d+)', _nombre_amb, _re.IGNORECASE)
        _piso_num = int(_m.group(1)) if _m else 1
        if _piso_num <= 2:
            _minutos_cer = 2
        elif _piso_num <= 4:
            _minutos_cer = 4
        else:
            _minutos_cer = 6
        abrir_cerradura_ambiente(
            ambiente=_nombre_amb,
            persona=persona,
            origen='instructor',
            delay_minutos=_minutos_cer
        )
        return ocupacion

    # SALIDA del instructor: cancelar apertura pendiente o cerrar cerradura abierta.
    if tipo.upper() == 'SALIDA':
        _amb_salida = registro.ambiente or None
        if _amb_salida:
            apertura_activa = AperturaAmbiente.query.filter_by(
                ambiente=_amb_salida, cerrado_en=None, deleted_at=None
            ).order_by(AperturaAmbiente.abierto_en.desc()).first()
            if apertura_activa:
                apertura_activa.cerrado_en = datetime.utcnow()
                db.session.commit()
                try:
                    if websocket_handler.socketio:
                        websocket_handler.socketio.emit('cerradura_cerrada', {
                            'ambiente':   _amb_salida,
                            'cerrado_en': apertura_activa.cerrado_en.isoformat() + 'Z',
                            'origen':     'instructor_salida',
                        })
                except Exception as _e:
                    print(f'[CERRADURA] Error emitiendo cierre por salida instructor: {_e}')
    return None


def abrir_cerradura_ambiente(ambiente, persona=None, usuario_id=None, origen='sistema', delay_minutos=0):
    """
    Registra una apertura de cerradura.
    - delay_minutos=0  → abre inmediatamente (vigilante).
    - delay_minutos>0  → abre después del delay (instructor); queda indefinida.
    La cerradura se cierra sólo por cierre manual o salida del instructor.
    """
    import threading as _thr, time as _time
    ahora = datetime.utcnow()
    abre_en = ahora + timedelta(minutes=delay_minutos) if delay_minutos > 0 else ahora
    persona_nombre = persona.nombre if persona else 'Vigilante'

    apertura = AperturaAmbiente(
        ambiente=ambiente,
        abierto_por_persona_id=persona.id if persona else None,
        abierto_por_usuario_id=usuario_id,
        origen=origen,
        duracion_minutos=delay_minutos,
        abierto_en=abre_en,
    )
    db.session.add(apertura)
    db.session.commit()

    if delay_minutos > 0:
        # Notificar que hay apertura programada
        try:
            if websocket_handler.socketio:
                websocket_handler.socketio.emit('cerradura_pendiente', {
                    'ambiente':           ambiente,
                    'origen':             origen,
                    'abierto_por':        persona_nombre,
                    'abre_en':            abre_en.isoformat() + 'Z',
                    'segundos_para_abrir': delay_minutos * 60,
                })
        except Exception as e:
            print(f'[CERRADURA] Error emitiendo pendiente: {e}')
        # Hilo daemon: espera el delay y emite apertura real
        def _emitir_cuando_abra():
            _time.sleep(delay_minutos * 60)
            try:
                if websocket_handler.socketio:
                    websocket_handler.socketio.emit('cerradura_abierta', {
                        'ambiente':  ambiente,
                        'origen':    origen,
                        'abierto_por': persona_nombre,
                        'abierto_en': abre_en.isoformat() + 'Z',
                    })
            except Exception as _e:
                print(f'[CERRADURA] Error emitiendo apertura programada: {_e}')
            try:
                _encolar_cmd_esp32(ambiente, 'abrir', 10)
            except Exception as _e_esp:
                print(f'[ESP32] Error encolando apertura retardada: {_e_esp}')
        _thr.Thread(target=_emitir_cuando_abra, daemon=True).start()
    else:
        # Apertura inmediata
        try:
            if websocket_handler.socketio:
                websocket_handler.socketio.emit('cerradura_abierta', {
                    'ambiente':  ambiente,
                    'origen':    origen,
                    'abierto_en': abre_en.isoformat() + 'Z',
                    'abierto_por': persona_nombre,
                })
        except Exception as e:
            print(f'[CERRADURA] Error emitiendo apertura: {e}')
        try:
            _encolar_cmd_esp32(ambiente, 'abrir', 10)
        except Exception as _e_esp:
            print(f'[ESP32] Error encolando apertura inmediata: {_e_esp}')
    return apertura


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
    """Endpoint público para buscar persona por número de documento (para ingreso.html)"""
    codigo = request.args.get('numero_doc', '').strip()
    
    if not codigo or len(codigo) < 5:
        return jsonify({'error': 'Número de documento inválido'}), 400
    
    try:
        persona = Persona.query.filter_by(numero_doc=codigo, deleted_at=None).first()
        
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
        else:
            return jsonify({'found': False, 'error': 'Número de identidad no encontrado en la base de datos'}), 404
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
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = request.args.get('por_pagina', 20, type=int)
    perfil = request.args.get('perfil', None)
    buscar = request.args.get('buscar', None)
    
    query = Persona.query.filter_by(deleted_at=None)
    
    if perfil:
        query = query.filter_by(perfil=perfil)
    
    if buscar:
        query = query.filter(
            (Persona.nombre.ilike(f'%{buscar}%')) |
            (Persona.numero_doc.ilike(f'%{buscar}%'))
        )
    
    paginated = query.paginate(page=pagina, per_page=por_pagina, error_out=False)
    
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
        datos = request.get_json()
        
        if not datos:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        numero_doc = datos.get('numero_doc')
        if not numero_doc:
            return jsonify({'error': 'numero_doc is required'}), 400
        
        if Persona.query.filter_by(numero_doc=numero_doc, deleted_at=None).first():
            return jsonify({'error': 'Documento ya existe'}), 400
        
        persona = Persona(
            nombre=datos.get('nombre', 'Sin nombre'),
            tipo_doc=datos.get('tipo_doc', 'CC'),
            numero_doc=numero_doc,
            email=datos.get('email'),
            telefono=datos.get('telefono'),
            perfil=datos.get('perfil', 'APRENDIZ'),
            programa=datos.get('programa'),
            ficha=datos.get('ficha'),
            especialidad=datos.get('especialidad'),
            area=datos.get('area'),
            creado_por_id=usuario_id,
            actualizado_por_id=usuario_id
        )
        
        db.session.add(persona)
        db.session.commit()

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
        except Exception:
            pass

        # Correo de bienvenida al aprendiz/instructor si tiene email
        srv_correo.bienvenida_nueva_persona({
            'nombre':     persona.nombre,
            'numero_doc': persona.numero_doc,
            'tipo_doc':   persona.tipo_doc,
            'perfil':     persona.perfil,
            'programa':   persona.programa,
            'ficha':      persona.ficha,
            'email':      persona.email,
        })

        return jsonify({'id': persona.id, 'numero_doc': persona.numero_doc}), 201
    except Exception as e:
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
            )
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
    )
    db.session.add(cambio)
    db.session.commit()

    # Emitir evento en tiempo real
    try:
        if websocket_handler.socketio:
            websocket_handler.socketio.emit('persona_eliminada', {'id': persona_id}, namespace='/')
    except Exception:
        pass

    return jsonify({'mensaje': 'Eliminado'}), 200

@api_bp.route('/registros-acceso', methods=['POST'])
@token_required
def registrar_acceso(usuario_id):
    datos = request.get_json()
    numero_doc = datos.get('numero_doc')
    tipo = datos.get('tipo', 'ENTRADA')
    
    persona = Persona.query.filter_by(numero_doc=numero_doc, deleted_at=None).first()
    if not persona:
        return jsonify({'error': 'Persona no encontrada'}), 404
    
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
    )
    
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
            )
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
        )
        db.session.add(reg_equipo)

    db.session.commit()

    emitir_evento_acceso_tiempo_real(registro, persona)
    try:
        gestionar_ocupacion_instructor(persona, registro, tipo)
    except Exception as _e_gest:
        print(f'[OCUPACION] Error en gestionar_ocupacion_instructor: {_e_gest}')
        # No interrumpir el registro por fallo en cerradura/ocupación

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
        RegistroAcceso.deleted_at == None
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


@api_bp.route('/registros-acceso/busqueda-global', methods=['GET'])
@token_required
def busqueda_global_registros(usuario_id):
    """Busca registros en TODA la base de datos (todos los vigilantes). Uso: investigación."""
    numero_doc = request.args.get('numero_doc', '').strip()
    nombre = request.args.get('nombre', '').strip()
    pagina = request.args.get('pagina', 1, type=int)

    if not numero_doc and not nombre:
        return jsonify({'error': 'Proporciona numero_doc o nombre para buscar'}), 400

    query = RegistroAcceso.query.filter_by(deleted_at=None)
    if numero_doc:
        query = query.filter(RegistroAcceso.numero_doc.like(f'%{numero_doc}%'))
    if nombre:
        query = query.join(Persona, RegistroAcceso.persona_id == Persona.id)\
                     .filter(Persona.nombre.ilike(f'%{nombre}%'))

    paginated = query.order_by(RegistroAcceso.timestamp.desc()).paginate(page=pagina, per_page=50, error_out=False)

    registros = []
    for r in paginated.items:
        vig = Usuario.query.get(r.vigilante_id) if r.vigilante_id else None
        registros.append({
            'id': r.id,
            'numero_doc': r.numero_doc,
            'tipo': r.tipo,
            'timestamp': r.timestamp.isoformat() + 'Z',
            'created_at': r.timestamp.isoformat() + 'Z',
            'ambiente': r.ambiente,
            'vigilante': {'nombre': vig.nombre, 'email': vig.email} if vig else None,
            'persona': {
                'id': r.persona.id if r.persona else None,
                'nombre': r.persona.nombre if r.persona else 'N/A',
                'numero_doc': r.persona.numero_doc if r.persona else r.numero_doc,
                'perfil': r.persona.perfil if r.persona else None,
                'ficha': r.persona.ficha if r.persona else None,
                'programa': r.persona.programa if r.persona else None,
            }
        })

    return jsonify({'registros': registros, 'total': paginated.total, 'pagina': pagina}), 200


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
        Persona.deleted_at == None
    ).first()
    if not persona:
        # fallback: búsqueda parcial
        persona = Persona.query.filter(
            Persona.numero_doc.contains(codigo),
            Persona.deleted_at == None
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
            perfil='VISITANTE'
        )
        db.session.add(persona)
        db.session.flush()
    
    registro = RegistroAcceso(
        persona_id=persona.id,
        numero_doc=numero_doc,
        tipo=tipo,
        timestamp=datetime.utcnow(),
        ambiente=datos.get('ambiente', 'Entrada principal')
    )
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
                tamaño_bytes=len(imagen_bytes)
            )
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
            Computador.deleted_at != None
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
        )
        
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
            perfil='VISITANTE'
        )
        db.session.add(persona)
        db.session.flush()
    
    registro = RegistroAcceso(
        persona_id=persona.id,
        numero_doc=numero_doc,
        tipo=tipo,
        timestamp=datetime.utcnow(),
        ambiente=datos.get('ambiente', 'Entrada principal')
    )
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
                tamaño_bytes=len(imagen_bytes)
            )
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
        Computador.deleted_at == None
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
            perfil='VISITANTE'
        )
        db.session.add(persona)
        db.session.flush()
    
    # Registrar acceso de persona
    registro_persona = RegistroAcceso(
        persona_id=persona.id,
        numero_doc=numero_doc,
        tipo=tipo,
        timestamp=datetime.utcnow(),
        ambiente=datos.get('ambiente', 'Entrada principal')
    )
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
                tamaño_bytes=len(imagen_bytes)
            )
            db.session.add(foto)
        except:
            pass
    
    # Obtener y registrar equipos PERMANENTEMENTE asignados
    equipos = Computador.query.filter(
        Computador.asignado_a_id == persona.id,
        Computador.deleted_at == None
    ).all()
    
    equipos_registrados = []
    for equipo in equipos:
        # Registrar acceso del equipo
        reg_equipo = RegistroAccesoEquipo(
            computador_id=equipo.id,
            persona_id=persona.id,
            tipo=tipo,
            timestamp=datetime.utcnow(),
            registro_acceso_id=registro_persona.id
        )
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
            tamaño_bytes=len(imagen_datos)
        )
        
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
        
        if not persona:
            persona = Persona(
                nombre=nombre,
                tipo_doc=tipo_doc,
                numero_doc=numero_doc,
                perfil='visitante',
                verificado=False
            )
            db.session.add(persona)
            db.session.commit()
        
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
        )
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
        
        if not persona and nombre:
            tipo_doc = datos.get('tipo_doc', 'CC')
            persona = Persona(
                nombre=nombre,
                tipo_doc=tipo_doc,
                numero_doc=numero_doc,
                perfil='visitante',
                verificado=False
            )
            db.session.add(persona)
            db.session.commit()
        
        if not persona:
            return jsonify({'error': 'Persona no encontrada'}), 404

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
        )
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
        )
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


# ─────────────────────────────────────────────
#  CERRADURA ELECTRÓNICA DE AMBIENTES
# ─────────────────────────────────────────────

@api_bp.route('/ambientes/cerradura/abrir', methods=['POST'])
@token_required
def api_abrir_cerradura(usuario_id):
    """Vigilante abre manualmente la cerradura de un ambiente."""
    datos = request.get_json()
    ambiente = (datos.get('ambiente') or '').strip()
    if not ambiente:
        return jsonify({'error': 'Ambiente requerido'}), 400
    # Calcular minutos según piso: pisos 1-2 → 2 min, 3-4 → 4 min, 5+ → 6 min
    apertura = abrir_cerradura_ambiente(
        ambiente=ambiente,
        usuario_id=usuario_id,
        origen='vigilante',
        delay_minutos=0
    )
    return jsonify({
        'ok': True,
        'ambiente': ambiente,
        'abierto_en':  apertura.abierto_en.isoformat() + 'Z',
        'mensaje':     'Cerradura abierta. Cierra sólo manualmente.',
    }), 201


@api_bp.route('/ambientes/cerradura/cerrar', methods=['POST'])
@token_required
def api_cerrar_cerradura(usuario_id):
    """Cierra manualmente una cerradura antes de que expire."""
    datos = request.get_json()
    ambiente = (datos.get('ambiente') or '').strip()
    if not ambiente:
        return jsonify({'error': 'Ambiente requerido'}), 400
    ahora = datetime.utcnow()
    apertura = AperturaAmbiente.query.filter_by(
        ambiente=ambiente, cerrado_en=None, deleted_at=None
    ).order_by(AperturaAmbiente.abierto_en.desc()).first()
    if not apertura:
        return jsonify({'error': 'No hay cerradura abierta para este ambiente'}), 404
    apertura.cerrado_en = ahora
    apertura.cerrado_por_usuario_id = usuario_id
    db.session.commit()
    try:
        if websocket_handler.socketio:
            websocket_handler.socketio.emit('cerradura_cerrada', {
                'ambiente':   ambiente,
                'cerrado_en': ahora.isoformat() + 'Z',
            })
    except Exception as e:
        print(f'[CERRADURA] Error emitiendo cierre: {e}')
    try:
        _encolar_cmd_esp32(ambiente, 'cerrar', 0)
    except Exception as _e_esp:
        print(f'[ESP32] Error encolando cierre: {_e_esp}')
    return jsonify({'ok': True, 'ambiente': ambiente}), 200


@api_bp.route('/ambientes/cerradura/estado', methods=['GET'])
@token_required
def api_estado_cerraduras(usuario_id):
    """Estado actual (abierto/cerrado + tiempo restante) de todas las cerraduras."""
    from sqlalchemy import func
    ahora = datetime.utcnow()
    subq = db.session.query(
        AperturaAmbiente.ambiente,
        func.max(AperturaAmbiente.abierto_en).label('ultima')
    ).filter(AperturaAmbiente.deleted_at.is_(None)).group_by(AperturaAmbiente.ambiente).subquery()

    ultimas = db.session.query(AperturaAmbiente).join(
        subq,
        db.and_(
            AperturaAmbiente.ambiente == subq.c.ambiente,
            AperturaAmbiente.abierto_en == subq.c.ultima,
        )
    ).all()

    resultado = []
    for ap in ultimas:
        ahora_c = datetime.utcnow()
        pendiente = ap.cerrado_en is None and ap.abierto_en > ahora_c
        abierto   = ap.cerrado_en is None and ap.abierto_en <= ahora_c
        try:
            abierto_por = (ap.usuario.nombre if ap.usuario else None) or (ap.persona.nombre if ap.persona else None) or 'Sistema'
        except Exception:
            abierto_por = 'Sistema'
        seg_para_abrir = max(0, int((ap.abierto_en - ahora_c).total_seconds())) if pendiente else 0
        resultado.append({
            'ambiente':           ap.ambiente,
            'abierto':            abierto,
            'pendiente':          pendiente,
            'origen':             ap.origen,
            'abierto_por':        abierto_por,
            'abierto_en':         ap.abierto_en.isoformat() + 'Z',
            'segundos_para_abrir': seg_para_abrir,
            'segundos_restantes': 0,
        })
    return jsonify(resultado), 200


@api_bp.route('/ambientes/cerradura/historial', methods=['GET'])
@token_required
def api_historial_cerraduras(usuario_id):
    """Historial completo de aperturas y cierres de cerraduras (guarda quién abrió/cerró)."""
    limite = min(int(request.args.get('limite', 50)), 200)
    registros = AperturaAmbiente.query.filter_by(deleted_at=None)\
        .order_by(AperturaAmbiente.abierto_en.desc()).limit(limite).all()
    ahora = datetime.utcnow()
    resultado = []
    for ap in registros:
        try:
            if ap.usuario:
                abierto_por = ap.usuario.nombre
            elif ap.persona:
                abierto_por = ap.persona.nombre + ' (instructor)'
            else:
                abierto_por = 'Sistema'
        except Exception:
            abierto_por = 'Sistema'
        try:
            if ap.cerrado_en:
                try:
                    cerrado_por = ap.cerrado_by.nombre + ' (manual)' if ap.cerrado_by else 'Instructor (salida)'
                except Exception:
                    cerrado_por = 'Manual'
                cerrado_en_iso = ap.cerrado_en.isoformat() + 'Z'
            else:
                cerrado_por = None
                cerrado_en_iso = None
        except Exception:
            cerrado_por = None
            cerrado_en_iso = None
        activo     = ap.cerrado_en is None and ap.abierto_en <= ahora
        pendiente_h = ap.cerrado_en is None and ap.abierto_en > ahora
        resultado.append({
            'id':               ap.id,
            'ambiente':         ap.ambiente,
            'origen':           ap.origen,
            'abierto_por':      abierto_por,
            'abierto_en':       ap.abierto_en.isoformat() + 'Z',
            'cerrado_por':      cerrado_por,
            'cerrado_en':       cerrado_en_iso,
            'duracion_minutos': ap.duracion_minutos,
            'activo':           activo,
            'pendiente':        pendiente_h,
        })
    return jsonify(resultado), 200


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
            RegistroAcceso.deleted_at == None,
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

        # ── 6. Eliminar solo los registros del turno (HOY) + ambientes ───
        # Primero eliminar registros de equipos asociados
        ids_registros = [r.id for r in registros_db]
        if ids_registros:
            RegistroAccesoEquipo.query.filter(
                RegistroAccesoEquipo.registro_acceso_id.in_(ids_registros)
            ).delete(synchronize_session='fetch')
            
            # Luego eliminar registros de acceso del día
            RegistroAcceso.query.filter(
                RegistroAcceso.id.in_(ids_registros)
            ).delete(synchronize_session='fetch')
        
        # Limpiar ocupación de ambientes
        OcupacionAmbiente.query.delete()
        db.session.commit()

        # Notificar a todas las páginas conectadas que los registros fueron limpiados
        try:
            if websocket_handler.socketio:
                websocket_handler.socketio.emit('registros_limpiados', {
                    'motivo': 'cerrar_turno',
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
                    )
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
             .filter_by(estado='EN_SEDE')
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
    q = (RegistroInventario.query
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
    )
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
        ).filter(RegistroAcceso.deleted_at == None,
                 RegistroAcceso.persona_id != None)
         .group_by(RegistroAcceso.persona_id).subquery())

        registros = (db.session.query(RegistroAcceso, Persona)
            .join(sub, (RegistroAcceso.persona_id == sub.c.persona_id) &
                       (RegistroAcceso.timestamp == sub.c.ultima))
            .join(Persona, RegistroAcceso.persona_id == Persona.id)
            .filter(RegistroAcceso.tipo == 'ENTRADA',
                    RegistroAcceso.deleted_at == None,
                    Persona.deleted_at == None)
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
                             RegistroAcceso.deleted_at == None)
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
                Edificio.deleted_at == None
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
        if 'orden' in d:
            ed.orden = int(d['orden'])
        db.session.commit()
        return jsonify({'mensaje': 'Edificio actualizado'}), 200
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


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
    _MAINTENANCE_STATE['activo']  = bool(data.get('activo', False))
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


# ═══════════════════════════════════════════════════════════════════════════════
#  ESP32 — INTEGRACIÓN CERRADURA FÍSICA
#  El ESP32 hace polling a /api/esp32/comando/<id>?key=<k> para recibir órdenes.
#  El frontend puede también llamar al ESP32 directamente por su IP local.
# ═══════════════════════════════════════════════════════════════════════════════
import threading as _esp_thr
import time     as _esp_time
import re       as _esp_re

# Registro en memoria: { device_id: {ip, key, ambiente, ultimo_ping, pending_cmd, pending_seg} }
_esp32_devices: dict = {}
_esp32_lock = _esp_thr.Lock()


def _encolar_cmd_esp32(ambiente: str, cmd: str, segundos: int = 15):
    """Encola un comando para todos los ESP32 registrados asociados a ese ambiente."""
    segundos = min(segundos, 15)  # nunca superar 15 s (indicación fabricante cerradura)
    with _esp32_lock:
        for dev_id, dev in _esp32_devices.items():
            amb_dev = (dev.get('ambiente') or '').strip()
            # Aplica si el ESP32 está asociado al mismo ambiente O no tiene ambiente
            if not amb_dev or amb_dev == ambiente:
                dev['pending_cmd'] = cmd
                dev['pending_seg'] = segundos
                print(f'[ESP32] Comando "{cmd}" encolado para {dev_id} '
                      f'(ambiente registrado: "{amb_dev or "todos"}")')


def _verificar_key_esp32(device_id: str, key: str) -> bool:
    """Verifica que el device_id y key coincidan con el registro."""
    with _esp32_lock:
        dev = _esp32_devices.get(device_id)
        if not dev:
            return False
        return dev.get('key') == key


@api_bp.route('/esp32/registrar', methods=['POST'])
def esp32_registrar():
    """ESP32 o frontend POST para registrar/actualizar un dispositivo. Sin auth JWT."""
    datos = request.get_json(silent=True) or {}
    device_id = (datos.get('device_id') or '').strip()
    ip        = (datos.get('ip') or '').strip()
    key       = (datos.get('key') or '').strip()
    ambiente  = (datos.get('ambiente') or '').strip()
    try:
        pin = int(datos.get('pin', 26))
        if not (0 <= pin <= 39):
            pin = 26
    except (TypeError, ValueError):
        pin = 26

    if not device_id or not key:
        return jsonify({'error': 'device_id y key son requeridos'}), 400

    # Validar IPv4 básica
    if ip and not _esp_re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
        return jsonify({'error': 'IP inválida'}), 400

    with _esp32_lock:
        _esp32_devices[device_id] = {
            'ip':          ip,
            'key':         key,
            'ambiente':    ambiente,
            'pin':         pin,
            'ultimo_ping': _esp_time.time(),
            'pending_cmd': None,
            'pending_seg': 10,
        }
    print(f'[ESP32] Registrado: {device_id} @ {ip or "sin-IP"} → ambiente: "{ambiente or "todos"}" · pin GPIO{pin}')
    return jsonify({'ok': True, 'device_id': device_id}), 200


@api_bp.route('/esp32/comando/<device_id>', methods=['GET'])
def esp32_polling_comando(device_id):
    """ESP32 consulta si hay comando pendiente. Usa ?key=<k> para autenticar."""
    key = request.args.get('key', '')
    if not _verificar_key_esp32(device_id, key):
        return jsonify({'error': 'No autorizado'}), 401

    with _esp32_lock:
        dev = _esp32_devices.get(device_id)
        if not dev:
            return jsonify({'cmd': 'ninguno'}), 200
        dev['ultimo_ping'] = _esp_time.time()
        cmd = dev.pop('pending_cmd', None)      # consume el comando
        seg = dev.get('pending_seg', 10)
        pin = dev.get('pin', 26)
        if cmd:
            return jsonify({'cmd': cmd, 'segundos': seg, 'pin': pin}), 200
        return jsonify({'cmd': 'ninguno', 'pin': pin}), 200


@api_bp.route('/esp32/ack/<device_id>', methods=['POST'])
def esp32_ack(device_id):
    """ESP32 confirma que ejecutó el comando."""
    key = request.args.get('key', '')
    if not _verificar_key_esp32(device_id, key):
        return jsonify({'error': 'No autorizado'}), 401
    datos = request.get_json(silent=True) or {}
    print(f'[ESP32] ACK de {device_id}: ejecutó "{datos.get("cmd", "?")}". '
          f'Estado cerradura: {datos.get("estado", "??")}')
    return jsonify({'ok': True}), 200


@api_bp.route('/esp32/dispositivos', methods=['GET'])
@token_required
def esp32_listar_dispositivos(usuario_id):
    """Listar dispositivos ESP32 registrados (requiere sesión)."""
    ahora = _esp_time.time()
    with _esp32_lock:
        resultado = [
            {
                'device_id':   dev_id,
                'ip':          dev.get('ip', ''),
                'ambiente':    dev.get('ambiente', ''),
                'pin':         dev.get('pin', 26),
                'en_linea':    (ahora - dev.get('ultimo_ping', 0)) < 15,
                'seg_sin_ping': int(ahora - dev.get('ultimo_ping', 0)),
                'cmd_pendiente': dev.get('pending_cmd'),
            }
            for dev_id, dev in _esp32_devices.items()
        ]
    return jsonify({'dispositivos': resultado}), 200


@api_bp.route('/esp32/test', methods=['POST'])
@token_required
def esp32_test_cmd(usuario_id):
    """Encola un comando de prueba hacia un ESP32 específico."""
    datos = request.get_json(silent=True) or {}
    device_id = (datos.get('device_id') or '').strip()
    cmd       = (datos.get('cmd') or 'abrir').strip()
    segundos  = int(datos.get('segundos', 10))

    if cmd not in ('abrir', 'cerrar'):
        return jsonify({'error': 'cmd debe ser "abrir" o "cerrar"'}), 400
    if not device_id:
        return jsonify({'error': 'device_id requerido'}), 400

    with _esp32_lock:
        if device_id not in _esp32_devices:
            return jsonify({'error': 'Dispositivo no registrado'}), 404
        _esp32_devices[device_id]['pending_cmd'] = cmd
        _esp32_devices[device_id]['pending_seg'] = segundos

    print(f'[ESP32] Test "{cmd}" encolado → {device_id}')
    return jsonify({'ok': True, 'cmd': cmd, 'device_id': device_id}), 200


