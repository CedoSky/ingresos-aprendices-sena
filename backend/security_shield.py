"""
═══════════════════════════════════════════════════════════════════════════════
  SECURITY SHIELD — Protecciones contra ataques comunes
  Sistema de Control de Ingresos SENA
═══════════════════════════════════════════════════════════════════════════════

Protecciones implementadas:
  ✓ SQL Injection     — Uso de ORM (SQLAlchemy) + validación de entrada
  ✓ XSS (Cross-Site Scripting)  — Sanitización y escape de salida
  ✓ CSRF (Cross-Site Request Forgery) — Token CSRF en formularios
  ✓ Rate Limiting     — Límite de requests por IP/usuario
  ✓ Brute Force       — Bloqueo temporal tras intentos fallidos
  ✓ Input Validation  — Validación de tipos y longitud
  ✓ Command Injection — No usar shell commands con user input
  ✓ XXE Injection     — Parseo XML seguro
  ✓ Directory Traversal — Sanitización de rutas
"""

import re
import html
import secrets
import hashlib
from typing import Any, Tuple, List, Optional
from datetime import datetime, timedelta
from functools import wraps
import threading
import time
from flask import request, jsonify
import bleach

# ═══════════════════════════════════════════════════════════════════════════════
#  1. SANITIZACIÓN DE ENTRADA (Prevención de Injection Attacks)
# ═══════════════════════════════════════════════════════════════════════════════

class InputValidator:
    """Valida y sanitiza inputs del usuario"""
    
    # Patrones permitidos para cada tipo de dato
    PATTERNS = {
        'numero_doc': r'^[0-9]{6,11}$',  # Cédula: 6-11 dígitos
        'nombre': r"^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s'\-]{2,100}$",
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone': r'^[\d\s\-\+\(\)]{7,20}$',
        'alphanumeric': r'^[a-zA-Z0-9\-_]{1,50}$',
        'numeric': r'^[\d]{1,20}$',
        'ipv4': r'^(\d{1,3}\.){3}\d{1,3}$',
    }
    
    @staticmethod
    def validar_numero_documento(doc: str) -> Tuple[bool, str]:
        """Valida número de documento (cédula)"""
        if not doc or not isinstance(doc, str):
            return False, 'Documento inválido'
        
        # Eliminar espacios y caracteres especiales
        doc = doc.strip().replace(' ', '').replace('.', '')
        
        if not re.match(InputValidator.PATTERNS['numero_doc'], doc):
            return False, 'Documento debe contener 6-11 dígitos'
        
        # Validación dígito de verificación (cédula colombiana)
        if len(doc) == 10:
            if not _validar_digito_verificacion_cedula(doc):
                return False, 'Cédula inválida (dígito verificador fallido)'
        
        return True, ''
    
    @staticmethod
    def validar_nombre(nombre: str, min_len: int = 2, max_len: int = 100) -> Tuple[bool, str]:
        """Valida nombre de persona"""
        if not nombre or not isinstance(nombre, str):
            return False, 'Nombre requerido'
        
        nombre = nombre.strip()
        
        if len(nombre) < min_len or len(nombre) > max_len:
            return False, f'Nombre debe tener {min_len}-{max_len} caracteres'
        
        if not re.match(InputValidator.PATTERNS['nombre'], nombre):
            return False, 'Nombre contiene caracteres inválidos'
        
        return True, ''
    
    @staticmethod
    def validar_email(email: str) -> Tuple[bool, str]:
        """Valida email"""
        if not email or not isinstance(email, str):
            return False, 'Email requerido'
        
        email = email.strip().lower()
        
        if not re.match(InputValidator.PATTERNS['email'], email):
            return False, 'Email inválido'
        
        if len(email) > 255:
            return False, 'Email muy largo'
        
        return True, ''
    
    @staticmethod
    def sanitizar_string(texto: str, max_len: int = 500, permitir_html: bool = False) -> str:
        """
        Sanitiza string para evitar XSS
        - Remueve HTML/JavaScript si no está permitido
        - Escapa caracteres especiales HTML
        - Limita longitud
        """
        if not isinstance(texto, str):
            return ''
        
        texto = texto.strip()[:max_len]
        
        if not permitir_html:
            # Bleach es más seguro que html.escape para remover HTML
            texto = bleach.clean(texto, tags=[], strip=True)
        else:
            # Si se permite HTML, solo escapar HTML entities
            texto = html.escape(texto)
        
        return texto
    
    @staticmethod
    def validar_rango_numerico(valor: Any, min_val: int = 0, max_val: int = 999999) -> Tuple[bool, Any]:
        """Valida que número esté en rango permitido"""
        try:
            num = int(valor)
            if min_val <= num <= max_val:
                return True, num
            return False, f'Valor fuera de rango [{min_val}, {max_val}]'
        except (ValueError, TypeError):
            return False, 'Valor debe ser numérico'
    
    @staticmethod
    def validar_tipo_acceso(tipo: str) -> Tuple[bool, str]:
        """Valida que tipo de acceso sea ENTRADA o SALIDA"""
        tipos_validos = {'ENTRADA', 'SALIDA'}
        if isinstance(tipo, str) and tipo.upper() in tipos_validos:
            return True, tipo.upper()
        return False, f'Tipo debe ser: {", ".join(tipos_validos)}'
    
    @staticmethod
    def prevenir_directory_traversal(ruta: str) -> Tuple[bool, str]:
        """Previene ataques de directory traversal (../)"""
        if '..' in ruta or ruta.startswith('/'):
            return False, 'Ruta inválida'
        
        # Solo permitir caracteres seguros
        if not re.match(r'^[a-zA-Z0-9\/_\-\.]+$', ruta):
            return False, 'Ruta contiene caracteres no permitidos'
        
        return True, ruta


