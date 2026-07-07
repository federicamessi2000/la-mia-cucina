"""
Processa le ricette della mamma (iPhone Notes) e genera import-mamma.html
con i dati incorporati, pronta per importare in Firebase.
"""
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

PYTHON = "C:/Users/feme/AppData/Local/Programs/Python/Python312/python.exe"

# ── Load ──────────────────────────────────────────────────────────────────────
with open('mamma ricette/ricette.json', encoding='utf-8') as f:
    raw = json.load(f)

# ── Filter ────────────────────────────────────────────────────────────────────
recipes = [r for r in raw
           if r.get('probabile_ricetta')
           and not r.get('solo_immagine')
           and r.get('testo', '').strip()]

print(f"Dopo filtro: {len(recipes)} ricette")

# ── Helpers ───────────────────────────────────────────────────────────────────
SOCIAL_PREFIXES = re.compile(
    r'^(Alzi la mano|Hai mai|Lo sai che|Prova questa|Salva questa|'
    r'Segui la ricetta|Ingredienti per|Clicca qui|Eccovi|Ecco come|'
    r'Chi non ama|Adoro questa|Se ami|Ti serve|Scopri come)',
    re.IGNORECASE)

def clean_title(titolo, testo):
    t = titolo.strip()
    # Remove [foto] from title
    t = re.sub(r'\[foto\]', '', t).strip()
    # Remove trailing ellipsis noise from iPhone cut-off
    t = re.sub(r'[…\.]{2,}$', '', t).strip()
    t = re.sub(r'[,\s]+$', '', t).strip()
    # If title starts with a number, try to find a better one in the text
    if re.match(r'^\d', t):
        # Look for lines like "Ricetta: XYZ" or headings in ALL CAPS
        caps_match = re.search(r'\n([A-ZÀÈÉÌÒÙ][A-ZÀÈÉÌÒÙA-Za-z\s\-]{4,40})\n', testo)
        if caps_match:
            candidate = caps_match.group(1).strip()
            if 3 < len(candidate) < 60:
                return candidate.title()
        return t  # keep numeric title as-is
    # Shorten very long social-media-style titles
    if len(t) > 60:
        # Try to cut at first meaningful break
        for sep in [' - ', ', ', '...', '…', '!', '?']:
            idx = t.find(sep)
            if 15 < idx < 60:
                t = t[:idx].strip()
                break
        else:
            # Hard cut at last space before 55 chars
            t = t[:55].rsplit(' ', 1)[0]
    return t

def clean_text(testo):
    # Remove [foto] markers
    t = re.sub(r'\[foto\]', '', testo)
    # Normalize whitespace runs (keep single blank lines)
    t = re.sub(r'\n{3,}', '\n\n', t)
    # Remove social-media noise lines (very short filler lines)
    lines = t.split('\n')
    lines = [l for l in lines if not re.match(r'^\s*(PUBBLICITÀ|inRead|Teads|Seguitemi su|Facebook|Instagram|seguimi)\s*$', l, re.I)]
    return '\n'.join(lines).strip()

def dedup_key(nome):
    # Normalize for dedup: lowercase, remove punctuation, collapse spaces
    return re.sub(r'[\s\W]+', '', nome.lower())

# ── Process ───────────────────────────────────────────────────────────────────
seen_keys = set()
output = []

for r in recipes:
    nome = clean_title(r.get('titolo', ''), r.get('testo', ''))
    if not nome:
        continue

    dk = dedup_key(nome)
    if dk in seen_keys:
        # Keep the most-recently-modified duplicate
        existing_idx = next((i for i, x in enumerate(output) if dedup_key(x['nome']) == dk), None)
        if existing_idx is not None:
            existing = output[existing_idx]
            if r.get('data_modifica', '') > existing.get('_data', ''):
                output[existing_idx] = {
                    'nome': nome,
                    'fonte': 'mamma',
                    'addedBy': 'La mamma',
                    'procedimento': clean_text(r.get('testo', '')),
                    'ingredienti': [],
                    'note': '',
                    'tags': [],
                    '_importId': r['id'],
                    '_data': r.get('data_modifica', ''),
                }
        continue
    seen_keys.add(dk)

    output.append({
        'nome': nome,
        'fonte': 'mamma',
        'addedBy': 'La mamma',
        'procedimento': clean_text(r.get('testo', '')),
        'ingredienti': [],
        'note': '',
        'tags': [],
        '_importId': r['id'],
        '_data': r.get('data_modifica', ''),
    })

# Remove internal _data field before export
for r in output:
    r.pop('_data', None)

