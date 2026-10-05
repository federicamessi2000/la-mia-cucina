"""Traduce con Gemini le ricette condivise nuove o modificate nelle altre due lingue dell'app:
una ricetta italiana in inglese e tedesco (svizzero), una tedesca in italiano e inglese, una inglese
in italiano e tedesco. La lingua della ricetta la riconosce Gemini.

Gira una volta al mese su GitHub (.github/workflows/translate.yml) e si può lanciare a mano.
Scrive solo recipeTr/<lingua>/<id> e recipeTrIdx/<lingua>: le ricette non vengono mai toccate.
Il database applica le sue regole come utente 'translator-bot', che può scrivere solo le traduzioni
(e non vede le ricette "Solo per me").

Segreti: FIREBASE_SERVICE_ACCOUNT (JSON della chiave), GEMINI_API_KEY.
Facoltativi: GEMINI_MODEL (default gemini-flash-latest), MAX_REQUESTS (default 15: il piano
gratuito di Gemini dà circa 20 richieste al giorno; ogni richiesta traduce più ricette).
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

DB_URL = 'https://la-mia-cucina-48a48-default-rtdb.europe-west1.firebasedatabase.app'
GEMINI = 'https://generativelanguage.googleapis.com/v1beta'
LANGS = ('it', 'en', 'de')
BATCH_CHARS = 7000  # testo italiano per richiesta
BATCH_MAX = 6  # ricette per richiesta
HERE = os.path.dirname(os.path.abspath(__file__))


# ── Impronta del testo italiano: uguale a trSrc/trHash in index.html ─────────────
def _s(x):
    """String(x) come in JavaScript (None -> '')."""
    if x is None:
        return ''
    if isinstance(x, bool):
        return 'true' if x else 'false'
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    if isinstance(x, list):
        return ','.join(_s(e) for e in x)
    if isinstance(x, dict):
        return '[object Object]'
    return str(x)


def ingredients(r):
    ing = r.get('ingredienti') or []
    return None if isinstance(ing, dict) else ing


def tr_src(r):
    p = [_s(r.get(k)) for k in ('nome', 'tempo', 'porzioni', 'note', 'procedimento')]
    for i in ingredients(r) or []:
        if isinstance(i, str):
            p.append('|' + i)
        else:
            i = i or {}
            sez = i.get('sezione')
            p.append((_s(sez) if sez else '') + '|' + _s(i.get('name')))
    return '\x01'.join(p)


def tr_hash(r):
    """FNV-1a a 32 bit sulle unità UTF-16, in base 36."""
    h = 0x811C9DC5
    b = tr_src(r).encode('utf-16-le')
    for k in range(0, len(b), 2):
        h ^= b[k] | (b[k + 1] << 8)
        h = (h * 0x01000193) & 0xFFFFFFFF
    digits, out = '0123456789abcdefghijklmnopqrstuvwxyz', ''
    while True:
        h, d = divmod(h, 36)
        out = digits[d] + out
        if not h:
            return out


LETTERS = re.compile(r'[A-Za-zÀ-ÿ]')


def to_translate(r):
    """Le parti da tradurre, nella forma che riceve il traduttore."""
    out = {'nome': _s(r.get('nome'))}
    for k in ('tempo', 'porzioni'):
        v = r.get(k)
        if isinstance(v, str) and LETTERS.search(v):
            out[k] = v
    for k in ('note', 'procedimento'):
        v = r.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v
    ing = []
    for i in ingredients(r) or []:
        if isinstance(i, str):
            ing.append({'n': i})
        else:
            i = i or {}
            x = {'n': _s(i.get('name'))}
            if i.get('sezione'):
                x['s'] = _s(i.get('sezione'))
            ing.append(x)
    if ing:
        out['ing'] = ing
    return out


# ── Controlli: gli stessi del giro manuale (traduzioni/check_part.py) ────────────
NUM = re.compile(r'\d+(?:[.,]\d+)?')
IT_WORDS = re.compile(
    r'\b(aggiungere|aggiungete|mescolare|mescolate|cuocere|cuocete|tagliare|tagliate|versare|versate|quindi|'
    r'infornare|infornate|impastare|impastate|lasciare|lasciate|mettere|mettete|frullare|pentola|padella|teglia|'
    r'forno|farina|zucchero|uova|burro|latte|sale|olio|minuti|circa|fino a|della|dello|degli|delle|nella|nel|'
    r'con il|con la|e poi)\b',
    re.I,
)


def _lines(s):
    return [x for x in str(s).split('\n') if x.strip()]


def check(orig, tr, source='it'):
    """Errori di una traduzione (lista vuota = va bene). orig è il testo originale, nella lingua source."""
    if not isinstance(tr, dict):
        return ['missing']
    errs = []
    if set(tr) != set(orig):
        errs.append('keys %s, expected %s' % (sorted(tr), sorted(orig)))
    for k, v in orig.items():
        t = tr.get(k)
        if k == 'ing':
            if not isinstance(t, list) or len(t) != len(v):
                errs.append('ing must have %d entries' % len(v))
                continue
            for j, (a, b) in enumerate(zip(v, t)):
                if not isinstance(b, dict) or set(b) != set(a) or any(not isinstance(b[x], str) for x in b):
                    errs.append('ing[%d] must have keys %s' % (j, sorted(a)))
                elif a.get('n', '').strip() and not b['n'].strip():
                    errs.append('ing[%d] empty' % j)
            continue
        if not isinstance(t, str) or (v.strip() and not t.strip()):
            errs.append('%s missing' % k)
            continue
        if k == 'procedimento' and len(_lines(v)) != len(_lines(t)):
            errs.append('procedimento must keep %d lines (one per step)' % len(_lines(v)))
        if k in ('procedimento', 'note'):
            if source == 'it' and len(IT_WORDS.findall(t)) >= 3:
                errs.append('%s still looks Italian' % k)
            elif source != 'it' and len(v) > 40 and t.strip() == v.strip():
                errs.append('%s is not translated' % k)
    return errs


def fix_de(tr):
    """Tedesco svizzero: niente ß."""
    return json.loads(json.dumps(tr, ensure_ascii=False).replace('ß', 'ss'))


# ── Glossario: i nomi del catalogo della spesa (i18n.js), così ricette e spesa dicono lo stesso ──
def load_catalog(path):
    q = r'"(?:[^"\\]|\\.)*"'
    cat = {}
    with open(path, encoding='utf-8') as f:
        for ln in f:
            m = re.match(r'\s*(%s):\{en:(%s),de:(%s)\}' % (q, q, q), ln)
            if m:
                cat[json.loads(m.group(1))] = (json.loads(m.group(2)), json.loads(m.group(3)))
    return cat


def glossary_for(items, catalog):
    text = ' '.join(x.get('n', '') for it in items for x in it.get('ing', [])).lower()
    lines = ['%s | %s | %s' % (k, en, de) for k, (en, de) in sorted(catalog.items())
             if k.lower() in text or en.lower() in text or de.lower() in text]
    return '\n'.join(lines[:80])


PROMPT = """These are family recipes from a recipe app. Each recipe is written in Italian, English or German.
For each recipe, recognise its language and translate it into the other two of: Italian ("it"), British English ("en"), Swiss Standard German ("de").
Return only JSON: an object with the same keys as the input (the recipe ids); each value is {"lang": "<language of the recipe: it, en or de>", "<other language>": {...}, "<other language>": {...}}.
For example an Italian recipe gives {"lang": "it", "en": {...}, "de": {...}}, a German one {"lang": "de", "it": {...}, "en": {...}}.
Each translation has exactly the same keys as the recipe object. "ing" keeps the same number of entries in the same order, each with the same keys ("n", plus "s" only where the original has "s").

