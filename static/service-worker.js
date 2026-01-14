const CACHE_VERSION = 'v10';
const STATIC_CACHE = `multimax-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `multimax-dynamic-${CACHE_VERSION}`;
const API_CACHE = `multimax-api-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  '/static/manifest.json',
  '/static/css/design-system.css',
  '/static/multimax-estilo.css',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/icon-192-maskable.png',
  '/static/icons/icon-512-maskable.png',
  '/static/icons/apple-touch-icon-180.png',
  '/static/icons/favicon.ico',
  '/static/icons/logo-user.png'
];

const API_ROUTES = [
  '/api/v1/notifications',
  '/api/v1/search'
];

const CACHE_STRATEGIES = {
  cacheFirst: async (request, cacheName) => {
    const cached = await caches.match(request);
    if (cached) return cached;

    try {
      const response = await fetch(request);
      if (response.ok) {
        const cache = await caches.open(cacheName);
        cache.put(request, response.clone());
      }
      return response;
    } catch (error) {
      return new Response('Offline', { status: 503, statusText: 'Offline' });
    }
  },

  networkFirst: async (request, cacheName, timeout = 3000) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(request, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (response.ok) {
        const cache = await caches.open(cacheName);
        cache.put(request, response.clone());
      }
      return response;
    } catch (error) {
      const cached = await caches.match(request);
      if (cached) return cached;

      return new Response(JSON.stringify({ error: 'Offline', cached: false }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  },

  staleWhileRevalidate: async (request, cacheName) => {
    const cached = await caches.match(request);

    const fetchPromise = fetch(request).then(response => {
      if (response.ok) {
        const cache = caches.open(cacheName).then(c => c.put(request, response.clone()));
      }
      return response;
    }).catch(() => cached);

    return cached || fetchPromise;
  }
};

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys
          .filter(key => !key.includes(CACHE_VERSION))
          .map(key => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(CACHE_STRATEGIES.cacheFirst(request, STATIC_CACHE));
    return;
  }

  if (API_ROUTES.some(route => url.pathname.startsWith(route))) {
    event.respondWith(CACHE_STRATEGIES.networkFirst(request, API_CACHE, 2000));
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/') || new Response('Offline'))
    );
    return;
  }

  event.respondWith(CACHE_STRATEGIES.staleWhileRevalidate(request, DYNAMIC_CACHE));
});

self.addEventListener('message', event => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }

  if (event.data === 'clearCache') {
    caches.keys().then(keys => {
      keys.forEach(key => caches.delete(key));
    });
  }
});

self.addEventListener('push', event => {
  const data = event.data?.json() || {};
  const title = data.title || 'MultiMax';
  const options = {
    body: data.body || 'Você tem uma nova notificação',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/'
    }
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientList => {
        const url = event.notification.data.url;

        for (const client of clientList) {
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }

        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});
