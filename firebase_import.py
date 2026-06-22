import json, urllib.request, urllib.error, sys, time, re, collections
sys.stdout.reconfigure(encoding='utf-8')

TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImVlOTA0NmVhZDJlMDUwMDAxMGVkNTA0M2I0ODNkODRiMGM1MmM3YzQiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiRmVkZXJpY2EgTWVzc2kiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jSklJN0tYQmYzcWNHRTVXSERyZkNTdzdMMlZmZ3IxbmluSm9QdHd1OUd1N1lxSXp3PXM5Ni1jIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL2xhLW1pYS1jdWNpbmEtNDhhNDgiLCJhdWQiOiJsYS1taWEtY3VjaW5hLTQ4YTQ4IiwiYXV0aF90aW1lIjoxNzgxODczNjg0LCJ1c2VyX2lkIjoiSkc1OG4xNFE0OGhaVkJSaVozNGdSMHo5bE5sMSIsInN1YiI6IkpHNThuMTRRNDhoWlZCUmlaMzRnUjB6OWxObDEiLCJpYXQiOjE3ODIxMTc2MDYsImV4cCI6MTc4MjEyMTIwNiwiZW1haWwiOiJmZWRlcmljYW1lc3NpMjAwMEBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJnb29nbGUuY29tIjpbIjExMTY1NDI5NzYwNTU2MTQyMTgxMiJdLCJlbWFpbCI6WyJmZWRlcmljYW1lc3NpMjAwMEBnbWFpbC5jb20iXX0sInNpZ25faW5fcHJvdmlkZXIiOiJnb29nbGUuY29tIn19.W1gqWXFDj7HqNumI13qeGiySKpD9ViN-aVyLJTdVqyP8uwdKz-TvIWSN8E1A6ajBMxhGNwDrhPHtKDKryAh-EbmZnvRKzfh8ih6Rb7nZl1jPW7spERn_VtV_zLonsZZFaTSIe0AeYlpVsEe7TnIfCj810oO37Q3ueeFlRO3jGw7cUD_mRIFhlsILKqgL2K0fNH3m840tux7dY9G8SHrHAGY9cLnUQYDDTe-haOaUfDSublcqMvQpcJOdl8AiOWYA0Cp9TnlJ2dObyBbbNW_EptwCmSu5LvzzEMAZftuCYWfjxoWMtweIvpN_D1z-3ecbNSTcFP9Ah4I6lruyKYxC9w"
DB = "https://la-mia-cucina-48a48-default-rtdb.europe-west1.firebasedatabase.app"

# ── Firebase REST helpers ─────────────────────────────────────────────────────
def fb_get(path):
    url = f"{DB}/{path}.json?auth={TOKEN}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())

def fb_delete(path):
    url = f"{DB}/{path}.json?auth={TOKEN}"
    req = urllib.request.Request(url, method='DELETE')
    urllib.request.urlopen(req, timeout=30)

def fb_post(path, data):
    url = f"{DB}/{path}.json?auth={TOKEN}"
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST',
                                  headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(req, timeout=30)

# ── Tag derivation (based on ingredients + procedure, overrides AI tags) ──────
CARNE_PAT = re.compile(
    r'\b(pollo|petto\s+di\s+pollo|tacchino|manzo|vitello|maiale|agnello|coniglio|'
    r'cinghiale|anatra|salsiccia|salame|pancetta|prosciutto|bresaola|speck|mortadella|'
    r'hamburger|polpette|arrosto|bistecca|cotoletta|carne\s+macinata|ragù|wurstel|lonza|'
    r'lardo|guanciale|coppa|nduja|carpaccio|tartare)\b', re.I)

PESCE_PAT = re.compile(
    r'\b(pesce|salmone|tonno|merluzzo|branzino|orata|sgombro|sardine?|acciughe?|'
    r'gamberi|mazzancolle|cozze|vongole|calamari|polpo|seppia|aragosta|scampi|'
    r'baccalà|stoccafisso|trota|spigola|dentice|sogliola|rombo|anguilla|surimi)\b', re.I)

PASTA_PAT = re.compile(
    r'\b(spaghetti|rigatoni|penne|fusilli|tagliatelle?|lasagne?|fettuccine|linguine|'
    r'tortellini|ravioli|gnocchi|orecchiette|farfalle?|bucatini|paccheri|mezze\s+penne|'
    r'calamarata|trofie|maltagliati|pappardelle|maccheroni)\b', re.I)

