import os
from datetime import timedelta

class Config:
    """Configuración base"""
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    if not SECRET_KEY or not JWT_SECRET_KEY:
        import secrets
        SECRET_KEY = SECRET_KEY or secrets.token_hex(32)
        JWT_SECRET_KEY = JWT_SECRET_KEY or secrets.token_hex(32)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args': {'check_same_thread': False}
    }
    
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET', '')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # ── Wompi (pasarela colombiana) ────────────────────────────────────────────
    # Obtén tus claves en https://comercios.wompi.co/
    WOMPI_PUBLIC_KEY       = os.getenv('WOMPI_PUBLIC_KEY', '')
    WOMPI_PRIVATE_KEY      = os.getenv('WOMPI_PRIVATE_KEY', '')
    WOMPI_INTEGRITY_SECRET = os.getenv('WOMPI_INTEGRITY_SECRET', '')
    WOMPI_EVENTS_SECRET    = os.getenv('WOMPI_EVENTS_SECRET', '')
    WOMPI_ENV              = os.getenv('WOMPI_ENV', 'sandbox')  # 'sandbox' o 'prod'

    # Secreto del Panel de Sistemas (código dinámico TOTP-style, cambia cada 5 min)
    # Se genera automáticamente la primera vez que corres MANTENIMIENTO.bat → [P]
    # Nunca hardcodear el valor aquí; se lee de backend/.env
    DEV_PIN_SECRET = os.getenv('DEV_PIN_SECRET', '')

    # ── Correo institucional Gmail ─────────────────────────────────────────────
    # Instrucciones en backend/correo.py (sección docstring al inicio)
    GMAIL_REMITENTE    = os.getenv('GMAIL_REMITENTE', '')
    GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
    GMAIL_NOMBRE       = os.getenv('GMAIL_NOMBRE', 'SENA — Sistema de Ingresos')
    ADMIN_EMAIL        = os.getenv('ADMIN_EMAIL', '')

    # ── Almacenamiento de respaldos ────────────────────────────────────────────
    # 'usb'     → Copia directamente en el pendrive detectado
    # 'network' → Carpeta compartida en otra laptop de la red local (recomendado)
    # 's3'      → Sube a AWS S3 (requiere claves AWS en .env)
    STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'usb')

    # ── ESP32 TRIAC CONTROL ───────────────────────────────────────────────────
    # IP del ESP32 en la red local (ej: 172.20.10.5 en iPhone de AMAT)
    ESP32_IP = os.getenv('ESP32_IP', '192.168.1.100')
    ESP32_HTTP_TIMEOUT = 3  # segundos

    # Nombre de la carpeta que se crea dentro del pendrive
    USB_BACKUP_FOLDER = os.getenv('USB_BACKUP_FOLDER', 'SENA_RESPALDOS')

    # Ruta explícita a la USB (ej: "E:/"). Si está vacío el sistema detecta automáticamente.
    USB_PATH_OVERRIDE = os.getenv('USB_PATH_OVERRIDE', '')

    # ── Respaldo en disco duro remoto (otra laptop en la red) ──────────────────
    # Ruta UNC de la carpeta compartida en la otra laptop.
    # Ejemplos:
    #   \\192.168.1.50\SENA_RESPALDOS   (por IP)
    #   \\LAPTOP-ADMIN\SENA_RESPALDOS   (por nombre del equipo)
    # En .env escribirlo con doble barra: NETWORK_BACKUP_PATH=\\\\192.168.1.50\\SENA_RESPALDOS
    NETWORK_BACKUP_PATH = os.getenv('NETWORK_BACKUP_PATH', '')

    # Credenciales opcionales si la carpeta compartida requiere contraseña
    NETWORK_USERNAME = os.getenv('NETWORK_USERNAME', '')
    NETWORK_PASSWORD = os.getenv('NETWORK_PASSWORD', '')

    # Tiempo máximo de espera para verificar si la red está disponible (segundos)
    NETWORK_TIMEOUT = int(os.getenv('NETWORK_TIMEOUT', '5'))

class DevelopmentConfig(Config):
    """Configuración desarrollo"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    
    # Soportar USB o local
    if os.getenv('USE_USB') == 'true':
        # Usar BD desde USB
        SQLALCHEMY_DATABASE_URI = os.getenv(
            'DATABASE_URL',
            'sqlite:///E:/SENA_BASE_DATOS/sena.db'
        )
    else:
        # Usar BD local
        SQLALCHEMY_DATABASE_URI = 'sqlite:///sena.db'

class ProductionConfig(Config):
    """Configuración producción"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    
    # En producción, esperamos DATABASE_URL en formato PostgreSQL
    # Ejemplo: postgresql://user:password@host:5432/dbname
    database_url = os.getenv('DATABASE_URL', '')
    
    # Normalizar formato PostgreSQL si es necesario
    if database_url.startswith('postgres://'):
        # Algunos proveedores usan postgres://, cambiar a postgresql://
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///sena.db'

class TestingConfig(Config):
    """Configuración pruebas"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
