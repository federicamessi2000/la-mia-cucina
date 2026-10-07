// Loads index.html's scripts in a Node VM with fake DOM + fake Firebase, then exercises the new logic.
// Every DB write is recorded instead of sent anywhere.
const fs = require('fs'), vm = require('vm'), assert = require('assert'), path = require('path');
const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);

// ---------- fake DOM ----------
const els = {};
function el(id) {
  if (!els[id]) {
    const classes = new Set();
    els[id] = {
      id, style: {}, value: '', textContent: '', innerHTML: '', dataset: {}, disabled: false,
      classList: { toggle(c, on) { if (on === undefined) on = !classes.has(c); on ? classes.add(c) : classes.delete(c); }, add(c) { classes.add(c); }, remove(c) { classes.delete(c); }, contains(c) { return classes.has(c); } },
      focus() {}, appendChild() {}, remove() {}, insertAdjacentElement() {}, closest() { return null; }, querySelector() { return null; }, setAttribute() {}, getAttribute() { return null; },
    };
  }
  return els[id];
}
const documentStub = {
  getElementById: el, querySelectorAll: () => [], querySelector: () => null,
  addEventListener() {}, createElement: () => el('_new' + Math.random()), body: { appendChild() {}, removeChild() {} },
  visibilityState: 'visible', documentElement: {},
};

// ---------- fake Firebase ----------
const writes = [], listeners = [];
let pushN = 0, authCb = null;
function makeRef(path) {
  const r = {
    path, key: path.split('/').pop(),
    child: p => makeRef(path + '/' + p),
    push(v) {
      const k = '-Ktest' + String(++pushN).padStart(14, '0');
      const nr = makeRef(path + '/' + k);
      if (v !== undefined) writes.push({ op: 'push', path: path + '/' + k, v });
      const p = Promise.resolve(makeRef(path + '/' + k));  // resolves to a plain ref, like Firebase's ThenableReference
      nr.then = p.then.bind(p); nr.catch = p.catch.bind(p);
      return nr;
    },
    set(v) { writes.push({ op: 'set', path, v: JSON.parse(JSON.stringify(v)) }); return Promise.resolve(); },
    update(v) { writes.push({ op: 'update', path, v: JSON.parse(JSON.stringify(v)) }); return Promise.resolve(); },
    remove() { writes.push({ op: 'remove', path }); return Promise.resolve(); },
    on(ev, cb, err) { listeners.push({ path, ev, cb, err }); return cb; },
    once(ev, cb, err) { listeners.push({ path, ev: 'once:' + ev, cb, err }); return Promise.resolve({ exists: () => false, val: () => null, forEach() {} }); },
    off() { for (let i = listeners.length - 1; i >= 0; i--) if (listeners[i].path === path) listeners.splice(i, 1); },
    get: () => Promise.resolve({ exists: () => false }),
  };
  return r;
}
const firebaseStub = {
  initializeApp() {},
  auth: Object.assign(() => ({ onAuthStateChanged(cb) { authCb = cb; }, signInWithPopup: () => sandbox._popup(), signInWithRedirect: () => { sandbox._redirects++; return Promise.resolve(); }, getRedirectResult: () => Promise.resolve(null), signOut() {} }), { GoogleAuthProvider: function () {} }),
  database: () => ({ ref: p => makeRef(p || '') }),
};
const store = {};
const sandbox = {
  document: documentStub, firebase: firebaseStub, console,
  navigator: { userAgent: 'node-test', onLine: true, clipboard: { writeText: () => Promise.resolve() }, share: o => { sandbox._shared.push(o); return Promise.resolve(); } },
  _shared: [], crypto: globalThis.crypto, prompt: () => sandbox._promptAnswer, _promptAnswer: null,
  _popup: () => Promise.resolve(), _redirects: 0,
  localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } },
  location: { href: '' }, setTimeout: (...a) => global.setTimeout(...a), clearTimeout, setInterval, clearInterval,
  alert: m => { sandbox._alerts.push(m); }, confirm: () => true, _alerts: [],
  matchMedia: () => ({ matches: false }), scrollTo() {}, innerWidth: 390, innerHeight: 844, addEventListener() {},
};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(ROOT, 'i18n.js'), 'utf8'), sandbox, { filename: 'i18n.js' });
blocks.forEach((b, i) => vm.runInContext(b, sandbox, { filename: 'inline' + i + '.js' }));
const run = code => vm.runInContext(code, sandbox);
const fire = (path, ev, key, val) => listeners.filter(l => l.path === path && l.ev === ev).forEach(l => l.cb({ key, val: () => val }));

// tests run strictly one after another (async ones are awaited), so they can't race on shared state
let passed = 0; const queue = [];
function test(name, fn) { queue.push([name, fn]); }

// ---------- sign in as a friend (non-admin) ----------
authCb({ uid: 'friendUid', email: 'amica@gmail.com', displayName: 'Amica Test' });

test('listeners on shared and private recipes', () => {
  assert(listeners.some(l => l.path === 'recipes' && l.ev === 'child_added'));
  assert(listeners.some(l => l.path === 'users/friendUid/recipes' && l.ev === 'child_added'));
  assert(!writes.some(w => w.path.startsWith('recipes')), 'no writes to recipes at startup (seed/migration removed)');
});

test('merge shared + private, removal by id + origin', () => {
  fire('recipes', 'child_added', 'pubA', { nome: 'Pasta mamma', fonte: 'mamma', ingredienti: [{ qty: 100, unit: 'g', name: 'pasta' }], procedimento: '1. cuoci' });
  fire('recipes', 'child_added', 'pubOwn', { nome: 'Torta amica', ownerUid: 'friendUid', fonte: 'internet' });
  fire('users/friendUid/recipes', 'child_added', 'priv1', { nome: 'Segreta', ownerUid: 'friendUid' });
  fire('users/friendUid/recipes', 'child_added', 'pubA', { nome: 'Copia con stessa chiave' });
  assert.strictEqual(run('recipes.length'), 4);
  fire('users/friendUid/recipes', 'child_removed', 'pubA', null);
  assert.strictEqual(run('recipes.length'), 3);
  assert.strictEqual(run("recipes.find(r=>r.id==='pubA')._priv"), false, 'shared one kept');
});

test('canEdit: friend edits own + private, not legacy', () => {
  assert.strictEqual(run("canEdit(recipes.find(r=>r.id==='pubA'))"), false);
  assert.strictEqual(run("canEdit(recipes.find(r=>r.id==='pubOwn'))"), true);
  assert.strictEqual(run("canEdit(recipes.find(r=>r.id==='priv1'))"), true);
});

test('recipe modal hides edit/delete on legacy recipe, escapes fonte', () => {
  run("recipes.push({id:'x1',nome:'Hack',fonte:'\"><img src=x onerror=alert(1)>',_priv:false})");
  run("openRecipe('x1')");
  const body = el('modal-body').innerHTML;
  assert(!body.includes('onerror=alert'), 'fonte not injected');
  assert(!body.includes('Modifica'), 'no edit button');
  run("recipes.push({id:\"bad');alert(1);//\",nome:'Bad id'})");
  assert.strictEqual(run("safeId(\"bad');alert(1);//\")"), '');
});

test('new private recipe goes to users/<uid>/recipes with ownerUid; choice remembered', () => {
  writes.length = 0;
  run("resetRecipeForm()");
  assert.strictEqual(run('recipeVis'), 'priv', 'first time private');
  el('r-nome').value = 'Nuova privata';
  run("saveRecipe()");
  const w = writes.find(w => w.op === 'push');
  assert(w && w.path.startsWith('users/friendUid/recipes/'), JSON.stringify(writes));
  assert.strictEqual(w.v.ownerUid, 'friendUid');
  run("setRecipeVis('pub')"); el('r-nome').value = 'Nuova condivisa';
  writes.length = 0; run("saveRecipe()");
  const w2 = writes.find(w => w.op === 'push');
  assert(w2.path.startsWith('recipes/'), w2.path);
  run("resetRecipeForm()");
  assert.strictEqual(run('recipeVis'), 'pub', 'last choice remembered');
});

