from app import create_app

# create_app devuelve la aplicación Flask y la instancia Socket.IO.
# Gunicorn necesita exponer únicamente la aplicación Flask.
app, socketio = create_app('production')

if __name__ == "__main__":
    # Escuchar en TODAS las interfaces (0.0.0.0) para que ESP32 pueda conectarse desde otra IP
    host = os.getenv('FLASK_HOST', '0.0.0.0')     # 0.0.0.0 = todas las interfaces
    port = int(os.getenv('FLASK_PORT', 8000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    print(f'[FLASK] Escuchando en {host}:{port}')
    app.run(host=host, port=port, debug=debug)
