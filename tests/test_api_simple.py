#!/usr/bin/env python3
import sys
import os
import random
import jwt
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 70)
print("[TEST API] Diagnostico GET/POST sync")
print("=" * 70)

try:
    from backend.app import create_app, db
    from backend.models import Persona, Usuario
    
    print("[OK] Backend importado")
    
    app, socketio = create_app()
    ctx = app.app_context()
    ctx.push()
    
    print("[OK] App context creado")
    
    admin = Usuario.query.filter_by(email='admin@sena.edu.co').first()
    if not admin:
        print("[ERROR] No admin")
        sys.exit(1)
    
    secret_key = app.config.get('SECRET_KEY', 'dev-secret-key')
    payload = {
        'usuario_id': admin.id,
        'email': admin.email,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    client = app.test_client()
    
    print("\nBD Status:")
    total_bd = db.session.query(Persona).count()
    activas_bd = db.session.query(Persona).filter_by(deleted_at=None).count()
    print(f"  Total: {total_bd}")
    print(f"  Activas: {activas_bd}")
    
    print("\nGET /api/personas?limit=100&pagina=1:")
    response = client.get('/api/personas?limit=100&pagina=1', headers=headers)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.get_json()
        print(f"  API retorna: {len(data.get('personas', []))} personas")
        print(f"  Total segun API: {data.get('total')}")
    
    print("\nRegistrando nueva persona...")
    numero_doc = str(random.randint(1000000000, 9999999999))
    nueva = {
        'nombre': 'TEST_' + numero_doc[-4:],
        'numero_doc': numero_doc,
        'tipo_doc': 'CC',
        'perfil': 'APRENDIZ',
        'email': f'test.{numero_doc}@test.com'
    }
    
    response = client.post('/api/personas', json=nueva, headers=headers)
    print(f"  POST Status: {response.status_code}")
    
    if response.status_code == 201:
        print(f"  [OK] Persona registrada")
        
        print(f"\nGET /api/personas - Buscando documento {numero_doc}:")
        response = client.get('/api/personas?limit=1000&pagina=1', headers=headers)
        
        if response.status_code == 200:
            data = response.get_json()
            personas = data.get('personas', [])
            print(f"  API retorna ahora: {len(personas)} personas")
            
            encontrada = any(p['numero_doc'] == numero_doc for p in personas)
            
            if encontrada:
                print(f"  [OK] PERSONA ENCONTRADA!")
            else:
                print(f"  [ERROR] PERSONA NO ENCONTRADA!")
                print(f"  Primeras 3:")
                for p in personas[:3]:
                    print(f"    - {p['nombre'][:20]} ({p['numero_doc']})")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'ctx' in locals():
        ctx.pop()
