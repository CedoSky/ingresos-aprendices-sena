"""
Script para restaurar base de datos desde USB
Ejecutar: python restore_from_usb.py
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

def listar_respaldos_usb(usb_path=None):
    """Listar todos los respaldos disponibles"""
    
    if usb_path is None:
        usb_path = os.path.join(os.path.dirname(__file__), '..', 'RESPALDOS_USB')
    
    usb_path = os.path.abspath(usb_path)
    
    if not os.path.exists(usb_path):
        return []
    
    respaldos = []
    for item in sorted(os.listdir(usb_path), reverse=True):
        item_path = os.path.join(usb_path, item)
        if os.path.isdir(item_path) and item.startswith('respaldo_'):
            tamaño = sum(os.path.getsize(os.path.join(item_path, f)) 
                       for f in os.listdir(item_path) 
                       if os.path.isfile(os.path.join(item_path, f))) / (1024 * 1024)
            respaldos.append({
                'carpeta': item,
                'ruta': item_path,
                'tamaño': tamaño
            })
    
    return respaldos


def restaurar_respaldo(numero=1, usb_path=None):
    """
    Restaurar un respaldo específico
    
    Args:
        numero: Número del respaldo (1 = más reciente)
        usb_path: Ruta de USB (None = carpeta local)
    """
    
    if usb_path is None:
        usb_path = os.path.join(os.path.dirname(__file__), '..', 'RESPALDOS_USB')
    
    usb_path = os.path.abspath(usb_path)
    
    # Listar respaldos
    respaldos = listar_respaldos_usb(usb_path)
    
    if not respaldos:
        print("❌ No hay respaldos disponibles en USB")
        return False
    
    if numero > len(respaldos) or numero < 1:
        print(f"❌ Respaldo {numero} no existe")
        return False
    
    respaldo = respaldos[numero - 1]
    
    print("=" * 60)
    print("🔄 RESTAURANDO BASE DE DATOS DESDE USB")
    print("=" * 60)
    print(f"📅 Respaldo: {respaldo['carpeta']}")
    print(f"💾 Tamaño: {respaldo['tamaño']:.2f} MB")
    print()
    
    try:
        # Rutas
        db_backup = os.path.join(respaldo['ruta'], 'sena.db')
        db_destino = os.path.join(os.path.dirname(__file__), 'instance', 'sena.db')
        
        # Asegurar carpeta instance
        os.makedirs(os.path.dirname(db_destino), exist_ok=True)
        
        if not os.path.exists(db_backup):
            db_backup = os.path.join(os.path.dirname(__file__), 'sena.db')
        
        if not os.path.exists(db_backup):
            print(f"❌ No se encuentra sena.db en respaldo")
            return False
        
        # Hacer backup de BD actual si existe
        if os.path.exists(db_destino):
            backup_anterior = db_destino + '.anterior'
            print("1️⃣  Guardando BD anterior como respaldo...")
            shutil.copy2(db_destino, backup_anterior)
            print(f"   ✓ Guardado en: {backup_anterior}")
        
        # Restaurar
        print("\n2️⃣  Restaurando nueva BD...")
        shutil.copy2(db_backup, db_destino)
        print(f"   ✓ Restaurado en: {db_destino}")
        
        # Crear info
        print("\n3️⃣  Registrando restauración...")
        info_file = os.path.join(os.path.dirname(__file__), 'ULTIMO_RESPALDO_RESTAURADO.txt')
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(f"Fecha de restauración: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Desde respaldo: {respaldo['carpeta']}\n")
            f.write(f"Base de datos: {db_destino}\n")
        print("   ✓ Información guardada")
        
        print("\n" + "=" * 60)
        print("✅ RESTAURACIÓN COMPLETADA")
        print("=" * 60)
        print("\n⚠️  IMPORTANTE: Reinicia la aplicación para aplicar cambios")
        print("\nPasos:")
        print("  1. Cierra la aplicación")
        print("  2. Espera 5 segundos")
        print("  3. Reinicia la aplicación")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False


def mostrar_menu_respaldos(usb_path=None):
    """Mostrar menú interactivo para seleccionar respaldo"""
    
    if usb_path is None:
        usb_path = os.path.join(os.path.dirname(__file__), '..', 'RESPALDOS_USB')
    
    respaldos = listar_respaldos_usb(usb_path)
    
    if not respaldos:
        print("❌ No hay respaldos disponibles")
        return
    
    print("\n" + "=" * 60)
    print("RESPALDOS DISPONIBLES")
    print("=" * 60 + "\n")
    
    for i, respaldo in enumerate(respaldos, 1):
        fecha = respaldo['carpeta'].replace('respaldo_', '')
        try:
            dt = datetime.strptime(fecha, '%Y%m%d_%H%M%S')
            fecha_legible = dt.strftime('%d/%m/%Y - %H:%M:%S')
        except:
            fecha_legible = fecha
        
        print(f"  {i}. {fecha_legible} ({respaldo['tamaño']:.2f} MB)")
    
    print("\n" + "-" * 60)
    try:
        eleccion = input("\nSelecciona el número del respaldo a restaurar (0 para cancelar): ").strip()
        
        if eleccion == '0':
            print("Cancelado")
            return
        
        numero = int(eleccion)
        restaurar_respaldo(numero, usb_path)
        
    except ValueError:
        print("❌ Opción inválida")
    except KeyboardInterrupt:
        print("\nCancelado por usuario")


if __name__ == '__main__':
    mostrar_menu_respaldos()
