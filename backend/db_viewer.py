"""
Vista web para explorar la base de datos SQLite
Se integra con Flask mostrando tablas, registros y permite ejecutar queries
"""

from flask import Blueprint, render_template_string, request, jsonify
import sqlite3
import os
from pathlib import Path

db_viewer_bp = Blueprint('db_viewer', __name__, url_prefix='/db')


def get_db_path():
    """Obtiene la ruta de la BD (USB o local)"""
    
    # Intentar USB primero (donde está la BD real)
    usb_path = 'E:/SENA_BASE_DATOS/sena.db'
    if os.path.exists(usb_path):
        return usb_path
    
    # Fallback a variables de entorno
    if os.getenv('USE_USB') == 'true' and os.getenv('DATABASE_URL'):
        db_url = os.getenv('DATABASE_URL')
        if db_url.startswith('sqlite:///'):
            db_path = db_url[10:]
        else:
            db_path = db_url
        
        if os.path.exists(db_path):
            return db_path
    
    # Fallback a BD local
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'sena.db')


@db_viewer_bp.route('/')
def index():
    """Página principal del visor de BD"""
    
    db_path = get_db_path()
    
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Visor Base de Datos - SENA</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 28px;
                margin-bottom: 10px;
            }
            
            .header p {
                font-size: 14px;
                opacity: 0.9;
            }
            
            .content {
                display: grid;
                grid-template-columns: 250px 1fr;
                min-height: 600px;
            }
            
            .sidebar {
                background: #f5f5f5;
                border-right: 1px solid #ddd;
                padding: 20px;
                overflow-y: auto;
            }
            
            .sidebar h3 {
                font-size: 14px;
                color: #666;
                text-transform: uppercase;
                margin-bottom: 15px;
                margin-top: 20px;
            }
            
            .sidebar h3:first-child {
                margin-top: 0;
            }
            
            .table-list {
                list-style: none;
            }
            
            .table-item {
                padding: 10px 12px;
                margin-bottom: 5px;
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.3s;
                font-size: 13px;
            }
            
            .table-item:hover {
                background: #667eea;
                color: white;
                border-color: #667eea;
            }
            
            .table-item.active {
                background: #667eea;
                color: white;
                border-color: #667eea;
                font-weight: bold;
            }
            
            .main {
                padding: 30px;
            }
            
            .table-info {
                background: #f9f9f9;
                padding: 15px;
                border-radius: 4px;
                margin-bottom: 20px;
                border-left: 4px solid #667eea;
            }
            
            .table-info h4 {
                color: #667eea;
                margin-bottom: 8px;
                font-size: 14px;
            }
            
            .table-info p {
                font-size: 12px;
                color: #666;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            
            thead {
                background: #f0f0f0;
            }
            
            th {
                padding: 12px;
                text-align: left;
                font-weight: 600;
                border-bottom: 2px solid #ddd;
                font-size: 12px;
                color: #333;
            }
            
            td {
                padding: 12px;
                border-bottom: 1px solid #eee;
                font-size: 12px;
            }
            
            tr:hover {
                background: #f9f9f9;
            }
            
            .empty {
                text-align: center;
                padding: 40px;
                color: #999;
            }
            
            .stats {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                margin-bottom: 20px;
            }
            
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            
            .stat-box .number {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            .stat-box .label {
                font-size: 12px;
                opacity: 0.9;
            }
            
            .loading {
                text-align: center;
                padding: 40px;
                color: #999;
            }
            
            .error {
                background: #fee;
                color: #c33;
                padding: 15px;
                border-radius: 4px;
                margin: 20px 0;
                border-left: 4px solid #c33;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Visor Base de Datos SENA</h1>
                <p>Explorador SQLite en tiempo real</p>
            </div>
            
            <div class="content">
                <div class="sidebar">
                    <h3>Tablas</h3>
                    <ul class="table-list" id="tableList"></ul>
                </div>
                
                <div class="main">
                    <div id="stats" class="stats"></div>
                    <div id="tableInfo"></div>
                    <div id="content" class="loading">Selecciona una tabla...</div>
                </div>
            </div>
        </div>
        
        <script>
            let currentTable = null;
            
            // Cargar lista de tablas
            async function loadTables() {
                const response = await fetch('/db/api/tables');
                const data = await response.json();
                
                const tableList = document.querySelector('.table-list');
                tableList.innerHTML = '';
                
                data.tables.forEach(table => {
                    const li = document.createElement('li');
                    li.className = 'table-item';
                    li.textContent = table;
                    li.onclick = () => loadTable(table);
                    tableList.appendChild(li);
                });
                
                // Cargar primeras estadísticas
                loadStats();
            }
            
            // Cargar tabla
            async function loadTable(tableName) {
                currentTable = tableName;
                
                // Marcar activa
                document.querySelectorAll('.table-item').forEach(item => {
                    item.classList.remove('active');
                    if (item.textContent === tableName) {
                        item.classList.add('active');
                    }
                });
                
                const response = await fetch(`/db/api/table/${tableName}`);
                const data = await response.json();
                
                // Mostrar info
                const infoDiv = document.querySelector('#tableInfo');
                infoDiv.innerHTML = `
                    <div class="table-info">
                        <h4>${tableName}</h4>
                        <p>${data.count} registros | ${data.columns.length} columnas</p>
                    </div>
                `;
                
                // Crear tabla
                let html = '<table><thead><tr>';
                data.columns.forEach(col => {
                    html += `<th>${col}</th>`;
                });
                html += '</tr></thead><tbody>';
                
                if (data.rows.length === 0) {
                    html += '<tr><td colspan="' + data.columns.length + '" class="empty">Sin registros</td></tr>';
                } else {
                    data.rows.forEach(row => {
                        html += '<tr>';
                        row.forEach(cell => {
                            const display = cell === null ? '(NULL)' : String(cell).substring(0, 100);
                            html += `<td title="${cell}">${display}</td>`;
                        });
                        html += '</tr>';
                    });
                }
                
                html += '</tbody></table>';
                document.querySelector('#content').innerHTML = html;
            }
            
            // Cargar estadísticas
            async function loadStats() {
                const response = await fetch('/db/api/stats');
                const data = await response.json();
                
                const statsDiv = document.querySelector('#stats');
                statsDiv.innerHTML = `
                    <div class="stat-box">
                        <div class="number">${data.usuarios}</div>
                        <div class="label">Usuarios</div>
                    </div>
                    <div class="stat-box">
                        <div class="number">${data.personas}</div>
                        <div class="label">Personas</div>
                    </div>
                    <div class="stat-box">
                        <div class="number">${data.registros}</div>
                        <div class="label">Accesos Registrados</div>
                    </div>
                `;
            }
            
            // Inicializar
            loadTables();
            setInterval(loadStats, 5000); // Actualizar estadísticas cada 5s
        </script>
    </body>
    </html>
    """
    
    return render_template_string(html)


@db_viewer_bp.route('/api/tables')
def api_tables():
    """API: Obtener lista de tablas"""
    
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'tables': tables})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@db_viewer_bp.route('/api/table/<table_name>')
def api_table(table_name):
    """API: Obtener datos de tabla"""
    
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener columnas
        cursor.execute(f'PRAGMA table_info({table_name})')
        columns = [row[1] for row in cursor.fetchall()]
        
        # Obtener registros (max 100)
        cursor.execute(f'SELECT * FROM {table_name} LIMIT 100')
        rows = cursor.fetchall()
        
        # Contar total
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'columns': columns,
            'rows': rows,
            'count': count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@db_viewer_bp.route('/api/stats')
def api_stats():
    """API: Obtener estadísticas"""
    
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM usuarios')
            usuarios = cursor.fetchone()[0]
        except:
            usuarios = 0
        
        try:
            cursor.execute('SELECT COUNT(*) FROM personas')
            personas = cursor.fetchone()[0]
        except:
            personas = 0
        
        try:
            cursor.execute('SELECT COUNT(*) FROM registros_acceso')
            registros = cursor.fetchone()[0]
        except:
            registros = 0
        
        conn.close()
        
        return jsonify({
            'usuarios': usuarios,
            'personas': personas,
            'registros': registros
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Para usar en app.py:
# from db_viewer import db_viewer_bp
# app.register_blueprint(db_viewer_bp)
