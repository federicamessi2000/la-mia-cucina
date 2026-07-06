# Project State — La Mia Cucina

**Last updated:** 2026-07-06
**Branch:** main (+ PR `migliorie-2026-07`)
**Repo:** https://github.com/federicamessi2000/la-mia-cucina

---

## Current State

Single-file PWA (vanilla JS + Firebase RTDB + Google Auth) con ~820 ricette.

### Funzioni
- Ricette condivise: categorie, tag, preferiti, ricerca (anche senza accenti), foto via URL
- Aggiungi/modifica ricette, parser "importa da testo"
- Planner mensile/settimanale privato (pranzo/cena + alternative + extra), kcal stimate
- Lista spesa per settimana: da planner (sync che preserva gli spuntati), da ricetta,
  manuale, catalogo con 400+ ingredienti; merge automatico unità (g/kg, ml/L);
  categorie ordinabili "a giro supermercato"; condivisione via testo; spesa condivisa (codice famiglia)
- Congelatore per categorie
- **Modalità cucina**: passo-passo full screen, wake lock, timer auto-rilevati
- **Export Bimby/Cookidoo**: testo formattato + guida per Ricette create
- Design "trattoria editoriale": Fraunces+Figtree, dark mode automatica, nav flottante

### Sicurezza
- `database.rules.json` con allowlist famiglia — **da pubblicare in Firebase Console** (vedi SECURITY.md)
- Backup notturno via GitHub Actions — **da attivare coi 2 secret** (vedi SECURITY.md)
- Strumenti di import una tantum rimossi dal repo (restano nella storia git)

### Note tecniche
- Listener Firebase incrementali (child_added/changed/removed) — niente re-download completo
- Planner referenzia le ricette per ID (retrocompatibile col vecchio formato per nome)
- Escape HTML centralizzato (`esc()`), URL sanificati (`safeUrl()`), errori di scrittura con toast
- Liste lunghe renderizzate a blocchi da 120
