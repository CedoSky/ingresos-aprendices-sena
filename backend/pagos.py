"""
Módulo de pagos — Integración con Wompi (Bancolombia)
------------------------------------------------------
Documentación oficial Wompi: https://docs.wompi.co/

Métodos de pago soportados automáticamente por el widget de Wompi:
  • Tarjetas crédito/débito  (Visa, Mastercard, Amex, Diners — nacionales e internacionales)
  • Nequi
  • PSE  (débito bancario directo)
  • Bancolombia button
  • Efecty
  • Baloto

Variables de entorno requeridas (backend/.env):
  WOMPI_PUBLIC_KEY      = pub_test_XXXX  (o pub_prod_XXXX en producción)
  WOMPI_PRIVATE_KEY     = prv_test_XXXX
  WOMPI_INTEGRITY_SECRET = integ_test_XXXX
  WOMPI_EVENTS_SECRET   = evt_test_XXXX
  WOMPI_ENV             = sandbox   (o prod)
"""

import os
import hashlib
import hmac
import uuid
import requests
from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
import correo as srv_correo

pagos_bp = Blueprint('pagos', __name__, url_prefix='/api/pagos')

# ── Configuración Wompi ────────────────────────────────────────────────────────
WOMPI_PUBLIC_KEY        = os.getenv('WOMPI_PUBLIC_KEY', '')
WOMPI_PRIVATE_KEY       = os.getenv('WOMPI_PRIVATE_KEY', '')
WOMPI_INTEGRITY_SECRET  = os.getenv('WOMPI_INTEGRITY_SECRET', '')
WOMPI_EVENTS_SECRET     = os.getenv('WOMPI_EVENTS_SECRET', '')
WOMPI_ENV               = os.getenv('WOMPI_ENV', 'sandbox')   # 'sandbox' | 'prod'

WOMPI_API = {
    'sandbox': 'https://sandbox.wompi.co/v1',
    'prod':    'https://production.wompi.co/v1',
}

SECRET_KEY = os.getenv('JWT_SECRET_KEY')

# ── Planes (precios en COP) ────────────────────────────────────────────────────
PLANES = {
    'mensual': {
        'nombre':      'Plan Mensual',
        'precio_cop':  39_900,           # $39,900 COP
        'centavos':    3_990_000,        # Wompi trabaja en centavos
        'dias':        30,
        'descripcion': '1 mes — generaciones ilimitadas de códigos de barras',
    },
    'anual': {
        'nombre':      'Plan Anual',
        'precio_cop':  299_000,          # $299,000 COP
        'centavos':    29_900_000,
        'dias':        365,
        'descripcion': '12 meses — ahorra 37% respecto al plan mensual',
    },
}

# ── Decorador JWT ──────────────────────────────────────────────────────────────
def _token_requerido(f):
    @wraps(f)
    def _decorated(*args, **kwargs):
        raw = request.headers.get('Authorization', '')
        token = raw.replace('Bearer ', '').strip()
        if not token:
            return jsonify({'error': 'Token requerido'}), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except Exception:
            return jsonify({'error': 'Token inválido o expirado'}), 401
        return f(*args, **kwargs)
    return _decorated


# ── Utilidades ─────────────────────────────────────────────────────────────────
def _integridad(referencia: str, centavos: int, moneda: str = 'COP') -> str:
    """
    Hash SHA-256 requerido por Wompi para validar la integridad del widget.
    Fórmula: SHA256(referencia + centavos + moneda + integrity_secret)
    """
    cadena = f"{referencia}{centavos}{moneda}{WOMPI_INTEGRITY_SECRET}"
    return hashlib.sha256(cadena.encode('utf-8')).hexdigest()


def _wompi_get(path: str) -> dict:
    """Consulta GET autenticada a la API de Wompi."""
    base = WOMPI_API.get(WOMPI_ENV, WOMPI_API['sandbox'])
    r = requests.get(
        f"{base}{path}",
        headers={'Authorization': f'Bearer {WOMPI_PRIVATE_KEY}'},
        timeout=12,
    )
    r.raise_for_status()
    return r.json()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@pagos_bp.route('/planes', methods=['GET'])
def get_planes():
    """Devuelve los planes con precios en COP (sin autenticación)."""
    return jsonify({'planes': PLANES, 'wompi_env': WOMPI_ENV}), 200


