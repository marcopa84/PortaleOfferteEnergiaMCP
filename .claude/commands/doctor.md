---
description: Diagnostica perché il server MCP Portale Offerte non funziona
---

Diagnostica l'installazione di portale-offerte-mcp. Esegui questi controlli, riporta ciascuno come OK/KO e
poi proponi le correzioni (applicale solo dopo il consenso dell'utente):

1. `uv --version` e percorso assoluto di `uvx`.
2. `claude mcp list`: `portale-offerte` è presente e connesso? (Salta se manca la CLI `claude`.)
3. Se l'utente usa Claude Desktop: leggi la sua configurazione (percorso in `INSTALL_FOR_AI.md`) e controlla
   la voce `portale-offerte`: JSON valido, percorso assoluto di `uvx`, argomenti corretti.
4. Esegui `uvx --refresh --from git+https://github.com/marcopa84/PortaleOfferteEnergiaMCP portale-offerte-mcp --version`.
5. Prova il tool MCP `stato_dati` e poi `cerca_offerte` (luce, comune "Milano") e leggi l'eventuale errore.
6. Claude Desktop: leggi il log del server (`~/Library/Logs/Claude/mcp-server-portale-offerte.log` su macOS,
   `%APPDATA%\Claude\logs\mcp-server-portale-offerte.log` su Windows) e chiedi se l'app è stata chiusa del
   tutto (⌘Q / area di notifica → Esci) dopo la modifica della configurazione.

Se stai girando in una sandbox cloud e non sul computer dell'utente, dillo: lì gli errori di rete non
riguardano la sua installazione.

Usa la tabella di risoluzione problemi in `INSTALL_FOR_AI.md` per interpretare gli errori.
