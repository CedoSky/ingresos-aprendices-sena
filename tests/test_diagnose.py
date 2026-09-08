#!/usr/bin/env python3
"""
Script de diagnóstico para verificar si la base de datos y el API están funcionando
"""

import sys
import os
from datetime import datetime

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 60)
print("[INFO] DIAGNOSTICO DE BASE DE DATOS")
print("=" * 60)

try:
    from backend.app import create_app, db
    from backend.models import Persona, Usuario
    
    print("\n[OK] Backend importado correctamente")
    
    # Crear app (devuelve tupla: app, socketio)
    app, socketio = create_app()
    
    with app.app_context():
        print("\n[INFO] ESTADO DE LA BASE DE DATOS:")
        print("-" * 60)
        
        # Contar personas totales
        total_personas = db.session.query(Persona).count()
        print(f"Total de personas en BD: {total_personas}")
        
        # Contar personas NO eliminadas
        activas = db.session.query(Persona).filter_by(deleted_at=None).count()
        print(f"Personas activas (no eliminadas): {activas}")
        
        # Contar personas eliminadas
        eliminadas = db.session.query(Persona).filter(Persona.deleted_at != None).count()
        print(f"Personas eliminadas: {eliminadas}")
        
        print("\n[INFO] ULTIMAS 5 PERSONAS REGISTRADAS:")
        print("-" * 60)
        ultimas = db.session.query(Persona).filter_by(deleted_at=None).order_by(Persona.id.desc()).limit(5).all()
        
        if ultimas:
            for i, persona in enumerate(ultimas, 1):
                print(f"\n{i}. {persona.nombre}")
                print(f"   Documento: {persona.numero_doc}")
                print(f"   Perfil: {persona.perfil}")
                print(f"   Email: {persona.email}")
                print(f"   Creada: {persona.created_at}")
        else:
            print("[WARN] No hay personas registradas")
        
        print("\n[INFO] USUARIOS DEL SISTEMA:")
        print("-" * 60)
        usuarios = db.session.query(Usuario).all()
        if usuarios:
            for user in usuarios:
                print(f"- {user.email} ({user.nombre}) - Rol: {user.rol}")
        else:
            print("[WARN] No hay usuarios")
        
        print("\n" + "=" * 60)
        print("[OK] DIAGNOSTICO COMPLETADO EXITOSAMENTE")
        print("=" * 60)
        
except ImportError as e:
    print(f"\n[ERROR] Error importando backend: {e}")
    print("\nVerifica que:")
    print("1. El archivo 'backend/app.py' existe")
    print("2. Las dependencias están instaladas (pip install -r requirements.txt)")
    sys.exit(1)
    
except Exception as e:
    print(f"\n[ERROR] Error en diagnostico: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

