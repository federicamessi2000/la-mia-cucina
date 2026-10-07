var CACHE = 'cucina-v41';
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

  // File dell'app: sempre l'ultima versione dalla rete, saltando la cache HTTP del browser (GitHub Pages la tiene
  // 10 minuti): così dopo un aggiornamento pagina e testi (i18n.js) non restano di versioni diverse
  var own = url.indexOf(self.location.origin + '/') === 0;
  e.respondWith(
    fetch(own ? new Request(url, { cache: 'no-cache', credentials: 'same-origin' }) : e.request).then(function(r) {
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

// Promemoria del congelatore (notifiche dal workflow GitHub): ogni push mostra la sua notifica;
// il tocco porta in primo piano l'app se è aperta, se no la apre
self.addEventListener('push', function(e) {
  var d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { d = { body: e.data ? e.data.text() : '' }; }
  e.waitUntil(self.registration.showNotification(d.title || 'Al Dente', {
    body: d.body || '', icon: 'icon-192.png', tag: d.tag || 'al-dente', data: { url: d.url || './' }
  }));
});

self.addEventListener('notificationclick', function(e) {
  e.notification.close();
  var url = new URL((e.notification.data && e.notification.data.url) || './', self.registration.scope).href;
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(list) {
    for (var i = 0; i < list.length; i++) {
      if (list[i].url.indexOf(self.registration.scope) === 0 && 'focus' in list[i]) { return list[i].focus(); }
    }
    return self.clients.openWindow(url);
  }));
});
