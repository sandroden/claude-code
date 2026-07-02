#!/usr/bin/env python3
"""Analizza i transcript (.jsonl) di un progetto Claude Code e produce un report
HTML interattivo su: crescita del contesto, consumo totale di token (integrale)
e stima costi per modello.

Due modalita':
  --list    elenca le sessioni del progetto ordinate per lunghezza (turni)
  (default) genera l'HTML per le sessioni scelte

Solo stdlib. Vedi `--help`.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"

# prezzi per token [input, output, cache_read, cache_creation] (listino gen 2026)
PRICES = {
    "Opus":   [5e-6, 25e-6, 0.5e-6, 6.25e-6],
    "Sonnet": [3e-6, 15e-6, 0.3e-6, 3.75e-6],
    "Haiku":  [1e-6,  5e-6, 0.1e-6, 1.25e-6],
}


def encode_cwd(path):
    """Replica la codifica di Claude Code: ogni char non alfanumerico -> '-'."""
    return re.sub(r"[^a-zA-Z0-9]", "-", str(path))


def default_name(dirname):
    """Nome leggibile dal nome-cartella codificato: toglie il prefisso
    '-home-<user>-...' e tiene gli ultimi 2 token (es. 'desica-teams')."""
    parts = [p for p in dirname.split("-") if p]
    return "-".join(parts[-2:]) if len(parts) >= 2 else dirname


def resolve_project_dir(dir_arg, cwd_arg, project_arg):
    """Restituisce la Path della cartella transcript del progetto."""
    if dir_arg:
        p = Path(dir_arg).expanduser()
        if p.is_dir():
            return p
        sys.exit(f"cartella non trovata: {p}")
    if project_arg:
        # nome esatto oppure match per sottostringa sul basename
        cand = PROJECTS_DIR / project_arg
        if cand.is_dir():
            return cand
        dirs = [d for d in PROJECTS_DIR.iterdir() if d.is_dir()]
        # priorita': suffisso esatto > sottostringa
        ends = [d for d in dirs if d.name.endswith(project_arg)]
        hits = ends or [d for d in dirs if project_arg in d.name]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            sys.exit("piu' progetti corrispondono a '%s':\n  %s"
                     % (project_arg, "\n  ".join(d.name for d in hits)))
        sys.exit(f"nessun progetto contiene '{project_arg}' in {PROJECTS_DIR}")
    base = cwd_arg or os.getcwd()
    enc = PROJECTS_DIR / encode_cwd(base)
    if enc.is_dir():
        return enc
    sys.exit(f"transcript non trovati per '{base}'\n  atteso: {enc}\n"
             "  usa --dir o --project")


def is_real_user(line):
    """True se la riga e' un prompt utente reale (un 'Enter'), non un rimbalzo di
    protocollo (tool_result), non metadato/sidechain, non marker di sistema."""
    if line.get("type") != "user" or line.get("isMeta") or line.get("isSidechain"):
        return False
    c = line.get("message", {}).get("content")
    if isinstance(c, str):
        t = c
    elif isinstance(c, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
            return False
        has_img = any(isinstance(b, dict) and b.get("type") == "image" for b in c)
        has_txt = any(isinstance(b, dict) and b.get("type") == "text" for b in c)
        if has_img and not has_txt:
            return True
        t = " ".join(b.get("text", "") for b in c
                     if isinstance(b, dict) and b.get("type") == "text")
    else:
        return False
    t = t.strip()
    if not t:
        return False
    for bad in ("[Request interrupted", "<command-", "<local-command", "Caveat:"):
        if t.startswith(bad):
            return False
    return True


def first_prompt_snippet(line, n=38):
    c = line.get("message", {}).get("content")
    if isinstance(c, list):
        c = " ".join(b.get("text", "") for b in c
                     if isinstance(b, dict) and b.get("type") == "text")
    t = re.sub(r"\s+", " ", str(c or "")).strip()
    return (t[:n] + "…") if len(t) > n else t


def analyze_file(path):
    """Estrae i dati di una sessione dal .jsonl. None se non ha turni assistant."""
    aturn = 0
    pts, cum, comp, marks = [], [], [], []
    tot_out = tot_cr = total = 0
    snippet = ""
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                l = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if is_real_user(l):
                marks.append(aturn + 1)
                if not snippet:
                    snippet = first_prompt_snippet(l)
            if l.get("type") == "assistant":
                u = l.get("message", {}).get("usage")
                if not u:
                    continue
                aturn += 1
                cr = u.get("cache_read_input_tokens", 0) or 0
                cc = u.get("cache_creation_input_tokens", 0) or 0
                inp = u.get("input_tokens", 0) or 0
                out = u.get("output_tokens", 0) or 0
                ctx = cr + cc + inp
                pts.append([aturn, ctx])
                cum.append([aturn, total + ctx + out])
                comp.append([aturn, cr, cc, inp, out])
                total += ctx + out
                tot_out += out
                tot_cr += cr
    if aturn == 0:
        return None
    maxctx = max(p[1] for p in pts)
    n = len(pts)
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxx = sum(p[0] ** 2 for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx) if (n * sxx - sx * sx) else 0
    n_user = len(marks)
    return {
        "id": path.stem,
        "id8": path.stem[:8],
        "snippet": snippet,
        "turns": aturn,
        "n_user": n_user,
        "usermarks": marks,
        "total": total,
        "tot_out": tot_out,
        "tot_cr": tot_cr,
        "ratio": round(tot_cr / tot_out) if tot_out else 0,
        "maxctx": maxctx,
        "slope": round(slope),
        "integral_x": round(total / maxctx) if maxctx else 0,
        "bounce": round(aturn / n_user, 1) if n_user else 0.0,
        "pts": pts,
        "cum": cum,
        "comp": comp,
        "mtime": path.stat().st_mtime,
    }


def scan(proj_dir, min_turns=1):
    out = []
    for f in sorted(proj_dir.glob("*.jsonl")):
        try:
            s = analyze_file(f)
        except Exception as e:  # noqa: BLE001
            print(f"# skip {f.name}: {e}", file=sys.stderr)
            continue
        if s and s["turns"] >= min_turns:
            out.append(s)
    out.sort(key=lambda s: s["turns"], reverse=True)
    return out


def cmd_list(sessions, as_json):
    if as_json:
        light = [{k: s[k] for k in ("id", "id8", "snippet", "turns", "n_user",
                                    "total", "maxctx", "integral_x", "mtime")}
                 for s in sessions]
        print(json.dumps(light, ensure_ascii=False))
        return
    fmt = lambda n: (f"{n/1e6:.1f}M" if n >= 1e6 else
                     f"{n/1e3:.0f}k" if n >= 1e3 else str(n))
    print(f"{'#':>2}  {'id':8}  {'turni':>6}  {'prompt':>6}  "
          f"{'picco':>7}  {'consumo':>8}  primo prompt")
    for i, s in enumerate(sessions, 1):
        print(f"{i:>2}  {s['id8']:8}  {s['turns']:>6}  {s['n_user']:>6}  "
              f"{fmt(s['maxctx']):>7}  {fmt(s['total']):>8}  {s['snippet']}")


# --------------------------------------------------------------------------- #
#  Generazione HTML
# --------------------------------------------------------------------------- #

def build_data(selected, featured):
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ordered = [featured] + [s for s in selected if s is not featured]
    D = {"sessions": {}, "stats": {}}
    for i, s in enumerate(ordered):
        letter = letters[i] if i < len(letters) else f"#{i+1}"
        label = f"Sessione {letter}"
        if s["snippet"]:
            label += " — " + s["snippet"]
        D["sessions"][s["id8"]] = {
            "label": label,
            "turns": s["turns"],
            "n_user": s["n_user"],
            "usermarks": s["usermarks"],
            "total": s["total"],
            "bounce": s["bounce"],
            "pts": s["pts"],
            "cum": s["cum"],
            "comp": s["comp"],
        }
    f = featured
    D["stats"] = {
        "turns": f["turns"], "maxctx": f["maxctx"], "slope": f["slope"],
        "tot_out": f["tot_out"], "tot_cr": f["tot_cr"], "ratio": f["ratio"],
        "total": f["total"], "n_user": f["n_user"], "bounce": f["bounce"],
        "integral_x": f["integral_x"],
    }
    return D


def render_html(D, project_name):
    data_js = ("const D=" + json.dumps(D, ensure_ascii=False) +
               ", S=D.sessions, ST=D.stats;")
    return HTML_TEMPLATE.replace("__PROJECT__", project_name).replace(
        "/*__DATA__*/", data_js)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Contesto, consumo e costi &mdash; sessioni Claude Code</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
 :root{--bg:#0f1720;--card:#18232f;--fg:#e6edf3;--mut:#8aa0b3;--acc:#4fb0ff;--warn:#ff9f43;--ok:#39d98a;--vio:#c792ea;--red:#ff6b81}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
 header{padding:32px 24px 8px;max-width:1100px;margin:0 auto}
 h1{font-size:26px;margin:0 0 6px}
 .sub{color:var(--mut);margin:0 0 4px}
 main{max-width:1100px;margin:0 auto;padding:16px 24px 60px}
 .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin:20px 0 28px}
 .card{background:var(--card);border:1px solid #24313f;border-radius:12px;padding:16px}
 .card .n{font-size:24px;font-weight:700}
 .card .l{color:var(--mut);font-size:12.5px;margin-top:2px}
 .card.hot .n{color:var(--warn)}
 .card.cost .n{color:var(--ok)}
 .panel{background:var(--card);border:1px solid #24313f;border-radius:14px;padding:18px 18px 22px;margin:22px 0}
 .panel h2{margin:0 0 4px;font-size:18px}
 .panel p.note{color:var(--mut);margin:0 0 14px;font-size:13.5px}
 .chartbox{position:relative;height:420px}
 .chartbox.sm{height:340px}
 .readout{margin-top:12px;padding:11px 14px;background:#0d1a12;border:1px solid #204a30;border-radius:9px;font-size:14px}
 .readout b{color:var(--ok)}
 .readout .hint{color:var(--mut)}
 .readout table{border-collapse:collapse;margin-top:8px;font-size:13.5px}
 .readout td,.readout th{padding:3px 14px 3px 0;text-align:right}
 .readout th:first-child,.readout td:first-child{text-align:left}
 .readout th{color:var(--mut);font-weight:600}
 .chk{display:inline-flex;align-items:center;gap:7px;margin:2px 0 12px;font-size:13.5px;color:var(--mut);cursor:pointer;user-select:none}
 .chk input{width:15px;height:15px;accent-color:var(--ok);cursor:pointer}
 ul.reflect{list-style:none;padding:0;margin:0}
 ul.reflect li{padding:12px 14px;margin:9px 0;background:#13202b;border-left:3px solid var(--acc);border-radius:8px}
 ul.reflect li b{color:var(--fg)}
 .tag{display:inline-block;font-size:11px;color:#0f1720;background:var(--acc);border-radius:20px;padding:2px 9px;font-weight:700}
 .warn{border-left-color:var(--warn)!important}
 .ok{border-left-color:var(--ok)!important}
 .vio{border-left-color:var(--vio)!important}
 footer{color:var(--mut);font-size:12px;text-align:center;padding:20px}
 code{background:#0b1219;padding:1px 6px;border-radius:5px;color:#9fd0ff}
 table.bt{width:100%;border-collapse:collapse;margin-top:6px;font-size:13.5px}
 table.bt th,table.bt td{text-align:right;padding:7px 10px;border-bottom:1px solid #223040}
 table.bt th:first-child,table.bt td:first-child{text-align:left}
 table.bt th{color:var(--mut);font-weight:600}
 table.bt td.big{color:var(--warn);font-weight:700}
 table.bt td.cost{color:var(--ok);font-weight:700}
</style>
</head>
<body>
<header>
 <span class="tag">Claude Code &middot; progetto __PROJECT__</span>
 <h1>Contesto, consumo di token e costo API</h1>
 <p class="sub">Transcript reali delle sessioni pi&ugrave; lunghe. Tre grandezze: il <b>contesto</b> di un turno, il <b>consumo totale</b> (integrale dei token) e il <b>costo</b> &mdash; che <b>non</b> &egrave; proporzionale ai token, perch&eacute; i token riletti da cache costano ~1/10.</p>
</header>
<main>
 <div class="cards" id="cards"></div>

 <div class="panel">
  <h2>1 &middot; Contesto per turno &mdash; tutte le sessioni</h2>
  <p class="note">Asse X = turno dell'assistente (ogni chiamata al modello, <b>inclusi i rimbalzi</b>). Asse Y = token in contesto. Rossa tratteggiata = 200k.</p>
  <div class="chartbox"><canvas id="c1"></canvas></div>
 </div>

 <div class="panel">
  <h2>2 &middot; Di cosa &egrave; fatto il contesto &mdash; Sessione A (<span id="d-ft"></span> turni)</h2>
  <p class="note">Area impilata. Il <b>cache_read</b> (blu) domina &mdash; ed &egrave; anche il token pi&ugrave; economico (~1/10 dell'input). <b>output</b> resta piccolo ma &egrave; il pi&ugrave; caro.</p>
  <div class="chartbox sm"><canvas id="c2"></canvas></div>
 </div>

 <div class="panel">
  <h2>3 &middot; Un prompt utente, tanti rimbalzi</h2>
  <p class="note">Sessione A. Ogni <b style="color:var(--ok)">barretta verde</b> &egrave; un <b>prompt utente</b> (Enter): <span id="d-np"></span> prompt &rarr; <span id="d-ft2"></span> turni. Hover per il <b>prompt #N</b>; <b>trascina</b> per l'integrale (token) di un intervallo.</p>
  <div class="chartbox"><canvas id="c3"></canvas></div>
  <div class="readout" id="c3read"><span class="hint">&harr; Trascina sul grafico per l'integrale di un intervallo.</span></div>
 </div>

 <div class="panel">
  <h2>4 &middot; Consumo (integrale) e costo API</h2>
  <p class="note">Asse <b>sinistro</b>: token consumati cumulativi (milioni). Asse <b>destro</b>: costo cumulativo stimato su <b>Opus 4.8</b> (linea gialla tratteggiata, solo Sessione A) &mdash; il modello reale delle sessioni. <b>Trascina</b> per il costo di un intervallo su pi&ugrave; modelli. Prezzi: Opus $5/$25, Sonnet $3/$15, Haiku $1/$5 per Mtok; cache-read ~1/10 dell'input.</p>
  <label class="chk"><input type="checkbox" id="tgl4"> mostra i prompt utente (Enter) &mdash; Sessione A</label>
  <div class="chartbox"><canvas id="c4"></canvas></div>
  <div class="readout" id="c4read"><span class="hint">&harr; Trascina sul grafico per il costo dell'intervallo, per modello.</span></div>
  <table class="bt" id="bt"></table>
 </div>

 <div class="panel">
  <h2>Riflessioni</h2>
  <ul class="reflect">
   <li class="vio"><b>&laquo;Interazione&raquo; non &egrave; &laquo;prompt&raquo;.</b> I <b id="r-turns"></b> turni della Sessione A nascono da <b id="r-user"></b> prompt tuoi: ~<b id="r-bounce"></b> turni di protocollo per prompt (<span id="d-hb"></span>). I rimbalzi non li comandi ma pesano quanto e pi&ugrave; dei tuoi messaggi.</li>
   <li class="warn"><b>Contesto di picco &ne; consumo.</b> Picco <b id="r-max"></b>, ma consumo totale <b id="r-total"></b> di token: <b id="r-int"></b> volte il picco. L'occupazione della finestra nasconde il costo vero, che &egrave; l'integrale.</li>
   <li class="ok"><b>Il costo non segue i token.</b> La Sessione A consuma <b id="r-total2"></b> di token ma costa solo <b id="r-costopus"></b> su Opus &mdash; molto meno del prezzo input pieno. Il <code>cache_read</code> (la gran parte del volume) costa ~1/10, quindi <b>abbatte il costo</b>. Stesso lavoro su Sonnet ~<b id="r-costsonnet"></b>, su Haiku ~<b id="r-costhaiku"></b>.</li>
   <li><b>Cresce quadraticamente.</b> Contesto ~lineare (<b id="r-slope"></b> tok/turno) &rarr; consumo e costo (l'integrale) crescono col <b>quadrato</b> dei turni. Le ultime interazioni costano molto pi&ugrave; delle prime a parit&agrave; di lavoro.</li>
   <li class="ok"><b>Cosa farci.</b> (1) Compattare / aprire sessioni nuove ai cambi di task abbassa l'altezza e quindi area e costo. (2) Ridurre i rimbalzi inutili taglia l'integrale. (3) Delegare a subagenti isola il contesto pesante. (4) Il caching &egrave; gi&agrave; il maggior risparmio: non invalidarlo (evitare di cambiare tool/prompt di sistema a met&agrave; sessione).</li>
  </ul>
 </div>
 <footer>Analisi di <span id="d-ns"></span> sessioni &middot; costi stimati (listino gen 2026, TTL cache 5 min) &middot; dati locali, nessun invio esterno</footer>
</main>
<script>
/*__DATA__*/
const fmt=n=>n>=1e6?(n/1e6).toFixed(n>=1e7?0:1)+'M':n>=1e3?(n/1e3).toFixed(0)+'k':Math.round(n);
const usd=n=>n>=100?'$'+n.toFixed(0):n>=1?'$'+n.toFixed(2):'$'+n.toFixed(3);
const palette=['#4fb0ff','#39d98a','#ff9f43','#c792ea','#ff6b81','#5adfd0'];
const keys=Object.keys(S), A=keys[0];
const marks=S[A].usermarks.slice().sort((a,b)=>a-b);
const promptOf=t=>{let i=0;for(const m of marks){if(m<=t)i++;else break;}return i;};

// prezzi per token: [input, output, cache_read, cache_creation]
const PRICES={Opus:[5e-6,25e-6,0.5e-6,6.25e-6],Sonnet:[3e-6,15e-6,0.3e-6,3.75e-6],Haiku:[1e-6,5e-6,0.1e-6,1.25e-6]};
// comp Sessione A: [t,cr,cc,inp,out]
const AC=S[A].comp; const maxT=S[A].turns;
const ctxByT=[]; S[A].pts.forEach(p=>ctxByT[p[0]]=p[1]);
const preCtx=[0]; for(let t=1;t<=maxT;t++)preCtx[t]=preCtx[t-1]+(ctxByT[t]||0);
const integralCtx=(a,b)=>preCtx[b]-preCtx[a-1];
// prefix per componente
const preCR=[0],preCC=[0],preINP=[0],preOUT=[0]; const byT={};
AC.forEach(r=>byT[r[0]]=r);
for(let t=1;t<=maxT;t++){const r=byT[t]||[t,0,0,0,0];preCR[t]=preCR[t-1]+r[1];preCC[t]=preCC[t-1]+r[2];preINP[t]=preINP[t-1]+r[3];preOUT[t]=preOUT[t-1]+r[4];}
function costRange(a,b,model){const p=PRICES[model];const cr=preCR[b]-preCR[a-1],cc=preCC[b]-preCC[a-1],inp=preINP[b]-preINP[a-1],out=preOUT[b]-preOUT[a-1];return inp*p[0]+out*p[1]+cr*p[2]+cc*p[3];}
// costo cumulativo Opus (Sessione A) per il dataset asse destro
const cumCostOpus=[]; {let c=0; for(let i=0;i<AC.length;i++){const r=AC[i];const p=PRICES.Opus;c+=r[3]*p[0]+r[4]*p[1]+r[1]*p[2]+r[2]*p[3];cumCostOpus.push({x:r[0],y:c});}}
const totOpus=costRange(1,maxT,'Opus'),totSonnet=costRange(1,maxT,'Sonnet'),totHaiku=costRange(1,maxT,'Haiku');

// testi dinamici
const q=id=>document.getElementById(id);
[['d-ft',ST.turns],['d-ft2',ST.turns],['d-np',marks.length],['d-ns',keys.length]].forEach(([i,v])=>{if(q(i))q(i).textContent=v;});
{const hb=keys.map(k=>S[k]).reduce((a,b)=>((b.turns/Math.max(1,b.n_user))>(a.turns/Math.max(1,a.n_user))?b:a));
 if(q('d-hb'))q('d-hb').textContent=`${hb.label.split(' —')[0].trim()}: ${hb.n_user} prompt → ${hb.turns} turni`;}

// cards
const cards=[[String(ST.n_user),'prompt utente (Sessione A)',''],[String(ST.turns),'turni generati',''],[fmt(ST.maxctx),'contesto di picco',''],[fmt(ST.total),'token consumati',' hot'],[ST.integral_x+'&times;','consumo / picco',' hot'],[usd(totOpus),'costo Sessione A (Opus)',' cost']];
document.getElementById('cards').innerHTML=cards.map(c=>`<div class="card${c[2]}"><div class="n">${c[0]}</div><div class="l">${c[1]}</div></div>`).join('');
const set=(id,v)=>{const e=document.getElementById(id);if(e)e.innerHTML=v;};
set('r-turns',ST.turns);set('r-user',ST.n_user);set('r-bounce',ST.bounce.toFixed(0));set('r-max',fmt(ST.maxctx));set('r-total',fmt(ST.total));set('r-total2',fmt(ST.total));set('r-int',ST.integral_x+'&times;');set('r-slope','~'+ST.slope);
set('r-costopus',usd(totOpus));set('r-costsonnet',usd(totSonnet));set('r-costhaiku',usd(totHaiku));

const l200={id:'l200',afterDraw:ch=>{const y=ch.scales.y.getPixelForValue(200000);if(y<ch.chartArea.top||y>ch.chartArea.bottom)return;const c=ch.ctx;c.save();c.strokeStyle='#ff6b81';c.setLineDash([6,5]);c.lineWidth=1.5;c.beginPath();c.moveTo(ch.chartArea.left,y);c.lineTo(ch.chartArea.right,y);c.stroke();c.fillStyle='#ff6b81';c.font='11px sans-serif';c.fillText('200k — finestra standard',ch.chartArea.left+6,y-5);c.restore();}};
const axes=(xt,yt,ycb)=>({x:{type:'linear',title:{display:true,text:xt,color:'#8aa0b3'},ticks:{color:'#8aa0b3'},grid:{color:'#1e2b38'}},y:{title:{display:true,text:yt,color:'#8aa0b3'},ticks:{color:'#8aa0b3',callback:ycb},grid:{color:'#1e2b38'}}});
const leg={labels:{color:'#cfe0ee',boxWidth:14}};
const enterBars=()=>({id:'eb',afterDatasetsDraw:ch=>{const c=ch.ctx,ca=ch.chartArea,xs=ch.scales.x;c.save();marks.forEach(m=>{const x=xs.getPixelForValue(m);if(x<ca.left||x>ca.right)return;c.strokeStyle='rgba(57,217,138,.28)';c.lineWidth=1;c.beginPath();c.moveTo(x,ca.top);c.lineTo(x,ca.bottom);c.stroke();c.fillStyle='#39d98a';c.fillRect(x-2,ca.bottom-9,4,9);});c.restore();}});
function makeBand(sel){return {id:'band',afterDatasetsDraw:ch=>{if(sel.a==null||sel.b==null)return;const c=ch.ctx,ca=ch.chartArea,xs=ch.scales.x;let a=Math.min(sel.a,sel.b),b=Math.max(sel.a,sel.b);let xa=Math.max(ca.left,Math.min(ca.right,xs.getPixelForValue(a))),xb=Math.max(ca.left,Math.min(ca.right,xs.getPixelForValue(b)));c.save();c.fillStyle='rgba(79,176,255,.16)';c.fillRect(xa,ca.top,xb-xa,ca.bottom-ca.top);c.strokeStyle='#4fb0ff';c.lineWidth=1;[xa,xb].forEach(x=>{c.beginPath();c.moveTo(x,ca.top);c.lineTo(x,ca.bottom);c.stroke();});c.restore();}};}

// chart 1
new Chart(document.getElementById('c1'),{type:'line',data:{datasets:keys.map((k,i)=>({label:S[k].label+` (${S[k].turns}t)`,data:S[k].pts.map(p=>({x:p[0],y:p[1]})),borderColor:palette[i%6],backgroundColor:palette[i%6],borderWidth:2,pointRadius:0,tension:.15}))},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'nearest',intersect:false},plugins:{legend:leg,tooltip:{callbacks:{label:c=>c.dataset.label.split(' (')[0]+': '+fmt(c.parsed.y)+' tok @ t'+c.parsed.x}}},scales:axes('turno dell\'assistente','token in contesto',v=>fmt(v))},plugins:[l200]});

// chart 2
const mk=(idx,lab,col)=>({label:lab,data:AC.map(r=>({x:r[0],y:r[idx]})),borderColor:col,backgroundColor:col+'cc',fill:true,pointRadius:0,borderWidth:0,tension:.1});
new Chart(document.getElementById('c2'),{type:'line',data:{datasets:[mk(1,'cache_read (economico ~1/10)','#4fb0ff'),mk(2,'cache_creation (caro 1,25×)','#c792ea'),mk(3,'input','#39d98a'),mk(4,'output (il più caro)','#ff9f43')]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:leg,tooltip:{callbacks:{label:c=>c.dataset.label.split(' (')[0]+': '+fmt(c.parsed.y)}}},scales:{x:{type:'linear',stacked:true,title:{display:true,text:'turno dell\'assistente',color:'#8aa0b3'},ticks:{color:'#8aa0b3'},grid:{color:'#1e2b38'}},y:{stacked:true,title:{display:true,text:'token (per turno)',color:'#8aa0b3'},ticks:{color:'#8aa0b3',callback:v=>fmt(v)},grid:{color:'#1e2b38'}}}}});

// chart 3
const sel3={a:null,b:null,drag:false};
const c3=new Chart(document.getElementById('c3'),{type:'line',data:{datasets:[{label:'contesto',data:S[A].pts.map(p=>({x:p[0],y:p[1]})),borderColor:'#4fb0ff',backgroundColor:'#4fb0ff22',fill:true,borderWidth:2,pointRadius:0,tension:.15},{label:'| = prompt utente ('+marks.length+')',data:[],borderColor:'#39d98a',backgroundColor:'#39d98a'}]},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'nearest',intersect:false},plugins:{legend:leg,tooltip:{filter:it=>it.datasetIndex===0,callbacks:{label:c=>'contesto: '+fmt(c.parsed.y)+' @ turno '+c.parsed.x,afterLabel:c=>'prompt utente #'+promptOf(c.parsed.x)}}},scales:axes('turno dell\'assistente','token in contesto',v=>fmt(v))},plugins:[enterBars(),makeBand(sel3)]});
const r3=document.getElementById('c3read');
function px2turn(ch,e){return Math.max(1,Math.min(maxT,Math.round(ch.scales.x.getValueForPixel(e.offsetX))));}
function show3(){if(sel3.a==null||sel3.b==null){r3.innerHTML='<span class="hint">&harr; Trascina sul grafico per l\'integrale di un intervallo.</span>';return;}let a=Math.min(sel3.a,sel3.b),b=Math.max(sel3.a,sel3.b);const np=marks.filter(m=>m>=a&&m<=b).length;r3.innerHTML=`Turni <b>${a}–${b}</b> · prompt <b>#${promptOf(a)}→#${promptOf(b)}</b> (${np} prompt)&nbsp;&rarr;&nbsp;integrale ≈ <b>${fmt(integralCtx(a,b))} token</b> <span class="hint">(area sotto la curva)</span>`;}
c3.canvas.addEventListener('mousedown',e=>{sel3.a=px2turn(c3,e);sel3.b=sel3.a;sel3.drag=true;c3.render();show3();});
c3.canvas.addEventListener('mousemove',e=>{if(!sel3.drag)return;sel3.b=px2turn(c3,e);c3.render();show3();});
window.addEventListener('mouseup',()=>{if(sel3.drag){sel3.drag=false;if(sel3.a===sel3.b){sel3.a=sel3.b=null;c3.render();}show3();}});

// chart 4 — dual axis (token sx, costo Opus dx) + Enter toggle + drag costo
let show4=false;
const eb4={id:'eb4',afterDatasetsDraw:ch=>{if(!show4)return;const c=ch.ctx,ca=ch.chartArea,xs=ch.scales.x;c.save();marks.forEach(m=>{const x=xs.getPixelForValue(m);if(x<ca.left||x>ca.right)return;c.strokeStyle='rgba(57,217,138,.22)';c.lineWidth=1;c.beginPath();c.moveTo(x,ca.top);c.lineTo(x,ca.bottom);c.stroke();c.fillStyle='#39d98a';c.fillRect(x-2,ca.bottom-9,4,9);});c.restore();}};
const sel4={a:null,b:null,drag:false};
const ds4=keys.map((k,i)=>({label:S[k].label,data:S[k].cum.map(p=>({x:p[0],y:p[1]})),borderColor:palette[i%6],backgroundColor:palette[i%6]+'22',fill:k===A,borderWidth:k===A?2.5:2,pointRadius:0,tension:.1,yAxisID:'y'}));
ds4.push({label:'costo Opus (Sessione A, $)',data:cumCostOpus,borderColor:'#ffd24f',borderDash:[6,4],borderWidth:2,pointRadius:0,tension:.1,yAxisID:'y1'});
const c4=new Chart(document.getElementById('c4'),{type:'line',data:{datasets:ds4},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'nearest',intersect:false},plugins:{legend:leg,tooltip:{callbacks:{label:c=>c.dataset.yAxisID==='y1'?'costo Opus: '+usd(c.parsed.y):c.dataset.label.split(' (')[0]+': '+fmt(c.parsed.y)+' tok'}}},scales:{x:{type:'linear',title:{display:true,text:'turno dell\'assistente',color:'#8aa0b3'},ticks:{color:'#8aa0b3'},grid:{color:'#1e2b38'}},y:{position:'left',title:{display:true,text:'token consumati (cumulativo)',color:'#8aa0b3'},ticks:{color:'#8aa0b3',callback:v=>fmt(v)},grid:{color:'#1e2b38'}},y1:{position:'right',title:{display:true,text:'costo cumulativo Opus ($)',color:'#ffd24f'},ticks:{color:'#ffd24f',callback:v=>'$'+v.toFixed(0)},grid:{drawOnChartArea:false}}}},plugins:[eb4,makeBand(sel4)]});
document.getElementById('tgl4').addEventListener('change',e=>{show4=e.target.checked;c4.render();});
const r4=document.getElementById('c4read');
function show4read(){if(sel4.a==null||sel4.b==null){r4.innerHTML='<span class="hint">&harr; Trascina sul grafico per il costo dell\'intervallo, per modello.</span>';return;}let a=Math.min(sel4.a,sel4.b),b=Math.max(sel4.a,sel4.b);const tok=S[A].cum[b-1][1]-(a>1?S[A].cum[a-2][1]:0);const co=costRange(a,b,'Opus'),cs=costRange(a,b,'Sonnet'),ch=costRange(a,b,'Haiku');r4.innerHTML=`Turni <b>${a}–${b}</b> (Sessione A) · ${fmt(tok)} token consumati`+
 `<table><tr><th>modello</th><th>costo intervallo</th></tr>`+
 `<tr><td>Opus 4.8</td><td><b>${usd(co)}</b></td></tr>`+
 `<tr><td>Sonnet 5</td><td><b>${usd(cs)}</b></td></tr>`+
 `<tr><td>Haiku 4.5</td><td><b>${usd(ch)}</b></td></tr></table>`;}
c4.canvas.addEventListener('mousedown',e=>{sel4.a=px2turn(c4,e);sel4.b=sel4.a;sel4.drag=true;c4.render();show4read();});
c4.canvas.addEventListener('mousemove',e=>{if(!sel4.drag)return;sel4.b=px2turn(c4,e);c4.render();show4read();});
window.addEventListener('mouseup',()=>{if(sel4.drag){sel4.drag=false;if(sel4.a===sel4.b){sel4.a=sel4.b=null;c4.render();}show4read();}});

// tabella
let rows='<tr><th>Sessione</th><th>Prompt</th><th>Turni</th><th>Picco</th><th>Consumo</th><th>Costo Opus</th></tr>';
keys.forEach(k=>{const s=S[k];const peak=Math.max(...s.pts.map(p=>p[1]));let c=0;s.comp.forEach(r=>{const p=PRICES.Opus;c+=r[3]*p[0]+r[4]*p[1]+r[1]*p[2]+r[2]*p[3];});rows+=`<tr><td>${s.label}</td><td>${s.n_user}</td><td>${s.turns}</td><td>${fmt(peak)}</td><td class="big">${fmt(s.total)}</td><td class="cost">${usd(c)}</td></tr>`;});
document.getElementById('bt').innerHTML=rows;
</script>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser(
        description="Report HTML su contesto/consumo/costi delle sessioni Claude Code.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Esempi:\n"
               "  %(prog)s --project desica-teams --list\n"
               "  %(prog)s --cwd /path/al/progetto --top 6 --out report.html\n"
               "  %(prog)s --dir ~/.claude/projects/<enc> --sessions 65ab0ff1 641bfc8f\n")
    src = ap.add_argument_group("sorgente progetto (scegline una; default: cwd)")
    src.add_argument("--dir", help="cartella transcript (~/.claude/projects/<enc>)")
    src.add_argument("--project", help="nome progetto sotto ~/.claude/projects (anche sottostringa)")
    src.add_argument("--cwd", help="working dir del progetto da codificare (default: cwd corrente)")
    ap.add_argument("--list", action="store_true", help="elenca le sessioni ordinate per turni ed esci")
    ap.add_argument("--json", action="store_true", help="con --list: output JSON")
    ap.add_argument("--sessions", nargs="+", metavar="ID",
                    help="id (anche prefisso a 8 char) delle sessioni da includere")
    ap.add_argument("--top", type=int, metavar="N", help="usa le N sessioni piu' lunghe")
    ap.add_argument("--min-turns", type=int, default=2,
                    help="ignora sessioni con meno di N turni (default 2)")
    ap.add_argument("--out", default="context-graph.html", help="file HTML di output")
    ap.add_argument("--name", help="nome progetto mostrato nel report (default: ricavato dal path)")
    args = ap.parse_args()

    proj = resolve_project_dir(args.dir, args.cwd, args.project)
    sessions = scan(proj, args.min_turns)
    if not sessions:
        sys.exit(f"nessuna sessione con >= {args.min_turns} turni in {proj}")

    if args.list:
        cmd_list(sessions, args.json)
        return

    chosen = sessions
    if args.sessions:
        wanted = set(args.sessions)
        chosen = [s for s in sessions
                  if s["id"] in wanted or s["id8"] in wanted
                  or any(s["id"].startswith(w) for w in wanted)]
        if not chosen:
            sys.exit("nessuna sessione corrisponde a --sessions")
    elif args.top:
        chosen = sessions[:args.top]
    else:
        chosen = sessions[:6]

    featured = max(chosen, key=lambda s: s["turns"])
    D = build_data(chosen, featured)
    name = args.name or default_name(proj.name)
    html = render_html(D, name)
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"scritto {args.out} — {len(chosen)} sessioni "
          f"(featured: {featured['id8']}, {featured['turns']} turni)")


if __name__ == "__main__":
    main()
