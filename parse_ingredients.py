"""
Parser ricette mamma v2 — gestisce titoli sporchi, ingredienti inline,
filtra note non-ricette. Genera import-mamma.html.
"""
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

# ── Unità ─────────────────────────────────────────────────────────────────────
UNITS_MAP = {
    'grammi':'g','grammo':'g','gr':'g','g':'g',
    'kg':'kg','chilo':'kg','chilogrammo':'kg','chilogrammi':'kg',
    'ml':'ml','cc':'ml',
    'dl':'dl','cl':'cl',
    'litri':'L','litro':'L','lt':'L',
    'cucchiaio':'cucchiaio','cucchiai':'cucchiaio',
    'cucchiaino':'cucchiaino','cucchiaini':'cucchiaino',
    'bicchiere':'bicchiere','bicchieri':'bicchiere',
    'bustina':'bustina','bustine':'bustina',
    'mazzetto':'mazzetto','mazzetti':'mazzetto','mazzo':'mazzetto',
    'spicchio':'n°','spicchi':'n°',
    'fetta':'fetta','fette':'fetta',
    'n°':'n°','pz':'n°','pezzi':'n°','pezzo':'n°',
    'pizzico':'pizzico','pizzichi':'pizzico',
    'foglia':'n°','foglie':'n°',
    'scatola':'scatola','scatole':'scatola','lattina':'scatola',
    'rametto':'n°','rametti':'n°',
    'noce':'n°','noci_unita':'n°',
    'filo':'q.b.',
}
UNITS_PAT = '|'.join(re.escape(u) for u in sorted(UNITS_MAP, key=len, reverse=True))
WORD_NUMS = {'un':1,'una':1,'uno':1,'mezzo':0.5,'mezza':0.5,
             'due':2,'tre':3,'quattro':4,'cinque':5,'sei':6}

# Regex per una singola voce ingrediente (numero+unità+nome, o numero+nome, o nome+q.b.)
# Permette anche formato compatto: "240ml", "500g"
RE_ING = re.compile(
    r'(\d+[\.,]?\d*(?:\s*/\s*\d+[\.,]?\d*)?)\s*(' + UNITS_PAT + r')\s*(?:di\s+|d\')?([^\n,;\.]{2,50})'
    r'|(\d+)\s+(?:di\s+)?([a-zA-ZàèéìòùÀÈÉÌÒÙ][^\n,;\.]{1,45})'
    r'|(un[ao]?|mezzo|mezza|due|tre|quattro|cinque|sei)\s+(?:di\s+)?([a-zA-ZàèéìòùÀÈÉÌÒÙ][^\n,;\.]{1,45})'
    r'|([a-zA-ZàèéìòùÀÈÉÌÒÙ][^\n,;\.]{2,45})\s+q\.?\s*b\.?',
    re.IGNORECASE
)

RE_PROC = re.compile(
    r'\b(mescol|versare|cuocer|infornar|incorporar|amalgamar|aggiungere|preparare|'
    r'portare a ebollizione|portate|aggiungete|mescolate|versate|stendete|'
    r'preriscaldare|soffriggere|tagliare|lavare|sbucciare|formare|impastare|'
    r'lasciate lievitare|mettete|unite|incorpor|stemper|dorate|sfornate)\b',
    re.IGNORECASE
)
RE_ING_HEAD = re.compile(r'\bingredienti\b', re.IGNORECASE)
RE_PROC_HEAD = re.compile(
    r'^(preparazione|procedimento|come\s+si\s+(?:fa|prepara)|istruzioni|metodo|'
    r'esecuzione|preparare|cottura|la\s+preparazione)\b',
    re.IGNORECASE
)
RE_SUB_SEC = re.compile(
    r'^(?:per\s+(?:il|la|l\'|i|le|lo|un|una)\s+[\w\s\']{2,30}|'
    r'per\s+la\s+(?:pasta|salsa|crema|farcia|bagna|glassa|decorazione|copertura|marinatura)|'
    r'per\s+il\s+(?:ripieno|condimento|sugo|brodo|fondo|composto|impasto)|'
    r'per\s+la\s+finitura|l\'impasto|la\s+salsa|il\s+ripieno|'
    r'la\s+crema|il\s+sugo|impasto|condimento|decorazione)\s*:?\s*$',
    re.IGNORECASE
)
RE_NOISE = re.compile(
    r'PUBBLICITÀ|inRead invented|Teads|Seguitemi su|seguimi su|seguici su|'
    r'facebook|instagram|youtube|tiktok|pinterest|iscriviti|newsletter|'
    r'\[foto\]|clicca qui|scopri di più|vai alla ricetta|scarica l\'app|'
    r'condividi su|share on|powered by|copyright|all rights reserved',
    re.IGNORECASE
)
RE_FILE = re.compile(r'\.(jpg|jpeg|png|webp|gif|bmp)\b|^\d{5,}_', re.IGNORECASE)
RE_UNIT_INLINE = re.compile(r'\d\s*(?:g|gr|kg|ml|dl|cl|l\b|lt|cucchiai|cucchiaino|bicchiere|bustina)', re.IGNORECASE)


