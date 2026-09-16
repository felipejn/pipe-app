const CACHE = 'pipe-v2';
const ASSETS = [
  '/',
  '/static/css/pipe.css',
  '/static/manifest.json'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // Rede primeiro para CSS, JS e HTML — garante que as alterações chegam ao browser
  if (['style', 'script', 'document'].includes(e.request.destination)) {
    e.respondWith(
      fetch(e.request).then(resposta => {
        const copia = resposta.clone();
        caches.open(CACHE).then(cache => cache.put(e.request, copia));
        return resposta;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  // Cache primeiro para o resto (ícones, manifestos, etc.)
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
