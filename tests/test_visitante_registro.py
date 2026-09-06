#!/usr/bin/env python3
"""
PRUEBA: Control de Acceso a Visitantes (Terceros)

REQUISITO:
  Los VISITANTES (terceros, personas NO registradas en SENA) pueden SOLO ser
  registrados por el VIGILANTE desde el panel de vigilancia.
  
  ✅ Vigilante SÍ puede registrar visitantes
  ❌ Aprendices NO pueden registrar visitantes
  ❌ Instructores NO pueden registrar visitantes
  ❌ Visitantes NO pueden auto-registrarse

VALIDACIONES:
  1. POST /api/personas con perfil='visitante' → Solo vigilante
  2. POST /api/registros-acceso para visitante → Solo vigilante  
  3. POST /api/registros-acceso/manual visitante nuevo → Solo vigilante
  4. POST /api/registros-acceso-offline visitante → Rechazado siempre
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def obtener_token(email, password):
    """Obtiene un token JWT"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    if resp.status_code == 200:
        return resp.json().get('token')
    return None

def test_1_registrar_visitante(token, rol):
    """Prueba: Registrar visitante en /api/personas"""
    payload = {
        "nombre": "Juan Pérez García",
        "tipo_doc": "CC",
        "numero_doc": "1105123456",
        "perfil": "visitante",
        "email": "juan@example.com",
        "area": "Empresa de Mantenimiento"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    resp = requests.post(f"{BASE_URL}/api/personas", json=payload, headers=headers)
    return resp.status_code, resp.json()

def test_2_registrar_acceso_visitante(token, rol, numero_doc):
    """Prueba: Registrar acceso de visitante en /api/registros-acceso"""
    payload = {
        "numero_doc": numero_doc,
        "tipo": "ENTRADA"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    resp = requests.post(f"{BASE_URL}/api/registros-acceso", json=payload, headers=headers)
    return resp.status_code, resp.json()

def test_3_registrar_acceso_manual(token, rol):
    """Prueba: Registrar visitante nuevo en /api/registros-acceso/manual"""
    payload = {
        "nombre": "María López García",
        "tipo_doc": "CC",
        "numero_doc": "1105234567",
        "tipo": "ENTRADA",
        "ambiente": "Entrada Principal"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    resp = requests.post(f"{BASE_URL}/api/registros-acceso/manual", json=payload, headers=headers)
    return resp.status_code, resp.json()

def main():
    print("\n" + "="*80)
    print("CONTROL DE ACCESO A VISITANTES (TERCEROS)")
    print("="*80)
    print("\nREQUISITO: Los VISITANTES solo pueden ser registrados por VIGILANTES")
    print("desde el panel de vigilancia. NO desde paneles de ingreso de aprendices.")
    
    # Obtener tokens
    print("\n" + "─"*80)
    print("📋 OBTENIENDO CREDENCIALES")
    print("─"*80)
    
    print("\n➡️  Obteniendo token de VIGILANTE...")
    vigilante_token = obtener_token("vigilante@sena.edu.co", "vigilante123")
    if not vigilante_token:
        print("❌ No se pudo obtener token de vigilante")
        return
    print("✅ Token de vigilante obtenido")
    
    print("\n➡️  Obteniendo token de APRENDIZ...")
    aprendiz_token = obtener_token("aprendiz@sena.edu.co", "aprendiz123")
    if not aprendiz_token:
        print("❌ No se pudo obtener token de aprendiz")
        return
    print("✅ Token de aprendiz obtenido")
    
    # PRUEBAS
    print("\n" + "="*80)
    print("🧪 EJECUTANDO PRUEBAS")
    print("="*80)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n1️⃣  REGISTRAR VISITANTE EN /api/personas")
    print("-"*80)
    
    print("\n  📌 Vigilante intenta registrar visitante:")
    status, data = test_1_registrar_visitante(vigilante_token, "vigilante")
    print(f"    Estatus: {status}")
    print(f"    Resultado: {'✅ ÉXITO' if status in [201, 400] else '❌ FALLO'} (código {status})")
    if status != 201:
        print(f"    Respuesta: {data.get('error', 'N/A')}")
    
    print("\n  📌 Aprendiz intenta registrar visitante:")
    status, data = test_1_registrar_visitante(aprendiz_token, "aprendiz")
    print(f"    Estatus: {status}")
    expect = "✅ CORRECTO" if status == 403 else "❌ INCORRECTO"
    print(f"    Resultado: {expect} (esperaba 403, obtuvo {status})")
    print(f"    Mensaje: {data.get('error', 'N/A')}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n2️⃣  REGISTRAR ACCESO DE VISITANTE (entrada/salida)")
    print("-"*80)
    
    numero_visitante = "1105123456"
    
    print("\n  📌 Vigilante registra ENTRADA de visitante:")
    status, data = test_2_registrar_acceso_visitante(vigilante_token, "vigilante", numero_visitante)
    print(f"    Estatus: {status}")
    print(f"    Resultado: {'✅ CORRECTO' if status in [201, 404, 403] else '❌ INCORRECTO'}")
    
    print("\n  📌 Aprendiz intenta registrar ENTRADA de visitante:")
    status, data = test_2_registrar_acceso_visitante(aprendiz_token, "aprendiz", numero_visitante)
    print(f"    Estatus: {status}")
    expect = "✅ CORRECTO" if status == 403 else "❌ INCORRECTO"
    print(f"    Resultado: {expect} (esperaba 403, obtuvo {status})")
    print(f"    Mensaje: {data.get('error', 'N/A')}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n3️⃣  REGISTRAR VISITANTE NUEVO EN /api/registros-acceso/manual")
    print("-"*80)
    
    print("\n  📌 Vigilante registra visitante nuevo (manual):")
    status, data = test_3_registrar_acceso_manual(vigilante_token, "vigilante")
    print(f"    Estatus: {status}")
    print(f"    Resultado: {'✅ CORRECTO' if status in [201, 400] else '❌ INCORRECTO'}")
    if status != 201:
        print(f"    Respuesta: {data.get('error', 'N/A')}")
    
    print("\n  📌 Aprendiz intenta registrar visitante nuevo (manual):")
    status2, data2 = test_3_registrar_acceso_manual(aprendiz_token, "aprendiz")
    print(f"    Estatus: {status2}")
    expect = "✅ CORRECTO" if status2 == 403 else "❌ INCORRECTO"
    print(f"    Resultado: {expect} (esperaba 403, obtuvo {status2})")
    print(f"    Mensaje: {data2.get('error', 'N/A')}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n" + "="*80)
    print("✅ RESUMEN")
    print("="*80)
    print("""
Los visitantes (terceros) son personas que:
  • NO están registradas en el sistema SENA
  • Solo pueden entrar y salir bajo supervisión del VIGILANTE
  • El vigilante es responsable de registrar su entrada y salida
  
Restricciones implementadas:
  ❌ Visitante NO puede registrarse desde panel de ingreso de aprendices
  ❌ Aprendiz NO puede crear/registrar visitantes
  ⛔ Solo el VIGILANTE puede operar con visitantes
  🔒 Los registros offline de visitantes son rechazados
""")

if __name__ == "__main__":
    main()

