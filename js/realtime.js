/**
 * CONEXION EN TIEMPO REAL CON WEBSOCKET
 * Permite que las páginas reciban actualizaciones automáticas de la BD
 */

class RealtimeDB {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.personas = [];
        this.stats = {};
        this.callbacks = {
            onPersonasUpdated: null,
            onStatsUpdated: null,
            onConnected: null,
            onDisconnected: null
        };
    }
    
    /**
     * Conectar a WebSocket del servidor
     */
    connect() {
        // Importar socket.io desde CDN
        if (typeof io === 'undefined') {
            // Cargar socket.io library
            const script = document.createElement('script');
            script.src = 'https://cdn.socket.io/4.5.4/socket.io.min.js';
            script.onload = () => this._initSocket();
            document.head.appendChild(script);
        } else {
            this._initSocket();
        }
    }
    
    /**
     * Inicializar conexión de socket
     */
    _initSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const url = `${protocol}://${window.location.host}`;
        
        console.log('[REALTIME] Conectando a WebSocket:', url);
        
        this.socket = io(url, {
            transports: ['websocket', 'polling']
        });
        
        // Eventos de conexión
        this.socket.on('connect', () => {
            console.log('[REALTIME] Conectado al servidor');
            this.connected = true;
            if (this.callbacks.onConnected) {
                this.callbacks.onConnected();
            }
            
            // Solicitar datos iniciales
            this.socket.emit('request_personas');
            this.socket.emit('request_stats');
        });
        
        this.socket.on('disconnect', () => {
            console.log('[REALTIME] Desconectado del servidor');
            this.connected = false;
            if (this.callbacks.onDisconnected) {
                this.callbacks.onDisconnected();
            }
        });
        
        // Recibir datos de personas
        this.socket.on('personas_data', (data) => {
            console.log(`[REALTIME] Recibido ${data.total} personas`);
            this.personas = data.personas;
            if (this.callbacks.onPersonasUpdated) {
                this.callbacks.onPersonasUpdated(data);
            }
        });
        
        // Recibir actualización de personas
        this.socket.on('personas_updated', (data) => {
            console.log(`[REALTIME] Personas actualizadas: ${data.total}`);
            this.personas = data.personas;
            this.stats = data.stats;
            if (this.callbacks.onPersonasUpdated) {
                this.callbacks.onPersonasUpdated(data);
            }
            if (this.callbacks.onStatsUpdated) {
                this.callbacks.onStatsUpdated(data.stats);
            }
        });
        
        // Recibir estadísticas
        this.socket.on('stats_data', (data) => {
            console.log('[REALTIME] Estadísticas recibidas');
            this.stats = data;
            if (this.callbacks.onStatsUpdated) {
                this.callbacks.onStatsUpdated(data);
            }
        });
        
        // Registros limpiados por el admin — limpiar cola offline para evitar
        // que registros obsoletos se sincronicen y bloqueen entradas/salidas
        this.socket.on('registros_limpiados', () => {
            console.log('[REALTIME] Registros limpiados por admin — vaciando cola offline');
            localStorage.removeItem('registros_pendientes');
        });

        // Errores
        this.socket.on('error', (error) => {
            console.error('[REALTIME] Error de WebSocket:', error);
        });
    }
    
    /**
     * Buscar una persona por cedula/numero_doc
     */
    buscarPersona(numero_doc) {
        const persona = this.personas.find(p => p.numero_doc === numero_doc);
        return persona || null;
    }
    
    /**
     * Obtener todas las personas
     */
    obtenerPersonas() {
        return this.personas;
    }
    
    /**
     * Obtener estadísticas
     */
    obtenerStats() {
        return this.stats;
    }
    
    /**
     * Registrar callback para cuando se actualicen personas
     */
    onPersonasUpdated(callback) {
        this.callbacks.onPersonasUpdated = callback;
    }
    
    /**
     * Registrar callback para cuando se actualicen estadísticas
     */
    onStatsUpdated(callback) {
        this.callbacks.onStatsUpdated = callback;
    }
    
    /**
     * Registrar callback para cuando se conecte
     */
    onConnected(callback) {
        this.callbacks.onConnected = callback;
    }
    
    /**
     * Registrar callback para cuando se desconecte
     */
    onDisconnected(callback) {
        this.callbacks.onDisconnected = callback;
    }
}

// Crear instancia global
window.realtimeDB = new RealtimeDB();

// Auto-conectar cuando la página carga
document.addEventListener('DOMContentLoaded', function() {
    console.log('[REALTIME] Página cargada, conectando a servidor...');
    window.realtimeDB.connect();
});
