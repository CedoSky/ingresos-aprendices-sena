#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Informe del Sistema de Control de Ingresos SENA
Crea un documento Word explicando la plataforma para usuarios no técnicos
"""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os
from datetime import datetime

def add_heading_styled(doc, text, level):
    """Agrega un encabezado con estilo personalizado"""
    heading = doc.add_heading(text, level=level)
    heading.style = f'Heading {level}'
    
    # Colores para diferentes niveles
    if level == 1:
        for run in heading.runs:
            run.font.color.rgb = RGBColor(26, 82, 0)  # Verde SENA
            run.font.size = Pt(28)
            run.font.bold = True
    elif level == 2:
        for run in heading.runs:
            run.font.color.rgb = RGBColor(57, 169, 0)  # Verde claro
            run.font.size = Pt(16)
    
    return heading

def add_paragraph_justified(doc, text, size=11, color=None):
    """Agrega párrafo justificado"""
    p = doc.add_paragraph(text)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    for run in p.runs:
        run.font.size = Pt(size)
        if color:
            run.font.color.rgb = color
    
    return p

def shade_paragraph(p, color):
    """Agrega sombreado a un párrafo"""
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color)
    p._element.get_or_add_pPr().append(shading_elm)

def create_table_with_borders(doc, rows, cols):
    """Crea tabla con bordes personalizados"""
    table = doc.add_table(rows=rows, cols=cols)
    table.style = 'Light Grid Accent 1'
    return table

def main():
    # Crear documento
    doc = Document()
    
    # ==== PORTADA ====
    title = doc.add_heading('Sistema de Control de Ingresos', level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.color.rgb = RGBColor(26, 82, 0)
        run.font.size = Pt(34)
    
    subtitle = doc.add_paragraph('Centro de Formación SENA')
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in subtitle.runs:
        run.font.size = Pt(20)
        run.font.color.rgb = RGBColor(57, 169, 0)
    
    doc.add_paragraph()
    
    info_text = doc.add_paragraph(
        f'Informe de Funcionamiento y Guía de Uso\n'
        f'Versión: 6.0\n'
        f'Fecha: {datetime.now().strftime("%d de %B de %Y")}'
    )
    info_text.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in info_text.runs:
        run.font.size = Pt(12)
    
    doc.add_page_break()
    
    # ==== ÍNDICE ====
    add_heading_styled(doc, 'Contenido', 1)
    
    toc_items = [
        '1. Introducción',
        '2. ¿Qué es el Sistema?',
        '3. Acceso al Sistema: Login',
        '4. Proceso de Ingreso con Código de Barras',
        '5. Panel de Vigilancia',
        '6. Panel de Administración',
        '7. Seguridad y Protección de Datos',
        '8. Preguntas Frecuentes',
    ]
    
    for item in toc_items:
        p = doc.add_paragraph(item, style='List Bullet')
        p.paragraph_format.left_indent = Inches(0.5)
    
    doc.add_page_break()
    
    # ==== SECCIÓN 1: INTRODUCCIÓN ====
    add_heading_styled(doc, '1. Introducción', 1)
    
    add_paragraph_justified(doc,
        'El Sistema de Control de Ingresos SENA es una plataforma digital diseñada '
        'para gestionar y monitorear el acceso de aprendices, instructores y visitantes '
        'en los centros de formación. Este sistema moderniza el proceso tradicional de '
        'registro manual, proporcionando seguridad, eficiencia y trazabilidad completa '
        'de todos los movimientos dentro de la institución.')
    
    add_paragraph_justified(doc,
        'A través de esta plataforma, se registran automáticamente los ingresos y salidas '
        'de personas, se generan reportes detallados, y se controla el acceso a diferentes '
        'instalaciones. El sistema está disponible en línea y cuenta con múltiples interfaces '
        'especializadas para diferentes usuarios.')
    
    doc.add_page_break()
    
    # ==== SECCIÓN 2: ¿QUÉ ES? ====
    add_heading_styled(doc, '2. ¿Qué es el Sistema?', 1)
    
    add_heading_styled(doc, 'Componentes Principales', 2)
    
    components = [
        ('Portal de Ingreso', 'Interfaz de lector de códigos de barras donde los aprendices registran su entrada y salida.'),
        ('Panel de Vigilancia', 'Pantalla de monitoreo en tiempo real para vigilantes. Muestra quién está dentro, alertas de seguridad, y control de puertas.'),
        ('Panel de Administración', 'Centro de control completo para administradores. Gestiona usuarios, registra personas nuevas, genera reportes, configura el sistema.'),
        ('Base de Datos', 'Almacena de forma segura toda la información de personas, registros de acceso e historial de cambios.'),
    ]
    
    for titulo, descripcion in components:
        p = doc.add_paragraph()
        run = p.add_run(f'• {titulo}: ')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        p.add_run(descripcion)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_page_break()
    
    # ==== SECCIÓN 3: LOGIN ====
    add_heading_styled(doc, '3. Acceso al Sistema: Login', 1)
    
    add_heading_styled(doc, 'Paso 1: Acceder a la Plataforma', 2)
    
    add_paragraph_justified(doc,
        'Para acceder al sistema, abre tu navegador web (Chrome, Firefox, Edge, etc.) '
        'y dirígete a la dirección de acceso del sistema. Se mostrará la pantalla de '
        'entrada (login) con dos campos a completar.')
    
    add_heading_styled(doc, 'Paso 2: Completar Credenciales', 2)
    
    credentials_data = [
        ['Campo', 'Descripción', 'Ejemplo'],
        ['Correo Electrónico', 'Tu email registrado en el sistema', 'admin@sena.edu.co'],
        ['Contraseña', 'Tu contraseña segura (no compartir)', '••••••••'],
    ]
    
    table = create_table_with_borders(doc, len(credentials_data), 3)
    table.autofit = False
    table.allow_autofit = False
    
    for i, row_data in enumerate(credentials_data):
        cells = table.rows[i].cells
        for j, cell_text in enumerate(row_data):
            cell = cells[j]
            cell.text = cell_text
            
            # Formato para encabezado
            if i == 0:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                shade_paragraph(cell.paragraphs[0], '39A900')
            else:
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph()
    
    add_heading_styled(doc, 'Paso 3: Roles y Acceso', 2)
    
    add_paragraph_justified(doc,
        'Dependiendo de tu cuenta, recibirás acceso a diferentes secciones:')
    
    roles = [
        ('🔒 Aprendiz', 'Solo puede usar el portal de ingreso (código de barras)'),
        ('👮 Vigilante', 'Acceso al panel de vigilancia para monitoreo en tiempo real'),
        ('🛡️ Administrador', 'Acceso completo a todo el sistema: usuarios, reportes, configuración'),
    ]
    
    for rol_nombre, descripcion in roles:
        p = doc.add_paragraph(f'{rol_nombre}: {descripcion}')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    add_paragraph_justified(doc,
        'Después de ingresar correctamente, verás el DASHBOARD (menú principal) '
        'con opciones según tu rol.')
    
    doc.add_page_break()
    
    # ==== SECCIÓN 4: INGRESO CON CÓDIGO DE BARRAS ====
    add_heading_styled(doc, '4. Proceso de Ingreso con Código de Barras', 1)
    
    add_paragraph_justified(doc,
        'Los aprendices utilizan el Portal de Ingreso para registrar su entrada y salida '
        'diariamente. Este proceso es simple, rápido y automático. Aquí te explicamos cómo funciona.')
    
    add_heading_styled(doc, '¿Cómo Funciona?', 2)
    
    steps = [
        ('Paso 1: Accede al Portal', 
         'Abre el navegador en la computadora destinada para ingresos. Verás una pantalla '
         'con el logo de SENA y un cuadro de entrada.'),
        
        ('Paso 2: Escanea tu Documento', 
         'Usa el lector de código de barras para escanear tu cédula o carnet. El número '
         'debe aparecer automáticamente en el campo de entrada. No necesitas escribir nada.'),
        
        ('Paso 3: Confirmación Automática', 
         'El sistema busca instantáneamente tu nombre en la base de datos. Si lo encuentra, '
         'muestra un mensaje de INGRESO EXITOSO o SALIDA EXITOSA (dependiendo si es la primera '
         'vez del día o si ya habías ingresado).'),
        
        ('Paso 4: ¡Listo!', 
         'Tu entrada/salida queda registrada automáticamente. El sistema guarda la hora exacta '
         'y quedará en el historial.'),
    ]
    
    for paso, descripcion in steps:
        p = doc.add_paragraph()
        run = p.add_run(paso + '\n')
        run.bold = True
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(57, 169, 0)
        p.add_run(descripcion)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    add_heading_styled(doc, 'Posibles Mensajes', 2)
    
    messages_data = [
        ['Mensaje', 'Significado', 'Acción'],
        ['✅ Ingreso Exitoso', 'Tu entrada fue registrada correctamente', 'Puedes proceder normalmente'],
        ['✅ Salida Exitosa', 'Tu salida fue registrada', 'Registro completo del día'],
        ['⚠️ No Encontrado', 'Tu documento no está en el sistema', 'Contacta a vigilancia para verificación'],
        ['⚠️ Acceso Denegado', 'Hay una restricción en tu cuenta', 'Reporta a administración'],
    ]
    
    table = create_table_with_borders(doc, len(messages_data), 3)
    
    for i, row_data in enumerate(messages_data):
        cells = table.rows[i].cells
        for j, cell_text in enumerate(row_data):
            cell = cells[j]
            cell.text = cell_text
            
            if i == 0:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                shade_paragraph(cell.paragraphs[0], '39A900')
            else:
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_page_break()
    
    # ==== SECCIÓN 5: PANEL DE VIGILANCIA ====
    add_heading_styled(doc, '5. Panel de Vigilancia', 1)
    
    add_paragraph_justified(doc,
        'El Panel de Vigilancia es la pantalla de control para los vigilantes y personal '
        'de seguridad. Desde aquí se monitorea en tiempo real quién está adentro de '
        'la institución, se controlan accesos y se detectan posibles anomalías de seguridad.')
    
    add_heading_styled(doc, 'Acceso al Panel', 2)
    
    add_paragraph_justified(doc,
        'Los vigilantes acceden con su usuario y contraseña. Al iniciar sesión como vigilante, '
        'verán automáticamente el Panel de Vigilancia con todas las herramientas disponibles.')
    
    add_heading_styled(doc, 'Características Principales', 2)
    
    features = [
        ('Monitor en Tiempo Real', 'Muestra un listado de todas las personas que ingresaron hoy. Se actualiza automáticamente cada vez que alguien escanea su código.'),
        ('Hora Actualizada', 'Reloj digital grande que muestra la hora exacta del sistema. Importante para sincronización con registros.'),
        ('Estadísticas', 'Números rápidos de:  - Personas ingresadas hoy\n  - Personas actualmente adentro\n  - Accesos por piso/zona\n  - Alertas pendientes'),
        ('Filtros de Búsqueda', 'Opción para filtrar registros por:\n  - Entrada / Salida\n  - Fecha específica\n  - Persona (por nombre o documento)'),
        ('Zonas/Pisos', 'Distribuidor visual de cuántas personas hay en cada piso o zona de la institución. Ayuda a detectar concentraciones anormales.'),
        ('Información de Persona', 'Al hacer clic en un registro, puedes ver:\n  - Nombre completo\n  - Documento\n  - Programa/Especialidad\n  - Fotografía\n  - Historial de accesos'),
        ('Control de Puertas', 'Si el sistema cuenta con cerradura electrónica (ESP32 TRIAC), muestra:\n  - Estado de la puerta (abierta/cerrada)\n  - Opción para abrir remotamente\n  - Historial de aperturas'),
        ('Alertas Automáticas', 'Sistema de alertas visuales para:\n  - Intentos de acceso denegado\n  - Personas no autorizadas\n  - Horarios fuera de lo normal\n  - Puertas abiertas anormalmente'),
    ]
    
    for feature_name, description in features:
        p = doc.add_paragraph()
        run = p.add_run(f'🔹 {feature_name}\n')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        p.add_run(description)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_page_break()
    
    # ==== SECCIÓN 6: PANEL DE ADMINISTRACIÓN ====
    add_heading_styled(doc, '6. Panel de Administración', 1)
    
    add_paragraph_justified(doc,
        'El Panel de Administración es el centro de control completo del sistema. '
        'Solo los administradores pueden acceder a esta sección. Aquí se gestionan usuarios, '
        'registros, configuración y se generan reportes.')
    
    add_heading_styled(doc, 'Acceso al Panel', 2)
    
    add_paragraph_justified(doc,
        'Necesitas una cuenta de administrador. Al iniciar sesión con tu credencial, '
        'verás el Dashboard principal con un menú de opciones. Selecciona "Administración" '
        'o "Admin Panel" para entrar.')
    
    add_heading_styled(doc, 'Áreas Principales', 2)
    
    areas = [
        ('1. Gestión de Usuarios',
         'Crear, editar, eliminar y administrar cuentas de:\n'
         '  • Vigilantes\n'
         '  • Otros administradores\n'
         'Asignar roles y permisos, cambiar contraseñas, activar/desactivar cuentas.'),
        
        ('2. Registro de Personas',
         'Agregar nuevas personas al sistema:\n'
         '  • Aprendices (estudiantes)\n'
         '  • Instructores (personal docente)\n'
         '  • Visitantes (personas autorizadas de afuera)\n'
         'Capturar datos: nombre, documento, email, teléfono, programa, foto.'),
        
        ('3. Búsqueda de Registros',
         'Encontrar a cualquier persona en el sistema por:\n'
         '  • Nombre\n'
         '  • Documento\n'
         '  • Email\n'
         'Ver historial completo de accesos.'),
        
        ('4. Control de Accesos',
         'Monitor general de todos los ingresos y salidas.\n'
         'Opciones:\n'
         '  • Ver listado actualizado\n'
         '  • Filtrar por fecha/tipo\n'
         '  • Editar/eliminar registros incorrectos\n'
         '  • Bloquear/desbloquear acceso a personas.'),
        
        ('5. Gestión de Pagos',
         'Administración de servicios pagados:\n'
         '  • Pago de cafetería\n'
         '  • Fotocopia\n'
         '  • Otros servicios\n'
         'Ver transacciones y generar reportes de ingresos.'),
        
        ('6. Reportes y Exportación',
         'Generar reportes en Excel:\n'
         '  • Asistencia diaria\n'
         '  • Resumen mensual\n'
         '  • Personas registradas\n'
         '  • Accesos por usuario\n'
         'Descargar en formato Excel para análisis.'),
        
        ('7. Configuración del Sistema',
         'Ajustar parámetros generales:\n'
         '  • IP del ESP32 (cerradura electrónica)\n'
         '  • Horarios de apertura\n'
         '  • Zonas/pisos del edificio\n'
         '  • Mensajes personalizados.'),
        
        ('8. Auditoría y Historial',
         'Ver historial completo de:\n'
         '  • Cambios realizados por usuarios\n'
         '  • Quién modificó qué y cuándo\n'
         '  • Intentos de acceso\n'
         'Para propósitos de seguridad e investigación.'),
    ]
    
    for area_title, description in areas:
        p = doc.add_paragraph()
        run = p.add_run(area_title + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 82, 0)
        run.font.size = Pt(12)
        p.add_run(description)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_page_break()
    
    # ==== SECCIÓN 7: SEGURIDAD ====
    add_heading_styled(doc, '7. Seguridad y Protección de Datos', 1)
    
    add_paragraph_justified(doc,
        'El sistema implementa múltiples capas de seguridad para proteger la información '
        'de la institución y garantizar la integridad de todos los registros.')
    
    add_heading_styled(doc, 'Medidas de Seguridad Implementadas', 2)
    
    security_measures = [
        ('Autenticación con Token JWT', 
         'Cada usuario obtiene un token único después de iniciar sesión. Este token es '
         'necesario para acceder a funciones protegidas, evitando accesos no autorizados.'),
        
        ('Encriptación de Datos', 
         'La información sensible (contraseñas, datos personales) se almacena encriptada '
         'en la base de datos. Incluso si alguien accede a los archivos, no podrá leer la información.'),
        
        ('Validación CSRF', 
         'Protección contra ataques que intentan realizar acciones maliciosas en nombre de '
         'un usuario. Cada acción importante requiere confirmación adicional.'),
        
        ('Control de Permisos', 
         'No todos los usuarios pueden hacer todo. Cada rol tiene permisos específicos:\n'
         '  - Aprendices: Solo ingreso\n'
         '  - Vigilantes: Monitoreo\n'
         '  - Administradores: Control total'),
        
        ('Registro de Auditoría', 
         'Todos los cambios importantes quedan registrados: quién hizo qué, cuándo, y desde dónde. '
         'Esto permite investigar cualquier actividad sospechosa.'),
        
        ('Cierre de Sesión', 
         'Las sesiones expiran automáticamente después de cierto tiempo de inactividad. '
         'También puedes cerrar sesión manualmente para mayor seguridad.'),
        
        ('Respaldo de Datos', 
         'La información se respalda regularmente en ubicaciones seguras. Si ocurre un problema, '
         'los datos pueden recuperarse sin pérdida.'),
    ]
    
    for measure, description in security_measures:
        p = doc.add_paragraph()
        run = p.add_run(f'🔐 {measure}\n')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        p.add_run(description)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    add_heading_styled(doc, 'Buenas Prácticas de Seguridad', 2)
    
    practices = [
        'Nunca compartas tu contraseña con otros usuarios, incluso si son colegas.',
        'Cierra sesión antes de dejar tu computadora, especialmente si es compartida.',
        'Cambia tu contraseña periódicamente (cada 3-6 meses).',
        'Usa contraseñas fuertes: combinación de letras, números y símbolos.',
        'No escribas tu contraseña en papeles o notas visibles.',
        'Reporta inmediatamente si notas actividad sospechosa en el sistema.',
        'Mantén actualizado tu navegador para evitar vulnerabilidades.',
    ]
    
    for practice in practices:
        p = doc.add_paragraph(f'✓ {practice}', style='List Bullet')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_page_break()
    
    # ==== SECCIÓN 8: FAQ ====
    add_heading_styled(doc, '8. Preguntas Frecuentes', 1)
    
    faqs = [
        ('¿Qué debo hacer si olvido mi contraseña?',
         'Contacta al administrador del sistema. Él puede restablecer tu contraseña o '
         'enviarte un enlace de recuperación a tu correo electrónico.'),
        
        ('¿Qué pasa si no puedo escanear mi documento?',
         'Intenta limpiar el código de barras de tu cédula. Si sigue sin funcionar, '
         'comunícate con vigilancia. Pueden registrar tu ingreso manualmente.'),
        
        ('¿Se puede modificar un registro de acceso una vez registrado?',
         'Sí, pero solo los administradores pueden hacerlo. Esto queda registrado en '
         'el historial de auditoría.'),
        
        ('¿Cuánto tiempo se guardan los registros?',
         'Los registros se mantienen indefinidamente en la base de datos. Puedes consultarlos '
         'en cualquier momento desde el panel.'),
        
        ('¿Qué información se puede ver en los reportes?',
         'Los reportes muestran fecha, hora, nombre, documento y tipo de acceso (entrada/salida). '
         'Los administradores pueden ver más detalles de auditoría.'),
        
        ('¿Hay restricción de horarios para ingresar?',
         'Depende de la configuración del sistema. El administrador puede establecer horarios '
         'permitidos. Si intentas acceder fuera de horario, verás un error.'),
        
        ('¿Se puede usar el sistema sin conexión?',
         'No. El sistema requiere conexión a internet para funcionar correctamente. '
         'Sin conexión, no se podrá registrar ningún ingreso.'),
        
        ('¿Dónde puedo ver mi historial personal de accesos?',
         'Los aprendices pueden solicitar este información a vigilancia o al administrador. '
         'Vigilantes y administradores lo ven en el panel.'),
        
        ('¿Qué hago si detecto un error en mi registro?',
         'Reporta inmediatamente a vigilancia o al administrador con la hora, fecha y detalles. '
         'Se puede corregir y quedar registrado como ajuste en la auditoría.'),
        
        ('¿El sistema es seguro? ¿Se perderán mis datos?',
         'Sí, el sistema es muy seguro. Usa encriptación, respaldos automáticos y múltiples '
         'medidas de protección. Tus datos están protegidos.'),
    ]
    
    for question, answer in faqs:
        p = doc.add_paragraph()
        run = p.add_run(f'P: {question}\n')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 82, 0)
        p.add_run(f'\nR: {answer}')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    # ==== CONCLUSIÓN ====
    add_heading_styled(doc, 'Conclusión', 1)
    
    add_paragraph_justified(doc,
        'El Sistema de Control de Ingresos SENA es una herramienta moderna y segura que '
        'simplifica el registro de acceso en la institución. Con este sistema:',
        size=12)
    
    benefits = [
        'Se eliminan los registros manuales y la posibilidad de perder información.',
        'Se gana eficiencia: ingresos en segundos, no en minutos.',
        'Se aumenta la seguridad: registro preciso de quién está dónde.',
        'Se facilita la generación de reportes para análisis y auditoría.',
        'Se protegen los datos personales con tecnología de encriptación moderna.',
    ]
    
    for benefit in benefits:
        p = doc.add_paragraph(f'✓ {benefit}', style='List Bullet')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_paragraph()
    
    add_paragraph_justified(doc,
        'Si tienes preguntas, suggerencias o encuentras problemas, no dudes en contactar '
        'al equipo administrativo o de soporte técnico.',
        size=12)
    
    doc.add_paragraph()
    doc.add_paragraph()
    
    footer = doc.add_paragraph('Centro de Formación SENA - Sistema de Control de Ingresos')
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in footer.runs:
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(120, 120, 120)
    
    # ==== GUARDAR ====
    output_path = r'C:\Users\AMAT\Desktop\ingreso de aprendices\INFORME_SISTEMA_INGRESOS.docx'
    doc.save(output_path)
    print(f'✅ Documento guardado en: {output_path}')
    print(f'📄 Archivo: INFORME_SISTEMA_INGRESOS.docx')

if __name__ == '__main__':
    main()