DAIRY_PAT = re.compile(
    r'\b(latte|burro|panna|formaggio|mozzarella|parmigiano|pecorino|ricotta|'
    r'mascarpone|gorgonzola|brie|fontina|scamorza|yogurt|kefir|panna\s+acida)\b', re.I)

EGG_PAT    = re.compile(r'\buov[ao]\b', re.I)
GLUTEN_PAT = re.compile(
    r'\b(farina\s+(?:00|0|1|2|integrale|manitoba|di\s+frumento|di\s+grano)|'
    r'semola|pangrattato|pane\s+gratt|biscotti|pasta\s+fresca)\b', re.I)

LIEVITO_PAT = re.compile(
    r'\b(lievito\s+madre|lievito\s+di\s+birra|lievito\s+naturale|biga|pasta\s+madre|'
    r'poolish|lievito\s+secco|lievito\s+fresco)\b', re.I)

FORNO_PAT  = re.compile(r'\b(forno|inforna|infornare|cuoci\s+in\s+forno|metti\s+in\s+forno)\b', re.I)
FRITTO_PAT = re.compile(r'\b(friggi|friggere|fritto|olio\s+di\s+arachidi|frittura|fritti)\b', re.I)
DOLCE_CATS = {'Dolci', 'Torte', 'Biscotti', 'Colazione'}
SALATO_CATS = {'Antipasti', 'Primi', 'Secondi', 'Contorni', 'Conserve', 'Salse e Creme'}
LIEVITO_CATS = {'Lievitati', 'Pane e Pizza'}

def derive_tags(r):
    titolo   = r.get('titolo', '').lower()
    categoria = r.get('categoria', '')
    old_tags  = set(r.get('tag', []))
    ings      = r.get('ingredienti', [])
    ing_str   = ' '.join(i.get('nome', '') for i in ings).lower()
    proc_str  = ' '.join(r.get('procedimento', [])).lower()
    full      = f"{titolo} {ing_str} {proc_str}"
    tags = []

    # CARNE / PESCE (ingredient-based, most reliable)
    has_carne = bool(CARNE_PAT.search(full))
    has_pesce = bool(PESCE_PAT.search(full))
    if has_carne: tags.append('carne')
    if has_pesce: tags.append('pesce')

    # PASTA (ingredient-based)
    if PASTA_PAT.search(ing_str) or PASTA_PAT.search(titolo):
        tags.append('pasta')

    # DOLCE
    is_dolce = (
        categoria in DOLCE_CATS
        or 'dolce' in old_tags
        or re.search(r'\b(torta|biscotti?|crostata|marmellata|budino|mousse|cheesecake|'
                     r'tiramisù|pandoro|panettone|pastiera|cassata|cannolo|gelato|sorbetto|'
                     r'panna\s+cotta|zeppole|struffoli|strudel|macaron|meringhe?|mousse)\b', titolo)
    )
    if is_dolce: tags.append('dolce')

    # SALATO
    if not is_dolce and (categoria in SALATO_CATS or 'salato' in old_tags):
        tags.append('salato')

    # VEGETARIANO
    if not has_carne and not has_pesce:
        tags.append('vegetariano')
        # VEGANO
        if not DAIRY_PAT.search(ing_str) and not EGG_PAT.search(ing_str) and not re.search(r'\bmiele\b', ing_str):
            tags.append('vegano')

    # SENZA GLUTINE
    if 'senza glutine' in old_tags or 'senza-glutine' in old_tags:
        if not GLUTEN_PAT.search(ing_str):  # double-check ingredients
            tags.append('senza-glutine')
    elif not GLUTEN_PAT.search(ing_str) and re.search(r'senza\s+glutine', full):
        tags.append('senza-glutine')

    # SENZA LATTOSIO
    if 'senza lattosio' in old_tags:
        tags.append('senza-lattosio')

    # LIEVITATO
    if (categoria in LIEVITO_CATS
            or LIEVITO_PAT.search(ing_str)
            or any(t in old_tags for t in ['lievitato','lievitati','lievito madre','lievito di birra','biga'])):
        tags.append('lievitato')

    # AL FORNO
    if 'al forno' in old_tags or FORNO_PAT.search(proc_str):
        tags.append('al-forno')

    # FRITTO
    if 'fritto' in old_tags or FRITTO_PAT.search(proc_str):
        tags.append('fritto')

    # COLAZIONE
    if categoria == 'Colazione' or 'colazione' in old_tags:
        tags.append('colazione')

    # VELOCE (ingredient-based time estimate takes priority)
    tempo_tot = estimate_time(r)
    if tempo_tot is not None and tempo_tot <= 30:
        tags.append('veloce')
    elif 'veloce' in old_tags:
        tags.append('veloce')

    # FACILE
    if r.get('difficolta') == 'Facile':
        tags.append('facile')

    # DA FOTO (keep as informational tag)
    if 'da-foto' in old_tags:
        tags.append('da-foto')

    return list(dict.fromkeys(tags))  # deduplicate

