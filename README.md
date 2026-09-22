# Second Guess

**Your commitments live in email and Slack, where no app tracks them. This reads
them, checks them against your calendar and the live web, and tells you which
promise is about to break.**

Built for Battle of the Personal Brains — Cognee x Bright Data x AWS Strands x
Docker, Sept 21 2026.

---

## The problem

The things you're on the hook for don't live in any app. They live in sentences.

*"I'll send you the pricing by Friday."* — that's an email body. Not a task, not
a calendar event, not a ticket. No system owns it, so nothing tracks it, reminds
you, or notices when you can't keep it.

Two ways it goes wrong:

1. **You can't keep it.** You promised Friday in prose. Your calendar says you're
   on PTO Friday. Nothing joins those, because one side is prose and one side is
   structured, and no single app owns both.
2. **The world moved.** You committed to building on an API that got sunset. Your
   notes are perfectly self-consistent and completely dead. Only the public web
   knows.

Either way you find out when the other person asks.

## The design rule

> **If a single application owns both sides of the fact, it is not our problem.**

Calendars already reconcile calendar conflicts. Jira already tracks ticket state.
We only handle conflicts where the two sides live in different systems **and at
least one side is prose.** That is the entire reason a knowledge graph is needed
here: structured synced data doesn't need one, prose does.

## The three operations (Cognee's own framing)

| Op | What we do |
|---|---|
| **Ingest** | Email, Slack, meeting notes, calendar -> commitments as graph entities |
| **Query + self-improve** | "What am I on the hook for?" -> corrections distill into the permanent graph |
| **Lint** | Check every commitment against your availability and against the live web |

Lint is the one almost nobody builds. It has its own section in Cognee's
submission template and it's the third named operation in their Redis hackathon.

## Sponsor roles (each load-bearing)

- **Cognee** — the brain. Commitments as entities, session -> permanent
  distillation, the feedback loop, lint. Remove it and there's no product.
- **Bright Data** — external dependency resolver. Runs over *every* commitment
  naming a person, company, product or deadline. Not one scripted lookup.
- **AWS Strands** — harness. Extraction agent, one resolver agent per commitment
  (parallel, isolated context), action/draft agent. Bright Data ships an official
  MCP server with a documented Strands integration — use that path.
- **Docker** — sandbox for handling untrusted scraped content. First thing to cut.

## Demo data

`data/` is a seeded 10-day corpus: 8 emails, 2 Slack logs, 3 meeting notes, a
calendar. It contains **5 real commitments** and **10 traps** — vague hedges,
other people's action items, an already-completed promise, a marketing CTA, an
external deadline.

Two of the five commitments cannot be judged without the live web:

| Entity | Reality | Effect |
|---|---|---|
| OpenAI Assistants API | Sunset 2026-08-26 | **BROKEN** — the commitment was made after the API died |
| Miro | Being acquired by Bending Spoons, Q4 2026 | **OK** — changed, but not broken |

That contrast is deliberate: it proves the resolver distinguishes *changed* from
*broken* instead of alarming on every external hit.

`fixtures/web_cache.json` holds the same facts as a **fallback only**. Always try
the live lookup first — the point is that these are unknowable from the corpus.
If you fall back during the demo, say so out loud.

## Scoring

`scripts/score.py` is deterministic plain Python. The LLM extracts; this decides
whether it was right. No model output is trusted for any number.

```bash
python3 scripts/score.py runs/baseline.json runs/improved.json
```

Reference arc with the included sample runs:

```
baseline   precision 0.56  recall 1.00  F1 0.71   lint 1.00
improved   precision 1.00  recall 1.00  F1 1.00   lint 1.00

            f1: 0.71  ->  1.00   (+0.29)
 lint_accuracy: 1.00  ->  1.00   (+0.00)
```

It also names which trap each false positive fell for, which demos well.

## Build order (4:00 - 8:15 PM)

| Time | Goal | Cut line if late |
|---|---|---|
| 4:00-5:00 | Ingest corpus into Cognee, extract commitments, score a baseline | — |
| 5:00-6:00 | Lint v1: prose commitments vs calendar (the PTO conflict) | — |
| 6:00-7:00 | Bright Data resolver over external entities (the dead API) | drop parallel, run sequential |
| 7:00-7:45 | Feedback -> distill to permanent graph -> rerun -> score moves | — |
| 7:45-8:15 | Draft the action, freeze, record backup video | show draft, don't send |

**Never cut:** the lint step, or the before/after rerun. Those are the scored parts.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install strands-agents strands-agents-tools 'strands-agents[anthropic]' cognee
npm install -g @brightdata/mcp        # Bright Data MCP runs as a node process
cp .env.example .env                  # then fill it in
```

**Credits**

| Sponsor | How |
|---|---|
| Cognee $50 | promo `PERSONALBRAIN0926` at <https://platform.cognee.ai/billing> |
| Bright Data $50 | promo `cognee50` at <https://brightdata.com?promo=cognee50&hs_signup=1> |
| AWS $25 | <https://pulse.amazon/promotion/ZENKK7R1> |

Discord: `#hackathon-sf-sept-26`

**Verified live against the hackathon tenant (2026-09-21):**

```python
# cognee 1.6.0 - Cloud path. serve() IS a coroutine.
client = await cognee.serve(url=COGNEE_BASE_URL, api_key=COGNEE_API_KEY)
await client.remember(text, dataset_name=...)   # returns status "running"
await client.recall(query_text=..., datasets=[...])  # 409s until indexed - poll
```

Gotchas that cost real time, already fixed here:

- `CACHE_BACKEND=fs` — **not** `filesystem`. The docs say filesystem; the code
  only accepts `redis|fs|tapes|sqlite|postgres` and dies on import otherwise.
- `cognee.serve()` must be awaited. It looks synchronous; it is not.
- Local SDK mode raises `KeylessExtractorNotInstalledError` without an
  `LLM_API_KEY`. **Go through the Cloud tenant instead** — it runs extraction
  server-side, needs no local LLM key, and scores the Cloud bonus.
- `recall()` returns 409 until indexing finishes. Retry, don't sleep-and-hope.
- Bright Data MCP auto-creates `mcp_unlocker` and `mcp_browser` zones on first
  launch. Verified working via `npx -y @brightdata/mcp` with `API_TOKEN`.

```python
# strands-agents 1.56.0
AnthropicModel(client_args={"api_key": ...}, model_id=..., max_tokens=...)
Agent(model=..., tools=[...], system_prompt=...)
from mcp import StdioServerParameters, stdio_client
from strands.tools.mcp import MCPClient
```

## First 15 minutes at the event

1. `python -m secondguess.lint_calendar` — works with **no keys**, proves the
   corpus and the deterministic half are live.
2. Redeem all three credits, fill `.env`.
3. Smoke-test one Cognee `remember` and one Bright Data lookup **before**
   building anything on top of them.
4. `python -m secondguess.extract > runs/baseline.json` — your real baseline.
   Delete the hand-written sample runs; they are targets, not results.
