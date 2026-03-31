const CACHE_NAME = "inventario-v1";

self.addEventListener("install", (event) => {
    console.log("[SW] Instalado");
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    console.log("[SW] Activado");
    event.waitUntil(clients.claim());
});

// ⚠️ Este evento fetch es OBLIGATORIO para que Chrome permita instalar la PWA
self.addEventListener("fetch", (event) => {
    // Deja pasar todas las peticiones normalmente (sin cache agresivo)
    event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
