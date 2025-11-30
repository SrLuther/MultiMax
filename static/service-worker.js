const CACHE_NAME = 'multimax-cache-v5';
const STATIC_ASSETS = [
  '/static/manifest.json',
  '/static/icons/icon-192-v2.png',
  '/static/icons/icon-512-v2.png',
  '/static/icons/icon-192-maskable-v2.png',
  '/static/icons/icon-512-maskable-v2.png',
  '/static/icons/apple-touch-icon-180-v2.png',
  '/static/favicon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.mode === 'navigate') {
    event.respondWith(fetch(req));
    return;
  }
  event.respondWith(
    caches.match(req).then((response) => response || fetch(req))
  );
});
