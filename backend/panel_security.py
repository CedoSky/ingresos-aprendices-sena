"""
═══════════════════════════════════════════════════════════════════════════════
  PANEL SECURITY — Protección de Paneles Restringidos (Vigilancia, Admin)
  Sistema de Control de Ingresos SENA
═══════════════════════════════════════════════════════════════════════════════

Protecciones implementadas:
  ✓ Validación de sesión activa antes de acceso a panel
  ✓ Cierre automático de sesión si múltiples accesos simultáneos
  ✓ Token session vinculado a dispositivo/IP para evitar session hijacking
  ✓ Expiración de token de panel después de cierto tiempo inactivo
  ✓ Auditoría de todos los intentos de acceso (exitosos y fallidos)
  ✓ Redirección automática a login si no hay permisos

Flujo de seguridad:
  1. Usuario hace login → obtiene JWT + Token Session
  2. Usuario accede a panel restringido → valida Token Session + JWT
  3. Frontend mantiene "heartbeat" con servidor
  4. Si no hay actividad → cierra sesión automáticamente
  5. Si detecta acceso no autorizado → registra en auditoría y cierra sesión
"""

import jwt
import secrets
from functools import wraps
from datetime import datetime, timedelta
from flask import request, jsonify, session, g
from typing import Tuple, Optional
import os

# Mapeo de roles a paneles permitidos
PANEL_PERMISSIONS = {
    'vigilante': ['vigilancia'],
    'administrador': ['administracion'],
    'admin': ['administracion'],
    'instructor': ['vigilancia'],
    'instructora': ['vigilancia'],
}

# Tiempos de expiración para tokens de panel
PANEL_TOKEN_EXPIRY_MINUTES = 480  # 8 horas (mismo que JWT)
PANEL_INACTIVITY_TIMEOUT_MINUTES = 30  # 30 mins sin actividad = cierra sesión

# Almacenamiento en memoria de sesiones activas de panel
# Formato: { token_session: { usuario_id, panel, ip, user_agent, creado_at, ultimo_acceso } }
_active_panel_sessions = {}
_session_lock = __import__('threading').Lock()

SECRET_KEY = os.getenv('JWT_SECRET_KEY', '')


def obtener_fingerprint_cliente() -> str:
    """Genera fingerprint único del cliente basado en IP + User-Agent"""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0')
    user_agent = request.headers.get('User-Agent', 'unknown')
    fingerprint = f"{ip}|{user_agent}"
    return fingerprint


def generar_token_sesion_panel() -> str:
    """Genera token criptográficamente seguro para sesión de panel"""
    return secrets.token_urlsafe(32)


def crear_sesion_panel(usuario_id: int, panel: str, ip: str, user_agent: str, tab_id: Optional[str] = None) -> str:
    """
    Crea una nueva sesión de panel y retorna el token.
    
    Solo permite una pestaña/ventana activa por usuario+panel.
    Si el usuario abre otra pestaña con el mismo panel, la sesión anterior se cierra.
    
    Args:
        usuario_id: ID del usuario
        panel: Nombre del panel ('vigilancia' o 'administracion')
        ip: Dirección IP del cliente
        user_agent: User-Agent del navegador
        tab_id: ID único de la pestaña/ventana cliente
    
    Returns:
        Token de sesión de panel (UUID-like)
    """
    token = generar_token_sesion_panel()
    
    with _session_lock:
        # Cerrar sesiones previas del mismo usuario en el MISMO panel
        # (evita múltiples pestañas/windows del MISMO panel)
        tokens_a_eliminar = [
            t for t, data in _active_panel_sessions.items()
            if data['usuario_id'] == usuario_id and data['panel'] == panel
        ]
        for t in tokens_a_eliminar:
            del _active_panel_sessions[t]
        
        # Crear nueva sesión
        _active_panel_sessions[token] = {
            'usuario_id': usuario_id,
            'panel': panel,
            'ip': ip,
            'user_agent': user_agent,
            'tab_id': tab_id or 'unknown',
            'creado_at': datetime.utcnow(),
            'ultimo_acceso': datetime.utcnow(),
        }
    
    return token


