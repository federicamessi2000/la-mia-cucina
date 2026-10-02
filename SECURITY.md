# Sicurezza — La Mia Cucina

## 1. Regole del database — ✅ AGGIORNATE (2026-09-30)

Dal 2026-09-30 l'app è aperta a **qualsiasi account Google** (prima: solo i 4 account di
famiglia). Regole pubblicate dalla Console; il file sorgente resta `database.rules.json`.

| Dato | Chi legge | Chi scrive |
|---|---|---|
| Ricette condivise (`recipes`) | chiunque abbia fatto l'accesso | chi le crea (a suo nome, `ownerUid`); modifica/elimina solo l'autore o un account di famiglia |
| Ricette private, planner, spesa privata, congelatore, preferiti (`users/<uid>`) | solo il proprietario | solo il proprietario |
| Spesa condivisa (`families/<codice>`) | solo i membri | i membri; chi conosce il codice può unirsi |
| Segnalazioni (`bugReports`) | solo l'account di Federica (gmail) | chiunque può crearne una a suo nome; risolve/elimina solo Federica |

Account di famiglia (possono modificare anche le ricette senza autore, es. quelle di mamma):
Federica, Daniele, Alessandro, Maria Grazia. Le regole validano anche chiave, nome (max 200
caratteri), fonte (`mamma`/`internet`/`libro`) e la lunghezza di procedimento e note.

**Per aggiungere un account di famiglia**: aggiungi l'email nella condizione `.write` di
`recipes/$recipeId` in `database.rules.json` e in `ADMIN_EMAILS` in `index.html`, poi
pubblica (Console → Realtime Database → Regole → Pubblica, o `firebase deploy --only database`).

## 2. Backup automatico — ✅ ATTIVO (2026-07-07)

Backup notturno **attivo** sul server di casa di Daniele (cron alle 03:15, ultimi 60 giorni,
verifica anti-anomalia sul numero di ricette). Primo backup completato: 812 ricette.

In più esiste il workflow `.github/workflows/backup.yml` (backup ridondante su GitHub),
opzionale. Per attivarlo:

1. Crea un repo **privato** `federicamessi2000/la-mia-cucina-backup`
2. Firebase Console → Impostazioni progetto → Account di servizio → **Genera nuova chiave privata**
3. Nel repo la-mia-cucina: Settings → Secrets and variables → Actions → New secret:
   - `FIREBASE_SERVICE_ACCOUNT`: incolla il JSON della chiave scaricata
   - `BACKUP_REPO_TOKEN`: un fine-grained PAT con permesso *Contents: read/write* sul repo di backup
4. Il backup parte da solo ogni notte alle 03:00 (oppure lancialo a mano da Actions → Backup)

## 2b. Traduzioni automatiche delle ricette

Il workflow `.github/workflows/translate.yml` gira il 1° di ogni mese (o a mano da Actions) e
traduce con Gemini le ricette condivise nuove o modificate (`.github/scripts/translate_recipes.py`).

- Usa due secret del repo: `FIREBASE_SERVICE_ACCOUNT` (lo stesso JSON del backup) e
  `GEMINI_API_KEY` (Google AI Studio → API key). Senza i secret il workflow salta senza errore.
- Il database applica le regole come utente `translator-bot`: legge le ricette condivise
  (non quelle "Solo per me") e può scrivere **solo** `recipeTr` e `recipeTrIdx`.
- Testi delle ricette inviati a Gemini: sul piano gratuito Google può usarli per migliorare i suoi prodotti.
- GitHub sospende i workflow programmati di un repo pubblico dopo 60 giorni senza commit
  (manda un'email): si riattivano da Actions → il workflow → *Enable workflow*.

## 3. Dati personali nel repo

- `firebase_import.py` conteneva un token di sessione Firebase di Federica (scaduto — durano
  1 ora — ma con dentro email e user-id). Il file è stato **rimosso** insieme agli strumenti
  di import una tantum (`import-mamma.html`, `mamma ricette/`, `parse_ingredients.py`) che
  pubblicavano tutte le ricette di famiglia sulla pagina GitHub Pages.
- I file restano però **nella storia git** del repo pubblico. Due opzioni:
  - **Consigliata**: rendere privato il repo non è possibile senza perdere GitHub Pages (piano
    free) → riscrivere la storia con `git filter-repo` e fare force-push, oppure
  - Accettare il rischio residuo: il token è scaduto e le ricette non sono dati sensibili.
