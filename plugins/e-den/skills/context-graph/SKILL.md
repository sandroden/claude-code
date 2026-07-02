---
name: context-graph
description: "SOLO SU RICHIESTA ESPLICITA (comando /context-graph o \"usa context-graph\"). NON attivare automaticamente. Analizza i transcript .jsonl di un progetto Claude Code e genera un report HTML interattivo su crescita del contesto, consumo totale di token (integrale) e stima costi per modello."
---

# context-graph

Genera un report HTML interattivo che, a partire dai transcript reali (`.jsonl`)
di un progetto Claude Code, mostra tre grandezze distinte e spesso confuse:

1. **Contesto** di ogni turno (token nella finestra).
2. **Consumo totale** = integrale dei token consumati man mano (area sotto la curva).
3. **Costo API** stimato per modello (Opus/Sonnet/Haiku) — che **non** è
   proporzionale ai token, perché il `cache_read` costa ~1/10.

Distingue i **prompt utente** reali (gli "Enter") dai **rimbalzi di protocollo**
(tool call → tool result → nuova chiamata), che l'utente non comanda ma che
dominano il consumo.

## Quando usarla

**Solo su invocazione esplicita** (l'utente scrive `/context-graph`, "usa la skill
context-graph", "fammi il grafico del contesto di questo progetto", ecc.).
Non attivarla in automatico su altri argomenti.

## Procedura

Lo script è `scripts/analizza_contesto.py` (solo stdlib, ha `-h`). Percorso completo:
`${CLAUDE_PLUGIN_ROOT}/skills/context-graph/scripts/analizza_contesto.py`
(se la var non è disponibile, è la cartella di questo file + `scripts/`).

### 1. Individua il progetto

- **Default = progetto corrente**: lo script codifica la working dir in
  `~/.claude/projects/<enc>`. Passa `--cwd <path>` col percorso reale del
  progetto (NON la cwd di questa sessione, che di solito è un'altra cartella),
  oppure `--project <nome>` (accetta anche una sottostringa / il suffisso del
  nome, es. `desica-teams`), oppure `--dir <cartella-transcript>`.
- Se l'utente non specifica quale progetto, chiediglielo.

### 2. Elenca le sessioni e proponi la scelta

Esegui **sempre** prima `--list` per vedere le sessioni ordinate per lunghezza:

```bash
python3 <script> --project <nome> --list
```

Mostra all'utente le prime righe (turni, prompt, picco, consumo, primo prompt) e
**proponi una scelta** con `AskUserQuestion`, tipicamente:

- **Le 6 più lunghe** (default consigliato — buon compromesso di leggibilità).
- **Solo la più lunga** (analisi mono-sessione).
- **Seleziona sessioni specifiche** (l'utente indica gli id a 8 caratteri).
- **Tutte** (se sono poche).

La sessione più lunga tra quelle scelte diventa la "Sessione A" in evidenza
(grafici 2/3/4, card, riflessioni).

### 3. Genera il report

```bash
# le N più lunghe
python3 <script> --project <nome> --top 6 --out <path>/context-graph.html
# sessioni scelte a mano
python3 <script> --project <nome> --sessions 65ab0ff1 641bfc8f --out <out>
```

Opzioni utili: `--name "nome leggibile"` (mostrato nel report),
`--min-turns N` (esclude sessioni troppo corte, default 2).
Salva l'HTML dove chiede l'utente (o nella cwd del progetto).

Lo script stampa il percorso assoluto e l'URL `file://` del report: **riporta
all'utente quel link** (`file://…`) così può aprirlo con un click.

### 4. Valida graficamente

Come da preferenza dell'utente, **valida sempre con screenshot** usando
`agent-browser` (i canvas Chart.js non compaiono negli screenshot *full-page*
headless: usa screenshot di viewport scrollando, non `--full`):

```bash
agent-browser --allow-file-access open "file://$(realpath <out>)"
agent-browser wait 1500
agent-browser screenshot top.png
agent-browser scroll down 1600 && agent-browser screenshot mid.png
agent-browser close
```

Verifica: 4 grafici presenti, card popolate, tabella riepilogativa, e (opzionale)
i drag sui grafici 3 e 4 via `eval` simulando i MouseEvent con `offsetX`.

## Subagenti (tool `Agent`)

I subagenti hanno **transcript separati**: `<progetto>/<session-id>/subagents/agent-*.jsonl`
(un file per invocazione, righe `isSidechain`, `usage` proprio, spesso su un
**modello diverso** — es. Haiku). Il file principale della sessione **non** contiene
il loro consumo interno: nel main compaiono solo come un turno `Agent` e come il
risultato che rientra nel contesto. Lo script li recupera e li collega al turno di
spawn per **timestamp** (chiamata `Agent` più vicina).

Il report, per la sessione in evidenza, mostra:

- **grafico 3** — barre (asse destro, colore = modello) col consumo **reale** di
  ogni subagente allo spawn; curva tratteggiata **«contesto se inlineato (stima)»**:
  controfattuale = il *footprint* del subagente (picco − baseline, il materiale
  accumulato) reso **residente** nel contesto main dallo spawn in poi e riletto ad
  ogni turno. È una **stima** del costo evitato delegando, non una misura esatta;
- **grafico 4** — curva «totale sistema» (token main + subagenti) sull'asse token;
  sull'asse costi: «costo reale (main)» e «costo se SENZA delega (stima)» — il
  divario è il risparmio della delega; il drag mostra anche il costo controfattuale
  dell'intervallo;
- **grafico 5** — pannello dedicato: una barra per subagente (lunghezza = token,
  colore = modello) col dettaglio isolato che non appare nel transcript principale;
- card (token/costo subagenti, costo controfattuale, risparmio), colonna «Subag.»
  in tabella e una riflessione con il confronto costi.

Assunzioni/limiti: mapping per timestamp; footprint come proxy del residente;
i subagenti annidati (un subagente che ne lancia un altro) non vengono ricorsi.
Se una sessione non usa subagenti, tutti questi elementi spariscono automaticamente.

Per un confronto *esatto* con/senza subagenti serve un esperimento controllato
(stesso prompt eseguito due volte, una vietando la delega): il report da solo
mostra il controfattuale **stimato**, non due run reali.

## Come è definito un "prompt utente" reale

Riga `type=="user"` con contenuto testo/stringa o immagine, **escludendo**:
`tool_result`, `isMeta`, `isSidechain`, e marker di sistema
(`[Request interrupted`, `<command-`, `<local-command`, `Caveat:`).
`usermarks` = indice del turno assistant innescato da quel prompt.

## Dati e costi

- Per turno assistant: `contesto = input + cache_read + cache_creation`;
  `consumo = contesto + output`. Integrale = somma cumulativa del consumo.
- Prezzi per token (listino gen 2026, modificabili in cima allo script, dict
  `PRICES`): Opus $5/$25, Sonnet $3/$15, Haiku $1/$5 per Mtok; cache_read ≈ 0,1×
  input, cache_creation ≈ 1,25× input (TTL 5 min). Stime **qualitative**.
- Tutto locale, nessun invio esterno.