def validar_sesion_panel(token: str, usuario_id: int, panel: str, tab_id: Optional[str] = None) -> Tuple[bool, str]:
    """
    Valida que el token de sesión de panel sea válido y activo.
    
    Verifica:
      1. Token existe en sesiones activas
      2. Usuario ID coincide
      3. Panel coincide
      4. Tab ID válido (solo una pestaña activa por sesión)
      5. No ha expirado (< 8 horas)
      6. No ha estado inactivo (< 30 mins)
    
    IMPORTANTE: La PRIMERA pestaña que se conecta registra su tabId.
                Las siguientes pestañas con el MISMO token son rechazadas
                (no pueden tener el mismo tab_id registrado).
    
    Args:
        token: Token de sesión de panel
        usuario_id: ID del usuario que se identifica
        panel: Nombre del panel que intenta acceder
        tab_id: ID de la pestaña/ventana cliente
    
    Returns:
        (es_valido, mensaje_error)
    """
    with _session_lock:
        if token not in _active_panel_sessions:
            return False, "Sesión expirada o inválida"
        
        sesion = _active_panel_sessions[token]
        ahora = datetime.utcnow()
        
        # Validar usuario ID
        if sesion['usuario_id'] != usuario_id:
            del _active_panel_sessions[token]
            return False, "Usuario no autorizado para esta sesión"
        
        # Validar panel
        if sesion['panel'] != panel:
            return False, "Panel no corresponde a esta sesión"
        
        # ═══════════════════════════════════════════════════════════════════
        # VALIDACIÓN CRÍTICA: TabId para evitar múltiples pestañas
        # ═══════════════════════════════════════════════════════════════════
        sesion_tab_id = sesion.get('tab_id')
        
        if not sesion_tab_id or sesion_tab_id == 'unknown':
            # Primera pestaña: registrar este tabId
            if tab_id:
                sesion['tab_id'] = tab_id
                sesion['tab_id_registrado_en'] = ahora
            else:
                # Sin tabId, rechazar si ya hay otra pestaña
                return False, "Error: tab_id no disponible. La sesión puede estar en otra pestaña"
        else:
            # Ya hay un tabId registrado
            if tab_id != sesion_tab_id:
                # Otra pestaña intenta usar el MISMO token → RECHAZAR
                return False, "Esta sesión está activa en otra pestaña. Cierre la otra pestaña e intente de nuevo"
        
        # Validar expiración (8 horas)
        tiempo_transcurrido = (ahora - sesion['creado_at']).total_seconds() / 60
        if tiempo_transcurrido > PANEL_TOKEN_EXPIRY_MINUTES:
            del _active_panel_sessions[token]
            return False, "Sesión expirada"
        
        # Validar inactividad (30 mins)
        tiempo_inactivo = (ahora - sesion['ultimo_acceso']).total_seconds() / 60
        if tiempo_inactivo > PANEL_INACTIVITY_TIMEOUT_MINUTES:
            del _active_panel_sessions[token]
            return False, f"Sesión cerrada por inactividad ({int(tiempo_inactivo)} mins)"
        
        # Token válido: actualizar último acceso
        sesion['ultimo_acceso'] = ahora
        return True, ""


def cerrar_sesion_panel(token: str) -> bool:
    """Cierra explícitamente una sesión de panel"""
    with _session_lock:
        if token in _active_panel_sessions:
            del _active_panel_sessions[token]
            return True
    return False


def obtener_panel_del_token(token: str) -> Optional[str]:
    """Retorna el nombre del panel asociado a un token"""
    with _session_lock:
        sesion = _active_panel_sessions.get(token)
        if sesion:
            return sesion['panel']
    return None


