#!/usr/bin/env python3
"""Build the static CFP site from decrypted YAML data.

Reads every `data/*.yaml` file (which must already be decrypted by SOPS),
sorts entries by the nearest upcoming deadline, and emits:

  site/cfps.json   – machine-readable dump of all entries
  site/index.html  – human-readable table

The private curation fields (notes/priority/contacts) are intentionally
DROPPED from the public output. They exist only to help you rank/annotate
entries privately; publishing them would defeat the point of encrypting them.
Set PUBLISH_PRIVATE=1 to include them (e.g. for an internal-only build).
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "site"
PRIVATE_FIELDS = {"notes", "priority", "contacts"}
PUBLISH_PRIVATE = os.environ.get("PUBLISH_PRIVATE") == "1"


def load_entries() -> list[dict]:
    entries = []
    for path in sorted(DATA_DIR.glob("*.yaml")) + sorted(DATA_DIR.glob("*.yml")):
        with path.open() as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            print(f"WARN: {path.name} is not a mapping, skipping", file=sys.stderr)
            continue
        data["_source"] = path.name
        entries.append(data)
    return entries


def next_deadline(entry: dict) -> str:
    """Earliest deadline that is still in the future (falls back to earliest)."""
    deadlines = [d for d in (entry.get("deadlines") or {}).values() if d]
    if not deadlines:
        return "9999-12-31"
    today = date.today().isoformat()
    upcoming = sorted(d for d in deadlines if d >= today)
    return upcoming[0] if upcoming else sorted(deadlines)[-1]


def public_view(entry: dict) -> dict:
    if PUBLISH_PRIVATE:
        return entry
    return {k: v for k, v in entry.items() if k not in PRIVATE_FIELDS}


def render_html(entries: list[dict]) -> str:
    # Data is embedded as JSON and rendered by the browser so the table can be
    # searched, sorted, and filtered without any server or build step.
    data_json = json.dumps(entries, ensure_ascii=False)
    # Escape </script> so the payload can't break out of the script tag.
    data_json = data_json.replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Conference Call for Papers</title>
<style>
  :root {{
    color-scheme: light dark;
    --accent: #4f8cff;
    --soon: #e9a23b;
    --passed: #8a8a8a;
    --chip: color-mix(in srgb, CanvasText 10%, Canvas);
    --border: color-mix(in srgb, CanvasText 18%, Canvas);
    --hover: color-mix(in srgb, CanvasText 6%, Canvas);
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; margin: 2rem auto; max-width: 1120px; padding: 0 1rem; line-height: 1.45; }}
  h1 {{ font-size: 1.6rem; margin-bottom: .2rem; }}
  .sub {{ opacity: .75; margin-top: 0; }}
  .controls {{ display: flex; flex-wrap: wrap; gap: .6rem; align-items: center; margin: 1.2rem 0 .8rem; }}
  .controls input, .controls select {{
    font: inherit; padding: .45rem .6rem; border: 1px solid var(--border);
    border-radius: 8px; background: Canvas; color: CanvasText;
  }}
  #q {{ flex: 1 1 260px; min-width: 200px; }}
  .count {{ opacity: .7; font-size: .9rem; margin-left: auto; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .94rem; }}
  th, td {{ text-align: left; padding: .55rem .65rem; border-bottom: 1px solid var(--border); vertical-align: top; }}
  thead th {{
    position: sticky; top: 0; background: Canvas; cursor: pointer; user-select: none;
    white-space: nowrap; z-index: 1;
  }}
  thead th:hover {{ background: var(--hover); }}
  th .arrow {{ opacity: .4; font-size: .8em; }}
  th[aria-sort="ascending"] .arrow, th[aria-sort="descending"] .arrow {{ opacity: 1; color: var(--accent); }}
  tbody tr:hover {{ background: var(--hover); }}
  .name a {{ color: inherit; font-weight: 600; text-decoration: none; }}
  .name a:hover {{ text-decoration: underline; }}
  .name small {{ display: block; opacity: .6; font-weight: 400; font-size: .82em; }}
  .tier {{ font-weight: 600; white-space: nowrap; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: .3rem; }}
  .chip {{ background: var(--chip); border-radius: 20px; padding: .1rem .55rem; font-size: .8em; white-space: nowrap; }}
  td.dl {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .badge {{ display: inline-block; margin-left: .35rem; padding: .05rem .4rem; border-radius: 6px; font-size: .74em; font-weight: 600; }}
  .badge.soon {{ background: color-mix(in srgb, var(--soon) 25%, Canvas); color: var(--soon); }}
  .badge.passed {{ background: color-mix(in srgb, var(--passed) 22%, Canvas); color: var(--passed); }}
  .tentative {{ color: var(--soon); cursor: help; font-size: .8em; margin-left: .3rem; }}
  .fmt {{ font-size: .82em; opacity: .8; text-transform: capitalize; }}
  footer {{ margin-top: 2rem; font-size: .85rem; opacity: .7; }}
  .empty {{ text-align: center; padding: 2rem; opacity: .6; }}
</style>
</head>
<body>
<h1>AI Conference — Call for Papers</h1>
<p class="sub">Curated deadlines for reputed global AI conferences. Search, sort any column, or filter by tier and topic.</p>

<div class="controls">
  <input id="q" type="search" placeholder="Search conference, topic, or location…" autocomplete="off" aria-label="Search">
  <select id="tier" aria-label="Filter by tier"><option value="">All tiers</option></select>
  <select id="topic" aria-label="Filter by topic"><option value="">All topics</option></select>
  <span class="count" id="count"></span>
</div>

<table>
  <thead>
    <tr>
      <th data-key="name">Conference <span class="arrow">↕</span></th>
      <th data-key="tier">Tier <span class="arrow">↕</span></th>
      <th data-key="topics">Topics <span class="arrow">↕</span></th>
      <th data-key="location">Location <span class="arrow">↕</span></th>
      <th data-key="paper" data-default="asc">Paper deadline <span class="arrow">↕</span></th>
      <th data-key="conf">Conference dates <span class="arrow">↕</span></th>
    </tr>
  </thead>
  <tbody id="rows"></tbody>
</table>
<p class="empty" id="empty" hidden>No conferences match your filters.</p>

<noscript><p>Enable JavaScript for search and sorting, or see the raw <a href="cfps.json">cfps.json</a>.</p></noscript>
<footer>Generated by scripts/build.py · data in <code>data/*.yaml</code> · <a href="cfps.json">cfps.json</a></footer>

<script id="cfp-data" type="application/json">{data_json}</script>
<script>
const DATA = JSON.parse(document.getElementById('cfp-data').textContent);
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const today = new Date(); today.setHours(0,0,0,0);

const paperDeadline = e => (e.deadlines && e.deadlines.full_paper) || '';
const confStart = e => (e.conference_dates && e.conference_dates.start) || '';

function deadlineCell(e) {{
  const d = paperDeadline(e);
  if (!d) return '—';
  const dt = new Date(d + 'T00:00:00');
  const days = Math.round((dt - today) / 86400000);
  const tentative = e.dates_confirmed === false
    ? ' <span class="tentative" title="Estimated from prior editions — verify against the official CFP">≈</span>' : '';
  let badge = '';
  if (days < 0) badge = ' <span class="badge passed">passed</span>';
  else if (days <= 45) badge = ` <span class="badge soon">${{days}}d left</span>`;
  return esc(d) + tentative + badge;
}}

function topicsCell(e) {{
  return '<div class="chips">' + (e.topics || []).map(t => `<span class="chip">${{esc(t)}}</span>`).join('') + '</div>';
}}

function rowHtml(e) {{
  const url = esc(e.cfp_url || e.website || '#');
  const conf = e.conference_dates || {{}};
  const confTxt = conf.start ? `${{esc(conf.start)}} – ${{esc(conf.end || '?')}}` : '—';
  return `<tr>
    <td class="name"><a href="${{url}}" target="_blank" rel="noopener">${{esc(e.name || e.id)}}</a>
      <small>${{esc(e.full_name || '')}} <span class="fmt">${{esc(e.format || '')}}</span></small></td>
    <td class="tier">${{esc(e.tier || '—')}}</td>
    <td>${{topicsCell(e)}}</td>
    <td>${{esc(e.location || '—')}}</td>
    <td class="dl">${{deadlineCell(e)}}</td>
    <td class="dl">${{confTxt}}</td>
  </tr>`;
}}

// --- sorting ---
let sortKey = 'paper', sortDir = 1;
const sortVal = {{
  name: e => (e.name || '').toLowerCase(),
  tier: e => (e.tier || '~'),
  topics: e => (e.topics || []).join(', ').toLowerCase(),
  location: e => (e.location || '~').toLowerCase(),
  paper: e => paperDeadline(e) || '9999',
  conf: e => confStart(e) || '9999',
}};

function apply() {{
  const q = $('#q').value.trim().toLowerCase();
  const tier = $('#tier').value;
  const topic = $('#topic').value;
  let rows = DATA.filter(e => {{
    if (tier && e.tier !== tier) return false;
    if (topic && !(e.topics || []).includes(topic)) return false;
    if (q) {{
      const hay = [e.name, e.full_name, e.location, (e.topics||[]).join(' ')].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }}
    return true;
  }});
  rows.sort((a, b) => {{
    const va = sortVal[sortKey](a), vb = sortVal[sortKey](b);
    return va < vb ? -sortDir : va > vb ? sortDir : 0;
  }});
  $('#rows').innerHTML = rows.map(rowHtml).join('');
  $('#empty').hidden = rows.length > 0;
  $('#count').textContent = `${{rows.length}} of ${{DATA.length}} conferences`;
  document.querySelectorAll('thead th').forEach(th => {{
    th.setAttribute('aria-sort',
      th.dataset.key === sortKey ? (sortDir === 1 ? 'ascending' : 'descending') : 'none');
  }});
}}

// populate filters
[...new Set(DATA.map(e => e.tier).filter(Boolean))].sort()
  .forEach(t => $('#tier').insertAdjacentHTML('beforeend', `<option value="${{esc(t)}}">${{esc(t)}}</option>`));
[...new Set(DATA.flatMap(e => e.topics || []))].sort()
  .forEach(t => $('#topic').insertAdjacentHTML('beforeend', `<option value="${{esc(t)}}">${{esc(t)}}</option>`));

$('#q').addEventListener('input', apply);
$('#tier').addEventListener('change', apply);
$('#topic').addEventListener('change', apply);
document.querySelectorAll('thead th').forEach(th => th.addEventListener('click', () => {{
  const k = th.dataset.key;
  if (sortKey === k) sortDir = -sortDir;
  else {{ sortKey = k; sortDir = 1; }}
  apply();
}}));

apply();
</script>
</body>
</html>
"""


def main() -> int:
    if not DATA_DIR.exists():
        print(f"ERROR: {DATA_DIR} not found", file=sys.stderr)
        return 1
    entries = load_entries()
    entries.sort(key=next_deadline)
    OUT_DIR.mkdir(exist_ok=True)

    public = [public_view(e) for e in entries]
    (OUT_DIR / "cfps.json").write_text(json.dumps(public, indent=2, sort_keys=True))
    (OUT_DIR / "index.html").write_text(render_html(public))
    print(f"Built {len(entries)} CFP entries -> {OUT_DIR}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
