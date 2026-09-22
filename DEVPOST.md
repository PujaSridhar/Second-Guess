# Second Guess — Devpost submission

## Tagline

Your commitments live in email and Slack, where no app tracks them. Second Guess
reads them, checks each one against your calendar and the live web, and tells you
which promise is about to break.

---

## Inspiration

Every "personal brain" demo answers questions. None of them notice when the
answer is wrong.

The things you're actually on the hook for don't live in any app — they live in
sentences. "I'll have the pricing deck to you by Friday" is an email body. It is
not a task, not a calendar event, not a ticket. No system owns it, so nothing
tracks it, nothing reminds you, and nothing notices when you can't keep it.

Two ways that goes wrong. Either **you can't keep it** — you promised Friday in
prose and your calendar says you're on PTO Friday, and nothing joins those two
facts because one is prose and one is structured. Or **the world moved** — you
committed to building on an API that got sunset, and your notes are perfectly
self-consistent and completely dead.

Either way you find out when the other person asks.

## What it does

Point it at a corpus of email, Slack, meeting notes and a calendar. It:

1. **Extracts** every commitment the owner made in prose — not action items
   assigned to other people, not hedges, not ones already delivered.
2. **Lints** each one deterministically: does the due date collide with real
   unavailability? Did a later message in the same thread already close it?
3. **Resolves** every commitment that names a company, product, API or public
   deadline against the live web — is the thing it depends on still there?
4. **Drafts** the follow-up for anything flagged. Nothing is sent.
5. **Learns.** Corrections are written to a permanent knowledge graph and read
   back on the next run, so a rule you teach once holds forever.

It returns three verdicts: `BROKEN` (undeliverable), `AT_RISK` (collides with
your actual availability), `OK`.

The `OK` case matters as much as the others. Miro is being acquired by Bending
Spoons — a real external change the resolver finds and then deliberately ignores,
because the product still runs. Changed is not broken. It is not an alarm machine.

## How we built it

**Cognee** holds the permanent knowledge graph. The rules that separate a real
commitment from a hedge are not hardcoded in a prompt — they are written to the
graph when the user corrects the system, and recalled into the next run. Pull
Cognee out and the improved run degrades to the baseline. That is the test of
whether a dependency is real.

**Bright Data** resolves external dependencies over MCP. Not one scripted lookup:
it sweeps every commitment naming an external entity. It is the only component
that can possibly know the Assistants API died, because no internal signal exists.

**AWS Strands** is the agent harness — extraction, entity naming, resolution and
drafting, with the Bright Data MCP server attached as tools.

**Docker** sandboxes untrusted web content. A scraped page is attacker-controlled
text heading into a model prompt, and the concrete attack on this product is a
page asserting "the Assistants API was never deprecated", which would flip the
headline verdict. Normalization runs in a throwaway container — no network,
read-only, all capabilities dropped, nobody user, 256m memory, 64 pids — and a
verdict whose source carried injection markers is downgraded in Python. The model
gets no vote on whether it was manipulated.

**Plain Python decides everything that matters.** Calendar collision, closure
detection, deduplication across sources, an evidence gate that refuses `BROKEN`
without a dated citable source, and the scoring itself. The model proposes; it
never writes a verdict and never scores itself.

## Challenges we ran into

Every one of these surfaced only by actually running the thing.

- **`CACHE_BACKEND=filesystem` kills Cognee on import.** The docs say
  `filesystem`; the code accepts only `redis|fs|tapes|sqlite|postgres` and dies
  with a pydantic literal error before anything runs.
- **The local Cognee SDK needs its own LLM key.** Going through the Cloud tenant
  instead runs extraction server-side, removes the dependency, and lands the
  Cloud bonus.
- **Strands streams model output to stdout by default**, which silently corrupted
  every JSON file we redirected. `Agent(callback_handler=None)` fixes it.
- **The same promise appears in a meeting note and the Slack message repeating
  it**, so the model extracts both. Worse than double-counting: one copy resolved
  `BROKEN` while its twin still read `OK`. Deterministic dedupe merges on token
  overlap and keeps the most severe verdict.
- **The resolver marked a commitment `BROKEN` because it found nothing.** Absence
  of evidence read as evidence of absence. A false alarm on a healthy commitment
  is worse than a miss, so `BROKEN` now requires a source URL and an event date.
- **A learned rule in the graph wasn't enough.** The model kept re-proposing a
  W-9 that had already been confirmed received three lines down its own thread.
  Whether a thread confirms delivery is a fact about the document, not a
  judgement — so it moved out of the prompt into Python, where it holds every
  time instead of most of the time.

## Accomplishments we're proud of

- A **measured** improvement loop, not an asserted one: F1 0.71 → 1.00 and
  verdict accuracy 1.00 against a hand-labelled set, computed by a scorer the
  model never touches.
- A **live** dashboard. Click Run and the real pipeline executes — extraction,
  Cognee recall, calendar lint, a live Bright Data search, drafts — and the page
  renders whatever that run produced, including a bad one. No replayed fixtures.
- Every tool is load-bearing. We can name what breaks if you remove each one.

## What we learned

Put the judgement in the model and the arithmetic in Python. Every time we moved
a decision from a prompt into deterministic code, it got more reliable and more
explainable at once — and it became something we could measure rather than
something we could only claim.

And a corollary we didn't expect: a rule living in a knowledge graph is not the
same as a rule being applied. Retrieval is not enforcement.

## What's next

- Real inboxes instead of a seeded corpus.
- Session-to-permanent distillation — right now only the permanent graph is
  written.
- Crisper retrieval: the graph currently returns a synthesized blend rather than
  the exact corrections taught to it.

## Honest limits

The corpus is seeded and the internal conflicts are planted. The **external**
facts are real and fetched live at run time — the OpenAI Assistants API sunset of
2026-08-26 and the Bending Spoons acquisition of Miro both actually happened,
which is also why the numbers move slightly between runs. F1 of 1.00 is five
labelled commitments against ten decoys, not a benchmark.

## Built with

`python` `cognee` `bright-data` `aws-strands-agents` `mcp` `docker` `openai`
`knowledge-graphs` `html` `javascript`