# ── Time estimation ───────────────────────────────────────────────────────────
def estimate_time(r):
    prep = r.get('tempo_preparazione_min')
    cook = r.get('tempo_cottura_min')
    if prep is not None and cook is not None:
        return prep + cook
    if prep is not None:
        return prep
    if cook is not None:
        return cook
    # Estimate from procedure text
    proc = ' '.join(r.get('procedimento', []))
    mins = []
    for m in re.finditer(r'(\d+)(?:\s*[–-]\s*\d+)?\s*(?:minut[oi]|min\.?)', proc, re.I):
        mins.append(int(m.group(1)))
    for m in re.finditer(r'(\d+)(?:\s*[–-]\s*\d+)?\s*or[ae]\b', proc, re.I):
        v = int(m.group(1)) * 60
        if v <= 480:  # exclude multi-day leavening
            mins.append(v)
    if not mins:
        return None
    # Take the sum of the 3 largest "reasonable" values (prep + cook + rest)
    reasonable = [t for t in mins if t <= 180]
    return sum(sorted(reasonable, reverse=True)[:3]) if reasonable else None

# ── Ingredient mapping ────────────────────────────────────────────────────────
def map_ingredienti(ings):
    result = []
    for i in ings:
        nome_raw = i.get('nome', '').strip()
        # Extract section from suffix " - sezione"
        sezione = None
        if ' - ' in nome_raw:
            parts = nome_raw.rsplit(' - ', 1)
            nome_clean = parts[0].strip()
            sezione_candidate = parts[1].strip()
            # Only treat as section if it looks like a section label (short, no numbers)
            if len(sezione_candidate) < 30 and not re.search(r'\d', sezione_candidate):
                sezione = sezione_candidate
                nome_raw = nome_clean
        # Parse quantity
        qty_raw = i.get('quantita', '')
        qty = None
        if qty_raw and qty_raw.lower() not in ('q.b.', 'qb', ''):
            m = re.match(r'^(\d+(?:[.,]\d+)?)', str(qty_raw).strip())
            if m:
                try:
                    qty = float(m.group(1).replace(',', '.'))
                except ValueError:
                    pass
        ing = {'qty': qty, 'unit': i.get('unita', '').strip(), 'name': nome_raw}
        if sezione:
            ing['sezione'] = sezione
        result.append(ing)
    return result

# ── Porzioni extraction ───────────────────────────────────────────────────────
def extract_porzioni(s):
    if not s:
        return 4
    m = re.search(r'(\d+)', str(s))
    return int(m.group(1)) if m else 4

# ── Full recipe mapping ───────────────────────────────────────────────────────
def map_recipe(r):
    tempo_min = estimate_time(r)
    tempo_str = None
    if tempo_min:
        h, m = divmod(tempo_min, 60)
        tempo_str = f"{h}h {m}min" if h else f"{m} min"
    procedimento = r.get('procedimento', [])
    proc_text = '\n\n'.join(procedimento) if isinstance(procedimento, list) else str(procedimento)
    tags = derive_tags(r)
    return {
        'nome':          r.get('titolo', '').strip(),
        'fonte':         'mamma',
        'addedBy':       'La mamma',
        'categoria':     r.get('categoria', ''),
        'difficolta':    r.get('difficolta', ''),
        'porzioni':      extract_porzioni(r.get('porzioni')),
        'tempo':         tempo_str,
        'ingredienti':   map_ingredienti(r.get('ingredienti', [])),
        'procedimento':  proc_text,
        'note':          r.get('note', '') or '',
        'tags':          tags,
        '_importId':     r.get('id'),
        'fonte_originale': r.get('fonte_originale', '') or '',
    }

