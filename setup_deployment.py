#!/usr/bin/env python3
"""
Script de configuración para deployment
Ayuda a preparar la app para la nube
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_step(num, text):
    print(f"[{num}] {text}")

def run_command(cmd, description=""):
    """Ejecuta un comando y muestra su estado"""
    if description:
        print(f"    → {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    ✓ Éxito")
            return True
        else:
            print(f"    ✗ Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False

def generate_secret():
    """Genera una clave secreta aleatoria"""
    import secrets
    return secrets.token_hex(32)

def setup_env_file():
    """Crea archivo .env si no existe"""
    print_step(1, "Configurar archivo .env")
    
    env_file = Path(".env")
    if env_file.exists():
        print("    ℹ .env ya existe")
        return True
    
    example_file = Path(".env.example")
    if not example_file.exists():
        print("    ✗ No se encuentra .env.example")
        return False
    
    # Leer .env.example
    content = example_file.read_text()
    
    # Reemplazar valores por defecto
    replacements = {
        "SECRET_KEY=cambiar_esto_por_valor_aleatorio_largo": f"SECRET_KEY={generate_secret()}",
        "JWT_SECRET_KEY=cambiar_esto_por_valor_aleatorio_largo": f"JWT_SECRET_KEY={generate_secret()}",
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Escribir .env
    env_file.write_text(content)
    print("    ✓ Archivo .env creado")
    return True

def check_git():
    """Verifica si Git está instalado"""
    print_step(2, "Verificar Git")
    
    result = subprocess.run("git --version", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"    ✓ {result.stdout.strip()}")
        return True
    else:
        print("    ✗ Git no está instalado")
        print("    → Descargalo de: https://git-scm.com/download/win")
        return False

def init_git():
    """Inicializa repositorio Git"""
    print_step(3, "Inicializar repositorio Git")
    
    git_dir = Path(".git")
    if git_dir.exists():
        print("    ℹ Repositorio Git ya existe")
        return True
    
    run_command("git init", "Inicializar Git")
    run_command('git config user.name "SENA Development"', "Configurar usuario Git")
    run_command('git config user.email "dev@sena.edu.co"', "Configurar email Git")
    run_command("git add .", "Agregar archivos")
    run_command('git commit -m "Initial commit: Sistema SENA de ingresos y salidas"', 
                "Hacer commit inicial")
    
    print("\n    ✓ Repositorio Git listo")
    return True

def check_dependencies():
    """Verifica dependencias Python"""
    print_step(4, "Verificar dependencias Python")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("    ✗ Carpeta 'backend' no encontrada")
        return False
    
    # Instalar dependencias
    run_command(f"{sys.executable} -m pip install --upgrade pip", 
                "Actualizar pip")
    
    req_file = backend_dir / "requirements.txt"
    if req_file.exists():
        run_command(f"{sys.executable} -m pip install -r {req_file}",
                    "Instalar dependencias (esto puede tardar...)")
        print("    ✓ Dependencias instaladas")
        return True
    else:
        print("    ✗ requirements.txt no encontrado")
        return False

def test_app():
    """Prueba que la app inicia correctamente"""
    print_step(5, "Verificar que la app funciona")
    
    backend_dir = Path("backend")
    if not (backend_dir / "app.py").exists():
        print("    ✗ backend/app.py no encontrado")
        return False
    
    # Verificar imports
    test_code = """
import sys
sys.path.insert(0, 'backend')
from app import app, db
print('✓ App imports OK')
"""
    
    result = subprocess.run(f"{sys.executable} -c \"{test_code}\"", 
                          shell=True, capture_output=True, text=True, timeout=10)
    
    if result.returncode == 0:
        print("    ✓ Imports verificados")
        return True
    else:
        print(f"    ✗ Error: {result.stderr}")
        return False

def print_next_steps():
    """Muestra próximos pasos"""
    print_header("PRÓXIMOS PASOS")
    
    print("""
1. CREAR REPOSITORIO EN GITHUB
   • Ve a https://github.com/new
   • Nombre: sena-ingresos-nube
   • Push local: git remote add origin https://github.com/TU_USER/sena-ingresos-nube.git
   • git push -u origin main

2. CREAR CUENTA EN RENDER
   • Regístrate en https://render.com (gratis)
   • Conecta tu GitHub

3. CREAR SERVICIO EN RENDER
   • New → Web Service
   • Selecciona tu repo
   • Configurar variables de entorno
   • Crear PostgreSQL
   
4. VER GUÍA COMPLETA
   • Lee DEPLOYMENT_GUIDE.md

5. PROBAR EN NUBE
   • curl https://tu-app.onrender.com/api/health
   • Verificar que funcione

    """)

def main():
    print_header("CONFIGURACIÓN PARA DEPLOYMENT")
    
    steps = [
        ("Configurar .env", setup_env_file),
        ("Verificar Git", check_git),
        ("Inicializar Git", init_git),
        ("Verificar dependencias", check_dependencies),
        ("Verificar app", test_app),
    ]
    
    results = []
    for i, (name, func) in enumerate(steps, 1):
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"    ✗ Error: {e}")
            results.append((name, False))
    
    # Resumen
    print_header("RESUMEN")
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    all_ok = all(r for _, r in results)
    
    if all_ok:
        print("\n🎉 ¡TODO LISTO PARA DEPLOYMENT!")
        print_next_steps()
        return 0
    else:
        print("\n⚠ Algunos pasos fallaron. Revisa los errores arriba.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
