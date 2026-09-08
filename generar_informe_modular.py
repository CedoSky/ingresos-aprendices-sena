#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Informe del Sistema de Control de Ingresos SENA - VERSIÓN MODULAR
Crea un documento Word con estructura modular: Ingreso > Vigilancia > Administración
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
            run.font.color.rgb = RGBColor(26, 82, 0)  # Verde SENA oscuro
            run.font.size = Pt(28)
            run.font.bold = True
    elif level == 2:
        for run in heading.runs:
            run.font.color.rgb = RGBColor(57, 169, 0)  # Verde claro
            run.font.size = Pt(18)
    elif level == 3:
        for run in heading.runs:
            run.font.color.rgb = RGBColor(57, 169, 0)
            run.font.size = Pt(14)
    
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
    title = doc.add_heading('Sistema de Control de Ingresos SENA', level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.color.rgb = RGBColor(26, 82, 0)
        run.font.size = Pt(36)
    
    subtitle = doc.add_paragraph('Informe Completo de Funcionamiento')
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in subtitle.runs:
        run.font.size = Pt(18)
        run.font.color.rgb = RGBColor(57, 169, 0)
    
    doc.add_paragraph()
    
    info_text = doc.add_paragraph(
        f'Centro de Formación SENA\n'
        f'Versión: 6.0\n'
        f'Fecha: {datetime.now().strftime("%d de %B de %Y")}'
    )
    info_text.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in info_text.runs:
        run.font.size = Pt(12)
    
    doc.add_page_break()
    
    # ==== TABLA DE CONTENIDO ====
    add_heading_styled(doc, 'Tabla de Contenido', 1)
    
    toc_items = [
        'MÓDULO 1: SISTEMA DE INGRESO CON CÓDIGO DE BARRAS',
        '    • Introducción al módulo de ingreso',
        '    • Funcionalidad general',
        '    • Proceso paso a paso',
        '    • Mensajes del sistema',
        '    • Requisitos y preparación',
        '',
        'MÓDULO 2: PANEL DE VIGILANCIA',
        '    • Introducción a vigilancia',
        '    • Panel general',
        '    • Monitor en tiempo real',
        '    • Estadísticas y filtros',
        '    • Control de zonas y accesos',
        '    • Sistema de alertas',
        '    • Funcionalidades avanzadas',
        '',
        'MÓDULO 3: PANEL DE ADMINISTRACIÓN',
        '    • Introducción a administración',
        '    • Acceso y permisos',
        '    • Gestión de usuarios',
        '    • Registro de personas',
        '    • Búsqueda y reportes',
        '    • Control y auditoría',
        '    • Configuración del sistema',
    ]
    
    for item in toc_items:
        if item == '':
            doc.add_paragraph()
        elif item.startswith('    '):
            p = doc.add_paragraph(item[4:], style='List Bullet')
            p.paragraph_format.left_indent = Inches(0.7)
        else:
            p = doc.add_paragraph(item, style='List Bullet')
            p.paragraph_format.left_indent = Inches(0.3)
            for run in p.runs:
                run.font.bold = True
                run.font.size = Pt(11)
    
    doc.add_page_break()
    
    # ===============================================
    # MÓDULO 1: INGRESO CON CÓDIGO DE BARRAS
    # ===============================================
    
    add_heading_styled(doc, 'MÓDULO 1: SISTEMA DE INGRESO CON CÓDIGO DE BARRAS', 1)
    
    add_paragraph_justified(doc,
        'El módulo de ingreso es la interfaz principal donde los aprendices, instructores y '
        'visitantes registran su entrada y salida diaria de la institución. Es un sistema simple, '
        'rápido y automático que funciona escaneando el código de barras del documento de identidad.')
    
    doc.add_paragraph()
    
    add_heading_styled(doc, 'Introducción al Módulo de Ingreso', 2)
    
    add_paragraph_justified(doc,
        'Antes del sistema digital, el registro de ingreso se hacía manualmente: un vigilante anotaba '
        'en un cuaderno quién entraba y a qué hora. Esto era lento, propenso a errores y difícil de consultar después. '
        '\n\n'
        'Ahora, con el código de barras, todo es automático y digital. El sistema registra instantáneamente '
        'quién entra, a qué hora exacta, y mantiene un archivo digital permanente. Además, permite detectar '
        'personas no autorizadas o intentos de acceso irregular.')
    
    doc.add_paragraph()
    
    add_heading_styled(doc, 'Funcionalidad General', 2)
    
    add_paragraph_justified(doc,
        'El sistema de ingreso funciona así:')
    
    doc.add_paragraph()
    
    workflow = [
        ('1. Se abre la página de ingreso', 
         'En la computadora ubicada en la entrada, se muestra la pantalla del portal de ingreso con el logo SENA y un campo para escanear.'),
        
        ('2. La persona escanea su documento', 
         'Usa un lector de código de barras (similar a los de las tiendas) para escanear su cédula o carnet. El número aparece automáticamente.'),
        
        ('3. El sistema busca en la base de datos', 
         'En milisegundos, el sistema busca si esa persona está registrada. Si existe, continúa; si no, muestra un error.'),
        
        ('4. Se registra entrada o salida', 
         'Si es la primera vez en el día, marca INGRESO. Si ya había ingresado, marca SALIDA. Se guarda la hora exacta.'),
        
        ('5. Confirmación visual y sonora', 
         'La pantalla muestra un mensaje de éxito con el nombre, foto y hora. También emite un sonido para confirmar.'),
        
        ('6. Registro permanente', 
         'El evento queda guardado en la base de datos. Vigilancia y administración lo pueden ver inmediatamente en sus paneles.'),
    ]
    
    for step_title, description in workflow:
        p = doc.add_paragraph()
        run = p.add_run(step_title + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        run.font.size = Pt(12)
        p.add_run(description)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Proceso Paso a Paso: Cómo Ingresar', 2)
    
    steps_detail = [
        ('PASO 1: Ubicación e Identificación de la Pantalla',
         'Cuando llegas a la institución, dirígete a la entrada donde verás una computadora o tablet con la pantalla del sistema SENA. '
         'La pantalla mostrará:\n\n'
         '  • Logo del SENA en grande en el centro\n'
         '  • Un cuadro de texto blanco (campo de entrada)\n'
         '  • Instrucciones que dicen "Escanea tu documento"\n'
         '  • La hora actual en la esquina superior'),
        
        ('PASO 2: Preparar tu Documento',
         'Ten tu cédula o carnet a mano. Limpia el código de barras si está sucio o rayado. El código de barras debe estar en la parte trasera '
         'de tu documento, usualmente es una serie de líneas verticales negras.'),
        
        ('PASO 3: Escanear el Código',
         'Usa el lector de código de barras (el dispositivo rojo o negro con un escáner) para leer tu documento. Solo acerca la cédula a la lectura. '
         'No necesitas presionar nada, el lector automáticamente capturará el código. Deberás escuchar un beep o ver una luz confirmar que se leyó.'),
        
        ('PASO 4: Esperar Procesamiento',
         'Después de escanear, el sistema tardará 1-2 segundos en buscar tu nombre en la base de datos. Durante este tiempo, '
         'la pantalla mostrará "Procesando..." o un ícono de carga.'),
        
        ('PASO 5: Ver el Resultado',
         'La pantalla mostrará uno de estos mensajes:\n\n'
         '  ✅ INGRESO EXITOSO - Tu entrada fue registrada\n'
         '  ✅ SALIDA EXITOSA - Tu salida fue registrada\n'
         '  ⚠️ ERROR - Tu documento no fue encontrado\n\n'
         'Si es exitoso, también verás:\n'
         '  • Tu nombre completo\n'
         '  • Tu programa/especialidad\n'
         '  • La hora exacta del registro\n'
         '  • De verdad, tu foto de perfil (si está registrada)'),
        
        ('PASO 6: Confirmación y Acceso',
         'Una vez registrado, puedes pasar a la institución normalmente. El sistema guarda automáticamente el evento. '
         'No necesitas hacer nada más. El registro está completo.'),
    ]
    
    for step_num, step_content in steps_detail:
        p = doc.add_paragraph()
        run = p.add_run(step_num + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 82, 0)
        run.font.size = Pt(13)
        p.add_run(step_content)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Mensajes del Sistema y Significados', 2)
    
    add_paragraph_justified(doc,
        'Cuando escaneas tu documento, el sistema te muestra un mensaje. Aquí explicamos cada uno:')
    
    doc.add_paragraph()
    
    messages_data = [
        ['Mensaje', 'Significado', 'Qué Hacer'],
        [
            '✅ INGRESO\nEXITOSO',
            'Tu documento fue encontrado y es tu primera vez en el día. Tu entrada está registrada.',
            'Puedes proceder. Ya estás dentro del sistema.'
        ],
        [
            '✅ SALIDA\nEXITOSA',
            'Tu documento fue encontrado y ya habías ingresado hoy. Ahora tu salida está registrada.',
            'Completaste tu el registro del día. Puedes retirarte.'
        ],
        [
            '⚠️ NO\nENCONTRADO',
            'Tu documento no existe en la base de datos. Posiblemente aún no fue registrado o hay un error en el código de barras.',
            'Acude a vigilancia. Ellos pueden registrarte manualmente o verificar tu información.'
        ],
        [
            '⚠️ ACCESO\nDENEGADO',
            'Tu cuenta fue desactivada (vacaciones, suspensión, baja, etc.).',
            'Contacta con administración. Hay una restricción en tu acceso.'
        ],
        [
            '⚠️ ERROR\nDE LECTURA',
            'El código de barras de tu documento no se pudo leer correctamente. Posiblemente está dañado o sucio.',
            'Limpia tu documento e intenta de nuevo. Si persiste, ve a vigilancia.'
        ],
        [
            '⚠️ ERROR\nDE SISTEMA',
            'Hay un problema técnico en el servidor o conexión a internet.',
            'Intenta de nuevo en unos segundos. Si sigue fallando, avisa a vigilancia.'
        ],
    ]
    
    table = create_table_with_borders(doc, len(messages_data), 3)
    table.autofit = False
    
    for i, row_data in enumerate(messages_data):
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
                        run.font.size = Pt(11)
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                shade_paragraph(cell.paragraphs[0], '1a5200')
            else:
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for run in paragraph.runs:
                        run.font.size = Pt(10)
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Requisitos y Preparación', 2)
    
    add_paragraph_justified(doc,
        'Para que el sistema de ingreso funcione correctamente, se necesitan algunos requisitos:')
    
    doc.add_paragraph()
    
    requirements = [
        ('📋 Estar Registrado en el Sistema',
         'Antes de poder ingresar, tu información debe estar cargada en la base de datos. '
         'Esto incluye: nombre completo, tipo de documento, número de documento, programa, '
         'especialidad y foto. El administrador es quien realiza este registro.'),
        
        ('📞 Mantener el Código de Barras Legible',
         'Tu cédula o carnet debe tener el código de barras en buen estado (sin rayones, '
         'roturas o manchas). Si está dañado, el lector no podrá capturarlo y tendrás que '
         'registrarte manualmente con vigilancia.'),
        
        ('🌐 Conexión a Internet',
         'El sistema requiere conexión a internet para consultar la base de datos. '
         'Si no hay conexión, no se puede registrar el acceso. El administrador debe '
         'revisar la conexión de wifi o ethernet de la computadora.'),
        
        ('⚡ Hardware Funcional',
         'La computadora, el lector de código de barras y el escritorio de ingreso deben estar en buen estado. '
         'Si algo presenta fallas (pantalla no enciende, lector no funciona, etc.), '
         'reporta a vigilancia para que lo reparen.'),
        
        ('🕐 Hora Sincronizada',
         'La computadora debe tener la hora correcta. Si la hora está atrasada o adelantada, '
         'los registros pueden aparecer con tiempo incorrecto. El sistema la sincroniza automáticamente.'),
    ]
    
    for req_title, req_desc in requirements:
        p = doc.add_paragraph()
        run = p.add_run(req_title + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        run.font.size = Pt(12)
        p.add_run(req_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    add_heading_styled(doc, 'Problemas Comunes y Soluciones', 2)
    
    problems = [
        ('El código de barras no se escanea',
         'Causa: Código sucio, rayado, o dañado\n'
         'Solución: Limpia tu documento con un paño suave. Intenta nuevamente. Si sigue sin funcionar, '
         've a vigilancia para registro manual.'),
        
        ('Sale "Documento no encontrado"',
         'Causa: Tu información aún no está registrada en el sistema\n'
         'Solución: Acude a administración para que te registren. Necesitarán tu documento, datos personales y foto.'),
        
        ('Sale "Acceso Denegado" sin razón aparente',
         'Causa: Tu cuenta fue desactivada (posible error o cambio de estado)\n'
         'Solución: Contacta con administración para que revisen tu estado y reactiven tu acceso.'),
        
        ('La pantalla no responde o se cuelga',
         'Causa: Problema técnico, desconexión, o sobrecarga\n'
         'Solución: Espera 10 segundos. Si sigue igual, reporta a vigilancia. Ellos reiniciarán el sistema.'),
        
        ('El lector no funciona (no emite beep)',
         'Causa: Dispositivo desconectado, batería agotada, o falla de hardware\n'
         'Solución: Reporta a vigilancia. Pueden usar registro manual mientras se repara.'),
    ]
    
    for prob_title, solution in problems:
        p = doc.add_paragraph()
        run = p.add_run(f'❌ {prob_title}\n')
        run.bold = True
        run.font.color.rgb = RGBColor(200, 0, 0)
        run.font.size = Pt(11)
        p.add_run(solution)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    # ===============================================
    # MÓDULO 2: PANEL DE VIGILANCIA
    # ===============================================
    
    add_heading_styled(doc, 'MÓDULO 2: PANEL DE VIGILANCIA', 1)
    
    add_paragraph_justified(doc,
        'El Panel de Vigilancia es la interfaz de control y monitoreo para vigilantes y personal de seguridad. '
        'Desde aquí se supervisa en tiempo real quién está adentro de la institución, se monitorean los accesos '
        'y se detectan posibles problemas de seguridad. Es el "centro de mando" de la seguridad.')
    
    doc.add_paragraph()
    
    add_heading_styled(doc, 'Introducción al Módulo de Vigilancia', 2)
    
    add_paragraph_justified(doc,
        'La vigilancia es crítica en cualquier institución educativa. El vigilante debe saber en todo momento '
        'quién está adentro, quién intenta entrar sin autorización, y alertar si hay situaciones anormales. '
        'Antes, esto se hacía manualmente: leyendo cuadernos, contando personas, buscando en papeles. '
        '\n\n'
        'Ahora, el sistema le presenta toda esta información en una pantalla, actualizada en tiempo real. '
        'El vigilante puede ver instantáneamente:\n'
        '  • Quién acaba de entrar o salir\n'
        '  • Cuántas personas hay adentro\n'
        '  • Quién falta por salir\n'
        '  • Personas no autorizadas\n'
        '  • Patrones anormales')
    
    doc.add_paragraph()
    
    add_heading_styled(doc, 'Acceso al Panel de Vigilancia', 2)
    
    add_paragraph_justified(doc,
        'Para acceder al panel de vigilancia:')
    
    doc.add_paragraph()
    
    access_steps = [
        ('1. Login como Vigilante',
         'Abre el navegador y ve a la página de login. Ingresa tu email de vigilante y contraseña. '
         'Ejemplo: vigilante01@sena.edu.co'),
        
        ('2. Seleccionar Panel de Vigilancia',
         'Después de ingresar, verás el DASHBOARD (menú principal). Busca el botón que dice '
         '"CONTROL DE ACCESOS", "VIGILANCIA", o similar. Haz clic en él.'),
        
        ('3. Pantalla Principal Carga',
         'Se abrirá el Panel de Vigilancia con todos los datos. Esto toma 2-5 segundos dependiendo de la conexión.'),
    ]
    
    for desc in access_steps:
        p = doc.add_paragraph(f'• {desc[0]}\n{desc[1]}', style='List Bullet')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Componentes del Panel de Vigilancia', 2)
    
    add_paragraph_justified(doc,
        'El panel está dividido en varias secciones, cada una con información específica:')
    
    doc.add_paragraph()
    
    components = [
        ('🎯 BARRA SUPERIOR (TOPBAR)',
         'En la parte superior de la pantalla verás:\n'
         '  • Logo SENA\n'
         '  • Nombre del panel: "Control de Accesos"\n'
         '  • RELOJ DIGITAL grande con la hora exacta (importante para sincronización)\n'
         '  • Nombre del vigilante conectado\n'
         '  • Botón SALIR para cerrar sesión'),
        
        ('📊 ESTADÍSTICAS (CARDS SUPERIORES)',
         'Números rápidos en tarjetas de colores:\n'
         '  • Total de Ingresos Hoy: Cuántas personas han entrado\n'
         '  • Personas Dentro Ahora: Cuántas están adentro en este momento\n'
         '  • Faltas por Salir: Quién debe irse\n'
         '  • Alertas Activas: Problemas detectados'),
        
        ('🏢 ZONAS/PISOS (LEFT PANEL)',
         'Panel a la izquierda mostrando la distribución por piso:\n'
         '  • Piso 1: 15 personas\n'
         '  • Piso 2: 8 personas\n'
         '  • Piso 3: 5 personas\n'
         '  • Si alguno está muy lleno o vacío, se marca en color de alerta'),
        
        ('📋 TABLA DE REGISTROS (MAIN AREA)',
         'La sección más importante: listado de TODAS las personas que entraron hoy\n'
         'Columnas:\n'
         '  • Tiempo (hora exacta)\n'
         '  • Nombre\n'
         '  • Documento\n'
         '  • Tipo (Entrada/Salida)\n'
         '  • Estado (Dentro/Fuera)\n'
         '  • Foto/Botones de acción'),
        
        ('🔍 FILTROS Y BÚSQUEDA (TOP OF TABLE)',
         'Herramientas para filtrar la información:\n'
         '  • Filtro por Tipo: ENTRADA / SALIDA / TODOS\n'
         '  • Búsqueda por Nombre: Escribe el nombre\n'
         '  • Búsqueda por Documento: Ingresa el número\n'
         '  • Los resultados se actualizan automáticamente'),
    ]
    
    for comp_title, comp_desc in components:
        p = doc.add_paragraph()
        run = p.add_run(comp_title + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 82, 0)
        run.font.size = Pt(12)
        p.add_run(comp_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Usando el Monitor en Tiempo Real', 2)
    
    add_paragraph_justified(doc,
        'El monitor muestra TODOS los eventos a medida que ocurren. Cada vez que alguien escanea su documento '
        'en la entrada, aparece instantáneamente en la tabla:')
    
    doc.add_paragraph()
    
    realtime_features = [
        ('Fila Nueva se Destaca',
         'La fila más reciente (última persona que escaneó) se ilumina con un fondo verde claro por 3 segundos, '
         'indicando que es un registro NUEVO.'),
        
        ('Color Verde = Entrada',
         'Si la fila está con un fondo verde o tiene un ícono de entrada, significa que la persona ENTRÓ.'),
        
        ('Color Naranja = Salida',
         'Si la fila está con fondo naranja o ícono de salida, significa que la persona SALIÓ.'),
        
        ('Ordenamiento Automático',
         'Los registros aparecen ordenados por hora (los más recientes primero), para que siempre veas quién '
         'acaba de llegar.'),
        
        ('Auto-Actualización',
         'No necesitas actualizar la página. El sistema se refresca automáticamente cada 2 segundos sin que hagas nada.'),
        
        ('Información Completa',
         'Haciendo clic en una fila, puedes ver más detalles:\n'
         '  • Foto de la persona\n'
         '  • Programa/especialidad\n'
         '  • Email y teléfono\n'
         '  • Historial completo de accesos de esa persona'),
    ]
    
    for feature_title, feature_desc in realtime_features:
        p = doc.add_paragraph()
        run = p.add_run(f'▶ {feature_title}\n')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        p.add_run(feature_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Filtros y Búsqueda Avanzada', 2)
    
    add_paragraph_justified(doc,
        'Para encontrar información específica, usa los filtros disponibles en la parte superior de la tabla:')
    
    doc.add_paragraph()
    
    filters = [
        ('Filtro por Tipo',
         'Tres botones para elegir:\n'
         '  • ENTRADA: Solo muestra a quienes entraron\n'
         '  • SALIDA: Solo muestra a quienes salieron\n'
         '  • TODOS: Muestra entrada y salida (por defecto)'),
        
        ('Búsqueda por Nombre',
         'Campo de texto que dice "Buscar nombre". Escribe el nombre completo o parcial. '
         'El sistema filtra instantáneamente mostrando solo coincidencias. '
         'Ejemplo: Si escribes "Juan", muestra a todos los Juanes.'),
        
        ('Búsqueda por Documento',
         'Campo que dice "Buscar documento". Ingresa el número de cédula. '
         'Útil si buscas a una persona específica. Ejemplo: 1234567890'),
        
        ('Búsqueda por Fecha/Hora',
         'Algunos sistemas permiten filtrar por rango de fechas. '
         'Selecciona "Desde" y "Hasta" para ver registros de un período específico. '
         'Ejemplo: Todos los registros de ayer.'),
    ]
    
    for filter_title, filter_desc in filters:
        p = doc.add_paragraph()
        run = p.add_run(f'🔎 {filter_title}\n')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        p.add_run(filter_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Sistema de Alertas y Monitoreo', 2)
    
    add_paragraph_justified(doc,
        'El sistema detecta automáticamente situaciones anormales y las marca como ALERTAS. '
        'El vigilante debe revisar estas alertas constantemente:')
    
    doc.add_paragraph()
    
    alerts = [
        ('🚨 Acceso Denegado',
         'Una persona intentó acceder pero fue rechazada (no autorizada, cuenta suspendida, etc.). '
         'ACCIÓN: Verificar quién es y contactar con administración si es necesario.'),
        
        ('⚠️ Documento No Encontrado',
         'Alguien escaneó su documento pero NO está registrado en el sistema. '
         'ACCIÓN: Interrogar a la persona, tomar datos, avisar a administración.'),
        
        ('⏰ Acceso Fuera de Horario',
         'Una persona entró fuera de los horarios permitidos. '
         'ACCIÓN: Revisar si es personal autorizado (instructor, administrador) o si hay error configuración.'),
        
        ('👥 Concentración Anormal',
         'Un piso tiene demasiadas personas (capacidad excedida). '
         'ACCIÓN: Asegurarse de que no haya aglomeración peligrosa.'),
        
        ('🚪 Puerta Abierta Anormalmente',
         'Si el sistema está connectado a cerradura electrónica, se alerta si la puerta permanece abierta mucho tiempo. '
         'ACCIÓN: Verificar y cerrar si es necesario.'),
        
        ('❌ Falta de Salida',
         'Una persona que entró no ha salido después de cierto tiempo (ejemplo: 8 horas después). '
         'ACCIÓN: Contactar con la persona o administración para verificar.'),
    ]
    
    for alert_title, alert_desc in alerts:
        p = doc.add_paragraph()
        run = p.add_run(alert_title + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(200, 0, 0)
        run.font.size = Pt(11)
        p.add_run(alert_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Control de Zonas y Pisos', 2)
    
    add_paragraph_justified(doc,
        'Si la institución tiene múltiples pisos o zonas, el panel muestra una distribución visual:')
    
    doc.add_paragraph()
    
    add_paragraph_justified(doc,
        'Tabla de Distribución (LEFT PANEL):\n\n'
        'PISO 1: 23 personas\n'
        'PISO 2: 12 personas\n'
        'PISO 3: 5 personas\n'
        'PATIO/AFUERA: 3 personas\n\n'
        'Cada sección muestra cuánta gente hay en ese momento en esa zona. Esto es importante para:\n'
        '  • Detectar aglomeraciones\n'
        '  • Saber dónde buscar a una persona\n'
        '  • Verificar capacity\n'
        '  • Detectar si alguien se salió del área permitida')
    
    doc.add_paragraph()
    
    add_paragraph_justified(doc,
        'Si algún piso está MUY LLENO (capacidad máxima), el número se marca en ROJO o con alerta, '
        'indicándole al vigilante que debe prestar atención.')
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Control de Puertas Electrónicas (ESP32)', 2)
    
    add_paragraph_justified(doc,
        'Si la institución tiene una cerradura electrónica instalada (sistema ESP32 TRIAC), '
        'el panel de vigilancia incluye un control adicional para la puerta:')
    
    doc.add_paragraph()
    
    door_features = [
        ('Estado de la Puerta',
         'Muestra si está ABIERTA o CERRADA\n'
         '  • 🟢 Verde = CERRADA (seguro)\n'
         '  • 🔴 Rojo = ABIERTA (alerta)'),
        
        ('Abrir Remotamente',
         'Botón que dice "ABRIR PUERTA" o "🔓 Desbloquear". Permite abrir la puerta '
         'desde el panel sin ir físicamente a ella. Útil cuando el vigilante autoriza entrada.'),
        
        ('Historial de Aperturas',
         'Registro de todas las veces que se abrió/cerró la puerta, quién la abrió (manual o remoto), y a qué hora. '
         'Importante para auditoría de seguridad.'),
        
        ('Historial de Fallos',
         'Si la puerta falla (no abre, no cierra, desconexión), se registra. Útil para mantenimiento.'),
    ]
    
    for feature_title, feature_desc in door_features:
        p = doc.add_paragraph()
        run = p.add_run(f'🔐 {feature_title}\n')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 82, 0)
        run.font.size = Pt(11)
        p.add_run(feature_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Tareas Diarias del Vigilante', 2)
    
    add_paragraph_justified(doc,
        'El vigilante debe realizar estas tareas usando el panel:')
    
    doc.add_paragraph()
    
    daily_tasks = [
        ('Mañana (7:00 - 8:30)',
         'Recibimiento y monitoreo\n'
         '  ✓ Llegar temprano y abrir el sistema\n'
         '  ✓ Ver cómo van llegando las personas\n'
         '  ✓ Verificar que los códigos de barras funcionen\n'
         '  ✓ Reportar cualquier dispositivo dañado'),
        
        ('Durante el Día (8:30 - 12:00)',
         'Vigilancia continua\n'
         '  ✓ Monitorear eventos en tiempo real\n'
         '  ✓ Revisar alertas que aparezcan\n'
         '  ✓ Verificar personas no autorizadas\n'
         '  ✓ Responder a consultas sobre acceso'),
        
        ('Almuerzo/Zona Baja (12:00 - 1:00)',
         'Monitoreo en horas bajas\n'
         '  ✓ Vigilar posibles movimientos anormales\n'
         '  ✓ Verificar cuánta gente falta por salir\n'
         '  ✓ Hacer rondas de seguridad'),
        
        ('Tarde (1:00 - 5:00)',
         'Control de salidas\n'
         '  ✓ Monitorear que la gente salga en orden\n'
         '  ✓ Alertar sobre personas que se quedan muy tarde\n'
         '  ✓ Preparar reporte del día'),
        
        ('Cierre (5:00 - 6:00)',
         'Finalización y documentación\n'
         '  ✓ Verificar que todos hayan salido\n'
         '  ✓ Generar reporte del día\n'
         '  ✓ Anotar eventos especiales\n'
         '  ✓ Cerrar sesión segura'),
    ]
    
    for task_title, task_desc in daily_tasks:
        p = doc.add_paragraph()
        run = p.add_run(f'⏰ {task_title}\n')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        p.add_run(task_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    # ===============================================
    # MÓDULO 3: PANEL DE ADMINISTRACIÓN
    # ===============================================
    
    add_heading_styled(doc, 'MÓDULO 3: PANEL DE ADMINISTRACIÓN', 1)
    
    add_paragraph_justified(doc,
        'El Panel de Administración es el centro de control total del sistema. Solo administradores con '
        'credenciales especiales pueden acceder. De aquí se gestiona todo: usuarios, registros, reportes, '
        'configuración, auditoría y seguridad del sistema.')
    
    doc.add_paragraph()
    
    add_heading_styled(doc, 'Introducción al Módulo de Administración', 2)
    
    add_paragraph_justified(doc,
        'Mientras los aprendices usan el portal de ingreso y los vigilantes monitorean, el administrador '
        'es responsable de mantener todo el sistema funcionando: crear cuentas, registrar nuevas personas, '
        'generar reportes, solucionar problemas, y asegurar que los datos sean correctos y seguros. '
        '\n\n'
        'El administrador tiene la responsabilidad más grande: tener en sus manos toda la información '
        'de la institución y sus usuarios. Por eso, debe ser una persona de confianza con conocimiento '
        'de sistemas.')
    
    doc.add_paragraph()
    
    add_heading_styled(doc, 'Acceso y Permisos', 2)
    
    add_paragraph_justified(doc,
        'Hay dos tipos de administradores:')
    
    doc.add_paragraph()
    
    admin_roles = [
        ('👑 SUPERADMIN',
         'Es el principal. Tiene acceso a TODO sin restricciones:\n'
         '  • Ver/editar/eliminar cualquier usuario\n'
         '  • Ver logs completos de auditoría\n'
         '  • Cambiar configuración del sistema\n'
         '  • Restaurar respaldos\n'
         '  • Eliminar datos (cuidado)\n'
         '  Generalmente solo 1 persona tiene este nivel.'),
        
        ('🛡️ ADMIN NORMAL',
         'Es un administrador regular. Tiene permisos limitados:\n'
         '  • Crear/editar usuarios (no eliminar)\n'
         '  • Registrar personas\n'
         '  • Ver reportes\n'
         '  • Cambiar algunos parámetros\n'
         '  • No puede acceder a auditoría completa\n'
         '  Puede haber uno o más admins normales.'),
    ]
    
    for role_title, role_desc in admin_roles:
        p = doc.add_paragraph()
        run = p.add_run(role_title + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 82, 0)
        run.font.size = Pt(12)
        p.add_run(role_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    add_paragraph_justified(doc,
        'Para acceder al panel admin:\n\n'
        '1. Inicia sesión con tu email de administrador\n'
        '2. En el Dashboard, selecciona "ADMINISTRACIÓN" o "ADMIN PANEL"\n'
        '3. Se cargará la interfaz de administración con todas las herramientas')
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Gestión de Usuarios (Crear y Editar Cuentas)', 2)
    
    add_paragraph_justified(doc,
        'La gestión de usuarios es crear, editar y controlar las cuentas de vigilantes y otros administradores. '
        'Los aprendices NO se crean aquí (se registran en la sección "Registro de Personas").')
    
    doc.add_paragraph()
    
    user_management = [
        ('📝 Crear Nuevo Usuario',
         'Procedimiento:\n'
         '  1. Click en "Crear Nuevo Usuario" o "+ Nuevo Usuario"\n'
         '  2. Completa el formulario:\n'
         '     - Email: dirección de correo único\n'
         '     - Contraseña: fuerte (combinación de letras, números, símbolos)\n'
         '     - Nombre: nombre completo\n'
         '     - Rol: Elegir (Vigilante, Admin, SuperAdmin)\n'
         '     - Activo: Marcar sí/no\n'
         '  3. Click "GUARDAR"\n'
         '  4. El usuario recibe un email de confirmación con instrucciones'),
        
        ('✏️ Editar Usuario Existente',
         'Procedimiento:\n'
         '  1. Busca el usuario en la lista (por nombre o email)\n'
         '  2. Click en "EDITAR" o ícono de lápiz\n'
         '  3. Modifica los campos que necesites (no la contraseña aquí)\n'
         '     - Nombre\n'
         '     - Email\n'
         '     - Rol\n'
         '     - Estado activo/inactivo\n'
         '  4. Click "GUARDAR CAMBIOS"'),
        
        ('🔑 Cambiar Contraseña de un Usuario',
         'Si un usuario olvida su contraseña:\n'
         '  1. Selecciona el usuario\n'
         '  2. Click en "RESETEAR CONTRASEÑA\n'
         '  3. El sistema envía un email con enlace de recuperación\n'
         '  4. El usuario puede crear una nueva contraseña\n'
         '  Alternativa: Asignar una temporal (no recomendado)'),
        
        ('🔴 Desactivar/Bloquear Usuario',
         'Si alguien se va o hay un problema:\n'
         '  1. Click en el usuario\n'
         '  2. Cambiar "Activo" a NO\n'
         '  3. Click "GUARDAR"\n'
         '  4. Esa cuenta YA NO puede iniciar sesión\n'
         '  No eliminamos, solo desactivamos (para auditoría histórica)'),
        
        ('🗑️ Eliminar Usuario (SuperAdmin Only)',
         'Solo el SuperAdmin puede eliminar (permanentemente):\n'
         '  1. Click en usuario\n'
         '  2. Click "ELIMINAR USUARIO"\n'
         '  3. Confirmar en el diálogo\n'
         '  ⚠️ CUIDADO: Esto es PERMANENTE, no se puede deshacer. '
         'Solo hacerlo si es realmente necesario (error de duplicado, etc.)'),
    ]
    
    for procedure_title, procedure_desc in user_management:
        p = doc.add_paragraph()
        run = p.add_run(procedure_title + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        p.add_run(procedure_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Registro de Personas (Aprendices, Instructores, Visitantes)', 2)
    
    add_paragraph_justified(doc,
        'Esta es la función más importante. Aquí se agregan todas las personas que pueden acceder a la institución:')
    
    doc.add_paragraph()
    
    add_heading_styled(doc, 'Tipos de Personas', 3)
    
    person_types = [
        ('👨‍🎓 APRENDICES',
         'Estudiantes inscritos en programas de formación.\n'
         'Datos: Nombre, documento, email, teléfono, programa, ficha, especialidad.'),
        
        ('👨‍🏫 INSTRUCTORES',
         'Personal docente de la institución.\n'
         'Datos: Nombre, documento, email, teléfono, departamento, especialidad.'),
        
        ('👔 ADMINISTRATIVOS',
         'Personal de administración, mantenimiento, servicios generales.\n'
         'Datos: Nombre, documento, email, teléfono, cargo, departamento.'),
        
        ('👨‍💼 VISITANTES',
         'Personas de afuera autorizadas a visitar (proveedores, padres, etc.).\n'
         'Datos: Nombre, documento, email, teléfono, motivo de visita, fecha de autorización, hasta cuándo.'),
    ]
    
    for ptype, ptype_desc in person_types:
        p = doc.add_paragraph()
        run = p.add_run(ptype + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 82, 0)
        p.add_run(ptype_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    add_heading_styled(doc, 'Cómo Registrar una Persona', 3)
    
    registration_steps = [
        ('PASO 1: Acceder a Registro',
         'Click en "REGISTRO DE PERSONAS" o "+ REGISTRAR NUEVA PERSONA"'),
        
        ('PASO 2: Completar Datos Básicos',
         'Rellena los campos obligatorios (*)\n'
         '  • Nombre Completo\n'
         '  • Tipo de Documento (Cédula, Pasaporte, etc.)\n'
         '  • Número de Documento\n'
         '  • Email\n'
         '  • Teléfono'),
        
        ('PASO 3: Seleccionar Perfil',
         'Dropdown que dice "Perfil". Elige:\n'
         '  - Aprendiz\n'
         '  - Instructor\n'
         '  - Administrativo\n'
         '  - Visitante'),
        
        ('PASO 4: Datos Específicos',
         'Dependiendo del perfil, aparecen campos adicionales:\n'
         '  • Si es Aprendiz: Programa, Ficha, Especialidad, Área\n'
         '  • Si es Instructor: Departamento, Especialidad\n'
         '  • Si es Visitante: Motivo, Fecha inicio, Fecha fin'),
        
        ('PASO 5: Foto (Opcional)',
         'Click en "SUBIR FOTO" o arrastra una imagen. Formatos: JPG, PNG.\n'
         '  • Tamaño recomendado: 200x200 px\n'
         '  • La foto aparecerá en el panel de vigilancia\n'
         '  • Útil para identificación rápida'),
        
        ('PASO 6: Guardar',
         'Click en "GUARDAR" o "REGISTRAR PERSONA"\n'
         '  • Se carga en la base de datos\n'
         '  • La persona ya puede ingresar (escanear su código)\n'
         '  • Un email de confirmación se envía (opcional)'),
    ]
    
    for step_num, step_content in registration_steps:
        p = doc.add_paragraph()
        run = p.add_run(step_num + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        p.add_run(step_content)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Búsqueda y Edición de Personas', 2)
    
    add_paragraph_justified(doc,
        'Una vez registradas, puedes buscar y editar personas:')
    
    doc.add_paragraph()
    
    search_edit = [
        ('🔍 BÚSQUEDA RÁPIDA',
         'Click en "BUSCAR PERSONA" o "BÚSQUEDA"\n'
         'Ingresa:\n'
         '  • Nombre completo o parcial\n'
         '  • Número de documento\n'
         '  • Email\n'
         'El sistema muestra resultados instantáneamente'),
        
        ('📋 VER DETALLES',
         'Click en el resultado. Se abre una pantalla con:\n'
         '  • Información personal completa\n'
         '  • Foto\n'
         '  • Historial de accesos (entrada/salida)\n'
         '  • Cambios realizados (auditoría)'),
        
        ('✏️ EDITAR INFORMACIÓN',
         'Click en "EDITAR" para cambiar datos:\n'
         '  • Nombre\n'
         '  • Email\n'
         '  • Teléfono\n'
         '  • Programa/especialidad\n'
         '  • Foto\n'
         '  • Estado (activo/inactivo)\n'
         'Los cambios quedan registrados en auditoría'),
        
        ('🚫 DESACTIVAR ACCESO',
         'Si alguien debe dejar de poder entrar (graduado, baja, etc.):\n'
         '  1. Buscar la persona\n'
         '  2. Click "EDITAR"\n'
         '  3. Cambiar "Activo" a NO\n'
         '  4. GUARDAR\n'
         '  Ya no podrá escanear su código'),
        
        ('🔑 AUTORIZAR VISITANTE',
         'Para visitantes:\n'
         '  1. Registrar con Perfil: VISITANTE\n'
         '  2. Establecer fecha de inicio y fin\n'
         '  3. Después de la fecha fin, acceso automáticamente denegado'),
    ]
    
    for feature_title, feature_desc in search_edit:
        p = doc.add_paragraph()
        run = p.add_run(f'▶ {feature_title}\n')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 82, 0)
        p.add_run(feature_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Control de Accesos y Registros', 2)
    
    add_paragraph_justified(doc,
        'Vista completa de todos los registros de entrada/salida:')
    
    doc.add_paragraph()
    
    access_control = [
        ('📊 VER TODOS LOS REGISTROS',
         'Click en "CONTROL DE ACCESOS" o "REGISTROS"\n'
         'Se abre una tabla monumental con:\n'
         '  • Fecha y hora exact\n'
         '  • Nombre y documento\n'
         '  • Tipo (Entrada/Salida)\n'
         '  • Vigilante que registró (si fue manual)\n'
         '  • Piso/Zona\n'
         '  • Observaciones'),
        
        ('🔍 FILTRAR REGISTROS',
         'Herramientas de filtrado:\n'
         '  • Por Fecha: Desde / Hasta\n'
         '  • Por Persona: Nombre o documento\n'
         '  • Por Tipo: Entrada / Salida / Todos\n'
         '  • Por Vigilante: Quién registró\n'
         '  Los filtros se combinan (AND)'),
        
        ('✏️ EDITAR REGISTRO',
         'Si hay un error en un registro (hora incorrecta, persona equivocada):\n'
         '  1. Click en "EDITAR" en la fila\n'
         '  2. Cambiar los datos necesarios\n'
         '  3. Por qué fue el cambio (comentario)\n'
         '  4. Click "GUARDAR"\n'
         '  ⚠️ El cambio queda marcado en auditoría'),
        
        ('🗑️ ELIMINAR REGISTRO',
         'Si fue un registro erróneo (duplicado, escaneo accidental):\n'
         '  1. Click en "ELIMINAR" o ícono de basura\n'
         '  2. Confirmar en el diálogo\n'
         '  3. Desaparece de la tabla\n'
         '  ⚠️ Queda rastro en auditoría de qué se eliminó'),
        
        ('📋 VER HISTORIAL DE PERSONA',
         'Para una persona específica, ver solo sus accesos:\n'
         '  1. Buscar el nombre en filtro\n'
         '  2. Se muestra solo sus entradas/salidas\n'
         '  3. Útil para asistencia, auditoría personal, investigación'),
    ]
    
    for ctrl_title, ctrl_desc in access_control:
        p = doc.add_paragraph()
        run = p.add_run(ctrl_title + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        p.add_run(ctrl_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Generación de Reportes y Exportación a Excel', 2)
    
    add_paragraph_justified(doc,
        'El sistema permite generar reportes detallados y exportarlos a Excel para análisis en cálculo:')
    
    doc.add_paragraph()
    
    reports = [
        ('📅 REPORTE DE ASISTENCIA DIARIA',
         'Genera una lista de quién entró y salió cada día\n'
         'Columnas: Nombre, Documento, Entrada, Salida, Total Horas, Estado\n'
         'Útil para: Control de asistencia, cálculo de horas trabajadas\n'
         'Exportar a: Excel, PDF'),
        
        ('📊 REPORTE MENSUAL',
         'Resumen de todo un mes: personas, accesos, patrones\n'
         'Incluye: Asistencia, faltas, retrasos, salidas temprano\n'
         'Útil para: Análisis de recursos, ocupación\n'
         'Exportar a: Excel, PDF'),
        
        ('👥 REPORTE DE PERSONAS REGISTRADAS',
         'Lista completa de todas las personas en el sistema\n'
         'Columnas: Nombre, Documento, Perfil, Programa, Email, Teléfono, Fecha Registro\n'
         'Útil para: Control de población, auditoría\n'
         'Exportar a: Excel'),
        
        ('📍 REPORTE POR ZONA/PISO',
         'Quién accede a cada zona, cuándo, frecuencia\n'
         'Útil para: Seguridad por ubicación, ocupación\n'
         'Exportar a: Excel'),
        
        ('⚠️ REPORTE DE ALERTAS/ANOMALÍAS',
         'Accesos denegados, documentos no encontrados, fallos de seguridad\n'
         'Columnas: Fecha, Tipo de Alerta, Detalles, Acción Tomada\n'
         'Útil para: Investigación, seguridad\n'
         'Exportar a: Excel, PDF'),
        
        ('💰 REPORTE DE INGRESOS (si hay pagos)',
         'Si el sistema registra pagos de servicios (cafetería, fotocopia)\n'
         'Columnas: Fecha, Persona, Servicio, Cantidad, Total\n'
         'Útil para: Finanzas, auditoría contable\n'
         'Exportar a: Excel'),
    ]
    
    for report_title, report_desc in reports:
        p = doc.add_paragraph()
        run = p.add_run(f'📋 {report_title}\n')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 82, 0)
        run.font.size = Pt(11)
        p.add_run(report_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    add_heading_styled(doc, 'Cómo Generar y Descargar un Reporte', 3)
    
    download_steps = [
        ('1. Click en "REPORTES" o "GENERAR REPORTE"'),
        ('2. Seleccionar tipo de reporte (ej: "Asistencia Diaria")'),
        ('3. Elegir rango de fechas (Desde / Hasta)'),
        ('4. Aplicar filtros adicionales si necesitas (persona, zona, etc.)'),
        ('5. Click en "GENERAR"'),
        ('6. El sistema procesa... (puede tomar 5-30 segundos)'),
        ('7. Aparece un botón "DESCARGAR EXCEL" o "DESCARGAR PDF"'),
        ('8. Click para descargar el archivo'),
        ('9. Se abre en Excel (o Acrobat para PDF)'),
        ('10. Puedes editar, gráficos, enviar, guardar, imprimir'),
    ]
    
    for step in download_steps:
        p = doc.add_paragraph(f'✓ {step}', style='List Bullet')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Configuración del Sistema', 2)
    
    add_paragraph_justified(doc,
        'Opciones avanzadas para personalizar el comportamiento del sistema:')
    
    doc.add_paragraph()
    
    config = [
        ('🌐 CONFIGURACIÓN DE RED',
         'IP del ESP32 (cerradura electrónica)\n'
         '  • Campo: "IP del ESP32"\n'
         '  • Ingresar: Ejemplo 192.168.1.45\n'
         '  • Botón "Probar Conexión" para verificar\n'
         '  • Click "Guardar" para aplicar'),
        
        ('🚪 CONFIGURACIÓN DE PUERTAS',
         'Número de pisos/zonas de la institución\n'
         '  • Agregar/Eliminar pisos\n'
         '  • Nombre de cada piso\n'
         '  • Capacidad máxima permitida\n'
         '  • Horarios de apertura/cierre'),
        
        ('🕐 HORARIOS PERMITIDOS',
         'Horas en que se permite acceso\n'
         '  • Hora de apertura (ej: 6:00 AM)\n'
         '  • Hora de cierre (ej: 6:00 PM)\n'
         '  • Accesos fuera de horario: permitir sí/no\n'
         '  • Horarios especiales (fin de semana, feriados)'),
        
        ('📢 MENSAJES PERSONALIZADOS',
         'Textos que aparecen en la pantalla de ingreso\n'
         '  • Mensaje de bienvenida\n'
         '  • Mensaje de error\n'
         '  • Instrucciones personalizadas'),
        
        ('🔐 CONFIGURACIÓN DE SEGURIDAD (SuperAdmin)',
         'Opciones de auditoría y protección\n'
         '  • Retención de logs (cuántos días guardar)\n'
         '  • Encriptación de datos\n'
         '  • Respaldos automáticos\n'
         '  • Intentos fallidos permitidos'),
    ]
    
    for config_title, config_desc in config:
        p = doc.add_paragraph()
        run = p.add_run(config_title + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(57, 169, 0)
        p.add_run(config_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Auditoría e Historial Completo', 2)
    
    add_paragraph_justified(doc,
        'El sistema registra TODOS los cambios realizados. Esta es una herramienta crítica para '
        'investigación y seguridad:')
    
    doc.add_paragraph()
    
    add_paragraph_justified(doc,
        '🔍 ¿QUÉ SE REGISTRA?\n\n'
        '  • Quién hizo qué (administrador que hizo el cambio)\n'
        '  • Qué cambió (nombre del campo modificado)\n'
        '  • Cuándo (fecha y hora exacta)\n'
        '  • Valor anterior y nuevo\n'
        '  • Razón del cambio (comentario del admin)\n'
        '  • IP desde donde se hizo')
    
    doc.add_paragraph()
    
    add_paragraph_justified(doc,
        '📋 EJEMPLOS REGISTRADOS:\n\n'
        '  • Un admin creó usuario "vigilante01@sena.edu.co" (2024-04-08 10:30)\n'
        '  • Se cambió nombre de persona "Juan García" → "Juan García López" (razón: corrección ortografía)\n'
        '  • Se desactivó acceso a "maria@sena.edu.co" (razón: baja de programa)\n'
        '  • Se eliminó registro de acceso duplicado (ID 12345)\n'
        '  • Se editó horario de apertura: 6:00 → 6:30')
    
    doc.add_paragraph()
    
    add_paragraph_justified(doc,
        'Para ver auditoría:\n'
        '  1. Click en "AUDITORÍA" o "HISTORIAL DE CAMBIOS"\n'
        '  2. Filtrar por:\n'
        '     - Usuario que hizo cambio\n'
        '     - Rango de fechas\n'
        '     - Tipo de cambio (creación, edición, eliminación)\n'
        '     - Qué se modificó\n'
        '  3. Click en un registro para ver detalles completos')
    
    doc.add_paragraph()
    
    add_paragraph_justified(doc,
        '⚠️ CASOS DE USO:\n'
        '  • Investigar: ¿Quién eliminó ese registro?\n'
        '  • Revertir: ¿Qué datos había antes del cambio?\n'
        '  • Seguridad: ¿Hubo cambios anormales?\n'
        '  • Responsabilidad: Cada acción tiene autor')
    
    doc.add_page_break()
    
    add_heading_styled(doc, 'Tareas Críticas del Administrador', 2)
    
    add_paragraph_justified(doc,
        'Un administrador debe realizar estas tareas regularmente:')
    
    doc.add_paragraph()
    
    critical_tasks = [
        ('🌅 PRIMERA COSA (Cada Mañana)',
         '  ✓ Verificar que el sistema esté UP (encendido y funcionando)\n'
         '  ✓ Probar el lector de código de barras\n'
         '  ✓ Revisar alertas de la noche\n'
         '  ✓ Confirmar conexión a internet'),
        
        ('👥 SEMANALMENTE',
         '  ✓ Revisar personas nuevas registradas\n'
         '  ✓ Desactivar visitantes cuya autorización venció\n'
         '  ✓ Verificar auditoría de cambios\n'
         '  ✓ Contactar a nuevos usuarios para confirmar cuenta'),
        
        ('📊 MENSUALMENTE',
         '  ✓ Generar reportes de asistencia\n'
         '  ✓ Revisar estadísticas de ocupación\n'
         '  ✓ Analizar patrones de seguridad\n'
         '  ✓ Hacer respaldo de datos\n'
         '  ✓ Revisar auditoría completa del mes'),
        
        ('🔐 CADA 3 MESES',
         '  ✓ Cambiar contraseña del SuperAdmin\n'
         '  ✓ Revisar permisos de usuarios (tienen lo necesario?)\n'
         '  ✓ Verificar respaldos están completos\n'
         '  ✓ Reportar estadísticas a directivas'),
        
        ('🚨 CUANDO OCURRAN EVENTOS',
         '  ✓ Intento de acceso denegado: Investigar\n'
         '  ✓ Fallo de sistema: Reiniciar, revisar logs\n'
         '  ✓ Fallo de seguridad: Alertar a dirección, cambiar contraseñas\n'
         '  ✓ Llegada de visitante nuevo: Verificar autorización'),
    ]
    
    for task_title, task_list in critical_tasks:
        p = doc.add_paragraph()
        run = p.add_run(task_title + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 82, 0)
        p.add_run(task_list)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_page_break()
    
    # ==== CONCLUSIÓN ====
    add_heading_styled(doc, 'Conclusión: Los Tres Mundos del Sistema', 1)
    
    add_paragraph_justified(doc,
        'El Sistema de Control de Ingresos SENA tiene tres módulos completamente separados e independientes, '
        'cada uno con su propósito específico:')
    
    doc.add_paragraph()
    
    conclusion = [
        ('🎯 MÓDULO DE INGRESO',
         'Es lo que ven los aprendices todos los días. Rápido, simple, automático. '
         'Solo escanear y pasar. No requiere entrenamiento especial. El 99% de usuarios del sistema pasan por aquí.'),
        
        ('👮 MÓDULO DE VIGILANCIA',
         'Es la pantalla del vigilante. Monitoreo en tiempo real, alertas, control de acceso. '
         'Requiere vigilancia constante y rápida reacción ante anomalías. El vigilante es los "ojos" del sistema.'),
        
        ('🛡️ MÓDULO DE ADMINISTRACIÓN',
         'Es el "corazón" del sistema. Aquí se configura todo, se registran personas, se generan reportes, '
         'se audita todo. Requiere cuidado, responsabilidad y conocimiento. Es el poder total del sistema.'),
    ]
    
    for module_title, module_desc in conclusion:
        p = doc.add_paragraph()
        run = p.add_run(module_title + '\n')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 82, 0)
        run.font.size = Pt(13)
        p.add_run(module_desc)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph()
    
    doc.add_paragraph()
    
    add_paragraph_justified(doc,
        'Los tres módulos trabajan juntos: Los aprendices ingresan (módulo 1), el vigilante ve en tiempo real (módulo 2), '
        'y el administrador gestiona todo detrás (módulo 3). Es un sistema integrado y completo.')
    
    doc.add_paragraph()
    doc.add_paragraph()
    
    final = doc.add_paragraph('Sistema de Control de Ingresos SENA - Centro de Formación\n© 2026')
    final.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in final.runs:
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(120, 120, 120)
    
    # ==== GUARDAR ====
    output_path = r'C:\Users\AMAT\Desktop\ingreso de aprendices\INFORME_SISTEMA_INGRESOS_MODULAR.docx'
    doc.save(output_path)
    print(f'✅ Documento guardado en: {output_path}')
    print(f'📄 Archivo: INFORME_SISTEMA_INGRESOS_MODULAR.docx')
    print(f'📊 Estructura: INGRESO > VIGILANCIA > ADMINISTRACIÓN')

if __name__ == '__main__':
    main()
