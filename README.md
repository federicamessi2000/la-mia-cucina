# La Mia Cucina

App di ricette di famiglia, mobile-first — ricette condivise, planner dei pasti, lista della spesa intelligente, congelatore e modalità cucina passo-passo.

**Live:** https://federicamessi2000.github.io/la-mia-cucina/

---

## Funzioni

- **Ricette** — ~820 ricette condivise (di mamma e dal web), categorie, tag, preferiti, ricerca anche senza accenti, porzioni scalabili, kcal stimate
- **Aggiungi** — form con ingredienti strutturati, autocomplete dal catalogo, "importa da testo" che compila il form da una ricetta incollata
- **Planner** — pianificazione pranzo/cena per settimana o mese, privata per account, con alternative, extra e "fuori casa"
- **Spesa** — si popola dal planner (ricordando ciò che hai già spuntato), da ricette o a mano; somma automaticamente le quantità (500 g + 1 kg → 1.5 kg); categorie ordinabili nell'ordine del tuo supermercato; condivisibile con il partner in tempo reale (codice famiglia)
- **Congelatore** — inventario di cosa c'è in freezer, per categorie e date
- **Modalità cucina** — un passo alla volta a schermo intero, schermo sempre acceso, timer avviabili direttamente dai tempi scritti nei passi
- **Bimby / Cookidoo** — esporta qualsiasi ricetta come testo pronto da incollare nelle *Ricette create* di Cookidoo, o condividila su WhatsApp

## Stack

- Vanilla HTML/CSS/JS — un solo `index.html`, nessuna build
- Firebase Realtime Database + Google Auth
- PWA installabile (iPhone e Android), dark mode automatica

## Sicurezza e backup

Vedi [SECURITY.md](SECURITY.md): regole del database con allowlist di famiglia
(`database.rules.json`) e backup notturno automatico del database via GitHub Actions.

## Note

- Le ricette taggate **Mamma** sono ricette di famiglia; quelle **Web** vengono da internet
- Planner, spesa, congelatore e preferiti sono privati: li vede solo il tuo account
