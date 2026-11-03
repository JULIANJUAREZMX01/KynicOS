// Service Worker de la consola KYNIKOS: shell offline, sin caché de respuestas del nodo.
const CACHE = 'kynikos-shell-v1';
const SHELL = ['./index.html', './manifest.webmanifest'];

self.addEventListener('install', (ev) => {
  ev.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (ev) => {
  ev.waitUntil(
    caches.keys().then((claves) =>
      Promise.all(claves.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (ev) => {
  const url = new URL(ev.request.url);
  // El nodo y Telegram nunca se cachean: respuestas del modelo deben ser frescas.
  if (ev.request.method !== 'GET' || url.pathname.startsWith('/api/')) return;
  ev.respondWith(
    caches.match(ev.request).then((hit) =>
      hit || fetch(ev.request).then((r) => {
        const copia = r.clone();
        caches.open(CACHE).then((c) => c.put(ev.request, copia)).catch(() => {});
        return r;
      }).catch(() => caches.match('./index.html'))
    )
  );
});