test('switching own shared recipe to private moves it atomically with the same key', () => {
  writes.length = 0;
  run("openEditRecipe('pubOwn')");
  run("setRecipeVis('priv')");
  el('r-nome').value = 'Torta amica';
  run("saveRecipe()");
  const u = writes.find(w => w.op === 'update' && w.path === '');
  assert(u, JSON.stringify(writes));
  assert.strictEqual(u.v['recipes/pubOwn'], null);
  assert.strictEqual(u.v['users/friendUid/recipes/pubOwn'].ownerUid, 'friendUid');
  assert.strictEqual(u.v['users/friendUid/recipes/pubOwn'].nome, 'Torta amica');
});

test('editing keeps text servings and saves the author', () => {
  run("recipes.push({id:'m1',nome:'Crepes',porzioni:'10-15 crepes',ownerUid:'friendUid',_priv:false})");
  run("openEditRecipe('m1')");
  assert.strictEqual(el('r-porzioni').value, 10);
  el('r-autore').value = 'Zia';
  writes.length = 0; run("saveRecipe()");
  const u = writes.find(w => w.op === 'update');
  assert.strictEqual(u.v.porzioni, '10-15 crepes');
  assert.strictEqual(u.v.addedBy, 'Zia');
});

test('text import keeps steps with "cottura" and reads PER 4 PERSONE', () => {
  const r = run(`parseRecipeText("Risotto\\nPER 4 PERSONE\\nTempo: 30 min\\n320 g di riso\\nProcedimento\\n1. Tostare il riso\\n2. A fine cottura mantecare")`);
  assert.strictEqual(r.porzioni, 4);
  assert.strictEqual(r.tempo, '30 min');
  assert(r.procedimento.includes('fine cottura'), r.procedimento);
});

// ---------- planner ----------
const today = new Date(); const key = today.getFullYear() + '-' + (today.getMonth() + 1) + '-' + today.getDate();
test('several dishes: render, remove middle one -> renumbered', () => {
  run(`planner=${JSON.stringify({ [key]: { pranzo: 'Pasta mamma', pranzo_id: 'pubA', pranzo_porzioni: 2, pranzo2: '__ingredienti', pranzo2_ings: [{ name: 'Mele', qty: 2, unit: 'n°' }], pranzo3: 'Segreta', pranzo3_id: 'priv1', pranzo3_porzioni: 1, pranzo3_skip: ['sale'] } })}`);
  run("plannerView='week';currentMonth=new Date();renderPlanner()");
  const h = el('planner-days').innerHTML;
  assert(h.includes('Pasta mamma') && h.includes('Segreta') && h.includes('🧺 Mele') && h.includes('+ altro piatto'), h.slice(0, 500));
  assert(!h.includes('__ingredienti'), 'no raw sentinel');
  writes.length = 0; run(`quickClearMeal('${key}','pranzo2')`);
  const s = writes.find(w => w.op === 'set');
  assert.strictEqual(s.v.pranzo, 'Pasta mamma');
  assert.strictEqual(s.v.pranzo2, 'Segreta');
  assert.strictEqual(s.v.pranzo2_id, 'priv1');
  assert.deepStrictEqual(s.v.pranzo2_skip, ['sale']);
  assert(!('pranzo3' in s.v) && !('pranzo2_ings' in s.v), JSON.stringify(s.v));
  run("renderPlannerMonth()");
  assert(el('planner-days').innerHTML.includes(' / '), 'month view lists extra dishes');
});

test('fuori casa on dish 1 removes the others; tile hidden for extra dishes', () => {
  run(`planner=${JSON.stringify({ [key]: { cena: 'Pasta mamma', cena_id: 'pubA', cena2: 'Segreta', cena2_id: 'priv1' } })}`);
  run(`openPickModal('${key}','cena2')`); assert.strictEqual(el('pick-fc-tile').style.display, 'none');
  run(`openPickModal('${key}','cena')`); assert.strictEqual(el('pick-fc-tile').style.display, 'flex');
  writes.length = 0; run('setFuoriCasa()');
  const s = writes.find(w => w.op === 'set');
  assert.strictEqual(s.v.cena, '__fuori_casa');
  assert(!('cena2' in s.v) && !('cena2_id' in s.v), JSON.stringify(s.v));
});

test('copy previous week drops freezer links', () => {
  const d = new Date(); d.setDate(d.getDate() - 7);
  const pk = d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
  run(`planner=${JSON.stringify({ [pk]: { pranzo: '__dal_freezer', pranzo_freezer_id: 'f1', pranzo_freezer_name: 'Ragù', pranzo_freezer_data: { name: 'Ragù' }, pranzo_freezer_qty_used: 1 } })}`);
  writes.length = 0; run("plannerView='week';currentMonth=new Date();copyPrevWeek()");
  const u = writes.find(w => w.op === 'update');
  const copied = Object.values(u.v)[0];
  assert.strictEqual(copied.pranzo_freezer_name, 'Ragù');
  assert(!('pranzo_freezer_data' in copied) && !('pranzo_freezer_id' in copied), JSON.stringify(copied));
});

test('fill from planner: one batched update, all dishes, current weeks only, past untouched', () => {
  const past = new Date(); past.setDate(past.getDate() - 14);
  const pastKey = past.getFullYear() + '-' + (past.getMonth() + 1) + '-' + past.getDate();
  run(`planner=${JSON.stringify({ [key]: { pranzo: 'Pasta mamma', pranzo_id: 'pubA', pranzo_porzioni: 2, pranzo2: '__ingredienti', pranzo2_ings: [{ name: 'Mele', qty: 2, unit: 'n°' }] }, [pastKey]: { cena: 'Pasta mamma', cena_id: 'pubA' } })}`);
  const mk = (d => { const day = d.getDay(); const m = new Date(d.getFullYear(), d.getMonth(), d.getDate() - (day === 0 ? 6 : day - 1)); return m.getFullYear() + '-' + (m.getMonth() + 1) + '-' + m.getDate(); });
  run(`shopping=${JSON.stringify([{ id: 'old1', fromPlanner: true, weekSort: mk(past), ingName: 'x' }, { id: 'cur1', fromPlanner: true, weekSort: mk(today), ingName: 'y' }, { id: 'man1', weekSort: mk(today), ingName: 'z' }])}`);
  writes.length = 0; run('syncPlannerToShop()');
  const ups = writes.filter(w => w.op === 'update');
  assert.strictEqual(ups.length, 1, JSON.stringify(writes));
  const v = ups[0].v;
  assert.strictEqual(v.cur1, null); assert(!('old1' in v) && !('man1' in v));
  const items = Object.values(v).filter(Boolean);
  // recipe without servings counts as 4: 100 g × 2 people ÷ 4 = 50 g
  assert(items.some(i => i.ingName === 'pasta' && i.ingQty === 50), JSON.stringify(items));
  assert(items.some(i => i.ingName === 'mele'));
  assert(items.every(i => i.weekSort === mk(today)), 'past week not regenerated');
});

test('family create writes familyCode only after the member write', async () => {
  writes.length = 0; run('createFamily()');
  await new Promise(r => setTimeout(r, 10));
  const i1 = writes.findIndex(w => w.path.startsWith('families/')), i2 = writes.findIndex(w => w.path.endsWith('/familyCode'));
  assert(i1 >= 0 && i2 > i1, JSON.stringify(writes));
});

test('bug report is saved in the app (no email, no mail app), with details', async () => {
  run("logErr('prova errore')");
  el('bug-text').value = 'Non si apre la ricetta';
  writes.length = 0; sandbox.location.href = '';
  run('sendBugReport()'); await new Promise(r => setTimeout(r, 10));
  const w = writes.find(w => w.op === 'push' && w.path.startsWith('bugReports/'));
  assert(w, JSON.stringify(writes));
  assert.strictEqual(w.v.uid, 'friendUid'); assert.strictEqual(w.v.text, 'Non si apre la ricetta');
  assert(w.v.details.includes('Versione: ') && w.v.details.includes('prova errore'), w.v.details);
  assert.strictEqual(sandbox.location.href, '', 'no mailto');
  assert(!/hotmail/.test(html.replace("gmmagnani@hotmail.it", '')), 'no personal email in the page');
  assert.strictEqual(el('reports-entry').innerHTML, '', 'a friend sees no inbox');
});

