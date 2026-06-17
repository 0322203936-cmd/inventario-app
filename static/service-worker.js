/**
 * service-worker.js — Service Worker con soporte offline completo
 * 
 * Estrategia: Network-First con fallback a caché
 * - Pre-cachea las páginas principales al instalar
 * - Si hay red → sirve desde red y actualiza caché
 * - Si no hay red → sirve desde caché
 */

const CACHE_NAME    = 'inventario-v3';
const STATIC_ASSETS = [
    '/',
    '/registros',
    '/static/offline.js',
    '/static/manifest.json',
    '/static/icon-192.png',
    '/static/icon-512.png',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'
];

// ── Install: pre-cachear assets ────────────────────────────────────────────────

self.addEventListener('install', (event) => {
    console.log('[SW] Instalando v3…');
    event.waitUntil(
        caches.open(CACHE_NAME).then(async (cache) => {
            for (const url of STATIC_ASSETS) {
                try {
                    await cache.add(url);
                    console.log('[SW] Cacheado:', url);
                } catch (err) {
                    console.warn('[SW] No se pudo cachear:', url, err.message);
                }
            }
        })
    );
    self.skipWaiting();
});

// ── Activate: limpiar cachés viejos ───────────────────────────────────────────

self.addEventListener('activate', (event) => {
    console.log('[SW] Activado v3');
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((k) => k !== CACHE_NAME)
                    .map((k) => {
                        console.log('[SW] Eliminando caché viejo:', k);
                        return caches.delete(k);
                    })
            )
        )
    );
    clients.claim();
});

// ── Fetch: Network-First con fallback a caché ─────────────────────────────────

self.addEventListener('fetch', (event) => {
    const req = event.request;
    const url = new URL(req.url);

    // Solo manejamos GET (POST/DELETE van directo, son peticiones al servidor)
    if (req.method !== 'GET') return;

    // No cachear /ping (siempre debe ir a la red para detectar conectividad real)
    if (url.pathname === '/ping') return;

    // No cachear /sync
    if (url.pathname === '/sync') return;

    // Páginas de editar: cachear dinámicamente
    event.respondWith(networkFirstWithCache(req));
});

async function networkFirstWithCache(req) {
    const cache = await caches.open(CACHE_NAME);
    try {
        // Intentar red
        const networkRes = await fetch(req);
        if (networkRes.ok) {
            // Solo cachear respuestas exitosas
            cache.put(req, networkRes.clone());
        }
        return networkRes;
    } catch {
        // Sin red → buscar en caché
        const cached = await cache.match(req);
        if (cached) {
            console.log('[SW] Sirviendo desde caché:', req.url);
            return cached;
        }
        // Fallback: si es navegación, mostrar la página raíz cacheada
        if (req.mode === 'navigate') {
            const root = await cache.match('/');
            if (root) return root;
        }
        // Sin caché → devolver error
        return new Response(
            '<html><body style="font-family:sans-serif;text-align:center;padding:40px">' +
            '<h2>📵 Sin conexión</h2>' +
            '<p>La página no está disponible sin internet.</p>' +
            '<button onclick="location.reload()" style="padding:10px 20px;margin-top:16px;' +
            'background:#1a73e8;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer">' +
            'Reintentar</button></body></html>',
            {
                status: 503,
                headers: { 'Content-Type': 'text/html; charset=utf-8' }
            }
        );
    }
}
