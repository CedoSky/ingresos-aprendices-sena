"""
Módulo de correo institucional — Sistema SENA
----------------------------------------------
Envía correos HTML profesionales usando Gmail SMTP.

Variables requeridas en backend/.env:
  GMAIL_REMITENTE    = tucorreo@gmail.com
  GMAIL_APP_PASSWORD = xxxx xxxx xxxx xxxx   ← Contraseña de aplicación Gmail (16 caracteres)
  GMAIL_NOMBRE       = SENA Centro de Formación   (nombre que aparece en el remitente)
  ADMIN_EMAIL        = admin@sena.edu.co          (recibe reportes y alertas)

Cómo obtener la contraseña de aplicación Gmail:
  1. Activa verificación en 2 pasos en tu cuenta Google
  2. Ve a myaccount.google.com → Seguridad → Contraseñas de aplicaciones
  3. Selecciona "Correo" + "Otro dispositivo" → Genera
  4. Copia las 16 letras y pégalas en GMAIL_APP_PASSWORD
"""

import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── Configuración ──────────────────────────────────────────────────────────────
GMAIL_REMITENTE    = os.getenv('GMAIL_REMITENTE', '')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
GMAIL_NOMBRE       = os.getenv('GMAIL_NOMBRE', 'SENA — Sistema de Ingresos')
ADMIN_EMAIL        = os.getenv('ADMIN_EMAIL', '')

# ── Color palette SENA ─────────────────────────────────────────────────────────
VERDE_SENA  = '#39A900'
AZUL_OSCURO = '#0a1628'
GRIS_CLARO  = '#f5f7fa'


def _emails_admin() -> list:
    """
    Devuelve la lista de correos de todos los usuarios con rol 'admin' activos.
    Consulta la BD en tiempo real — no requiere configuracion manual.
    Si la consulta falla, usa ADMIN_EMAIL del .env como respaldo.
    """
    try:
        from models import Usuario
        admins = Usuario.query.filter_by(rol='admin', activo=True, deleted_at=None).all()
        emails = [u.email for u in admins if u.email]
        if emails:
            return emails
    except Exception:
        pass
    # Fallback: variable de entorno
    fallback = ADMIN_EMAIL
    return [fallback] if fallback else []


def _configurado() -> bool:
    """Retorna True si las credenciales de Gmail están configuradas."""
    return bool(GMAIL_REMITENTE and GMAIL_APP_PASSWORD)


def _enviar_smtp(destinatario: str, asunto: str, html: str, texto_plano: str = '') -> bool:
    """Envía el correo por SMTP. Bloquea hasta terminar — usar en hilo separado."""
    if not _configurado():
        print(f'[CORREO] No configurado. Correo a {destinatario} omitido: {asunto}')
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = asunto
        msg['From']    = f'{GMAIL_NOMBRE} <{GMAIL_REMITENTE}>'
        msg['To']      = destinatario
        msg['Reply-To'] = GMAIL_REMITENTE

        if texto_plano:
            msg.attach(MIMEText(texto_plano, 'plain', 'utf-8'))
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_REMITENTE, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_REMITENTE, destinatario, msg.as_string())

        print(f'[CORREO] ✓ Enviado a {destinatario}: {asunto}')
        return True
    except Exception as e:
        print(f'[CORREO] ✗ Error enviando a {destinatario}: {e}')
        return False


def _enviar_async(destinatario: str, asunto: str, html: str, texto_plano: str = ''):
    """Envía el correo en un hilo de fondo para no bloquear la petición HTTP."""
    if not destinatario or '@' not in destinatario:
        return
    t = threading.Thread(
        target=_enviar_smtp,
        args=(destinatario, asunto, html, texto_plano),
        daemon=True
    )
    t.start()


