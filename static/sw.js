const CACHE_NAME = 'hortifruti-v1';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
    // Busca na rede primeiro para evitar telas desatualizadas no celular
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
