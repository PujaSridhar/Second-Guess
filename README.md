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
baseline   precision 0.40  recall 0.80  F1 0.53   lint 0.50
improved   precision 0.83  recall 1.00  F1 0.91   lint 1.00

            f1: 0.53  ->  0.91   (+0.38)
 lint_accuracy: 0.50  ->  1.00   (+0.50)
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
# Cognee (use Cloud - "Best use of Cognee Cloud" was a bonus track last time)
export COGNEE_API_KEY=...
# Bright Data MCP
export BRIGHT_DATA_API_TOKEN=...
# Strands is model-agnostic. If Bedrock access is any friction, point it at
# Anthropic directly and move on. Do not spend hackathon minutes on IAM.
export ANTHROPIC_API_KEY=...
```

Note: AWS credits are listed in the **prize** pool, not handed out at the door.
The $100 upfront is Cognee + Bright Data.
