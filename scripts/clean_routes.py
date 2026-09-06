#!/usr/bin/env python3
"""Limpiar el archivo routes.py eliminar el BOM """

import os

# Move to project root first
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)

# Leer el archivo en binario
with open('backend/routes.py', 'rb') as f:
    raw = f.read()

# Investigar qué hay al inicio
print(f"Longitud del archivo: {len(raw)} bytes")
print(f"Primeros 20 bytes (hex): {raw[:20].hex()}")

# Decodificar como UTF-8 ignorando errores, esto debería saltar el BOM
try:
    text = raw.decode('utf-8-sig')
    print("✓ Decodificado con utf-8-sig")
except:
    text = raw.decode('utf-8', errors='replace')
    print("✓ Decodificado con utf-8 (con errores reemplazados)")

# Escribir limpio sin BOM
with open('backend/routes.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("✅ Archivo reescrito sin BOM")

# Verificar
with open('backend/routes.py', 'rb') as f:
    check = f.read(10).hex()
    print(f"Primeros 10 bytes después (hex): {check}")
