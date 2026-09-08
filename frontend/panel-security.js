/**
 * ═══════════════════════════════════════════════════════════════════════════════
 *   PANEL SECURITY CLIENT — Protección de Paneles en Frontend
 *   Sistema de Control de Ingresos SENA
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Funcionalidades:
 *   ✓ Valida sesión al cargar el panel
 *   ✓ Mantiene heartbeat con servidor cada 5 minutos
 *   ✓ Cierra sesión automáticamente si está inactivo
 *   ✓ Detecta acceso desde múltiples pestañas y cierra automáticamente
 *   ✓ Redirecciona a login si sesión está expirada
 *   ✓ Muestra advertencia visual cuando va a expirar la sesión
 *
 * USO EN HTML:
 *   <script src="/static/panel-security.js"></script>
 *   <script>
 *     // Inicializar protección para este panel
 *     initPanelSecurity('vigilancia', {
 *       tokenJWT: '{{ jwt_token }}',
 *       panelSessionToken: '{{ panel_session_token }}',
 *       expiryMinutes: 480,
 *       inactivityTimeout: 30
 *     });
 *   </script>
 */

class PanelSecurityClient {
  constructor(panelName, options = {}) {
    this.panelName = panelName;
    this.tokenJWT = options.tokenJWT || '';
    this.panelSessionToken = options.panelSessionToken || '';
    this.expiryMinutes = options.expiryMinutes || 480;
    this.inactivityTimeout = options.inactivityTimeout || 30;
    
    // ID único para esta pestaña/ventana
    this.tabId = this.generateTabId();
    this.tabOpenTime = Date.now();
    
    // Timers
    this.heartbeatInterval = null;
    this.inactivityTimer = null;
    this.expiryWarningTimer = null;
    this.tabCheckInterval = null;
    
    // Estado
    this.isSessionValid = true;
    this.lastActivityTime = Date.now();
    this.sessionStartTime = Date.now();
    this.warningShown = false;
    this.isMainTab = true;
    
    // Detectar cambios de foco/ventana
    this.unloadWarningShown = false;
    
    this.init();
  }

