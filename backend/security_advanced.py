"""
═══════════════════════════════════════════════════════════════════════════════
  MÓDULO DE ENCRIPTACIÓN Y AUDITORÍA — SENA CUMPLIMIENTO NORMATIVO
═══════════════════════════════════════════════════════════════════════════════

Cumplimiento con:
  ✓ Ley 1581 de 2012 (Protección de datos personales - HABEAS DATA)
  ✓ Decreto 1377 de 2013 (Régimen de protección de datos)
  ✓ Resoluciones del MinTIC
  ✓ Estándares ISO 27001
"""

from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import json
import os
from functools import wraps
from flask import request, session, jsonify
from werkzeug.security import generate_password_hash

# ═══════════════════════════════════════════════════════════════════════════════
#  1. ENCRIPTACIÓN DE DATOS SENSIBLES
# ═══════════════════════════════════════════════════════════════════════════════

class EncriptadorDatos:
    """Encripta campos sensibles según Ley 1581/2012"""
    
    _cipher = None
    
    @classmethod
    def inicializar(cls, clave_secreta=None):
        """Inicializa el encriptor con clave de Fernet"""
        if clave_secreta is None:
            clave_secreta = os.getenv('ENCRYPTION_KEY')
            if not clave_secreta:
                # Generar y guardar en .env si no existe
                clave_secreta = Fernet.generate_key().decode()
                print(f"[SECURITY] Genera esta clave en .env: ENCRYPTION_KEY={clave_secreta}")
                clave_secreta = clave_secreta.encode()
        
        if isinstance(clave_secreta, str):
            clave_secreta = clave_secreta.encode()
        
        cls._cipher = Fernet(clave_secreta)
    
    @classmethod
    def encriptar(cls, texto):
        """Encripta un string con Fernet (AES-128)"""
        if cls._cipher is None:
            cls.inicializar()
        
        if not texto:
            return None
        
        return cls._cipher.encrypt(texto.encode()).decode()
    
    @classmethod
    def desencriptar(cls, texto_encriptado):
        """Desencripta un string"""
        if cls._cipher is None:
            cls.inicializar()
        
        if not texto_encriptado:
            return None
        
        try:
            return cls._cipher.decrypt(texto_encriptado.encode()).decode()
        except:
            return None


# ═══════════════════════════════════════════════════════════════════════════════
#  2. AUDITORÍA COMPLETA DE CAMBIOS ADMINISTRATIVOS
# ═══════════════════════════════════════════════════════════════════════════════

