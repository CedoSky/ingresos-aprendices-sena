"""
Módulo de validaciones de seguridad — Sistema SENA
----------------------------------------------------
Valida emails (formato + dominio real), contraseñas seguras y nombres.
Usado tanto en el script de gestión de usuarios (terminal) como en la API.
"""
import re
import socket

# ── Regex de email RFC-5321 simplificado ────────────────────────────────────
_EMAIL_RE = re.compile(
    r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
)

# Dominios de correo desechable/temporal conocidos
_DOMINIOS_DESECHABLES = {
    'mailinator.com', 'guerrillamail.com', 'guerrillamailblock.com',
    'temp-mail.org', 'throwaway.email', 'yopmail.com', 'dispostable.com',
    'trashmail.com', 'maildrop.cc', '10minutemail.com', 'tempmail.com',
    'fakeinbox.com', 'discard.email', 'sharklasers.com', 'spam4.me',
    'getairmail.com', 'filzmail.com', 'trashmail.at', 'trashmail.io',
    'tempinbox.com', 'mailnull.com', 'spamgourmet.com', 'spamgourmet.net',
    'spamgourmet.org', 'jetable.fr.nf', 'trashmail.me', 'throwam.com',
}

# Contraseñas comunes prohibidas
_CONTRASENAS_COMUNES = {
    'password', 'contraseña', 'contrasena', '12345678', '123456789',
    '1234567890', 'password1', 'qwerty123', 'admin1234', 'sena1234',
    'sena2024', 'sena2025', 'sena2026', '87654321', 'abcd1234',
    'pass1234', 'welcome1', 'colombia1', 'bogota123', 'Colombia1',
    'Sena2024', 'Sena2025', 'Sena2026', 'Admin123', 'admin123',
    'Admin1234', 'adminadmin', 'passpass', 'test1234', 'Test1234',
}


# ═══════════════════════════════════════════════════════════════════════════
#  VALIDACIÓN DE EMAIL
# ═══════════════════════════════════════════════════════════════════════════

def validar_formato_email(email: str) -> tuple:
    """
    Valida que el email tenga un formato correcto y no sea de un
    proveedor desechable.
    Retorna (ok: bool, mensaje: str).
    """
    if not email:
        return False, 'El email es requerido.'
    if len(email) > 255:
        return False, 'El email es demasiado largo (máximo 255 caracteres).'
    if not _EMAIL_RE.match(email):
        return False, f'Formato de email inválido: "{email}". Ejemplo válido: nombre@dominio.com'
    dominio = email.split('@')[1].lower()
    if dominio in _DOMINIOS_DESECHABLES:
        return False, f'No se permiten correos desechables o temporales ({dominio}).'
    return True, ''


def validar_dominio_email(email: str, verbose: bool = False) -> tuple:
    """
    Verifica que el dominio del email exista en DNS usando el resolvedor
    del sistema operativo (socket), que es el más confiable en cualquier
    red incluidas redes corporativas/educativas.

    Retorna (ok: bool, mensaje: str).
    """
    dominio = email.split('@')[1].lower()
    # Dominios muy conocidos: aceptar directamente sin consulta DNS
    _DOMINIOS_CONOCIDOS = {
        'gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com', 'yahoo.es',
        'live.com', 'icloud.com', 'me.com', 'protonmail.com', 'proton.me',
        'sena.edu.co', 'misena.edu.co', 'etb.net.co', 'une.net.co',
    }
    if dominio in _DOMINIOS_CONOCIDOS:
        if verbose:
            return True, f'Dominio "{dominio}" reconocido.'
        return True, ''

    # Para otros dominios: usar el DNS del sistema (no dnspython, evita timeouts de firewall)
    socket.setdefaulttimeout(4)
    try:
        socket.getaddrinfo(dominio, None)
        if verbose:
            return True, f'Dominio "{dominio}" verificado.'
        return True, ''
    except socket.gaierror:
        return False, (
            f'El dominio "{dominio}" no existe o no se puede resolver. '
            f'Verifica que el email sea correcto.'
        )
    except OSError:
        # Sin conexión a internet: advertencia no fatal
        return True, f'(Sin conexión para verificar "{dominio}" — se asume válido.)'
    finally:
        socket.setdefaulttimeout(None)