test('only Federica gets the inbox, with a badge for new reports', () => {
  authCb(null);
  authCb({ uid: 'fedeUid', email: 'federicamessi2000@gmail.com', displayName: 'Federica' });
  assert(listeners.some(l => l.path === 'bugReports' && l.ev === 'value'), 'admin listens to reports');
  const snap = { forEach(f) { [{ key: 'r1', val: () => ({ text: 'Bug A', name: 'Amica', email: 'a@b.c', createdAt: 2, status: 'nuova' }) }, { key: 'r2', val: () => ({ text: 'Bug B', createdAt: 1, status: 'risolta' }) }].forEach(f); } };
  listeners.filter(l => l.path === 'bugReports' && l.ev === 'value').forEach(l => l.cb(snap));
  assert(el('reports-entry').innerHTML.includes('1 da vedere'), el('reports-entry').innerHTML);
  assert.strictEqual(el('reports-dot').style.display, 'block');
  run('openReports()');
  assert(el('reports-list').innerHTML.includes('Bug A') && el('reports-list').innerHTML.includes('Riapri'));
  writes.length = 0; run("toggleReport('r1')");
  assert.deepStrictEqual(writes[0], { op: 'set', path: 'bugReports/r1/status', v: 'risolta' });
  authCb(null);
  assert.strictEqual(el('reports-dot').style.display, 'none', 'badge cleared on sign-out');
  authCb({ uid: 'friendUid', email: 'amica@gmail.com', displayName: 'Amica Test' });
});

test('sign-out drops private recipes and detaches listeners', () => {
  authCb(null);
  assert.strictEqual(run('recipes.length'), 0);
  assert(!listeners.some(l => l.path === 'users/friendUid/recipes'), 'private listener detached');
});

test('load error shows a message instead of the endless spinner', () => {
  authCb({ uid: 'u2', email: 'x@y.z', displayName: 'X' });
  listeners.filter(l => l.path === 'recipes' && l.ev === 'child_added').forEach(l => l.err({ code: 'PERMISSION_DENIED' }));
  return new Promise(r => setTimeout(() => { run('renderRecipeHome()'); assert(el('recipe-home').innerHTML.includes('Non riesco a caricare'), el('recipe-home').innerHTML); r(); }, 120));
});

// ---------- round 2 fixes ----------
test('round 2: sign-out also clears planner, shopping, freezer, favourites', () => {
  run(`planner={x:{pranzo:'A'}};shopping=[{id:'s1'}];freezer=[{id:'f'}];userFavorites={r:true}`);
  writes.length = 0;
  authCb(null);
  assert.strictEqual(writes.length, 0, 'signing out must not write or delete anything in the database: ' + JSON.stringify(writes));
  assert.strictEqual(run('Object.keys(planner).length + shopping.length + freezer.length + Object.keys(userFavorites).length'), 0);
  authCb({ uid: 'friendUid', email: 'amica@gmail.com', displayName: 'Amica Test' });
});

test('round 2: Condividi sends only the week on screen', () => {
  const mk = run('shopWeekSort()');
  run(`shopping=${JSON.stringify([{ id: 'a', ingName: 'mele', text: 'mele', weekSort: mk, category: 'Frutta' }, { id: 'b', ingName: 'pere', text: 'pere', weekSort: '2020-1-6', category: 'Frutta' }])}`);
  el('shop-week-label').textContent = '28 set – 4 ott';
  sandbox._shared.length = 0; run('shareShopList()');
  const t = sandbox._shared[0].text;
  assert(t.includes('mele') && !t.includes('pere'), t);
});

test('round 2: Copia settimana fills only empty meals, never overwrites', () => {
  const d = new Date(); d.setDate(d.getDate() - 7);
  const pk = d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
  const t = new Date(); const tk = t.getFullYear() + '-' + (t.getMonth() + 1) + '-' + t.getDate();
  run(`planner=${JSON.stringify({ [pk]: { pranzo: 'A', pranzo_id: 'pubA', pranzo2: 'B', cena: 'C', cena_porzioni: 3 }, [tk]: { pranzo: 'Già deciso', pranzo_porzioni: 2 } })}`);
  writes.length = 0; run("plannerView='week';currentMonth=new Date();copyPrevWeek()");
  const v = writes.find(w => w.op === 'update').v[tk];
  assert.strictEqual(v.pranzo, 'Già deciso'); assert(!('pranzo2' in v), 'lunch not merged into a planned lunch');
  assert.strictEqual(v.cena, 'C'); assert.strictEqual(v.cena_porzioni, 3);
});

test('round 2: freezer "Usa" on grams asks how much and subtracts', () => {
  run(`freezer=${JSON.stringify([{ id: 'f1', name: 'Ragù', qty: 500, unit: 'g' }, { id: 'f2', name: 'Polpette', qty: 3, unit: 'n°' }])}`);
  sandbox._promptAnswer = '200'; writes.length = 0;
  run("useFreezerItem({stopPropagation(){}},'f1')");
  assert.deepStrictEqual(writes[0], { op: 'set', path: 'users/friendUid/freezer/f1/qty', v: 300 });
  sandbox._promptAnswer = '500'; writes.length = 0;
  run("useFreezerItem({stopPropagation(){}},'f1')");
  assert.strictEqual(writes[0].op, 'remove');
  writes.length = 0; run("useFreezerItem({stopPropagation(){}},'f2')");
  assert.deepStrictEqual(writes[0], { op: 'set', path: 'users/friendUid/freezer/f2/qty', v: 2 }, 'pieces still go down by one');
});

test('round 2: category is saved and prefilled', () => {
  run('resetRecipeForm()');
  assert(el('r-categoria').innerHTML.includes('Primi'), 'options rendered');
  el('r-nome').value = 'Con categoria'; el('r-categoria').value = 'Primi';
  writes.length = 0; run('saveRecipe()');
  assert.strictEqual(writes.find(w => w.op === 'push').v.categoria, 'Primi');
  run("recipes.push({id:'c1',nome:'Vecchia',categoria:'Categoria strana',ownerUid:'friendUid',_priv:false})");
  run("openEditRecipe('c1')");
  assert(el('r-categoria').innerHTML.includes('Categoria strana'), 'unknown old category kept as an option');
});

test('round 2: new family code is random, checked, then member before familyCode', async () => {
  writes.length = 0; run('createFamily()');
  await new Promise(r => setTimeout(r, 20));
  const m = writes.find(w => /^families\/[A-HJ-NP-Z2-9]{6}\/members\/friendUid$/.test(w.path));
  assert(m, JSON.stringify(writes));
  const code = m.path.split('/')[1];
  const f = writes.findIndex(w => w.path.endsWith('/familyCode'));
  assert(f > writes.indexOf(m) && writes[f].v === code, JSON.stringify(writes));
  assert.notStrictEqual(code, 'FRIEND', 'not derived from the uid');
});

// ---------- round 3 fixes ----------
test('round 3: servings scaling + "già in casa" counts only for its own day', () => {
  const d0 = new Date(), d1 = new Date(); d1.setDate(d1.getDate() + 1);
  const k = d => d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
  run(`recipes.push({id:'carb',nome:'Carbonara',porzioni:4,ingredienti:[{qty:400,unit:'g',name:'spaghetti'},{qty:200,unit:'g',name:'guanciale'}],_priv:false})`);
  run(`planner=${JSON.stringify({ [k(d0)]: { cena: 'Carbonara', cena_id: 'carb', cena_porzioni: 2, cena_skip: ['guanciale'] }, [k(d1)]: { pranzo: 'Carbonara', pranzo_id: 'carb', pranzo_porzioni: 2 } })}`);
  run('shopping=[]'); writes.length = 0; run('syncPlannerToShop()');
  const items = Object.values(writes.find(w => w.op === 'update').v).filter(Boolean);
  const byName = n => items.filter(i => i.ingName === n).reduce((t, i) => t + i.ingQty, 0);
  const sameWeek = (() => { const m = x => { const y = new Date(x); const dd = y.getDay(); y.setDate(y.getDate() - (dd === 0 ? 6 : dd - 1)); return y.toDateString(); }; return m(d0) === m(d1); })();
  if (sameWeek) {
    assert.strictEqual(byName('spaghetti'), 400, 'carbonara for 4 planned 2+2 → 400 g');
    assert.strictEqual(byName('guanciale'), 100, 'guanciale skipped on day 1 only → 100 g');
  } else {
    assert.strictEqual(byName('spaghetti'), 400); assert.strictEqual(byName('guanciale'), 100);
  }
});

