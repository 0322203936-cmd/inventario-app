/**
 * offline.js — Módulo de soporte offline para Inventario App
 * 
 * - Almacena registros pendientes en IndexedDB cuando no hay conexión
 * - Sincroniza automáticamente con el servidor al recuperar internet
 * - Expone funciones globales usadas por index.html y registros.html
 */

const DB_NAME    = 'inventario-offline';
const DB_VERSION = 1;
const STORE_NAME = 'pendientes';

// ── IndexedDB helpers ──────────────────────────────────────────────────────────

function abrirDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = (e) => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
            }
        };
        req.onsuccess = (e) => resolve(e.target.result);
        req.onerror   = (e) => reject(e.target.error);
    });
}

/**
 * Guarda un registro pendiente en IndexedDB.
 * @param {Object} datos - El objeto con los datos del formulario
 */
async function guardarPendiente(datos) {
    const db    = await abrirDB();
    const tx    = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    return new Promise((resolve, reject) => {
        const req = store.add({ ...datos, _guardadoEn: new Date().toISOString() });
        req.onsuccess = () => resolve(req.result);
        req.onerror   = () => reject(req.error);
    });
}

/**
 * Lee todos los registros pendientes de IndexedDB.
 * @returns {Promise<Array>}
 */
async function leerPendientes() {
    const db    = await abrirDB();
    const tx    = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    return new Promise((resolve, reject) => {
        const req = store.getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror   = () => reject(req.error);
    });
}

/**
 * Cuenta los registros pendientes.
 * @returns {Promise<number>}
 */
async function contarPendientes() {
    const db    = await abrirDB();
    const tx    = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    return new Promise((resolve, reject) => {
        const req = store.count();
        req.onsuccess = () => resolve(req.result);
        req.onerror   = () => reject(req.error);
    });
}

/**
 * Borra un registro pendiente por su id de IndexedDB.
 * @param {number} id
 */
async function borrarPendiente(id) {
    const db    = await abrirDB();
    const tx    = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    return new Promise((resolve, reject) => {
        const req = store.delete(id);
        req.onsuccess = () => resolve();
        req.onerror   = () => reject(req.error);
    });
}

/**
 * Limpia todos los registros pendientes de IndexedDB.
 */
async function limpiarPendientes() {
    const db    = await abrirDB();
    const tx    = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    return new Promise((resolve, reject) => {
        const req = store.clear();
        req.onsuccess = () => resolve();
        req.onerror   = () => reject(req.error);
    });
}

// ── Conectividad ───────────────────────────────────────────────────────────────

/**
 * Verifica conectividad real haciendo un fetch a /ping.
 * Más confiable que navigator.onLine.
 * @returns {Promise<boolean>}
 */
async function isOnline() {
    try {
        const res = await fetch('/ping', {
            method: 'GET',
            cache: 'no-store',
            signal: AbortSignal.timeout(4000)
        });
        return res.ok;
    } catch {
        return false;
    }
}

// ── Sincronización ─────────────────────────────────────────────────────────────

let _sincronizando = false;

/**
 * Envía todos los registros pendientes al servidor (/sync).
 * Se llama automáticamente al detectar internet.
 * @returns {Promise<number>} Cantidad de registros sincronizados
 */
async function syncPendientes() {
    if (_sincronizando) return 0;
    _sincronizando = true;

    try {
        const pendientes = await leerPendientes();
        if (!pendientes.length) return 0;

        const online = await isOnline();
        if (!online) return 0;

        // Agrupar en formato que espera /sync
        const body = { registros: [], cf_registros: [] };
        for (const p of pendientes) {
            if (p.tipo === 'merma') body.registros.push(p);
            else if (p.tipo === 'cf') body.cf_registros.push(p);
            else {
                // Formato unificado (un envío puede tener ambos)
                if (p.filas_detalle && p.filas_detalle.length) body.registros.push(p);
                if (p.filas_cf && p.filas_cf.length) body.cf_registros.push(p);
            }
        }

        const res = await fetch('/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pendientes })
        });

        if (res.ok) {
            const data = await res.json();
            if (data.ok) {
                await limpiarPendientes();
                actualizarBannerOffline();
                return pendientes.length;
            }
        }
        return 0;
    } catch (err) {
        console.warn('[Offline] Error al sincronizar:', err);
        return 0;
    } finally {
        _sincronizando = false;
    }
}

// ── Banner de estado ───────────────────────────────────────────────────────────