def enviar_codigo_verificacion(destinatario: str, codigo: str, nombre: str = '') -> bool:
    """
    Envía un código de verificación de 6 dígitos al correo indicado.
    Usado al crear usuarios desde la terminal para confirmar que el correo es real.
    Bloquea hasta que se envíe (síncrono), retorna True si tuvo éxito.
    """
    saludo = f'Hola {nombre.split()[0]},' if nombre else 'Hola,'
    html = _base(f"""
    <h2>Verificación de correo electrónico</h2>
    <p>{saludo} se está creando una cuenta en el <strong>Sistema SENA de Control de Ingresos</strong>.
    Para confirmar que este correo es tuyo, ingresa el siguiente código en la terminal:</p>
    <div style="text-align:center;margin:32px 0;">
      <span style="font-size:42px;font-weight:900;letter-spacing:12px;
                   color:#003087;background:#f0f4ff;padding:16px 32px;
                   border-radius:12px;border:2px dashed #003087;">{codigo}</span>
    </div>
    <p style="color:#888;font-size:13px;">Este código expira en <strong>10 minutos</strong>.
    Si no solicitaste esto, ignora este mensaje.</p>
    """)
    texto = f'{saludo}\n\nTu código de verificación SENA es: {codigo}\n\nExpira en 10 minutos.'
    return _enviar_smtp(destinatario, 'SENA — Código de verificación de correo', html, texto)