class AuditoriaAdministrativa:
    """Registra TODOS los cambios administrativos según normas SENA"""
    
    OPERACIONES = {
        'CREAR': 'CREATE',
        'MODIFICAR': 'UPDATE',
        'ELIMINAR': 'DELETE',
        'LOGIN': 'AUTH_LOGIN',
        'LOGOUT': 'AUTH_LOGOUT',
        'CAMBIO_PERMISOS': 'PERMISSION_CHANGE',
        'CAMBIO_CONTRASENA': 'PASSWORD_CHANGE',
        'ACCESO_DATOS': 'DATA_ACCESS',
    }
    
    @staticmethod
    def registrar(
        usuario_id,
        operacion,
        tabla,
        registro_id,
        datos_anterior=None,
        datos_nuevo=None,
        ip_address=None,
        motivo=None
    ):
        """Registra un cambio administrativo con auditoría completa"""
        
        if ip_address is None:
            ip_address = _obtener_ip_real()
        
        timestamp = datetime.now().isoformat()
        
        # Obtener user-agent para rastrear dispositivo
        user_agent = request.headers.get('User-Agent', 'Unknown')[:255]
        
        registro_auditoria = {
            'timestamp': timestamp,
            'usuario_id': usuario_id,
            'operacion': operacion,
            'tabla': tabla,
            'registro_id': registro_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'datos_anterior': json.dumps(datos_anterior) if datos_anterior else None,
            'datos_nuevo': json.dumps(datos_nuevo) if datos_nuevo else None,
            'motivo': motivo,
        }
        
        # Guardar en archivo de auditoría (rotación diaria automática)
        _guardar_auditoria_archivo(registro_auditoria)
        
        # Guardar en BD si tabla de auditoría existe
        _guardar_auditoria_bd(registro_auditoria)
        
        return registro_auditoria
    
    @staticmethod
    def obtener_historial(usuario_id=None, tabla=None, dias=30):
        """Obtiene historial de auditoría"""
        desde = (datetime.now() - timedelta(days=dias)).isoformat()
        
        try:
            from models import db, AuditoriaAdministrativa
            
            query = AuditoriaAdministrativa.query.filter(
                AuditoriaAdministrativa.timestamp > desde
            )
            
            if usuario_id:
                query = query.filter(AuditoriaAdministrativa.usuario_id == usuario_id)
            
            if tabla:
                query = query.filter(AuditoriaAdministrativa.tabla == tabla)
            
            # Limitar a 1000 registros más recientes
            resultados = query.order_by(
                AuditoriaAdministrativa.timestamp.desc()
            ).limit(1000).all()
            
            return [
                {
                    'timestamp': r.timestamp,
                    'usuario_id': r.usuario_id,
                    'operacion': r.operacion,
                    'tabla': r.tabla,
                    'registro_id': r.registro_id,
                    'ip_address': r.ip_address,
                    'user_agent': r.user_agent,
                    'datos_anterior': r.datos_anterior,
                    'datos_nuevo': r.datos_nuevo,
                    'motivo': r.motivo,
                }
                for r in resultados
            ]
        
        except Exception as e:
            print(f"[AUDIT] Error obtener historial: {e}")
            return []


# ═══════════════════════════════════════════════════════════════════════════════
#  3. SESSION SECURITY MEJORADA
# ═══════════════════════════════════════════════════════════════════════════════

class SesionSegura:
    """Gestión de sesiones seguras con protecciones adicionales"""
    
    TIMEOUT_INACTIVIDAD = 1800  # 30 minutos sin actividad = logout
    TIMEOUT_ABSOLUTO = 28800     # 8 horas máximo por sesión
    
    @staticmethod
    def crear_sesion_segura(usuario_id, ip_address=None, user_agent=None):
        """Crea una sesión con metadata de seguridad"""
        
        if ip_address is None:
            ip_address = _obtener_ip_real()
        
        if user_agent is None:
            user_agent = request.headers.get('User-Agent', 'Unknown')
        
        ahora = datetime.now()
        
        session['usuario_id'] = usuario_id
        session['ip_address'] = ip_address
        session['user_agent_hash'] = hash(user_agent)
        session['timestamp_creacion'] = ahora.isoformat()
        session['ultima_actividad'] = ahora.isoformat()
        session.permanent = True
        
        AuditoriaAdministrativa.registrar(
            usuario_id=usuario_id,
            operacion='LOGIN',
            tabla='usuarios',
            registro_id=usuario_id,
            ip_address=ip_address,
            motivo='Login exitoso'
        )
    
    @staticmethod
    def validar_sesion():
        """Valida que la sesión sea legítima"""
        
        if 'usuario_id' not in session:
            return False, "Sin sesión activa"
        
        # Verificar timeout de inactividad
        ultima_actividad = datetime.fromisoformat(session.get('ultima_actividad', datetime.now().isoformat()))
        if (datetime.now() - ultima_actividad).total_seconds() > SesionSegura.TIMEOUT_INACTIVIDAD:
            del session['usuario_id']
            return False, "Sesión expirada por inactividad"
        
        # Verificar timeout absoluto
        timestamp_creacion = datetime.fromisoformat(session.get('timestamp_creacion', datetime.now().isoformat()))
        if (datetime.now() - timestamp_creacion).total_seconds() > SesionSegura.TIMEOUT_ABSOLUTO:
            del session['usuario_id']
            return False, "Sesión expirada (duración máxima alcanzada)"
        
        # Verificar cambio de IP (posible hijacking)
        ip_actual = _obtener_ip_real()
        ip_sesion = session.get('ip_address', '')
        if ip_sesion and ip_actual != ip_sesion:
            # Registrar intento sospechoso pero permitir (puede ser proxy)
            AuditoriaAdministrativa.registrar(
                usuario_id=session.get('usuario_id'),
                operacion='ACCESO_SOSPECHOSO_IP',
                tabla='sesiones',
                registro_id=session.get('usuario_id'),
                ip_address=ip_actual,
                motivo=f'Cambio de IP: {ip_sesion} → {ip_actual}'
            )
        
        # Actualizar última actividad
        session['ultima_actividad'] = datetime.now().isoformat()
        
        return True, "Sesión válida"
    
    @staticmethod
    def destruir_sesion(usuario_id=None):
        """Cierra la sesión de forma segura"""
        if 'usuario_id' in session:
            usuario_id = usuario_id or session['usuario_id']
            AuditoriaAdministrativa.registrar(
                usuario_id=usuario_id,
                operacion='LOGOUT',
                tabla='usuarios',
                registro_id=usuario_id,
                motivo='Cierre de sesión'
            )
        
        session.clear()


