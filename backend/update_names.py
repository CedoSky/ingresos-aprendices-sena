import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'sena.db')

# Primero listar tablas
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print('Tablas:')
for table in tables:
    print(f'  - {table[0]}')

# Encontrar la tabla que tiene columna nombre
for table_name in [t[0] for t in tables]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    column_names = [c[1] for c in columns]
    if 'nombre' in column_names:
        print(f'\n✓ Tabla con columna "nombre": {table_name}')
        
        # Actualizar
        cursor.execute(f'UPDATE {table_name} SET nombre = UPPER(nombre) WHERE nombre IS NOT NULL')
        conn.commit()
        
        cursor.execute(f'SELECT COUNT(*) FROM {table_name} WHERE nombre IS NOT NULL')
        total = cursor.fetchone()[0]
        print(f'✅ {total} nombres actualizados a MAYÚSCULAS en tabla "{table_name}"')

conn.close()
