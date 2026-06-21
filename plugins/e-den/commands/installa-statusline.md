---
description: Installa/aggiorna la status line di Claude Code aggiungendo info progetto (nome, tipo, branch)
allowed-tools: [Bash, Read]
model: sonnet
---

# Installa Status Line e-den

Estende la status line esistente dell'utente aggiungendo informazioni sul progetto corrente:
nome (in giallo), tipo (app/pkg) e branch hg/git (in ciano).

## Procedura

Esegui questi comandi bash nell'ordine indicato. NON usare Edit/Write su settings.json,
usa solo i comandi bash indicati.

### 1. Copia lo script

Il file sorgente è nel plugin. Trovalo e copialo:

```bash
mkdir -p ~/.claude/scripts
cp "$(find ~/.claude/plugins -name 'eden-statusline.sh' -type f 2>/dev/null | head -1)" ~/.claude/scripts/eden-statusline.sh
chmod +x ~/.claude/scripts/eden-statusline.sh
```

Verifica:

```bash
test -x ~/.claude/scripts/eden-statusline.sh && echo "OK: script copiato" || echo "ERRORE: script non trovato"
```

Se ERRORE, ferma tutto e informa l'utente.

### 2. Aggiorna settings.json

Leggi `~/.claude/settings.json` con il tool Read.

Il suffisso da appendere al comando della statusLine è esattamente questo (un frammento bash):

```
; eden_extra=$(~/.claude/scripts/eden-statusline.sh); [ -n "$eden_extra" ] && printf ' | %s' "$eden_extra"; printf '\n'
```

Controlla il campo `statusLine.command` nel JSON:

- Se **contiene già** `eden-statusline.sh`: lo script è già installato.
  Informa l'utente: "Status line già configurata, aggiornato solo lo script."
  Non modificare settings.json.

- Se **esiste** `statusLine.command` ma **non contiene** `eden-statusline.sh`:
  Usa `jq` per appendere il suffisso al comando esistente:

  ```bash
  jq '.statusLine.command += "; eden_extra=$(~/.claude/scripts/eden-statusline.sh); [ -n \"$eden_extra\" ] && printf '"'"' | %s'"'"' \"$eden_extra\"; printf '"'"'\\n'"'"'"' ~/.claude/settings.json > /tmp/settings_new.json && mv /tmp/settings_new.json ~/.claude/settings.json
  ```

- Se **non esiste** `statusLine`:
  Usa `jq` per aggiungerlo:

  ```bash
  jq '. + {"statusLine": {"type": "command", "command": "cat > /dev/null; eden_extra=$(~/.claude/scripts/eden-statusline.sh); [ -n \"$eden_extra\" ] && printf '"'"'%s'"'"' \"$eden_extra\"; printf '"'"'\\n'"'"'"}}' ~/.claude/settings.json > /tmp/settings_new.json && mv /tmp/settings_new.json ~/.claude/settings.json
  ```

**IMPORTANTE**: Non sovrascrivere la statusLine esistente. L'output dello script e-den deve essere **aggiunto in coda** all'output del comando già configurato.

### 3. Verifica

```bash
cat ~/.claude/scripts/eden-statusline.sh
```

```bash
jq '.statusLine' ~/.claude/settings.json
```

Mostra entrambi gli output all'utente e suggerisci di riavviare Claude Code.