def parse_qty(s):
    s = s.replace(',', '.').strip()
    if '/' in s:
        parts = s.split('/')
        try: return round(float(parts[0].strip()) / float(parts[1].strip()), 2)
        except: pass
    try: return float(s)
    except: return None


def clean_name(s):
    s = re.sub(r'\s*[\(\[].+?[\)\]]', '', s)
    s = re.sub(r'\s+', ' ', s).strip().lower()
    s = re.sub(r'\s*(?:a temperatura ambiente|già pelat[oi]|tritati?|grattugiati?|'
               r'fres[ch][oa]|sott\'olio|in scatola|macinati?|a dadini)\s*$', '', s, flags=re.I)
    return s.strip()


def match_to_ing(m, sezione):
    """Convert a RE_ING match to a dict or None."""
    g = m.groups()
    # Group 1-3: qty+unit+name
    if g[0] and g[1] and g[2]:
        qty = parse_qty(g[0])
        unit = UNITS_MAP.get(g[1].lower(), g[1].lower())
        name = clean_name(g[2])
        if len(name) > 1 and not RE_PROC_HEAD.match(name):
            ing = {'qty': qty, 'unit': unit, 'name': name}
            if sezione: ing['sezione'] = sezione
            return ing
    # Group 4-5: qty only (n°)
    elif g[3] and g[4]:
        qty = parse_qty(g[3])
        name = clean_name(g[4])
        if len(name) > 1 and not RE_PROC_HEAD.match(name) and not RE_PROC.search(name):
            ing = {'qty': qty, 'unit': 'n°', 'name': name}
            if sezione: ing['sezione'] = sezione
            return ing
    # Group 6-7: word number
    elif g[5] and g[6]:
        qty = WORD_NUMS.get(g[5].lower(), 1)
        name = clean_name(g[6])
        if len(name) > 1:
            ing = {'qty': qty, 'unit': 'n°', 'name': name}
            if sezione: ing['sezione'] = sezione
            return ing
    # Group 8: q.b.
    elif g[7]:
        name = clean_name(g[7])
        if len(name) > 1 and not RE_PROC.search(name):
            ing = {'qty': None, 'unit': 'q.b.', 'name': name}
            if sezione: ing['sezione'] = sezione
            return ing
    return None


def parse_inline_list(text, sezione):
    """Parse a comma/dash/dot separated inline ingredient list."""
    results = []
    # Try splitting by common separators, but be careful with decimal numbers
    # Split by ", " or " - " or ". " (only if followed by digit or capital)
    parts = re.split(r',\s*(?=\d|[A-ZàèéìòùÀÈÉÌÒÙ]|\d)|'
                     r'\s+[-–]\s+(?=\d|[A-ZàèéìòùÀÈÉÌÒÙ])|'
                     r'\.\s+(?=\d{1,3}\s*(?:g|gr|kg|ml)|[A-Z])', text)
    for part in parts:
        part = part.strip().rstrip('.')
        if not part or len(part) < 2:
            continue
        for m in RE_ING.finditer(part):
            ing = match_to_ing(m, sezione)
            if ing:
                results.append(ing)
                break
    return results