@pagos_bp.route('/iniciar', methods=['POST'])
@_token_requerido
def iniciar_pago():
    """
    Genera la referencia única y el hash de integridad para el widget de Wompi.
    El frontend usa esta respuesta para abrir el checkout de Wompi directamente.

    Body JSON:
        { "plan": "mensual" | "anual" }

    Respuesta:
        referencia, monto_centavos, integridad, wompi_public_key, redirect_url, ...
    """
    datos = request.get_json(silent=True) or {}
    plan = datos.get('plan', 'mensual')

    if plan not in PLANES:
        return jsonify({'error': f'Plan inválido: {plan}'}), 400

    info = PLANES[plan]
    ref  = f"SENA-BC-{plan.upper()}-{uuid.uuid4().hex[:10].upper()}"

    # URL de retorno después del pago (página de resultado en el mismo servidor)
    host = request.host_url.rstrip('/')
    redirect_url = f"{host}/pago-resultado"

    # Modo demo: claves no configuradas o son placeholders de ejemplo
    _es_demo = (
        not WOMPI_PUBLIC_KEY
        or 'XXXX' in WOMPI_PUBLIC_KEY
        or WOMPI_PUBLIC_KEY in ('pub_test_XXXXXXXXXXXXXXXXXXXXXXXX', 'pub_prod_XXXXXXXXXXXXXXXXXXXXXXXX')
    )

    return jsonify({
        'referencia':       ref,
        'monto_centavos':   info['centavos'],
        'monto_cop':        info['precio_cop'],
        'moneda':           'COP',
        'integridad':       _integridad(ref, info['centavos']),
        'plan':             plan,
        'plan_nombre':      info['nombre'],
        'plan_descripcion': info['descripcion'],
        'dias':             info['dias'],
        'wompi_public_key': WOMPI_PUBLIC_KEY,
        'wompi_env':        WOMPI_ENV,
        'redirect_url':     redirect_url,
        'demo_mode':        _es_demo,
    }), 200


@pagos_bp.route('/verificar/<transaction_id>', methods=['GET'])
@_token_requerido
def verificar_pago(transaction_id):
    """
    Consulta el estado real de una transacción en la API de Wompi.
    Estados posibles: PENDING, APPROVED, DECLINED, VOIDED, ERROR
    """
    try:
        data = _wompi_get(f'/transactions/{transaction_id}')
        tx   = data.get('data', {})
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Timeout al consultar Wompi'}), 504
    except requests.exceptions.HTTPError as e:
        return jsonify({'error': f'Error Wompi: {e.response.status_code}'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    estado    = tx.get('status', '')
    referencia = tx.get('reference', '')
    aprobado  = estado == 'APPROVED'

    # Determinar el plan desde la referencia
    plan = None
    if '-MENSUAL-' in referencia:
        plan = 'mensual'
    elif '-ANUAL-' in referencia:
        plan = 'anual'

    dias = PLANES[plan]['dias'] if plan else 0

    # Enviar correo de confirmacion si el pago fue aprobado
    if aprobado:
        try:
            raw = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
            from models import Usuario
            token_data = jwt.decode(raw, SECRET_KEY, algorithms=['HS256'])
            usuario = Usuario.query.get(token_data.get('usuario_id'))
            if usuario and usuario.email:
                from datetime import datetime, timedelta
                expiry = datetime.utcnow() + timedelta(days=dias)
                srv_correo.confirmacion_suscripcion(
                    email            = usuario.email,
                    plan             = plan or 'mensual',
                    dias             = dias,
                    metodo_pago      = tx.get('payment_method_type', ''),
                    fecha_expiracion = expiry.strftime('%d/%m/%Y'),
                )
        except Exception as _e:
            print(f'[CORREO] Error enviando confirmacion suscripcion: {_e}')

    return jsonify({
        'transaction_id': transaction_id,
        'estado':         estado,
        'aprobado':       aprobado,
        'referencia':     referencia,
        'plan':           plan,
        'dias':           dias,
        'monto_centavos': tx.get('amount_in_cents', 0),
        'moneda':         tx.get('currency', 'COP'),
        'metodo_pago':    tx.get('payment_method_type', ''),
        'fecha':          tx.get('created_at', ''),
    }), 200


@pagos_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook oficial de Wompi.
    Wompi envía eventos POST aquí cuando una transacción cambia de estado.
    Se valida la firma usando WOMPI_EVENTS_SECRET.

    Configurar en el dashboard de Wompi:
      URL: https://tu-dominio.com/api/pagos/webhook
    """
    checksum_recibido = request.headers.get('X-Event-Checksum', '')
    timestamp         = request.headers.get('X-Event-Timestamp', '')
    cuerpo            = request.get_data(as_text=True)

    # Validar firma si el secret está configurado
    if WOMPI_EVENTS_SECRET and checksum_recibido:
        cadena_firma = timestamp + cuerpo + WOMPI_EVENTS_SECRET
        firma_calc   = hashlib.sha256(cadena_firma.encode('utf-8')).hexdigest()
        if not hmac.compare_digest(firma_calc, checksum_recibido):
            return jsonify({'error': 'Firma de webhook inválida'}), 401

    evento = request.get_json(force=True) or {}
    tipo   = evento.get('event', '')
    tx     = evento.get('data', {}).get('transaction', {})

    if tipo == 'transaction.updated' and tx.get('status') == 'APPROVED':
        referencia = tx.get('reference', '')
        monto      = tx.get('amount_in_cents', 0)
        metodo     = tx.get('payment_method_type', 'desconocido')
        print(f'[WOMPI WEBHOOK] ✅ Pago aprobado | ref={referencia} | ${monto} COP | via {metodo}')
        # ─ Aquí puedes persistir la suscripción en BD si agregas una tabla de suscripciones ─

    return jsonify({'received': True}), 200
