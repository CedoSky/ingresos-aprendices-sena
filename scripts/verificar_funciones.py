#!/usr/bin/env python3

import re

# Leer el archivo HTML
with open('frontend/vigilancia.html', 'r', encoding='utf-8') as f:
    contenido = f.read()

# Verificar que las funciones antiguas que se esperan sean llamadas aún existan
funciones_requeridas = [
    "abrirModalAmbientes",  # Compatibilidad hacia atrás
    "liberarAmb",           # Acción en tabla
    "abrirTraslado",        # Acción en tabla
    "forceAbrirCerradura",  # Control manual
    "forceCloseCerradura",  # Control manual
    "cargarAmbientes",      # Carga de datos
    "cargarIntentosCerradura",  # Carga de intentos
]

print("🔍 Verificación de funciones requeridas\n")
print("=" * 60)

todos_ok = True
for func in funciones_requeridas:
    patron = f"function {func}\\("
    existe = bool(re.search(patron, contenido))
    estado = "✅" if existe else "❌"
    print(f"{estado} Función '{func}' existe")
    if not existe:
        todos_ok = False

print("=" * 60)

# Verificar que no haya referencias a elementos eliminados
elementos_eliminados = [
    'id="mbody-amb"',  # Este elemento fue eliminado
]

print("\n🔍 Verificación de elementos eliminados\n")
print("=" * 60)

for elem in elementos_eliminados:
    if elem in contenido:
        print(f"⚠️  Advertencia: '{elem}' aún presente en el código")
        print("   (Se usa por la función antigua - esto podría causar problemas)")

print("=" * 60)

if todos_ok:
    print("\n✅ Todas las funciones requeridas existen")
else:
    print("\n❌ Faltan algunas funciones")
