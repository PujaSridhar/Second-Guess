"""The whole pipeline: extract -> lint -> resolve -> verdicts.

Division of labour, deliberately:
  LLM      proposes commitments and names external entities.
  Python   decides every verdict. The model never writes a status.
"""
import argparse
import json

from .config import AT_RISK, BROKEN, OK, RUNS
from .extract import extract
from .lint_calendar import busy_days, check as calendar_check
from .llm import agent, parse_structured

ENTITY_PROMPT = """For each commitment, name the ONE external thing it depends on
- a company, product, API, service or public deadline - that could have changed
out in the world without anyone telling the owner.

Return ONLY a JSON array, same order and length as the input:
  [{"index": 0, "entity": "OpenAI Assistants API"}, {"index": 1, "entity": null}]

Use null when the commitment depends on nothing external. People inside the
owner's own company are not external dependencies."""


def name_entities(commitments):
    listing = "\n".join(f"{i}. {c['description']}" for i, c in enumerate(commitments))
    try:
        rows = parse_structured(str(agent(ENTITY_PROMPT)(listing)))
    except Exception as exc:
        print(f"  entity naming failed ({exc}); skipping web resolution")
        return {}
    # The model sometimes emits bare nulls in the array instead of objects.
    return {r["index"]: r["entity"] for r in rows
            if isinstance(r, dict) and r.get("entity") and "index" in r}


# Severity order: a BROKEN reading of a commitment outranks an OK one.
_SEVERITY = {OK: 0, AT_RISK: 1, BROKEN: 2}


def _tokens(text):
    import re
    stop = {"the", "a", "an", "to", "for", "of", "on", "by", "and", "over", "send"}
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower())
            if w not in stop and len(w) > 2}


def dedupe(commitments, threshold=0.6):
    """Merge commitments describing the same promise.

    The same promise usually appears in two places - a meeting note and the
    Slack message that repeated it - and the model rightly extracts both. Left
    alone they double-count, and worse, one copy can be resolved BROKEN while
    its twin still reads OK. Merging is deterministic: union the sources, keep
    the most severe verdict.
    """
    merged = []
    for c in commitments:
        ct = _tokens(c["description"])
        for m in merged:
            mt = _tokens(m["description"])
            if ct and mt and len(ct & mt) / min(len(ct), len(mt)) >= threshold:
                if _SEVERITY.get(c.get("status"), 0) > _SEVERITY.get(m.get("status"), 0):
                    m.update({k: v for k, v in c.items() if k != "sources"})
                m.setdefault("sources", [m.get("source")])
                if c.get("source") and c["source"] not in m["sources"]:
                    m["sources"].append(c["source"])
                break
        else:
            c.setdefault("sources", [c.get("source")] if c.get("source") else [])
            merged.append(c)
    return merged


def run(learned=False, use_web=True, sandbox=True):
    commitments = extract(learned=learned)
    busy = busy_days()
    entities = name_entities(commitments) if use_web else {}

    for i, c in enumerate(commitments):
        # 1. Availability lint - deterministic, no network.
        status, why, suggested = calendar_check(c, busy)
        c["status"], c["why"] = status, why
        if suggested:
            c["suggested_date"] = suggested

        # 2. External lint - only where there is something external to check.
        entity = entities.get(i)
        if not entity:
            continue
        c["external_entity"] = entity
        from .resolve_web import resolve_with_fallback
        try:
            found = resolve_with_fallback(entity, c["description"])
        except Exception as exc:
            c["web_error"] = str(exc)[:200]
            continue

        c["web"] = found
        # BROKEN outranks everything: an undeliverable promise is not merely at risk.
        if found.get("status") == BROKEN:
            c["status"] = BROKEN
            c["why"] = found.get("finding", "External dependency is gone.")
        elif found.get("status") == "UNVERIFIED":
            c["why"] += " (external check untrusted: " + ", ".join(found.get("_flags", [])) + ")"

    commitments = dedupe(commitments)
    return {"run": "improved" if learned else "baseline", "commitments": commitments}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--learned", action="store_true")
    ap.add_argument("--no-web", action="store_true")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    result = run(learned=a.learned, use_web=not a.no_web)
    out = a.out or str(RUNS / ("improved.json" if a.learned else "baseline.json"))
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{result['run']}: {len(result['commitments'])} commitments -> {out}\n")
    for c in result["commitments"]:
        mark = {OK: "  ", AT_RISK: "! ", BROKEN: "!!"}.get(c["status"], "? ")
        print(f"{mark}[{c['status']:8}] {c['description'][:64]}")
        print(f"        {c['why'][:150]}")
