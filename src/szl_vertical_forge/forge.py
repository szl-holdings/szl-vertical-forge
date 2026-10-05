"""Build and verify deterministic vertical landing-page artifacts.

The forge is deliberately a build tool, not a runtime oracle. It validates the
audited configuration, renders bytes, writes those bytes, and emits a
recomputable SHA-256 chain. Browser probes label verified upstream evidence as
REACHABLE, PARTIAL, STALE, SAMPLE, MODELED, or UNAVAILABLE; a successful HTTP
response is never promoted to a domain result.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urlsplit

VERSION = "0.2.3"
RECEIPT_SCHEMA = "szl.vertical-forge.receipt/v4"
RECEIPT_ALGORITHM = "sha256-canonical-json-chain"
HEADER_FIELDS = (
    "schema",
    "generator",
    "algorithm",
    "genesis",
    "config_sha256",
    "vertical_count",
)
ARTIFACT_SCHEMA = "szl.vertical-forge.artifact/v1"
ZERO_HASH = "0" * 64
WIDGETS = {"osint", "receipts", "lambda", "probe", "ouroboros", "bm25", "quant"}
# These flagship shells read the existing publisher's /api/live route. The
# configured root URLs for Counsel and Finance are product pages, not evidence
# endpoints. Sources are pinned from that publisher so a different feed cannot
# become evidence merely because the proxy returned HTTP 200.
PROBE_ENDPOINTS = {
    "counsel": "https://szlholdings-counsel.hf.space/api/live",
    "finance": "https://szlholdings-finance.hf.space/api/live",
}
PROBE_SOURCES = {
    "terra": "https://szlholdings-a11oy.hf.space/api/a11oy/v1/vert/realestate/feed",
    "counsel": "https://szlholdings-a11oy.hf.space/api/a11oy/v1/vert/legal/feed",
    "finance": "https://szlholdings-a11oy.hf.space/api/a11oy/v1/finance/overview",
}
VERTICALS_PATH = Path(__file__).with_name("verticals.json")
ASSET_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
HEX64_RE = re.compile(r"[0-9a-f]{64}")
GENERATOR_RE = re.compile(r"szl-vertical-forge/[0-9]+\.[0-9]+\.[0-9]+")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_verticals(
    path: str | os.PathLike[str] = VERTICALS_PATH,
) -> list[dict[str, Any]]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    verticals = document.get("verticals") if isinstance(document, dict) else None
    if not isinstance(verticals, list):
        raise ValueError("verticals document must contain a verticals array")
    return verticals


def _valid_probe_endpoint(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str) or not value:
        return False
    parsed = urlsplit(value)
    if value.startswith("/"):
        return not value.startswith("//") and not parsed.query and not parsed.fragment
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
    )


def _valid_source_url(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
    )


def validate_vertical(vertical: dict[str, Any]) -> list[str]:
    if not isinstance(vertical, dict):
        return ["vertical must be an object"]
    errors: list[str] = []
    scalar_fields = ("id", "name", "domain", "tagline", "widget")
    list_fields = ("kernels", "models", "datasets", "repos")
    for key in scalar_fields:
        if not isinstance(vertical.get(key), str) or not vertical[key].strip():
            errors.append(f"missing/empty string: {key}")
    for key in list_fields:
        value = vertical.get(key)
        if not isinstance(value, list) or any(
            not isinstance(item, str)
            or not item.strip()
            or not ASSET_RE.fullmatch(item)
            for item in (value if isinstance(value, list) else [])
        ):
            errors.append(f"{key} must be an array of safe non-empty names")
    if vertical.get("widget") not in WIDGETS:
        errors.append(f"unknown widget: {vertical.get('widget')}")
    if not SLUG_RE.fullmatch(str(vertical.get("id", ""))):
        errors.append("id must be slug-safe")
    if not _valid_probe_endpoint(vertical.get("endpoint")):
        errors.append("endpoint must be a safe root-relative path or HTTPS URL")
    lineage = vertical.get("lineage")
    if (
        not isinstance(lineage, dict)
        or set(lineage) != {"leader", "job", "tweak", "sources"}
        or any(
            not isinstance(lineage.get(key), str) or not lineage[key].strip()
            for key in ("leader", "job", "tweak")
        )
        or not isinstance(lineage.get("sources"), list)
        or not lineage["sources"]
        or any(not _valid_source_url(value) for value in lineage["sources"])
    ):
        errors.append("lineage must carry leader + job + tweak + HTTPS sources")
    return errors


PROBE_SCRIPT = r"""
const pill=document.getElementById('livepill'),out=document.getElementById('demodata');
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
function stateFor(response,body){
  if(!response.ok)return {label:'UNAVAILABLE',reason:'HTTP '+response.status};
  if(!object(body))return {label:'UNAVAILABLE',reason:'Missing or malformed payload'};
  if(body.status===undefined){
    if(EXPECTED_SOURCE)return {label:'UNAVAILABLE',reason:'Missing proxy state'};
    return {label:'REACHABLE',reason:'Response only; evidence state unverified'};
  }
  if(typeof body.status!=='string'||!['REACHABLE','LIVE','SNAPSHOT','CACHED','PARTIAL','STALE','UNAVAILABLE','SAMPLE','MODELED'].includes(body.status))
    return {label:'UNAVAILABLE',reason:'Unknown proxy state'};
  if(EXPECTED_SOURCE&&body.source!==EXPECTED_SOURCE)
    return {label:'UNAVAILABLE',reason:'Source mismatch'};
  if(!Number.isInteger(body.http_status)||body.http_status<200||body.http_status>=300||body.status==='UNAVAILABLE')
    return {label:'UNAVAILABLE',reason:'Upstream unavailable'};
  if(!object(body.data))return {label:'UNAVAILABLE',reason:'Missing upstream data'};
  if(body.data.status==='UNAVAILABLE'||body.data.state==='UNAVAILABLE'||body.data.ok===false)
    return {label:'UNAVAILABLE',reason:'Upstream data unavailable'};
  if(VERTICAL==='finance'&&(body.status!=='SNAPSHOT'||body.data.ok!==true))
    return {label:'UNAVAILABLE',reason:'Finance snapshot is not accepted'};
  if(body.source_revision!==undefined||body.data.source_revision!==undefined){
    const revision=/^[0-9a-f]{40}$/;
    if(!revision.test(body.data.source_revision)||
       (body.source_revision!==undefined&&(!revision.test(body.source_revision)||body.source_revision!==body.data.source_revision))||
       (body.source_revision===undefined&&VERTICAL!=='finance'))
      return {label:'UNAVAILABLE',reason:'Source revision mismatch'};
  }
  if(VERTICAL==='finance'&&body.status==='SNAPSHOT'&&!/^[0-9a-f]{40}$/.test(body.data.source_revision))
    return {label:'UNAVAILABLE',reason:'Missing finance source revision'};
  const mode=[body.status,body.data_kind,body.truth_label,body.mode,
    body.data.status,body.data.state,body.data.data_kind,body.data.truth_label,body.data.mode]
    .filter(value=>typeof value==='string').map(value=>value.toUpperCase());
  if(mode.includes('SAMPLE')||mode.includes('FIXTURE'))return {label:'SAMPLE',reason:'Sample evidence'};
  if(mode.includes('MODELED'))return {label:'MODELED',reason:'Modeled evidence'};
  let sourceStale=false;
  const sourceSpecs=VERTICAL==='terra'?[['hpd_litigations',900],['dob_violations',900],['rates',3600]]:
    VERTICAL==='counsel'?[['federal_register',600],['court_filings',900]]:null;
  if(sourceSpecs){
    if(body.data.vertical!==(VERTICAL==='terra'?'realestate':'legal'))
      return {label:'UNAVAILABLE',reason:'Vertical mismatch'};
    const sources=sourceSpecs.map(([key])=>body.data[key]);
    if(sources.some(source=>!object(source)||!object(source.freshness)))
      return {label:'UNAVAILABLE',reason:'Missing source evidence'};
    let available=0,stale=false;
    for(let index=0;index<sources.length;index++){
      const source=sources[index];
      const freshness=source.freshness,status=String(freshness.status||'').toLowerCase();
      if(!['live','cached','stale','unavailable'].includes(status))
        return {label:'UNAVAILABLE',reason:'Unknown source freshness'};
      if(status==='unavailable'){
        if(source.value!==null)return {label:'UNAVAILABLE',reason:'Contradictory source evidence'};
        continue;
      }
      if(!object(source.value)||!Number.isFinite(freshness.fetched_at)||freshness.fetched_at<=0||freshness.fetched_at>Date.now()/1000+60)
        return {label:'UNAVAILABLE',reason:'Missing or invalid observation clock'};
      available++;
      if(status!=='live'||Date.now()/1000-freshness.fetched_at>sourceSpecs[index][1])stale=true;
    }
    if(!available)return {label:'UNAVAILABLE',reason:'No available source evidence'};
    if(available<sources.length)
      return {label:'PARTIAL',reason:stale?'Some sources unavailable; others cached or stale':'Some sources unavailable'};
    sourceStale=stale;
  }
  if(body.status==='PARTIAL'||body.data.status==='PARTIAL')
    return {label:'PARTIAL',reason:'Partially available upstream data'};
  if(sourceStale||body.status==='STALE'||body.status==='CACHED'||body.data.status==='STALE'||body.data.status==='CACHED')
    return {label:'STALE',reason:'Stale upstream data'};
  return {label:'REACHABLE',reason:'Upstream response; domain result unverified'};
}
async function probe(){
  if(!EP){pill.textContent='DECLARED - NO PUBLIC PROBE';out.textContent='No endpoint is declared.';return}
  try{
    const response=await fetch(EP,{method:'GET',cache:'no-store',headers:{'Accept':'application/json'}});
    const contentType=response.headers.get('content-type')||'';
    let body;
    if(contentType.includes('json'))body=await response.json();
    else if(EXPECTED_SOURCE)body=null;
    else body={content_type:contentType,text:(await response.text()).slice(0,1200)};
    const state=stateFor(response,body);
    pill.textContent=state.label;
    pill.className='pill '+(state.label==='UNAVAILABLE'?'unavailable':'');
    out.textContent=state.reason+'\n'+JSON.stringify(body,null,2).slice(0,4000);
  }catch(error){
    pill.textContent='UNAVAILABLE';pill.className='pill unavailable';out.textContent=String(error);
  }
}
probe();
"""


LANDING = """<!doctype html>
<html lang="en" data-szl-vertical-forge="0.2.2"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="dark"><title>{name} — SZL Holdings</title><meta name="description" content="{tagline}">
<style>
:root{{--bg:#070b12;--ink:#e6edfb;--muted:#9fb0cf;--faint:#6b7a99;--line:rgba(140,170,220,.14);--teal:#3af4c8;--blue:#5b8dee;--violet:#8a6bff;--amber:#d4a444;--red:#fb7185}}
*{{box-sizing:border-box;min-inline-size:0}}html{{overflow-x:clip}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,"Segoe UI",Roboto,sans-serif}}
body::before{{content:"";position:fixed;inset:-30%;z-index:-1;pointer-events:none;filter:blur(6px);animation:drift 24s ease-in-out infinite alternate;background:radial-gradient(45% 40% at 18% 12%,rgba(58,244,200,.10),transparent 60%),radial-gradient(50% 45% at 85% 8%,rgba(91,141,238,.12),transparent 60%),radial-gradient(55% 50% at 70% 95%,rgba(138,107,255,.12),transparent 60%)}}
@keyframes drift{{from{{transform:translate3d(-2%,-1%,0)}}to{{transform:translate3d(2%,1%,0) scale(1.06)}}}}main{{max-width:980px;margin:auto;padding:64px 20px 80px}}.kicker{{font-size:11px;letter-spacing:.4em;text-transform:uppercase;color:var(--faint)}}
h1{{font-size:clamp(34px,7vw,64px);line-height:1.02;margin:14px 0;font-weight:850;letter-spacing:-.5px;overflow-wrap:anywhere}}.grad{{background:linear-gradient(100deg,var(--teal),var(--blue) 45%,var(--violet));-webkit-background-clip:text;background-clip:text;color:transparent}}.lede{{max-width:62ch;color:var(--muted);font-size:17px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0}}.chip{{font-size:11px;font-weight:600;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:6px 12px;background:rgba(255,255,255,.028)}}.chip b{{color:var(--ink)}}.actions{{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}}.button{{display:inline-flex;align-items:center;min-height:44px;border:1px solid var(--line);border-radius:9px;padding:8px 14px;text-decoration:none;font-weight:700}}.button:focus-visible,a:focus-visible{{outline:3px solid var(--teal);outline-offset:3px}}
.pill{{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:7px 12px;font:700 10.5px ui-monospace,monospace;border:1px solid var(--line);color:var(--amber)}}.pill::before{{content:"";width:7px;height:7px;border-radius:50%;background:currentColor;box-shadow:0 0 12px currentColor}}.pill.unavailable{{color:var(--red)}}
.panel{{border:1px solid var(--line);border-radius:16px;padding:22px;margin-top:26px;background:linear-gradient(145deg,rgba(12,24,39,.9),rgba(8,15,27,.9))}}.panel h2{{font-size:13px;letter-spacing:.28em;text-transform:uppercase;color:var(--teal);margin:0 0 10px}}a{{color:var(--blue);overflow-wrap:anywhere}}code{{background:rgba(255,255,255,.06);border-radius:6px;padding:1px 6px;font-size:12.5px;color:var(--teal)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin-top:10px}}.asset{{border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:12px;color:var(--muted)}}.asset b{{display:block;color:var(--ink);font:700 10px ui-monospace,monospace;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}}.asset i{{color:var(--faint)}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;max-height:360px;overflow:auto}}footer{{margin-top:34px;color:var(--faint);font-size:12px;border-top:1px solid var(--line);padding-top:16px}}
@media(prefers-reduced-motion:reduce){{body::before{{animation:none}}}}@media(forced-colors:active){{*{{forced-color-adjust:auto}}}}
</style></head><body><main>
<div class="kicker">SZL Holdings &middot; {domain}</div><h1>{name} <span class="grad">— evidence before inference.</span></h1><p class="lede">{tagline}.</p>
<div class="chips"><span class="chip">Doctrine <b>v11</b></span><span class="chip">&Lambda; = Conjecture 1 &middot; advisory</span><span class="chip">receipt chain <b>SHA-256</b></span><span class="chip">widget <b>{widget}</b></span></div>
<div class="actions"><a class="button" href="/panels">Open governed workbench</a><a class="button" href="/build-receipt.json">Verify build receipt</a></div><span class="pill" id="livepill">PROBING</span>
<div class="panel"><h2>Runtime observation</h2><p style="color:var(--muted);font-size:13px">This read-only probe reports the upstream evidence state. Reachability alone is not a domain measurement or authorization.</p><pre id="demodata">waiting for probe…</pre></div>
<div class="panel"><h2>Estate wiring</h2><div class="grid"><div class="asset"><b>Repos</b>{repos}</div><div class="asset"><b>Kernels</b>{kernels}</div><div class="asset"><b>Models</b>{models}</div><div class="asset"><b>Datasets</b>{datasets}</div><div class="asset"><b>Lineage</b>Field leader: {leader} — {job}. <b>SZL adaptation:</b> {tweak}. <b>Primary sources:</b> {lineage_sources}. <i>Take the job, never proprietary code.</i></div></div></div>
<footer>Generated by szl-vertical-forge v0.2.2 &middot; config receipt <code>{config_receipt}</code> &middot; verify the committed receipt before deployment</footer>
</main><script>
{probe_script}
</script></body></html>
"""


def _links(items: Iterable[str], base: str) -> str:
    rendered = []
    for item in items:
        href = base + quote(item, safe="/-._~")
        rendered.append(
            f'<a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(item)}</a>'
        )
    return ", ".join(rendered) or "none declared"


def _source_links(items: Iterable[str]) -> str:
    rendered = []
    for position, item in enumerate(items, start=1):
        rendered.append(
            f'<a href="{html.escape(item, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">source {position}</a>'
        )
    return ", ".join(rendered)


def render_vertical(vertical: dict[str, Any]) -> str:
    lineage = vertical["lineage"]
    config_receipt = sha256_bytes(canonical_json(vertical).encode("utf-8"))
    endpoint_js = json.dumps(
        PROBE_ENDPOINTS.get(vertical["id"], vertical.get("endpoint")),
        ensure_ascii=False,
    ).replace(
        "<", "\\u003c"
    )
    source_js = json.dumps(PROBE_SOURCES.get(vertical["id"]), ensure_ascii=False)
    probe_script = (
        f"const EP={endpoint_js},EXPECTED_SOURCE={source_js},"
        f"VERTICAL={json.dumps(vertical['id'])};\n" + PROBE_SCRIPT
    )
    replacements = {
        "name": html.escape(vertical["name"], quote=True),
        "domain": html.escape(vertical["domain"], quote=True),
        "tagline": html.escape(vertical["tagline"], quote=True),
        "widget": html.escape(vertical["widget"], quote=True),
        "repos": _links(vertical["repos"], "https://github.com/szl-holdings/"),
        "kernels": _links(vertical["kernels"], "https://huggingface.co/SZLHOLDINGS/"),
        "models": _links(vertical["models"], "https://huggingface.co/SZLHOLDINGS/"),
        "datasets": _links(
            vertical["datasets"], "https://huggingface.co/datasets/SZLHOLDINGS/"
        ),
        "leader": html.escape(lineage["leader"]),
        "job": html.escape(lineage["job"]),
        "tweak": html.escape(lineage["tweak"]),
        "lineage_sources": _source_links(lineage["sources"]),
        "config_receipt": config_receipt[:16],
        "probe_script": probe_script,
    }
    # Interpret template escapes once; substituted text is never templated again.
    return LANDING.format_map(replacements)


def _receipt_for(index_files: dict[str, bytes], config_sha256: str) -> dict[str, Any]:
    previous = ZERO_HASH
    events: list[dict[str, Any]] = []
    for path, content in sorted(index_files.items()):
        event = {
            "artifact_sha256": sha256_bytes(content),
            "kind": "generated-index",
            "path": path,
            "prev_hash": previous,
        }
        event["chain_hash"] = sha256_bytes(canonical_json(event).encode("utf-8"))
        previous = event["chain_hash"]
        events.append(event)
    header = {
        "schema": RECEIPT_SCHEMA,
        "generator": f"szl-vertical-forge/{VERSION}",
        "algorithm": RECEIPT_ALGORITHM,
        "genesis": ZERO_HASH,
        "config_sha256": config_sha256,
        "vertical_count": len(index_files),
    }
    return {
        **header,
        "events": events,
        "chain_tip": previous,
        "master_hash": _master_hash(header, previous),
    }


def _master_hash(header: dict[str, Any], chain_tip: str) -> str:
    """Bind the canonical receipt header and the event-chain tip together.

    The header (generator, algorithm, genesis, config digest, count) is part of
    the verified authority: mutating any header field changes the master hash.
    """
    return sha256_bytes(
        canonical_json({"chain_tip": chain_tip, "header": header}).encode("utf-8")
    )


def verify_receipt(
    receipt: Any, expected_config_sha256: str | None = None
) -> dict[str, Any]:
    """Recompute the receipt chain and its bound header.

    ``expected_config_sha256`` is an optional independently supplied config
    authority; when given, the receipt's config digest must equal it.
    """
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        return {"state": "INVALID", "detail": "receipt schema mismatch"}
    missing = [field for field in HEADER_FIELDS if field not in receipt]
    if missing:
        return {"state": "INVALID", "detail": "receipt header missing: " + ", ".join(missing)}
    if receipt.get("algorithm") != RECEIPT_ALGORITHM:
        return {"state": "INVALID", "detail": "unsupported receipt algorithm"}
    if receipt.get("genesis") != ZERO_HASH:
        return {"state": "INVALID", "detail": "receipt genesis mismatch"}
    generator = receipt.get("generator")
    if not isinstance(generator, str) or not GENERATOR_RE.fullmatch(generator):
        return {"state": "INVALID", "detail": "receipt generator not recognised"}
    config_sha256 = receipt.get("config_sha256")
    if not isinstance(config_sha256, str) or not HEX64_RE.fullmatch(config_sha256):
        return {"state": "INVALID", "detail": "receipt config digest malformed"}
    if expected_config_sha256 is not None and config_sha256 != expected_config_sha256:
        return {"state": "INVALID", "detail": "receipt config digest does not match expected authority"}
    previous = receipt["genesis"]
    events = receipt.get("events")
    if not isinstance(events, list) or not events:
        return {"state": "INVALID", "detail": "receipt events missing"}
    for position, event in enumerate(events):
        if not isinstance(event, dict) or event.get("prev_hash") != previous:
            return {
                "state": "INVALID",
                "detail": f"chain link mismatch at event {position}",
            }
        candidate = {key: value for key, value in event.items() if key != "chain_hash"}
        calculated = sha256_bytes(canonical_json(candidate).encode("utf-8"))
        if event.get("chain_hash") != calculated:
            return {
                "state": "INVALID",
                "detail": f"chain hash mismatch at event {position}",
            }
        previous = calculated
    if receipt.get("chain_tip") != previous:
        return {"state": "INVALID", "detail": "chain tip mismatch"}
    if receipt.get("vertical_count") != len(events):
        return {"state": "INVALID", "detail": "vertical count mismatch"}
    header = {field: receipt[field] for field in HEADER_FIELDS}
    master_hash = _master_hash(header, previous)
    if receipt.get("master_hash") != master_hash:
        return {"state": "INVALID", "detail": "master hash mismatch"}
    return {"state": "VERIFIED", "events": len(events), "master_hash": master_hash}


def forge(verticals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    selected = load_verticals() if verticals is None else verticals
    errors: dict[str, list[str]] = {}
    identifiers: set[str] = set()
    for position, vertical in enumerate(selected):
        item_errors = validate_vertical(vertical)
        identifier = (
            vertical.get("id", f"position-{position}")
            if isinstance(vertical, dict)
            else f"position-{position}"
        )
        if identifier in identifiers:
            item_errors.append("id must be unique")
        identifiers.add(str(identifier))
        if item_errors:
            errors[str(identifier)] = item_errors
    if errors:
        return {"state": "INVALID", "errors": errors}
    if not selected:
        return {
            "state": "INVALID",
            "errors": {"verticals": ["at least one vertical is required"]},
        }

    index_files = {
        f"{item['id']}/index.html": render_vertical(item).encode("utf-8")
        for item in selected
    }
    config_sha256 = sha256_bytes(canonical_json(selected).encode("utf-8"))
    receipt = _receipt_for(index_files, config_sha256)
    event_by_path = {event["path"]: event for event in receipt["events"]}
    files = dict(index_files)
    for item in selected:
        index_path = f"{item['id']}/index.html"
        artifact_receipt = {
            "schema": ARTIFACT_SCHEMA,
            "generator": receipt["generator"],
            "vertical": item["id"],
            "config_sha256": sha256_bytes(canonical_json(item).encode("utf-8")),
            "fleet_config_sha256": config_sha256,
            "fleet_master_hash": receipt["master_hash"],
            "chain_event": event_by_path[index_path],
        }
        files[f"{item['id']}/build-receipt.json"] = (
            json.dumps(artifact_receipt, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode("utf-8")
    files["RECEIPT.json"] = (
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return {
        "state": "MEASURED_LOCAL_BUILD",
        "count": len(selected),
        "generated": sorted(index_files),
        "files": files,
        "receipt": receipt,
        "master_hash": receipt["master_hash"],
    }


def _safe_destination(root: Path, relative: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve()
    if root_resolved != candidate and root_resolved not in candidate.parents:
        raise ValueError(f"output escaped destination: {relative}")
    return candidate


def write_output(
    result: dict[str, Any], output_dir: str | os.PathLike[str]
) -> dict[str, Any]:
    if result.get("state") != "MEASURED_LOCAL_BUILD" or not isinstance(
        result.get("files"), dict
    ):
        return {"state": "INVALID", "detail": "forge result is not writable"}
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for relative, content in sorted(result["files"].items()):
        target = _safe_destination(root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_bytes(content)
        os.replace(temporary, target)
        written.append(relative)
    return {"state": "WRITTEN", "files": written, "output_dir": str(root.resolve())}


def verify_output(
    result: dict[str, Any], output_dir: str | os.PathLike[str]
) -> dict[str, Any]:
    if result.get("state") != "MEASURED_LOCAL_BUILD" or not isinstance(
        result.get("files"), dict
    ):
        return {"state": "INVALID", "detail": "forge result is not verifiable"}
    root = Path(output_dir)
    missing: list[str] = []
    mismatched: list[str] = []
    for relative, expected in sorted(result["files"].items()):
        target = _safe_destination(root, relative)
        if not target.is_file():
            missing.append(relative)
        elif target.read_bytes() != expected:
            mismatched.append(relative)
    chain = verify_receipt(
        result["receipt"], expected_config_sha256=result["receipt"].get("config_sha256")
    )
    state = (
        "VERIFIED_LOCAL_ARTIFACTS"
        if not missing and not mismatched and chain["state"] == "VERIFIED"
        else "INVALID"
    )
    return {
        "state": state,
        "files_checked": len(result["files"]),
        "missing": missing,
        "mismatched": mismatched,
        "chain": chain,
        "master_hash": result["master_hash"],
    }


def _select(
    verticals: list[dict[str, Any]], requested: list[str]
) -> list[dict[str, Any]]:
    if not requested:
        return verticals
    by_id = {item.get("id"): item for item in verticals if isinstance(item, dict)}
    unknown = sorted(set(requested) - set(by_id))
    if unknown:
        raise ValueError("unknown vertical(s): " + ", ".join(unknown))
    return [by_id[identifier] for identifier in requested]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate or verify deterministic vertical artifacts"
    )
    parser.add_argument(
        "command", nargs="?", choices=("generate", "verify"), default="generate"
    )
    parser.add_argument("--output-dir", default="dist")
    parser.add_argument(
        "--vertical",
        action="append",
        default=[],
        help="limit output to one or more audited IDs",
    )
    args = parser.parse_args(argv)
    try:
        selected = _select(load_verticals(), args.vertical)
        result = forge(selected)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "INVALID", "detail": str(exc)}, sort_keys=True))
        return 2
    if result["state"] != "MEASURED_LOCAL_BUILD":
        print(json.dumps(result, sort_keys=True))
        return 2
    if args.command == "generate":
        write_result = write_output(result, args.output_dir)
        if write_result["state"] != "WRITTEN":
            print(json.dumps(write_result, sort_keys=True))
            return 2
    verification = verify_output(result, args.output_dir)
    print(
        json.dumps(
            {
                "state": verification["state"],
                "vertical_count": result["count"],
                "files_checked": verification["files_checked"],
                "master_hash": result["master_hash"],
                "output_dir": str(Path(args.output_dir).resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if verification["state"] == "VERIFIED_LOCAL_ARTIFACTS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
