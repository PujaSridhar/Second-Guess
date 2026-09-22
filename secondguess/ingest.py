"""Cognee ingest.

Permanent graph  = the corpus and the distilled rules (no session_id).
Session memory   = one run's observations and lookups (session_id set).

Verified against the Cognee docs for remember():
    await cognee.remember(data, dataset_name=..., session_id=None,
                          self_improvement=True, run_in_background=False)
File paths are passed as strings - open() handles are rejected.
"""
import asyncio

from .config import COGNEE_DATASET, DATA
from .extract import corpus


async def ingest_corpus():
    import cognee
    paths = []
    for sub in ("email", "slack", "meetings"):
        paths += [str(p) for p in sorted((DATA / sub).glob("*.md"))]
    paths.append(str(DATA / "calendar" / "calendar.json"))
    result = await cognee.remember(paths, dataset_name=COGNEE_DATASET)
    return result


async def remember_session(text, session_id):
    """Per-run observation. self_improvement bridges it to the permanent graph."""
    import cognee
    return await cognee.remember(text, session_id=session_id, self_improvement=True)


async def remember_rule(rule_text):
    """Distil a correction into the permanent graph - no session_id."""
    import cognee
    return await cognee.remember(rule_text, dataset_name=COGNEE_DATASET)


async def recall(question):
    import cognee
    return await cognee.recall(query_text=question, datasets=[COGNEE_DATASET])


if __name__ == "__main__":
    print(asyncio.run(ingest_corpus()))
