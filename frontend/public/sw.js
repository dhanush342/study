/**
 * Bharat Tech Atlas — Service Worker v3.0
 * Google Maps-level performance via aggressive caching strategy.
 *
 * Strategy:
 * 1. Static assets (JS/CSS/images): Cache-First (instant load)
 * 2. Map tiles: Cache-First with network fallback (offline maps)
 * 3. API data: Network-First with stale-while-revalidate (fresh + fast)
 * 4. Prefetch: Popular viewport data cached proactively
 */

const CACHE_VERSION = 'bta-v3.0';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const TILE_CACHE = `${CACHE_VERSION}-tiles`;
const API_CACHE = `${CACHE_VERSION}-api`;

// Static assets to precache on install
const PRECACHE_URLS = [
  '/',
  '/index.html',
];

// Cache size limits
const MAX_TILE_CACHE = 500;  // ~50MB of map tiles
const MAX_API_CACHE = 100;
const API_CACHE_TTL = 5 * 60 * 1000; // 5 minutes for API responses

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(key => key !== STATIC_CACHE && key !== TILE_CACHE && key !== API_CACHE)
          .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // ── Map tiles: Cache-First (instant render) ──
  if (url.hostname.includes('carto') || url.hostname.includes('tile') ||
      url.pathname.includes('/tiles/') || url.pathname.endsWith('.pbf')) {
    event.respondWith(cacheFirst(event.request, TILE_CACHE, MAX_TILE_CACHE));
    return;
  }

  // ── Static assets: Cache-First ──
  if (url.pathname.startsWith('/assets/') || url.pathname.endsWith('.js') ||
      url.pathname.endsWith('.css') || url.pathname.endsWith('.woff2')) {
    event.respondWith(cacheFirst(event.request, STATIC_CACHE));
    return;
  }

  // ── API calls: Stale-While-Revalidate (fast + fresh) ──
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(staleWhileRevalidate(event.request, API_CACHE, API_CACHE_TTL));
    return;
  }

  // ── Everything else: Network-First ──
  event.respondWith(networkFirst(event.request));
});

// ─── Caching Strategies ──────────────────────────────────────────────────────

async function cacheFirst(request, cacheName, maxEntries = null) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
      if (maxEntries) trimCache(cacheName, maxEntries);
    }
    return response;
  } catch {
    return new Response('Offline', { status: 503 });
  }
}

async function staleWhileRevalidate(request, cacheName, ttl) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  // Return cached immediately if fresh enough
  const fetchPromise = fetch(request).then(response => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => cached);

  // Return stale data instantly, update in background
  return cached || fetchPromise;
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response('Offline', { status: 503 });
  }
}

async function trimCache(cacheName, maxEntries) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (keys.length > maxEntries) {
    // Delete oldest entries (FIFO)
    const deleteCount = keys.length - maxEntries;
    for (let i = 0; i < deleteCount; i++) {
      await cache.delete(keys[i]);
    }
  }
}

// ─── Prefetch popular data on idle ──────────────────────────────────────────

self.addEventListener('message', (event) => {
  if (event.data?.type === 'PREFETCH_VIEWPORT') {
    // Prefetch common viewport data
    const urls = [
      '/api/entities/clusters?min_lng=68&max_lng=97&min_lat=6&max_lat=37&zoom=4.5',
      '/api/entities/facets',
      '/api/entities/analytics/overview',
    ];
    urls.forEach(url => {
      fetch(url).then(resp => {
        if (resp.ok) {
          caches.open(API_CACHE).then(cache => cache.put(url, resp));
        }
      }).catch(() => {});
    });
  }
});