test('round 3: "Rimuovi spuntati" only clears the week on screen', () => {
  const mk = run('shopWeekSort()');
  run(`shopping=${JSON.stringify([{ id: 'c1', checked: true, weekSort: mk }, { id: 'c2', checked: true, weekSort: '2020-1-6' }, { id: 'c3', checked: false, weekSort: mk }])}`);
  writes.length = 0; run('clearChecked()');
  assert.deepStrictEqual(writes.map(w => w.path.split('/').pop()), ['c1']);
});

test('round 3: login falls back to redirect, or offers the alternative button', async () => {
  sandbox._popup = () => Promise.reject({ code: 'auth/popup-blocked' });
  sandbox._redirects = 0; run('signInWithGoogle()'); await new Promise(r => setTimeout(r, 10));
  assert.strictEqual(sandbox._redirects, 1, 'blocked popup → redirect');
  sandbox._popup = () => Promise.reject({ code: 'auth/popup-closed-by-user' });
  el('login-alt-btn').style.display = 'none'; run('signInWithGoogle()'); await new Promise(r => setTimeout(r, 10));
  assert.strictEqual(el('login-alt-btn').style.display, 'block', 'closed popup → alternative button shown');
  assert.strictEqual(sandbox._redirects, 1, 'no automatic redirect when the user closed the popup');
});

// ---------- languages ----------
test('language: phone language first, then the saved choice; anything else is Italian', () => {
  const src = fs.readFileSync(path.join(ROOT, 'i18n.js'), 'utf8');
  const pick = (nav, saved) => {
    const st = saved ? { lmc_lang: saved } : {};
    const c = vm.createContext({ navigator: nav, localStorage: { getItem: k => (k in st ? st[k] : null) }, document: { documentElement: {} } });
    vm.runInContext(src, c); return vm.runInContext('LANG+"|"+LOCALE', c);
  };
  assert.strictEqual(pick({ language: 'de-CH' }), 'de|de-CH');
  assert.strictEqual(pick({ languages: ['en-US', 'it'], language: 'en-US' }), 'en|en-GB');
  assert.strictEqual(pick({ language: 'fr-CH' }), 'it|it-IT');
  assert.strictEqual(pick({ language: 'de-CH' }, 'it'), 'it|it-IT', 'saved choice wins');
  const c = vm.createContext({ navigator: {}, localStorage: { getItem() { throw new Error('blocked'); } }, document: { documentElement: {} } });
  vm.runInContext(src, c); assert.strictEqual(vm.runInContext('LANG', c), 'it', 'storage blocked → no crash');
});

test('language: setLang switches the app live and is remembered on this phone', () => {
  run("plannerView='week';currentMonth=new Date();planner={};renderPlanner();renderRecipes();resetRecipeForm()");
  run("setLang('de')");
  assert.strictEqual(store.lmc_lang, 'de');
  assert.strictEqual(run('document.documentElement.lang'), 'de');
  assert.strictEqual(el('planner-view-btn').textContent, 'Monatsansicht');
  assert(el('planner-days').innerHTML.includes('Mittag') && el('planner-days').innerHTML.includes('Hinzufügen'), el('planner-days').innerHTML.slice(0, 300));
  assert(/Montag, \d+\./.test(el('planner-days').innerHTML), 'German date format');
  assert(el('recipe-home').innerHTML.includes('Rezepte'), el('recipe-home').innerHTML.slice(0, 300));
  assert.strictEqual(el('aggiungi-title').textContent, 'Rezept hinzufügen');
  run("setLang('en')");
  assert(el('planner-days').innerHTML.includes('Lunch'));
  run("setLang('it')");
  assert(el('planner-days').innerHTML.includes('Pranzo') && el('planner-days').innerHTML.includes('Aggiungi'));
  assert.strictEqual(el('planner-view-btn').textContent, 'Vista mese');
  assert.strictEqual(store.lmc_lang, 'it');
});

test('language: a catalogue item picked in German is saved in Italian and merges with the recipe one', () => {
  run("setLang('de')");
  const de = run("CATALOG_I18N['Mele'].de");
  el('shop-input').value = de; run('addShopItem()');
  assert.strictEqual(run('catalogAddItem.name'), 'Mele', 'typed German name finds the catalogue item');
  assert.strictEqual(el('catalog-add-title').textContent, de, 'title shown in German');
  el('cat-name-group').style.display = 'none'; el('cat-qty').value = '2'; el('cat-unit').value = 'n°'; el('cat-note').value = '';
  const qsa = documentStub.querySelectorAll; documentStub.querySelectorAll = q => (q === '.nav-item' ? [0, 1, 2, 3].map(() => ({ click() {} })) : []);
  writes.length = 0; run('confirmCatalogAdd()'); documentStub.querySelectorAll = qsa;
  const w = writes.find(w => w.op === 'push');
  assert.strictEqual(w.v.ingName, 'mele'); assert.strictEqual(w.v.ingUnit, 'n°'); assert.strictEqual(w.v.category, 'Frutta');
  const mk = run('shopWeekSort()');
  run(`shopping=${JSON.stringify([Object.assign({ id: 'a1' }, w.v), { id: 'a2', text: '3 n° mele', ingName: 'mele', ingUnit: 'n°', ingQty: 3, category: 'Frutta', source: 'Torta (\u00d72 porz.)', weekSort: mk, checked: false }])}`);
  run('renderShopping()');
  const h = el('shop-list').innerHTML;
  assert.strictEqual((h.match(/class="shop-item"/g) || []).length, 1, 'one merged line');
  assert(h.includes('5 Stk. ' + de) && h.includes('Katalog') && h.includes('(\u00d72 Port.)'), h);
  run("setLang('it')");
  assert(el('shop-list').innerHTML.includes('5 n° mele'), 'Italian unchanged');
});

test('language: German ingredients get their shopping category and kcal; German text import', () => {
  const de = run("CATALOG_I18N['Zucchero'].de"), kcal = run("CATALOG_SEED.find(c=>c[0]==='Zucchero')[3]");
  assert.strictEqual(run(`ingCategory(${JSON.stringify(de)})`), run("CATS[CATALOG_SEED.find(c=>c[0]==='Zucchero')[1]]"));
  const n = run(`calcNutrition({ingredienti:[{qty:2,unit:'EL',name:${JSON.stringify(de)}}],porzioni:1},1)`);
  assert.strictEqual(n.kcal, Math.round(30 / 100 * kcal), '2 EL = 30 g');
  const r = run(`parseRecipeText("Zitronenkuchen\\nFür 4 Personen\\nZutaten\\n200 g Mehl\\n2 EL Zucker\\nZubereitung\\n1. Alles mischen\\n2. 30 Minuten backen")`);
  assert.strictEqual(r.porzioni, 4);
  assert.strictEqual(r.ingredienti.map(i => i.unit + ' ' + i.name).join('|'), 'g Mehl|el Zucker');
  assert(r.procedimento.includes('Alles mischen') && r.procedimento.includes('backen'), r.procedimento);
  const e = run(`parseRecipeText("Pancakes\\nServes 2\\nIngredients\\n1 cup of flour\\n2 tbsp sugar\\nMethod\\n1. Mix")`);
  assert.strictEqual(e.porzioni, 2);
  assert.strictEqual(e.ingredienti.map(i => i.unit + ' ' + i.name).join('|'), 'cup flour|tbsp sugar');
});

