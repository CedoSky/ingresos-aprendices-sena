#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para actualizar todos los nombres existentes en la BD a MAYÚSCULAS
Ejecutar: python actualizar_nombres_mayusculas.py
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from app import create_app, db
from models import Persona

def actualizar_nombres_a_mayusculas():
    """Actualiza todos los nombres de personas a mayúsculas"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("\n" + "="*70)
            print("🔄 INICIANDO ACTUALIZACIÓN DE NOMBRES A MAYÚSCULAS")
            print("="*70)
            
            # Obtener todas las personas (incluyendo eliminadas lógicamente)
            personas = Persona.query.all()
            
            if not personas:
                print("✅ No hay personas registradas. Nada que actualizar.")
                return
            
            print(f"\n📋 Total de personas encontradas: {len(personas)}")
            print("-" * 70)
            
            actualizadas = 0
            sin_cambios = 0
            
            for persona in personas:
                if persona.nombre:
                    nombre_original = persona.nombre
                    nombre_mayuscula = nombre_original.upper()
                    
                    if nombre_original != nombre_mayuscula:
                        persona.nombre = nombre_mayuscula
                        actualizadas += 1
                        print(f"✏️  '{nombre_original}' → '{nombre_mayuscula}'")
                    else:
                        sin_cambios += 1
            
            # Guardar cambios
            if actualizadas > 0:
                print("\n" + "-" * 70)
                print(f"💾 Guardando {actualizadas} cambios en la base de datos...")
                db.session.commit()
                print("✅ Cambios guardados exitosamente")
            else:
                print("\n" + "-" * 70)
                print("ℹ️  Todos los nombres ya estaban en mayúsculas")
            
            print("\n" + "="*70)
            print("📊 RESUMEN:")
            print(f"  • Total de personas: {len(personas)}")
            print(f"  • Actualizadas: {actualizadas}")
            print(f"  • Sin cambios: {sin_cambios}")
            print("="*70)
            print("✅ Actualización completada\n")
            
        except Exception as e:
            print(f"\n❌ Error durante la actualización: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    actualizar_nombres_a_mayusculas()