def parse_single_line(line, sezione):
    """Try to extract ingredients from a single line (may be one item or inline list)."""
    line = line.strip()
    line_clean = re.sub(r'^[-•·*]\s*', '', line).strip()
    if not line_clean or len(line_clean) < 2:
        return []
    if RE_NOISE.search(line_clean):
        return []

    # Check if this is a long inline list (multiple separators + unit patterns)
    comma_count = line_clean.count(',')
    dash_count = len(re.findall(r'\s-\s', line_clean))
    unit_count = len(RE_UNIT_INLINE.findall(line_clean))

    if (comma_count >= 2 or dash_count >= 2) and unit_count >= 2:
        return parse_inline_list(line_clean, sezione)

    # q.b. check
    if re.search(r'\bq\.?\s*b\.?\s*$', line_clean, re.IGNORECASE):
        name = re.sub(r'\s+q\.?\s*b\.?\s*$', '', line_clean, flags=re.IGNORECASE)
        name = clean_name(name)
        if 1 < len(name) < 50:
            ing = {'qty': None, 'unit': 'q.b.', 'name': name}
            if sezione: ing['sezione'] = sezione
            return [ing]

    # Single ingredient match
    for m in RE_ING.finditer(line_clean):
        ing = match_to_ing(m, sezione)
        if ing:
            # Sanity: name should not be very long prose
            if len(ing['name']) < 60 and not RE_PROC.search(ing['name']):
                return [ing]
    return []


def looks_like_ingredient_line(s):
    """True if s looks like an ingredient (quantity or common ingredient word patterns)."""
    if RE_UNIT_INLINE.search(s): return True
    if re.match(r'^\d', s): return True
    if re.match(r'^(?:un[ao]?|mezzo|mezza|due|tre|quattro)\s+', s, re.I): return True
    if re.search(r'\bq\.?\s*b\.?\s*$', s, re.I): return True
    if re.search(r'^(?:sale|pepe|olio|acqua|farina|zucchero|burro|uova?|latte|'
                 r'lievito|panna|basilico|aglio|cipolla|prezzemolo|rosmarino)\b', s, re.I): return True
    return False


def extract_title(titolo, testo):
    """Try to get a meaningful recipe title."""
    t = re.sub(r'\[foto\]', '', titolo).strip()
    t = re.sub(r'[…\.]{2,}$', '', t).strip()
    t = re.sub(r'[,;:\s]+$', '', t).strip()

    is_filename = bool(RE_FILE.match(t))
    starts_num  = bool(re.match(r'^\d', t))
    is_ing_list = bool(RE_UNIT_INLINE.search(t) and (t.count(',') >= 1 or RE_UNIT_INLINE.search(t[:25])))

    if is_filename or starts_num or is_ing_list:
        lines = [l.strip() for l in testo.split('\n') if l.strip()]

        # P1: "NNNN - RECIPE NAME" in original title
        m = re.match(r'^\d+\s*[-–]\s*(.+)', t)
        if m:
            cand = m.group(1).strip()
            if not RE_UNIT_INLINE.search(cand) and len(cand) > 5:
                return title_case(cand[:70])

        # P2: "Ingredienti [Name]:" or "Ingredienti per [Name]:" on first lines
        for line in lines[:6]:
            # Strip leading [foto] noise
            line_c = re.sub(r'\[foto\]\s*', '', line).strip()
            m2 = re.search(r'ingredienti\s+(?:per\s+)?(?:la\s+|le\s+|il\s+|i\s+)?(.{4,50}):\s*$', line_c, re.I)
            if m2:
                cand = m2.group(1).strip()
                if not RE_UNIT_INLINE.search(cand):
                    return title_case(cand[:70])

        # P3: ALL CAPS line in text
        for line in lines[:25]:
            if (line.isupper() and 5 < len(line) < 60
                    and not RE_NOISE.search(line)
                    and not RE_UNIT_INLINE.search(line)
                    and not re.match(r'^\d', line)):
                return title_case(line[:70])

        # P4: recognizable dish name at start of line or after "la/il/per"
        food_pat = re.search(
            r'(?:^|\n|(?:preparare\s+(?:la\s+|il\s+|le\s+|i\s+|l\')|la\s+ricetta\s+(?:della\s+|del\s+)?|ricetta:\s*))'
            r'((?:Torta|Brioche|Gnocchi|Pollo|Biscotti|Focaccia|Crostata|Marmellata|Zuppa|'
            r'Minestra|Insalata|Lasagne|Tagliatelle|Linguine|Fettuccine|Spaghetti|Ragù|'
            r'Frittata|Ciambella|Polpette|Strudel|Bomboloni|Bagel|Panettone|Colomba|'
            r'Pasta Matta|Pasta Frolla|Pasta Brisée|Pasta Sfoglia)[^\n,\.]{2,40})',
            testo[:500], re.IGNORECASE
        )
        if food_pat:
            cand = food_pat.group(1).strip()
            # Trim at first verb/conjunction that makes it a sentence
            cand = re.sub(r'\s+(?:si\s|è\s|che\s|come\s|non\s|ma\s|ed?\s|per\s+(?:far|prepara)).+$', '', cand, flags=re.I).strip().rstrip(',').strip()
            if len(cand) > 4 and not RE_PROC.search(cand):
                return title_case(cand[:70])

        # P5: first non-ingredient, non-noise, non-proc, non-section line (lines 1–15)
        for line in lines[1:15]:
            line_c = re.sub(r'\[foto\]\s*', '', line).strip()
            if (not RE_NOISE.search(line_c)
                    and not looks_like_ingredient_line(line_c)
                    and not re.match(r'^\d', line_c)
                    and 6 < len(line_c) < 65
                    and not RE_PROC_HEAD.match(line_c)
                    and not RE_ING_HEAD.search(line_c)
                    and not RE_PROC.search(line_c)
                    and not RE_SUB_SEC.match(line_c)):
                return title_case(line_c[:70])

        # P6: strip leading qty from title (e.g. "200gr lievito" → "lievito")
        if starts_num:
            # Sort units longest-first to avoid "g" matching before "gr"
            cleaned = re.sub(
                r'^\d+[\.,]?\d*\s*(?:grammi|chilogrammi|grammo|litri|bustine|cucchiai|cucchiaino|kg|gr|ml|dl|cl|lt|g|l\b)?\s*',
                '', t).strip()
            if len(cleaned) > 5 and not RE_UNIT_INLINE.search(cleaned):
                return title_case(cleaned[:70])

        return title_case(t[:70])

    # Title seems OK — shorten if too long
    if len(t) > 65:
        for sep in [' - ', ': ', '! ', '? ', '… ']:
            idx = t.find(sep)
            if 10 < idx < 65:
                t = t[:idx].strip()
                break
        else:
            t = t[:60].rsplit(' ', 1)[0]

    return title_case(t)


