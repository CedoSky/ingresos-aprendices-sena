#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script directo para actualizar nombres a MAYÚSCULAS usando SQL
Para SQLite: simplemente ejecutar
Ejecutar: python update_nombres_sql.py
"""

import sqlite3
import os
import sys
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'instance', 'app.db')

def actualizar_directamente():
    """Actualiza directamente en la BD con SQL"""
    
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Base de datos no encontrada en: {DATABASE_PATH}")
        sys.exit(1)
    
    try:
        print("\n" + "="*70)
        print("🚀 ACTUALIZACIÓN DIRECTA DE NOMBRES A MAYÚSCULAS (SQL)")
        print("="*70)
        print(f"📁 Base de datos: {DATABASE_PATH}\n")
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Contar antes
        cursor.execute("SELECT COUNT(*) FROM personas WHERE deleted_at IS NULL")
        total_antes = cursor.fetchone()[0]
        print(f"📊 Total de personas activas: {total_antes}")
        
        # Contar cuántas ya están en mayúsculas
        cursor.execute("""
            SELECT COUNT(*) FROM personas 
            WHERE deleted_at IS NULL AND nombre != UPPER(nombre)
        """)
        a_actualizar = cursor.fetchone()[0]
        print(f"✏️  Pendientes de actualizar: {a_actualizar}\n")
        
        if a_actualizar == 0:
            print("ℹ️  Todos los nombres ya están en mayúsculas")
            conn.close()
            return
        
        print("-" * 70)
        print("🔄 Ejecutando actualización...")
        
        # Ejecutar la actualización
        cursor.execute("""
            UPDATE personas 
            SET nombre = UPPER(nombre),
                updated_at = ?
            WHERE deleted_at IS NULL AND nombre != UPPER(nombre)
        """, (datetime.utcnow(),))
        
        # Confirmar cambios
        conn.commit()
        
        # Verificar resultado
        cursor.execute("SELECT COUNT(*) FROM personas WHERE deleted_at IS NULL")
        total_despues = cursor.fetchone()[0]
        
        print(f"✅ {a_actualizar} nombres actualizados a MAYÚSCULAS")
        print(f"📊 Total de personas: {total_despues}")
        
        print("\n" + "="*70)
        print("✅ Actualización completada exitosamente")
        print("="*70 + "\n")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"\n❌ Error de base de datos: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    actualizar_directamente()
