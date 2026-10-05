# Project State — Al Dente (ex La Mia Cucina)

**Last updated:** 2026-10-05
**Branch:** main · **Versione app:** 2026-10-05.3 (cache del service worker `cucina-v30`)
**Repo:** https://github.com/federicamessi2000/la-mia-cucina · **Live:** https://federicamessi2000.github.io/la-mia-cucina/

---

## Current State

PWA vanilla JS (`index.html` + `i18n.js`) con Firebase RTDB e Google Auth, ~980 ricette, aperta a qualsiasi account Google, in italiano, inglese e tedesco.
Dal 2026-10-05 si chiama **Al Dente** (prima "La Mia Cucina"): indirizzo, repo e dati sono rimasti gli stessi.

### Funzioni
- Ricette condivise o private ("Solo per me", in `users/<uid>/recipes`): categorie, tag, preferiti, ricerca (anche senza accenti), foto via URL; modifica/elimina solo l'autore o la famiglia
- Aggiungi/modifica ricette (con categoria), parser "importa da testo"; due libri importati (fonte "Libro")
- Planner mensile/settimanale privato (fino a 6 piatti per pranzo/cena + extra), kcal stimate
- **Cosa cucino?** (prima card in Ricette): ingredienti in casa + freezer + basi sempre presenti (sale, pepe, acqua, olio, aceto, zucchero, farina) → ricette ordinate per meno ingredienti mancanti; "+ Spesa" aggiunge quelli che mancano. Dispensa in `users/<uid>/pantry`
- "Segnala un problema": salvata in `bugReports` con dettagli tecnici ed errori recenti; Federica le legge in "Segnalazioni" (badge sull'avatar)
- Lista spesa per settimana: da planner (sync che preserva gli spuntati), da ricetta,
  manuale, catalogo con 400+ ingredienti; merge automatico unità (g/kg, ml/L);
  categorie ordinabili "a giro supermercato"; condivisione via testo; spesa condivisa (codice famiglia)
- Congelatore per categorie
- **Modalità cucina**: passo-passo full screen, wake lock, timer auto-rilevati
- **Export Bimby/Cookidoo**: testo formattato + guida per Ricette create
- **Lingue**: italiano, inglese, tedesco svizzero ("ss", mai "ß"); segue la lingua del telefono, si cambia dal profilo (`localStorage` `lmc_lang`). I dati restano in italiano canonico (categorie, catalogo, unità): si traduce solo ciò che si vede
- **Ricette tradotte**: ogni ricetta in it/en/de, con "Originale" a un tocco; vale anche per le ricette scritte in tedesco o in inglese
- **Design "Al Dente"**: parete chiara a puntini, contorni blu notte e ombre piene, blu/azzurro/giallo; Unbounded (titoli) + Montserrat (testi); emoji delle categorie su "prese" da arrampicata; dark mode automatica (parete blu notte); icona astratta (192, 512 e maskable)

### Traduzioni delle ricette
- Dati: `recipeTr/<it|en|de>/<id>` = `{src, from?, nome, tempo?, porzioni?, note?, procedimento?, ing:[{n,s?}]}`; indice leggero `recipeTrIdx/<lang>` = `{n:{id:[nome it, nome tradotto]}, ing:[[it, tradotto]], at}`. `src` è l'impronta (FNV-1a) del testo originale: se la ricetta cambia, la traduzione va rifatta. Stessa funzione in JS e in Python
- Automatiche ogni mese: GitHub Action "Traduci le ricette nuove" (`.github/workflows/translate.yml`, il 1° del mese alle 03:17 UTC, avviabile anche a mano) → `.github/scripts/translate_recipes.py` con Gemini (`gemini-flash-latest`, al massimo 15 richieste per giro: il piano gratuito ne concede circa 20 al giorno). Scrive come utente `translator-bot`. Segreti su GitHub: `FIREBASE_SERVICE_ACCOUNT`, `GEMINI_API_KEY`
- Strumenti per traduzioni in blocco: in locale in `traduzioni/` (nel `.gitignore`, non su GitHub)

### Sicurezza
- `database.rules.json`: lettura per ogni account Google, scrittura per autore (`ownerUid`) o famiglia; spesa condivisa ai soli membri; `recipeTr` e `recipeTrIdx` scrivibili solo dal bot di traduzione o dall'account di Federica, con controlli su lingua e lunghezze
- Backup notturno sul server di Daniele (+ workflow GitHub opzionale, vedi SECURITY.md)
- I PDF dei libri (`libri ricette/`) e i testi delle traduzioni restano fuori dal repo pubblico (`.gitignore`)
- Strumenti di import una tantum rimossi dal repo (restano nella storia git)

### Note tecniche
- Listener Firebase incrementali (child_added/changed/removed) — niente re-download completo
- Planner referenzia le ricette per ID (retrocompatibile col vecchio formato per nome)
- Escape HTML centralizzato (`esc()`), URL sanificati (`safeUrl()`), errori di scrittura con toast
- Liste lunghe renderizzate a blocchi da 120
- Testi dell'interfaccia in `i18n.js` (`t()`, `tn()` per i plurali, attributi `data-i18n*`); date con `Intl` (it-IT, en-GB, de-CH)
- Stile: un solo blocco `<style>` in `index.html` con variabili CSS. I nomi sono storici (`--terracotta` = blu principale, `--sage` = azzurro) perché li usano anche gli script
- A ogni rilascio si alzano `APP_VERSION` in `index.html` e `CACHE` in `sw.js`, così i telefoni scaricano la versione nuova. Nome e icona nuovi si vedono dopo aver rimesso l'app nella schermata Home

### Da tenere d'occhio / da fare
- GitHub spegne i workflow programmati di un repo pubblico dopo 60 giorni senza attività: il "Backup database" su GitHub è spento così (`disabled_inactivity`), e la traduzione mensile farebbe la stessa fine. Si riattivano da Actions → workflow → "Enable workflow"
- In futuro: import da link Instagram/TikTok (caption + AI tramite piccolo Worker)
