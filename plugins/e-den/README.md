# e-den

Plugin Claude Code con skill e comandi di uso quotidiano: comparazione di termini
inglesi, scaffolding di progetti Django/Quasar e configurazione della status line.

**Versione**: 1.1.0
**Autore**: Alessandro Dentella

---

## Installazione

```
/plugin marketplace add sandroden/claude-code
/plugin install e-den@e-den-marketplace
```

Dopo l'installazione riavvia/riconnetti Claude Code per rendere disponibili comandi e skill.

---

## Contenuto del plugin

### Comandi (`/comando`)

| Comando | Modello | Descrizione |
|---------|---------|-------------|
| [`/installa-statusline`](#installa-statusline) | sonnet | Estende la status line con info progetto (nome, tipo, branch) |

### Skill (si attivano automaticamente)

| Skill | Descrizione |
|-------|-------------|
| `compare-words` | Confronta 2-3 termini inglesi spiegando differenze di significato, registro e contesto (analisi in italiano) |
| `django-startproject` | Scaffold di un nuovo progetto backend Django |
| `quasar-startproject` | Scaffold di un nuovo frontend Quasar (Vue 3, TypeScript, Pinia, Router, Vite, SCSS) — SPA/SSR/PWA |

---

## Quick start

### Confrontare termini inglesi

```
compare-words: affect vs effect
```

### Creare un backend Django

```
/django-startproject myproject
```

### Creare un frontend Quasar

```
/quasar-startproject myfrontend "descrizione" spa
```

### Installare la status line

```
/installa-statusline
```

---

## installa-statusline

**Invocazione**: `/installa-statusline`
**Strumenti**: Bash, Read
**Sorgente**: [`scripts/eden-statusline.sh`](scripts/eden-statusline.sh)

Estende **in coda** la status line già configurata (senza sovrascriverla) aggiungendo,
per il progetto corrente:

- **modello** e barra colorata della **context window** (con percentuale e token usati/totali);
- **nome progetto** (giallo), letto da `pyproject.toml` o dal nome cartella;
- **tipo** `app` (se c'è `Dockerfile`/`manage.py`) o `pkg` (se c'è `pyproject.toml`);
- **branch** hg/git (ciano), con eventuale topic Mercurial.

Il comando:

1. copia `eden-statusline.sh` in `~/.claude/scripts/`;
2. appende un frammento bash al campo `statusLine.command` di `~/.claude/settings.json`
   (via `jq`, mai sovrascrivendo quello esistente);
3. mostra il risultato e invita a riavviare Claude Code.

### Configurazione

Le soglie colore della context bar sono in [`scripts/eden-statusline.conf`](scripts/eden-statusline.conf)
(copiato accanto allo script). I profili associano soglie percentuali diverse a fasce di
context size: context piccolo → soglie alte (si può riempire di più), context grande →
soglie basse (meglio cambiare sessione prima).

> **Nota**: script e percorsi usano il prefisso `eden-` per non collidere con la status line
> del plugin `thx` (`thx-statusline.sh`). Installare entrambi i plugin appenderebbe due volte
> le info di progetto: usane uno solo.

---

## Struttura file

```
e-den/
  .claude-plugin/
    plugin.json
  commands/
    installa-statusline.md
  scripts/
    eden-statusline.sh
    eden-statusline.conf
  skills/
    compare-words/SKILL.md
    django-startproject/SKILL.md
    quasar-startproject/SKILL.md
  README.md
```