# ── Load and filter ───────────────────────────────────────────────────────────
print("Caricamento ricette_pulite.json...")
with open('ricette mamma/ricette_pulite.json', encoding='utf-8') as f:
    raw = json.load(f)

to_import = []
skipped = []
NON_RECIPE_PAT = re.compile(
    r'\b(lista\s+della\s+spesa|lista\s+cose|trucchi\s+per|istruzioni\s+per\s+il\s+cane|'
    r'come\s+pulire|pulire\s+il\s+forno|esca\s+anti|racconto\s+di\s+natale|'
    r'testo\s+non\s+culinario|catena|profezia|pantana|men[uù]\s*:|la\s+forza\s+della\s+farina|'
    r'estratto\s+dal\s+libro|a\s+braccia\s+aperte|conversione\s+del\s+lievito)\b', re.I)

for r in raw:
    cat = r.get('categoria', '')
    titolo = r.get('titolo', '')
    is_da_foto = 'da-foto' in r.get('tag', [])
    has_ings = len(r.get('ingredienti', [])) >= 2
    has_proc = len(r.get('procedimento', [])) >= 2
    if cat == 'Altro' and not is_da_foto:
        # Keep only if it clearly has recipe data and doesn't match non-recipe patterns
        if has_ings and has_proc and not NON_RECIPE_PAT.search(titolo):
            to_import.append(r)
        else:
            skipped.append(titolo)
        continue
    to_import.append(r)

print(f"Da importare: {len(to_import)} | Scartate (note non-ricetta): {len(skipped)}")
print("Scartate:", skipped[:8])

# Process
print("\nElaborazione tag e tempi...")
processed = [map_recipe(r) for r in to_import]

# Stats
tag_counts = collections.Counter(t for r in processed for t in r['tags'])
no_time = sum(1 for r in processed if not r['tempo'])
print("Tag distribution:", dict(tag_counts.most_common(16)))
print(f"Senza tempo: {no_time}/{len(processed)}")
print(f"\nEsempio: {processed[1]['nome']}")
print(f"  Tags: {processed[1]['tags']}")
print(f"  Tempo: {processed[1]['tempo']}")
print(f"  Ingredienti ({len(processed[1]['ingredienti'])}): {processed[1]['ingredienti'][:3]}")

# ── Step 1: Delete old mamma recipes ─────────────────────────────────────────
print("\n" + "="*50)
print("STEP 1: Cancellazione ricette vecchie...")
try:
    all_r = fb_get('recipes')
except urllib.error.HTTPError as e:
    print(f"ERRORE Firebase: {e.code} {e.reason}")
    if e.code == 401:
        print("Token scaduto! Servito un nuovo token.")
    sys.exit(1)

if all_r:
    to_del = [k for k, v in all_r.items()
              if v.get('addedBy') == 'La mamma' or v.get('_importId')]
    print(f"Trovate {len(to_del)} ricette della mamma da cancellare")
    for i, key in enumerate(to_del):
        fb_delete(f'recipes/{key}')
        if (i+1) % 30 == 0:
            print(f"  Cancellate {i+1}/{len(to_del)}...")
            time.sleep(0.1)
    print(f"✓ Cancellate {len(to_del)} ricette")
else:
    print("Nessuna ricetta esistente.")

# ── Step 2: Import ────────────────────────────────────────────────────────────
print("\nSTEP 2: Import ricette...")
ok = err = 0
for i, r in enumerate(processed):
    try:
        fb_post('recipes', r)
        ok += 1
    except urllib.error.HTTPError as e:
        err += 1
        if e.code == 401:
            print(f"\nToken scaduto a ricetta {i+1}! Importate {ok} finora.")
            sys.exit(1)
        print(f"  ERRORE [{r['nome'][:35]}]: {e.code}")
    except Exception as e:
        err += 1
        print(f"  ERRORE [{r['nome'][:35]}]: {e}")
    if (i+1) % 30 == 0:
        print(f"  {i+1}/{len(processed)} importate...")
        time.sleep(0.2)

print(f"\n✅ Fatto! {ok} importate, {err} errori.")
