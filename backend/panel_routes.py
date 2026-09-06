"""
═══════════════════════════════════════════════════════════════════════════════
  PANEL SECURITY ROUTES — Endpoints de Seguridad de Paneles
  Sistema de Control de Ingresos SENA
═══════════════════════════════════════════════════════════════════════════════
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from functools import wraps
from models import db, Usuario
from panel_security import (
    panel_seguro,
    validar_sesion_panel,
    cerrar_sesion_panel,
    endpoint_obtener_token_panel
)
from security_advanced import AuditoriaAdministrativa
from security_shield import log_evento_seguridad

panel_bp = Blueprint('panel', __name__, url_prefix='/api/security')


@panel_bp.route('/panel/vigilancia', methods=['GET'])
@panel_seguro('vigilancia')
def panel_vigilancia():
    """
    Acceso al panel de vigilancia.
    
    Requiere:
    - JWT token válido en Authorization header
    - Token de sesión de panel en X-Panel-Session-Token
    - Usuario con rol 'vigilante' o 'admin'
    
    Retorna: Información de sesión válida
    """
    from os import getenv
    import jwt
    
    # Extraer usuario y token del JWT
    SECRET_KEY = getenv('JWT_SECRET_KEY', '')
    auth_header = request.headers.get('Authorization', '')
    token_jwt = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else ''
    
    try:
        payload = jwt.decode(token_jwt, SECRET_KEY, algorithms=['HS256'])
        usuario_id = payload.get('usuario_id')
        usuario = Usuario.query.get(usuario_id)
    except:
        usuario = None
    
    token_sesion = request.headers.get('X-Panel-Session-Token', '')
    
    if not usuario:
        return jsonify({'ok': False, 'error': 'Usuario no válido'}), 401
    
    return jsonify({
        'ok': True,
        'panel': 'vigilancia',
        'usuario': {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'rol': usuario.rol,
            'email': usuario.email
        },
        'sesion': {
            'token': token_sesion,
            'creada_en': datetime.utcnow().isoformat() + 'Z',
            'valida': True
        },
        'mensaje': 'Acceso autorizado al panel de vigilancia'
    }), 200


@panel_bp.route('/panel/administracion', methods=['GET'])
@panel_seguro('administracion')
def panel_administracion():
    """
    Acceso al panel de administración.
    
    Requiere:
    - JWT token válido en Authorization header
    - Token de sesión de panel en X-Panel-Session-Token
    - Usuario con rol 'admin'
    
    Retorna: Información de sesión válida
    """
    from os import getenv
    import jwt
    
    # Extraer usuario y token del JWT
    SECRET_KEY = getenv('JWT_SECRET_KEY', '')
    auth_header = request.headers.get('Authorization', '')
    token_jwt = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else ''
    
    try:
        payload = jwt.decode(token_jwt, SECRET_KEY, algorithms=['HS256'])
        usuario_id = payload.get('usuario_id')
        usuario = Usuario.query.get(usuario_id)
    except:
        usuario = None
    
    token_sesion = request.headers.get('X-Panel-Session-Token', '')
    
    if not usuario:
        return jsonify({'ok': False, 'error': 'Usuario no válido'}), 401
    
    return jsonify({
        'ok': True,
        'panel': 'administracion',
        'usuario': {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'rol': usuario.rol,
            'email': usuario.email
        },
        'sesion': {
            'token': token_sesion,
            'creada_en': datetime.utcnow().isoformat() + 'Z',
            'valida': True
        },
        'mensaje': 'Acceso autorizado al panel de administración'
    }), 200


@panel_bp.route('/validate-panel-session', methods=['POST'])
def validate_panel_session():
    """
    Valida que la sesión de panel sea válida (endpoint para frontend).
    
    Body JSON:
    {
      "panel": "vigilancia|administracion"
    }
    
    Headers requeridos:
    - Authorization: Bearer <jwt_token>
    - X-Panel-Session-Token: <panel_session_token>
    
    Retorna:
    - 200: Sesión válida
    - 401: Token inválido
    - 410: Sesión expirada
    """
    from os import getenv
    import jwt
    
    SECRET_KEY = getenv('JWT_SECRET_KEY', '')
    
    # 1. Obtener JWT token
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'valid': False, 'error': 'Token requerido'}), 401
    
    try:
        token_jwt = auth_header.split(' ')[1]
        payload = jwt.decode(token_jwt, SECRET_KEY, algorithms=['HS256'])
        usuario_id = payload.get('usuario_id')
    except jwt.ExpiredSignatureError:
        return jsonify({'valid': False, 'error': 'Token expirado'}), 401
    except Exception:
        return jsonify({'valid': False, 'error': 'Token inválido'}), 401
    
    # 2. Obtener token de sesión de panel
    token_sesion = request.headers.get('X-Panel-Session-Token', '')
    datos = request.get_json(silent=True) or {}
    panel = datos.get('panel', 'vigilancia')
    
    if not token_sesion:
        return jsonify({'valid': False, 'error': 'Token de sesión requerido'}), 401
    
    # 3. Validar sesión de panel
    es_valido, msg_error = validar_sesion_panel(token_sesion, usuario_id, panel)
    
    if es_valido:
        usuario = Usuario.query.get(usuario_id)
        if usuario:
            return jsonify({
                'valid': True,
                'usuario': {
                    'id': usuario.id,
                    'nombre': usuario.nombre,
                    'rol': usuario.rol
                },
                'panel': panel,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }), 200
        else:
            return jsonify({
                'valid': False,
                'error': 'Usuario no encontrado',
                'code': 'USER_NOT_FOUND'
            }), 401
    else:
        return jsonify({
            'valid': False,
            'error': msg_error,
            'code': 'SESSION_INVALID'
        }), 410


@panel_bp.route('/panel-heartbeat', methods=['POST'])
def panel_heartbeat():
    """
    Mantiene viva la sesión de panel (heartbeat).
    El frontend debe llamar a este endpoint periódicamente (cada 5 minutos).
    
    Body JSON:
    {
      "panel": "vigilancia|administracion"
    }
    
    Headers requeridos:
    - Authorization: Bearer <jwt_token>
    - X-Panel-Session-Token: <panel_session_token>
    
    Retorna:
    - 200: Sesión renovada
    - 410: Sesión expirada
    """
    from os import getenv
    import jwt
    
    SECRET_KEY = getenv('JWT_SECRET_KEY', '')
    
    # 1. Validar JWT
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'ok': False, 'error': 'Token requerido'}), 401
    
    try:
        token_jwt = auth_header.split(' ')[1]
        payload = jwt.decode(token_jwt, SECRET_KEY, algorithms=['HS256'])
        usuario_id = payload.get('usuario_id')
    except jwt.ExpiredSignatureError:
        return jsonify({'ok': False, 'error': 'Token expirado'}), 401
    except Exception:
        return jsonify({'ok': False, 'error': 'Token inválido'}), 401
    
    # 2. Validar token de sesión
    token_sesion = request.headers.get('X-Panel-Session-Token', '')
    datos = request.get_json(silent=True) or {}
    panel = datos.get('panel', 'vigilancia')
    
    if not token_sesion:
        return jsonify({'ok': False, 'error': 'Token de sesión requerido'}), 401
    
    es_valido, msg_error = validar_sesion_panel(token_sesion, usuario_id, panel)
    
    if es_valido:
        return jsonify({
            'ok': True,
            'mensaje': 'Heartbeat recibido',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
    else:
        return jsonify({
            'ok': False,
            'error': msg_error,
            'code': 'SESSION_EXPIRED'
        }), 410


@panel_bp.route('/panel-leaving', methods=['POST'])
def panel_leaving():
    """
    El frontend notifica que el usuario está cerrando la sesión (unload).
    
    Body JSON:
    {
      "panel": "vigilancia|administracion",
      "reason": "page_unload|manual_logout|inactivity"
    }
    
    Headers requeridos:
    - Authorization: Bearer <jwt_token>
    - X-Panel-Session-Token: <panel_session_token>
    
    Retorna:
    - 200: OK, sesión cerrada
    """
    from os import getenv
    import jwt
    
    SECRET_KEY = getenv('JWT_SECRET_KEY', '')
    
    # Intentar extraer información, pero no fallar si no está completa
    auth_header = request.headers.get('Authorization', '')
    token_sesion = request.headers.get('X-Panel-Session-Token', '')
    datos = request.get_json(silent=True) or {}
    panel = datos.get('panel', 'unknown')
    reason = datos.get('reason', 'unknown')
    
    usuario_id = None
    try:
        if auth_header.startswith('Bearer '):
            token_jwt = auth_header.split(' ')[1]
            payload = jwt.decode(token_jwt, SECRET_KEY, algorithms=['HS256'])
            usuario_id = payload.get('usuario_id')
    except:
        pass
    
    # Intentar cerrar sesión
    if token_sesion:
        cerrar_sesion_panel(token_sesion)
    
    # Log de salida
    if usuario_id:
        log_evento_seguridad(
            'PANEL_LEAVING',
            usuario_id=usuario_id,
            detalles=f'Panel: {panel}, Reason: {reason}',
            severidad='INFO'
        )
    
    return jsonify({
        'ok': True,
        'mensaje': f'Sesión cerrada - Razón: {reason}',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200


@panel_bp.route('/obtain-panel-token', methods=['POST'])
def obtain_panel_token():
    """
    Obtiene un nuevo token de sesión de panel después del login.
    
    Llamado desde el login después de autenticarse exitosamente.
    
    Body JSON:
    {
      "panel": "vigilancia|administracion"
    }
    
    Headers requeridos:
    - Authorization: Bearer <jwt_token>
    
    Retorna:
    - 200: Token de sesión de panel generado
    - 401: Token inválido
    - 403: Usuario no autorizado para el panel
    """
    from os import getenv
    import jwt
    
    SECRET_KEY = getenv('JWT_SECRET_KEY', '')
    
    # 1. Validar JWT
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Token requerido'}), 401
    
    try:
        token_jwt = auth_header.split(' ')[1]
        payload = jwt.decode(token_jwt, SECRET_KEY, algorithms=['HS256'])
        usuario_id = payload.get('usuario_id')
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expirado'}), 401
    except Exception:
        return jsonify({'error': 'Token inválido'}), 401
    
    # 2. Obtener usuario y panel
    usuario = Usuario.query.get(usuario_id)
    if not usuario or not usuario.activo:
        return jsonify({'error': 'Usuario no válido'}), 401
    
    datos = request.get_json(silent=True) or {}
    panel = datos.get('panel', '').strip().lower()
    
    if not panel:
        return jsonify({'error': 'Panel requerido'}), 400
    
    # 3. Validar permisos
    from panel_security import PANEL_PERMISSIONS
    paneles_permitidos = PANEL_PERMISSIONS.get(usuario.rol.lower(), [])
    if panel not in paneles_permitidos:
        return jsonify({
            'error': f'Usuario no autorizado para panel {panel}',
            'paneles_permitidos': paneles_permitidos
        }), 403
    
    # 4. Generar token de sesión
    panel_sesion_data = endpoint_obtener_token_panel(usuario_id, panel)
    
    return jsonify({
        'ok': True,
        'panel_sesion': panel_sesion_data,
        'usuario': {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'rol': usuario.rol
        }
    }), 200
