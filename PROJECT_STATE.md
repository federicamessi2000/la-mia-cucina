# Project State — La Mia Cucina

**Last updated:** 2026-09-30
**Branch:** main
**Repo:** https://github.com/federicamessi2000/la-mia-cucina

---

## Current State

Single-file PWA (vanilla JS + Firebase RTDB + Google Auth) con ~980 ricette, aperta a qualsiasi account Google.

### Funzioni
- Ricette condivise o private ("Solo per me", in `users/<uid>/recipes`): categorie, tag, preferiti, ricerca (anche senza accenti), foto via URL; modifica/elimina solo l'autore o la famiglia
- Aggiungi/modifica ricette (con categoria), parser "importa da testo"; due libri importati (fonte "Libro")
- Planner mensile/settimanale privato (fino a 6 piatti per pranzo/cena + extra), kcal stimate
- "Segnala un problema": mailto precompilato con dettagli tecnici ed errori recenti
- Lista spesa per settimana: da planner (sync che preserva gli spuntati), da ricetta,
  manuale, catalogo con 400+ ingredienti; merge automatico unità (g/kg, ml/L);
  categorie ordinabili "a giro supermercato"; condivisione via testo; spesa condivisa (codice famiglia)
- Congelatore per categorie
- **Modalità cucina**: passo-passo full screen, wake lock, timer auto-rilevati
- **Export Bimby/Cookidoo**: testo formattato + guida per Ricette create
- Design "trattoria editoriale": Fraunces+Figtree, dark mode automatica, nav flottante

### Sicurezza
- `database.rules.json`: lettura per ogni account Google, scrittura per autore (`ownerUid`) o famiglia; spesa condivisa ai soli membri — **pubblicate il 2026-09-30**
- Backup notturno sul server di Daniele (+ workflow GitHub opzionale, vedi SECURITY.md)
- Strumenti di import una tantum rimossi dal repo (restano nella storia git)
- Da fare in futuro: import da link Instagram/TikTok (caption + AI tramite piccolo Worker)

### Note tecniche
- Listener Firebase incrementali (child_added/changed/removed) — niente re-download completo
- Planner referenzia le ricette per ID (retrocompatibile col vecchio formato per nome)
- Escape HTML centralizzato (`esc()`), URL sanificati (`safeUrl()`), errori di scrittura con toast
- Liste lunghe renderizzate a blocchi da 120
