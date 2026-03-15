"""
═══════════════════════════════════════════════════════════════════════════════
  SEGURIDAD DEL SISTEMA SENA — Reporte de Protecciones Implementadas
═══════════════════════════════════════════════════════════════════════════════

Documento de auditoría que detalla todas las medidas de seguridad
implementadas en el Sistema de Control de Ingresos SENA.

Generado: 15/03/2026
Versión: 2024-Security-Hardened
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  1. PROTECCIONES CONTRA ATAQUES WEB (OWASP Top 10)
# ═══════════════════════════════════════════════════════════════════════════════

PROTECCIONES = {
    "SQL_INJECTION": {
        "descripcion": "Prevención de inyección de código SQL",
        "mecanismos": [
            "✓ Uso exclusivo de ORM (SQLAlchemy)",
            "✓ Parametrización de todas las queries",
            "✓ Validación de entrada (InputValidator)",
            "✓ Sanitización de strings",
            "✓ NO usar concatenación string en SQL",
        ],
        "archivo": "security_shield.py::InputValidator",
        "pruebas": "security_tests.py::TestSQLInjection",
        "severidad": "CRÍTICA"
    },
    
    "CROSS_SITE_SCRIPTING": {
        "descripcion": "Prevención de ataques XSS (ejecutar scripts en navegador)",
        "mecanismos": [
            "✓ Sanitización con bleach (remover HTML/JS)",
            "✓ Escape de caracteres HTML en salida",
            "✓ Content Security Policy (CSP) header",
            "✓ X-XSS-Protection header",
            "✓ Validación de input de usuario",
        ],
        "archivo": "security_shield.py::InputValidator.sanitizar_string",
        "pruebas": "security_tests.py::TestXSSPrevention",
        "severidad": "CRÍTICA"
    },
    
    "BRUTE_FORCE": {
        "descripcion": "Prevención de ataques de fuerza bruta",
        "mecanismos": [
            "✓ Límite de intentos fallidos de login: 5 intentos",
            "✓ Bloqueo temporal: 15 minutos",
            "✓ Ventana de reset: 10 minutos sin intentos",
            "✓ Detección por IP + User-Agent",
            "✓ Log de intentos fallidos",
        ],
        "archivo": "routes.py::_verificar_limite_login",
        "ubicacion_api": "POST /api/auth/login",
        "severidad": "ALTA"
    },
    
    "RATE_LIMITING": {
        "descripcion": "Límite de requests por IP (DoS prevention)",
        "mecanismos": [
            "✓ Límite configurable por endpoint",
            "✓ Bloqueo temporal tras exceder límite",
            "✓ Tracking por IP real (considerando proxies)",
            "✓ Reset automático tras período de inactividad",
        ],
        "archivo": "security_shield.py::RateLimiter",
        "decorador": "@rate_limit(max_requests=30, ventana_segundos=60)",
        "severidad": "MEDIA"
    },
    
    "CSRF": {
        "descripcion": "Protección contra CSRF (Cross-Site Request Forgery)",
        "mecanismos": [
            "✓ Generación de tokens CSRF seguros",
            "✓ Validación de token por request",
            "✓ Tokens one-time-use (solo válidos una vez)",
            "✓ Verificación de IP y usuario",
            "✓ Expiración automática (1 hora)",
        ],
        "archivo": "security_shield.py::CSRFProtection",
        "uso": "csrf_protection.generar_token() / csrf_protection.validar_token()",
        "severidad": "MEDIA"
    },
    
    "PATH_TRAVERSAL": {
        "descripcion": "Prevención de acceso a archivos fuera del scope",
        "mecanismos": [
            "✓ Detección de ../ y ..\\ en rutas",
            "✓ Validación de caracteres permitidos",
            "✓ Prevención de rutas absolutas",
            "✓ Encoding seguro de rutas",
        ],
        "archivo": "security_shield.py::InputValidator.prevenir_directory_traversal",
        "severidad": "ALTA"
    },
    
    "VALIDACION_ENTRADA": {
        "descripcion": "Validación exhaustiva de entrada de usuario",
        "mecanismos": [
            "✓ Validación de número de documento (cédula)",
            "✓ Verificación de dígito verificador (módulo 11)",
            "✓ Validación de emails con DNS check",
            "✓ Rangos numéricos (min/max)",
            "✓ Patrones regex para tipos de dato",
        ],
        "archivo": "security_shield.py::InputValidator",
        "severidad": "CRÍTICA"
    },
    
    "HEADERS_SEGURIDAD": {
        "descripcion": "Headers HTTP de seguridad recomendados por OWASP",
        "headers": {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "restrictive",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Cache-Control": "no-store, no-cache"
        },
        "archivo": "security_shield.py::aplicar_headers_seguridad",
        "severidad": "ALTA"
    },
    
    "AUTENTICACION": {
        "descripcion": "Seguridad en autenticación y autorización",
        "mecanismos": [
            "✓ JWT con expiración (8 horas)",
            "✓ Contraseñas hasheadas con werkzeug (PBKDF2)",
            "✓ Salt automático por hash",
            "✓ Mensaje de error genérico (no revelar si email existe)",
            "✓ Verificación de token en cada request",
        ],
        "archivo": "routes.py::token_required decorator",
        "algoritmo": "HS256 (JWT)",
        "severidad": "CRÍTICA"
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
#  2. LOGGING Y AUDITORÍA DE SEGURIDAD
# ═══════════════════════════════════════════════════════════════════════════════

EVENTOS_REGISTRADOS = {
    "LOGIN_EXITOSO": "Inicio de sesión correcto",
    "LOGIN_FALLIDO": "Intento fallido de login (cuenta regresiva antes de bloqueo)",
    "IP_BLOQUEADA": "IP bloqueada tras N intentos fallidos",
    "ACCESO_DENEGADO_VALIDACION": "Intento de acceso con datos inválidos",
    "CAMBIO_DATOS": "Cambio de datos de usuario/persona",
    "ACCESO_NO_AUTORIZADO": "Intento de acceso sin autorización suficiente",
    "CSRF_INVALIDO": "Token CSRF inválido o expirado",
    "RATE_LIMIT_EXCEEDED": "Límite de requests excedido",
}

LOG_FORMAT = "[{severidad}] [{timestamp}] {evento} | Usuario: {usuario_id} | IP: {ip} | Detalles: {detalles}"

# ═══════════════════════════════════════════════════════════════════════════════
#  3. CONFIGURACIÓN DE SEGURIDAD EN .env
# ═══════════════════════════════════════════════════════════════════════════════

CONFIGURACION_REQUERIDA = """
# === SEGURIDAD ===
FLASK_ENV=production
DEBUG=False

