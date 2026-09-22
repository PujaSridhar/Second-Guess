#!/usr/bin/env python3
"""Render the dashboard from a run file. No content is written by hand.

    python3 scripts/dashboard.py runs/improved.json runs/baseline.json -o dashboard.html

Every commitment, quote, source path, URL and draft on the page comes out of the
JSON the pipeline produced. Re-run the pipeline, re-run this, and the page
changes. That is the difference between a report and a mockup.
"""
import argparse
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.score import score  # noqa: E402

CLASS = {"BROKEN": "broken", "AT_RISK": "risk", "OK": "ok"}
LABEL = {"BROKEN": "BROKEN", "AT_RISK": "AT RISK", "OK": "OK"}
ORDER = {"BROKEN": 0, "AT_RISK": 1, "OK": 2}


def e(x):
    return html.escape(str(x if x is not None else ""))


def ev_row(key, value, mono_class="path"):
    return (f'<div class="evrow"><div class="evk">{e(key)}</div>'
            f'<div class="{mono_class} mono">{value}</div></div>')


def render_commitment(c):
    st = c.get("status", "OK")
    cls = CLASS.get(st, "ok")
    due = c.get("due_date") or "no date"
    rows = []
    if c.get("quote"):
        rows.append(ev_row("Said", e(c["quote"]), "quote"))
    for src in (c.get("sources") or [c.get("source")]):
        if src:
            rows.append(ev_row("Source", e(src)))
    web = c.get("web") or {}
    if web:
        bits = []
        if web.get("source_url"):
            u = e(web["source_url"])
            bits.append(f'<a href="{u}">{u}</a>')
        else:
            bits.append(e(web.get("finding", "")))
        if web.get("event_date"):
            bits.append(f'· event {e(web["event_date"])}')
        if web.get("_live"):
            bits.append('<span class="live">LIVE</span>')
        rows.append(ev_row("Web", " ".join(bits)))
    if c.get("suggested_date"):
        rows.append(ev_row("Next free", e(c["suggested_date"])))

    draft = ""
    d = c.get("draft") or {}
    if d.get("body"):
        draft = f'''<div class="draft"><div class="dlab">Drafted follow-up</div>
      <div class="dmeta"><b>To</b> {e(d.get("to"))} &nbsp;·&nbsp; <b>Subject</b> {e(d.get("subject"))}</div>
      <div class="dbody">{e(d["body"])}</div>
      <div class="unsent">Not sent. Drafts are shown for a human to read first.</div></div>'''

    return f'''<div class="row {cls}">
    <div class="rhead"><span class="pill {cls}">{LABEL.get(st, e(st))}</span>
      <span class="title">{e(c.get("description"))}</span>
      <span class="due mono">{e(due)}</span></div>
    <div class="owed">owed to {e(c.get("owed_to") or "—")}</div>
    <p class="why">{e(c.get("why"))}</p>
    <div class="ev">{"".join(rows)}</div>
    {draft}
  </div>'''


def build(run_path, baseline_path, template):
    run = json.loads(Path(run_path).read_text())
    commitments = sorted(run["commitments"], key=lambda c: ORDER.get(c.get("status"), 9))

    cur = score(run_path)
    base = score(baseline_path) if baseline_path else None

    counts = {}
    for c in commitments:
        counts[c.get("status")] = counts.get(c.get("status"), 0) + 1
    summary = (f'{len(commitments)} open · {counts.get("AT_RISK", 0)} at risk '
               f'· {counts.get("BROKEN", 0)} broken')

    def delta(key):
        if not base:
            return "&nbsp;"
        return f'{base[key]:.2f} baseline'

    f1d = (f'<span class="up">+{cur["f1"]-base["f1"]:.2f} vs {base["f1"]:.2f}</span>'
           if base else "&nbsp;")
    gold = len(json.loads((ROOT / "ground_truth" / "commitments.json").read_text())["commitments"])
    traps = len(json.loads((ROOT / "ground_truth" / "commitments.json").read_text())["traps"])

    return (template
            .replace("{{SUMMARY}}", summary)
            .replace("{{PRECISION}}", f'{cur["precision"]:.2f}')
            .replace("{{PRECISION_BASE}}", delta("precision"))
            .replace("{{RECALL}}", f'{cur["recall"]:.2f}')
            .replace("{{RECALL_BASE}}", delta("recall"))
            .replace("{{F1}}", f'{cur["f1"]:.2f}')
            .replace("{{F1_DELTA}}", f1d)
            .replace("{{LINT}}", f'{cur["lint_accuracy"]:.2f}')
            .replace("{{GOLD}}", str(gold))
            .replace("{{TRAPS}}", f"+{traps} decoys")
            .replace("{{ROWS}}", "\n".join(render_commitment(c) for c in commitments)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("baseline", nargs="?")
    ap.add_argument("-o", "--out", default=str(ROOT / "dashboard.html"))
    ap.add_argument("-t", "--template", default=str(ROOT / "scripts" / "dashboard_template.html"))
    a = ap.parse_args()
    out = build(a.run, a.baseline, Path(a.template).read_text())
    Path(a.out).write_text(out)
    print(f"wrote {a.out} from {a.run}")