Rules:
- Translate everything: the name, every step, the notes (completely, never summarised), every ingredient name and section heading, and time/servings texts.
- "procedimento": exactly the same lines, one translated line per original line, with the same numbering ("1.", "2." ...) if there is one. Never merge or split lines.
- Keep every number, quantity, temperature, time and unit as written (no conversions). Keep emojis, brand names and people's names.
- Italian: natural Italian as in Italian cookbooks; steps in the infinitive ("Mescolare la farina con lo zucchero.").
- English: British spelling and words (aubergine, courgette, coriander, plain flour, caster sugar, icing sugar, double cream, bicarbonate of soda, hob, tin, grill, frying pan). Steps in the imperative.
- German: Swiss Standard German as in Swiss cookbooks (Betty Bossi). Always "ss", never "ß". Swiss words: Rahm, Halbrahm, Poulet, Peperoni (bell peppers), Zucchetti, Glace, Teigwaren, Backofen, Backpapier, Springform, Paniermehl, Kartoffelstock. Steps in the infinitive style ("Mehl und Zucker mischen.").
- Keep well-known Italian dish names (Tiramisù, Risotto, Lasagne, Gnocchi, Focaccia, Panna cotta, Carbonara, Pesto, Ossobuco ...) and translate the descriptive parts ("Risotto ai funghi" → "Mushroom risotto" / "Pilzrisotto"). Keep names short.
- Never add anything that is not in the original.
{glossary}
Recipes:
{recipes}
"""


def build_prompt(batch, catalog, errors=None):
    g = glossary_for([x['it'] for x in batch], catalog)
    g = '\nUse these words for matching ingredients (Italian | English | German):\n' + g + '\n' if g else ''
    text = PROMPT.replace('{glossary}', g).replace(
        '{recipes}', json.dumps({x['id']: x['it'] for x in batch}, ensure_ascii=False, indent=1)
    )
    if errors:
        text += '\nA previous attempt had these problems, fix them: ' + '; '.join(errors) + '\n'
    return text


# ── Gemini ───────────────────────────────────────────────────────────────────────
class QuotaExhausted(Exception):
    pass


class Gemini:
    def __init__(self, key, model):
        self.key, self.model, self.calls = key, model or 'gemini-flash-latest', 0

    def _post(self, model, body):
        req = urllib.request.Request(
            '%s/models/%s:generateContent' % (GEMINI, model),
            data=json.dumps(body).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'x-goog-api-key': self.key},
        )
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode('utf-8'))

    def _fallback_model(self):
        """Il modello scelto non c'è più: prende il Flash più recente che sa fare generateContent."""
        req = urllib.request.Request('%s/models?pageSize=200' % GEMINI, headers={'x-goog-api-key': self.key})
        with urllib.request.urlopen(req, timeout=60) as r:
            models = json.loads(r.read().decode('utf-8')).get('models', [])
        names = [
            m['name'].split('/', 1)[1]
            for m in models
            if 'generateContent' in m.get('supportedGenerationMethods', [])
            and 'flash' in m['name']
            and 'lite' not in m['name']
            and 'image' not in m['name']
        ]
        if not names:
            raise RuntimeError('no Gemini Flash model available')
        return sorted(names)[-1]

    def ask(self, prompt):
        body = {
            'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': 0.2, 'responseMimeType': 'application/json'},
        }
        for attempt in range(4):
            self.calls += 1
            try:
                res = self._post(self.model, body)
                text = ''.join(p.get('text', '') for p in res['candidates'][0]['content']['parts'])
                return json.loads(text)
            except urllib.error.HTTPError as e:
                if e.code == 404 and attempt == 0:
                    self.model = self._fallback_model()
                    print('model not found, using', self.model)
                    continue
                if e.code == 429:
                    if attempt == 3:
                        raise QuotaExhausted() from e
                    time.sleep(65)
                    continue
                if e.code >= 500 and attempt < 3:
                    time.sleep(20)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == 3:
                    raise
                time.sleep(20)
            except (KeyError, IndexError, ValueError):
                return None  # risposta vuota o non JSON: la ricetta si riprova al prossimo giro
        return None


