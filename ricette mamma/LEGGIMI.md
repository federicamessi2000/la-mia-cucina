# Ricette della mamma — export completo per l'app

Esportate dalle Note dell'iPhone (cartella **RICETTE** + ricette sparse nelle note),
poi **ripulite e strutturate con l'AI** per essere pronte all'uso.

## File nel pacchetto
- **`ricette_pulite.json`** ⭐ — **827 ricette STRUTTURATE** (il file da usare per l'app)
- `ricette.json` — versione "grezza" (testo originale delle note), come riferimento/fallback
- `foto_ricette/` — **814 immagini**, una sottocartella per ricetta (nome = `id`)

## Struttura di `ricette_pulite.json` (formato ricco)
```json
{
  "id": 356,                          // id univoco (= nome cartella foto)
  "titolo": "Crepes ricetta base",
  "categoria": "Dolci",               // Antipasti, Primi, Secondi, Contorni, Lievitati,
                                      // Pane e Pizza, Dolci, Colazione, Biscotti, Torte,
                                      // Conserve, Bevande, Salse e Creme, Altro
  "tag": ["vegetariano", "dolce"],    // etichette per filtri (0-5)
  "difficolta": "Facile",             // Facile | Media | Difficile
  "porzioni": "10-15 crepes",
  "tempo_preparazione_min": 45,        // intero o null
  "tempo_cottura_min": 20,             // intero o null
  "ingredienti": [
    { "quantita": "3", "unita": "", "nome": "uova medie" },
    { "quantita": "350", "unita": "ml", "nome": "latte" }
  ],
  "procedimento": [
    "In una ciotola sbattere le uova con un pizzico di sale.",
    "Aggiungere il latte e l'acqua frizzante..."
  ],
  "note": "",
  "fonte_originale": "",              // sito/autore citato nella nota, se presente
  "foto_files": ["foto_ricette/356/crepes.jpg"]   // presente solo se ci sono immagini
}
```

## Note pratiche
- **514 ricette** hanno foto, collegate in `foto_files` (percorsi relativi a questa cartella).
- Le quantità non indicate nella nota originale sono segnate **`q.b.`** (l'AI non le ha inventate).
- Negli ingredienti, suffissi tipo `- prefermento` / `- ripieno` / `- glassa` indicano la **sezione** della ricetta.
- **11 ricette** hanno tag `["da-foto"]`: il testo era dentro una foto, quindi `ingredienti`/`procedimento` sono vuoti → guarda l'immagine in `foto_files`.
- Qualche nota non-ricetta può essere finita in categoria **"Altro"** (es. consigli vari): filtrabili facilmente.
- Formati immagine: per lo più jpg/png/webp; **12 file .heic** (Apple) potrebbero richiedere conversione in jpg.

## Suggerimenti per l'import
- Usa `ricette_pulite.json` come sorgente principale; `id` come chiave primaria (coincide con la cartella foto).
- Per partire pulito puoi escludere categoria `"Altro"` o le ricette con `ingredienti` vuoti.
- I campi sono già pronti per filtri (categoria, tag, difficoltà, tempi) e per una scheda ricetta (ingredienti + procedimento).
