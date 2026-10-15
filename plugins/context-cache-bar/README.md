# context-cache-bar

Mod per Claude Code (hooks module, richiede Claude Code ≥ 2.1.287): una banda sopra il
prompt, nel terminale e nell'app desktop.

```
ctx [████░░░░░░░░] 14% (140K/1M)                          cache [████████] 58:36 /1h
proactivity(pkg)@default/topic
```

## Prima riga

- **Contesto**, a sinistra: barra non lineare, ripresa da `thx-statusline.sh`. Tre zone da 4
  blocchi (verde, ambra, giallo), ognuna riempita in proporzione al proprio tratto; oltre
  l'ultima soglia è rossa e piena. Le soglie dipendono dalla finestra del modello
  (`PROFILES` in `hooks/bar.ts`):

  | finestra | verde | ambra | giallo |
  |----------|-------|-------|--------|
  | ≤ 200K   | 40%   | 55%   | 75%    |
  | 1M       | 12%   | 25%   | 60%    |

  Con 1M, a 150K la barra è già ambra e piena per un terzo.

- **Cache**, a destra: countdown dall'ultima richiesta del thread principale (i subagenti
  non lo azzerano). Verde oltre il 50% del TTL, ambra oltre il 20%, poi rossa; a zero
  mostra `fredda`. È una stima: le API dei mod non espongono la scadenza vera.

## Seconda riga

Progetto, tipo e branch, come `render_project` della status line: nome da `pyproject.toml`
(o la cartella), `app` se c'è `Dockerfile`/`manage.py`, `pkg` con solo `pyproject.toml`;
branch `hg branch` + topic, oppure `git branch --show-current`. Nell'app desktop è un piccolo
SVG a 11px, nel terminale testo attenuato. Si aggiorna a fine turno.

## Opzioni

| opzione | valori | default |
|---------|--------|---------|
| `ttl`   | `auto`, `5m`, `1h` | `auto`: 1h se ci sono i rate limit dell'abbonamento, altrimenti 5m; un hit di cache dopo più di 5 minuti la porta a 1h |

## Sviluppo

```bash
claude plugin validate plugins/context-cache-bar
```

```bash
claude plugin test plugins/context-cache-bar
```

Nota: `$` non può essere passato a funzioni importate da altri file del mod (il caricamento
fallisce anche se `validate` passa): le funzioni che usano `$` stanno in `register.tsx`,
`bar.ts` contiene solo logica pura.
