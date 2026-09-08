#!/usr/bin/env python3
"""Remover BOM agresivamente"""

# Leer en modo binario
with open('backend/routes.py', 'rb') as f:
    content = f.read()

print(f"Primeros 10 bytes: {content[:10]}")
print(f"Como hex: {content[:10].hex()}")

# Remover BOM si existe (UTF-8: EF BB BF)
if content.startswith(b'\xef\xbb\xbf'):
    print("BOM UTF-8 encontrado, removiendo...")
    content = content[3:]
    with open('backend/routes.py', 'wb') as f:
        f.write(content)
    print("✅ BOM removido")
elif content.startswith(b'\xff\xfe'):
    print("BOM UTF-16 LE encontrado, removiendo...")
    content = content[2:]
    with open('backend/routes.py', 'wb') as f:
        f.write(content)
    print("✅ BOM removido")
else:
    print("No se encontró BOM conocido")
    print(f"Primeros caracteres: {repr(content[:20])}")