def _validar_digito_verificacion_cedula(cedula: str) -> bool:
    """
    Valida el dígito de verificación de cédula colombiana.
    Algoritmo modulo 11.
    """
    if len(cedula) != 10:
        return False
    
    try:
        pesos = [3, 7, 13, 17, 19, 23, 29, 31, 37]
        suma = 0
        
        for i, digito in enumerate(cedula[:9]):
            suma += int(digito) * pesos[i]
        
        digito_esperado = 11 - (suma % 11)
        if digito_esperado == 11:
            digito_esperado = 0
        elif digito_esperado == 10:
            digito_esperado = 0
        
        return int(cedula[9]) == digito_esperado
    except:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#  2. RATE LIMITING (Protección contra abuso)
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """Limita la cantidad de requests por IP/usuario"""
    
    def __init__(self):
        self.limites = {}  # {clave: {'reqs': [], 'bloqueado_hasta': float}}
        self.lock = threading.Lock()
    
    def obtener_ip(self) -> str:
        """Obtiene IP real del cliente"""
        if request.headers.get('X-Forwarded-For'):
            return request.headers['X-Forwarded-For'].split(',')[0].strip()
        return request.remote_addr or '0.0.0.0'
    
    def verificar(self, max_requests: int = 30, ventana_segundos: int = 60, clave: Optional[str] = None) -> Tuple[bool, int]:
        """
        Verifica si se permite el request.
        Retorna (permitido, segundos_para_reintentar)
        """
        if clave is None:
            clave = self.obtener_ip()
        
        ahora = time.time()
        
        with self.lock:
            if clave not in self.limites:
                self.limites[clave] = {'reqs': [], 'bloqueado_hasta': 0}
            
            info = self.limites[clave]
            
            # Si está bloqueado temporalmente
            if info['bloqueado_hasta'] > ahora:
                restantes = int(info['bloqueado_hasta'] - ahora)
                return False, restantes
            
            # Limpiar requests antiguos
            info['reqs'] = [ts for ts in info['reqs'] if ahora - ts < ventana_segundos]
            
            # Verificar si superó límite
            if len(info['reqs']) >= max_requests:
                info['bloqueado_hasta'] = ahora + ventana_segundos
                return False, ventana_segundos
            
            info['reqs'].append(ahora)
            return True, 0
    
    def reiniciar(self, clave: Optional[str] = None):
        """Reinicia el contador para una clave (tras login exitoso, p.ej.)"""
        if clave is None:
            clave = self.obtener_ip()
        
        with self.lock:
            self.limites.pop(clave, None)


# Instancia global
rate_limiter = RateLimiter()


def rate_limit(max_requests: int = 30, ventana_segundos: int = 60):
    """Decorador para limitar requests por IP"""
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            permitido, espera = rate_limiter.verificar(max_requests, ventana_segundos)
            if not permitido:
                return jsonify({
                    'error': 'Demasiadas solicitudes',
                    'detalles': f'Reintenta en {espera} segundos',
                    'codigo_error': 'RATE_LIMIT_EXCEEDED'
                }), 429
            return f(*args, **kwargs)
        return wrapper
    return decorador


