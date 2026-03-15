/**
 * API Client para conectar el frontend con el backend Flask
 * Maneja autenticación, CRUD de personas y registros de acceso
 */

let API_TOKEN = localStorage.getItem('sena_api_token');
const API_URL = window.location.origin + '/api';

class APIClient {
    constructor() {
        this.token = localStorage.getItem('sena_api_token');
        this.usuario = localStorage.getItem('sena_usuario') ? JSON.parse(localStorage.getItem('sena_usuario')) : null;
    }

    /**
     * Login con email y password
     */
    async login(email, password) {
        try {
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                throw new Error('Credenciales inválidas');
            }

            const data = await response.json();
            this.token = data.token;
            this.usuario = data.usuario;

            localStorage.setItem('sena_api_token', this.token);
            localStorage.setItem('sena_usuario', JSON.stringify(this.usuario));

            return { success: true, usuario: this.usuario };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Obtener headers para peticiones autenticadas
     */
    getHeaders() {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`
        };
    }

    /**
     * Crear una nueva persona
     */
    async crearPersona(datos) {
        try {
            const response = await fetch(`${API_URL}/personas`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(datos)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Error al crear persona');
            }

            const data = await response.json();
            return { success: true, id: data.id };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Buscar persona por documento
     */
    async buscarPersona(numeroDoc) {
        try {
            const response = await fetch(`${API_URL}/personas?buscar=${encodeURIComponent(numeroDoc)}`, {
                headers: this.getHeaders()
            });

            if (!response.ok) {
                throw new Error('Error al buscar persona');
            }

            const data = await response.json();
            return data.personas && data.personas.length > 0 ? data.personas[0] : null;
        } catch (error) {
            console.error('Error en buscarPersona:', error);
            return null;
        }
    }

    /**
     * Listar todas las personas con filtros opcionales
     */
    async listarPersonas(filtros = {}) {
        try {
            let url = `${API_URL}/personas`;
            const params = new URLSearchParams();

            if (filtros.perfil) params.append('perfil', filtros.perfil);
            if (filtros.buscar) params.append('buscar', filtros.buscar);
            if (filtros.pagina) params.append('pagina', filtros.pagina);
            if (filtros.por_pagina) params.append('por_pagina', filtros.por_pagina);

            if (params.toString()) {
                url += '?' + params.toString();
            }

            const response = await fetch(url, { headers: this.getHeaders() });

            if (!response.ok) {
                throw new Error('Error al listar personas');
            }

            const data = await response.json();
            return { success: true, personas: data.personas, total: data.total };
        } catch (error) {
            return { success: false, error: error.message, personas: [] };
        }
    }

    /**
     * Obtener persona por ID
     */
    async obtenerPersona(id) {
        try {
            const response = await fetch(`${API_URL}/personas/${id}`, {
                headers: this.getHeaders()
            });

            if (!response.ok) {
                throw new Error('Persona no encontrada');
            }

            const data = await response.json();
            return { success: true, persona: data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Actualizar persona
     */
    async actualizarPersona(id, datos) {
        try {
            const response = await fetch(`${API_URL}/personas/${id}`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify(datos)
            });

            if (!response.ok) {
                throw new Error('Error al actualizar persona');
            }

            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Registrar acceso (entrada o salida)
     */
    async registrarAcceso(numeroDoc, tipo = 'ENTRADA', ambiente = null) {
        try {
            const datos = {
                numero_doc: numeroDoc,
                tipo: tipo,
                ambiente: ambiente || 'Sin especificar'
            };

            const response = await fetch(`${API_URL}/registros-acceso`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(datos)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Error al registrar acceso');
            }

            const data = await response.json();
            return { success: true, registroId: data.id };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Listar accesos registrados
     */
    async listarAccesos(filtros = {}) {
        try {
            let url = `${API_URL}/registros-acceso`;
            const params = new URLSearchParams();

            if (filtros.tipo) params.append('tipo', filtros.tipo);
            if (filtros.numeroDoc) params.append('numero_doc', filtros.numeroDoc);
            if (filtros.fechaDesde) params.append('fecha_desde', filtros.fechaDesde);

            if (params.toString()) {
                url += '?' + params.toString();
            }

            const response = await fetch(url, { headers: this.getHeaders() });

            if (!response.ok) {
                throw new Error('Error al listar accesos');
            }

            const data = await response.json();
            return { success: true, accesos: data.registros, total: data.total };
        } catch (error) {
            return { success: false, error: error.message, accesos: [] };
        }
    }

    /**
     * Obtener estadísticas del sistema
     */
    async obtenerEstadisticas() {
        try {
            const response = await fetch(`${API_URL}/estadisticas`, {
                headers: this.getHeaders()
            });

            if (!response.ok) {
                throw new Error('Error al obtener estadísticas');
            }

            const data = await response.json();
            return { success: true, estadisticas: data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Crear respaldo en S3
     */
    async crearRespaldo(descripcion = '') {
        try {
            const response = await fetch(`${API_URL}/respaldos/crear`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ descripcion })
            });

            if (!response.ok) {
                throw new Error('Error al crear respaldo');
            }

            const data = await response.json();
            return { success: true, respaldoId: data.id };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Listar respaldos
     */
    async listarRespaldos() {
        try {
            const response = await fetch(`${API_URL}/respaldos`, {
                headers: this.getHeaders()
            });

            if (!response.ok) {
                throw new Error('Error al listar respaldos');
            }

            const data = await response.json();
            return { success: true, respaldos: data.respaldos };
        } catch (error) {
            return { success: false, error: error.message, respaldos: [] };
        }
    }

    /**
     * Subir foto asociada a un registro de acceso
     */
    async subirFoto(numero_doc, persona_id, imagen_base64, registro_acceso_id = null) {
        try {
            const response = await fetch(`${API_URL}/fotos`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    numero_doc,
                    persona_id,
                    imagen_base64,
                    registro_acceso_id
                })
            });

            if (!response.ok) {
                throw new Error('Error al subir foto');
            }

            const data = await response.json();
            return { success: true, fotoId: data.id };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Obtener foto de una persona
     */
    async obtenerFotoPersona(numero_doc) {
        try {
            const response = await fetch(`${API_URL}/fotos/${numero_doc}`, {
                headers: this.getHeaders()
            });

            if (!response.ok) {
                throw new Error('Foto no encontrada');
            }

            const blob = await response.blob();
            const dataUrl = URL.createObjectURL(blob);
            return { success: true, dataUrl };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Listar fotos de una persona
     */
    async listarFotosPersona(persona_id) {
        try {
            const response = await fetch(`${API_URL}/fotos/persona/${persona_id}`, {
                headers: this.getHeaders()
            });

            if (!response.ok) {
                throw new Error('Error al listar fotos');
            }

            const data = await response.json();
            return { success: true, fotos: data.fotos, total: data.total };
        } catch (error) {
            return { success: false, error: error.message, fotos: [] };
        }
    }

    /**
     * Buscar persona rápido por código de barras (documento)
     */
    async buscarPorBarras(codigo) {
        try {
            const response = await fetch(`${API_URL}/barras/persona?codigo=${encodeURIComponent(codigo)}`, {
                headers: this.getHeaders()
            });

            if (!response.ok) {
                return { found: false };
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error en buscarPorBarras:', error);
            return { found: false, error: error.message };
        }
    }

    /**
     * Ingreso rápido con barras + foto
     */
    async ingresoRapidoBarras(numeroDoc, tipo, foto = null, ambiente = 'Entrada principal') {
        try {
            const body = {
                numero_doc: numeroDoc,
                tipo: tipo,
                ambiente: ambiente
            };
            
            if (foto) {
                body.foto = foto;
            }

            const response = await fetch(`${API_URL}/barras/ingreso-rapido`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(body)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Error en ingreso');
            }

            const data = await response.json();
            return { success: true, ...data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Buscar computador por código de barras
     */
    async buscarComputador(codigoBarras) {
        try {
            const response = await fetch(`${API_URL}/computadores?codigo_barras=${encodeURIComponent(codigoBarras)}`, {
                headers: this.getHeaders()
            });

            if (!response.ok) {
                return { found: false };
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error en buscarComputador:', error);
            return { found: false, error: error.message };
        }
    }

    /**
     * Crear nuevo computador
     */
    async crearComputador(codigoBarras, marca, modelo, tipo = 'Computador', serie = null) {
        try {
            const response = await fetch(`${API_URL}/computadores`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    codigo_barras: codigoBarras,
                    marca: marca,
                    modelo: modelo,
                    tipo: tipo,
                    serie: serie
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Error al crear computador');
            }

            const data = await response.json();
            return { success: true, ...data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Ingreso de persona + equipos a la vez
     */
    async ingresoConEquipos(numeroDoc, tipo, equipos = [], foto = null) {
        try {
            const body = {
                numero_doc: numeroDoc,
                tipo: tipo,
                equipos: equipos,
                ambiente: 'Aula 101'
            };
            
            if (foto) {
                body.foto = foto;
            }

            const response = await fetch(`${API_URL}/ingreso-equipos`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(body)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Error en ingreso');
            }

            const data = await response.json();
            return { success: true, ...data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Obtener equipos permanentemente asignados a una persona
     */
    async obtenerEquiposAsignados(personaId) {
        try {
            const response = await fetch(`${API_URL}/personas/${personaId}/equipos-asignados`, {
                headers: this.getHeaders()
            });

            if (!response.ok) {
                return { equipos: [] };
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error en obtenerEquiposAsignados:', error);
            return { equipos: [] };
        }
    }

    /**
     * Asignar equipo permanentemente a persona (primera vez)
     */
    async asignarEquipoAPersona(personaId, codigoBarras) {
        try {
            const response = await fetch(`${API_URL}/personas/${personaId}/asignar-equipo`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ codigo_barras: codigoBarras })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Error al asignar equipo');
            }

            const data = await response.json();
            return { success: true, ...data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Ingreso automático - Persona + todos sus equipos asignados
     */
    async ingresoAutomaticoConEquipos(numeroDoc, tipo, foto = null) {
        try {
            const body = {
                numero_doc: numeroDoc,
                tipo: tipo,
                ambiente: 'Aula 101'
            };
            
            if (foto) {
                body.foto = foto;
            }

            const response = await fetch(`${API_URL}/ingreso-automatico-equipo`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(body)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Error en ingreso');
            }

            const data = await response.json();
            return { success: true, ...data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Cerrar sesión
     */
    logout() {
        this.token = null;
        this.usuario = null;
        localStorage.removeItem('sena_api_token');
        localStorage.removeItem('sena_usuario');
        return { success: true };
    }

    /**
     * Verificar si hay sesión activa
     */
    estaAutenticado() {
        return this.token !== null && this.token !== undefined;
    }
}

// Instancia global del cliente API
const apiClient = new APIClient();