def title_case(s):
    """Capitalize recipe title sensibly (ALL CAPS → Title Case, else keep)."""
    s = s.strip()
    if s.isupper():
        return s.title()
    # Fix ALL CAPS at start
    return s[0].upper() + s[1:] if s else s


def is_real_recipe(testo):
    """Return False for very short notes or pure ingredient lists without any procedure."""
    t = testo.strip()
    if len(t) < 80:
        return False
    # Must have either procedure verbs or a procedure header
    has_proc = bool(RE_PROC.search(t)) or bool(re.search(r'(preparazione|procedimento|preparare)', t, re.I))
    # Or must have at least 5 ingredient matches
    ing_count = len(RE_UNIT_INLINE.findall(t))
    if not has_proc and ing_count < 4:
        return False
    return True


def assign_tags(nome, ingredienti, testo):
    tags = []
    ing_names = ' '.join(i.get('name','') for i in ingredienti).lower()
    full = (nome + ' ' + ing_names + ' ' + testo).lower()
    nome_l = nome.lower()

    DOLCE_TITLE = r'\b(torta|biscotti?|crostata|marmellata|brioche|bomboloni?|krapfen|gelato|budino|mousse|cheesecake|dolce|dessert|cannoli?|tiramisù|pannacotta|granita|sorbetto|zuccotto|semifreddo|pandoro|panettone|colomba|pastiera|cassata|muffin|cupcake|macaron|wafer|strudel)\b'
    DOLCE_ING   = r'\b(vanillina|lievito\s+per\s+dolci|cioccolato|nutella|cacao|zucchero\s+a\s+velo)\b'
    is_dolce = (
        bool(re.search(DOLCE_TITLE, nome_l))
        or bool(re.search(DOLCE_ING, ing_names))
        or (re.search(r'\bzucchero\b', ing_names) and re.search(r'\bfarina\b', ing_names)
            and re.search(r'\b(uov[ao]|burro|olio)\b', ing_names))
    )
    if is_dolce:
        tags.append('dolce')

    PASTA_PAT = r'\b(spaghetti|rigatoni|penne|fusilli|tagliatelle?|lasagne?|fettuccine|linguine|tortiglioni|paccheri|bucatini|orecchiette|farfalle?|conchiglie?|tortellini|ravioli|gnocchi)\b'
    if re.search(PASTA_PAT, ing_names) or re.search(PASTA_PAT, nome_l) or re.search(r'\bpasta\b', ing_names):
        tags.append('pasta')

    CARNE_PAT = r'\b(pollo|tacchino|manzo|vitello|maiale|agnello|coniglio|cinghiale|anatra|salsiccia|salame|pancetta|prosciutto|bresaola|speck|mortadella|hamburger|polpette|arrosto|bistecca|cotoletta|carne\s+macinata|ragù)\b'
    if re.search(CARNE_PAT, full):
        tags.append('carne')

    PESCE_PAT = r'\b(pesce|salmone|tonno|merluzzo|branzino|orata|sgombro|sardine?|acciughe?|gamberi|mazzancolle|cozze|vongole|calamari|polpo|seppia|aragosta|astice|scampi|baccalà|stoccafisso|trota|spigola)\b'
    if re.search(PESCE_PAT, full):
        tags.append('pesce')

    has_carne = 'carne' in tags or 'pesce' in tags
    DAIRY_PAT = r'\b(latte|burro|panna|formaggi?|mozzarella|parmigiano|pecorino|ricotta|mascarpone|gorgonzola|fontina|provolone|grana|scamorza|yogurt)\b'
    has_dairy = bool(re.search(DAIRY_PAT, ing_names))
    has_egg   = bool(re.search(r'\buov[ao]\b', ing_names))
    if not has_carne:
        tags.append('vegetariano')
        if not has_dairy and not has_egg:
            tags.append('vegano')

    mentions_gf  = bool(re.search(r'senza\s+glutine|gluten\s*free', full))
    has_gf_flour = bool(re.search(r'\bfarina\s+(?:00|0\b|1\b|2\b|manitoba|integrale|di\s+frumento|di\s+grano)\b', ing_names))
    alt_flour    = bool(re.search(r'\bfarina\s+di\s+(riso|mandorle|mais|ceci|grano\s+saraceno|avena|cocco)\b', ing_names))
    if mentions_gf or (alt_flour and not has_gf_flour and 'pasta' not in tags):
        tags.append('senza-glutine')

    veloce = False
    time_m = re.search(r'(\d+)\s*(?:minut[io]|min\.?)\b', testo, re.I)
    if time_m and int(time_m.group(1)) <= 25:
        veloce = True
    if re.search(r'\b(veloce|rapida?|in\s+\d{1,2}\s+minut|express|svelt[ao]|pochissimo\s+tempo)\b', full):
        veloce = True
    if veloce:
        tags.append('veloce')

    if re.search(r'\b(facile|facilissim[ao]|semplice|semplicissim[ao]|pochi\s+ingredienti|elementare)\b', full):
        tags.append('facile')

    if re.search(r'\b(piatto\s+unico|zuppa|minestra|minestrone|ribollita|stufato|spezzatino|insalata\s+(?:di|con))\b', full):
        tags.append('piatto-unico')

    return list(dict.fromkeys(tags))


