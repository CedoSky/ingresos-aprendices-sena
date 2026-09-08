#!/usr/bin/env python3
"""Verificar que los cambios de herramientas se aplicaron correctamente"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def verificar_html():
    """Verificar el archivo administracion.html"""
    html_path = os.path.join(BASE_DIR, 'frontend', 'administracion.html')
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n=== VERIFICACION DE administracion.html ===\n")
    
    # Verificar que las funciones JavaScript están definidas
    funciones = [
        'rotarPinSecreto',
        'obtenerEstadisticsasSistema',
        'verCountersActuales',
        'verAuditoriaReciente',
        'verUltimosAccesos',
        'listarUsuariosActivos',
        'listarSesionesActivas',
        'cerrarTodosSesiones',
        'restablecerPasswordRandom',
        'verUltimosLogs',
        'limpiarLogs',
        'verUsoDisco',
        'limpiarCacheAvanzado'
    ]

    faltantes = []
    for func in funciones:
        if f'async function {func}' not in content:
            faltantes.append(func)

    if faltantes:
        print(f"ERROR: Funciones sin definir: {', '.join(faltantes)}")
    else:
        print("OK: Todas las funciones JavaScript estan definidas")

    # Verificar estructura HTML
    if 'Seguridad y Control de Acceso' in content:
        print("OK: Nueva seccion de herramientas encontrada")
    else:
        print("ERROR: Nueva seccion de herramientas NO encontrada")
        
    if 'Generar PIN de Acceso' not in content:
        print("OK: Antigua seccion de 'Generar PIN' removida")
    else:
        print("ERROR: Antigua seccion de 'Generar PIN' sigue presente")

    # Verificar botones principales
    botones = [
        'Rotar Secreto',
        'Estadísticas',
        'Contadores',
        'Auditoría',
        'Últimos Accesos',
        'Usuarios Activos',
        'Sesiones Activas'
    ]
    
    print("\nBotones encontrados:")
    for boton in botones:
        if boton in content:
            print(f"  - {boton}: OK")
        else:
            print(f"  - {boton}: FALTANTE")

def verificar_routes():
    """Verificar el archivo routes.py"""
    routes_path = os.path.join(BASE_DIR, 'backend', 'routes.py')
    
    with open(routes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n=== VERIFICACION DE routes.py ===\n")
    
    endpoints = [
        '/admin/rotar-pin-secreto',
        '/admin/estadisticas-sistema',
        '/admin/system-counters',
        '/admin/auditoria-reciente',
        '/admin/ultimos-accesos',
        '/admin/usuarios-activos',
        '/admin/sesiones-activas',
        '/admin/cerrar-todas-sesiones',
        '/admin/resetear-password',
        '/admin/logs-recientes',
        '/admin/limpiar-logs',
        '/admin/uso-disco',
        '/admin/limpiar-cache-avanzado'
    ]
    
    print("Endpoints encontrados:")
    for endpoint in endpoints:
        if endpoint in content:
            print(f"  - {endpoint}: OK")
        else:
            print(f"  - {endpoint}: FALTANTE")

if __name__ == '__main__':
    try:
        verificar_html()
        verificar_routes()
        print("\n========================================")
        print("VERIFICACION COMPLETADA")
        print("========================================\n")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
