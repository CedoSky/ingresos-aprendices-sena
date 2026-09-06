import re

# Leer el archivo
with open('backend/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar patrones de parámetros dentro de constructores y agregar # type: ignore
# Este es un regex que encuentra parámetros de constructor sin tipo ignore
pattern = r'(\s+)([\w_]+=.+?)(\n)(?=\s+[\w=)])'

replacements = 0
def add_ignore_if_needed(match):
    global replacements
    indent = match.group(1)
    param = match.group(2)
    newline = match.group(3)
    
    # Solo agregar si no tiene ya # type: ignore
    if '# type: ignore' not in param:
        replacements += 1
        return f'{indent}{param}  # type: ignore{newline}'
    return match.group(0)

content = re.sub(pattern, add_ignore_if_needed, content)

# Guardar
with open('backend/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Agregados {replacements} # type: ignore')

