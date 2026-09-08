#!/usr/bin/env python3
"""Remover BOM de archivos Python"""

import os

files_to_check = [
    'backend/routes.py',
    'backend/app.py',
    'backend/models.py'
]

for filepath in files_to_check:
    if not os.path.exists(filepath):
        print(f'⚠️  {filepath} no existe')
        continue
    
    try:
        # Leer con utf-8-sig para detectar BOM
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # Escribir sin BOM
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f'✅ {filepath} - BOM removido/procesado')
    except Exception as e:
        print(f'❌ Error procesando {filepath}: {e}')

print('\nVerificación completada')
