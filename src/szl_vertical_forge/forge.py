"""szl-vertical-forge: audited vertical configs in, killinchu-pattern shells out.

Doctrine:
- Configs are the audited estate map (verticals.json), not invention.
- Every shell probes its live endpoint at request time and labels the result
  MEASURED or UNAVAILABLE - never fabricated.
- Generation is deterministic: same configs, same bytes, same master hash.
- Invalid configs fail closed with every error named.
- Lineage is honored, never hidden: every vertical names its field leader,
  the job that leader owns, and the SZL tweak. Take the JOB, never the code.
"""
from __future__ import annotations
import hashlib, json, os, re
from typing import Any, Dict, List

WIDGETS = {"osint", "receipts", "lambda", "probe", "ouroboros", "bm25", "quant"}
VERTICALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verticals.json")

def load_verticals(path: str = VERTICALS_PATH) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["verticals"]

def validate_vertical(v: Dict[str, Any]) -> List[str]:
    errs = []
    for k in ("id", "name", "domain", "tagline", "widget", "kernels", "repos"):
        if k not in v or not v[k]:
            errs.append(f"missing/empty: {k}")
    if v.get("widget") not in WIDGETS:
        errs.append(f"unknown widget: {v.get('widget')}")
    if v.get("endpoint") and not str(v["endpoint"]).startswith("https://"):
        errs.append("endpoint must be https")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", v.get("id", "")):
        errs.append("id must be slug-safe")
    lin = v.get("lineage")
    if not isinstance(lin, dict) or set(lin) != {"leader", "job", "tweak"} or not all(lin.values()):
        errs.append("lineage must carry leader + job + tweak")
    return errs

