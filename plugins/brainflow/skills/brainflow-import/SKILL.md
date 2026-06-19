---
name: brainflow-import
description: >-
  Importa un programma di corso in Brainflow come Flow, orchestrando i tool del
  server MCP "brainflow". Attiva quando l'utente nomina "brainflow" insieme
  all'intenzione di importare/caricare un programma, un syllabus o un corso
  (anche da un file PDF/DOCX/testo), es. "importa in brainflow il programma in
  /path/x.pdf", "carica questo corso in brainflow", "brainflow: importa questo
  syllabus". Keywords: brainflow, importa programma, carica corso, syllabus,
  flow, import flow.
allowed-tools:
  - ToolSearch
  - Read
  - mcp__brainflow__list_flows
  - mcp__brainflow__preview_flow
  - mcp__brainflow__import_flow
---

# Brainflow — Import di un programma come Flow

Questa skill NON re-implementa la logica di import: orchestra i tool del server
MCP `brainflow`. La *struttura* del flow è definita dallo schema input dei tool
(`FlowOutline`); questa skill aggiunge la *procedura* (leggere la fonte,
preview-prima, conferma, import).

## Passo 0 — Carica i tool MCP (ambiente lazy)

I tool MCP possono essere deferred. PRIMA di tutto caricane gli schemi:

```
ToolSearch  query: "select:mcp__brainflow__list_flows,mcp__brainflow__preview_flow,mcp__brainflow__import_flow"
```

Se la chiamata non trova i tool, il server `brainflow` non è collegato o non si
è autenticato. Cause tipiche: credenziali assenti
(`BRAINFLOW_MCP_EMAIL`/`BRAINFLOW_MCP_PASSWORD`) o API non raggiungibile
(`BRAINFLOW_API_URL`). Dillo all'utente (vedi il README del plugin per il setup)
e fermati.

## Passo 1 — Procurati il programma

- Se l'utente ha **incollato il testo**, usalo direttamente.
- Se ha indicato un **file** (PDF/DOCX/testo), leggilo con `Read`. Per i PDF,
  anche scansionati, leggi il contenuto e ricostruiscine il testo. Questa è la
  parte di parsing "fuzzy": è compito tuo (LLM), non del server.

## Passo 2 — Mappa in FlowOutline

Costruisci l'oggetto `outline` secondo lo schema dei tool:

- `units` = le lezioni/moduli/giornate del programma, in ordine.
- `topics` = gli argomenti principali di ogni unit.
- `subtopics` = i dettagli sotto un argomento. **Massimo 2 livelli**: se trovi
  una struttura più profonda, appiattiscila a 2.
- `tracks` = solo se il programma ha binari paralleli (es. Teoria/Lab); imposta
  `parallel_tracks_enabled` e assegna `track` ai topic. Altrimenti lascia
  `tracks` vuoto (default 'A').
- `is_exercise` = true per esercizi/attività pratiche.
- `date` (ISO `YYYY-MM-DD`) sulle unit solo se il programma le indica.

## Passo 2b — Conferma le scelte inferite (non assumere)

Prima della preview, NON decidere in silenzio le scelte consequenziali o
ambigue: esplicitale e fatti confermare.

- **Titolo**: se l'utente NON ha indicato un titolo, proponine uno (dedotto dal
  programma) e chiedi conferma. Se l'ha indicato, usa il suo.
- **Tracce**: se dal programma non è ovvio se servano tracce parallele,
  **CHIEDI** "una traccia unica o più tracce (es. Teoria/Lab)?" invece di
  decidere da solo. Le tracce cambiano la struttura: è una scelta da confermare.
- Dichiara comunque cosa hai **inferito** vs cosa ti è stato **dato**.

Procedi alla preview solo con le scelte confermate. (Il titolo è a basso
rischio: `import_flow` lo rende comunque unico. Le tracce no: confermale.)

## Passo 3 — Evita duplicati (opzionale)

Se l'utente sta (ri)caricando un programma che potrebbe già esistere, chiama
`list_flows` e segnala eventuali flow con titolo simile, chiedendo se creare
nuovo o procedere comunque. `list_flows` mostra solo i flow su cui l'utente
autenticato ha visibilità.

## Passo 4 — Preview SEMPRE prima di scrivere

Chiama `preview_flow(outline)` e MOSTRA all'utente:
- l'albero (`tree`),
- il riepilogo (`summary`),
- i `warnings` (es. track sconosciute, unit senza argomenti),
- e le scelte `inferred` (es. tracce defaultate) per un'ultima conferma.

La preview è una validazione **locale** (struttura): non scrive nulla. La
validazione autorevole avviene lato API al Passo 6.

## Passo 5 — Conferma esplicita

FERMATI e attendi un OK esplicito dell'utente. Non chiamare `import_flow` di
tua iniziativa.

## Passo 6 — Import

Dopo la conferma, chiama `import_flow(outline)` e riporta `id`, `title` e
numero di unit creati. Il server crea tutto in transazione atomica e rende
unico il titolo in caso di collisione.

Se la risposta contiene `error` invece di `id`, l'import è stato rifiutato
dall'API: mostra `error`/`details` (es. validazione fallita o permessi
mancanti), correggi se possibile e riprova dal Passo 4.