def parse_recipe(testo):
    """Returns (ingredienti: list, procedimento: str)"""
    testo = RE_NOISE.sub('', testo)
    testo = re.sub(r'\n{3,}', '\n\n', testo).strip()
    lines = testo.split('\n')

    ing_start = None
    proc_start = None
    for i, line in enumerate(lines):
        ls = line.strip()
        if ing_start is None and RE_ING_HEAD.search(ls) and len(ls) < 60:
            ing_start = i
        if RE_PROC_HEAD.match(ls) and len(ls) < 60:
            proc_start = i
            break

    if ing_start is not None and proc_start is not None and ing_start < proc_start:
        cand_lines = lines[ing_start + 1:proc_start]
        proc_lines = lines[proc_start:]
    elif ing_start is not None:
        cand_lines = lines[ing_start + 1:]
        proc_lines = []
    elif proc_start is not None:
        cand_lines = lines[:proc_start]
        proc_lines = lines[proc_start:]
    else:
        cand_lines = lines
        proc_lines = []

    # Special case: "Ingredienti: X, Y, Z" all on one line
    if ing_start is not None:
        ing_line = lines[ing_start].strip()
        inline_after = re.sub(r'^.*ingredienti\s*:', '', ing_line, flags=re.I).strip()
        if inline_after and RE_UNIT_INLINE.search(inline_after):
            inline_ings = parse_inline_list(inline_after, None)
            if inline_ings:
                proc_text = '\n'.join(proc_lines).strip() or testo
                return inline_ings, proc_text

    ingredienti = []
    sezione = None
    trailing_prose = []
    hit_prose = False

    for line in cand_lines:
        ls = line.strip()
        if not ls:
            continue
        if RE_SUB_SEC.match(ls):
            sezione = ls.rstrip(':').strip()
            continue
        if hit_prose:
            trailing_prose.append(line)
            continue

        ings = parse_single_line(ls, sezione)
        if ings:
            ingredienti.extend(ings)
        else:
            # Is it prose?
            if len(ls) > 60 or RE_PROC.search(ls):
                hit_prose = True
                trailing_prose.append(line)
            # else skip short unrecognized line

    proc_text = '\n'.join(trailing_prose + proc_lines).strip()
    if not proc_text:
        proc_text = testo
    return ingredienti, proc_text


