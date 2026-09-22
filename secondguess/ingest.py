"""Cognee Cloud ingest.

VERIFIED against cognee 1.6.0 and the live hackathon tenant:
  client = await cognee.serve(url=..., api_key=...)   # serve() IS a coroutine
  await client.remember(data, dataset_name=...)       # returns status "running"
  await client.recall(query_text=..., datasets=[...]) # 409 until indexed

Going through the Cloud tenant means the tenant runs graph extraction, so no
LLM_API_KEY is needed locally. It also puts us on the "Best use of Cognee Cloud"
bonus track. Local SDK mode fails without LLM_API_KEY (KeylessExtractorNotInstalled).

CloudClient exposes: add, cognify, forget, improve, list_data, recall,
remember, remember_entry, search, update.
"""
import asyncio
import os

from dotenv import load_dotenv

from .config import COGNEE_DATASET, DATA, ROOT

load_dotenv(ROOT / ".env")


async def client():
    import cognee
    url = os.environ.get("COGNEE_BASE_URL", "").strip('"')
    key = os.environ.get("COGNEE_API_KEY", "").strip('"')
    if not url or not key:
        raise RuntimeError("COGNEE_BASE_URL / COGNEE_API_KEY not set (see .env)")
    return await cognee.serve(url=url, api_key=key)


def source_docs():
    """Every corpus document as (label, text)."""
    docs = []
    for sub in ("email", "slack", "meetings"):
        for path in sorted((DATA / sub).glob("*.md")):
            docs.append((f"{sub}/{path.name}", path.read_text()))
    cal = DATA / "calendar" / "calendar.json"
    docs.append((f"calendar/{cal.name}", cal.read_text()))
    return docs


async def ingest_corpus(c=None, dataset=COGNEE_DATASET):
    """Push the whole corpus into the permanent graph (no session_id)."""
    c = c or await client()
    results = []
    for label, text in source_docs():
        r = await c.remember(f"--- source: {label} ---\n{text}", dataset_name=dataset)
        results.append((label, getattr(r, "status", r)))
        print(f"  ingested {label}")
    return results


async def remember_session(text, session_id, c=None):
    """One run's observation. Stays in session cache until distilled."""
    c = c or await client()
    return await c.remember(text, session_id=session_id)


async def remember_rule(rule_text, c=None, dataset=COGNEE_DATASET):
    """Distil a correction into the permanent graph - no session_id.

    This is the self-improvement write. What goes through here is what makes
    the improved run better than the baseline.
    """
    c = c or await client()
    return await c.remember(rule_text, dataset_name=dataset)


async def recall(question, c=None, dataset=COGNEE_DATASET, attempts=12, delay=10):
    """Recall, retrying while the tenant indexes.

    remember() returns immediately with status "running"; recall 409s until the
    dataset finishes indexing. Poll rather than guessing a sleep.
    """
    c = c or await client()
    last = None
    for i in range(1, attempts + 1):
        try:
            return await c.recall(query_text=question, datasets=[dataset])
        except Exception as exc:
            last = exc
            if i < attempts:
                print(f"  indexing... ({i}/{attempts})")
                await asyncio.sleep(delay)
    raise RuntimeError(f"recall failed after {attempts} attempts: {last}")


async def _main():
    c = await client()
    print("connected to Cognee Cloud")
    await ingest_corpus(c)
    print("\nrecall check:")
    out = await recall("What did Puja promise Marcus Reyes, and when is it due?", c)
    print(out)


if __name__ == "__main__":
    asyncio.run(_main())
