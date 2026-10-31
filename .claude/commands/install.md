---
description: Installa e verifica il server MCP Portale Offerte nel client Claude dell'utente
argument-hint: "[claude-code | claude-desktop]"
---

Installa il server portale-offerte-mcp per l'utente. Leggi `INSTALL_FOR_AI.md` in questo repository e
seguilo alla lettera. Client di destinazione: $ARGUMENTS (se vuoto, chiedi se usa Claude Code o Claude Desktop).

Non saltare il warm-up (passo 2): il primo avvio scarica le dipendenze.
Per Claude Desktop, chiudi dicendo all'utente di uscire completamente dall'app (⌘Q / area di notifica → Esci)
e riaprirla, con il messaggio del passo 3.4 della guida; dai tutte le istruzioni prima che esca, perché
uscire può chiudere questa conversazione.

Regole: spiega brevemente ogni passo, chiedi prima di modificare qualsiasi file di configurazione, unisci il
JSON invece di sovrascriverlo, verifica alla fine con una vera chiamata a un tool e riporta cosa hai cambiato.
