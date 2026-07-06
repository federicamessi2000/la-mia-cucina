# Sicurezza — La Mia Cucina

## 1. Regole del database (IMPORTANTE — da applicare a mano)

Oggi chiunque acceda con un qualsiasi account Google può modificare o **cancellare tutte le ricette**
(la app è pubblica su GitHub Pages, quindi chiunque può trovarla). Il file `database.rules.json`
in questo repo limita lettura e scrittura ai soli account di famiglia.

**Come applicarle** (serve l'account Firebase di Federica, ~2 minuti):

1. Vai su [console.firebase.google.com](https://console.firebase.google.com) → progetto **la-mia-cucina-48a48**
2. Realtime Database → scheda **Regole**
3. Incolla il contenuto di `database.rules.json` e premi **Pubblica**

**Per aggiungere una persona** (es. la mamma): aggiungi il suo indirizzo Gmail in *tutte* le
condizioni `auth.token.email === '...'` del file (sono 3 blocchi: recipes read, recipes write,
families) e ripubblica. Poi falla accedere alla app col suo account Google.

Nota: `users/$uid` è già limitato al proprietario — planner, spesa privata, congelatore e
preferiti restano visibili solo all'account che li ha creati.

## 2. Backup automatico

Il workflow `.github/workflows/backup.yml` scarica ogni notte l'intero database e lo carica
in un **repository privato** di backup. Per attivarlo:

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
