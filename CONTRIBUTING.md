# 🤝 Guía de Contribución

¡Gracias por tu interés en contribuir al Sistema de Control de Ingresos SENA! Este documento te guiará a través del proceso.

---

## 📋 Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Cómo Reportar Bugs](#cómo-reportar-bugs)
- [Cómo Sugerir Mejoras](#cómo-sugerir-mejoras)
- [Guía de Desarrollo](#guía-de-desarrollo)
- [Process de Pull Request](#process-de-pull-request)
- [Guía de Estilo](#guía-de-estilo)

---

## 📜 Código de Conducta

### Nuestro Compromiso

Nos comprometemos a proporcionar un ambiente acogedor y libre de acoso para todos, independientemente de edad, tamaño corporal, discapacidad, etnia, identidad de género, nivel de experiencia, nacionalidad, apariencia personal, raza, religión, identidad o orientación sexual.

### Nuestros Estándares

Los comportamientos que contribuyen a crear un ambiente positivo incluyen:

- Usar lenguaje acogedor e inclusivo
- Ser respetuoso con diferentes opiniones
- Aceptar críticas constructivas
- Enfocarse en lo que es mejor para la comunidad
- Mostrar empatía hacia otros miembros de la comunidad

---

## 🐛 Cómo Reportar Bugs

### Antes de Reportar

- Verifica si el bug ya ha sido reportado
- Intenta reproducir con la versión más reciente
- Recopila información sobre tu entorno

### Cómo Reportar

1. Usa el título descriptivo para la issue
2. Describe los pasos exactos para reproducir
3. Incluye ejemplos específicos (código, logs)
4. Describe el comportamiento observado
5. Explica qué comportamiento esperabas
6. Incluye capturas si es relevante

### Ejemplo de Issue

```
Título: Login falla con email en mayúsculas

Descripción:
Cuando intento hacer login con "Usuario@SENA.EDU.CO",
el sistema rechaza la contraseña correcta.

Pasos para reproducir:
1. Ir a /login
2. Ingresar "Usuario@SENA.EDU.CO"
3. Ingresar contraseña correcta
4. Click en "Ingresar"

Resultado esperado:
Debería aceptar el login normalmente.

Logs:
[ERROR] Usuario no encontrado: Usuario@SENA.EDU.CO
```

---

## 💡 Cómo Sugerir Mejoras

### Contexto

- Explica el caso de uso
- Describe el comportamiento actual
- Describe el comportamiento esperado
- Proporciona ejemplos si es posible

### Formato

```
Título: Agregación de notificaciones por email

Descripción:
Cuando ocurren eventos críticos (puerta abierta por más
de 5 minutos), sería útil recibir una notificación por email.

Beneficio:
- Alertas en tiempo real
- No requiere estar en el dashboard
- Mejor monitoreo de seguridad

Posible implementación:
1. Crear tabla EmailNotificaciones
2. Agregar endpoint POST /api/notificaciones/email
3. Usar servicio SendGrid o similar
```

---

## 👨‍💻 Guía de Desarrollo

### Configuración del Entorno

```bash
# 1. Fork el repositorio
git clone https://github.com/tu-usuario/sistema-ingresos-sena.git
cd sistema-ingresos-sena

# 2. Agregar upstream
git remote add upstream https://github.com/usuario-original/sistema-ingresos-sena.git

# 3. Crear rama
git checkout -b feature/tu-feature

# 4. Instalar dependencias
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 5. Ejecutar tests
python -m pytest tests/
```

### Estructura de Ramas

```
main                    # Producción
├── develop             # Desarrollo
    ├── feature/...     # Nuevas características
    ├── fix/...         # Corrección de bugs
    ├── docs/...        # Documentación
    └── refactor/...    # Refactorización
```

### Nombres de Ramas

- `feature/agregar-notificaciones-email` ✅
- `fix/login-case-insensitive` ✅
- `docs/actualizar-readme` ✅
- `refactor/seguridad-schemas` ✅

- `nuevaFeature` ❌
- `arreglo-rapido` ❌
- `cambios` ❌

---

## 📮 Process de Pull Request

### Antes de Enviar

1. **Tests** - Asegúrate de que pasen todos
2. **Linting** - Ejecuta verificaciones de código
3. **Docs** - Actualiza documentación si aplica
4. **Commits** - Usa mensajes claros

### Enviar Pull Request

1. Empuja a tu fork
2. Abre PR contra `develop` (no `main`)
3. Llena el template completo
4. Referencia issues relacionadas

### Template de PR

```markdown
## Descripción
Breve descripción de los cambios.

## Tipo de Cambio
- [ ] Bug fix
- [ ] Nueva característica
- [ ] Breaking change
- [ ] Cambio de documentación

## Pruebas
Cómo se probaron los cambios:
- [ ] Test A
- [ ] Test B

## Checklist
- [ ] Mi código sigue el estilo del proyecto
- [ ] He ejecutado tests locales
- [ ] He actualizado la documentación
- [ ] No hay cambios innecesarios

## Screenshots (si aplica)
Incluye capturas relevantes.

## Relacionado con Issues
Cierra #123
```

---

## 📝 Guía de Estilo

### Python (Backend)

**PEP 8 Compliance:**

```python
# ✅ Bien
def crear_usuario(email: str, password: str) -> Usuario:
    """
    Crea un nuevo usuario en la base de datos.
    
    Args:
        email: Email del usuario
        password: Contraseña sin encriptar
        
    Returns:
        Usuario creado
    """
    usuario = Usuario(email=email)
    usuario.set_password(password)
    db.session.add(usuario)
    db.session.commit()
    return usuario

# ❌ Mal
def crearUsuario(mail,pass):
    u=Usuario(email=mail)
    u.setPassword(pass)
    db.session.add(u)
    db.session.commit()
    return u
```

**Naming Conventions:**

```python
# Variables y funciones: snake_case
usuario_activo = True
def obtener_usuarios()

# Clases: PascalCase
class UsuarioRegistro

# Constantes: UPPER_SNAKE_CASE
MAX_INTENTOS_LOGIN = 5
TIMEOUT_SESION = 3600

# Privados: _leading_underscore
def _validar_email_interno()
```

### JavaScript (Frontend)

**Convenciones:**

```javascript
// ✅ Bien - camelCase
const usuarioActivo = true;
function obtenerDatos() { }
const $btnSubmit = document.querySelector('.btn-submit');

// ✅ Bien - descriptivo
const API_ENDPOINT = 'http://localhost:8000';
const TIMEOUT_MS = 5000;

// ❌ Mal
const usrActv = true;
const fn = () => { };
const x = 5;
```

### Commits

**Formato:**

```
<tipo>(<ámbito>): <asunto>

<cuerpo>

<footer>
```

**Tipos válidos:**
- `feat:` Nueva característica
- `fix:` Corrección de bug
- `docs:` Cambios en documentación
- `style:` Cambios de formato (no funcionalidad)
- `refactor:` Refactorización sin cambios funcionales
- `test:` Adición o cambios en tests
- `chore:` Cambios en build, dependencias, etc.

**Ejemplos:**

```
feat(auth): agregar autenticación 2FA

Implementa verificación en dos pasos usando
códigos TOTP. Los usuarios pueden habilitar
desde el panel de configuración.

Cierra #234

---

fix(login): corregir validación case-sensitive

El email ahora se convierte a minúsculas
antes de verificar en la base de datos.

Cierra #123

---

docs(readme): actualizar instrucciones instalación

Agrega ejemplos de Docker y nuevos requisitos.
```

### HTML/CSS

**Convenciones:**

```html
<!-- ✅ Bien - clases descriptivas -->
<button class="btn btn-primary">Enviar</button>
<div class="modal-overlay">

<!-- ❌ Mal - nombres genéricos -->
<button class="btn1">Enviar</button>
<div class="overlay">
```

---

## 🧪 Testing

### Cobertura Mínima

- 80% de coverage total
- 100% de código crítico (seguridad, auth)
- Todos los endpoints testados

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Con coverage
pytest --cov=backend tests/

# Tests específicos
pytest tests/test_auth.py -v
```

### Ejemplo de Test

```python
def test_login_exitoso():
    """Test login con credenciales válidas"""
    # Arrange
    usuario = crear_usuario_test('admin@sena.edu.co', 'password123')
    
    # Act
    response = client.post('/api/login', json={
        'email': 'admin@sena.edu.co',
        'password': 'password123'
    })
    
    # Assert
    assert response.status_code == 200
    assert 'token' in response.json()
```

---

## 📖 Documentación

### Docstrings

```python
def crear_registro(usuario_id: int, tipo: str) -> Registro:
    """
    Crea un nuevo registro de entrada/salida.
    
    Args:
        usuario_id: ID del usuario
        tipo: 'entrada' o 'salida'
        
    Returns:
        Registro creado
        
    Raises:
        ValueError: Si el tipo no es válido
        NotFoundError: Si el usuario no existe
        
    Example:
        >>> crear_registro(1, 'entrada')
        <Registro id=42>
    """
```

### README de Funcionalidades

Actualizar docs cuando agregues:
- Nuevas rutas API
- Nuevos campos en BD
- Nuevas características
- Breaking changes

---

## 🎯 Checklist Final

Antes de enviar tu PR:

- [ ] Tests pasan localmente
- [ ] No hay warnings
- [ ] Código sigue guía de estilo
- [ ] Documentación actualizada
- [ ] Commits limpios y descriptivos
- [ ] PR contra `develop`
- [ ] Template de PR completo
- [ ] Sin archivos irrelevantes

---

¡Gracias por contribuir! 🎉

**Última actualización:** Enero 2025