// ---------- translated recipes ----------
const flush = () => new Promise(r => setTimeout(r, 0));
const trState = () => {
  run("recipes=recipes.filter(r=>r.id!=='trA');recipes.push({id:'trA',nome:'Pasta mamma',fonte:'mamma',ingredienti:[{qty:100,unit:'g',name:'pasta'}],procedimento:'1. cuoci',_priv:false})");
  const h = run("trHash(recipes.find(r=>r.id==='trA'))");
  run(`_trIdx={trA:['Pasta mamma','Mamas Teigwaren']};_trIng={'pasta della nonna':'Nonnas Teigwaren'};_trNameMap=null;_trSlow={};_trShowOriginal=false;`);
  run(`_trCache={trA:{src:${JSON.stringify(h)},nome:'Mamas Teigwaren',procedimento:'1. kochen',ing:[{n:'Teigwaren'}]}}`);
};
test('recipes: German name in lists, sheet, cook mode, export, planner and shopping; Original switch', async () => {
  run("setLang('de')"); await flush(); trState();
  el('search-input').value = 'mamas'; run('renderRecipes()');
  assert(el('recipe-home').innerHTML.includes('Mamas Teigwaren'), 'search finds the German name');
  el('search-input').value = ''; run('renderRecipes()');
  run("openRecipe('trA')");
  let b = el('modal-body').innerHTML;
  assert(b.includes('Mamas Teigwaren') && b.includes('Teigwaren') && b.includes('kochen'), b);
  assert(b.includes('Aus dem Italienischen übersetzt') && b.includes('Original anzeigen') && !b.includes('cuoci'), b);
  const txt = run("recipePlainText(recipes.find(r=>r.id==='trA'),4)");
  assert(txt.includes('ZUTATEN') && txt.includes('ZUBEREITUNG') && txt.includes('100 g Teigwaren') && txt.includes('1. kochen'), txt);
  run("openCookMode('trA')");
  assert.strictEqual(el('cook-step-text').textContent, 'kochen'); assert.strictEqual(el('cook-title').textContent, 'Mamas Teigwaren');
  run('closeCookMode()');
  run("openRecipe('trA');toggleTrOriginal()");
  b = el('modal-body').innerHTML;
  assert(b.includes('Pasta mamma') && b.includes('cuoci') && b.includes('Übersetzung anzeigen'), b);
  assert(run("recipePlainText(recipes.find(r=>r.id==='trA'),4)").includes('INGREDIENTI'), 'original export stays Italian');
  run('toggleTrOriginal()');
  assert(el('modal-body').innerHTML.includes('kochen'));
  run(`planner=${JSON.stringify({ [key]: { pranzo: 'Pasta mamma', pranzo_id: 'trA', pranzo_porzioni: 2 } })}`);
  run("plannerView='week';currentMonth=new Date();renderPlanner()");
  assert(el('planner-days').innerHTML.includes('Mamas Teigwaren'), 'planner shows the German name');
  const mk = run('shopWeekSort()');
  run(`shopping=${JSON.stringify([{ id: 'q1', text: '50 g pasta della nonna', ingName: 'pasta della nonna', ingUnit: 'g', ingQty: 50, category: 'Pasta, Riso e Cereali', source: 'Pasta mamma (×2 porz.)', weekSort: mk, checked: false, fromPlanner: true }])}`);
  run('renderShopping()');
  const s = el('shop-list').innerHTML;
  assert(s.includes('50 g Nonnas Teigwaren') && s.includes('Mamas Teigwaren (×2 Port.)'), s);
});

test('recipes: a recipe edited after the translation shows the original', async () => {
  await flush(); trState();
  run("recipes.find(r=>r.id==='trA').procedimento='1. cuoci al dente'");
  run("openRecipe('trA')");
  const b = el('modal-body').innerHTML;
  assert(b.includes('cuoci al dente') && b.includes('Noch nicht übersetzt') && !b.includes('kochen'), b);
});

test('recipes: the translation is downloaded when the recipe is opened', async () => {
  await flush(); trState(); run('_trCache={}');
  run("openRecipe('trA')");
  assert(el('modal-body').innerHTML.includes('Übersetzung wird geladen'), 'loading state while downloading');
  await new Promise(r => setTimeout(r, 20));
  assert(listeners.some(l => l.path === 'recipeTr/de/trA'), 'reads recipeTr/de/<id>');
  const b = el('modal-body').innerHTML;  // the fake database has none: the original appears
  assert(!b.includes('Übersetzung wird geladen') && b.includes('cuoci') && b.includes('Noch nicht übersetzt'), b);
});

test('recipes: back in Italian an Italian recipe is shown as it is, with no note', async () => {
  run("setLang('it')"); await flush();
  assert(listeners.some(l => l.path === 'recipeTrIdx/it'), 'Italian index loaded too (German/English recipes)');
  run("openRecipe('trA')");
  const b = el('modal-body').innerHTML;
  assert(b.includes('Pasta mamma') && !b.includes('Non ancora tradotta') && !b.includes('Tradotta'), b);
});

test('recipes: a German recipe is shown in Italian and English, "tradotta dal tedesco"', async () => {
  run("recipes=recipes.filter(r=>r.id!=='trD');recipes.push({id:'trD',nome:'Apfelkuchen',fonte:'internet',procedimento:'1. Mehl und Zucker mischen.\\n2. Im Ofen 40 Minuten backen.',ingredienti:[{qty:2,unit:'EL',name:'Mehl'},{qty:3,unit:'Stk.',name:'Äpfel'}],_priv:false})");
  assert.strictEqual(run("detectLang(recipes.find(r=>r.id==='trD'))"), 'de');
  assert.strictEqual(run("detectLang(recipes.find(r=>r.id==='trA'))"), 'it');
  const h = run("trHash(recipes.find(r=>r.id==='trD'))");
  // Italian app: translation from German
  run(`_trIdx={trD:['Apfelkuchen','Torta di mele']};_trIng={'mehl':'farina'};_trNameMap=null;_trSlow={};_trShowOriginal=false;`);
  run(`_trCache={trD:{src:${JSON.stringify(h)},from:'de',nome:'Torta di mele',procedimento:'1. Mescolare farina e zucchero.\\n2. Cuocere in forno per 40 minuti.',ing:[{n:'farina'},{n:'mele'}]}}`);
  run("openRecipe('trD')");
  let b = el('modal-body').innerHTML;
  assert(b.includes('Torta di mele') && b.includes('Tradotta dal tedesco') && b.includes("Mostra l'originale"), b);
  assert(b.includes('2 cucchiaio') && b.includes('3 n°') && !b.includes('EL'), 'German units shown in Italian: ' + b);
  assert.strictEqual(run("ingLabel('mehl')"), 'farina');
  // not translated yet: in German it is the original (no note), in Italian it says so
  run('_trCache={};_trIdx={}');
  run("openRecipe('trD')");
  assert(el('modal-body').innerHTML.includes('Non ancora tradotta'), 'Italian app, German recipe without translation');
  run("setLang('de')"); await flush(); run('_trIdx={};_trCache={}');
  run("openRecipe('trD')");
  b = el('modal-body').innerHTML;
  assert(b.includes('Apfelkuchen') && !b.includes('Noch nicht übersetzt'), 'German recipe in German: the original, no note');
  assert(run("recipePlainText(recipes.find(r=>r.id==='trD'),4)").includes('ZUTATEN'), 'export headings in the recipe language');
  run("setLang('en')"); await flush();
  assert.strictEqual(run("unitLabel('EL')"), 'tbsp');
  run("setLang('it')"); await flush();
});

// ---------- Cosa cucino? ----------
test('cosa cucino: stems match singular/plural and ignore small words', () => {
  assert.strictEqual(run("cwStems('Pomodori pelati').join(' ')"), run("cwStems('pomodoro pelato').join(' ')"));
  assert.strictEqual(run("cwStems('2 uova grandi').join(' ')"), '2 uov grand');
  assert.strictEqual(run("cwHas(cwStems('farina 00'),[cwStems('farina')])"), true);
  assert.strictEqual(run("cwHas(cwStems('pepe nero'),[cwStems('peperoni')])"), false);
});

test('cosa cucino: recipes ordered by fewest missing; freezer and basics count; nothing used = not shown', async () => {
  run("setLang('it')"); await flush();
  run(`recipes=recipes.filter(r=>!/^cw/.test(r.id));recipes.push(
    {id:'cw1',nome:'Frittata',ingredienti:[{name:'uova'},{name:'sale'},{name:'parmigiano grattugiato'}],_priv:false},
    {id:'cw2',nome:'Carbonara',ingredienti:[{name:'spaghetti'},{name:'guanciale'},{name:'uova'},{name:'pecorino'},{name:'pepe nero'}],_priv:false},
    {id:'cw3',nome:'Risotto ai piselli',ingredienti:[{name:'riso'},{name:'piselli'},{name:'brodo'}],_priv:false},
    {id:'cw4',nome:'Torta',ingredienti:[{name:'farina 00'},{name:'zucchero'},{name:'burro'}],_priv:false})`);
  run(`pantry={items:['Uova','Parmigiano'],basics:CW_BASICS.slice(),freezer:true};freezer=[{id:'f9',name:'Piselli surgelati'}]`);
  run('openCookWhat()');
  const ids = run("_cwLast.map(x=>x.r.id).filter(id=>/^cw/.test(id)).join(',')");
  assert.strictEqual(ids, 'cw1,cw3,cw2', 'frittata (nothing missing), then risotto (2 missing), then carbonara (3 missing); torta uses nothing you have');
  const h = el('cw-results').innerHTML;
  assert(h.includes('Hai tutto') && h.includes('manca: riso, brodo'), h.slice(0, 600));
  run('toggleCwFreezer(false)');
  assert(!run("_cwLast.some(x=>x.r.id==='cw3')"), 'without the freezer the risotto uses nothing you have');
  run('toggleCwFreezer(true)');
});

