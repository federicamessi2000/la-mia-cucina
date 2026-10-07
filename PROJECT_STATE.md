# Project State — Al Dente (ex La Mia Cucina)

**Last updated:** 2026-10-07
**Branch:** main · **Versione app:** 2026-10-07.9 (cache del service worker `cucina-v40`)
**Repo:** https://github.com/federicamessi2000/la-mia-cucina · **Live:** https://federicamessi2000.github.io/la-mia-cucina/
**Regole Firebase:** https://console.firebase.google.com/project/la-mia-cucina-48a48/database/la-mia-cucina-48a48-default-rtdb/rules

---

## Current State

PWA vanilla JS (`index.html` + `i18n.js`) con Firebase RTDB e Google Auth, ~980 ricette, aperta a qualsiasi account Google, in italiano, inglese e tedesco.
Dal 2026-10-05 si chiama **Al Dente** (prima "La Mia Cucina"): indirizzo, repo e dati sono rimasti gli stessi.

### Funzioni
- Ricette con tre visibilità: "Condivisa con tutti" (`recipes`), "Famiglia" (`families/<codice>/recipes`, c'è solo con un codice famiglia) e "Solo per me" (`users/<uid>/recipes`). Categorie, tag, preferiti, ricerca (anche senza accenti), foto via URL. Modifica/elimina solo l'autore o gli amministratori (gli account di famiglia di Federica); le ricette "Famiglia" chiunque abbia quel codice famiglia, che ne può anche cambiare la visibilità
- **Voti**: da 1 a 5 stelle a testa nella scheda della ricetta (la stessa stella di nuovo toglie il voto); media e numero di voti li vedono tutti, e negli elenchi c'è "★ 4,5". Dati in `ratings/<ricetta>/<uid>`
- **Liste di ricette** (categorie, "Tutte", "Preferiti"): si ordinano per A–Z, tempo, numero di ingredienti, voto o data di aggiunta, nei due versi; chi non ha il dato va in fondo; l'ordine resta sul telefono (`lmc_recipe_sort`). Filtri: Veloce = tag o al massimo 30 minuti dal tempo scritto (`recipeMinutes()` legge "1 ora e 30", "1h30", "20-30'", "1 Std. 15 Min."…); Vegetariano e Vegano = tag oppure ingredienti e nome, con prudenza (brodo, dado e ragù senza "vegetale" contano come carne; nel dubbio la ricetta non compare: basta aggiungerle il tag); Senza glutine solo col tag; ⭐ 4+ stelle; 👤 Mie (private o aggiunte da me)
- Aggiungi/modifica ricette (con categoria), parser "importa da testo"; due libri importati (fonte "Libro")
- Planner mensile/settimanale, personale o di famiglia (fino a 6 piatti per pranzo/cena + extra), kcal stimate. Un tocco su un piatto apre la ricetta alle porzioni pianificate, con la riga "Nel planner: <giorno> · <pasto>" e "Cambia piatto"; ⇄ accanto alla ✕ cambia il piatto (settimana: ogni piatto; mese: il primo), ✕ lo toglie; "Oggi" torna alla settimana o al mese corrente. Fuori casa, freezer e liste di ingredienti al tocco aprono "cambia piatto"
- **Cosa cucino?** (prima card in Ricette): ingredienti in casa + freezer + basi sempre presenti (sale, pepe, acqua, olio, aceto, zucchero, farina) → ricette ordinate per meno ingredienti mancanti; "+ Spesa" aggiunge quelli che mancano. Dispensa in `users/<uid>/pantry`
- "Segnala un problema": salvata in `bugReports` con dettagli tecnici ed errori recenti; Federica le legge in "Segnalazioni" (badge sull'avatar)
- Lista spesa per settimana: da planner (sync che preserva gli spuntati), da ricetta,
  manuale, catalogo con 400+ ingredienti (la ricerca trova anche singolare e plurale: "lasagna" → Lasagne, "pomodoro" → Pomodori);
  merge automatico unità (g/kg, ml/L); categorie ordinabili "a giro supermercato"; condivisione via testo.
  In famiglia due liste: "Famiglia" (condivisa) e "Solo mia" (privata, `users/<uid>/shopping`); ogni azione vale per la lista sullo schermo
- Congelatore per categorie (di famiglia con un codice famiglia)
- **Promemoria del congelatore**: la sera prima, alle 19 di Zurigo, una notifica con i piatti "dal freezer" di pranzo e cena del giorno dopo (planner personale o di famiglia), nella lingua dell'app. Si attiva a testa dal profilo, dall'app sulla schermata Home (iPhone con iOS 16.4+); l'iscrizione del telefono sta in `users/<uid>/push/<id>`. La manda il workflow "Promemoria congelatore" (`.github/workflows/freezer-reminder.yml` → `.github/scripts/freezer_reminder.py`, alle 17:03 e 18:03 UTC): una volta per sera (`reminderLog/<data>`), solo tra le 19 e le 22; le iscrizioni scadute si tolgono da sole; "Run workflow" con "force" manda subito, per provare (a tutti quelli che l'hanno attivato e hanno piatti dal freezer domani). Chi esce dall'account smette di riceverli su quel telefono. Segreti: `FIREBASE_SERVICE_ACCOUNT`, `VAPID_PRIVATE_KEY` (la chiave pubblica è in `index.html`)
- **Famiglia** (codice nel profilo): condivide sempre spesa, planner e congelatore, più le ricette messe su "Famiglia". Chi entra porta i suoi piatti nei pasti ancora vuoti del planner di casa e il suo congelatore in quello di casa (lo stesso nome non raddoppia); le famiglie nate prima lo hanno fatto una volta, alla prima apertura (`families/<codice>/merged/<uid>`). Chi esce ritrova spesa, planner e congelatore personali, più una copia privata delle ricette di famiglia che ha aggiunto
- **Senza rete**: l'app mostra gli ultimi dati salvati sul telefono (spesa, planner, congelatore, preferiti, dispensa) e tiene le modifiche fatte offline, che rimanda all'apertura successiva; uscendo dall'account il telefono li cancella
- **Modalità cucina**: passo-passo full screen, wake lock, timer auto-rilevati
- **Export Bimby/Cookidoo**: testo formattato + guida per Ricette create
- **Lingue**: italiano, inglese, tedesco svizzero ("ss", mai "ß"); segue la lingua del telefono, si cambia dal profilo (`localStorage` `lmc_lang`). I dati restano in italiano canonico (categorie, catalogo, unità): si traduce solo ciò che si vede
- **Ricette tradotte**: ogni ricetta in it/en/de, con "Originale" a un tocco; vale anche per le ricette scritte in tedesco o in inglese
- **Design "Al Dente"**: parete chiara a puntini, contorni blu notte e ombre piene, blu/azzurro/giallo; Unbounded (titoli) + Montserrat (testi); emoji delle categorie su "prese" da arrampicata; dark mode automatica (parete blu notte); icona astratta (192, 512 e maskable)

### Test e pubblicazione
- `tests/app.test.js` (58 test) e `tests/sw.test.js` (5): caricano `index.html` e `sw.js` in Node con un DOM e un Firebase finti; ogni scrittura viene solo registrata, niente arriva al database vero. In locale: `node tests/app.test.js`
- Workflow "Test e pubblicazione" (`.github/workflows/deploy.yml`): a ogni push su `main` gira i test e pubblica su GitHub Pages solo se passano (Pages con build_type "workflow")

### Traduzioni delle ricette
- Dati: `recipeTr/<it|en|de>/<id>` = `{src, from?, nome, tempo?, porzioni?, note?, procedimento?, ing:[{n,s?}]}`; indice leggero `recipeTrIdx/<lang>` = `{n:{id:[nome it, nome tradotto]}, ing:[[it, tradotto]], at}`. `src` è l'impronta (FNV-1a) del testo originale: se la ricetta cambia, la traduzione va rifatta. Stessa funzione in JS e in Python
- Automatiche ogni mese: GitHub Action "Traduci le ricette nuove" (`.github/workflows/translate.yml`, il 1° del mese alle 03:17 UTC, avviabile anche a mano) → `.github/scripts/translate_recipes.py` con Gemini (`gemini-flash-latest`, al massimo 15 richieste per giro: il piano gratuito ne concede circa 20 al giorno). Scrive come utente `translator-bot`. Segreti su GitHub: `FIREBASE_SERVICE_ACCOUNT`, `GEMINI_API_KEY`
- Strumenti per traduzioni in blocco: in locale in `traduzioni/` (nel `.gitignore`, non su GitHub)

### Sicurezza
- `database.rules.json`: lettura per ogni account Google, scrittura per autore (`ownerUid`) o amministratori; spesa, planner, congelatore e ricette di famiglia solo ai membri (le ricette di famiglia con gli stessi controlli delle altre); voti: ognuno scrive solo il suo, un intero da 1 a 5; `recipeTr` e `recipeTrIdx` scrivibili solo dal bot di traduzione o dall'account di Federica, con controlli su lingua e lunghezze
- Le regole vanno incollate e pubblicate a mano nella console Firebase (link in cima): il file nel repo da solo non cambia niente. Ultima pubblicazione: 2026-10-07 (ricette di famiglia + voti)
- Backup notturno sul server di Daniele (+ workflow GitHub opzionale, vedi SECURITY.md)
- I PDF dei libri (`libri ricette/`) e i testi delle traduzioni restano fuori dal repo pubblico (`.gitignore`)
- Strumenti di import una tantum rimossi dal repo (restano nella storia git)

### Note tecniche
- Listener Firebase incrementali (child_added/changed/removed) — niente re-download completo
- Planner referenzia le ricette per ID (retrocompatibile col vecchio formato per nome)
- Ricette: ogni elemento di `recipes` sa da dove arriva (`_priv`, `_fam`; `recipeScope()` → `pub` | `fam` | `priv`). Cambiare visibilità sposta la ricetta con la stessa chiave in un solo update, così planner, preferiti e voti restano validi
- Senza rete: in `localStorage` `lmc_cache_<uid>` (ultimi dati, per parte) e `lmc_outbox` (scritture non ancora confermate). Le scritture passano da un aggancio a `set/update/remove/push` del Reference di Firebase, che le annota finché il database non risponde
- Planner, congelatore e spesa passano da `plannerRef()`, `freezerRef()`, `shopRef()`: con un codice famiglia puntano a `families/<codice>/...`
- Escape HTML centralizzato (`esc()`), URL sanificati (`safeUrl()`), errori di scrittura con toast
- Liste lunghe renderizzate a blocchi da 120
- Testi dell'interfaccia in `i18n.js` (`t()`, `tn()` per i plurali, attributi `data-i18n*`); date con `Intl` (it-IT, en-GB, de-CH)
- Stile: un solo blocco `<style>` in `index.html` con variabili CSS. I nomi sono storici (`--terracotta` = blu principale, `--sage` = azzurro) perché li usano anche gli script
- A ogni rilascio si alzano `APP_VERSION` in `index.html` e `CACHE` in `sw.js`, così i telefoni scaricano la versione nuova. Nome e icona nuovi si vedono dopo aver rimesso l'app nella schermata Home
- Service worker: i file dell'app arrivano dalla rete con `cache: 'no-cache'`, saltando la cache HTTP del browser (GitHub Pages la tiene 10 minuti); così dopo un rilascio `index.html` e `i18n.js` sono sempre della stessa versione (prima si vedevano le chiavi tipo "planner.changeDish"). Le richieste verso altri siti (foto) restano invariate
- iPhone, app dalla schermata Home: `body{overflow-x:clip}` (non solo `hidden`) perché la topbar sticky resti ferma; le pagine a schermo intero (lista di una categoria, "Cosa cucino?") lasciano lo spazio della barra di stato con `env(safe-area-inset-top)`

### Da tenere d'occhio / da fare
- Nel profilo il testo "Il tuo planner è privato." non vale più per chi è in una famiglia (da correggere)
- Chi esce da una famiglia e poi rientra nella stessa vede due volte le ricette che si era portato via (la copia privata e quella di famiglia)
- GitHub spegne i workflow programmati di un repo pubblico dopo 60 giorni senza attività: il "Backup database" su GitHub è spento così (`disabled_inactivity`), e la traduzione mensile e il promemoria del congelatore farebbero la stessa fine. Si riattivano da Actions → workflow → "Enable workflow"
- In futuro: import da link Instagram/TikTok (caption + AI tramite piccolo Worker)