# ── Il giro ──────────────────────────────────────────────────────────────────────
def batches(items):
    out, cur, size = [], [], 0
    for x in items:
        n = len(json.dumps(x['it'], ensure_ascii=False))
        if cur and (size + n > BATCH_CHARS or len(cur) >= BATCH_MAX):
            out.append(cur)
            cur, size = [], 0
        cur.append(x)
        size += n
    if cur:
        out.append(cur)
    return out


def rebuild_index(store, recipes):
    """Come rebuildIdx in traduzioni.html: nomi tradotti ancora validi, ingredienti per la spesa,
    e via le traduzioni di ricette che non esistono più."""
    out = {}
    for lang in LANGS:
        all_tr = store.get('recipeTr/' + lang) or {}
        names, counts, orphans = {}, {}, {}
        for rid, tr in all_tr.items():
            r = recipes.get(rid)
            if not isinstance(r, dict):
                orphans[rid] = None
                continue
            if not isinstance(tr, dict) or tr.get('src') != tr_hash(r):
                continue
            names[rid] = [_s(r.get('nome')), _s(tr.get('nome') or r.get('nome'))]
            ti = tr.get('ing') or []
            if isinstance(ti, dict):
                ti = [ti.get(str(j)) for j in range(len(ingredients(r) or []))]
            for j, i in enumerate(ingredients(r) or []):
                if not isinstance(i, dict) or not i.get('name') or j >= len(ti) or not (ti[j] or {}).get('n'):
                    continue
                it, x = _s(i['name']).lower().strip(), ti[j]['n'].strip()
                if it and x and it != x.lower():
                    counts.setdefault(it, {}).setdefault(x, 0)
                    counts[it][x] += 1
        ing = [[it, sorted(c, key=lambda w, c=c: (-c[w], w))[0]] for it, c in sorted(counts.items())]
        store.set('recipeTrIdx/' + lang, {'n': names, 'ing': ing, 'at': int(time.time() * 1000)})
        if orphans:
            store.update('recipeTr/' + lang, orphans)
        out[lang] = (len(names), len(ing), len(orphans))
    return out


