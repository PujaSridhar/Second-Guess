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

RESOLVER_PROMPT = f"""You check whether a commitment has been invalidated by
something that happened in the public world. Today is {AS_OF}.

Search the web for the named entity. Decide ONE of:
  "BROKEN"  - the entity no longer exists or is unusable, so the commitment
              cannot be delivered as stated (e.g. a sunset API)
  "OK"      - the entity changed but the commitment still stands
              (e.g. the company was acquired but the product runs)

Be strict. Most changes do not break a commitment. Return ONLY:
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
        tools = client.list_tools_sync()
        reply = agent(RESOLVER_PROMPT, tools=tools)(
            f'Entity: "{entity}"\nCommitment: "{commitment_text}"\n\n'
            "Is this commitment still deliverable?"
        )
    return parse_structured(str(reply))


def resolve_with_fallback(entity, commitment_text):
    """Try live first. Fall back to the cached fixture only if that fails.

    If you fall back during the demo, SAY SO OUT LOUD. The whole claim is that
    these facts are unknowable from the personal corpus.
    """
    try:
        out = resolve(entity, commitment_text)
        out["_live"] = True
        return out
    except Exception as exc:
        cache = json.loads((FIXTURES / "web_cache.json").read_text())
        hit = cache["entities"].get(entity)
        if not hit:
            raise
        return {
            "status": BROKEN if hit["breaks_commitment"] else OK,
            "finding": hit["detail"],
            "source_url": hit["source_url"],
            "event_date": hit.get("sunset_date") or hit.get("announced"),
            "_live": False,
            "_fallback_reason": str(exc),
        }
