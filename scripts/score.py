#!/usr/bin/env python3
"""Deterministic scorer for Second Guess.

The LLM extracts commitments. This file decides whether it was right.
No model output is trusted here - every number below is computed in plain Python.

Usage:
    python3 scripts/score.py runs/baseline.json
    python3 scripts/score.py runs/improved.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = json.loads((ROOT / "ground_truth" / "commitments.json").read_text())

STOP = {
    "the", "a", "an", "to", "for", "of", "on", "at", "by", "and", "or", "in",
    "with", "is", "are", "be", "will", "send", "over", "that", "this", "it",
}
MATCH_THRESHOLD = 0.25


def toks(text):
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in STOP and len(w) > 2}


def overlap(a, b):
    """Overlap coefficient - forgiving about length differences in phrasing."""
    ta, tb = toks(a), toks(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def score(pred_path):
    pred = json.loads(Path(pred_path).read_text())
    preds = pred.get("commitments", [])
    gold = GOLD["commitments"]
    traps = GOLD["traps"]

    # Greedy one-to-one assignment, best pairs first.
    pairs = sorted(
        ((overlap(p.get("description"), g["description"]), i, j)
         for i, p in enumerate(preds) for j, g in enumerate(gold)),
        reverse=True,
    )
    p_used, g_used, matched = set(), set(), []
    for s, i, j in pairs:
        if s < MATCH_THRESHOLD or i in p_used or j in g_used:
            continue
        p_used.add(i)
        g_used.add(j)
        matched.append((preds[i], gold[j], s))

    fps = [p for i, p in enumerate(preds) if i not in p_used]
    fns = [g for j, g in enumerate(gold) if j not in g_used]

    tp = len(matched)
    precision = tp / len(preds) if preds else 0.0
    recall = tp / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    lint_ok = [
        (p, g) for p, g, _ in matched
        if (p.get("status") or "").upper() == g["expected_status"]
    ]
    lint_acc = len(lint_ok) / tp if tp else 0.0

    run = pred.get("run", Path(pred_path).stem)
    print(f"\n=== {run} ===")
    print(f"extracted {len(preds)}  |  gold {len(gold)}  |  correct {tp}")
    print(f"precision {precision:.2f}   recall {recall:.2f}   F1 {f1:.2f}")
    print(f"lint accuracy (status correct) {lint_acc:.2f}  [{len(lint_ok)}/{tp}]")

    if fns:
        print("\n  MISSED:")
        for g in fns:
            print(f"    - {g['description']}")

    if fps:
        print("\n  FALSE POSITIVES:")
        for p in fps:
            desc = p.get("description", "")
            hit = max(traps, key=lambda t: overlap(desc, t["text"]), default=None)
            if hit and overlap(desc, hit["text"]) >= MATCH_THRESHOLD:
                print(f"    - {desc}")
                print(f"        fell for trap '{hit['key']}': {hit['reason']}")
            else:
                print(f"    - {desc}  (unrecognized)")

    wrong_status = [(p, g) for p, g, _ in matched
                    if (p.get("status") or "").upper() != g["expected_status"]]
    if wrong_status:
        print("\n  WRONG STATUS:")
        for p, g in wrong_status:
            print(f"    - {g['key']}: said {p.get('status')!r}, expected {g['expected_status']!r}")
            print(f"        {g['why']}")

    print()
    return {"run": run, "precision": precision, "recall": recall,
            "f1": f1, "lint_accuracy": lint_acc}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: score.py runs/<run>.json [runs/<run2>.json ...]")
    results = [score(p) for p in sys.argv[1:]]
    if len(results) > 1:
        a, b = results[0], results[-1]
        print("=== before / after ===")
        for k in ("f1", "lint_accuracy"):
            print(f"{k:>14}: {a[k]:.2f}  ->  {b[k]:.2f}   ({b[k]-a[k]:+.2f})")
        print()