def run(store, ask, catalog, max_requests, log=print):
    recipes = store.get('recipes') or {}
    done = {lang: store.get('recipeTr/' + lang) or {} for lang in LANGS}
    todo = []
    for rid, r in recipes.items():
        if not isinstance(r, dict) or not r.get('nome') or ingredients(r) is None:
            continue
        h = tr_hash(r)
        # una ricetta ha bisogno di due traduzioni (le lingue diverse dalla sua): se ci sono e sono valide, è fatta
        if sum((done[lang].get(rid) or {}).get('src') == h for lang in LANGS) >= 2:
            continue
        todo.append({'id': rid, 'src': h, 'it': to_translate(r), 'at': r.get('addedAt') or 0})
    todo.sort(key=lambda x: -(x['at'] if isinstance(x['at'], (int, float)) else 0))  # prima le più nuove
    log('%d recipes to translate' % len(todo))
    queue, ok, failed, requests, retried = batches(todo), 0, {}, 0, set()
    while queue and requests < max_requests:
        batch = queue.pop(0)
        errors = [e for x in batch for e in failed.get(x['id'], [])]
        requests += 1
        try:
            res = ask(build_prompt(batch, catalog, errors))
        except QuotaExhausted:
            log('Gemini quota reached: the rest waits for the next run')
            queue.insert(0, batch)
            break
        writes = {lang: {} for lang in LANGS}
        for x in batch:
            got = (res or {}).get(x['id']) if isinstance(res, dict) else None
            got = got if isinstance(got, dict) else {}
            source = got.get('lang') if got.get('lang') in LANGS else None
            targets = [lang for lang in LANGS if lang != source]
            if isinstance(got.get('de'), dict):
                got['de'] = fix_de(got['de'])
            if source:
                errs = [lang + ': ' + e for lang in targets for e in check(x['it'], got.get(lang), source)]
            else:
                errs = ['"lang" must be it, en or de']
            if errs:
                failed[x['id']] = errs
                if x['id'] not in retried:  # un secondo tentativo, da sola e con gli errori da correggere
                    retried.add(x['id'])
                    queue.append([x])
                continue
            failed.pop(x['id'], None)
            for lang in targets:
                writes[lang][x['id']] = dict(got[lang], src=x['src'], **{'from': source})
            # una traduzione vecchia nella lingua della ricetta stessa non serve più
            if (done[source].get(x['id']) or {}).get('src') not in (None, x['src']):
                writes[source][x['id']] = None
            ok += 1
        for lang in LANGS:
            if writes[lang]:
                store.update('recipeTr/' + lang, writes[lang])
    left = sum(len(b) for b in queue)
    idx = rebuild_index(store, recipes)
    log('translated %d, still to do %d, not accepted %d (requests used %d)' % (ok, left, len(failed), requests))
    for rid, e in list(failed.items())[:10]:
        log('  not accepted %s: %s' % (rid, e[0]))
    for lang, (n, ing, orph) in idx.items():
        log('index %s: %d recipes, %d ingredients, %d removed' % (lang, n, ing, orph))
    return {'ok': ok, 'left': left, 'failed': len(failed), 'requests': requests}


# ── Database: il bot vede e scrive solo ciò che le regole gli permettono ───────────
class FirebaseStore:
    def __init__(self, service_account):
        import firebase_admin
        from firebase_admin import credentials, db

        firebase_admin.initialize_app(
            credentials.Certificate(service_account),
            {'databaseURL': DB_URL, 'databaseAuthVariableOverride': {'uid': 'translator-bot'}},
        )
        self.db = db

    def get(self, path):
        return self.db.reference(path).get()

    def update(self, path, data):
        self.db.reference(path).update(data)

    def set(self, path, data):
        self.db.reference(path).set(data)


def main():
    sa, key = os.environ.get('FIREBASE_SERVICE_ACCOUNT'), os.environ.get('GEMINI_API_KEY')
    if not sa or not key:
        print('::notice::Traduzioni non ancora configurate (mancano i secret FIREBASE_SERVICE_ACCOUNT o GEMINI_API_KEY): salto.')
        return 0
    catalog = load_catalog(os.path.join(HERE, '..', '..', 'i18n.js'))
    gemini = Gemini(key, os.environ.get('GEMINI_MODEL'))
    store = FirebaseStore(json.loads(sa))
    run(store, gemini.ask, catalog, int(os.environ.get('MAX_REQUESTS') or 15))
    print('model', gemini.model, '- API calls', gemini.calls)
    return 0


if __name__ == '__main__':
    sys.exit(main())
