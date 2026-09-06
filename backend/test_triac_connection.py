#!/usr/bin/env python3
"""
Test de conexión y comunicación con ESP32 TRIAC
Verifica que la comunicación HTTP extremo a extremo funcione correctamente.

Uso:
    python test_triac_connection.py [IP_ESP32]
    
Ejemplo:
    python test_triac_connection.py 172.20.10.5
"""

import sys
import requests
import json
from datetime import datetime

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_ok(text):
    print(f"  ✅ {text}")

def print_err(text):
    print(f"  ❌ {text}")

def print_warn(text):
    print(f"  ⚠️  {text}")

def print_info(text):
    print(f"  ℹ️  {text}")

def test_esp32_connection(ip_esp32: str, timeout: int = 3) -> bool:
    """Prueba la conexión básica con el ESP32."""
    print_header("PRUEBA 1: Conectividad Básica")
    
    try:
        # Intentar acceso a la raíz
        response = requests.get(f"http://{ip_esp32}/", timeout=timeout)
        print_ok(f"Puerto 80 abierto en {ip_esp32}")
        print_info(f"Status: {response.status_code}")
        return True
    except requests.exceptions.Timeout:
        print_err(f"Timeout: El ESP32 en {ip_esp32} no responde")
        return False
    except requests.exceptions.ConnectionError:
        print_err(f"No se puede conectar a {ip_esp32}")
        print_warn("Verifica:")
        print("    1. El ESP32 está encendido")
        print("    2. Está conectado a la red WiFi")
        print("    3. La IP es correcta")
        print("    4. Ambas máquinas están en la misma red")
        return False
    except Exception as e:
        print_err(f"Error: {str(e)}")
        return False

def test_triac_endpoints(ip_esp32: str, timeout: int = 3) -> bool:
    """Prueba los endpoints TRIAC del ESP32."""
    print_header("PRUEBA 2: Endpoints TRIAC HTTP")
    
    endpoints = [
        ("/triac/estado", "GET", "Obtener estado"),
        ("/triac/iniciar", "GET", "Iniciar ciclo"),
        ("/triac/parar", "GET", "Parar ciclo"),
    ]
    
    all_ok = True
    for endpoint, method, descripcion in endpoints:
        try:
            url = f"http://{ip_esp32}{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            else:
                response = requests.post(url, timeout=timeout)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print_ok(f"{descripcion}: {endpoint}")
                    print_info(f"   Respuesta: {json.dumps(data, indent=2, ensure_ascii=False)[:100]}...")
                except:
                    print_ok(f"{descripcion}: {endpoint} (sin JSON válido)")
            else:
                print_err(f"{descripcion}: {endpoint} → HTTP {response.status_code}")
                all_ok = False
        except requests.exceptions.Timeout:
            print_err(f"{descripcion}: {endpoint} → Timeout")
            all_ok = False
        except Exception as e:
            print_err(f"{descripcion}: {endpoint} → {str(e)}")
            all_ok = False
    
    return all_ok

def test_triac_ciclo(ip_esp32: str, timeout: int = 3) -> bool:
    """Prueba un ciclo completo del TRIAC (iniciar → esperar → parar)."""
    print_header("PRUEBA 3: Ciclo TRIAC Completo")
    
    try:
        # Obtener estado inicial
        response = requests.get(f"http://{ip_esp32}/triac/estado", timeout=timeout)
        estado_inicial = response.json() if response.status_code == 200 else {}
        print_ok(f"Estado inicial: ciclo_activo={estado_inicial.get('en_ciclo', 'desconocido')}")
        
        # Iniciar ciclo
        print_info("Iniciando ciclo TRIAC...")
        response = requests.get(f"http://{ip_esp32}/triac/iniciar", timeout=timeout)
        if response.status_code != 200:
            print_err("Error al iniciar el ciclo")
            return False
        
        resultado_inicio = response.json() if response.status_code == 200 else {}
        print_ok(f"Ciclo iniciado: {resultado_inicio.get('mensaje', 'ok')}")
        print_info("Esperando 5 segundos...")
        
        # Esperar un poco
        import time
        time.sleep(5)
        
        # Consultar estado durante ejecución
        response = requests.get(f"http://{ip_esp32}/triac/estado", timeout=timeout)
        estado_ejecucion = response.json() if response.status_code == 200 else {}
        print_ok(f"Estado en ejecución: ciclo_activo={estado_ejecucion.get('en_ciclo', '?')}, pulso={estado_ejecucion.get('pulso_actual', '?')}/{estado_ejecucion.get('pulsos_totales', '?')}")
        
        # Parar ciclo
        print_info("Parando ciclo TRIAC...")
        response = requests.get(f"http://{ip_esp32}/triac/parar", timeout=timeout)
        if response.status_code != 200:
            print_err("Error al parar el ciclo")
            return False
        
        resultado_parada = response.json() if response.status_code == 200 else {}
        print_ok(f"Ciclo parado: {resultado_parada.get('mensaje', 'ok')}")
        
        return True
    except Exception as e:
        print_err(f"Error durante ciclo: {str(e)}")
        return False

def main():
    print("\n╔" + "="*68 + "╗")
    print("║" + " "*15 + "TEST DE INTEGRACIÓN ESP32 TRIAC" + " "*21 + "║")
    print("╚" + "="*68 + "╝")
    
    # Obtener IP del ESP32
    if len(sys.argv) > 1:
        ip_esp32 = sys.argv[1]
    else:
        print("\n⚙️  Ingresa la IP del ESP32 (ej: 172.20.10.5):")
        ip_esp32 = input("  IP: ").strip()
    
    if not ip_esp32:
        ip_esp32 = "192.168.1.100"
        print(f"  ℹ️  Usando IP por defecto: {ip_esp32}")
    
    print(f"\n🔍 Probando conexión a ESP32 en: {ip_esp32}")
    
    # Ejecutar pruebas
    resultados = {
        "Conectividad": test_esp32_connection(ip_esp32),
        "Endpoints": test_triac_endpoints(ip_esp32),
        "Ciclo Completo": test_triac_ciclo(ip_esp32),
    }
    
    # Resumen
    print_header("📊 RESUMEN DE RESULTADOS")
    total = len(resultados)
    exitosas = sum(1 for v in resultados.values() if v)
    
    for prueba, resultado in resultados.items():
        estado = "✅ EXITOSA" if resultado else "❌ FALLIDA"
        print(f"  {prueba:.<40} {estado}")
    
    print(f"\n  Resultado: {exitosas}/{total} pruebas exitosas")
    
    if exitosas == total:
        print_ok("¡Integración ESP32-Backend FUNCIONANDO CORRECTAMENTE!")
        print("\n  Próximos pasos:")
        print("    1. Configura la IP en la página de vigilancia")
        print("    2. Prueba los botones de control del TRIAC")
        print("    3. Verifica los logs en la consola del ESP32")
        return 0
    else:
        print_err("Algunas pruebas fallaron. Revisa los errores arriba.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