  /**
   * Genera un ID único para esta pestaña basado en timestamp + random
   */
  generateTabId() {
    return `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  init() {
    console.log(`[PanelSecurity] Inicializando protección para panel: ${this.panelName}`);
    console.log(`[PanelSecurity] ID de pestaña: ${this.tabId}`);
    
    // Validar que tenemos los tokens necesarios
    if (!this.tokenJWT || !this.panelSessionToken) {
      console.error('[PanelSecurity] ERROR: Tokens no configurados. Redirigiendo a login...');
      this.redirectToLogin('Sesión no configurada correctamente');
      return;
    }

    // Registrar esta pestaña como activa
    this.registerThisTab();
    
    // Listeners de actividad del usuario
    this.setupActivityListeners();
    
    // Validar sesión al cargar
    this.validateSessionOnLoad();
    
    // Heartbeat periódico (cada 5 minutos)
    this.startHeartbeat();
    
    // Monitoreo de inactividad
    this.startInactivityMonitoring();
    
    // Detectar cierre de ventana/cambio de pestaña
    this.setupBeforeUnloadListener();
    
    // Detectar múltiples pestañas/windows - MEJORADO
    this.setupStorageListener();
    this.checkForOlderTabs();
    
    console.log('[PanelSecurity] Protección inicializada correctamente');
  }

  /**
   * Registra esta pestaña como activa en localStorage
   */
  registerThisTab() {
    const key = `panel_${this.panelName}_tabs`;
    let tabs = {};
    
    try {
      const stored = localStorage.getItem(key);
      if (stored) {
        tabs = JSON.parse(stored);
      }
    } catch (e) {
      console.warn('[PanelSecurity] Error leyendo tabs almacenados');
    }

    // Agregar esta pestaña al registro
    tabs[this.tabId] = {
      id: this.tabId,
      openedAt: this.tabOpenTime,
      lastSeen: Date.now()
    };

    try {
      localStorage.setItem(key, JSON.stringify(tabs));
    } catch (e) {
      console.error('[PanelSecurity] Error guardando registro de pestañas');
    }
  }

  /**
   * Verifica si hay pestañas más antiguas que esta y las cierra
   */
  checkForOlderTabs() {
    const key = `panel_${this.panelName}_tabs`;
    
    // Ejecutar cada 2 segundos (tiempo crítico)
    this.tabCheckInterval = setInterval(() => {
      try {
        const stored = localStorage.getItem(key);
        if (!stored) return;

        let tabs = JSON.parse(stored);
        
        // Limpiar pestañas muertas (sin actividad > 5 segundos)
        const now = Date.now();
        const deadTabTimeout = 5000;
        
        Object.keys(tabs).forEach(tabId => {
          if (now - tabs[tabId].lastSeen > deadTabTimeout) {
            delete tabs[tabId];
          }
        });

        // Encontrar la pestaña más antigua aún activa
        let oldestTabId = null;
        let oldestTime = Infinity;

        Object.keys(tabs).forEach(tabId => {
          if (tabs[tabId].openedAt < oldestTime) {
            oldestTime = tabs[tabId].openedAt;
            oldestTabId = tabId;
          }
        });

        // Si esta pestaña NO es la más antigua, cerrarla
        if (oldestTabId !== this.tabId) {
          console.warn(`[PanelSecurity] Detectada pestaña más nueva (${oldestTabId}). Cerrando esta pestaña...`);
          this.isMainTab = false;
          
          // Guardar aviso antes de cerrar
          localStorage.setItem(`panel_${this.panelName}_closed_by_new_tab`, 'true');
          
          // Limpiar esta pestaña
          delete tabs[this.tabId];
          localStorage.setItem(key, JSON.stringify(tabs));
          
          // Cerrar esta ventana/pestaña después de brevísimo delay
          setTimeout(() => {
            window.close();
          }, 100);
        } else if (!this.isMainTab) {
          // Si recuperamos el estado de main tab
          this.isMainTab = true;
          console.log('[PanelSecurity] Esta pestaña es ahora la principal');
        }

        // Actualizar lastSeen
        if (tabs[this.tabId]) {
          tabs[this.tabId].lastSeen = now;
          localStorage.setItem(key, JSON.stringify(tabs));
        }

      } catch (e) {
        console.warn('[PanelSecurity] Error en verificación de pestañas', e);
      }
    }, 2000);
  }

  /**
   * Valida que la sesión sea válida cuando se carga/recarga la página
   */
  validateSessionOnLoad() {
    this.fetchWithAuth('/api/security/validate-panel-session', 'POST', {
      panel: this.panelName
    }).then(response => {
      if (response.ok) {
        console.log('[PanelSecurity] Sesión válida al cargar');
      } else if (response.status === 401 || response.status === 410) {
        console.warn('[PanelSecurity] Sesión inválida al cargar');
        this.redirectToLogin('Sesión expirada o inválida');
      }
    }).catch(error => {
      console.error('[PanelSecurity] Error validando sesión:', error);
      // Si hay error de red pero estamos en el panel, permitir continuar
      // (podría ser problema de conectividad temporal)
    });
  }

  /**
   * Registra listeners de actividad del usuario
   */
  setupActivityListeners() {
    const activityEvents = ['mousedown', 'keydown', 'touchstart', 'click'];
    
    activityEvents.forEach(event => {
      document.addEventListener(event, () => this.recordActivity(), true);
    });
  }

  /**
   * Registra que el usuario tuvo actividad (resetea timeout de inactividad)
   */
  recordActivity() {
    if (!this.isSessionValid) return;
    
    this.lastActivityTime = Date.now();
    
    // Si estaba mostrando advertencia, ocultarla
    if (this.warningShown) {
      this.hideExpiryWarning();
    }
    
    // Resetear timer de inactividad
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
    }
    this.startInactivityMonitoring();
  }

  /**
   * Inicia monitoreo de inactividad
   */
  startInactivityMonitoring() {
    const timeoutMs = this.inactivityTimeout * 60 * 1000; // Convertir a ms
    const warningMs = Math.max(0, timeoutMs - 5 * 60 * 1000); // Advertir 5 mins antes
    
    // Mostrar advertencia (si hay tiempo)
    if (warningMs > 0) {
      this.expiryWarningTimer = setTimeout(() => {
        if (this.isSessionValid) {
          this.showExpiryWarning();
        }
      }, warningMs);
    }
    
    // Cerrar sesión si inactividad excedida
    this.inactivityTimer = setTimeout(() => {
      console.warn('[PanelSecurity] Sesión cerrada por inactividad');
      this.sessionExpired('Sesión cerrada por inactividad');
    }, timeoutMs);
  }

  /**
   * Inicia heartbeat periódico para mantener sesión activa
   */
  startHeartbeat() {
    // Heartbeat cada 5 minutos
    const heartbeatIntervalMs = 5 * 60 * 1000;
    
    this.heartbeatInterval = setInterval(() => {
      if (!this.isSessionValid) {
        clearInterval(this.heartbeatInterval);
        return;
      }
      
      this.fetchWithAuth('/api/security/panel-heartbeat', 'POST', {
        panel: this.panelName
      }).then(response => {
        if (!response.ok) {
          if (response.status === 410) {
            // Sesión expirada
            this.sessionExpired('Sesión expirada en servidor');
          }
        }
      }).catch(error => {
        // Error de red - no es razón para cerrar sesión
        console.warn('[PanelSecurity] Error en heartbeat:', error);
      });
    }, heartbeatIntervalMs);
  }

  /**
   * Configura listener para detectar cierre de ventana
   */
  setupBeforeUnloadListener() {
    window.addEventListener('beforeunload', (e) => {
      // Notificar al servidor que vamos a cerrar sesión
      // Usamos keepalive para que llegue incluso si se cierra la ventana
      this.fetchWithAuth('/api/security/panel-leaving', 'POST', {
        panel: this.panelName,
        reason: 'page_unload'
      }, { keepalive: true }).catch(() => {
        // Ignorar errores aquí - es mejor esfuerzo
      });
    });
  }

  /**
   * Detecta acceso desde múltiples pestañas/windows (MEJORADO)
   */
  setupStorageListener() {
    const key = `panel_${this.panelName}_tabs`;
    
    // Escuchar cambios en localStorage desde otras pestañas
    window.addEventListener('storage', (e) => {
      if (e.key !== key) return;
      
      try {
        const tabs = JSON.parse(e.newValue || '{}');
        
        // Si hay pestañas más nuevas abiertas, cerrar esta
        let hasNewerTab = false;
        Object.keys(tabs).forEach(tabId => {
          if (tabs[tabId].openedAt > this.tabOpenTime && tabId !== this.tabId) {
            hasNewerTab = true;
          }
        });

        if (hasNewerTab) {
          console.warn('[PanelSecurity] Detectada pestaña más nueva desde otra ventana. Cerrando...');
          this.multiTabDetected();
        }
      } catch (e) {
        console.warn('[PanelSecurity] Error procesando evento de storage');
      }
    });
  }

  /**
   * Fetch con autorización incluida
   */
  async fetchWithAuth(url, method = 'GET', body = null, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.tokenJWT}`,
      'X-Panel-Session-Token': this.panelSessionToken,
      'X-Panel-Tab-Id': this.tabId  // Enviar ID único de pestaña para validación
    };
    
