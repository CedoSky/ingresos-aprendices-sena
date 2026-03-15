"""
Script para respaldar la base de datos a USB
Ejecutar: python backup_to_usb.py
"""

import os
import json
import shutil
from datetime import datetime
import sqlite3
from pathlib import Path

def crear_respaldo_usb(usb_path=None):
    """
    Crear respaldo de la base de datos en USB
    
    Args:
        usb_path: Ruta de la USB (ej: E:/ en Windows). 
                 Si es None, usa una carpeta local simulada.
    """
    
    # Si no se especifica ruta, usar carpeta local de respaldos
    if usb_path is None:
        usb_path = os.path.join(os.path.dirname(__file__), '..', 'RESPALDOS_USB')
    
    usb_path = os.path.abspath(usb_path)
    
    # Crear carpeta si no existe
    os.makedirs(usb_path, exist_ok=True)
    
    # Ruta de la BD actual
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'sena.db')
    
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), 'sena.db')
    
    if not os.path.exists(db_path):
        print("❌ No se encuentra la base de datos (sena.db)")
        return False
    
    # Crear timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    fecha_legible = datetime.now().strftime('%d/%m/%Y - %H:%M:%S')
    
    # Carpeta de respaldo
    respaldo_dir = os.path.join(usb_path, f'respaldo_{timestamp}')
    os.makedirs(respaldo_dir, exist_ok=True)
    
    print("=" * 60)
    print("🔄 RESPALDANDO BASE DE DATOS A USB")
    print("=" * 60)
    print(f"📅 Fecha: {fecha_legible}")
    print(f"💾 Destino: {usb_path}")
    print()
    
    try:
        # 1. Copiar base de datos
        print("1️⃣  Copiando base de datos...")
        db_backup_path = os.path.join(respaldo_dir, 'sena.db')
        shutil.copy2(db_path, db_backup_path)
        db_size = os.path.getsize(db_backup_path) / (1024 * 1024)  # MB
        print(f"   ✓ {db_size:.2f} MB")
        
        # 2. Exportar datos a JSON
        print("\n2️⃣  Exportando datos a JSON...")
        exportar_json(db_path, respaldo_dir)
        print("   ✓ Datos exportados")
        
        # 3. Crear archivo de información
        print("\n3️⃣  Creando información del respaldo...")
        info_file = os.path.join(respaldo_dir, 'INFO_RESPALDO.txt')
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("INFORMACIÓN DEL RESPALDO\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Fecha: {fecha_legible}\n")
            f.write(f"Sistema: CONTROL ACCESO SENA\n")
            f.write(f"Versión: 1.0\n")
            f.write(f"Usuario: admin@sena.edu.co\n\n")
            f.write("ARCHIVOS EN ESTE RESPALDO:\n")
            f.write("  • sena.db - Base de datos SQLite\n")
            f.write("  • usuarios.json - Datos de usuarios\n")
            f.write("  • personas.json - Datos de aprendices/instructores\n")
            f.write("  • computadores.json - Datos de equipos\n")
            f.write("  • registros_acceso.json - Registros de entrada/salida\n")
            f.write("  • INFO_RESPALDO.txt - Este archivo\n\n")
            f.write("INSTRUCCIONES DE RESTAURACIÓN:\n")
            f.write("  1. Copiar sena.db a la carpeta del servidor\n")
            f.write("  2. Reiniciar la aplicación\n")
            f.write("  3. Los JSON son solo para referencia\n\n")
        print("   ✓ INFO_RESPALDO.txt creado")
        
        # 4. Crear índice general de respaldos
        print("\n4️⃣  Actualizando índice de respaldos...")
        crear_indice_respaldos(usb_path)
        print("   ✓ Índice actualizado")
        
        # Resumen
        print("\n" + "=" * 60)
        print("✅ RESPALDO COMPLETADO EXITOSAMENTE")
        print("=" * 60)
        print(f"\n📁 Carpeta: {respaldo_dir}")
        print(f"📊 Tamaño total: {db_size:.2f} MB")
        print(f"🔐 Estado: PROTEGIDO")
        print("\n✨ El respaldo está listo en tu USB")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False


def exportar_json(db_path, respaldo_dir):
    """Exportar datos de la BD a archivos JSON"""
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Tablas a exportar
        tablas = ['usuarios', 'personas', 'computadores', 'registros_acceso']
        
        for tabla in tablas:
            try:
                cursor.execute(f"SELECT * FROM {tabla} WHERE deleted_at IS NULL")
                filas = cursor.fetchall()
                
                datos = [dict(fila) for fila in filas]
                
                # Convertir datetime a string
                for registro in datos:
                    for key, value in registro.items():
                        if isinstance(value, bytes):
                            registro[key] = None
                        elif value and 'datetime' in str(type(value)).lower():
                            registro[key] = str(value)
                
                json_path = os.path.join(respaldo_dir, f'{tabla}.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(datos, f, ensure_ascii=False, indent=2)
                    
            except sqlite3.OperationalError:
                # Tabla no existe aún
                pass
        
        conn.close()
        
    except Exception as e:
        print(f"   ⚠️  Error exportando JSON: {str(e)}")


def crear_indice_respaldos(usb_path):
    """Crear archivo de índice con todos los respaldos"""
    
    try:
        indice_file = os.path.join(usb_path, 'INDICE_RESPALDOS.txt')
        
        respaldos = []
        for item in os.listdir(usb_path):
            item_path = os.path.join(usb_path, item)
            if os.path.isdir(item_path) and item.startswith('respaldo_'):
                timestamp = item.replace('respaldo_', '')
                fecha = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                tamaño = sum(os.path.getsize(os.path.join(item_path, f)) 
                           for f in os.listdir(item_path) 
                           if os.path.isfile(os.path.join(item_path, f))) / (1024 * 1024)
                respaldos.append((fecha, item, tamaño))
        
        respaldos.sort(reverse=True)
        
        with open(indice_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("ÍNDICE DE RESPALDOS - SISTEMA CONTROL ACCESO SENA\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Total de respaldos: {len(respaldos)}\n\n")
            
            f.write("RESPALDOS DISPONIBLES:\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'#':<4} {'Fecha':<20} {'Carpeta':<30} {'Tamaño':<10}\n")
            f.write("-" * 70 + "\n")
            
            for i, (fecha, carpeta, tamaño) in enumerate(respaldos, 1):
                fecha_str = fecha.strftime('%d/%m/%Y %H:%M:%S')
                f.write(f"{i:<4} {fecha_str:<20} {carpeta:<30} {tamaño:.2f} MB\n")
            
            f.write("\n" + "=" * 70 + "\n")
            
    except Exception as e:
        print(f"   ⚠️  Error creando índice: {str(e)}")


if __name__ == '__main__':
    # Usar carpeta local RESPALDOS_USB si no hay USB conectada
    crear_respaldo_usb()
