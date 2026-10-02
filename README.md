# La Mia Cucina

App di ricette di famiglia, mobile-first — ricette condivise, planner dei pasti, lista della spesa intelligente, congelatore e modalità cucina passo-passo.

**Live:** https://federicamessi2000.github.io/la-mia-cucina/

---

## Funzioni

- **Ricette** — ~980 ricette (di mamma, dal web e da due libri), condivise con tutti o private del tuo account; categorie, tag, preferiti, ricerca anche senza accenti, porzioni scalabili, kcal stimate
- **Aggiungi** — form con ingredienti strutturati, categoria, "Condivisa con tutti" / "Solo per me", autocomplete dal catalogo, "importa da testo" che compila il form da una ricetta incollata
- **Planner** — pianificazione pranzo/cena per settimana o mese, privata per account, fino a 6 piatti per pasto (ognuno con le sue porzioni), extra e "fuori casa"
- **Spesa** — si popola dal planner (ricordando ciò che hai già spuntato), da ricette o a mano; somma automaticamente le quantità (500 g + 1 kg → 1.5 kg); categorie ordinabili nell'ordine del tuo supermercato; condivisibile con il partner in tempo reale (codice famiglia)
- **Congelatore** — inventario di cosa c'è in freezer, per categorie e date
- **Modalità cucina** — un passo alla volta a schermo intero, schermo sempre acceso, timer avviabili direttamente dai tempi scritti nei passi
- **Bimby / Cookidoo** — esporta qualsiasi ricetta come testo pronto da incollare nelle *Ricette create* di Cookidoo, o condividila su WhatsApp
- **Lingue** — app in italiano, inglese o tedesco (svizzero): segue la lingua del telefono e si cambia dal profilo; anche le ricette e il catalogo della spesa sono tradotti, con l'originale italiano a un tocco
- **Segnala un problema** — dal profilo: la segnalazione (descrizione + dettagli tecnici) arriva a Federica nella sezione "Segnalazioni" dell'app, senza email

## Stack

- Vanilla HTML/CSS/JS — `index.html` più `i18n.js` (i testi nelle tre lingue), nessuna build
- Firebase Realtime Database + Google Auth
- PWA installabile (iPhone e Android), dark mode automatica

## Sicurezza e backup

Vedi [SECURITY.md](SECURITY.md): chi può leggere e modificare cosa (`database.rules.json`)
e backup notturno automatico del database.

## Note

- Si accede con qualsiasi account Google
- Le ricette taggate **Mamma** sono ricette di famiglia, **Web** vengono da internet, **Libro** da un libro di cucina
- Una ricetta condivisa la modifica solo chi l'ha aggiunta (o un account di famiglia)
- Planner, spesa, congelatore, preferiti e ricette "Solo per me" sono privati: li vede solo il tuo account