test('cosa cucino: the pantry is saved in the account, catalogue names in Italian; + Spesa ticks what you have', async () => {
  run("setLang('de')"); await flush();
  writes.length = 0;
  el('cw-input').value = run("CATALOG_I18N['Burro'].de"); run('addPantryItem()');
  const w = writes.filter(x => x.path === 'users/friendUid/pantry').pop();
  assert(w && w.v.items.includes('Burro') && w.v.freezer === true, JSON.stringify(writes.slice(-2)));
  assert(run("_cwLast.some(x=>x.r.id==='cw4')"), 'butter makes the cake appear');
  run("cwToShop('cw2')");
  const checks = el('shop-add-checks').innerHTML;
  const tag = n => (checks.match(new RegExp('<input[^>]*data-ing="' + n + '"[^>]*>')) || [''])[0];
  assert(/ checked /.test(tag('uova')) && / checked /.test(tag('pepe nero')), 'owned and basics ticked: ' + tag('uova') + ' ' + tag('pepe nero'));
  assert(tag('guanciale') && !/ checked /.test(tag('guanciale')), 'what you do not have stays unticked: ' + tag('guanciale'));
  run("setLang('it')"); await flush();
  run("renderRecipes()");
  assert(el('recipe-home').innerHTML.includes('openCookWhat()') && el('recipe-home').innerHTML.includes('Cosa cucino?'), 'card at the top of Ricette');
});

test('planner: tapping a planned recipe opens it at the planned servings, with "Cambia piatto"', () => {
  fire('recipes', 'child_added', 'pollo', { nome: 'Pollo alla cacciatora', porzioni: 4, ingredienti: [{ qty: 1200, unit: 'g', name: 'pollo' }], procedimento: '1. dorare' });
  run("planner['2026-10-7']={cena:'Pollo alla cacciatora',cena_id:'pollo',cena_porzioni:2,cena2:'Pollo alla cacciatora',cena2_id:'pollo',pranzo:'__fuori_casa'}");
  run("planner['2026-10-8']={pranzo:'Pollo alla cacciatora'}");  // old format: name only, no id
  run("tapDish('2026-10-7','cena')");
  assert.strictEqual(run('currentRecipeId'), 'pollo');
  assert.strictEqual(run('currentPortions'), 2, 'planned servings');
  const body = el('modal-body').innerHTML;
  assert(body.includes('class="plan-bar"') && body.includes('Cambia piatto') && body.includes('Cena'), body.slice(0, 600));
  run("tapDish('2026-10-8','pranzo')");
  assert.strictEqual(run('currentRecipeId'), 'pollo', 'old name-only entry still opens');
  assert.strictEqual(run('currentPortions'), 4, 'no planned servings: recipe default');
  assert(el('modal-body').innerHTML.includes('Pranzo'));
  run("tapDish('2026-10-7','cena')"); run("changePortions(1)");
  assert(el('modal-body').innerHTML.includes('plan-bar'), 'planner line survives a re-render');
  assert.strictEqual(run('currentPortions'), 3);
  run("openRecipe('pollo')");
  assert(!el('modal-body').innerHTML.includes('plan-bar'), 'opened from the list: no planner line');
  assert.strictEqual(run('currentPortions'), 4);
});

test('planner: eating out opens the picker; "Cambia piatto" closes the recipe and opens the picker on that meal', () => {
  el('pick-modal').style.display = 'none';
  run("tapDish('2026-10-7','pranzo')");
  assert.strictEqual(el('pick-modal').style.display, 'flex', 'eating out: change dish');
  el('pick-modal').style.display = 'none';
  run("tapDish('2026-10-7','cena2')"); run("changePlannedDish()");
  assert.strictEqual(el('recipe-modal').style.display, 'none', 'recipe closed');
  assert.strictEqual(el('pick-modal').style.display, 'flex', 'picker open');
  assert.strictEqual(run('pickTarget.key') + '|' + run('pickTarget.meal'), '2026-10-7|cena2');
});

test('planner: week and month views open recipes on tap, with the change button next to remove', () => {
  run("plannerView='week';currentMonth=new Date(2026,9,7);renderPlanner()");
  const wk = el('planner-days').innerHTML;
  assert(wk.includes("tapDish('2026-10-7','cena')") && wk.includes("tapDish('2026-10-7','cena2')"), 'week: tap opens');
  assert(wk.includes(`class="meal-alt-btn" aria-label="Cambia piatto" onclick="openPickModal('2026-10-7','cena')"`), 'week: change, first dish');
  assert(wk.includes(`onclick="openPickModal('2026-10-7','cena2')">&#8644;`), 'week: change, second dish');
  run("plannerView='month';renderPlanner()");
  const mo = el('planner-days').innerHTML;
  assert(mo.includes(`onclick="tapDish('2026-10-7','cena')"`) && mo.includes("event.stopPropagation();tapDish('2026-10-7','cena2')"), 'month: tap opens');
  assert(mo.includes(`onclick="openPickModal('2026-10-7','cena')">&#8644;</button><button class="meal-rm-btn"`), 'month: change before remove');
  assert(mo.includes("openPickModal('2026-10-9','pranzo')"), 'empty slots still open the picker');
});

test('planner: "Oggi" shows only away from the current week or month and brings you back', () => {
  run("plannerView='week';currentMonth=new Date();renderPlanner()");
  assert.strictEqual(el('planner-today-btn').style.display, 'none', 'this week: hidden');
  run("changeMonth(1)");
  assert.strictEqual(el('planner-today-btn').style.display, 'inline-block', 'next week: shown');
  run("changeMonth(0)");
  assert.strictEqual(el('planner-today-btn').style.display, 'none', 'back to this week');
  assert.strictEqual(run("currentMonth.toDateString()===new Date().toDateString()"), true);
  run("plannerView='month';renderPlanner()");
  assert.strictEqual(el('planner-today-btn').style.display, 'none', 'this month: hidden');
  run("changeMonth(-1)");
  assert.strictEqual(el('planner-today-btn').style.display, 'inline-block', 'other month: shown');
  run("changeMonth(0)");
  assert.strictEqual(el('planner-today-btn').style.display, 'none');
});

test('offline: every write is noted on the phone until the database confirms it', async () => {
  run(`(function(){
    function FR(p){this.path=p;}
    FR.prototype.set=function(){return Promise.resolve();};
    FR.prototype.update=function(){return Promise.resolve();};
    FR.prototype.remove=function(){return new Promise(function(){});};   // never confirmed: no signal
    FR.prototype.push=function(){var r=new FR(this.path+'/k1'),p=Promise.resolve(r);r.then=p.then.bind(p);return r;};
    patchRefWrites(FR.prototype);window._FR=FR;
  })()`);
  run("new _FR('users/friendUid/shopping/a').set({name:'latte'})");
  run("new _FR('users/friendUid/shopping/b').remove()");
  run("new _FR('users/friendUid/shopping').push({name:'pane'})");
  run("new _FR('users/friendUid/planner').update({'2026-10-9/cena':'Risotto'})");
  await flush();
  const ob = JSON.parse(store['lmc_outbox']);
  assert.deepStrictEqual(ob.map(x => x.op + ' ' + x.path + ' ' + x.uid), ['remove users/friendUid/shopping/b friendUid'], 'only the unconfirmed write stays');
});

