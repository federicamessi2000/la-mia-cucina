// Runs sw.js in a VM with a fake browser and checks which request it fetches.
const fs = require('fs'), vm = require('vm'), assert = require('assert'), path = require('path');

const handlers = {}, fetched = [];
const ctx = {
  self: { location: { origin: 'https://federicamessi2000.github.io' }, addEventListener: (t, h) => { handlers[t] = h; }, skipWaiting() {}, clients: { claim() {} } },
  caches: { open: () => Promise.resolve({ put() {}, addAll() {} }), match: () => Promise.resolve(undefined), keys: () => Promise.resolve([]) },
  fetch: req => { fetched.push(req); return Promise.resolve(new Response('ok', { status: 200 })); },
  Request, Response, Promise, console,
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'sw.js'), 'utf8'), ctx, { filename: 'sw.js' });
const fetchEvent = request => { let p; handlers.fetch({ request, respondWith: x => { p = x; } }); return p; };

(async () => {
  await fetchEvent({ method: 'GET', url: 'https://federicamessi2000.github.io/la-mia-cucina/i18n.js' });
  assert(fetched[0] instanceof Request && fetched[0].cache === 'no-cache', "the app's own files skip the browser's HTTP cache");
  console.log('ok - own files are fetched with cache: no-cache');

  const photo = { method: 'GET', url: 'https://www.example.com/foto.jpg', mode: 'no-cors' };
  await fetchEvent(photo);
  assert.strictEqual(fetched[1], photo, 'requests to other sites are passed on unchanged');
  console.log('ok - photos from other sites are fetched exactly as requested');

  const before = fetched.length;
  assert.strictEqual(fetchEvent({ method: 'POST', url: 'https://federicamessi2000.github.io/x' }), undefined);
  assert.strictEqual(fetched.length, before, 'POST is left to the browser');
  console.log('ok - non-GET requests are not touched');

  console.log('\n3 service worker tests passed');
})().catch(e => { console.error('FAILED:', e); process.exit(1); });