# ═══════════════════════════════════════════════════════════════════════════════
#  4. ACCOUNT LOCKOUT INTELIGENTE
# ═══════════════════════════════════════════════════════════════════════════════

class PoliticaBloqueoCuenta:
    """Bloquea cuentas tras intentos fallidos repetidos"""
    
    INTENTOS_MAXIMOS = 5
    TIEMPO_BLOQUEO_MINUTOS = 15
    TIEMPO_RESET_MINUTOS = 10
    
    @staticmethod
    def registrar_intento_fallido(email):
        """Registra un intento fallido de login"""
        try:
            from models import db, BloqueoCuentas
            
            ahora = datetime.now()
            
            # Buscar registro existente
            bloqueo = BloqueoCuentas.query.filter_by(email=email).first()
            
            if bloqueo:
                timestamp_primer = datetime.fromisoformat(bloqueo.timestamp_primer_intento) if bloqueo.timestamp_primer_intento else ahora
                
                # Si pasaron más de TIEMPO_RESET_MINUTOS, reiniciar contador
                if (ahora - timestamp_primer).total_seconds() > PoliticaBloqueoCuenta.TIEMPO_RESET_MINUTOS * 60:
                    bloqueo.intentos_fallidos = 1
                    bloqueo.timestamp_primer_intento = ahora.isoformat()
                else:
                    bloqueo.intentos_fallidos += 1
            else:
                # Primer intento fallido
                bloqueo = BloqueoCuentas(
                    email=email,
                    intentos_fallidos=1,
                    timestamp_primer_intento=ahora.isoformat()
                )
                db.session.add(bloqueo)
            
            db.session.commit()
            
        except Exception as e:
            print(f"[LOCKOUT] Error registrar intento: {e}")
            try:
                db.session.rollback()
            except:
                pass
    
    @staticmethod
    def verificar_bloqueo(email):
        """Verifica si la cuenta está bloqueada"""
        try:
            from models import db, BloqueoCuentas
            
            bloqueo = BloqueoCuentas.query.filter_by(email=email).first()
            
            if not bloqueo:
                return False, "Cuenta disponible"
            
            ahora = datetime.now()
            
            # Si hay bloqueo temporal
            if bloqueo.timestamp_bloqueo:
                timestamp_bloqueo_dt = datetime.fromisoformat(bloqueo.timestamp_bloqueo)
                tiempo_transcurrido = (ahora - timestamp_bloqueo_dt).total_seconds()
                
                if tiempo_transcurrido < PoliticaBloqueoCuenta.TIEMPO_BLOQUEO_MINUTOS * 60:
                    minutos_restantes = int((PoliticaBloqueoCuenta.TIEMPO_BLOQUEO_MINUTOS * 60 - tiempo_transcurrido) / 60)
                    return True, f"Cuenta bloqueada. Reintentar en {minutos_restantes} minutos"
                else:
                    # Desbloquear
                    bloqueo.intentos_fallidos = 0
                    bloqueo.timestamp_bloqueo = None
                    bloqueo.timestamp_primer_intento = None
                    db.session.commit()
                    return False, "Cuenta disponible"
            
            # Si alcanzó máximo de intentos
            if bloqueo.intentos_fallidos >= PoliticaBloqueoCuenta.INTENTOS_MAXIMOS:
                bloqueo.timestamp_bloqueo = ahora.isoformat()
                db.session.commit()
                
                AuditoriaAdministrativa.registrar(
                    usuario_id='SISTEMA',
                    operacion='ACCOUNT_LOCKED',
                    tabla='usuarios',
                    registro_id=email,
                    motivo=f'{bloqueo.intentos_fallidos} intentos fallidos de login'
                )
                
                return True, f"Cuenta bloqueada por seguridad ({PoliticaBloqueoCuenta.INTENTOS_MAXIMOS} intentos fallidos)"
            
            return False, "Cuenta disponible"
        
        except Exception as e:
            print(f"[LOCKOUT] Error verificar bloqueo: {e}")
            return False, "Error en verificación"
    
    @staticmethod
    def limpiar_intento_exitoso(email):
        """Limpia contadores tras login exitoso"""
        try:
            from models import db, BloqueoCuentas
            
            bloqueo = BloqueoCuentas.query.filter_by(email=email).first()
            
            if bloqueo:
                bloqueo.intentos_fallidos = 0
                bloqueo.timestamp_primer_intento = None
                bloqueo.timestamp_bloqueo = None
                db.session.commit()
        
        except Exception as e:
            print(f"[LOCKOUT] Error limpiar: {e}")
            try:
                db.session.rollback()
            except:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
