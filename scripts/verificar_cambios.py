#!/usr/bin/env python3

import re
import os

# Move to project root first
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)

# Leer el archivo HTML
with open('frontend/vigilancia.html', 'r', encoding='utf-8') as f:
    contenido = f.read()

# Verificar cambios clave
checks = {
    "Modal combinado (id=ov-ambcerr)": r'id="ov-ambcerr"' in contenido,
    "Función abrirModalAmbientesConCerraduras": r'abrirModalAmbientesConCerraduras' in contenido,
    "Función cambiarTabAmbCerr": r'cambiarTabAmbCerr' in contenido,
    "Función cerrarOvAmbCerr": r'cerrarOvAmbCerr' in contenido,
    "Pestaña de Ambientes": r'tab-amb' in contenido,
    "Pestaña de Cerraduras": r'tab-cerr' in contenido,
    "renderModalAmbTabla": r'renderModalAmbTabla' in contenido,
}

print("🔍 Verificación de cambios en vigilancia.html\n")
print("=" * 50)

todos_ok = True
for nombre, resultado in checks.items():
    estado = "✅" if resultado else "❌"
    print(f"{estado} {nombre}")
    if not resultado:
        todos_ok = False

print("=" * 50)
if todos_ok:
    print("\n✅ Todos los cambios han sido implementados correctamente")
else:
    print("\n❌ Faltan algunos cambios")
