# Project State — La Mia Cucina

**Last updated:** 2026-06-08  
**Branch:** main  
**Repo:** https://github.com/federicamessi2000/la-mia-cucina

---

## Current State

The app is a fully working single-file PWA. All core features are implemented and functional.

### What works
- Google sign-in via Firebase Auth
- Recipe list with search and filter (Mamma / Web / All)
- Recipe detail modal with scalable portions
- Add recipe manually (form with structured ingredients)
- Add recipe via AI (URL → CORS proxy → Claude API → JSON parse → save)
- Monthly meal planner (pranzo + cena per day, per-user, private)
- Shopping list: manual items + from recipe button + auto-sync from weekly planner
- PWA installable (manifest.json)
- 8 seed recipes loaded on first use

### Files
| File | Purpose |
|------|---------|
| `index.html` | Entire app (HTML + CSS + JS, ~590 lines) |
| `manifest.json` | PWA manifest |
| `README.md` | Project description |

### Known limitations / possible next steps
- Claude API key is called client-side (exposed in browser) — acceptable for personal use, but not for public deployment
- No offline support (no service worker)
- No image support for recipes
- No recipe editing (only add/delete)
- Planner only shows one month at a time; navigation works but no persistent scroll position

---

## Tech Debt
- None critical. The single-file approach is intentional for simplicity.