#  5. FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def _obtener_ip_real():
    """Obtiene IP real considerando proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr


def _guardar_auditoria_archivo(registro):
    """Guarda auditoría en archivo con rotación diaria"""
    from pathlib import Path
    import gzip
    
    log_dir = Path('logs/auditoria')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    fecha = datetime.now().strftime('%Y-%m-%d')
    log_path = log_dir / f'auditoria_{fecha}.log'
    
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(registro) + '\n')
    except Exception as e:
        print(f"[AUDIT] Error guardar archivo: {e}")


def _guardar_auditoria_bd(registro):
    """Guarda auditoría en base de datos usando SQLAlchemy"""
    try:
        from models import db, AuditoriaAdministrativa
        
        # Crear registro de auditoría usando ORM
        auditoria = AuditoriaAdministrativa(
            timestamp=registro['timestamp'],
            usuario_id=registro['usuario_id'],
            operacion=registro['operacion'],
            tabla=registro['tabla'],
            registro_id=registro['registro_id'],
            ip_address=registro['ip_address'],
            user_agent=registro['user_agent'],
            datos_anterior=registro['datos_anterior'],
            datos_nuevo=registro['datos_nuevo'],
            motivo=registro['motivo']
        )
        
        db.session.add(auditoria)
        db.session.commit()
        
    except Exception as e:
        print(f"[AUDIT] Error guardar BD: {e}")
        try:
            db.session.rollback()
        except:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  6. DECORADOR PARA AUDITORÍA DE OPERACIONES
# ═══════════════════════════════════════════════════════════════════════════════

def auditar_operacion(tabla, operacion='CREATE'):
    """Decorador para auditar automáticamente operaciones"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            resultado = f(*args, **kwargs)
            
            # Registrar si fue exitoso (status 200/201)
            if hasattr(resultado, 'status_code') and resultado.status_code in [200, 201]:
                usuario_id = session.get('usuario_id', 'SISTEMA')
                
                AuditoriaAdministrativa.registrar(
                    usuario_id=usuario_id,
                    operacion=operacion,
                    tabla=tabla,
                    registro_id=request.args.get('id') or request.json.get('id') if request.json else None,
                    ip_address=_obtener_ip_real(),
                    datos_nuevo=request.json if request.method in ['POST', 'PUT'] else None,
                    motivo=f"{operacion} en {tabla}"
                )
            
            return resultado
        
        return decorated_function
    
    return decorator
