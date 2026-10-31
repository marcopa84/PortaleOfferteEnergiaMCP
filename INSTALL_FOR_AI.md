# Guida di installazione per assistenti AI

> Sei un assistente AI (Claude Code, Claude Desktop con accesso ai file, Cline, ecc.) e l'utente ti ha chiesto
> di installare **portale-offerte-mcp** da questo repository. Segui questi passi, spiega all'utente cosa stai
> facendo e **chiedi prima di modificare qualsiasi file di configurazione**. Non eseguire nulla che non sia
> elencato qui.

Repository: https://github.com/marcopa84/PortaleOfferteEnergiaMCP

**Controlla prima dove stai girando.** Il server deve girare sul computer dell'utente. Se sei in una sandbox
cloud (es. l'esecuzione di codice in una *chat* di Claude.ai o Claude Desktop), quella sandbox di solito non
raggiunge `www.ilportaleofferte.it`: un errore DNS o di rete lì **non** significa che il server sia guasto, e
installarlo nella sandbox non serve all'utente. In quel caso modifica la configurazione locale dell'utente
(solo se hai accesso ai suoi file) oppure guidalo sul suo computer: gli bastano `uv` installato, la voce di
configurazione del passo 3 e il riavvio del client. Il passo 2 si può saltare.

Cos'è: un server MCP (Python) che legge gli open data del Portale Offerte (ARERA / Acquirente Unico) con i tool
`cerca_offerte`, `dettaglio_offerta`, `stima_costo`, `elenco_venditori`, `indici_prezzi`, `parametri_regolati`,
`stato_dati`, `controlla_aggiornamenti`. Non servono chiavi API né clonare il repository: `uvx` lo esegue
direttamente da GitHub.

Il comando del server usato in tutti i passi è:

```
uvx --from git+https://github.com/marcopa84/PortaleOfferteEnergiaMCP portale-offerte-mcp
```

## 1. Prerequisito: uv

Esegui `uv --version`. Se manca, dillo all'utente e offriti di installarlo (non installarlo senza chiedere):

- macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`  (oppure `brew install uv`)
- Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

Poi trova il percorso assoluto di `uvx` (`which uvx` / `where uvx`): le app grafiche spesso non vedono il PATH
della shell.

## 2. Controllo rapido (facoltativo)

Se puoi eseguire comandi sul computer dell'utente, verifica che `uvx` riesca a installare il server: deve
stampare la versione in pochi secondi. Serve a scoprire un problema prima di toccare la configurazione; se non
puoi eseguire comandi lì, salta questo passo, perché il client installa il server da solo al primo avvio.

```bash
uvx --from git+https://github.com/marcopa84/PortaleOfferteEnergiaMCP portale-offerte-mcp --version
```

Alla prima chiamata a un tool il server scarica anche gli open data del giorno (circa 40 MB, qualche secondo).

## 3. Registra il server (scegli il client dell'utente)

### Claude Code

```bash
claude mcp add portale-offerte -- uvx --from git+https://github.com/marcopa84/PortaleOfferteEnergiaMCP portale-offerte-mcp
```

Aggiungi `--scope user` se l'utente lo vuole disponibile in tutti i progetti. Verifica con `claude mcp list`
(deve mostrare `portale-offerte` connesso).

### Claude Desktop

File di configurazione:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

1. Leggi il file (potrebbe non esistere: in quel caso parti da `{}`). Fanne una copia di backup accanto (`.bak`).
2. **Unisci**, non sovrascrivere mai: leggi il JSON, aggiungi questa voce sotto `mcpServers` (crea la chiave se
   manca) e lascia identiche tutte le altre chiavi e gli altri server (il file contiene anche preferenze
   dell'app):

```json
"portale-offerte": {
  "command": "<PERCORSO ASSOLUTO DI uvx>",
  "args": ["--from", "git+https://github.com/marcopa84/PortaleOfferteEnergiaMCP", "portale-offerte-mcp"]
}
```

   Usa il percorso assoluto trovato al passo 1 (es. `/usr/local/bin/uvx` o `/opt/homebrew/bin/uvx`): Claude
   Desktop non vede il PATH della shell, quindi `uvx` da solo spesso non funziona.
3. Mostra la modifica all'utente e aspetta un sì prima di salvare. Scrivi con un serializzatore JSON (non
   modificando il testo), controlla che il risultato sia valido e mantieni i permessi originali del file (su
   macOS di solito `600`).
4. **L'app va riavviata: dillo all'utente, non puoi farlo tu.** Claude Desktop legge questo file solo
   all'avvio. Chiudere la finestra non basta: l'app resta attiva in background. Se stai girando dentro Claude
   Desktop, uscire chiuderà questa conversazione, quindi dai tutte le istruzioni *prima* che l'utente esca.
   Manda all'utente questo messaggio, nella sua lingua:

   > Ora chiudi **completamente** Claude Desktop e riaprilo:
   > - macOS: menu **Claude → Esci** oppure **⌘Q** (chiudere la finestra non basta)
   > - Windows: icona di Claude nell'area di notifica → **Esci**
   >
   > Poi apri una **nuova chat** e scrivi: *"Offerte luce a prezzo fisso a Bologna per 2.700 kWh l'anno"*.
   > Se gli strumenti portale-offerte non compaiono, scrivimi e controlliamo il log.

Se non puoi modificare file (chat senza accesso ai file), dai all'utente il JSON esatto qui sopra e il
percorso del file, e accompagnalo passo passo.

### Altri client (Cursor, Cline, VS Code, ...)

Stesso comando e argomenti nella configurazione MCP del client (trasporto stdio).

### ChatGPT / client remoti

Servono il trasporto HTTP e un tunnel pubblico, senza autenticazione: leggi con l'utente la sezione "ChatGPT"
del README e assicurati che abbia capito l'avvertenza prima di iniziare.

## 4. Verifica

- Claude Code: `claude mcp list` deve mostrare `portale-offerte` connesso; poi fai una vera chiamata a
  `stato_dati`.
- Claude Desktop: la verifica si fa **dopo il riavvio, in una nuova chat**. Chiedi all'utente di confermare che
  i tool compaiono e di fare una ricerca. Una buona prova è `stato_dati` e poi `cerca_offerte` (luce, comune
  "Milano", consumo 2700).
- Riporta il risultato. Se non funziona, leggi il log del server:
  - macOS: `~/Library/Logs/Claude/mcp-server-portale-offerte.log`
  - Windows: `%APPDATA%\Claude\logs\mcp-server-portale-offerte.log`

## Aggiornamenti (dillo all'utente)

Non c'è nulla da reinstallare: `uvx` scarica l'ultimo commit da GitHub a ogni avvio del server. Per
aggiornare basta chiudere completamente il client e riaprirlo. Il server espone anche
`controlla_aggiornamenti`: il modello lo chiama una volta per conversazione e avvisa quando c'è una versione
nuova.

## 5. Risoluzione problemi

| Sintomo | Soluzione |
|---|---|
| `command not found: uvx` nel log del client | Usare il percorso assoluto di `uvx` in `command` |
| "Impossibile scaricare gli open data e nessun dato in cache" | Il portale non è raggiungibile: controllare la rete; se il problema persiste può aver cambiato indirizzi, aggiornare con `--refresh` e controllare le issue su GitHub |
| "La pagina Open Data non contiene i file: ..." | Il portale ha cambiato la pagina Open Data: aggiornare (`uvx --refresh --from ...`) e aprire una issue |
| Server non elencato dopo la modifica della configurazione | Desktop non è stato chiuso del tutto. Uscire con ⌘Q / area di notifica → Esci, riaprire, nuova chat |
| Errore DNS / di rete verso www.ilportaleofferte.it provando da una chat | Sei in una sandbox cloud, non sul computer dell'utente (vedi inizio di questo file). Installare in locale |
| Il primo avvio fallisce o va in timeout, il secondo funziona | Rete lenta al primo scaricamento delle dipendenze. Eseguire il comando del passo 2, poi riavviare il client. In Claude Code si può alzare il timeout: `MCP_TIMEOUT=120000 claude` |

## Regole per l'assistente

- Le stime riguardano solo la parte vendita: dirlo sempre, insieme al link alla pagina dell'offerta.
- Non presentare i risultati come consulenza o raccomandazione: sono informazioni da verificare sul Portale
  Offerte e sul sito del venditore prima di sottoscrivere.
- Citare la fonte "Portale Offerte"; non usare i marchi del Portale Offerte, di ARERA o di Acquirente Unico.