# ── Main ──────────────────────────────────────────────────────────────────────
with open('mamma ricette/ricette.json', encoding='utf-8') as f:
    raw = json.load(f)

filtered = [r for r in raw
            if r.get('probabile_ricetta') and not r.get('solo_immagine')
            and r.get('testo', '').strip()]

def dedup_key(nome):
    return re.sub(r'[\s\W]+', '', nome.lower())

seen = set()
output = []
stats = {'parsed': 0, 'empty': 0, 'skipped_not_recipe': 0}

for r in filtered:
    testo = r.get('testo', '')
    if not is_real_recipe(testo):
        stats['skipped_not_recipe'] += 1
        continue

    nome = extract_title(r.get('titolo', ''), testo)
    if not nome or len(nome) < 3:
        continue
    # Skip obviously bad titles
    if re.match(r'^(q\.?\s*b|x\s*=|\d+\s*[-–]\s*\d+\s*person|i consigli|succo di \d)', nome, re.I):
        continue
    dk = dedup_key(nome)
    if dk in seen:
        continue
    seen.add(dk)

    ings, proc = parse_recipe(testo)
    if ings:
        stats['parsed'] += 1
    else:
        stats['empty'] += 1

    tags = assign_tags(nome, ings, testo)
    rec = {
        'nome': nome,
        'fonte': 'mamma',
        'addedBy': 'La mamma',
        'ingredienti': ings,
        'procedimento': proc,
        'note': '',
        'tags': tags,
        '_importId': r['id'],
    }
    output.append(rec)

print(f"Ricette importabili: {len(output)}")
print(f"  Con ingredienti: {stats['parsed']} ({100*stats['parsed']//max(len(output),1)}%)")
print(f"  Solo testo:      {stats['empty']}")
print(f"  Scartate (non ricette): {stats['skipped_not_recipe']}")
from collections import Counter
tag_counts = Counter(t for r in output for t in r['tags'])
print(f"\nDistribuzione tag:")
for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
    print(f"  {tag:20s} {count}")

# Show sample of improved titles
print("\nCampione titoli:")
for r in output[:30]:
    n = len(r['ingredienti'])
    print(f"  [{n:2d} ing] {r['nome'][:65]}")

# Show a few with ingredients
print("\nEsempi ingredienti:")
with_ings = [r for r in output if len(r['ingredienti']) >= 4][:5]
for r in with_ings:
    print(f"\n  {r['nome']}")
    for i in r['ingredienti'][:6]:
        sez = f" [{i['sezione']}]" if i.get('sezione') else ''
        print(f"    {i.get('qty','')} {i.get('unit','')} {i.get('name','')}{sez}")

