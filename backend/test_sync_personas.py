#!/usr/bin/env python3
"""
Script para verificar si el POST de personas se sincroniza correctamente en el GET.
Este script simula lo que hace el frontend: registra una persona y después las lista.
"""

import os
import sys
from datetime import datetime

# Asegurar que estamos en el directorio correcto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import Persona

def test_sync():
    app, socketio = create_app()
    
    with app.app_context():
        print("\n" + "="*70)
        print("TEST DE SINCRONIZACION POST -> GET")
        print("="*70)
        
        # 1. Contar personas actuales
        personas_iniciales = Persona.query.filter_by(deleted_at=None).count()
        print(f"\n[INICIAL] Personas activas en BD: {personas_iniciales}")
        
        # 2. Crear una persona de prueba
        print(f"\n[CREANDO] Nueva persona...")
        test_doc = f"TEST_{int(datetime.now().timestamp())}"
        test_name = f"PERSONA_TEST_{test_doc}"
        
        # Verificar que no existe
        existing = Persona.query.filter_by(numero_doc=test_doc, deleted_at=None).first()
        if existing:
            print(f"   [EXISTE] Persona con doc {test_doc} ya existe, eliminandola...")
            existing.deleted_at = datetime.now()
            db.session.commit()
            print(f"   [OK] Eliminada")
        
        # Crear nueva persona
        persona_nueva = Persona(
            nombre=test_name,
            tipo_doc='CC',
            numero_doc=test_doc,
            email='test@test.com',
            telefono='3105555555',
            perfil='APRENDIZ',
            programa='TEST_PROGRAMA'
        )
        
        print(f"   [DATOS] Nombre: {test_name}")
        print(f"   [DATOS] Documento: {test_doc}")
        
        db.session.add(persona_nueva)
        print(f"   [BD] Persona anadida a session")
        
        db.session.commit()
        print(f"   [BD_COMMIT] EXITO - ID generado: {persona_nueva.id}")
        
        # 3. Verificar que está en BD
        print(f"\n[VERIFICAR] Persona en BD despues de commit...")
        persona_check = Persona.query.get(persona_nueva.id)
        if persona_check:
            print(f"   [OK] ENCONTRADA: {persona_check.nombre} ({persona_check.numero_doc})")
        else:
            print(f"   [ERROR] Persona NO encontrada despues de commit")
            return False
        
        # 4. Contar personas después de insertar
        personas_despues_insert = Persona.query.filter_by(deleted_at=None).count()
        print(f"\n[DESPUES_INSERT] Personas activas en BD: {personas_despues_insert}")
        print(f"   [INCREMENTO] {personas_despues_insert - personas_iniciales} personas nuevas")
        
        # 5. Hacer una consulta de listado como lo hace el GET
        print(f"\n[GET_SIMULACION] Listando personas con limit=1000, pagina=1...")
        
        limit = 1000
        pagina = 1
        por_pagina = 100
        
        query = Persona.query.filter_by(deleted_at=None)
        total_count = query.count()
        
        print(f"   [QUERY_TOTAL] Total en query: {total_count}")
        print(f"   [PAGINACION] Pagina: {pagina}, Por pagina: {por_pagina}")
        
        paginated = query.paginate(page=pagina, per_page=por_pagina, error_out=False)
        
        personas_retornadas = [
            {
                'id': p.id,
                'nombre': p.nombre,
                'numero_doc': p.numero_doc,
                'perfil': p.perfil
            }
            for p in paginated.items
        ]
        
        print(f"   [RESPUESTA] Personas retornadas en pagina 1: {len(personas_retornadas)}")
        
        # 6. Buscar la persona creada en los resultados
        print(f"\n[BUSCAR] Persona de prueba en resultados...")
        persona_encontrada = False
        for p in personas_retornadas:
            if p['numero_doc'] == test_doc:
                print(f"   [OK] ENCONTRADA: {p['nombre']} ({p['numero_doc']})")
                persona_encontrada = True
                break
        
        if not persona_encontrada:
            print(f"   [ERROR] Persona con doc {test_doc} NO aparece en resultados del GET")
            print(f"\n   [INFO] Primeras 5 personas retornadas:")
            for i, p in enumerate(personas_retornadas[:5]):
                print(f"      {i+1}. {p['nombre']} ({p['numero_doc']})")
            return False
        
        # 7. Limpiar
        print(f"\n[LIMPIAR] Deletando persona de prueba...")
        persona_nueva.deleted_at = datetime.now()
        db.session.commit()
        print(f"   [OK] Deletada")
        
        print(f"\n" + "="*70)
        print("TEST COMPLETADO EXITOSAMENTE")
        print("="*70 + "\n")
        
        return True

if __name__ == '__main__':
    try:
        success = test_sync()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