LANDING = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>{name} — SZL Holdings</title>
<meta name="description" content="{tagline}">
<style>
:root{{--bg:#070b12;--ink:#e6edfb;--muted:#9fb0cf;--faint:#6b7a99;--line:rgba(140,170,220,.14);
--teal:#3af4c8;--blue:#5b8dee;--violet:#8a6bff;--amber:#d4a444}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,"Segoe UI",Roboto,sans-serif}}
body::before{{content:"";position:fixed;inset:-30%;z-index:-1;pointer-events:none;filter:blur(6px);animation:drift 24s ease-in-out infinite alternate;
background:radial-gradient(45% 40% at 18% 12%, rgba(58,244,200,.10), transparent 60%),
radial-gradient(50% 45% at 85% 8%, rgba(91,141,238,.12), transparent 60%),
radial-gradient(55% 50% at 70% 95%, rgba(138,107,255,.12), transparent 60%)}}
@keyframes drift{{from{{transform:translate3d(-2%,-1%,0)}}to{{transform:translate3d(2%,1%,0) scale(1.06)}}}}
main{{max-width:980px;margin:auto;padding:64px 20px 80px}}
.kicker{{font-size:11px;letter-spacing:.4em;text-transform:uppercase;color:var(--faint)}}
h1{{font-size:clamp(34px,7vw,64px);line-height:1.02;margin:14px 0;font-weight:850;letter-spacing:-.5px}}
.grad{{background:linear-gradient(100deg,var(--teal),var(--blue) 45%,var(--violet));-webkit-background-clip:text;background-clip:text;color:transparent}}
.lede{{max-width:62ch;color:var(--muted);font-size:17px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0}}
.chip{{font-size:11px;font-weight:600;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:6px 12px;background:rgba(255,255,255,.028)}}
.chip b{{color:var(--ink)}}
.pill{{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:7px 12px;font:700 10.5px ui-monospace,monospace;border:1px solid var(--line);color:var(--amber)}}
.pill::before{{content:"";width:7px;height:7px;border-radius:50%;background:currentColor;box-shadow:0 0 12px currentColor}}
.pill.live{{color:var(--teal);border-color:rgba(58,244,200,.35)}}
.panel{{border:1px solid var(--line);border-radius:16px;padding:22px;margin-top:26px;background:linear-gradient(145deg,rgba(12,24,39,.9),rgba(8,15,27,.9))}}
.panel h2{{font-size:13px;letter-spacing:.28em;text-transform:uppercase;color:var(--teal);margin:0 0 10px}}
a{{color:var(--blue)}}code{{background:rgba(255,255,255,.06);border-radius:6px;padding:1px 6px;font-size:12.5px;color:var(--teal)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin-top:10px}}
.asset{{border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:12px;color:var(--muted)}}
.asset b{{display:block;color:var(--ink);font:700 10px ui-monospace,monospace;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}}
.asset i{{color:var(--faint)}}
footer{{margin-top:34px;color:var(--faint);font-size:12px;border-top:1px solid var(--line);padding-top:16px}}
@media(prefers-reduced-motion:reduce){{body::before{{animation:none}}}}
</style></head><body><main>
<div class="kicker">SZL Holdings &middot; {domain}</div>
<h1>{name} <span class="grad">— proven, not promised.</span></h1>
<p class="lede">{tagline}.</p>
<div class="chips"><span class="chip">Doctrine <b>v11</b></span><span class="chip">&Lambda; = Conjecture 1 &middot; advisory</span>
<span class="chip">receipts.in &equiv; receipts.out</span><span class="chip">widget <b>{widget}</b></span></div>
<span class="pill" id="livepill">PROBING</span>
<div class="panel"><h2>The application, live</h2>
<p style="color:var(--muted);font-size:13px">The running console mounts at <code>/panels</code>. Data below is probed at request time and labeled MEASURED or UNAVAILABLE — never fabricated.</p>
<div id="demodata" style="font:12px ui-monospace,monospace;color:var(--muted);white-space:pre-wrap">waiting for probe…</div></div>
<div class="panel"><h2>Estate wiring</h2><div class="grid">
<div class="asset"><b>Repos</b>{repos}</div><div class="asset"><b>Kernels</b>{kernels}</div>
<div class="asset"><b>Models</b>{models}</div><div class="asset"><b>Datasets</b>{datasets}</div>
<div class="asset"><b>Lineage</b>Field leader: {leader} — {job}. <b>SZL tweak:</b> {tweak}. <i>Take the JOB from the leader, never the code.</i></div></div></div>
<footer>Proof before pitch. &middot; Generated by szl-vertical-forge &middot; build receipt <code>{receipt}</code></footer>
</main><script>
const EP = {endpoint_js};
const pill = document.getElementById('livepill');
const out = document.getElementById('demodata');
if (!EP) {{ pill.textContent = 'DECLARED - NO PUBLIC ENDPOINT'; }}
else {{ fetch(EP, {{method:'GET'}}).then(r => r.json().then(j => {{
  pill.textContent = 'MEASURED - HTTP ' + r.status; pill.classList.add('live');
  out.textContent = JSON.stringify(j, null, 2).slice(0, 1200);
}})).catch(e => {{ pill.textContent = 'UNAVAILABLE'; out.textContent = 'endpoint unreachable: ' + e; }}); }}
</script></body></html>
"""

def forge(verticals: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Validate every vertical, then generate its landing page. Deterministic."""
    if verticals is None:
        verticals = load_verticals()
    files: Dict[str, str] = {}
    errors: Dict[str, List[str]] = {}
    for v in verticals:
        errs = validate_vertical(v)
        if errs:
            errors[v.get("id", "?")] = errs
            continue
        def links(items, base):
            return ", ".join(f'<a href="{base}{i}" target="_blank" rel="noopener">{i}</a>' for i in items) or "none declared"
        lin = v["lineage"]
        body_src = f"{v['id']}:{v['tagline']}:{v['widget']}:{lin['leader']}"
        receipt = hashlib.sha256(body_src.encode()).hexdigest()[:16]
        html = (LANDING
                .replace("{name}", v["name"]).replace("{domain}", v["domain"])
                .replace("{tagline}", v["tagline"]).replace("{widget}", v["widget"])
                .replace("{repos}", links(v["repos"], "https://github.com/szl-holdings/"))
                .replace("{kernels}", links(v["kernels"], "https://huggingface.co/SZLHOLDINGS/"))
                .replace("{models}", links(v["models"], "https://huggingface.co/SZLHOLDINGS/"))
                .replace("{datasets}", links(v["datasets"], "https://huggingface.co/datasets/SZLHOLDINGS/"))
                .replace("{leader}", lin["leader"]).replace("{job}", lin["job"])
                .replace("{tweak}", lin["tweak"])
                .replace("{receipt}", receipt)
                .replace("{endpoint_js}", json.dumps(v["endpoint"])))
        files[f"{v['id']}/index.html"] = html
    if errors:
        return {"state": "INVALID", "errors": errors}
    master = hashlib.sha256(json.dumps({k: hashlib.sha256(s.encode()).hexdigest()
                                        for k, s in sorted(files.items())}, sort_keys=True).encode()).hexdigest()
    return {"state": "MEASURED", "generated": sorted(files), "count": len(files),
            "master_hash": master, "label": "forge output - deterministic from audited configs"}

if __name__ == "__main__":
    out = forge()
    if out["state"] != "MEASURED":
        raise SystemExit(f"forge INVALID: {out['errors']}")
    print(json.dumps({"state": out["state"], "count": out["count"],
                      "master_hash": out["master_hash"]}, indent=2))
