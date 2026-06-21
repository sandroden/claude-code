# e-den Marketplace

Raccolta di plugin Claude Code di Alessandro Dentella (e-den): skill e comandi per lo
sviluppo quotidiano e per l'integrazione con Brainflow.

**Owner**: Alessandro Dentella

---

## Installazione

Aggiungi il marketplace una sola volta, poi installa i plugin che ti servono:

```
/plugin marketplace add sandroden/claude-code
/plugin install e-den@e-den-marketplace
/plugin install brainflow@e-den-marketplace
```

Riavvia/riconnetti Claude Code dopo l'installazione.

> `sandroden/claude-code` è il repo GitHub di questo marketplace; in alternativa puoi passare
> il percorso locale del clone a `/plugin marketplace add`.

---

## Plugin disponibili

| Plugin | Versione | Descrizione | Documentazione |
|--------|----------|-------------|----------------|
| [e-den](plugins/e-den/) | 1.1.1 | Skill e comandi di uso quotidiano (compare-words, scaffolding Django/Quasar, status line) | [README](plugins/e-den/README.md) |
| [brainflow](plugins/brainflow/) | 1.0.0 | Importa programmi di corso in Brainflow come Flow (MCP remoto + skill) | [README](plugins/brainflow/README.md) |

---

## e-den

Skill e comandi di uso quotidiano.

### Comandi

| Comando | Descrizione | Docs |
|---------|-------------|------|
| `/installa-statusline` | Estende la status line con info progetto (nome, tipo, branch) | [docs](plugins/e-den/README.md#installa-statusline) |

### Skill

| Skill | Descrizione | Docs |
|-------|-------------|------|
| `compare-words` | Confronta 2-3 termini inglesi (significato, registro, contesto) | [README](plugins/e-den/README.md#contenuto-del-plugin) |
| `django-startproject` | Scaffold di un nuovo progetto backend Django | [README](plugins/e-den/README.md#contenuto-del-plugin) |
| `quasar-startproject` | Scaffold di un nuovo frontend Quasar (Vue 3 + TypeScript) | [README](plugins/e-den/README.md#contenuto-del-plugin) |

---

## brainflow

Importa programmi di corso (PDF, syllabus, testo) in **Brainflow** come *Flow*, via server
MCP remoto. Nessun codice da installare in locale: serve solo un token e (opzionale) l'URL
dell'istanza.

Vedi il [README del plugin](plugins/brainflow/README.md) per setup token, variabili
d'ambiente e troubleshooting.
