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

Le cartelle di Claude Code dipendono da `CLAUDE_CONFIG_DIR` (default `~/.claude`, ma una
sandbox o un ambiente di corso può usarne un'altra). Risolvi la dir una volta e usala ovunque,
così il comando funziona sia con la config di default sia con `CLAUDE_CONFIG_DIR` impostata:

```bash
DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
mkdir -p "$DIR/scripts"
cp "$(find "$DIR/plugins" -name 'eden-statusline.sh' -type f 2>/dev/null | head -1)" "$DIR/scripts/eden-statusline.sh"
chmod +x "$DIR/scripts/eden-statusline.sh"
```

Verifica:

```bash
DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
test -x "$DIR/scripts/eden-statusline.sh" && echo "OK: script copiato" || echo "ERRORE: script non trovato"
```

Se ERRORE, ferma tutto e informa l'utente.

### 2. Aggiorna settings.json

Leggi il file `settings.json` nella config dir attiva (`${CLAUDE_CONFIG_DIR:-~/.claude}/settings.json`)
con il tool Read.

Claude Code passa il JSON di stato alla statusLine **via stdin**, e stdin si può leggere
una sola volta. Lo script `eden-statusline.sh` ha bisogno di quel JSON (per modello e context
window). Perciò, quando esiste già una statusLine, NON basta appendere un frammento dopo il
comando esistente: se quel comando legge stdin (es. `input=$(cat)`), lo script e-den lo
troverebbe vuoto e perderebbe modello + context. La soluzione è **catturare stdin una volta**
(`__in=$(cat)`) e passarne una copia sia al comando esistente sia allo script e-den.

I `jq` qui sotto **bacano il path assoluto** dello script in settings.json (via `--arg s`),
così la statusLine funziona al render anche se `CLAUDE_CONFIG_DIR` non è nell'ambiente.

Controlla il campo `statusLine.command` nel JSON:

- Se **contiene già** `eden-statusline.sh`: lo script è già installato.
  Informa l'utente: "Status line già configurata, aggiornato solo lo script."
  Non modificare settings.json.

- Se **esiste** `statusLine.command` ma **non contiene** `eden-statusline.sh`:
  Usa `jq` per avvolgere il comando esistente condividendo stdin con lo script e-den:

  ```bash
  DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  jq --arg s "$DIR/scripts/eden-statusline.sh" '.statusLine.command = "__in=$(cat); printf \"%s\" \"$__in\" | { " + .statusLine.command + "; }; eden_extra=$(printf \"%s\" \"$__in\" | \($s)); [ -n \"$eden_extra\" ] && printf \" | %s\" \"$eden_extra\"; printf \"\\n\""' "$DIR/settings.json" > /tmp/settings_new.json && mv /tmp/settings_new.json "$DIR/settings.json"
  ```

- Se **non esiste** `statusLine`:
  Usa `jq` per aggiungerlo (lo script legge stdin direttamente, niente `cat > /dev/null`):

  ```bash
  DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  jq --arg s "$DIR/scripts/eden-statusline.sh" '. + {"statusLine": {"type": "command", "command": "eden_extra=$(\($s)); [ -n \"$eden_extra\" ] && printf \"%s\" \"$eden_extra\"; printf \"\\n\""}}' "$DIR/settings.json" > /tmp/settings_new.json && mv /tmp/settings_new.json "$DIR/settings.json"
  ```

**IMPORTANTE**: Non sovrascrivere la statusLine esistente. L'output dello script e-den deve essere **aggiunto in coda** all'output del comando già configurato, e il JSON di stdin deve arrivare a entrambi.

### 3. Verifica

```bash
DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
cat "$DIR/scripts/eden-statusline.sh"
```

```bash
DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
jq '.statusLine' "$DIR/settings.json"
```

Mostra entrambi gli output all'utente e suggerisci di riavviare Claude Code.
