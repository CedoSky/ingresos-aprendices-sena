#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar documento Word con diagrama de flujo del proyecto
"""

import sys
import os

# Verificar si python-docx está instalado
try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:
    print("Instalando python-docx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx", "--quiet"])
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

def add_heading_styled(doc, text, level=1, color=None):
    """Agregar encabezado con estilo"""
    heading = doc.add_heading(text, level=level)
    if color:
        for run in heading.runs:
            run.font.color.rgb = RGBColor(*color)
    return heading

def add_table_report(doc, headers, data):
    """Agregar tabla con datos"""
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    
    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        hdr_cells[i].text = header
        hdr_cells[i].paragraphs[0].runs[0].font.bold = True
        hdr_cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(102, 126, 234)
    
    for row_data in data:
        row_cells = table.add_row().cells
        for i, cell_text in enumerate(row_data):
            row_cells[i].text = str(cell_text)
    
    return table

def add_shaded_box(doc, title, content, color_rgb=(230, 244, 248)):
    """Agregar recuadro sombreado"""
    p = doc.add_paragraph()
    p_format = p.paragraph_format
    p_format.left_indent = Inches(0.25)
    p_format.space_before = Pt(10)
    p_format.space_after = Pt(10)
    
    # Título en negrita
    run = p.add_run(f"🔹 {title}\n")
    run.font.bold = True
    run.font.color.rgb = RGBColor(102, 126, 234)
    
    # Contenido
    run = p.add_run(content)
    run.font.size = Pt(10)
    
    # Sombreado
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), 'E8F4F8')
    p._element.get_or_add_pPr().append(shading_elm)
    
    return p

# Crear documento
doc = Document()

# ═════════════════════════════════════════════════════════════════════
# PORTADA
# ═════════════════════════════════════════════════════════════════════

title = doc.add_heading('SISTEMA DE CONTROL DE INGRESOS SENA', 0)
title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
for run in title.runs:
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = RGBColor(102, 126, 234)

subtitle = doc.add_heading('Diagrama de Flujo y Arquitectura del Sistema', level=2)
subtitle.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

# Metadatos
doc.add_paragraph()
meta_table = add_table_report(doc, 
    ['Propiedad', 'Valor'],
    [
        ['Versión', '6-WithSecurity'],
        ['Estado', '✅ Operacional y Endurecido'],
        ['Fecha', '8 de Abril de 2026'],
        ['Seguridad', 'OWASP / JWT / Encriptación Fernet'],
        ['Tecnología', 'Flask 3.1.3 | SQLAlchemy 2.0.48 | ESP32 TRIAC']
    ]
)

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# TABLA DE CONTENIDOS
# ═════════════════════════════════════════════════════════════════════

add_heading_styled(doc, '📋 Tabla de Contenidos', 1, (102, 126, 234))
toc_items = [
    '1. Descripción General',
    '2. Tecnologías Utilizadas',
    '3. Módulos Principales',
    '4. Medidas de Seguridad',
    '5. Estructura de Base de Datos',
    '6. Flujos de Procesos Clave',
    '7. Endpoints API Principal',
    '8. Integración IoT (ESP32)',
    '9. Despliegue e Instalación',
    '10. Estructura de Carpetas',
]

for item in toc_items:
    doc.add_paragraph(item, style='List Bullet')

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# SECCIÓN 1: DESCRIPCIÓN GENERAL
# ═════════════════════════════════════════════════════════════════════

add_heading_styled(doc, '1. 📊 Descripción General', 1, (102, 126, 234))

doc.add_paragraph(
    'El Sistema de Control de Ingresos SENA es una solución integral para gestionar acceso '
    'a la institución educativa SENA. Integra control de acceso físico mediante cerradura '
    'electromagnética, gestión completa de personas, administración de usuarios, procesamiento '
    'de pagos y generación de reportes avanzados.'
)

add_heading_styled(doc, 'Características Principales', 2)

features = [
    ('👤 Gestión de Personas', 'Registro y búsqueda de aprendices, instructores y visitantes'),
    ('🚪 Control de Acceso', 'Control de cerradura electromagnética con ESP32 TRIAC y MQTT'),
    ('🔐 Seguridad Avanzada', 'JWT, Encriptación Fernet, Auditoría, Prevención fuerza bruta'),
    ('💰 Sistema de Pagos', 'Procesamiento de pagos y gestión de créditos'),
    ('📈 Reportes', 'Exportación a Excel de registros y estadísticas'),
    ('🔄 Sincronización', 'Sincronización en tiempo real con WebSocket'),
]

for title, desc in features:
    p = doc.add_paragraph()
    run = p.add_run(title)
    run.font.bold = True
    p.add_run(f': {desc}')

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# SECCIÓN 2: TECNOLOGÍAS
# ═════════════════════════════════════════════════════════════════════

add_heading_styled(doc, '2. 🏗️ Tecnologías Utilizadas', 1, (102, 126, 234))

tech_data = [
    ['Capa', 'Tecnología', 'Versión'],
    ['Backend', 'Flask', '3.1.3'],
    ['ORM', 'SQLAlchemy', '2.0.48'],
    ['Frontend', 'HTML5 / JavaScript', 'Moderno'],
    ['Base Datos', 'SQLite (dev) / PostgreSQL (prod)', 'Compatible'],
    ['Autenticación', 'JWT / Fernet', 'Avanzada'],
    ['Messaging', 'MQTT / WebSocket', 'Real-time'],
    ['IoT', 'ESP32 TRIAC', 'Control Acceso'],
    ['Containerización', 'Docker / Docker Compose', 'Moderno'],
    ['Email', 'SMTP / SendGrid', 'Notificaciones'],
]

add_table_report(doc, tech_data[0], tech_data[1:])

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# SECCIÓN 3: MÓDULOS PRINCIPALES
# ═════════════════════════════════════════════════════════════════════

add_heading_styled(doc, '3. 📦 Módulos Principales', 1, (102, 126, 234))

modules_data = [
    ['Módulo', 'Archivo Principal', 'Función'],
    ['Autenticación', 'routes.py, security_shield.py', 'Login seguro, JWT, prevención fuerza bruta'],
    ['Gestión Personas', 'routes.py, validaciones.py', 'CRUD de personas'],
    ['Control Acceso', 'routes.py, mqtt_handler.py', 'Registro acceso, control TRIAC'],
    ['Administración', 'panel_routes.py, gestionar_usuarios.py', 'Gestión usuarios y seguridad'],
    ['Pagos', 'pagos.py', 'Procesamiento pagos, créditos'],
    ['Reportes', 'export_excel.py', 'Generación Excel'],
    ['Sincronización', 'sync_manager.py, websocket_handler.py', 'Sincronización real-time'],
    ['Base Datos', 'models.py', 'Modelos SQLAlchemy'],
]

add_table_report(doc, modules_data[0], modules_data[1:])

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# SECCIÓN 4: SEGURIDAD
# ═════════════════════════════════════════════════════════════════════

add_heading_styled(doc, '4. 🔐 Medidas de Seguridad Implementadas', 1, (102, 126, 234))

security_sections = [
    ('Autenticación y Autorización', [
        'JWT (JSON Web Tokens) para autenticación sin estado',
        'Sesiones seguras con cookies HTTP-only',
        'Control de acceso basado en roles (Admin, Vigilante)',
        'Validación JWT en cada endpoint protegido',
    ]),
    ('Protección contra Ataques', [
        'Fuerza Bruta: Bloqueo de 15 minutos tras 5 intentos fallidos',
        'CSRF: Tokens CSRF y validación SameSite=Strict',
        'SQL Injection: SQLAlchemy ORM con queries parametrizadas',
        'XSS: Validación de entrada y sanitización',
        'Rate Limiting: Limitación de tasa de solicitudes',
    ]),
    ('Encriptación y Datos Sensibles', [
        'Fernet encryption para datos sensibles en reposo',
        'Hashing bcrypt para contraseñas',
        'HTTPS/TLS para datos en tránsito (en producción)',
        'Almacenamiento seguro de credenciales en .env',
    ]),
    ('Auditoría y Monitoreo', [
        'Sistema de auditoría administrativo completo',
        'Registro de eventos de seguridad y acceso',
        'Validación de configuración de seguridad',
        'Headers HTTP de seguridad OWASP recomendados',
    ]),
]

for title, items in security_sections:
    add_heading_styled(doc, title, 2)
    for item in items:
        doc.add_paragraph(item, style='List Bullet')

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# SECCIÓN 5: BASE DE DATOS
# ═════════════════════════════════════════════════════════════════════

add_heading_styled(doc, '5. 🗄️ Estructura de Base de Datos', 1, (102, 126, 234))

db_data = [
    ['Entidad', 'Descripción', 'Campos Clave'],
    ['Usuario', 'Administradores y vigilantes', 'email, password_hash, rol, activo'],
    ['Persona', 'Aprendices, instructores, visitantes', 'nombre, tipo_doc, numero_doc, perfil'],
    ['RegistroAcceso', 'Log de entradas/salidas', 'persona_id, entry_time, exit_time'],
    ['Foto', 'Fotografías de personas', 'persona_id, ruta_archivo, tipo'],
    ['Pago', 'Transacciones de pago', 'usuario_id, monto, estado, fecha'],
    ['AuditoriaEvento', 'Eventos administrativos', 'usuario_id, tipo_evento, detalles'],
]

add_table_report(doc, db_data[0], db_data[1:])

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# SECCIÓN 6: FLUJOS DE PROCESOS
# ═════════════════════════════════════════════════════════════════════

add_heading_styled(doc, '6. 📝 Flujos de Procesos Clave', 1, (102, 126, 234))

flows = [
    ('Flujo de Autenticación',
     'Usuario → Validación Entrada → Verificación Password → Generación JWT → '
     'Creación Sesión → Log Auditoría → Dashboard'),
    
    ('Flujo de Control de Acceso',
     'Solicitud Acceso → Validación Horaria → Verificación Blacklist → Publicar MQTT → '
     'ESP32 Activa TRIAC → Cerradura Abre → Registro en BD → Notificación WebSocket'),
    
    ('Flujo de Registro de Personas',
     'Formulario → Validación Datos → Encriptación Sensibles → Guardado BD → '
     'Notificación WebSocket → Log Auditoría'),
    
    ('Flujo de Administración',
     'Panel Admin → Validación PIN → Acción (Usuarios/Seguridad/Backup) → '
     'Ejecución → Log Auditoría → Sincronización BD'),
]

for title, description in flows:
    add_heading_styled(doc, title, 2)
    add_shaded_box(doc, title, description)

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# SECCIÓN 7: API ENDPOINTS
# ═════════════════════════════════════════════════════════════════════

add_heading_styled(doc, '7. 🔌 Principales Endpoints API', 1, (102, 126, 234))

api_data = [
    ['Método', 'Endpoint', 'Descripción'],
    ['POST', '/api/login', 'Autenticación de usuario'],
    ['GET', '/api/personas', 'Obtener lista de personas'],
    ['POST', '/api/personas', 'Crear nueva persona'],
    ['POST', '/api/registros', 'Registrar acceso (entrada/salida)'],
    ['GET', '/api/registros', 'Obtener registros de acceso'],
    ['POST', '/api/pagos', 'Procesar pago'],
    ['GET', '/api/reportes', 'Obtener reportes (Excel)'],
    ['POST', '/panel/usuarios', 'Gestionar usuarios (admin)'],
]

add_table_report(doc, api_data[0], api_data[1:])

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# SECCIÓN 8: IOT INTEGRATION
# ═════════════════════════════════════════════════════════════════════

add_heading_styled(doc, '8. ⚡ Integración IoT (ESP32)', 1, (102, 126, 234))

add_heading_styled(doc, 'Comunicación MQTT', 2)
mqtt_items = [
    'Broker: mosquitto (puerto 1883)',
    'Topic: control/acceso',
    'QoS: 1 (at least once)',
    'Payload: JSON con comando',
]
for item in mqtt_items:
    doc.add_paragraph(item, style='List Bullet')

add_heading_styled(doc, 'Control TRIAC', 2)
triac_items = [
    'Solenoide electromagnético de cerradura',
    'Tiempo de apertura: 3-5 segundos',
    'Fallback manual si ESP32 está offline',
    'Registro de cada apertura de puerta',
]
for item in triac_items:
    doc.add_paragraph(item, style='List Bullet')

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# SECCIÓN 9: DESPLIEGUE
# ═════════════════════════════════════════════════════════════════════

add_heading_styled(doc, '9. 🚀 Despliegue e Instalación', 1, (102, 126, 234))

add_heading_styled(doc, 'Opción 1: Docker (Recomendado)', 2)
doc.add_paragraph('Ejecuta DOCKER_SETUP.bat para desplegar con Docker Compose')
doc.add_paragraph('Frontend: http://localhost', style='List Bullet')
doc.add_paragraph('Backend: http://localhost:8000', style='List Bullet')

add_heading_styled(doc, 'Opción 2: Local (Windows)', 2)
doc.add_paragraph('Ejecuta INSTALAR.bat e INICIAR.bat')
doc.add_paragraph('Requiere Python 3.11+ instalado', style='List Bullet')
doc.add_paragraph('Requiere Node.js para frontend (opcional)', style='List Bullet')

add_heading_styled(doc, 'Credenciales de Prueba', 2)
doc.add_paragraph('Email: admin@sena.edu.co', style='List Bullet')
doc.add_paragraph('Contraseña: admin123', style='List Bullet')

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# SECCIÓN 10: ESTRUCTURA CARPETAS
# ═════════════════════════════════════════════════════════════════════

add_heading_styled(doc, '10. 📂 Estructura de Carpetas del Proyecto', 1, (102, 126, 234))

structure = '''
ingresos-aprendices-7/
├── backend/
│   ├── app.py                  # Aplicación Flask principal
│   ├── routes.py               # Rutas API
│   ├── models.py               # Modelos SQLAlchemy
│   ├── security_shield.py      # Seguridad básica
│   ├── security_advanced.py    # Seguridad avanzada
│   ├── mqtt_handler.py         # Comunicación MQTT
│   ├── websocket_handler.py    # WebSocket real-time
│   ├── panel_routes.py         # Rutas administración
│   ├── pagos.py                # Sistema pagos
│   └── export_excel.py         # Generación reportes
├── frontend/
│   ├── login.html              # Página login
│   ├── administracion.html     # Panel admin
│   └── ...otros archivos HTML
├── Arduino/
│   ├── esp32_triac_mqtt.ino    # Código ESP32
│   └── esp32_triac_control/
├── docs/
│   ├── SEGURIDAD.md
│   └── DEPLOYMENT_GUIDE.md
├── scripts/
│   ├── INICIAR.bat             # Script inicio
│   └── MANTENIMIENTO.bat
├── logs/                       # Archivos de log
├── instance/                   # Base de datos SQLite
└── docker-compose.yml          # Orquestación Docker
'''

doc.add_paragraph(structure, style='Normal')

doc.add_page_break()

# ═════════════════════════════════════════════════════════════════════
# PIE DE PÁGINA Y CIERRE
# ═════════════════════════════════════════════════════════════════════

doc.add_heading('Conclusión', 1)
doc.add_paragraph(
    'El Sistema de Control de Ingresos SENA es una solución completa y endurecida '
    'que integra tecnologías modernas con medidas de seguridad OWASP. El sistema está '
    'listo para producción y puede escalarse fácilmente gracias a su arquitectura modular '
    'y uso de Docker.'
)

doc.add_paragraph()
footer = doc.add_paragraph('📄 Documento generado: 8 de Abril de 2026')
footer.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
footer_run = footer.runs[0]
footer_run.font.size = Pt(9)
footer_run.font.italic = True

# ═════════════════════════════════════════════════════════════════════
# GUARDAR DOCUMENTO
# ═════════════════════════════════════════════════════════════════════

output_path = os.path.join(
    os.path.dirname(__file__),
    'DIAGRAMA_FLUJO_PROYECTO.docx'
)

doc.save(output_path)
print("[OK] Documento Word creado exitosamente: {}".format(output_path))
