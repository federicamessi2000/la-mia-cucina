var CACHE = 'cucina-v30';
var PRECACHE = ['./index.html', './i18n.js', './manifest.json', './icon-192.png', './icon-512.png'];
// Librerie Firebase (versionate) e font Google: prese dalla cache se ci sono, così l'app si apre anche offline
var CDN = /^https:\/\/(www\.gstatic\.com\/firebasejs\/|fonts\.googleapis\.com\/|fonts\.gstatic\.com\/)/;

self.addEventListener('install', function(e) {
  e.waitUntil(caches.open(CACHE).then(function(c) { return c.addAll(PRECACHE); }));
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(keys.filter(function(k) { return k !== CACHE; }).map(function(k) { return caches.delete(k); }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function(e) {
  // Solo GET: la Cache API non può salvare POST & co.
  if (e.request.method !== 'GET') { return; }
  var url = e.request.url;
  if (CDN.test(url)) {
    e.respondWith(caches.match(e.request).then(function(hit) {
      return hit || fetch(e.request).then(function(r) {
        if (r.ok) {
          var clone = r.clone();
          caches.open(CACHE).then(function(c) { c.put(e.request, clone); });
        }
        return r;
      });
    }));
    return;
  }
  if (
    url.includes('firebaseio.com') ||
    url.includes('firebasedatabase.app') ||
    url.includes('googleapis.com') ||
    url.includes('gstatic.com') ||
    url.includes('generativelanguage') ||
    url.includes('allorigins') ||
    url.includes('corsproxy')
  ) { return; }

  e.respondWith(
    fetch(e.request).then(function(r) {
      if (r.ok) {
        var clone = r.clone();
        caches.open(CACHE).then(function(c) { c.put(e.request, clone); });
      }
      return r;
    }).catch(function() {
      return caches.match(e.request);
    })
  );
});
