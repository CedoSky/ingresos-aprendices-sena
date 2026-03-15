"""
Script para inicializar la base de datos con datos de ejemplo
Ejecutar: python init_db.py
"""

from app import create_app
from models import db, Usuario, Persona, Computador
from werkzeug.security import generate_password_hash
from datetime import datetime

def init_database():
    """Crear tablas e insertar datos de ejemplo"""
    
    app = create_app('development')
    
    with app.app_context():
        print("[*] Creando tablas...")
        db.create_all()
        print("[OK] Tablas creadas")
        
        # Verificar si ya existen datos
        if Persona.query.count() > 0:
            print("[!] La base de datos ya contiene datos. Saltando insercion.")
            return
        
        print("\n[*] Insertando datos de ejemplo...\n")
        
        # Crear usuarios
        usuarios = [
            Usuario(
                email='admin@sena.edu.co',
                password_hash=generate_password_hash('admin123'),
                nombre='Administrador',
                rol='admin',
                activo=True
            ),
            Usuario(
                email='vigilante@sena.edu.co',
                password_hash=generate_password_hash('vigilante123'),
                nombre='Vigilante',
                rol='vigilante',
                activo=True
            ),
            Usuario(
                email='sistemas@sena.edu.co',
                password_hash=generate_password_hash('sistemas123'),
                nombre='Sistemas',
                rol='sistemas',
                activo=True
            )
        ]
        
        for u in usuarios:
            db.session.add(u)
        db.session.commit()
        print("[OK] 3 Usuarios creados")
        
        # Crear personas (aprendices)
        personas_data = [
            {
                'nombre': 'Juan Carlos López',
                'tipo_doc': 'CC',
                'numero_doc': '1023456789',
                'email': 'juan.lopez@sena.edu.co',
                'telefono': '3001234567',
                'perfil': 'aprendiz',
                'programa': 'Tecnología en Sistemas Informáticos',
                'ficha': '2404350',
                'especialidad': 'Desarrollo Web',
                'area': 'Programación'
            },
            {
                'nombre': 'María García Smith',
                'tipo_doc': 'CC',
                'numero_doc': '1087654321',
                'email': 'maria.garcia@sena.edu.co',
                'telefono': '3009876543',
                'perfil': 'aprendiz',
                'programa': 'Tecnología en Sistemas Informáticos',
                'ficha': '2404350',
                'especialidad': 'Redes',
                'area': 'Infraestructura'
            },
            {
                'nombre': 'Carlos Mendoza Ruiz',
                'tipo_doc': 'CC',
                'numero_doc': '1045678901',
                'email': 'carlos.mendoza@sena.edu.co',
                'telefono': '3005551234',
                'perfil': 'aprendiz',
                'programa': 'Tecnología en Sistemas Informáticos',
                'ficha': '2404351',
                'especialidad': 'Security',
                'area': 'Ciberseguridad'
            },
            {
                'nombre': 'Laura Fernández Díaz',
                'tipo_doc': 'CC',
                'numero_doc': '1065432187',
                'email': 'laura.fernandez@sena.edu.co',
                'telefono': '3002223333',
                'perfil': 'instructor',
                'programa': 'Tecnología en Sistemas Informáticos',
                'ficha': '2404350',
                'especialidad': 'Programación',
                'area': 'Desarrollo'
            },
            {
                'nombre': 'Diego Ramírez Torres',
                'tipo_doc': 'CC',
                'numero_doc': '1098765432',
                'email': 'diego.ramirez@sena.edu.co',
                'telefono': '3007774444',
                'perfil': 'visitante',
                'programa': 'Visitante Externo',
                'ficha': None,
                'especialidad': None,
                'area': None
            }
        ]
        
        for p_data in personas_data:
            p = Persona(**p_data, verificado=True)
            db.session.add(p)
        db.session.commit()
        print("[OK] {} Personas creadas".format(len(personas_data)))
        
        # Crear computadores
        computadores_data = [
            {
                'codigo_barras': 'PC-001',
                'serie': 'SN12345001',
                'marca': 'Dell',
                'modelo': 'Inspiron 15',
                'tipo': 'laptop',
                'ubicacion': 'PISO 1 - SALA 1',
                'estado': 'activo'
            },
            {
                'codigo_barras': 'PC-002',
                'serie': 'SN12345002',
                'marca': 'HP',
                'modelo': 'ProBook 450',
                'tipo': 'laptop',
                'ubicacion': 'PISO 1 - SALA 2',
                'estado': 'activo'
            },
            {
                'codigo_barras': 'PC-003',
                'serie': 'SN12345003',
                'marca': 'ASUS',
                'modelo': 'VivoBook 15',
                'tipo': 'laptop',
                'ubicacion': 'PISO 2 - SALA 1',
                'estado': 'activo'
            },
            {
                'codigo_barras': 'PC-004',
                'serie': 'SN12345004',
                'marca': 'Lenovo',
                'modelo': 'ThinkPad E15',
                'tipo': 'laptop',
                'ubicacion': 'PISO 2 - SALA 3',
                'estado': 'activo'
            },
            {
                'codigo_barras': 'PC-005',
                'serie': 'SN12345005',
                'marca': 'Apple',
                'modelo': 'MacBook Pro 14',
                'tipo': 'laptop',
                'ubicacion': 'PISO 3 - SALA 2',
                'estado': 'activo'
            }
        ]
        
        for c_data in computadores_data:
            c = Computador(**c_data)
            db.session.add(c)
        db.session.commit()
        print("[OK] {} Computadores creados".format(len(computadores_data)))
        
        print("\n[SUCCESS] Base de datos inicializada correctamente!")
        print("\n[INFO] CREDENCIALES DE ACCESO:")
        print("-" * 50)
        for u in usuarios:
            print("  Email: {}".format(u.email))
            print("  Contrasena: {} (Ver en codigo)".format('*' * 11))
            print("  Rol: {}".format(u.rol))
            print()
        
        print("[STATS] RESUMEN:")
        print("  * Usuarios: {}".format(Usuario.query.count()))
        print("  * Personas: {}".format(Persona.query.count()))
        print("  * Computadores: {}".format(Computador.query.count()))

if __name__ == '__main__':
    init_database()
