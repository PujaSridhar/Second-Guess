"""External dependency resolver - Bright Data via MCP, driven by Strands.

Runs over EVERY commitment that names a person, company, product or deadline.
Not one scripted lookup: the demo line is "three commitments had external
dependencies, one was invalidated", and that only holds if this really sweeps.

Verified imports against mcp 2.1.1 / strands-agents 1.56.0.
"""
import json
import os

from mcp import StdioServerParameters, stdio_client
from strands.tools.mcp import MCPClient

from .config import (AS_OF, BRIGHTDATA_MCP_ARGS, BRIGHTDATA_MCP_CMD, BROKEN,
                     FIXTURES, OK)
from .llm import agent, parse_structured
from .sandbox import screen

RESOLVER_PROMPT = f"""You check whether a commitment has been invalidated by
something that happened in the public world. Today is {AS_OF}.

Search the web for the named entity and its current status, deprecation, sunset,
acquisition, or major changes. Do not search for internal tasks or project dates.
Decide ONE of:
  "BROKEN"  - the entity no longer exists or is unusable, so the commitment
              cannot be delivered as stated (e.g. a sunset API)
  "OK"      - the entity changed but the commitment still stands
              (e.g. the company was acquired but the product runs)

Be strict. Most changes do not break a commitment. If you cannot FIND
information about the entity, that is not evidence it is broken - return OK.
Only return BROKEN with a real source_url and a real event_date. Return ONLY:
  {{"status": "BROKEN|OK", "finding": "one sentence", "source_url": "...",
    "event_date": "YYYY-MM-DD or null"}}"""


def mcp_client():
    token = os.environ.get("BRIGHT_DATA_API_KEY") or os.environ.get("BRIGHT_DATA_API_TOKEN")
    if not token:
        raise RuntimeError("BRIGHT_DATA_API_KEY is not set")
    params = StdioServerParameters(
        command=BRIGHTDATA_MCP_CMD,
        args=BRIGHTDATA_MCP_ARGS,
        env={"API_TOKEN": token, "PRO_MODE": "true"},
    )
    return MCPClient(lambda: stdio_client(params))


def resolve(entity, commitment_text):
    """Live lookup. Raises if Bright Data is unreachable - caller decides."""
    client = mcp_client()
    with client:
        all_tools = client.list_tools_sync()
        tools = [t for t in all_tools if getattr(t, "tool_name", "") in ("search_engine", "scrape_as_markdown")]
        a = agent(RESOLVER_PROMPT, tools=tools)
        reply = a(
            f'Entity: "{entity}"\nCommitment: "{commitment_text}"\n\n'
            "Is this commitment still deliverable?"
        )
    parsed = parse_structured(str(reply))

    raw_text = ""
    for msg in getattr(a, "messages", []):
        if isinstance(msg, dict) and msg.get("role") == "tool":
            for part in msg.get("content", []):
                if isinstance(part, dict) and "text" in part:
                    raw_text += part["text"] + "\n"
    if not raw_text and parsed.get("finding"):
        raw_text = parsed["finding"]
    if raw_text:
        try:
            parsed = guard(parsed, raw_text)
        except Exception as exc:
            parsed["_sandbox_error"] = str(exc)[:200]

    return parsed


def _lookup_cache(entity):
    cache = json.loads((FIXTURES / "web_cache.json").read_text())
    entities = cache.get("entities", {})
    if entity in entities:
        return entities[entity]
    ent_lower = entity.lower()
    for k, v in entities.items():
        if ent_lower in k.lower() or k.lower() in ent_lower:
            return v
    return None


def resolve_with_fallback(entity, commitment_text, use_cache=False):
    """Try live first. Fall back to the cached fixture only if that fails.

    If you fall back during the demo, SAY SO OUT LOUD. The whole claim is that
    these facts are unknowable from the personal corpus.
    """
    if not use_cache:
        import concurrent.futures
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(resolve, entity, commitment_text)
                out = future.result(timeout=25)
            out["_live"] = True
            return out
        except Exception as exc:
            fallback_err = exc
    else:
        fallback_err = "cached run requested"

    hit = _lookup_cache(entity)
    if hit:
        return {
            "status": BROKEN if hit["breaks_commitment"] else OK,
            "finding": hit["detail"],
            "source_url": hit["source_url"],
            "event_date": hit.get("sunset_date") or hit.get("announced"),
            "_live": False,
            "_fallback_reason": str(fallback_err),
        }
    return {
        "status": OK,
        "finding": f"No positive evidence of breaking change found for {entity}.",
        "source_url": None,
        "event_date": None,
        "_live": False,
        "_fallback_reason": str(fallback_err),
    }


def guard(finding, raw_scraped_text=None):
    """Refuse to let injected web content soften a verdict.

    A page we scrape is attacker-controlled. The realistic attack here is a page
    asserting "this API was never deprecated" so the resolver downgrades BROKEN
    to OK. So: screen the raw text in the Docker sandbox, and if it carries
    injection markers, the finding may no longer claim everything is fine.

    Deterministic. The model does not get a vote on whether it was manipulated.
    """
    if not raw_scraped_text:
        return finding

    report = screen(raw_scraped_text)
    finding["_screened"] = True
    finding["_flags"] = report["flags"]

    if report["flags"] and finding.get("status") == OK:
        finding["status"] = "UNVERIFIED"
        finding["finding"] = (
            "Source content carried prompt-injection markers "
            f"({', '.join(report['flags'])}); its claim that this commitment is "
            "fine is not trusted. Needs a human look."
        )
    return finding


if __name__ == "__main__":
    import sys
    ent = sys.argv[1] if len(sys.argv) > 1 else "OpenAI Assistants API"
    comm = sys.argv[2] if len(sys.argv) > 2 else "Ship support assistant on Assistants API"
    print(f"Resolving: {ent}...")
    res = resolve_with_fallback(ent, comm)
    print(json.dumps(res, indent=2))