def validar_email_completo(email: str, verificar_dominio: bool = True) -> tuple:
    """
    Validación completa: formato + dominio.
    Retorna (ok: bool, lista_de_errores: list[str]).
    """
    errores = []
    ok_fmt, msg_fmt = validar_formato_email(email)
    if not ok_fmt:
        errores.append(msg_fmt)
        return False, errores  # No tiene sentido verificar dominio si el formato es malo

    if verificar_dominio:
        ok_dom, msg_dom = validar_dominio_email(email)
        if not ok_dom:
            errores.append(msg_dom)
        elif msg_dom:  # advertencias no fatales
            errores.append(f'[Advertencia] {msg_dom}')

    return len(errores) == 0, errores


# ═══════════════════════════════════════════════════════════════════════════
#  VALIDACIÓN DE CONTRASEÑA
# ═══════════════════════════════════════════════════════════════════════════

def validar_contrasena(password: str) -> tuple:
    """
    Valida que la contraseña cumpla la política de seguridad del sistema.
    Política:
      - Mínimo 10 caracteres
      - Al menos 1 letra MAYÚSCULA
      - Al menos 1 letra minúscula
      - Al menos 1 dígito (0-9)
      - Al menos 1 carácter especial
      - No debe ser una contraseña conocida/común

    Retorna (ok: bool, lista_de_errores: list[str]).
    """
    errores = []
    if len(password) < 10:
        errores.append('Mínimo 10 caracteres (actualmente: {}).'.format(len(password)))
    if not re.search(r'[A-Z]', password):
        errores.append('Debe incluir al menos una letra MAYÚSCULA (A-Z).')
    if not re.search(r'[a-z]', password):
        errores.append('Debe incluir al menos una letra minúscula (a-z).')
    if not re.search(r'\d', password):
        errores.append('Debe incluir al menos un número (0-9).')
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]', password):
        errores.append('Debe incluir al menos un carácter especial (ej: !@#$%&*-_=+).')
    if password.lower() in _CONTRASENAS_COMUNES or password in _CONTRASENAS_COMUNES:
        errores.append('Contraseña demasiado común o predecible. Elige una más segura.')
    return len(errores) == 0, errores


def describir_politica_contrasena() -> str:
    """Retorna un texto con los requisitos de contraseña para mostrar al usuario."""
    return (
        'Requisitos de contraseña:\n'
        '  • Mínimo 10 caracteres\n'
        '  • Al menos 1 letra MAYÚSCULA\n'
        '  • Al menos 1 letra minúscula\n'
        '  • Al menos 1 número (0-9)\n'
        '  • Al menos 1 carácter especial (!@#$%&*-_=+...)\n'
        '  • No usar contraseñas comunes o predecibles'
    )


# ═══════════════════════════════════════════════════════════════════════════
#  VALIDACIÓN DE NOMBRE
# ═══════════════════════════════════════════════════════════════════════════

def validar_nombre(nombre: str) -> tuple:
    """
    Valida que el nombre sea real: letras, espacios, tildes, ñ, guiones.
    Requiere al menos nombre y apellido (2 palabras).
    Retorna (ok: bool, mensaje: str).
    """
    if not nombre or len(nombre.strip()) < 3:
        return False, 'El nombre es demasiado corto.'
    if len(nombre) > 255:
        return False, 'El nombre es demasiado largo (máximo 255 caracteres).'
    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚàèìòùÀÈÌÒÙäëïöüÄËÏÖÜñÑ\s\-]+$', nombre):
        return False, (
            'El nombre solo puede contener letras (incluyendo tildes y ñ), '
            'espacios y guiones. No se permiten números ni símbolos.'
        )
    palabras = [p for p in nombre.strip().split() if p]
    if len(palabras) < 2:
        return False, 'Por favor ingresa el nombre completo (nombre y apellido, mínimo 2 palabras).'
    return True, ''