# ── Write JSON + HTML ─────────────────────────────────────────────────────────
with open('mamma ricette/import_parsed.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

n = len(output)
recipes_js = json.dumps(output, ensure_ascii=False, separators=(',', ':'))

html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Import Ricette della Mamma</title>
<style>
  body{{font-family:sans-serif;max-width:600px;margin:40px auto;padding:0 20px;background:#f5f0ea;color:#333;}}
  h1{{color:#7a4f3a;font-size:22px;}}
  .card{{background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.1);margin-bottom:20px;}}
  button{{background:#7a4f3a;color:#fff;border:none;border-radius:8px;padding:12px 24px;font-size:15px;cursor:pointer;margin-right:8px;margin-bottom:8px;}}
  button:disabled{{background:#ccc;cursor:default;}}
  button.red{{background:#b00020;}}
  #status{{margin-top:16px;font-size:13px;line-height:1.8;max-height:320px;overflow-y:auto;}}
  .ok{{color:#2d7a3a;font-weight:600;}} .err{{color:#c00;}} .info{{color:#555;}}
  progress{{width:100%;height:10px;border-radius:5px;margin-top:12px;accent-color:#7a4f3a;}}
</style>
</head>
<body>
<div class="card">
  <h1>🍝 Import Ricette della Mamma v2</h1>
  <p><strong>{n} ricette</strong> con ingredienti strutturati (qty + unità + nome + sezioni).</p>
  <p><strong>Passo 1:</strong> cancella le vecchie (senza ingredienti).<br>
     <strong>Passo 2:</strong> importa le nuove.</p>
  <button id="btn-del" onclick="deleteOld()">🗑 Passo 1 – Cancella vecchie</button>
  <button id="btn-imp" onclick="startImport()" disabled>▶ Passo 2 – Importa {n} ricette</button>
  <progress id="prog" value="0" max="{n}" style="display:none"></progress>
  <div id="status"></div>
</div>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-database-compat.js"></script>
<script>
firebase.initializeApp({{apiKey:"AIzaSyCw9yAhdgvJjQZ1h7NLMZnyMfIJpfvgeTM",authDomain:"la-mia-cucina-48a48.firebaseapp.com",databaseURL:"https://la-mia-cucina-48a48-default-rtdb.europe-west1.firebasedatabase.app",projectId:"la-mia-cucina-48a48"}});
var db=firebase.database();
var RECIPES={recipes_js};
var log=document.getElementById('status');
var prog=document.getElementById('prog');
function msg(text,cls){{var p=document.createElement('p');p.style.margin='2px 0';p.className=cls||'info';p.textContent=text;log.appendChild(p);log.scrollTop=log.scrollHeight;}}
async function deleteOld(){{
  if(!firebase.auth().currentUser){{msg('Fai il login prima.','err');return;}}
  document.getElementById('btn-del').disabled=true;
  msg('Lettura ricette in corso...','info');
  var snap=await db.ref('recipes').get();
  if(!snap.exists()){{msg('Nessuna ricetta trovata.','info');document.getElementById('btn-imp').disabled=false;return;}}
  var toDelete=[];
  snap.forEach(function(c){{var v=c.val();if(v.addedBy==='La mamma'||v._importId)toDelete.push(c.key);}});
  msg('Cancello '+toDelete.length+' ricette...','info');
  for(var i=0;i<toDelete.length;i++){{
    await db.ref('recipes/'+toDelete[i]).remove();
    if((i+1)%20===0)msg('Cancellate '+(i+1)+'/'+toDelete.length+'...','info');
    if((i+1)%20===0)await new Promise(function(r){{setTimeout(r,100);}});
  }}
  msg('✅ Cancellate '+toDelete.length+' ricette. Ora clicca Passo 2.','ok');
  document.getElementById('btn-imp').disabled=false;
}}
async function startImport(){{
  if(!firebase.auth().currentUser){{msg('Fai il login prima.','err');return;}}
  document.getElementById('btn-imp').disabled=true;
  prog.style.display='block';prog.value=0;prog.max=RECIPES.length;
  msg('Importo '+RECIPES.length+' ricette...','info');
  var ok=0,err=0;
  for(var i=0;i<RECIPES.length;i++){{
    try{{await db.ref('recipes').push(RECIPES[i]);ok++;}}
    catch(e){{err++;console.error(RECIPES[i].nome,e);}}
    prog.value=i+1;
    if((i+1)%10===0)msg((i+1)+' / '+RECIPES.length+'...','info');
    if((i+1)%20===0)await new Promise(function(r){{setTimeout(r,200);}});
  }}
  msg('✅ Completato! '+ok+' importate'+(err?' — '+err+' errori':'')+'.','ok');
}}
firebase.auth().onAuthStateChanged(function(user){{
  if(!user){{
    firebase.auth().signInWithPopup(new firebase.auth.GoogleAuthProvider()).catch(function(e){{msg('Login fallito: '+e.message,'err');}});
  }}else{{
    msg('✅ Loggata come '+user.email+' — Pronta.','ok');
  }}
}});
</script>
</body>
</html>"""

with open('import-mamma.html', 'w', encoding='utf-8') as f:
    f.write(html)
size_kb = len(recipes_js.encode()) // 1024
print(f"\nFile: import_parsed.json ({size_kb} KB) + import-mamma.html pronti.")