test('offline: unconfirmed writes are sent again at the next start, only for this account', () => {
  store['lmc_outbox'] = JSON.stringify([
    { id: 'x1', uid: 'friendUid', op: 'set', path: 'users/friendUid/shopping/a/checked', v: true },
    { id: 'x2', uid: 'otherUid', op: 'remove', path: 'users/otherUid/planner/x', v: null },
    { id: 'x3', uid: 'friendUid', op: 'update', path: 'users/friendUid/planner', v: { '2026-10-9/cena': 'Risotto' } },
  ]);
  writes.length = 0;
  run('obReplay()');
  assert(writes.some(w => w.op === 'set' && w.path === 'users/friendUid/shopping/a/checked' && w.v === true), JSON.stringify(writes));
  assert(writes.some(w => w.op === 'update' && w.path === 'users/friendUid/planner' && w.v['2026-10-9/cena'] === 'Risotto'));
  assert(!writes.some(w => w.path.startsWith('users/otherUid')), "another account's changes are not sent");
  const left = JSON.parse(store['lmc_outbox']).map(x => x.id);
  assert.deepStrictEqual(left, ['x2'], 'sent ones leave the list, the other account keeps its own');
});

test('offline: with no signal the last data shows; a tick shows at once; then the database takes over', () => {
  authCb(null);
  store['lmc_cache_friendUid'] = JSON.stringify({
    shopping: { s1: { name: 'latte', checked: false, weekSort: '2026-10-05' } },
    planner: { '2026-10-7': { cena: 'Pasta al pomodoro' } },
    freezer: { f1: { name: 'Ragù', qty: 2 } },
  });
  authCb({ uid: 'friendUid', email: 'amica@gmail.com', displayName: 'Amica Test' });
  assert.strictEqual(run('shopping.length'), 1, 'last shopping list shown');
  assert.strictEqual(run("planner['2026-10-7'].cena"), 'Pasta al pomodoro', 'last planner shown');
  assert.strictEqual(run('freezer[0].name'), 'Ragù', 'last freezer shown');
  run("obTrack('set','users/friendUid/shopping/s1/checked',true)");  // what ticking does, before the database answers
  assert.strictEqual(run('shopping[0].checked'), true, 'the tick shows at once');
  assert.strictEqual(JSON.parse(store['lmc_cache_friendUid']).shopping.s1.checked, true, 'and is kept on the phone');
  run("obTrack('remove','users/friendUid/freezer/f1',null)");
  assert.strictEqual(run('freezer.length'), 0, 'removing from the freezer shows at once too');
  fire('users/friendUid/familyCode', 'value', null, null);
  fire('users/friendUid/shopping', 'value', null, { s1: { name: 'latte', checked: true, weekSort: '2026-10-05' }, s2: { name: 'pane', checked: false, weekSort: '2026-10-05' } });
  assert.strictEqual(run('shopping.length'), 2, "the database's data replaces the saved one");
  run("obTrack('set','users/friendUid/shopping/s2/checked',true)");
  assert.strictEqual(run("shopping.find(x=>x.id==='s2').checked"), false, 'after that, Firebase updates the list (no double update)');
});

test('offline: signing out removes the saved data from the phone', () => {
  assert(store['lmc_cache_friendUid'] && store['lmc_cache_friendUid'] !== 'null');
  authCb(null);
  assert.strictEqual(store['lmc_cache_friendUid'], 'null');
  authCb({ uid: 'friendUid', email: 'amica@gmail.com', displayName: 'Amica Test' });
});

test('family: with a family code the planner and the freezer are the family ones', () => {
  fire('users/friendUid/familyCode', 'value', null, 'FAM234');
  assert.strictEqual(run('refPath(plannerRef())'), 'families/FAM234/planner');
  assert.strictEqual(run('refPath(freezerRef())'), 'families/FAM234/freezer');
  assert(listeners.some(l => l.path === 'families/FAM234/planner' && l.ev === 'value'), 'listening to the family planner');
  assert(listeners.some(l => l.path === 'families/FAM234/freezer' && l.ev === 'value'), 'listening to the family freezer');
  fire('families/FAM234/planner', 'value', null, { '2026-10-14': { cena: 'Pizza', cena2: 'Insalata' } });
  assert.strictEqual(run("planner['2026-10-14'].cena"), 'Pizza', 'the family menu is shown');
  writes.length = 0;
  run("quickClearMeal('2026-10-14','cena2')");
  assert(writes.length && writes.every(w => w.path.startsWith('families/FAM234/planner/2026-10-14')), JSON.stringify(writes));
  fire('families/FAM234/freezer', 'value', null, { fz1: { name: 'Ragù', qty: 2 } });
  assert.strictEqual(run('freezer[0].name'), 'Ragù', 'the family freezer is shown');
});

test('family: joining fills only the empty family meals; same-name freezer items are not doubled', () => {
  fire('users/friendUid/familyCode', 'value', null, null);  // back to personal
  run("planner={'2026-10-12':{pranzo:'__dal_freezer',pranzo_freezer_id:'p1',pranzo_freezer_name:'Ragù',pranzo_porzioni:2},'2026-10-13':{cena:'Minestrone'},'2026-10-15':{extras:[{name:'pane'}]}}");
  run("freezer=[{id:'p1',name:'Ragù',qty:2},{id:'p2',name:'Pesto',qty:1}]");
  const up = run("familyMerge({'2026-10-13':{cena:'Pizza'}},{x9:{name:'ragu',qty:3}})");
  assert.strictEqual(up['planner/2026-10-12'].pranzo, '__dal_freezer', 'my dish fills an empty day');
  assert.strictEqual(up['planner/2026-10-12'].pranzo_freezer_id, 'x9', 'and points to the family Ragù');
  assert.strictEqual(up['planner/2026-10-12'].pranzo_porzioni, 2);
  assert(!('planner/2026-10-13' in up), "the family's dinner is not overwritten");
  assert.strictEqual(JSON.stringify(up['planner/2026-10-15'].extras), '[{"name":"pane"}]', 'extras of an empty day come along');
  assert.strictEqual(JSON.stringify(up['freezer/p2']), '{"name":"Pesto","qty":1}', 'a new item joins the family freezer');
  assert(!('freezer/p1' in up), 'Ragù is already in the family freezer');
});

test('family: joining writes membership, then the merge, then the code; creating brings my planner and freezer', async () => {
  run("planner={'2026-10-16':{cena:'Gnocchi'}}");
  run("freezer=[{id:'p3',name:'Brodo',qty:1}]");
  writes.length = 0;
  el('family-join-input').value = 'joi345';
  run('joinFamily()');
  listeners.filter(l => l.path === 'families/JOI345/members' && l.ev === 'once:value').forEach(l => l.cb({ exists: () => true, val: () => ({ otherUid: {} }) }));
  await new Promise(r => setTimeout(r, 20));
  const iM = writes.findIndex(w => w.path === 'families/JOI345/members/friendUid');
  const iU = writes.findIndex(w => w.op === 'update' && w.path === 'families/JOI345');
  const iC = writes.findIndex(w => w.path === 'users/friendUid/familyCode' && w.v === 'JOI345');
  assert(iM >= 0 && iU > iM && iC > iU, JSON.stringify(writes));
  assert.strictEqual(writes[iU].v['planner/2026-10-16'].cena, 'Gnocchi');
  assert.strictEqual(writes[iU].v['merged/friendUid'], true, 'the new member counts as merged');
  assert.strictEqual(JSON.stringify(writes[iU].v['freezer/p3']), '{"name":"Brodo","qty":1}');

  writes.length = 0;
  run('createFamily()');
  await new Promise(r => setTimeout(r, 20));
  const seed = writes.find(w => w.op === 'update' && /^families\/[A-HJ-NP-Z2-9]{6}$/.test(w.path));
  assert(seed && seed.v.planner['2026-10-16'].cena === 'Gnocchi' && seed.v.freezer.p3.name === 'Brodo', JSON.stringify(writes));
  assert.strictEqual(seed.v['merged/friendUid'], true, 'the creator counts as merged');

  fire('users/friendUid/familyCode', 'value', null, null);  // leaving: back to the personal ones
  assert.strictEqual(run('refPath(plannerRef())'), 'users/friendUid/planner');
  assert.strictEqual(run('refPath(freezerRef())'), 'users/friendUid/freezer');
});

test('family: an existing family member is merged once, at the first open of the new version', async () => {
  const up = run("familyMerge({},{},{planner:{'2026-10-20':{pranzo:'Risotto'}},freezer:[{id:'q1',name:'Sugo',qty:1}]})");
  assert.strictEqual(up['planner/2026-10-20'].pranzo, 'Risotto', "someone else's personal planner can be merged too");
  assert.strictEqual(up['freezer/q1'].name, 'Sugo');
  writes.length = 0;
  fire('users/friendUid/familyCode', 'value', null, 'OLD567');
  await new Promise(r => setTimeout(r, 20));
  const u = writes.find(w => w.op === 'update' && w.path === 'families/OLD567');
  assert(u && u.v['merged/friendUid'] === true, 'merged, and marked: ' + JSON.stringify(writes));
  fire('users/friendUid/familyCode', 'value', null, null);
});