print(f"Dopo dedup: {len(output)} ricette")
print(f"Titoli con numero: {sum(1 for r in output if re.match(r'^\d', r['nome']))}")

# ── Sample output ─────────────────────────────────────────────────────────────
print("\nCampione titoli (primi 20):")
for r in output[:20]:
    print(f"  {r['nome'][:60]}")

# ── Write JSON ────────────────────────────────────────────────────────────────
with open('mamma ricette/import_ready.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

size_kb = len(json.dumps(output, ensure_ascii=False).encode('utf-8')) / 1024
print(f"\nFile scritto: mamma ricette/import_ready.json ({size_kb:.0f} KB, {len(output)} ricette)")

# ── Generate import-mamma.html ────────────────────────────────────────────────
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
  button{{background:#7a4f3a;color:#fff;border:none;border-radius:8px;padding:12px 24px;font-size:16px;cursor:pointer;}}
  button:disabled{{background:#ccc;cursor:default;}}
  #status{{margin-top:16px;font-size:14px;line-height:1.6;}}
  .ok{{color:#2d7a3a;}} .err{{color:#c00;}} .info{{color:#555;}}
  progress{{width:100%;height:8px;border-radius:4px;margin-top:8px;}}
</style>
</head>
<body>
<div class="card">
  <h1>🍝 Import Ricette della Mamma</h1>
  <p>Questa pagina importa <strong>{len(output)} ricette</strong> della mamma in Firebase.<br>
  Apri prima l'app principale in un altro tab (per essere autenticata), poi clicca Import.</p>
  <button id="btn" onclick="startImport()">▶ Avvia Import</button>
  <progress id="prog" value="0" max="{len(output)}" style="display:none"></progress>
  <div id="status"></div>
</div>

<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-database-compat.js"></script>
<script>
firebase.initializeApp({{
  apiKey:"AIzaSyCw9yAhdgvJjQZ1h7NLMZnyMfIJpfvgeTM",
  authDomain:"la-mia-cucina-48a48.firebaseapp.com",
  databaseURL:"https://la-mia-cucina-48a48-default-rtdb.europe-west1.firebasedatabase.app",
  projectId:"la-mia-cucina-48a48"
}});
var db=firebase.database();
var RECIPES={recipes_js};
var log=document.getElementById('status');
var prog=document.getElementById('prog');
var btn=document.getElementById('btn');

function msg(text,cls){{
  var p=document.createElement('p');p.className=cls||'info';p.textContent=text;
  log.insertBefore(p,log.firstChild);
}}

async function startImport(){{
  var user=firebase.auth().currentUser;
  if(!user){{
    msg('Non autenticata. Apri prima app.html e ricarica questa pagina.','err');
    return;
  }}
  btn.disabled=true;
  prog.style.display='block';
  msg('Inizio import di '+RECIPES.length+' ricette...','info');

  // Check which importIds already exist
  var existing=new Set();
  var snap=await db.ref('recipes').orderByChild('_importId').get();
  if(snap.exists())snap.forEach(function(c){{var v=c.val();if(v._importId)existing.add(v._importId);}});
  msg('Già presenti: '+existing.size+' ricette.','info');

  var toImport=RECIPES.filter(function(r){{return!existing.has(r._importId);}});
  msg('Da importare: '+toImport.length+' nuove ricette.','info');
  prog.max=toImport.length||1;

  var ok=0,err=0;
  for(var i=0;i<toImport.length;i++){{
    try{{
      await db.ref('recipes').push(toImport[i]);
      ok++;
    }}catch(e){{
      err++;
      console.error(toImport[i].nome,e);
    }}
    prog.value=i+1;
    if((i+1)%50===0)msg('Importate '+(i+1)+'/'+toImport.length+'...','info');
    // Small delay every 20 to avoid rate limits
    if((i+1)%20===0)await new Promise(function(r){{setTimeout(r,200);}});
  }}
  msg('✅ Completato! '+ok+' importate, '+err+' errori.','ok');
  btn.disabled=false;
}}

// Auto-login via redirect if needed
firebase.auth().onAuthStateChanged(function(user){{
  if(!user){{
    msg('Per favore apri app.html in un altro tab, poi ricarica questa pagina.','info');
    firebase.auth().signInWithPopup(new firebase.auth.GoogleAuthProvider()).catch(function(e){{
      msg('Login fallito: '+e.message,'err');
    }});
  }}else{{
    msg('Autenticata come '+user.email+'. Pronta per import.','ok');
  }}
}});
</script>
</body>
</html>
"""

with open('import-mamma.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML scritto: import-mamma.html")
print("\nProssimo passo: aprire import-mamma.html nel browser e cliccare 'Avvia Import'.")