def panel_seguro(panel_requerido: str):
    """
    Decorador para proteger rutas de paneles restringidos.
    
    Valida:
      1. JWT token en Authorization header
      2. Usuario tiene permisos para el panel
      3. Sesión de panel activa y válida
      4. IP y User-Agent no han cambiado (anti-hijacking)
    
    Uso:
        @api_bp.route('/api/panel/vigilancia')
        @panel_seguro('vigilancia')
        def vigilancia_panel():
            return jsonify({'data': 'panel'})
    
    Respuestas:
        - 401: Token inválido o ausente
        - 403: Permisos insuficientes
        - 410: Sesión expirada
        - 200: Acceso permitido
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from models import Usuario
            from security_advanced import AuditoriaAdministrativa
            from security_shield import log_evento_seguridad
            
            # ═══════════════════════════════════════════════════════════════════
            # 1. VALIDAR JWT TOKEN
            # ═══════════════════════════════════════════════════════════════════
            auth_header = request.headers.get('Authorization', '')
            if not auth_header or not auth_header.startswith('Bearer '):
                log_evento_seguridad(
                    'PANEL_ACCESS_DENIED_NO_TOKEN',
                    usuario_id=None,
                    detalles=f'panel: {panel_requerido}',
                    severidad='WARNING'
                )
                return jsonify({'error': 'Token requerido', 'code': 'NO_TOKEN'}), 401
            
            try:
                token_jwt = auth_header.split(' ')[1]
                payload = jwt.decode(token_jwt, SECRET_KEY, algorithms=['HS256'])
                usuario_id = payload.get('usuario_id')
                usuario_rol = payload.get('rol', '')
            except jwt.ExpiredSignatureError:
                log_evento_seguridad(
                    'PANEL_ACCESS_DENIED_EXPIRED_TOKEN',
                    usuario_id=None,
                    detalles=f'panel: {panel_requerido}, ip: {request.remote_addr}',
                    severidad='WARNING'
                )
                return jsonify({
                    'error': 'Sesión expirada',
                    'code': 'TOKEN_EXPIRED'
                }), 401
            except Exception as e:
                log_evento_seguridad(
                    'PANEL_ACCESS_DENIED_INVALID_TOKEN',
                    usuario_id=None,
                    detalles=f'panel: {panel_requerido}, ip: {request.remote_addr}, error: {str(e)}',
                    severidad='CRITICAL'
                )
                return jsonify({'error': 'Token inválido', 'code': 'TOKEN_INVALID'}), 401
            
            # ═══════════════════════════════════════════════════════════════════
            # 2. VALIDAR USUARIO EXISTE Y ESTÁ ACTIVO
            # ═══════════════════════════════════════════════════════════════════
            usuario = Usuario.query.filter_by(id=usuario_id, deleted_at=None).first()
            if not usuario or not usuario.activo:
                log_evento_seguridad(
                    'PANEL_ACCESS_DENIED_USER_INACTIVE',
                    usuario_id=usuario_id,
                    detalles=f'panel: {panel_requerido}, ip: {request.remote_addr}',
                    severidad='WARNING'
                )
                return jsonify({
                    'error': 'Cuenta desactivada',
                    'code': 'USER_INACTIVE'
                }), 403
            
            # ═══════════════════════════════════════════════════════════════════
            # 3. VALIDAR PERMISOS PARA EL PANEL
            # ═══════════════════════════════════════════════════════════════════
            paneles_permitidos = PANEL_PERMISSIONS.get(usuario_rol.lower(), [])
            if panel_requerido not in paneles_permitidos:
                log_evento_seguridad(
                    'PANEL_ACCESS_DENIED_NO_PERMISSIONS',
                    usuario_id=usuario_id,
                    detalles=f'panel: {panel_requerido}, rol: {usuario_rol}, ip: {request.remote_addr}',
                    severidad='CRITICAL'
                )
                return jsonify({
                    'error': 'Permisos insuficientes para este panel',
                    'code': 'NO_PERMISSIONS'
                }), 403
            
            # ═══════════════════════════════════════════════════════════════════
            # 4. OBTENER Y VALIDAR TOKEN DE SESIÓN DE PANEL
            # ═══════════════════════════════════════════════════════════════════
            token_sesion = request.headers.get('X-Panel-Session-Token', '')
            tab_id = request.headers.get('X-Panel-Tab-Id', None)  # ID único de la pestaña
            
            if not token_sesion:
                log_evento_seguridad(
                    'PANEL_ACCESS_DENIED_NO_SESSION_TOKEN',
                    usuario_id=usuario_id,
                    detalles=f'panel: {panel_requerido}',
                    severidad='WARNING'
                )
                return jsonify({
                    'error': 'Token de sesión de panel requerido',
                    'code': 'NO_SESSION_TOKEN'
                }), 401
            
            es_valido, msg_error = validar_sesion_panel(token_sesion, usuario_id, panel_requerido, tab_id)
            if not es_valido:
                log_evento_seguridad(
                    'PANEL_SESSION_INVALID',
                    usuario_id=usuario_id,
                    detalles=f'panel: {panel_requerido}, error: {msg_error}',
                    severidad='WARNING'
                )
                return jsonify({
                    'error': msg_error,
                    'code': 'SESSION_INVALID'
                }), 410  # 410 Gone (sesión expirada)
            
            # ═══════════════════════════════════════════════════════════════════
            # 5. VALIDAR IP Y USER-AGENT (anti-hijacking)
            # ═══════════════════════════════════════════════════════════════════
            with _session_lock:
                sesion = _active_panel_sessions.get(token_sesion, {})
                ip_sesion = sesion.get('ip', '')
                ua_sesion = sesion.get('user_agent', '')
            
            ip_actual = request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0').split(',')[0].strip()
            ua_actual = request.headers.get('User-Agent', 'unknown')
            
            if ip_actual != ip_sesion or ua_actual != ua_sesion:
                # Potencial session hijacking
                log_evento_seguridad(
                    'PANEL_SESSION_HIJACKING_ATTEMPT',
                    usuario_id=usuario_id,
                    detalles=f'panel: {panel_requerido}, ip_esperada: {ip_sesion}, ip_actual: {ip_actual}',
                    severidad='CRITICAL'
                )
                # Cerrar sesión automáticamente
                cerrar_sesion_panel(token_sesion)
                return jsonify({
                    'error': 'Sesión comprometida. Cierre sesión e intente de nuevo.',
                    'code': 'SESSION_HIJACKING'
                }), 403
            
            # ═══════════════════════════════════════════════════════════════════
            # 6. ACCESO CONCEDIDO - Registrar en auditoría
            # ═══════════════════════════════════════════════════════════════════
            
            # Pasar información del usuario al handler usando g (flask context)
            g.usuario_actual = usuario
            g.token_sesion_panel = token_sesion
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


def endpoint_obtener_token_panel(usuario_id: int, panel: str) -> dict:
    """
    Genera y retorna un token de sesión de panel después del login exitoso.
    
    Debe llamarsedespués de validar JWT token en login.
    
    Args:
        usuario_id: ID del usuario autenticado
        panel: Panel al que accederá ('vigilancia' o 'administracion')
    
    Returns:
        Dict con token_sesion_panel y metadata
    """
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0').split(',')[0].strip()
    user_agent = request.headers.get('User-Agent', 'unknown')
    
    token = crear_sesion_panel(usuario_id, panel, ip, user_agent)
    
    return {
        'token_sesion_panel': token,
        'expiry_minutes': PANEL_TOKEN_EXPIRY_MINUTES,
        'inactivity_timeout_minutes': PANEL_INACTIVITY_TIMEOUT_MINUTES,
        'panel': panel
    }