/**
 * Actualiza el banner visual de estado online/offline.
 */
async function actualizarBannerOffline() {
    const banner = document.getElementById('offlineBanner');
    if (!banner) return;

    const online     = await isOnline();
    const pendientes = await contarPendientes();

    if (online) {
        if (pendientes > 0) {
            // Hay internet pero quedan pendientes → sincronizar
            banner.className = 'offline-banner syncing';
            banner.innerHTML = `<span>🔄 Sincronizando ${pendientes} registro${pendientes !== 1 ? 's' : ''}…</span>`;
            banner.style.display = 'flex';
            syncPendientes().then(n => {
                if (n > 0) mostrarToast(`✅ ${n} registro${n !== 1 ? 's' : ''} sincronizado${n !== 1 ? 's' : ''} con SharePoint`);
                actualizarBannerOffline();
            });
        } else {
            banner.style.display = 'none';
        }
    } else {
        if (pendientes > 0) {
            banner.className = 'offline-banner offline';
            banner.innerHTML = `<span>📵 Sin conexión — <b>${pendientes}</b> registro${pendientes !== 1 ? 's' : ''} pendiente${pendientes !== 1 ? 's' : ''}</span>`;
        } else {
            banner.className = 'offline-banner offline';
            banner.innerHTML = `<span>📵 Sin conexión — guardando localmente</span>`;
        }
        banner.style.display = 'flex';
    }
}

// ── Toast ──────────────────────────────────────────────────────────────────────

/**
 * Muestra un mensaje toast temporal en la parte superior.
 * @param {string} msg
 * @param {string} tipo - 'success' | 'error' | 'info'
 */
function mostrarToast(msg, tipo = 'success') {
    let toast = document.getElementById('offlineToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'offlineToast';
        document.body.appendChild(toast);
    }
    toast.className = `offline-toast toast-${tipo}`;
    toast.textContent = msg;
    toast.style.display = 'block';
    toast.style.opacity = '1';

    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => { toast.style.display = 'none'; }, 400);
    }, 3500);
}

// ── Estilos del banner y toast ─────────────────────────────────────────────────

(function inyectarEstilos() {
    if (document.getElementById('offline-styles')) return;
    const style = document.createElement('style');
    style.id = 'offline-styles';
    style.textContent = `
        .offline-banner {
            display: none;
            align-items: center;
            justify-content: center;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
            text-align: center;
            gap: 8px;
            transition: background 0.3s;
        }
        .offline-banner.offline {
            background: #fff3cd;
            color: #856404;
            border-bottom: 1px solid #ffc107;
        }
        .offline-banner.syncing {
            background: #d1ecf1;
            color: #0c5460;
            border-bottom: 1px solid #bee5eb;
        }

        #offlineToast {
            display: none;
            position: fixed;
            top: 16px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            padding: 10px 20px;
            border-radius: 24px;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 4px 16px rgba(0,0,0,0.18);
            transition: opacity 0.4s;
            white-space: nowrap;
            max-width: 90vw;
            text-align: center;
        }
        .toast-success { background: #1e7e34; color: #fff; }
        .toast-error   { background: #c82333; color: #fff; }
        .toast-info    { background: #117a8b; color: #fff; }

        .badge-pendiente {
            display: inline-block;
            background: #fd7e14;
            color: #fff;
            border-radius: 10px;
            padding: 1px 8px;
            font-size: 11px;
            font-weight: 700;
            margin-left: 6px;
        }
    `;
    document.head.appendChild(style);
})();

// ── Inicialización automática ──────────────────────────────────────────────────

window.addEventListener('online', async () => {
    console.log('[Offline] Conexión recuperada, sincronizando…');
    await actualizarBannerOffline();
    const n = await syncPendientes();
    if (n > 0) {
        mostrarToast(`✅ ${n} registro${n !== 1 ? 's' : ''} sincronizado${n !== 1 ? 's' : ''} con SharePoint`);
        actualizarBannerOffline();
    }
});

window.addEventListener('offline', () => {
    console.log('[Offline] Sin conexión.');
    actualizarBannerOffline();
});

// Exportar funciones al scope global para uso en templates
window.offlineApp = {
    guardarPendiente,
    leerPendientes,
    contarPendientes,
    borrarPendiente,
    limpiarPendientes,
    isOnline,
    syncPendientes,
    actualizarBannerOffline,
    mostrarToast
};