# ── Plantilla base ─────────────────────────────────────────────────────────────
def _base(contenido_html: str, pie: str = '') -> str:
    year = datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ margin:0; padding:0; background:{GRIS_CLARO}; font-family:'Segoe UI',Arial,sans-serif; }}
  .wrapper {{ max-width:600px; margin:32px auto; background:#fff;
              border-radius:16px; overflow:hidden;
              box-shadow:0 8px 32px rgba(0,0,0,.10); }}
  .header {{ background:linear-gradient(135deg,{AZUL_OSCURO} 0%,#003087 60%,{VERDE_SENA} 100%);
             padding:36px 40px 28px; text-align:center; color:#fff; }}
  .header img {{ height:50px; margin-bottom:14px; }}
  .header h1 {{ margin:0; font-size:22px; font-weight:900; letter-spacing:.5px; }}
  .header p {{ margin:6px 0 0; opacity:.85; font-size:13px; }}
  .body {{ padding:36px 40px; color:#333; line-height:1.65; }}
  .body h2 {{ color:{AZUL_OSCURO}; font-size:18px; margin-top:0; }}
  .card {{ background:{GRIS_CLARO}; border-radius:12px; padding:20px 24px;
           margin:20px 0; border-left:4px solid {VERDE_SENA}; }}
  .card-row {{ display:flex; justify-content:space-between; padding:5px 0;
               border-bottom:1px solid #e8eaf0; font-size:14px; }}
  .card-row:last-child {{ border-bottom:none; }}
  .card-row .lbl {{ color:#777; font-weight:600; }}
  .card-row .val {{ color:#222; font-weight:700; text-align:right; max-width:60%; }}
  .badge {{ display:inline-block; padding:5px 16px; border-radius:20px;
            font-size:12px; font-weight:800; letter-spacing:.5px; }}
  .badge-verde  {{ background:#e6f7d9; color:#2a6b00; }}
  .badge-rojo   {{ background:#fff0f0; color:#c62828; }}
  .badge-azul   {{ background:#e8f0ff; color:#003087; }}
  .badge-naranja{{ background:#fff3e0; color:#e65100; }}
  .btn {{ display:inline-block; margin:20px 0 8px; padding:14px 32px;
          background:linear-gradient(135deg,#003087,{VERDE_SENA});
          color:#fff; border-radius:10px; text-decoration:none;
          font-weight:800; font-size:15px; }}
  .divider {{ height:1px; background:#eef0f4; margin:24px 0; }}
  .footer {{ background:#f0f4f8; padding:20px 40px; text-align:center;
             font-size:12px; color:#aaa; border-top:1px solid #e8eaf0; }}
  .footer a {{ color:{VERDE_SENA}; text-decoration:none; font-weight:700; }}
  @media(max-width:600px){{
    .body,.header,.footer{{ padding:24px 20px; }}
    .card-row{{ flex-direction:column; }}
    .card-row .val{{ text-align:left; margin-top:2px; }}
  }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>🏫 SENA — Sistema de Ingresos</h1>
    <p>Servicio Nacional de Aprendizaje</p>
  </div>
  <div class="body">
    {contenido_html}
  </div>
  <div class="footer">
    {pie or f'© {year} SENA — Sistema de Control de Ingresos &nbsp;·&nbsp; Correo generado automáticamente, no responder.'}
  </div>
</div>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════════════════════
#  CORREOS PÚBLICOS
# ══════════════════════════════════════════════════════════════════════════════

def bienvenida_nueva_persona(persona: dict):
    """
    Enviado cuando se registra una nueva persona en el sistema.
    persona = { nombre, numero_doc, tipo_doc, perfil, programa, ficha, email }
    """
    if not persona.get('email'):
        return

    nombre  = persona.get('nombre', 'Estimado/a')
    perfil  = (persona.get('perfil') or 'APRENDIZ').capitalize()
    prog    = persona.get('programa') or '—'
    ficha   = persona.get('ficha') or '—'
    doc     = persona.get('numero_doc', '—')
    tipo_d  = persona.get('tipo_doc', 'CC')
    fecha   = datetime.now().strftime('%d/%m/%Y %H:%M')

    html_cuerpo = f"""
    <h2>¡Bienvenido/a al SENA, {nombre.split()[0]}! 👋</h2>
    <p>Tu información ha sido registrada exitosamente en el <strong>Sistema de Control de Ingresos</strong>
       del SENA. Desde ahora podrás registrar tu entrada y salida de las instalaciones.</p>

    <div class="card">
      <div class="card-row"><span class="lbl">Nombre completo</span><span class="val">{nombre}</span></div>
      <div class="card-row"><span class="lbl">Documento</span><span class="val">{tipo_d} {doc}</span></div>
      <div class="card-row"><span class="lbl">Perfil</span>
        <span class="val"><span class="badge badge-azul">{perfil}</span></span></div>
      <div class="card-row"><span class="lbl">Programa</span><span class="val">{prog}</span></div>
      <div class="card-row"><span class="lbl">Ficha</span><span class="val">{ficha}</span></div>
      <div class="card-row"><span class="lbl">Fecha de registro</span><span class="val">{fecha}</span></div>
    </div>

    <div class="divider"></div>
    <p style="font-size:14px;color:#555;">
      📌 <strong>Cómo registrar tu ingreso:</strong><br>
      Presenta tu número de documento <strong>{doc}</strong> en el quiosco de entrada
      o al vigilante de turno. El sistema registrará tu entrada y salida automáticamente.
    </p>
    <p style="font-size:13px;color:#aaa;">
      Si no reconoces este registro, comunícate con el administrador del sistema.
    </p>
    """

    asunto = f'✅ Registro exitoso en SENA — Bienvenido/a, {nombre.split()[0]}'
    _enviar_async(persona['email'], asunto, _base(html_cuerpo),
                  f'Bienvenido/a al SENA, {nombre}. Tu documento {doc} ha sido registrado.')


def confirmacion_ingreso(persona: dict, tipo: str, timestamp: str,
                         ambiente: str = None, observaciones: str = None):
    """
    Enviado al registrar ENTRADA o SALIDA de una persona (si tiene email).
    """
    if not persona.get('email'):
        return

    nombre   = persona.get('nombre', 'Usuario')
    es_entrada = tipo.upper() == 'ENTRADA'
    color_badge = 'badge-verde' if es_entrada else 'badge-naranja'
    icono   = '🟢' if es_entrada else '🟠'
    accion  = 'Entrada registrada' if es_entrada else 'Salida registrada'

    try:
        dt = datetime.fromisoformat(timestamp.replace('Z',''))
        fecha_fmt = dt.strftime('%d/%m/%Y')
        hora_fmt  = dt.strftime('%H:%M:%S')
    except Exception:
        fecha_fmt = timestamp
        hora_fmt  = ''

    amb_row = f'<div class="card-row"><span class="lbl">Ambiente</span><span class="val">{ambiente}</span></div>' if ambiente else ''
    obs_row = f'<div class="card-row"><span class="lbl">Observaciones</span><span class="val">{observaciones}</span></div>' if observaciones else ''

    html_cuerpo = f"""
    <h2>{icono} {accion}</h2>
    <p>Hola <strong>{nombre.split()[0]}</strong>, confirmamos que tu
       <strong>{'entrada' if es_entrada else 'salida'}</strong> fue registrada correctamente.</p>

    <div class="card">
      <div class="card-row"><span class="lbl">Tipo de registro</span>
        <span class="val"><span class="badge {color_badge}">{tipo.upper()}</span></span></div>
      <div class="card-row"><span class="lbl">Fecha</span><span class="val">{fecha_fmt}</span></div>
      <div class="card-row"><span class="lbl">Hora</span><span class="val">{hora_fmt}</span></div>
      {amb_row}
      {obs_row}
    </div>

    <p style="font-size:13px;color:#aaa;">
      Si no reconoces este registro, comunícate inmediatamente con el área de vigilancia.
    </p>
    """

    asunto = f'{icono} {accion} — SENA {fecha_fmt} {hora_fmt}'
    _enviar_async(persona['email'], asunto, _base(html_cuerpo),
                  f'{accion}: {nombre} — {fecha_fmt} {hora_fmt}')


def credenciales_nuevo_usuario(email: str, nombre: str, rol: str, password_temporal: str):
    """
    Enviado al crear un nuevo usuario del sistema (admin, vigilante).
    """
    if not email:
        return

    rol_label = {'admin': 'Administrador', 'vigilante': 'Vigilante', 'sistemas': 'Sistemas'}.get(rol, rol)
    url_acceso = 'http://localhost:8000/login'

    html_cuerpo = f"""
    <h2>🔑 Credenciales de acceso al sistema</h2>
    <p>Hola <strong>{nombre}</strong>, se ha creado tu cuenta en el
       <strong>Sistema de Control de Ingresos SENA</strong>.</p>

    <div class="card">
      <div class="card-row"><span class="lbl">Correo de acceso</span><span class="val">{email}</span></div>
      <div class="card-row"><span class="lbl">Contraseña temporal</span>
        <span class="val" style="font-family:monospace;font-size:16px;letter-spacing:2px;">{password_temporal}</span></div>
      <div class="card-row"><span class="lbl">Rol asignado</span>
        <span class="val"><span class="badge badge-azul">{rol_label}</span></span></div>
    </div>

    <a href="{url_acceso}" class="btn">Iniciar sesión ahora →</a>

    <div class="divider"></div>
    <p style="font-size:13px;color:#c62828;font-weight:700;">
      ⚠️ Por seguridad, cambia tu contraseña en el primer inicio de sesión.
         No compartas estas credenciales.
    </p>
    """

    asunto = f'🔑 Tus credenciales de acceso — Sistema SENA'
    _enviar_async(email, asunto, _base(html_cuerpo),
                  f'Usuario: {email} | Contraseña: {password_temporal} | Rol: {rol_label}')


def alerta_acceso_fallido(email_admin: str = '', numero_doc: str = '', motivo: str = '',
                           ip: str = None, timestamp: str = None):
    """
    Enviado a todos los administradores cuando se detecta un intento de acceso bloqueado.
    """
    destinos = _emails_admin()
    if not destinos:
        return

    try:
        dt = datetime.fromisoformat((timestamp or datetime.utcnow().isoformat()).replace('Z',''))
        fecha_fmt = dt.strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        fecha_fmt = timestamp or datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    ip_row = f'<div class="card-row"><span class="lbl">IP origen</span><span class="val">{ip}</span></div>' if ip else ''

    html_cuerpo = f"""
    <h2>🚨 Alerta de acceso bloqueado</h2>
    <p>El sistema detectó un intento de registro que fue <strong>bloqueado</strong>.</p>

    <div class="card">
      <div class="card-row"><span class="lbl">Documento</span><span class="val">{numero_doc}</span></div>
      <div class="card-row"><span class="lbl">Motivo del bloqueo</span>
        <span class="val"><span class="badge badge-rojo">{motivo}</span></span></div>
      <div class="card-row"><span class="lbl">Fecha y hora</span><span class="val">{fecha_fmt}</span></div>
      {ip_row}
    </div>

    <p style="font-size:14px;color:#555;">
      Revisa el módulo de vigilancia para más detalles sobre este evento.
    </p>
    """

    asunto = f'🚨 Alerta SENA — Acceso bloqueado: {numero_doc}'
    texto_plano = f'Alerta: acceso bloqueado para {numero_doc}. Motivo: {motivo}'
    for dest in destinos:
        _enviar_async(dest, asunto, _base(html_cuerpo), texto_plano)


def alerta_seguridad_equipo(tipo_alerta: str,
                            codigo_barras: str,
                            marca_modelo: str,
                            portador_doc: str,
                            persona_esperada: str,
                            accion: str = 'ENTRADA',
                            email_admin: str = '',   # ignorado — se usa la BD
                            timestamp: str = None):
    """
    Enviado al administrador cuando se detecta una anomalía de seguridad en un equipo.

    tipo_alerta:
      'propietario' → la persona que porta el equipo NO es su dueño registrado.
      'custodio'    → la persona que intenta sacar el equipo NO fue quien lo ingresó.
    """
    destinos = _emails_admin()
    if not destinos:
        return

    try:
        dt = datetime.fromisoformat((timestamp or datetime.utcnow().isoformat()).replace('Z', ''))
        fecha_fmt = dt.strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        fecha_fmt = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    if tipo_alerta == 'propietario':
        titulo   = '⚠️ Alerta de propietario — equipo con portador no autorizado'
        desc     = f'Un equipo fue escaneado por una persona que <strong>no es su propietario registrado</strong>.'
        lbl_esp  = 'Propietario registrado'
        accion_label = 'ENTRADA'
    else:
        titulo   = '⚠️ Alerta de custodio — equipo saliendo con persona distinta'
        desc     = f'Un equipo está siendo sacado de sede por una persona <strong>diferente a quien lo ingresó</strong>.'
        lbl_esp  = 'Quien lo ingresó'
        accion_label = 'SALIDA'

    html_cuerpo = f"""
    <h2>{titulo}</h2>
    <p>{desc}</p>

    <div class="card">
      <div class="card-row"><span class="lbl">Equipo</span>
        <span class="val" style="font-weight:700">{marca_modelo}</span></div>
      <div class="card-row"><span class="lbl">Código de barras</span>
        <span class="val" style="font-family:monospace">{codigo_barras}</span></div>
      <div class="card-row"><span class="lbl">Acción detectada</span>
        <span class="val"><span class="badge badge-naranja">{accion_label}</span></span></div>
      <div class="card-row"><span class="lbl">Portador actual (documento)</span>
        <span class="val" style="font-family:monospace">{portador_doc}</span></div>
      <div class="card-row"><span class="lbl">{lbl_esp}</span>
        <span class="val">{persona_esperada}</span></div>
      <div class="card-row"><span class="lbl">Fecha y hora</span>
        <span class="val">{fecha_fmt}</span></div>
    </div>

    <p style="font-size:14px;color:#c62828;font-weight:700;">
      ⚠️ Revisa este evento en el panel de Seguridad y toma las medidas correspondientes.
    </p>
    """

    asunto = f'⚠️ Alerta equipo SENA — {tipo_alerta.capitalize()}: {codigo_barras}'
    texto_plano = f'Alerta {tipo_alerta}: equipo {codigo_barras} ({marca_modelo}) portado por {portador_doc}. Esperado: {persona_esperada}'
    for dest in destinos:
        _enviar_async(dest, asunto, _base(html_cuerpo), texto_plano)


def confirmacion_suscripcion(email: str, plan: str, dias: int,
                              metodo_pago: str = '', fecha_expiracion: str = ''):
    """
    Enviado cuando se activa una suscripción Premium del generador de códigos de barras.
    """
    if not email:
        return

    plan_nombre = 'Plan Mensual' if plan == 'mensual' else 'Plan Anual'
    precio      = '$39.900 COP' if plan == 'mensual' else '$299.000 COP'
    metodo_row  = f'<div class="card-row"><span class="lbl">Método de pago</span><span class="val">{metodo_pago}</span></div>' if metodo_pago else ''

    html_cuerpo = f"""
    <h2>⭐ ¡Suscripción Premium activada!</h2>
    <p>Tu pago fue procesado exitosamente. Ahora tienes acceso <strong>ilimitado</strong>
       al generador de códigos de barras del Sistema SENA.</p>

    <div class="card">
      <div class="card-row"><span class="lbl">Plan</span>
        <span class="val"><span class="badge badge-azul">{plan_nombre}</span></span></div>
      <div class="card-row"><span class="lbl">Precio pagado</span><span class="val">{precio}</span></div>
      <div class="card-row"><span class="lbl">Duración</span><span class="val">{dias} días</span></div>
      {metodo_row}
      <div class="card-row"><span class="lbl">Válido hasta</span>
        <span class="val" style="color:{VERDE_SENA};font-weight:900;">{fecha_expiracion}</span></div>
    </div>

    <p style="font-size:14px;color:#555;">
      Tu suscripción se administra directamente desde el panel de administración.
      No se renueva automáticamente — recibirás un aviso antes de que venza.
    </p>
    """

    asunto = f'⭐ Suscripción Premium activada — {plan_nombre}'
    _enviar_async(email, asunto, _base(html_cuerpo),
                  f'Suscripción {plan_nombre} activada. Válida por {dias} días hasta {fecha_expiracion}.')


def reporte_diario_admin(email_admin: str = '', resumen: dict = None):
    """
    Reporte diario enviado a todos los administradores con estadísticas del día.
    resumen = {
        fecha, total_entradas, total_salidas, total_personas_distintas,
        primera_entrada, ultima_salida, perfiles: {APRENDIZ: n, INSTRUCTOR: n, ...}
    }
    """
    resumen = resumen or {}
    destinos = _emails_admin()
    if not destinos:
        return

    fecha   = resumen.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    ent     = resumen.get('total_entradas', 0)
    sal     = resumen.get('total_salidas', 0)
    pers    = resumen.get('total_personas_distintas', 0)
    primera = resumen.get('primera_entrada', '—')
    ultima  = resumen.get('ultima_salida', '—')
    perfiles = resumen.get('perfiles', {})

    filas_perfiles = ''.join(
        f'<div class="card-row"><span class="lbl">{k.capitalize()}</span>'
        f'<span class="val">{v} personas</span></div>'
        for k, v in perfiles.items()
    )

    html_cuerpo = f"""
    <h2>📊 Reporte diario — {fecha}</h2>
    <p>Resumen de actividad del día en el Sistema de Control de Ingresos SENA.</p>

    <div class="card">
      <div class="card-row"><span class="lbl">Total entradas</span>
        <span class="val"><span class="badge badge-verde">▲ {ent}</span></span></div>
      <div class="card-row"><span class="lbl">Total salidas</span>
        <span class="val"><span class="badge badge-naranja">▼ {sal}</span></span></div>
      <div class="card-row"><span class="lbl">Personas distintas</span>
        <span class="val">{pers}</span></div>
      <div class="card-row"><span class="lbl">Primera entrada</span><span class="val">{primera}</span></div>
      <div class="card-row"><span class="lbl">Última salida</span><span class="val">{ultima}</span></div>
    </div>

    {'<div class="card">' + filas_perfiles + '</div>' if filas_perfiles else ''}

    <p style="font-size:13px;color:#aaa;">
      Este reporte fue generado automáticamente. Puedes consultarlo en detalle
      en el panel de administración.
    </p>
    """

    asunto = f'📊 Reporte diario SENA — {fecha}'
    texto_plano = f'Reporte {fecha}: {ent} entradas, {sal} salidas, {pers} personas.'
    for dest in destinos:
        _enviar_async(dest, asunto, _base(html_cuerpo), texto_plano)


# ── Endpoint de prueba (llamado desde admin) ────────────────────────────────────
def enviar_correo_prueba(email_destino: str) -> dict:
    """Envía un correo de prueba para verificar la configuración."""
    if not _configurado():
        return {
            'ok': False,
            'error': 'Credenciales Gmail no configuradas. Revisa GMAIL_REMITENTE y GMAIL_APP_PASSWORD en backend/.env'
        }

    html = _base(f"""
    <h2>✅ Configuración de correo verificada</h2>
    <p>Si recibes este mensaje, el sistema de correo institucional del SENA
       está funcionando correctamente.</p>
    <div class="card">
      <div class="card-row"><span class="lbl">Remitente</span><span class="val">{GMAIL_REMITENTE}</span></div>
      <div class="card-row"><span class="lbl">Nombre</span><span class="val">{GMAIL_NOMBRE}</span></div>
      <div class="card-row"><span class="lbl">Fecha prueba</span>
        <span class="val">{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</span></div>
    </div>
    """)

    ok = _enviar_smtp(email_destino, '✅ Prueba de correo — Sistema SENA', html)
    if ok:
        return {'ok': True, 'mensaje': f'Correo de prueba enviado a {email_destino}'}
    return {'ok': False, 'error': 'Error al enviar. Revisa los logs del servidor.'}