test('shopping: in a family there is also a private list; every action works on the list on screen', () => {
  run("shopScope='family'");
  fire('users/friendUid/familyCode', 'value', null, 'FAM890');
  assert.strictEqual(run('refPath(shopRef())'), 'families/FAM890/shopping', 'the family list first');
  assert(el('shop-scope').innerHTML.includes('Solo mia') && el('shop-scope').style.display === 'flex', 'two tabs');
  fire('families/FAM890/shopping', 'value', null, { f1: { name: 'pane', weekSort: '2026-10-05' } });
  run("setShopScope('mine')");
  assert.strictEqual(run('refPath(shopRef())'), 'users/friendUid/shopping', 'Solo mia = my personal list');
  assert(/filter-tab active" aria-pressed="true" onclick="setShopScope\('mine'\)/.test(el('shop-scope').innerHTML), el('shop-scope').innerHTML);
  assert(listeners.some(l => l.path === 'users/friendUid/shopping' && l.ev === 'value'));
  fire('users/friendUid/shopping', 'value', null, { m1: { name: 'regalo', weekSort: '2026-10-05' } });
  assert.strictEqual(run("shopping.map(x=>x.name).join()"), 'regalo', 'only my items on screen');
  writes.length = 0;
  el('shop-input').value = 'cioccolato'; run('addShopItem()');
  assert(writes.length && writes.every(w => w.path.startsWith('users/friendUid/shopping')), 'added to my list: ' + JSON.stringify(writes));
  const saved = JSON.parse(store['lmc_cache_friendUid']);
  assert(saved.shopping.f1 && saved.shoppingMine.m1, 'both lists kept on the phone, separately');
  run("setShopScope('family')");
  assert.strictEqual(run("shopping.map(x=>x.name).join()"), 'pane', 'back to the family list at once');
  assert.strictEqual(store['lmc_shop_scope'], '"family"', 'the choice stays on the phone');
  fire('users/friendUid/familyCode', 'value', null, null);
  assert.strictEqual(el('shop-scope').style.display, 'none', 'no family: no tabs');
  assert.strictEqual(run('refPath(shopRef())'), 'users/friendUid/shopping');
});

test('catalogue: Ravioli is there; the ingredient search finds singular and plural', () => {
  const names = q => run(`CATALOG_SEED.filter(c=>catMatch(c,${JSON.stringify(q)})).map(c=>c[0])`);
  assert.strictEqual(run("CATS[CATALOG_SEED.find(c=>c[0]==='Ravioli')[1]]"), 'Pasta, Riso e Cereali');
  assert(names('ravioli').includes('Ravioli') && names('raviolo').includes('Ravioli'));
  assert(names('lasagna').includes('Lasagne'), 'lasagna finds Lasagne');
  assert(names('pomodoro').includes('Pomodori') && names('pomodoro pelato').includes('Pomodori pelati'));
  assert(names('fungo').includes('Funghi porcini') && names('gnocco').includes('Gnocchi'));
  assert(names('lasag').includes('Lasagne') && names('lievito per').includes('Lievito per dolci'), 'typing halfway still works');
  assert(!names('pera').includes('Lievito per dolci'), '"pera" does not find every "per"');
  assert(!names('pasta').some(n => /^Pastiglie/.test(n)), 'no unrelated words');
});

test('family recipes: "Famiglia" shows with a family code; new ones go to the family; every member edits and moves them', () => {
  const rules = JSON.parse(fs.readFileSync(path.join(ROOT, 'database.rules.json'), 'utf8')).rules;
  assert.strictEqual(rules.families.$code.recipes.$recipeId['.validate'], rules.users.$uid.recipes.$recipeId['.validate'], 'same checks as the other recipes');
  run('resetRecipeForm()');
  assert.strictEqual(el('r-vis-fam').style.display, 'none', 'no family: two choices');
  fire('users/friendUid/familyCode', 'value', null, 'FAMR12');
  assert.strictEqual(el('r-vis-fam').style.display, '', 'in a family: "Famiglia" too');
  assert(listeners.some(l => l.path === 'families/FAMR12/recipes' && l.ev === 'child_added'), 'listening to the family recipes');
  run("setRecipeVis('fam')"); el('r-nome').value = 'Torta di casa';
  writes.length = 0; run('saveRecipe()');
  const w = writes.find(w => w.op === 'push');
  assert(w && w.path.startsWith('families/FAMR12/recipes/') && w.v.ownerUid === 'friendUid', JSON.stringify(writes));
  assert.strictEqual(store['lmc_recipe_vis'], 'fam', 'the choice is remembered');
  fire('families/FAMR12/recipes', 'child_added', 'famX', { nome: 'Lasagne della nonna', ownerUid: 'otherUid', addedBy: 'Dany' });
  const r = "recipes.find(r=>r.id==='famX')";
  assert.strictEqual(run(r + '._fam'), true);
  assert.strictEqual(run(`canEdit(${r})`), true, 'every member can edit');
  run("openRecipe('famX')");
  assert(el('modal-body').innerHTML.includes('Famiglia') && el('modal-body').innerHTML.includes('Modifica'), 'badge and edit button');
  run("openEditRecipe('famX')");
  assert.strictEqual(run('recipeVis'), 'fam');
  assert.strictEqual(el('r-vis-pub').disabled, false, 'every member can change who sees it');
  writes.length = 0; el('r-nome').value = 'Lasagne della nonna'; run('saveRecipe()');
  const u = writes.find(w => w.op === 'update' && w.path === 'families/FAMR12/recipes/famX');
  assert(u && u.v.nome === 'Lasagne della nonna' && !('ownerUid' in u.v), 'a plain edit keeps the author: ' + JSON.stringify(writes));
  run("openEditRecipe('famX')"); run("setRecipeVis('pub')"); el('r-nome').value = 'Lasagne della nonna';
  writes.length = 0; run('saveRecipe()');
  const m = writes.find(w => w.op === 'update' && w.path === '');
  assert(m && m.v['families/FAMR12/recipes/famX'] === null && m.v['recipes/famX'].ownerUid === 'friendUid', 'moved with the same key: ' + JSON.stringify(writes));
  assert(!('_fam' in m.v['recipes/famX']), 'app-only fields are not saved');
});

test('family recipes: deleting warns the whole family; leaving keeps a private copy of mine; then they disappear', () => {
  fire('families/FAMR12/recipes', 'child_added', 'famMine', { nome: 'Pane di casa', ownerUid: 'friendUid' });
  const asked = []; sandbox.confirm = m => { asked.push(m); return false; };
  run("deleteRecipe('famMine')");
  sandbox.confirm = () => true;
  assert(/famiglia/.test(asked[0]), asked[0]);
  writes.length = 0;
  run('leaveFamily()');
  const c = writes.find(w => w.op === 'update' && w.path === 'users/friendUid/recipes');
  assert(c && c.v.famMine && c.v.famMine.nome === 'Pane di casa' && !c.v.famX, 'only mine are copied: ' + JSON.stringify(writes));
  assert(!('_fam' in c.v.famMine) && !('id' in c.v.famMine));
  assert(writes.indexOf(c) < writes.findIndex(w => w.op === 'remove' && w.path === 'families/FAMR12/members/friendUid'), 'copied before leaving');
  fire('users/friendUid/familyCode', 'value', null, null);
  assert.strictEqual(run('recipes.filter(r=>r._fam).length'), 0, 'family recipes leave the list');
  assert(!listeners.some(l => l.path === 'families/FAMR12/recipes'), 'listener detached');
  assert.strictEqual(el('r-vis-fam').style.display, 'none');
  assert.strictEqual(run('recipeVisNow()'), 'priv', 'a saved "Famiglia" counts as "Solo per me" outside a family');
});

(async () => {
  for (const [name, fn] of queue) { await fn(); passed++; console.log('ok -', name); }
  console.log('\n' + passed + ' tests passed'); process.exit(0);
})().catch(e => { console.error('FAILED:', e); process.exit(1); });
