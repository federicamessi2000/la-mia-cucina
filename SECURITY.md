# Sicurezza — La Mia Cucina

## 1. Regole del database — ✅ FATTO (2026-07-07)

Le regole con allowlist famiglia sono state **pubblicate** il 2026-07-07 (deploy via
`firebase deploy --only database` dall'account di Daniele, ora membro del progetto).
Le regole precedenti (qualsiasi account Google poteva leggere e scrivere tutto) sono
salvate in locale da Daniele. Il file sorgente resta `database.rules.json`.

Account autorizzati: Federica, Daniele, Alessandro, Maria Grazia. Chiunque altro può
aprire l'app ma non vede né tocca nulla.

**Per aggiungere una persona**: aggiungi il suo indirizzo Gmail in *tutte* le condizioni
`auth.token.email === '...'` di `database.rules.json` (4 blocchi: recipes read/write,
families read/write), poi `firebase deploy --only database` dalla cartella del repo
(o incolla il file in Console → Realtime Database → Regole → Pubblica).

Nota: `users/$uid` è già limitato al proprietario — planner, spesa privata, congelatore e
preferiti restano visibili solo all'account che li ha creati.

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

## 3. Dati personali nel repo

- `firebase_import.py` conteneva un token di sessione Firebase di Federica (scaduto — durano
  1 ora — ma con dentro email e user-id). Il file è stato **rimosso** insieme agli strumenti
  di import una tantum (`import-mamma.html`, `mamma ricette/`, `parse_ingredients.py`) che
  pubblicavano tutte le ricette di famiglia sulla pagina GitHub Pages.
- I file restano però **nella storia git** del repo pubblico. Due opzioni:
  - **Consigliata**: rendere privato il repo non è possibile senza perdere GitHub Pages (piano
    free) → riscrivere la storia con `git filter-repo` e fare force-push, oppure
  - Accettare il rischio residuo: il token è scaduto e le ricette non sono dati sensibili.
