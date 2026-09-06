#!/usr/bin/env python3
"""
Test rápido de verificación - Sintaxis y estructura
Valida que el código Python no tenga errores básicos
"""

import sys
import ast

def test_python_syntax(filename):
    """Verifica la sintaxis Python de un archivo."""
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            code = f.read()
        ast.parse(code)
        print(f"✅ {filename}: Sintaxis OK")
        return True
    except SyntaxError as e:
        print(f"❌ {filename}: Error de sintaxis en línea {e.lineno}")
        print(f"   {e.msg}")
        return False
    except Exception as e:
        print(f"❌ {filename}: {str(e)}")
        return False

def main():
    files_to_check = [
        "backend/routes.py",
        "backend/config.py",
        "backend/test_triac_connection.py",
    ]
    
    print("🔍 Verificando sintaxis Python...\n")
    
    results = []
    for filename in files_to_check:
        try:
            result = test_python_syntax(filename)
            results.append((filename, result))
        except FileNotFoundError:
            print(f"⚠️  {filename}: Archivo no encontrado")
            results.append((filename, False))
    
    print(f"\n📊 Resultado: {sum(1 for _, r in results if r)}/{len(results)} archivos OK")
    
    if all(r for _, r in results):
        print("\n✅ Todos los archivos tienen sintaxis válida")
        return 0
    else:
        print("\n❌ Hay errores de sintaxis. Revisa arriba.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
