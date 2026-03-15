#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para llenar la base de datos con datos de prueba
"""
import os
import sys
from datetime import datetime

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import Usuario, Persona, Computador, RegistroAcceso

def populate_data():
    app = create_app()
    
    with app.app_context():
        print("[*] Limpiando datos previos...")
        
        # No eliminar usuarios admin
        Persona.query.delete()
        Computador.query.delete()
        RegistroAcceso.query.delete()
        
        print("[OK] Datos anteriores eliminados")
        
        # Crear personas de prueba
        personas_data = [
            {
                'nombre': 'Juan Carlos Rodríguez',
                'tipo_doc': 'CC',
                'numero_doc': '1023456789',
                'email': 'juan.rodriguez@sena.edu.co',
                'perfil': 'APRENDIZ',
                'programa': 'Técnico en Sistemas',
                'ficha': '2024001',
                'especialidad': 'Desarrollo Web',
                'area': 'Tecnología'
            },
            {
                'nombre': 'María González López',
                'tipo_doc': 'CC',
                'numero_doc': '1087654321',
                'email': 'maria.gonzalez@sena.edu.co',
                'perfil': 'APRENDIZ',
                'programa': 'Técnico en Sistemas',
                'ficha': '2024001',
                'especialidad': 'Bases de Datos',
                'area': 'Tecnología'
            },
            {
                'nombre': 'Carlos Mendoza Pérez',
                'tipo_doc': 'CC',
                'numero_doc': '1098765432',
                'email': 'carlos.mendoza@sena.edu.co',
                'perfil': 'APRENDIZ',
                'programa': 'Técnico en Administración',
                'ficha': '2024002',
                'especialidad': 'Gestión Empresarial',
                'area': 'Administración'
            },
            {
                'nombre': 'Ana Patricia Flores',
                'tipo_doc': 'CC',
                'numero_doc': '1056789012',
                'email': 'ana.flores@sena.edu.co',
                'perfil': 'INSTRUCTOR',
                'programa': 'Técnico en Sistemas',
                'especialidad': 'Programación',
                'area': 'Tecnología'
            },
            {
                'nombre': 'Pedro Sánchez Gutiérrez',
                'tipo_doc': 'CC',
                'numero_doc': '1045678901',
                'email': 'pedro.sanchez@sena.edu.co',
                'perfil': 'INSTRUCTOR',
                'programa': 'Técnico en Administración',
                'especialidad': 'Recursos Humanos',
                'area': 'Administración'
            },
            {
                'nombre': 'Roberto Fuentes',
                'tipo_doc': 'CC',
                'numero_doc': '1012341234',
                'email': 'roberto.fuentes@sena.edu.co',
                'perfil': 'VISITANTE',
                'programa': 'Consultoría Externa',
                'especialidad': 'TIC',
                'area': 'Visitantes'
            }
        ]
        
        print("[*] Creando personas de prueba...")
        for datos in personas_data:
            # Verificar si ya existe
            existe = Persona.query.filter_by(numero_doc=datos['numero_doc']).first()
            if not existe:
                persona = Persona(**datos)
                db.session.add(persona)
                print(f"  [OK] {datos['nombre']}")
        
        db.session.commit()
        print(f"[OK] Se crearon {len(personas_data)} personas")
        
        # Crear computadores de prueba
        computadores_data = [
            {
                'codigo_barras': 'LAPTOP001',
                'marca': 'Dell',
                'modelo': 'Inspiron 15',
                'serie': 'ABC123456',
                'tipo': 'LAPTOP',
                'ubicacion': 'Sala 101',
                'estado': 'activo'
            },
            {
                'codigo_barras': 'LAPTOP002',
                'marca': 'HP',
                'modelo': 'Pavilion 14',
                'serie': 'DEF789012',
                'tipo': 'LAPTOP',
                'ubicacion': 'Sala 102',
                'estado': 'activo'
            },
            {
                'codigo_barras': 'LAPTOP003',
                'marca': 'Lenovo',
                'modelo': 'IdeaPad 3',
                'serie': 'GHI345678',
                'tipo': 'LAPTOP',
                'ubicacion': 'Sala 103',
                'estado': 'activo'
            },
            {
                'codigo_barras': 'PC001',
                'marca': 'ASUS',
                'modelo': 'VivoBook',
                'serie': 'JKL901234',
                'tipo': 'COMPUTADOR',
                'ubicacion': 'Sala 201',
                'estado': 'activo'
            },
            {
                'codigo_barras': 'TABLET001',
                'marca': 'Samsung',
                'modelo': 'Galaxy Tab',
                'serie': 'MNO567890',
                'tipo': 'TABLET',
                'ubicacion': 'Sala 301',
                'estado': 'activo'
            }
        ]
        
        print("[*] Creando computadores de prueba...")
        for datos in computadores_data:
            existe = Computador.query.filter_by(codigo_barras=datos['codigo_barras']).first()
            if not existe:
                computador = Computador(**datos)
                db.session.add(computador)
                print(f"  [OK] {datos['marca']} {datos['modelo']} ({datos['codigo_barras']})")
        
        db.session.commit()
        print(f"[OK] Se crearon {len(computadores_data)} computadores")
        
        # Registrar algunos accesos de prueba
        print("[*] Creando registros de acceso de prueba...")
        
        personas = Persona.query.limit(3).all()
        for i, persona in enumerate(personas):
            registro = RegistroAcceso(
                persona_id=persona.id,
                numero_doc=persona.numero_doc,
                tipo='ENTRADA' if i % 2 == 0 else 'SALIDA',
                ambiente='Sala 101'
            )
            db.session.add(registro)
            print(f"  [OK] Acceso para {persona.nombre}")
        
        db.session.commit()
        print("[OK] Se crearon registros de acceso")
        
        print("\n" + "="*60)
        print("[SUCCESS] BASE DE DATOS POBLADA CON EXITO")
        print("="*60)
        print("\n[INFO] Estadísticas:")
        print(f"  * Personas: {Persona.query.count()}")
        print(f"  * Computadores: {Computador.query.count()}")
        print(f"  * Registros Acceso: {RegistroAcceso.query.count()}")
        print(f"  * Usuarios: {Usuario.query.count()}")
        print("\n[AUTH] Credenciales de Prueba:")
        print("  Email: admin@sena.edu.co")
        print("  Password: admin123")
        print("\n[DATA] Datos de Personas (número_doc):")
        for p in personas_data:
            print(f"  * {p['numero_doc']} - {p['nombre']}")

if __name__ == '__main__':
    populate_data()