# Claves secretas (generar con: openssl rand -hex 32)
SECRET_KEY=<generar_con_openssl>
JWT_SECRET_KEY=<generar_con_openssl>

# CORS (restrictivo en producción)
CORS_ORIGINS=https://example.com,https://www.example.com

# Database (usar contraseña fuerte)
DATABASE_URL=sqlite:///sena.db  # Cambiar a PostgreSQL en producción

# Email (para alertas de seguridad)
GMAIL_REMITENTE=seguridad@sena.edu.co
GMAIL_APP_PASSWORD=<app_password_gmail>
ADMIN_EMAIL=admin@sena.edu.co
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  4. VULNERABILIDADES CONOCIDAS Y MITIGACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

MITIGACION_VULNERABILIDADES = {
    "Contraseña débil": {
        "problema": "Usuarios pueden crear contraseñas fáciles de adivinar",
        "solucion": [
            "✓ Validación de contraseña fuerte",
            "✓ Mínimo 12 caracteres",
            "✓ Requerir mayúsculas, minúsculas, números, especiales",
            "✓ Lista negra de contraseñas comunes",
        ],
        "archivo": "validaciones.py"
    },
    
    "Sesión secuestrada": {
        "problema": "Token JWT podría ser interceptado",
        "solucion": [
            "✓ HTTPS obligatorio en producción",
            "✓ Expiración corta de tokens (8 horas)",
            "✓ Refresh tokens en desarrollo",
            "✓ HttpOnly cookies (si se usa)",
        ]
    },
    
    "Database expuesto": {
        "problema": "alguien gana acceso a la base de datos",
        "solucion": [
            "✓ Contraseñas hasheadas con salt",
            "✓ Datos sensibles encriptados",
            "✓ Respaldos encriptados",
            "✓ Acceso limitado a BD desde backend solo",
        ]
    },
    
    "File upload malicioso": {
        "problema": "Subir archivos ejecutables o maliciosos",
        "solucion": [
            "✓ Validar extensión de archivo",
            "✓ Validar MIME type",
            "✓ Renombrar archivo (evitar../ en nombre)",
            "✓ Almacenar fuera de web root",
            "✓ Scanner de virus (ClamAV, si crítico)",
        ]
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
#  5. LISTA DE VERIFICACIÓN DE SEGURIDAD (SECURITY CHECKLIST)
# ═══════════════════════════════════════════════════════════════════════════════

CHECKLIST_PRE_PRODUCCION = [
    ("☐", "HTTPS habilitado en servidor de producción"),
    ("☐", "Variables de entorno configuradas (.env no en git)"),
    ("☐", "Database con contraseña fuerte"),
    ("☐", "DEBUG desactivado (DEBUG=False)"),
    ("☐", "CORS configurado para dominios permitidos solo"),
    ("☐", "Backups encriptados"),
    ("☐", "Firewall configurado para bloquear acceso innecesario"),
    ("☐", "SSL certificate válido y renovación automática"),
    ("☐", "Rate limiting activado en todos los endpoints críticos"),
    ("☐", "Logging de seguridad activado y monitoreado"),
    ("☐", "Contraseñas admin cambiadas del default"),
    ("☐", "Actualizar todas las dependencias),
    ("☐", "Pruebas de penetración realizadas"),
    ("☐", "Plan de respuesta a incidentes documentado"),
]

# ═══════════════════════════════════════════════════════════════════════════════
#  6. COMANDOS PARA EJECUTAR PRUEBAS DE SEGURIDAD
# ═══════════════════════════════════════════════════════════════════════════════

COMANDOS_PRUEBA = """
# Ejecutar pruebas de seguridad
cd backend
python security_tests.py

# Con pytest (más detalles)
pip install pytest
pytest security_tests.py -v --tb=short

# Verificar dependencias vulnerables
pip install safety
safety check

# Análisis estático de código Python
pip install bandit
bandit -r . -f csv -o security_report.csv

# Escaneo de secrets en código
pip install detect-secrets
detect-secrets scan

# OWASP ZAP para pruebas de penetración (si están disponible)
# Descargar desde: https://www.zaproxy.org/
# owasp-zap -cmd -quickurl http://localhost:8000 -quickout report.html
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  7. REFERENCIAS Y ESTÁNDARES
# ═══════════════════════════════════════════════════════════════════════════════

REFERENCIAS = {
    "OWASP Top 10 (2021)": "https://owasp.org/Top10/",
    "OWASP Secure Coding": "https://owasp.org/www-community/controls/",
    "CWE Top 25": "https://cwe.mitre.org/top25/",
    "Flask Security": "https://flask.palletsprojects.com/en/latest/security/",
    "SQLAlchemy Security": "https://docs.sqlalchemy.org/en/stable/faq/security.html",
    "JWT Best Practices": "https://tools.ietf.org/html/rfc8725",
}

print(__doc__)
print("\n✅ PROTECCIONES IMPLEMENTADAS:")
for categoria, detalles in PROTECCIONES.items():
    print(f"\n[{detalles['severidad']}] {categoria}")
    print(f"  {detalles['descripcion']}")
    for mecanismo in detalles.get('mecanismos', []):
        print(f"  {mecanismo}")

print("\n\n🔍 PRÓXIMOS PASOS:")
print("  1. Ejecutar: python security_tests.py")
print("  2. Revisar: SEGURIDAD.md en el workspace")
print("  3. Completar: Checklist pre-producción")
print("  4. Ejecutar: Pruebas de penetración (OWASP ZAP)")
print("  5. Monitorear: Logs de seguridad en producción")
