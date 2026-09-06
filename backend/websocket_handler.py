"""
WEBSOCKETS PARA ACTUALIZACION EN TIEMPO REAL
Permite que las páginas se actualicen automáticamente cuando cambia la BD
"""

from flask import Blueprint
from flask_socketio import SocketIO, emit
import os
import threading
import time
from datetime import datetime

# Blueprint para WebSocket
websocket_bp = Blueprint('websocket', __name__)

# Variables globales para SocketIO y Flask app
socketio = None
flask_app = None

def init_websocket(app, socketio_instance):
    """Inicializar SocketIO con la instancia pasada desde app.py"""
    global flask_app
    flask_app = app
    global socketio
    socketio = socketio_instance
    
    @socketio.on('connect')
    def handle_connect():
        print(f'[WEBSOCKET] Cliente conectado: {socketio.server.environ.get("REMOTE_ADDR")}')
        emit('connected', {'data': 'Conectado al servidor'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print('[WEBSOCKET] Cliente desconectado')
    
    @socketio.on('request_personas')
    def handle_request_personas():
        """Envia lista de personas"""
        personas = obtener_personas_cache()
        emit('personas_data', {
            'personas': personas,
            'total': len(personas),
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
    
    @socketio.on('request_stats')
    def handle_request_stats():
        """Envia estadísticas de la BD"""
        stats = obtener_estadisticas()
        emit('stats_data', stats, broadcast=True)
    
    return socketio

def obtener_personas_cache():
    """Obtener todas las personas de la BD"""
    try:
        from models import Persona
        
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
        
        return personas
        
    except Exception as e:
        print(f'[ERROR] obtener_personas_cache: {e}')
        return []

def obtener_estadisticas():
    """Obtener estadísticas de la BD"""
    try:
        from models import Usuario, Persona, RegistroAcceso, Computador
        
        stats = {}
        
        # Contar usuarios
        stats['usuarios'] = Usuario.query.count()
        
        # Contar personas
        stats['personas'] = Persona.query.filter_by(deleted_at=None).count()
        
        # Contar registros de acceso
        stats['registros_acceso'] = RegistroAcceso.query.count()
        
        # Contar equipos
        stats['equipos'] = Computador.query.count()
        
        stats['timestamp'] = datetime.now().isoformat()
        
        return stats
        
    except Exception as e:
        print(f'[ERROR] obtener_estadisticas: {e}')
        return {'error': str(e)}

def emitir_actualizacion():
    """Emitir actualización de datos a todos los clientes conectados"""
    if socketio and flask_app:
        try:
            # Usar contexto de Flask si es necesario
            with flask_app.app_context():
                personas = obtener_personas_cache()
                stats = obtener_estadisticas()
                
                socketio.emit('personas_updated', {
                    'personas': personas,
                    'total': len(personas),
                    'stats': stats,
                    'timestamp': datetime.now().isoformat()
                }, namespace='/')
        except Exception as e:
            print(f'[ERROR] emitir_actualizacion: {e}')

def init_actualiza_continuo(app):
    """Iniciar hilo que monitorea cambios en la BD"""
    def monitorear():
        from models import Persona
        ultima_persona_id = None
        
        while True:
            try:
                time.sleep(2)  # Verificar cada 2 segundos
                
                # ✅ CONTEXT FIX: Usar app_context para acceder a DB
                with app.app_context():
                    # Obtener la persona más reciente usando SQLAlchemy
                    persona_reciente = Persona.query.order_by(Persona.created_at.desc()).first()
                    
                    if persona_reciente:
                        persona_id = persona_reciente.id
                        if ultima_persona_id != persona_id:
                            # Hubo un cambio
                            ultima_persona_id = persona_id
                            print(f'[WEBSOCKET] Cambio detectado en BD, emitiendo actualización...')
                            emitir_actualizacion()
                
            except Exception as e:
                print(f'[ERROR] monitorear: {e}')
    
    # Iniciar hilo de monitoreo
    thread = threading.Thread(target=monitorear, daemon=True)
    thread.start()
