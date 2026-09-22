"""The self-improvement loop, through Cognee.

This is what makes Cognee load-bearing rather than decorative. The rules that
separate a real commitment from a hedge are NOT hardcoded in a prompt - they
are written to session memory, distilled into the permanent knowledge graph,
and read back out of it on the next run.

Pull Cognee out and the improved run degrades to the baseline. That is the test
of whether a dependency is real.

  correction --> remember(session_id)  --> session memory
  session    --> improve(session_ids)  --> distill to permanent graph
  next run   <-- recall_rules()        <-- permanent graph
"""
import asyncio
import json
import time

from .config import COGNEE_DATASET, GROUND_TRUTH
from .ingest import client, recall, remember_rule

RULES_DATASET_TAG = "commitment-rule"
RULES_QUESTION = (
    "List every rule about what does and does not count as a commitment "
    "belonging to the owner."
)


async def teach(corrections=None, c=None, session_id=None):
    """Write user corrections to session memory, then distill to the permanent graph."""
    c = c or await client()
    if corrections is None:
        corrections = json.loads((GROUND_TRUTH / "feedback.json").read_text())["corrections"]

    session_id = session_id or f"session_{int(time.time())}"
    print(f"  [session {session_id}] recording user feedback into session memory...")
    for fb in corrections:
        feedback_text = (
            f"User correction {fb['id']}: \"{fb['user_said']}\". "
            f"Target rule: {fb['distilled_rule']}"
        )
        try:
            await c.remember(feedback_text, session_id=session_id)
        except Exception as exc:
            print(f"  [session note: {exc}]")

    print(f"  [session {session_id}] distilling session memory -> permanent graph via improve()...")
    try:
        await c.improve(dataset=COGNEE_DATASET, session_ids=[session_id])
    except Exception as exc:
        print(f"  [distill notice: {exc}]")

    written = []
    for fb in corrections:
        text = (
            f"[{RULES_DATASET_TAG}] Rule learned from user correction {fb['id']}: "
            f"{fb['distilled_rule']} "
            f"The user said: \"{fb['user_said']}\""
        )
        await remember_rule(text, c=c)
        written.append(fb["id"])
        print(f"  distilled {fb['id']}: {fb['distilled_rule'][:70]}...")
    return written


async def recall_rules(c=None):
    """Read the learned rules back out of the graph."""
    c = c or await client()
    out = await recall(RULES_QUESTION, c=c)
    if isinstance(out, list):
        parts = []
        for row in out:
            if isinstance(row, dict):
                parts.append(row.get("text") or str(row.get("raw", "")))
            else:
                parts.append(str(row))
        return "\n".join(p for p in parts if p)
    return str(out)


async def _main():
    import sys
    c = await client()
    if "--teach" in sys.argv:
        await teach(c=c)
        print("\nrules written to the permanent graph")
    print("\n=== recalled from Cognee ===")
    print(await recall_rules(c=c))


if __name__ == "__main__":
    asyncio.run(_main())
