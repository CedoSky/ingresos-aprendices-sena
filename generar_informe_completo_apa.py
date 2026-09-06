#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Informe Completo APA Séptima Edición
Sistema de Ingreso de Aprendices SENA + Desarrollo de Productos Electrónicos
"""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from datetime import datetime

# Colores SENA
SENA_DARK_GREEN = RGBColor(26, 82, 0)      # #1a5200
SENA_LIGHT_GREEN = RGBColor(57, 169, 0)    # #39A900
BLACK = RGBColor(0, 0, 0)
WHITE = RGBColor(255, 255, 255)
GRAY = RGBColor(200, 200, 200)

def shade_cell(cell, color):
    """Aplica color de fondo a una celda"""
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color)
    cell._element.get_or_add_tcPr().append(shading_elm)

def set_cell_vertical_alignment(cell, alignment):
    """Alinea el contenido verticalmente en una celda"""
    tc = cell._element
    tcPr = tc.get_or_add_tcPr()
    tcVAlign = OxmlElement('w:vAlign')
    tcVAlign.set(qn('w:val'), alignment)
    tcPr.append(tcVAlign)

def add_heading_apa(doc, text, level=1):
    """Agrega un encabezado con formato APA"""
    heading = doc.add_heading(text, level=level)
    para = heading.paragraph_format
    para.left_indent = Inches(0)
    para.line_spacing = 1.15
    para.space_before = Pt(12)
    para.space_after = Pt(6)
    
    for run in heading.runs:
        run.font.name = 'Calibri'
        if level == 1:
            run.font.size = Pt(26)
            run.font.bold = True
        elif level == 2:
            run.font.size = Pt(16)
            run.font.bold = True
        else:
            run.font.size = Pt(12)
            run.font.bold = True
    return heading

def add_paragraph_apa(doc, text, bold=False, italic=False, centered=False):
    """Agrega un párrafo con formato APA"""
    p = doc.add_paragraph(text)
    para = p.paragraph_format
    para.left_indent = Inches(0)
    para.first_line_indent = Inches(0.5)
    para.line_spacing = 1.5
    para.space_before = Pt(0)
    para.space_after = Pt(12)
    
    if centered:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.first_line_indent = Inches(0)
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    for run in p.runs:
        run.font.name = 'Calibri'
        run.font.size = Pt(12)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = BLACK
    
    return p

def create_portada(doc):
    """Crea la portada en formato APA"""
    # Espaciado
    for _ in range(8):
        doc.add_paragraph()
    
    # Título
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Sistema de Ingreso de Aprendices para el Servicio Nacional de Aprendizaje SENA")
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.name = 'Calibri'
    
    # Espaciado
    for _ in range(5):
        doc.add_paragraph()
    
    # Subtítulo
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Descripción de la Actividad: Desarrollo de Productos Electrónicos\n(Necesidad Local)")
    run.font.size = Pt(14)
    run.font.name = 'Calibri'
    
    # Espaciado
    for _ in range(8):
        doc.add_paragraph()
    
    # Información de institución
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info.add_run("SENA - Servicio Nacional de Aprendizaje\nCentro de Formación\nPrograma de Electrónica")
    run.font.size = Pt(12)
    run.font.name = 'Calibri'
    
    # Espaciado
    for _ in range(6):
        doc.add_paragraph()
    
    # Fecha
    fecha = doc.add_paragraph()
    fecha.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fecha.add_run(datetime.now().strftime("%B de %Y"))
    run.font.size = Pt(12)
    run.font.name = 'Calibri'
    
    # Salto de página
    doc.add_page_break()

def create_formatted_table(doc, headers, rows, col_widths=None):
    """Crea una tabla formateada con encabezados"""
    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    
    # Encabezados
    header_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        cell = header_cells[i]
        shade_cell(cell, '1a5200')  # Verde SENA oscuro
        set_cell_vertical_alignment(cell, 'center')
        
        # Limpiar celda
        cell.text = ''
        p = cell.paragraphs[0]
        p.text = header
        
        # Formato del encabezado
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para = p.paragraph_format
        para.space_before = Pt(6)
        para.space_after = Pt(6)
        
        for run in p.runs:
            run.font.bold = True
            run.font.size = Pt(11)
            run.font.color.rgb = WHITE
            run.font.name = 'Calibri'
    
    # Filas de datos
    for row_idx, row_data in enumerate(rows, 1):
        row_cells = table.rows[row_idx].cells
        for col_idx, cell_data in enumerate(row_data):
            cell = row_cells[col_idx]
            set_cell_vertical_alignment(cell, 'top')
            
            # Limpiar celda
            cell.text = ''
            p = cell.paragraphs[0]
            p.text = str(cell_data)
            
            # Formato de celda de datos
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            para = p.paragraph_format
            para.space_before = Pt(3)
            para.space_after = Pt(3)
            para.line_spacing = 1.2
            
            for run in p.runs:
                run.font.size = Pt(10)
                run.font.color.rgb = BLACK
                run.font.name = 'Calibri'
    
    # Ancho de columnas
    if col_widths:
        for idx, width in enumerate(col_widths):
            for row in table.rows:
                row.cells[idx].width = Inches(width)
    
    return table

def main():
    """Función principal para generar el informe completo"""
    
    doc = Document()
    
    # Configurar márgenes APA
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Portada
    create_portada(doc)
    
    # INTRODUCCIÓN
    add_heading_apa(doc, "Introducción", level=1)
    intro_text = """El Sistema de Ingreso de Aprendices para el Servicio Nacional de Aprendizaje (SENA) representa una solución integral diseñada para modernizar y optimizar los procesos de control de acceso en los centros de formación. Este informe presenta una descripción detallada de cómo funciona el sistema desde la perspectiva del usuario final, combinado con el análisis de la necesidad local de desarrollo de productos electrónicos que fundamenta su creación."""
    add_paragraph_apa(doc, intro_text)
    
    intro_text2 = """El presenté documento integra dos componentes principales: primero, el análisis exhaustivo de la necesidad identificada en el entorno productivo local relacionada con el desarrollo de productos electrónicos, y segundo, la descripción operativa del sistema implementado que responde a esta necesidad mediante tres módulos funcionales: ingreso de aprendices, vigilancia en tiempo real, y administración centralizada."""
    add_paragraph_apa(doc, intro_text2)
    
    # SECCIÓN 1: DESCRIPCIÓN DE LA ACTIVIDAD
    doc.add_page_break()
    add_heading_apa(doc, "1. Descripción de la Actividad: Desarrollo de Productos Electrónicos (Necesidad Local)", level=1)
    
    desc_intro = """La actividad de desarrollo de productos electrónicos surge de la necesidad identificada en el entorno productivo local. Los aprendices realiza una revisión exhaustiva del área de influencia del centro de formación para identificar necesidades de servicio y posibilidades de mejora en diferentes sectores económicos de la zona. Esta revisión permite identificar oportunidades donde se requiere personal capacitado en el área de electrónica."""
    add_paragraph_apa(doc, desc_intro)
    
    # 1.1 Planteamiento del Problema
    add_heading_apa(doc, "1.1 Planteamiento del Problema", level=2)
    
    p1_1 = """Los centros de formación SENA requieren sistemas modernos de control de acceso que integren tecnología electrónica, registro de información y administración centralizada. El contexto operativo actual presenta la necesidad urgente de automatizar el ingreso de aprendices, verificar identidades de forma confiable, registrar asistencia de manera precisa y generar reportes sin depender de procesos manuales propensos a errores."""
    add_paragraph_apa(doc, p1_1)
    
    p1_2 = """La solución propuesta consiste en el desarrollo de un sistema integrado con lectores de código de barras, bases de datos SQLite y comunicación en tiempo real mediante WebSockets. Este producto electrónico no solo resuelve la problemática inmediata de control de acceso, sino que contribuye significativamente al fortalecimiento de las competencias de los aprendices en electrónica, programación y desarrollo de soluciones IoT."""
    add_paragraph_apa(doc, p1_2)
    
    # 1.2 Antecedentes
    add_heading_apa(doc, "1.2 Antecedentes", level=2)
    
    p1_2a = """Históricamente, los centros de formación SENA han operado tradicionalmente con sistemas de registro manual de asistencia. Estos sistemas, aunque funcionales, presentaban importantes limitaciones en precisión, consistencia y accesibilidad de la información. La llegada de nuevas tecnologías como IoT, lectores RFID y sistemas web ha abierto posibilidades concretas para optimizar estos procesos de manera significativa."""
    add_paragraph_apa(doc, p1_2a)
    
    p1_2b = """Proyectos anteriores de automatización en otros centros de formación han demostrado tanto la viabilidad técnica como la operativa de soluciones similares. Adicionalmente, las políticas institucionales del SENA enfatizan fuertemente la innovación y el desarrollo de competencias tecnológicas en los aprendices, creando el marco propicio para este tipo de iniciativas. El presente proyecto construye sobre estas experiencias previas, incorporándolas en una solución adaptada a las necesidades específicas de la comunidad local."""
    add_paragraph_apa(doc, p1_2b)
    
    # 1.3 Objetivos
    add_heading_apa(doc, "1.3 Objetivos", level=2)
    
    p1_3a = """El objetivo general del proyecto es desarrollar un sistema electrónico integrado para el control de ingreso de aprendices que automatice procesos operativos y proporcione información en tiempo real a los paneles de vigilancia y administración. Este objetivo trasciende la simple automatización de un trámite, buscando crear una solución que mejore significativamente la calidad de los datos, la velocidad de respuesta y la capacidad de análisis institucional."""
    add_paragraph_apa(doc, p1_3a)
    
    p1_3b = """Los objetivos específicos del proyecto se organizan en torno a cuatro dimensiones: (1) Funcionalidad - implementar lectores de código de barras para identificación automática de aprendices; (2) Información - registrar datos completos de asistencia, hora de entrada y eventos especiales en una base de datos centralizada; (3) Acceso - proporcionar panel de vigilancia en tiempo real para monitoreo de ingresos y generación de alertas automáticas; y (4) Gestión - crear interfaces de administración para gestión de usuarios, configuración de permisos y generación de reportes personalizados."""
    add_paragraph_apa(doc, p1_3b)
    
    # 1.4 Alcance del Proyecto
    add_heading_apa(doc, "1.4 Alcance del Proyecto", level=2)
    
    p1_4a = """El alcance del proyecto incluye las siguientes funcionalidades: control de ingreso mediante lectura automática de código de barras, panel de vigilancia en tiempo real para monitoreo de eventos, administración de usuarios y permisos con control granular de acceso, y generación de reportes de asistencia en múltiples formatos. El sistema está diseñado para servir a los aprendices SENA como usuarios finales, a vigilantes y personal de seguridad como monitores en tiempo real, a administradores del centro como gestores de información, e instructores como consultores de asistencia."""
    add_paragraph_apa(doc, p1_4a)
    
    p1_4b = """Explícitamente, el proyecto no incluye en su primera fase: sistemas de reconocimiento biométrico facial, control de salida de aprendices, ni integración con terceros externos. El sistema opera en el entorno específico del centro de formación SENA, enfocándose en las áreas de ingreso, la oficina de vigilancia y la oficina administrativa. Estos límites se establecen para asegurar un alcance manejable, un cronograma realista y un producto que pueda ser entregado, probado y optimizado efectivamente."""
    add_paragraph_apa(doc, p1_4b)
    
    # 1.5 Materiales y Recursos
    add_heading_apa(doc, "1.5 Materiales y Recursos", level=2)
    
    p1_5a = """El proyecto requiere un conjunto diversificado de recursos tecnológicos organizados en varias categorías. En hardware de entrada, se necesitan lectores de código de barras profesionales, computadoras locales para ejecutar el sistema de ingreso y monitores de confirmación visual. Para la vigilancia, se requieren computadoras con acceso a la red corporativa, monitores de alta visibilidad y conexiones de red estables. La administración centralizada requiere un servidor o computadora dedicada para alojar la base de datos y computadoras administrativas con acceso controlado."""
    add_paragraph_apa(doc, p1_5a)
    
    p1_5b = """El software backend se desarrolla con Python 3.13, framework Flask 3.1.3, SQLite como motor de base de datos, y WebSockets para comunicación en tiempo real. El frontend utiliza HTML5, JavaScript moderno, Bootstrap para interfaces responsivas y CSS personalizado. La comunicación entre componentes se realiza mediante red Ethernet o WiFi, MQTT para dispositivos IoT como el ESP32, y protocolos estándar HTTP/HTTPS. La seguridad del sistema se implementa con JWT para autenticación de usuarios, encriptación con Fernet para datos sensibles, protección CSRF para formularios y SSL/TLS para todas las conexiones de red."""
    add_paragraph_apa(doc, p1_5b)
    
    # 1.6 Cronograma y Estimación de Tiempo
    add_heading_apa(doc, "1.6 Cronograma y Estimación de Tiempo", level=2)
    
    p1_6a = """El proyecto se desarrolla en seis fases principales con una duración total estimada de 12 a 16 semanas, aproximadamente tres a cuatro meses de trabajo continuo. La Fase 1 de Planificación (1-2 semanas) incluye la definición detallada de requisitos funcionales, análisis profundo de las necesidades reales y diseño de la arquitectura general del sistema. Esta fase es crítica para asegurar que posteriores desarrollos avancen en la dirección correcta."""
    add_paragraph_apa(doc, p1_6a)
    
    p1_6b = """La Fase 2 de Desarrollo Backend (3-4 semanas) se enfoca en la creación de la API Flask, definición de modelos de base de datos SQLite, implementación de autenticación JWT y medidas de seguridad. La Fase 3 de Desarrollo Frontend (3-4 semanas) incluye creación de interfaces HTML/JavaScript, integración con la API backend y pruebas de usabilidad. La Fase 4 de Integración IoT (2-3 semanas) cubre la programación del ESP32, comunicación MQTT y pruebas de hardware."""
    add_paragraph_apa(doc, p1_6b)
    
    p1_6c = """Las fases finales incluyen Fase 5 de Pruebas (2 semanas) con testing unitario, pruebas de integración y validación con usuarios finales, y Fase 6 de Despliegue (1 semana) que incluye instalación en producción, capacitación de usuarios y documentación final del proyecto. Esta estructura de fases permite validación temprana y ajustes rápidos si es necesario."""
    add_paragraph_apa(doc, p1_6c)
    
    # 1.7 Metodología de Trabajo
    add_heading_apa(doc, "1.7 Metodología de Trabajo", level=2)
    
    p1_7a = """El proyecto adopta una metodología ágil con iteraciones que duran dos semanas, permitiendo ajustes rápidos basados en feedback real. Se realizan reuniones de retrospectiva al final de cada iteración para identificar mejoras continuas y resolver problemas operativos. Este enfoque garantiza seguimiento constante del progreso y adaptación a cambios en requisitos o restricciones."""
    add_paragraph_apa(doc, p1_7a)
    
    p1_7b = """La revisión de necesidades se realiza mediante mesas redondas con todos los stakeholders - aprendices, vigilantes, administradores e instructores - para identificación colaborativa de requisitos funcionales y no funcionales. El diseño sigue un enfoque participativo donde usuarios finales contribuyen activamente en el diseño de interfaces para asegurar usabilidad práctica. Se desarrollan prototipos funcionales frecuentemente para validación temprana de conceptos antes de comprometer muchos recursos de desarrollo."""
    add_paragraph_apa(doc, p1_7b)
    
    p1_7c = """La validación es iterativa, realizando pruebas frecuentes con grupos reales de aprendices, vigilantes y administradores. La documentación se genera de manera progresiva a lo largo del proyecto, asegurando que la información esté actualizada y disponible cuando se necesita. Este enfoque integral combina rigor técnico con flexibilidad para responder a la realidad operativa del centro de formación."""
    add_paragraph_apa(doc, p1_7c)
    
    # 1.8 Procedimiento de Diseño y Validación de Proyectos
    add_heading_apa(doc, "1.8 Procedimiento de Diseño y Validación de Proyectos", level=2)
    
    p1_8a = """El procedimiento de diseño y validación del proyecto sigue un modelo estructurado en diez etapas progresivas. La Etapa 1 de Conceptualización establece una definición clara del problema, objetivos específicos y alcance del proyecto, identificando al mismo tiempo restricciones técnicas y presupuestarias. La Etapa 2 de Diseño Arquitectónico incluye la creación de diagramas de flujo detallados, arquitectura del sistema, diagramas de casos de uso y revisión técnica de la solución propuesta."""
    add_paragraph_apa(doc, p1_8a)
    
    p1_8b = """La Etapa 3 de Prototipado desarrolla prototipos de baja y alta fidelidad, realizando pruebas de concepto con tecnologías clave para validar viabilidad. La Etapa 4 de Diseño Detallado especifica componentes individuales, interfaces de usuario, algoritmos críticos y genera documentación técnica completa. La Etapa 5 de Implementación realiza codificación, desarrollo de interfaces, integración de módulos manteniendo control de versiones con Git."""
    add_paragraph_apa(doc, p1_8b)
    
    p1_8c = """Las pruebas se organizan en tres niveles: Etapa 6 de Pruebas Unitarias testea funciones individuales y valida lógica de negocio; Etapa 7 de Pruebas de Integración valida la interacción entre módulos y flujos completos; Etapa 8 de Pruebas de Usuario valida con usuarios finales, recopila feedback y realiza ajustes de experiencia. La Etapa 9 de Validación Final incluye pruebas de estrés, seguridad y desempeño, obteniendo aprobación final de stakeholders."""
    add_paragraph_apa(doc, p1_8c)
    
    p1_8d = """La Etapa 10 de Documentación genera toda la documentación requerida: manual de usuario, guía técnica para administradores, documentación completa de API para futuros desarrolladores y plan de soporte operativo. Esta estructura integral asegura que cada aspecto del proyecto recibe atención apropiada y que existe trazabilidad total desde concepto hasta validación final."""
    add_paragraph_apa(doc, p1_8d)
    
    # SECCIÓN 2: SISTEMA DE INGRESO DE APRENDICES
    doc.add_page_break()
    add_heading_apa(doc, "2. Sistema de Ingreso de Aprendices: Descripción Operativa del Producto Electrónico", level=1)
    
    sistema_intro = """El Sistema de Ingreso de Aprendices constituye la materialización tecnológica de los requisitos identificados en el análisis de necesidades locales. Se trata de una solución integral que implementa el proceso de control de acceso mediante tres módulos funcionales especializados: ingreso de aprendices, vigilancia en tiempo real, y administración centralizada. Cada módulo está optimizado para usuarios específicos y proporciona funcionalidades diferenciadas."""
    add_paragraph_apa(doc, sistema_intro)
    
    # MÓDULO 1: INGRESO
    add_heading_apa(doc, "2.1 Módulo 1: Ingreso de Aprendices", level=2)
    
    add_heading_apa(doc, "2.1.1 Flujo de Ingreso", level=3)
    table_flujo = [
        ["1. Llegada", "El aprendiz se acerca al punto de ingreso donde se encuentra el lector de código de barras."],
        ["2. Lectura", "El sistema lee el código de barras del carné del aprendiz de forma automática."],
        ["3. Identificación", "El código se valida contra la base de datos para identificar al aprendiz."],
        ["4. Registro", "Si la identificación es exitosa, se registra la hora exacta de ingreso."],
        ["5. Confirmación", "El sistema emite una confirmación visual y/o sonora al aprendiz."],
        ["6. Sincronización", "Los datos se sincronizan en tiempo real con los paneles de vigilancia y administración."]
    ]
    create_formatted_table(doc, ["Paso", "Descripción"], table_flujo, [0.8, 4.2])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.1.2 Componentes del Módulo de Ingreso", level=3)
    table_componentes_ingreso = [
        ["Lector Barras", "Dispositivo que captura el código de barras del carné del aprendiz."],
        ["Terminal Local", "Computadora conectada al lector que valida el código en la base de datos local."],
        ["Base de Datos Local", "Copia de la información de aprendices disponible sin conexión de red."],
        ["Interfaz Ingreso", "Pantalla simple que muestra confirmación de ingreso y mensajes al aprendiz."],
        ["Comunicación Real-Time", "WebSocket que transmite datos a vigilancia y administración instantáneamente."]
    ]
    create_formatted_table(doc, ["Componente", "Función"], table_componentes_ingreso, [1.2, 3.8])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.1.3 Mensajes y Notificaciones", level=3)
    table_mensajes = [
        ["✓ Ingreso Exitoso", "Mensaje en verde indicando que el aprendiz ingresó correctamente y la hora registrada."],
        ["⚠ Ingreso Pendiente", "Color amarillo cuando hay información que requiere atención."],
        ["✗ Carné No Reconocido", "Mensaje en rojo si el código no existe en el sistema."],
        ["📱 Conectado/Desconectado", "Indicador de estado de conexión con los servidores de vigilancia y administración."]
    ]
    create_formatted_table(doc, ["Tipo Mensaje", "Descripción"], table_mensajes, [1.5, 3.5])
    doc.add_paragraph()
    
    # MÓDULO 2: VIGILANCIA
    add_heading_apa(doc, "2.2 Módulo 2: Panel de Vigilancia en Tiempo Real", level=2)
    
    add_heading_apa(doc, "2.2.1 Acceso y Función Principal", level=3)
    table_vigilancia_acceso = [
        ["Usuario", "Personal de vigilancia/seguridad del centro SENA."],
        ["Acceso", "Monitor en oficina de vigilancia con conexión a la red del centro."],
        ["Función Principal", "Monitorear ingresos de aprendices en tiempo real y recibir alertas de eventos especiales."],
        ["Datos Visualizados", "Lista en vivo de ingresos, hora exacta, estado de aprendices, alertas y notificaciones."],
        ["Responsabilidad", "Supervisar integridad del proceso, investigar anomalías, registrar eventos especiales."]
    ]
    create_formatted_table(doc, ["Aspecto", "Detalle"], table_vigilancia_acceso, [1.2, 3.8])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.2.2 Componentes Principales del Panel", level=3)
    table_comp_vigilancia = [
        ["Feed en Vivo", "Flujo de ingresos mostrado en tiempo real con nombre, hora, foto del aprendiz."],
        ["Alertas", "Notificaciones destacadas para ingresos tardíos, ingresos repetidos, o visitantes no autorizados."],
        ["Historial de Sesión", "Registro del día actual con todos los ingresos, permite búsqueda por nombre o hora."],
        ["Control Puerta", "Botón para control manual de cerraduras (si está integrado el sistema smart lock)."],
        ["Reportes", "Acceso rápido a reportes de asistencia del día o periodos específicos."]
    ]
    create_formatted_table(doc, ["Componente", "Función"], table_comp_vigilancia, [1.2, 3.8])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.2.3 Tipos de Alertas en Vigilancia", level=3)
    table_alertas = [
        ["Ingreso Tardío", "Se destaca cuando un aprendiz ingresa fuera del horario permitido."],
        ["Ingreso Repetido", "Alerta si el mismo carné se registra múltiples veces en corto tiempo (posible fraude)."],
        ["Visitante", "Notificación cuando ingresa personal que no es aprendiz (proveedores, invitados)."],
        ["Puerta Forzada", "Alerta si se detecta apertura sin lectura de código de barras."],
        ["Desconexión", "Notificación si el sistema pierde conexión con el punto de ingreso."]
    ]
    create_formatted_table(doc, ["Tipo Alerta", "Trigger/Activador"], table_alertas, [1.2, 3.8])
    doc.add_paragraph()
    
    # MÓDULO 3: ADMINISTRACIÓN
    add_heading_apa(doc, "2.3 Módulo 3: Panel de Administración Centralizada", level=2)
    
    add_heading_apa(doc, "2.3.1 Tipos de Administrador", level=3)
    table_admin_tipos = [
        ["Admin Principal", "Control total del sistema, gestión de todos los usuarios, reportes estratégicos."],
        ["Coordinador Grupos", "Gestión de aprendices en grupos específicos, reportes de su grupo."],
        ["Instructor", "Acceso a reportes de asistencia de sus grupos, información de aprendices."],
        ["Vigilante Supervisor", "Acceso extendido a reportes y estadísticas de vigilancia."]
    ]
    create_formatted_table(doc, ["Rol", "Responsabilidades"], table_admin_tipos, [1.5, 3.5])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.3.2 Gestión de Usuarios y Permisos", level=3)
    table_gestion_usuarios = [
        ["Crear Aprendiz", "Registro de nuevo aprendiz con nombre, documento, foto, grupo, horario."],
        ["Crear Personal", "Registro de vigilantes, coordinadores, instructores con permisos específicos."],
        ["Asignar Permisos", "Definición granular de qué funciones puede acceder cada usuario."],
        ["Desactivar Usuario", "Opción para desactivar sin eliminar (caso de retiro de aprendiz)."],
        ["Auditoría", "Registro de quién modificó qué información y cuándo fue el cambio."]
    ]
    create_formatted_table(doc, ["Funcionalidad", "Descripción"], table_gestion_usuarios, [1.2, 3.8])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.3.3 Gestión de Personas (Aprendices)", level=3)
    table_gestion_personas = [
        ["Búsqueda", "Búsqueda rápida por nombre, documento, grupo o código de carné."],
        ["Información", "Visualización de datos completos: foto, documento, contacto, grupo, horarios."],
        ["Historial", "Acceso a registro histórico de ingresos y cambios en su perfil."],
        ["Carne Digital", "Visualización del código de barras asignado y datos del carné."],
        ["Estados", "Marcar como activo, inactivo, suspendido o especializado (ej: personas con discapacidad)."]
    ]
    create_formatted_table(doc, ["Función", "Detalle"], table_gestion_personas, [1.2, 3.8])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.3.4 Registro de Acceso y Reportes de Asistencia", level=3)
    table_registro = [
        ["Filtros", "Por aprendiz, grupo, rango de fechas, hora específica, tipo de evento."],
        ["Datos", "Hora de ingreso, nombre, documento, grupo, si fue ingreso normal o con alerta."],
        ["Exportación", "Descargar en Excel, PDF o texto para análisis externo."],
        ["Gráficas", "Visualización de tendencias de asistencia, horarios pico, porcentaje de puntualidad."],
        ["Reporte Periódico", "Generación automática de reportes diarios/semanales/mensuales."]
    ]
    create_formatted_table(doc, ["Aspecto", "Descripción"], table_registro, [1.2, 3.8])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.3.5 Búsqueda Avanzada", level=3)
    table_busqueda = [
        ["Por Aprendiz", "Ingresa nombre o número de documento para ver todos sus registros."],
        ["Por Grupo", "Selecciona un grupo de formación para ver asistencia completa del grupo."],
        ["Por Rango de Fechas", "Especifica período de análisis (ej: última semana, mes específico)."],
        ["Por Evento", "Filtrar solo ingresos normales, tardíos, con alerta o eventos especiales."],
        ["Exportar Resultados", "Descargar búsqueda en diferentes formatos para reportes."]
    ]
    create_formatted_table(doc, ["Tipo", "Uso"], table_busqueda, [1.2, 3.8])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.3.6 Generación de Reportes", level=3)
    table_reportes = [
        ["Reporte de Asistencia", "Por grupo, fecha, con indicadores de puntualidad."],
        ["Reporte de Ausencias", "Identificación de patrones de inasistencia, aprendices con problemas."],
        ["Reporte de Tardíos", "Análisis de atrasos por día, grupo, tendencias."],
        ["Reporte de Eventos", "Registro de todas las alertas y eventos especiales del período."],
        ["Reporte Ejecutivo", "Resumen de estadísticas para presentación a directiva."]
    ]
    create_formatted_table(doc, ["Tipo Reporte", "Contenido"], table_reportes, [1.2, 3.8])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.3.7 Descargar y Exportar Datos", level=3)
    table_descarga = [
        ["Formatos", "Excel (.xlsx), PDF, CSV, JSON para diferentes usos."],
        ["Contenido", "Seleccionar qué columnas incluir en la descarga."],
        ["Períodos", "Descargar datos de realidades específicas o períodos completos."],
        ["Automatización", "Opción de generar descargas automáticas en horarios específicos."],
        ["Almacenamiento", "Los descargas se guardan en servidor para recuperación posterior."]
    ]
    create_formatted_table(doc, ["Aspecto", "Detalle"], table_descarga, [1.2, 3.8])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.3.8 Configuración del Sistema", level=3)
    table_config = [
        ["Horarios", "Definición de horarios de ingreso permitido por grupos."],
        ["Alertas", "Configuración de qué eventos generan alertas en vigilancia."],
        ["Políticas", "Definición de políticas de acceso, tolerancia de retraso, etc."],
        ["Integración", "Configuración de conexiones con otros sistemas si es necesario."],
        ["Seguridad", "Cambio de contraseñas, actualización de certificados, configuración de backups."]
    ]
    create_formatted_table(doc, ["Configuración", "Descripción"], table_config, [1.2, 3.8])
    doc.add_paragraph()
    
    add_heading_apa(doc, "2.3.9 Tareas Críticas y Mantenimiento", level=3)
    table_tareas = [
        ["Backup", "Respaldo automático de base de datos, disponibilidad de restauración."],
        ["Logs de Auditoría", "Registro de todas las acciones para investigación de incidentes."],
        ["Sincronización", "Actualización de cambios entre módulos, garantiza consistencia de datos."],
        ["Limpieza de Datos", "Archivado de datos históricos, eliminación de registros obsoletos."],
        ["Respaldo a USB", "Opción de realizar respaldos en dispositivos USB para seguridad."]
    ]
    create_formatted_table(doc, ["Tarea", "Función"], table_tareas, [1.2, 3.8])
    doc.add_paragraph()
    
    # CONCLUSIÓN
    doc.add_page_break()
    add_heading_apa(doc, "3. Conclusión y Perspectiva Integrada", level=1)
    
    conclusion1 = """El Sistema de Ingreso de Aprendices para el Servicio Nacional de Aprendizaje SENA constituye una respuesta integral a la necesidad identificada de desarrollar una solución electrónica para el control de acceso en los centros de formación. El proyecto integra de manera coherente el análisis detallado de necesidades locales en el sector de productos electrónicos con la implementación de una plataforma tecnológica funcional y escalable."""
    add_paragraph_apa(doc, conclusion1)
    
    conclusion2 = """La solución presentada está estructurada en tres módulos perfectamente diferenciados pero integrados operativamente. El módulo de ingreso proporciona la interfaz de contacto inicial del aprendiz con el sistema, automatizando el proceso de identificación y registro. El módulo de vigilancia mantiene supervisión en tiempo real, facilitando la detección de anomalías y eventos especiales. El módulo de administración centraliza la gestión de información, permitiendo análisis estadísticos, generación de reportes y toma de decisiones informadas."""
    add_paragraph_apa(doc, conclusion2)
    
    conclusion3 = """Desde una perspectiva educativa, este proyecto contribuye significativamente al desarrollo de competencias de los aprendices en áreas críticas como programación backend con Python y Flask, desarrollo de interfaces con HTML/JavaScript, integración de sistemas de base de datos, seguridad informática, y desarrollo de soluciones IoT con microcontroladores. Además, proporciona una oportunidad de aprendizaje vivencial sobre gestión de proyectos, metodologías ágiles y validación de productos con usuarios reales."""
    add_paragraph_apa(doc, conclusion3)
    
    conclusion4 = """El sistema implementa mejores prácticas en seguridad informática mediante autenticación JWT, encriptación con Fernet, protección CSRF y validación de entrada de datos. La arquitectura escalable permite expansiones futuras, como integración de biometría, control de salida, o sincronización de múltiples sedes. La documentación completa y el código bien estructurado facilitan el mantenimiento y la transferencia de conocimiento a futuras generaciones de aprendices."""
    add_paragraph_apa(doc, conclusion4)
    
    conclusion5 = """En conclusión, el Sistema de Ingreso de Aprendices SENA representa un producto electrónico innovador que responde a una necesidad real, implementa tecnología de punta, facilita el aprendizaje competencial y demuestra la capacidad del SENA para desarrollar soluciones que mejoran significativamente los procesos institucionales. Este informe completo documenta tanto la justificación conceptual del proyecto como la operatividad práctica de la solución implementada."""
    add_paragraph_apa(doc, conclusion5)
    
    # Guardar documento
    import os
    import shutil
    
    final_path = r"C:\Users\AMAT\Desktop\ingreso de aprendices\INFORME_COMPLETO_APA_SEPTIMA_EDICION.docx"
    temp_output_path = r"C:\Users\AMAT\Desktop\ingreso de aprendices\INFORME_COMPLETO_TEMP.docx"
    
    # Guardar en temporal primero
    doc.save(temp_output_path)
    
    # Intentar renombrar/copiar
    try:
        if os.path.exists(final_path):
            os.remove(final_path)
        os.rename(temp_output_path, final_path)
    except:
        # Si no se puede remover, generar con nombre diferente
        from datetime import datetime as dt
        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        final_path = rf"C:\Users\AMAT\Desktop\ingreso de aprendices\INFORME_SISTEMA_{timestamp}.docx"
        if os.path.exists(temp_output_path):
            os.rename(temp_output_path, final_path)
    
    print("✅ INFORME COMPLETO APA SÉPTIMA EDICIÓN creado exitosamente")
    print(f"📄 Archivo: {os.path.basename(final_path)}")
    print(f"📊 Contenido: Necesidad Local + Sistema de Ingreso con PÁRRAFOS")
    print(f"📁 Ubicación: {final_path}")

if __name__ == "__main__":
    main()