    const config = {
      method,
      headers,
      ...options
    };
    
    if (body && (method === 'POST' || method === 'PUT')) {
      config.body = JSON.stringify(body);
    }
    
    return fetch(url, config);
  }

  /**
   * Muestra advertencia visual de que sesión va a expirar
   */
  showExpiryWarning() {
    if (this.warningShown) return;
    
    this.warningShown = true;
    console.warn('[PanelSecurity] Mostrando advertencia de expiración');
    
    // Crear modal de advertencia
    const warningHTML = `
      <div id="panel-expiry-warning" style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        border: 2px solid #ff9800;
        border-radius: 10px;
        padding: 30px;
        max-width: 400px;
        z-index: 10000;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease-out;
      ">
        <div style="text-align: center;">
          <h2 style="color: #ff9800; margin-bottom: 10px;">⚠️ Sesión Por Expirar</h2>
          <p style="color: #666; margin-bottom: 20px;">
            Tu sesión expirará en 5 minutos por inactividad.
          </p>
          <p style="color: #999; font-size: 12px; margin-bottom: 20px;">
            Continúa usando el panel para extender tu sesión.
          </p>
          <button onclick="
            document.getElementById('panel-expiry-warning').style.display = 'none';
            document.body.style.overflow = 'auto';
          " style="
            padding: 10px 20px;
            background: #ff9800;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
          ">Entendido</button>
        </div>
      </div>
      <div id="panel-expiry-overlay" style="
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.3);
        z-index: 9999;
      "></div>
      <style>
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translate(-50%, -60%);
          }
          to {
            opacity: 1;
            transform: translate(-50%, -50%);
          }
        }
      </style>
    `;
    
    document.body.insertAdjacentHTML('beforeend', warningHTML);
    document.body.style.overflow = 'hidden';
  }

  /**
   * Oculta advertencia de expiración
   */
  hideExpiryWarning() {
    const warning = document.getElementById('panel-expiry-warning');
    const overlay = document.getElementById('panel-expiry-overlay');
    
    if (warning) warning.remove();
    if (overlay) overlay.remove();
    
    document.body.style.overflow = 'auto';
    this.warningShown = false;
  }

  /**
   * Detecta acceso desde múltiples pestañas
   */
  multiTabDetected() {
    this.isSessionValid = false;
    
    const alertHTML = `
      <div style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        border: 3px solid #d32f2f;
        border-radius: 10px;
        padding: 30px;
        max-width: 450px;
        z-index: 10000;
        box-shadow: 0 10px 40px rgba(0,0,0,0.4);
      ">
        <div style="text-align: center;">
          <h2 style="color: #d32f2f; margin-bottom: 10px;">🔐 Sesión Cerrada por Seguridad</h2>
          <p style="color: #666; margin-bottom: 20px;">
            Este panel ha sido abierto en otra pestaña/window para proteger tu seguridad.
          </p>
          <p style="color: #999; font-size: 12px; margin-bottom: 20px;">
            Si continuarás usando este panel, por favor recarga la página.
          </p>
        </div>
      </div>
      <div style="
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.4);
        z-index: 9999;
      "></div>
    `;
    
    document.body.innerHTML = alertHTML;
    
    // Redirigir a login en 5 segundos
    setTimeout(() => {
      this.redirectToLogin('Panel abierto en múltiples pestañas');
    }, 5000);
  }

  /**
   * Sesión expirada - redirigir a login
   */
  sessionExpired(reason = 'Sesión expirada') {
    this.isSessionValid = false;
    clearInterval(this.heartbeatInterval);
    clearTimeout(this.inactivityTimer);
    clearTimeout(this.expiryWarningTimer);
    
    console.error(`[PanelSecurity] Sesión expirada: ${reason}`);
    this.redirectToLogin(reason);
  }

  /**
   * Redirige a login
   */
  redirectToLogin(reason = '') {
    // Guardar razón en sessionStorage para mostrar al usuario
    if (reason) {
      try {
        sessionStorage.setItem('logout_reason', reason);
      } catch (e) {
        // Ignorar si sessionStorage no disponible
      }
    }
    
    // Redirigir a login
    window.location.href = '/';
  }
}

/**
 * Función de inicialización global
 * USO: initPanelSecurity('vigilancia', { ... })
 */
function initPanelSecurity(panelName, options = {}) {
  window.panelSecurity = new PanelSecurityClient(panelName, options);
  return window.panelSecurity;
}

// Auto-inicializar si hay atributo data-panel en el body
document.addEventListener('DOMContentLoaded', () => {
  const panelName = document.body.getAttribute('data-panel');
  const tokenJWT = document.body.getAttribute('data-token-jwt');
  const panelSessionToken = document.body.getAttribute('data-panel-session-token');
  
  if (panelName && tokenJWT && panelSessionToken) {
    initPanelSecurity(panelName, {
      tokenJWT,
      panelSessionToken,
      expiryMinutes: parseInt(document.body.getAttribute('data-expiry-minutes') || '480'),
      inactivityTimeout: parseInt(document.body.getAttribute('data-inactivity-timeout') || '30')
    });
  }
});