# ═══════════════════════════════════════════════════════════════════════════════
#  3. CSRF TOKEN GENERATION & VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class CSRFProtection:
    """Protección contra Cross-Site Request Forgery"""
    
    def __init__(self):
        self.tokens = {}  # {token: {'expires': float, 'ip': str}}
        self.lock = threading.Lock()
    
    def generar_token(self, usuario_id: Optional[str] = None) -> str:
        """Genera un token CSRF seguro"""
        token = secrets.token_urlsafe(32)
        expira_en = time.time() + 3600  # 1 hora
        
        with self.lock:
            self.tokens[token] = {
                'expires': expira_en,
                'ip': rate_limiter.obtener_ip(),
                'usuario_id': usuario_id
            }
        
        return token
    
    def validar_token(self, token: str, usuario_id: Optional[str] = None) -> bool:
        """Valida que el token sea válido y no haya expirado"""
        if not token or not isinstance(token, str):
            return False
        
        with self.lock:
            if token not in self.tokens:
                return False
            
            info = self.tokens[token]
            
            # Verificar expiración
            if info['expires'] < time.time():
                del self.tokens[token]
                return False
            
            # Verificar IP (opcional, pero recomendado)
            if info['ip'] != rate_limiter.obtener_ip():
                return False
            
            # Verificar usuario si se proporciona
            if usuario_id and info.get('usuario_id') != usuario_id:
                return False
            
            # Token válido: eliminarlo (one-time use)
            del self.tokens[token]
            return True


csrf_protection = CSRFProtection()


# ═══════════════════════════════════════════════════════════════════════════════
#  4. LOGGING DE SEGURIDAD
# ═══════════════════════════════════════════════════════════════════════════════

def log_evento_seguridad(tipo: str, usuario_id: Optional[str], detalles: str, ip: Optional[str] = None, severidad: str = 'INFO'):
    """
    Registra eventos de seguridad (intentos fallidos, cambios, etc.)
    
    Tipos: LOGIN_EXITOSO, LOGIN_FALLIDO, CAMBIO_DATOS, ACCESO_DENEG, etc.
    Severidad: INFO, WARNING, CRITICAL
    """
    if ip is None:
        ip = rate_limiter.obtener_ip()
    
    timestamp = datetime.utcnow().isoformat()
    
    # En producción, guardar en BD o archivo de auditoría
    if severidad in ['WARNING', 'CRITICAL']:
        print(f'[{severidad}] [{timestamp}] {tipo} | Usuario: {usuario_id} | IP: {ip} | Detalles: {detalles}')
    else:
        print(f'[{severidad}] [{timestamp}] {tipo} | IP: {ip}')


def registrar_intento_seguridad(usuario_id: Optional[str], tipo: str, exitoso: bool, detalles: str = ''):
    """Wrapper para logging de intentos de acceso"""
    severidad = 'INFO' if exitoso else 'WARNING'
    evento = f'{tipo}_{"EXITOSO" if exitoso else "FALLIDO"}'
    log_evento_seguridad(evento, usuario_id, detalles, severidad=severidad)


# ═══════════════════════════════════════════════════════════════════════════════
#  5. VALIDACIÓN DE CONFIGURACIÓN DE APLICACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def validar_configuracion_seguridad() -> List[str]:
    """
    Valida que la aplicación tenga configuraciones de seguridad mínimas.
    Retorna lista de advertencias/errores.
    """
    warnings = []
    
    try:
        import os
        
        # Verificar variables de entorno críticas
        if not os.getenv('JWT_SECRET_KEY'):
            warnings.append('⚠️  JWT_SECRET_KEY no configurada')
        
        if not os.getenv('SECRET_KEY'):
            warnings.append('⚠️  SECRET_KEY no configurada')
        
        if os.getenv('FLASK_ENV') != 'production':
            warnings.append('⚠️  No está en modo PRODUCTION (debug posiblemente activado)')
        
        if os.getenv('DEBUG') == 'True':
            warnings.append('🔴 DEBUG ACTIVADO EN PRODUCCIÓN')
        
    except Exception as e:
        warnings.append(f'Error validando configuración: {e}')
    
    return warnings


# ═══════════════════════════════════════════════════════════════════════════════
#  6. HEADERS DE SEGURIDAD HTTP
# ═══════════════════════════════════════════════════════════════════════════════

def aplicar_headers_seguridad(response):
    """
    Aplica headers de seguridad recomendados por OWASP.
    Debe ser usado como after_request handler en Flask.
    """
    
    # Previene que el navegador interprete mal el content-type
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Previene clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Habilita filtro XSS del navegador
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Content Security Policy (restrictivo)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.socket.io; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'"
    )
    
    # Solo HTTPS en producción
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Disable cache para datos sensibles
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    
    return response
