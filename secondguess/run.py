"""The whole pipeline: extract -> lint -> resolve -> verdicts.

Division of labour, deliberately:
  LLM      proposes commitments and names external entities.
  Python   decides every verdict. The model never writes a status.
"""
import argparse
import json

from .config import AT_RISK, BROKEN, OK, RUNS
from .extract import extract
from .closure import is_closed
from .lint_calendar import busy_days, check as calendar_check
from .llm import agent, parse_structured

ENTITY_PROMPT = """For each commitment, name the ONE external thing it depends on
- a company, product, API, service or public deadline - that could have changed
out in the world without anyone telling the owner.

Return ONLY a JSON array, same order and length as the input:
  [{"index": 0, "entity": "OpenAI Assistants API"}, {"index": 1, "entity": null}]

Use null when the commitment depends on nothing external. People inside the
owner's own company, or customers/counterparties asking for information, are not external dependencies."""


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


def run(learned=False, use_web=True, force_cache=False, sandbox=True, draft_actions=True):
    commitments = extract(learned=learned)
    busy = busy_days()
    entities = name_entities(commitments) if use_web else {}

    web_results = {}
    if use_web and entities:
        from concurrent.futures import ThreadPoolExecutor
        from .resolve_web import resolve_with_fallback

        def _do_resolve(idx, ent, desc):
            try:
                return idx, resolve_with_fallback(ent, desc, use_cache=force_cache)
            except Exception as exc:
                return idx, {"web_error": str(exc)[:200]}

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [
                pool.submit(_do_resolve, i, entities[i], commitments[i]["description"])
                for i in entities
            ]
            for fut in futures:
                idx, res = fut.result()
                web_results[idx] = res

    for i, c in enumerate(commitments):
        # 0. Already delivered? Applied only when the closure rule is learned.
        if learned:
            closed, reason = is_closed(c)
            if closed:
                c["status"] = "CLOSED"
                c["why"] = reason
                continue

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
        found = web_results.get(i, {})
        if "web_error" in found:
            c["web_error"] = found["web_error"]
            continue

        c["web"] = found

        # A model may report BROKEN simply because it found nothing - absence of
        # evidence read as evidence of absence. A false alarm on a healthy
        # commitment is worse than a miss, so BROKEN is only accepted with
        # positive, citable evidence: a source URL and a dated event. This is a
        # Python gate; the model cannot assert BROKEN on its own say-so.
        if found.get("status") == BROKEN and not (
            found.get("source_url") and found.get("event_date")
        ):
            found["status"] = OK
            found["finding"] = (
                "No positive evidence of a breaking change was found, so the "
                "commitment stands. (Model proposed BROKEN without a dated, "
                "cited source; rejected.)"
            )
            c["web_verdict_rejected"] = True

        # BROKEN outranks everything: an undeliverable promise is not merely at risk.
        if found.get("status") == BROKEN:
            c["status"] = BROKEN
            c["why"] = found.get("finding", "External dependency is gone.")
        elif found.get("status") == "UNVERIFIED":
            c["why"] += " (external check untrusted: " + ", ".join(found.get("_flags", [])) + ")"

    commitments = dedupe(commitments)
    commitments = [c for c in commitments if c.get("status") != "CLOSED"]
    if draft_actions and learned:
        from .act import draft_all
        draft_all(commitments)
    return {"run": "improved" if learned else "baseline", "commitments": commitments}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--learned", action="store_true")
    ap.add_argument("--no-web", action="store_true")
    ap.add_argument("--cached", action="store_true", help="Use cached web fixtures for instant demo execution")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    result = run(learned=a.learned, use_web=not a.no_web, force_cache=a.cached)
    out = a.out or str(RUNS / ("improved.json" if a.learned else "baseline.json"))
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{result['run']}: {len(result['commitments'])} commitments -> {out}\n")
    for c in result["commitments"]:
        mark = {OK: "  ", AT_RISK: "! ", BROKEN: "!!"}.get(c["status"], "? ")
        print(f"{mark}[{c['status']:8}] {c['description'][:64]}")
        print(f"        {c['why'][:150]}")
        d = c.get("draft")
        if d and "body" in d:
            print(f"        DRAFT -> to: {d.get('to')} | {d.get('subject')}")
            for line in d["body"].splitlines():
                if line.strip():
                    print(f"          {line.strip()[:90]}")
