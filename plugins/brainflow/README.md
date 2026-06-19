# Plugin Brainflow

Importa programmi di corso (PDF, syllabus, testo) in **Brainflow** come *Flow*,
direttamente da Claude Code. Il plugin contiene:

- la connessione al **server MCP remoto** `brainflow` — un endpoint `/mcp`
  servito dal deployment Brainflow (niente da installare in locale);
- la **skill** `brainflow-import` — la procedura (leggi la fonte → mappa →
  preview → conferma → import).

Il server gira **dentro** Brainflow: non si scarica codice, non serve `uv`, non
parte alcun processo locale. Il plugin punta solo all'URL e porta la skill.

## Cosa serve

1. Un account su un'istanza **Brainflow** raggiungibile.
2. Un **token** API personale (vedi sotto).

## Setup — variabili d'ambiente

La connessione si configura con due variabili, esportate nell'ambiente da cui
lanci Claude Code:

```bash
# token personale (OBBLIGATORIO — niente default)
export BRAINFLOW_TOKEN="la-tua-key"

# URL dell'istanza (OPZIONALE — default https://brainflow.e-den.it)
export BRAINFLOW_API_URL="http://localhost:8000"   # solo per puntare a un'istanza locale
```

- `BRAINFLOW_TOKEN` non ha default: se manca, la config MCP non viene caricata.
- `BRAINFLOW_API_URL` ha fallback a produzione: **per testare modifiche locali**
  basta sovrascriverla (es. `http://localhost:8000`), il token resta lo stesso
  se il DB locale è una copia di quello di produzione.

L'`.mcp.json` del plugin usa queste due variabili:

```json
{
  "mcpServers": {
    "brainflow": {
      "type": "http",
      "url": "${BRAINFLOW_API_URL:-https://brainflow.e-den.it}/mcp",
      "headers": { "Authorization": "Token ${BRAINFLOW_TOKEN}" }
    }
  }
}
```

## Procurarsi il token

Sul backend Brainflow (o chiedendo a chi lo amministra):

```bash
python manage.py drf_create_token <tuo_username>
```

Il token è personale e revocabile: i permessi (visibilità dei flow,
condivisioni) sono quelli del tuo utente, applicati dall'API a ogni chiamata.

## Installazione

```
/plugin marketplace add e-den-marketplace
/plugin install brainflow@e-den-marketplace
```

Poi esporta le variabili sopra e riavvia/riconnetti. Verifica con `/mcp` che
`brainflow` risulti *connected*, quindi:

> "brainflow: importa il programma in /percorso/programma.pdf"

## I tre tool (per riferimento)

- `list_flows` → i flow visibili al tuo utente
- `preview_flow(outline)` → validazione locale, non scrive
- `import_flow(outline)` → crea il flow (atomico lato server)

## Troubleshooting

- **`/mcp` non si connette / config non caricata**: `BRAINFLOW_TOKEN` non è
  impostata (è obbligatoria), oppure l'URL non è raggiungibile.
- **401/403 dai tool**: token mancante, errato o revocato.
- **Punto a localhost ma non risponde**: l'istanza locale deve servire `/mcp`
  (codice con l'endpoint MCP nativo Django).
