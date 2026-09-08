#!/usr/bin/env python3
"""
Test de sesión y autenticación
Verifica que el login funciona y que la sesión es reconocida
"""

import requests
import json
import time
import sys

BASE_URL = 'http://localhost:8000'
API_URL = f'{BASE_URL}/api'

def test_login(email, password):
    """Prueba login con cualquier credencial admin"""
    print(f"\n{'='*60}")
    print(f"TEST DE LOGIN")
    print(f"{'='*60}")
    print(f"Email: {email}")
    print(f"Intentando login...")
    
    try:
        resp = requests.post(
            f'{API_URL}/auth/login',
            json={'email': email, 'password': password},
            timeout=10
        )
        
        print(f"✓ Respuesta del servidor: HTTP {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            token = data.get('token')
            usuario = data.get('usuario', {})
            
            print(f"\n✅ LOGIN EXITOSO")
            print(f"  - Token: {token[:20]}...{token[-20:] if token else 'VACÍO'}")
            print(f"  - Usuario: {usuario.get('nombre', 'N/A')}")
            print(f"  - Email: {usuario.get('email', 'N/A')}")
            print(f"  - Rol: {usuario.get('rol', 'N/A')}")
            
            return {
                'token': token,
                'usuario': usuario,
                'success': True
            }
        else:
            print(f"❌ LOGIN FALLÓ")
            print(f"  Error: {resp.json().get('error', 'Desconocido')}")
            return {'success': False}
            
    except requests.exceptions.ConnectionError:
        print(f"❌ No se pudo conectar al servidor en {BASE_URL}")
        print(f"   ¿Está el servidor corriendo?")
        return {'success': False}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {'success': False}


def test_sesion_activa(token):
    """Verifica que la sesión es válida"""
    print(f"\n{'='*60}")
    print(f"TEST DE SESIÓN ACTIVA")
    print(f"{'='*60}")
    print(f"Token: {token[:20]}...{token[-20:]}")
    print(f"Verificando con /api/auth/me...")
    
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        resp = requests.get(
            f'{API_URL}/auth/me',
            headers=headers,
            timeout=10
        )
        
        print(f"✓ Respuesta: HTTP {resp.status_code}")
        
        if resp.status_code == 200:
            usuario = resp.json()
            print(f"\n✅ SESIÓN VÁLIDA")
            print(f"  - Usuario ID: {usuario.get('id')}")
            print(f"  - Nombre: {usuario.get('nombre')}")
            print(f"  - Email: {usuario.get('email')}")
            print(f"  - Rol: {usuario.get('rol')}")
            return True
        else:
            print(f"❌ SESIÓN INVÁLIDA")
            print(f"  Error: {resp.json().get('error', 'Token inválido')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_acceso_personas(token):
    """Verifica que se puede acceder a /api/personas con token"""
    print(f"\n{'='*60}")
    print(f"TEST DE ACCESO A /api/personas")
    print(f"{'='*60}")
    print(f"Intentando acceder a lista de personas...")
    
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        resp = requests.get(
            f'{API_URL}/personas?limit=5',
            headers=headers,
            timeout=10
        )
        
        print(f"✓ Respuesta: HTTP {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            total = data.get('total', 0)
            personas = data.get('personas', [])
            
            print(f"\n✅ ACCESO PERMITIDO")
            print(f"  - Total de personas: {total}")
            print(f"  - Personas en respuesta: {len(personas)}")
            if personas:
                print(f"  - Primera: {personas[0].get('nombre', 'N/A')}")
            return True
        else:
            print(f"❌ ACCESO DENEGADO")
            print(f"  Código: {resp.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("SUITE DE TESTS - SESIÓN Y AUTENTICACIÓN")
    print("="*60)
    print(f"Servidor: {BASE_URL}")
    
    # Datos de prueba
    admin_email = 'admin@sena.edu.co'
    admin_password = 'admin123'
    
    # Test 1: Login
    login_result = test_login(admin_email, admin_password)
    if not login_result['success']:
        print("\n⚠️  No se pudo hacer login. Abortando tests.")
        sys.exit(1)
    
    token = login_result['token']
    
    # Test 2: Verificar sesión
    sesion_ok = test_sesion_activa(token)
    
    # Test 3: Acceder a recursos protegidos
    personas_ok = test_acceso_personas(token)
    
    # Resumen
    print(f"\n{'='*60}")
    print("RESUMEN")
    print(f"{'='*60}")
    print(f"✅ Login: EXITOSO")
    print(f"{'✅' if sesion_ok else '❌'} Sesión válida: {'SÍ' if sesion_ok else 'NO'}")
    print(f"{'✅' if personas_ok else '❌'} Acceso a /api/personas: {'SÍ' if personas_ok else 'NO'}")
    
    if sesion_ok and personas_ok:
        print(f"\n🎉 TODOS LOS TESTS PASARON")
        return 0
    else:
        print(f"\n⚠️  ALGUNOS TESTS FALLARON")
        return 1


if __name__ == '__main__':
    sys.exit(main())
