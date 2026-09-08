/**
 * ═════════════════════════════════════════════════════════════════════════════════
 * ESP32 Cerradura — Control Local con PROXY del Backend
 * 
 * Usa proxy HTTP en el backend para evitar problemas de CORS/bloqueos de Chrome
 * El backend redirige las solicitudes al ESP32 en 172.20.10.5
 * ═════════════════════════════════════════════════════════════════════════════════
 */

class ESP32Cerradura {
    constructor() {
        // Usar proxy del backend en lugar de conectar directamente a ESP32
        this.baseURL = "/api/esp32/proxy";  // Dirección del proxy en el backend
        this.estado = null;
        this.ultimaConexion = null;
    }

    /**
     * Abre la cerradura por N segundos
     * @param {number} segundos - Duración en segundos (1-15, por defecto 15)
     * @returns {Promise<Object>} Respuesta del ESP32
     */
    async abrir(segundos = 15) {
        if (segundos < 1 || segundos > 15) segundos = 15;
        
        try {
            console.log(`[ESP32] Abriendo cerradura por ${segundos}s...`);
            const response = await this._fetch(`/abrir?seg=${segundos}`);
            console.log('[ESP32] ✅ ABIERTA', response);
            return response;
        } catch (error) {
            console.error('[ESP32] ❌ Error abriendo:', error.message);
            throw error;
        }
    }

    /**
     * Cierra la cerradura inmediatamente
     * @returns {Promise<Object>} Respuesta del ESP32
     */
    async cerrar() {
        try {
            console.log('[ESP32] Cerrando cerradura...');
            const response = await this._fetch('/cerrar');
            console.log('[ESP32] 🔒 CERRADA', response);
            return response;
        } catch (error) {
            console.error('[ESP32] ❌ Error cerrando:', error.message);
            throw error;
        }
    }

    /**
     * Obtiene el estado actual de la cerradura
     * @returns {Promise<Object>} Estado (abierta/cerrada, ms abierta, etc.)
     */
    async obtenerEstado() {
        try {
            const response = await this._fetch('/estado');
            this.estado = response;
            this.ultimaConexion = new Date();
            console.log('[ESP32] Estado:', response);
            return response;
        } catch (error) {
            console.error('[ESP32] ❌ Error obteniendo estado:', error.message);
            throw error;
        }
    }

    /**
     * Prueba conectividad con el ESP32
     * @returns {Promise<Object>} Información del dispositivo
     */
    async ping() {
        try {
            const response = await this._fetch('/ping');
            this.ultimaConexion = new Date();
            console.log('[ESP32] Ping OK:', response);
            return response;
        } catch (error) {
            console.error('[ESP32] ❌ Ping falló:', error.message);
            throw error;
        }
    }

    /**
     * Realiza una solicitud HTTP através del proxy del backend
     * @private
     */
    async _fetch(endpoint) {
        const url = `${this.baseURL}${endpoint}`;
        const timeout = 10000;  // 10 segundos
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeout);

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
                throw new Error(error.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            return data;

        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Timeout: El ESP32 tardó demasiado en responder');
            }
            throw new Error(error.message || 'Error en comunicación con el proxy');
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Crear instancia global
// ─────────────────────────────────────────────────────────────────────────────
const cerraduraESP32 = new ESP32Cerradura();
