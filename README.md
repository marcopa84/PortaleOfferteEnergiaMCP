# Portale Offerte MCP

Server [MCP](https://modelcontextprotocol.io) che permette a Claude, ChatGPT e altri client MCP di consultare le
offerte di **luce e gas** del mercato italiano pubblicate negli open data del
[Portale Offerte](https://www.ilportaleofferte.it): cercarle per zona, tipo e venditore, leggerne i dettagli e
confrontarne il costo annuo stimato.

> **Progetto indipendente**, non affiliato né approvato da ARERA, Acquirente Unico o dal Portale Offerte.
> Le stime **non sono la bolletta** e **non sono una consulenza**: prima di sottoscrivere un'offerta verifica
> sempre sul Portale Offerte e sul sito del venditore. Leggi le [avvertenze](#avvertenze-legali-e-note-duso).

*English: an MCP server for the Italian electricity and gas offers published as open data by ARERA's Portale
Offerte. Unofficial and unaffiliated; estimates cover only the supplier-dependent part of the bill and are not
advice. The documentation is in Italian because the data only concerns the Italian market.*

## Strumenti

| Tool | Cosa fa |
|---|---|
| `cerca_offerte` | Filtra per luce/gas/dual, cliente, comune o regione, fisso/variabile, mercato libero/PLACET, venditore, testo. Con `consumo_annuo` ordina per costo stimato. Le versioni della stessa offerta (es. edizioni mensili) sono raggruppate in una riga |
| `dettaglio_offerta` | Prezzi per fascia, indice, sconti, condizioni contrattuali, zone e contatti, con i codici già tradotti |
| `stima_costo` | Confronta fino a 20 offerte luce oppure gas con il dettaglio delle voci; accetta la ripartizione F1/F2/F3 del cliente. Le dual si stimano tramite le offerte luce e gas collegate |
| `elenco_venditori` | Venditori con il numero di offerte per commodity |
| `indici_prezzi` | Storico mensile di PUN, PSV, PE, CMEM, Psbil |
| `parametri_regolati` | Corrispettivi regolati pubblicati con le offerte: oneri, trasporto, PCV, QVD, IVA, perdite di rete, accise della luce (quelle del gas non sono negli open data). Il file ufficiale non riporta le unità di misura |
| `stato_dati` | Data dei dati, conteggi, cache; con `aggiorna=true` riscarica |
| `controlla_aggiornamenti` | Dice all'assistente se su GitHub c'è una versione più recente (una volta per conversazione) |

Ogni risultato riporta la fonte, la data di pubblicazione dei dati e il link alla pagina dell'offerta del
venditore.

## Installazione

Serve solo [uv](https://docs.astral.sh/uv/getting-started/installation/) (scarica da sé Python e le
dipendenze). Non c'è nulla da clonare o compilare: al primo avvio il client scarica tutto in pochi secondi,
quindi basta registrare il server e riavviare il client.

### Fallo installare a Claude

Incolla questo in Claude Code (o in Claude Desktop con accesso ai file): farà la configurazione chiedendo prima
di toccare qualsiasi file.

```text
Installa questo server MCP e verifica che funzioni: https://github.com/marcopa84/PortaleOfferteEnergiaMCP
Segui INSTALL_FOR_AI.md di quel repository.
```

Se cloni il repository e apri Claude Code al suo interno hai anche tre comandi: `/install` (configurazione),
`/doctor` (diagnosi dei problemi), `/offerte <richiesta>` (ricerca in linguaggio naturale).

Oppure a mano:

### Claude Code

```bash
claude mcp add portale-offerte -- uvx --from git+https://github.com/marcopa84/PortaleOfferteEnergiaMCP portale-offerte-mcp
```

### Claude Desktop

Settings → Developer → Edit Config (Impostazioni → Sviluppatore), poi aggiungi:

```json
{
  "mcpServers": {
    "portale-offerte": {
      "command": "/usr/local/bin/uvx",
      "args": ["--from", "git+https://github.com/marcopa84/PortaleOfferteEnergiaMCP", "portale-offerte-mcp"]
    }
  }
}
```

Sostituisci `/usr/local/bin/uvx` con il risultato di `which uvx` (Claude Desktop non vede il PATH della shell)
e mantieni le altre chiavi già presenti nel file.

Poi **chiudi completamente Claude Desktop** (⌘Q su macOS, icona nell'area di notifica → Esci su Windows; chiudere
la finestra non basta), riaprilo, apri una nuova chat e chiedi: *"Offerte luce a prezzo fisso a Bologna per
2.700 kWh l'anno"*. Se gli strumenti non compaiono, controlla `~/Library/Logs/Claude/mcp-server-portale-offerte.log`.

### ChatGPT (e altri client remoti)

ChatGPT si collega a server su internet: avvia il trasporto HTTP ed esponilo con un tunnel. Serve un piano
ChatGPT con connettori personalizzati / Developer Mode (verifica i requisiti nella documentazione di OpenAI).

```bash
# terminale 1
uvx --from git+https://github.com/marcopa84/PortaleOfferteEnergiaMCP portale-offerte-mcp --transport http --port 8000 --allow-any-host
# terminale 2 (va bene qualsiasi tunnel; questo non richiede account)
cloudflared tunnel --url http://localhost:8000
```

In ChatGPT: Impostazioni → Connettori → Avanzate → Developer mode → aggiungi un connettore con
`https://<il-tuo-tunnel>.trycloudflare.com/mcp`, autenticazione *nessuna*.

⚠️ Questo server non ha autenticazione: chiunque conosca l'indirizzo del tunnel può usarlo e far scaricare dati
al tuo computer. Chiudi il tunnel quando hai finito e non lasciarlo attivo incustodito. Se l'hostname è stabile,
usa `--public-host <hostname-del-tunnel>` invece di `--allow-any-host`.

### Da un clone

```bash
git clone https://github.com/marcopa84/PortaleOfferteEnergiaMCP && cd PortaleOfferteEnergiaMCP
uv sync
uv run portale-offerte-mcp          # stdio
uv run pytest                       # test (offline)
uv run pytest -m live               # verifica sugli open data reali
```

## Configurazione (variabili d'ambiente, tutte facoltative)

| Variabile | Predefinito | Significato |
|---|---|---|
| `PORTALE_OFFERTE_CACHE` | `~/.cache/portale-offerte-mcp` | Cartella della cache |
| `PORTALE_OFFERTE_GIORNI_STORICO` | `365` | Giorni di storico da conservare (`0` = senza limite) |
| `PORTALE_OFFERTE_UPDATE_CHECK` | `1` | `0` disattiva il controllo degli aggiornamenti su GitHub |

## Aggiornamenti

Installato con `uvx --from git+...`, il server prende l'ultimo commit **a ogni avvio**. Per aggiornare basta
chiudere completamente il client e riaprirlo (Claude Desktop: ⌘Q / area di notifica → Esci). Finché l'app
resta aperta gira la versione precedente; l'assistente chiama `controlla_aggiornamenti` una volta per
conversazione e avvisa quando un riavvio porterebbe una versione nuova.

## Come funziona

```
client MCP ──► tool (server.py) ──► Archivio in memoria (ricerca, comuni ISTAT, indici)
                                        ├─ sorgenti.py  scarica la pagina Open Data e i file del giorno
                                        ├─ lettura.py   XML mercato libero + CSV PLACET → modello comune
                                        └─ costi.py     stima della parte vendita
```

Al primo uso il server legge la pagina [Open Data](https://www.ilportaleofferte.it/portaleOfferte/it/open-data.page)
del portale, scarica i file del giorno (circa 40 MB, pochi secondi) e li salva compressi (circa 1,7 MB al
giorno) nella cache locale. Poi ricontrolla al massimo ogni 30 minuti e riscarica solo quando il portale
pubblica una nuova giornata. Lo storico si accumula nella cache, perché sul portale resta disponibile solo per
pochi giorni.

Non esiste un'API ufficiale: se il portale cambia la pagina Open Data o il formato dei file il server può
smettere di funzionare. La CI settimanale esegue un controllo sui dati reali per accorgersene presto.

## Cosa stima (e cosa no)

`costo_vendita_anno` è la **parte vendita** della spesa, cioè quello che cambia tra un'offerta e l'altra:
componenti del venditore, indice per le variabili, dispacciamento scelto dal venditore, componenti regolate
incluse nell'offerta, sconti non condizionati del primo anno. Segue le
[regole di calcolo della spesa del SII](https://www.ilportaleofferte.it/portaleOfferte/resources/cms/documents/6bc502553cb0ea45958840b2de20078d.pdf)
dove i dati lo consentono.

Non è la bolletta e non coincide con la "spesa annua stimata" del Portale:

- **esclusi** trasporto e gestione del contatore, oneri di sistema, accise e IVA, uguali per tutte le offerte a
  parità di cliente;
- per le **variabili** si usa il valore storico dell'indice (ultimo mese o media 12 mesi), non le quotazioni
  forward usate dal Portale, che non sono open data: la stima segue l'andamento passato, non quello futuro.
  `stima_costo` riporta il costo con entrambi i riferimenti e le risposte avvisano quando l'ultimo mese si
  discosta di oltre il 20% dalla media;
- il **TTF** non è tra i prezzi storici pubblicati: le offerte indicizzate al TTF risultano "stima incompleta";
- gli sconti **condizionati** (fattura elettronica, domiciliazione…) non sono conteggiati, come fa il Portale;
- profilo per fasce standard: domestico F1 33%, F2 31%, F3 36%; altri usi 44%, 24%, 32%.

Ogni stima riporta voci, dettaglio e note sulle approssimazioni applicate.

## Limiti noti

- Il nome del venditore è presente solo nel CSV PLACET: per i venditori senza offerte PLACET (circa un terzo)
  si mostrano partita IVA e sito.
- Lo stesso codice offerta compare talvolta con venditori diversi: `dettaglio_offerta` li riporta tutti e
  accetta la `piva` per sceglierne uno.
- Non c'è la ricerca per CAP: si indica il comune (nome, "Nome (SIGLA)" o codice ISTAT). Sono accettate le
  forme d'uso ("Reggio Calabria" per "Reggio di Calabria") e per i nomi sbagliati vengono proposti i più simili.
- Il filtro `residente` incide poco: poche offerte dichiarano se sono riservate a residenti o non residenti.

## Avvertenze legali e note d'uso

Questa sezione non è una consulenza legale. Punti da conoscere prima di usare il progetto:

- **Nessuna affiliazione.** Progetto personale e indipendente, non affiliato, sponsorizzato o approvato da
  ARERA, Acquirente Unico S.p.A., dal Portale Offerte, dal Gestore del SII, da ISTAT o da alcun venditore di
  energia. "Portale Offerte", "AU" e "ARERA" sono marchi dei rispettivi titolari e qui sono citati solo per
  indicare la fonte dei dati; il progetto non ne usa i loghi.
- **Fonte e licenza dei dati.** Secondo le
  [informazioni legali](https://www.ilportaleofferte.it/portaleOfferte/it/informazioni-legali.page) del
  portale, i dati della sezione Open Data sono a uso libero, citando la fonte "Portale Offerte"; il resto del
  sito è consentito solo per uso personale. Il server usa **solo** la pagina e i file della sezione Open Data,
  non le API interne né le altre pagine del sito. L'elenco dei comuni viene da ISTAT
  ([CC BY 4.0](https://www.istat.it/note-legali/)). Le tabelle di decodifica dei codici sono ricavate dalla
  specifica tecnica pubblica del SII "Trasmissione Offerte Mercato Retail".
- **Il repository non contiene i dati.** Nessun file del portale è incluso o ridistribuito qui: ogni
  installazione scarica i dati direttamente dal portale sul computer di chi la usa.
- **Accuratezza.** Le offerte sono comunicate dai venditori, che ne sono gli unici responsabili; Acquirente
  Unico non ne garantisce completezza ed esattezza. Questo software può a sua volta contenere errori di lettura,
  di decodifica o di calcolo, e i dati possono non essere aggiornati: un'offerta può essere scaduta, cambiata o
  non disponibile nella tua zona.
- **Non è una consulenza.** Il progetto fornisce informazioni, non raccomandazioni né consulenza energetica,
  economica o finanziaria, e non sostituisce il comparatore ufficiale del Portale Offerte. Prima di
  sottoscrivere leggi la scheda sintetica e le condizioni contrattuali del venditore.
- **Uso rispettoso del servizio.** Il server scarica i file una volta al giorno e controlla la pagina Open
  Data al massimo ogni 30 minuti. Non modificarlo per interrogare il portale più spesso o in massa e non
  esporlo come servizio pubblico senza limiti.
- **Privacy.** Il server non raccoglie dati personali e non ha telemetria. Si collega solo a
  `www.ilportaleofferte.it`, `www.istat.it` e `api.github.com` (controllo aggiornamenti, disattivabile). I
  consumi che indichi restano sul tuo computer, ma fanno parte della conversazione con l'assistente AI che usi,
  e sono quindi trattati dal suo fornitore secondo le sue condizioni.
- **Nessuna garanzia.** Il software è fornito "così com'è", senza garanzie di alcun tipo, come previsto dalla
  [licenza MIT](LICENSE). L'autore non risponde di decisioni prese, contratti sottoscritti o danni derivanti
  dall'uso del software o dei dati.

## Contribuire

`INSTALL_FOR_AI.md` è scritto per gli assistenti AI: tienilo allineato quando cambiano i passi di
installazione. Segnalazioni e PR sono benvenute, soprattutto se il portale cambia formato o se una stima non
torna con le regole ufficiali (allega il codice offerta e la data dei dati).

## Licenza

Codice: MIT (vedi [LICENSE](LICENSE)). I dati scaricati restano soggetti alle condizioni delle rispettive fonti.
