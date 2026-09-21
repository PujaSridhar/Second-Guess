# Submission — On The Hook

> Pre-filled against Cognee's submission template from their last two hackathons.
> Fill the [ ] gaps at the event; everything else is already true.

## Team
- Team name: [ ]
- Participants: Puja Sridhar
- Project name: On The Hook

## Overview

On The Hook extracts the commitments you made in prose — email, Slack, meeting
notes — and checks each one against your actual availability and against the live
public web, surfacing the ones that are about to break. It self-improves: when
you correct it, the correction distills out of session memory into the permanent
graph as a reusable rule, so it holds for every future run.

- Data sources: email, Slack, meeting notes, calendar (personal); public web via Bright Data
- Primary use case: "What am I on the hook for this week, and what's about to break?"
- What makes it stand out: it implements **lint** — the operation almost nobody
  builds — and it only handles conflicts no single app can already reconcile.

## The three operations

### Ingest
- What goes in: 10 days of email, Slack, meeting notes, plus a calendar
- How captured: `cognee.remember()` into the permanent graph; commitments as entities
- Entry point: [ ]

### Query + self-improve
- Query: "What am I on the hook for?"
- Feedback: user marks false positives and mis-scoped items
- How it updates: corrections distill session -> permanent graph as rules
  (see `ground_truth/feedback.json` for the three used in the demo)
- Entry point: [ ]

### Lint
- What linting means here: checking each commitment for (a) collision with the
  owner's real availability and (b) invalidation by an external fact
- How it runs: calendar check in deterministic Python; external check via a
  Bright Data resolver agent per commitment with an external entity
- Entry point: [ ]

## Self-improvement evidence

### Baseline run
- Query: "What am I on the hook for?"
- Result: 10 extracted, 4 correct, all statuses OK
- **Score: precision 0.40 / recall 0.80 / F1 0.53 / lint accuracy 0.50**
- Feedback recorded: 3 corrections (hedges aren't commitments; others' items
  aren't mine; confirmed-receipt closes a commitment)

### Improved run
- Query: identical
- Result: 6 extracted, all 5 gold found, both conflicts caught
- **Score: precision 0.83 / recall 1.00 / F1 0.91 / lint accuracy 1.00**
- Change: **F1 +0.38, lint accuracy +0.50**

Scores are computed by `scripts/score.py` — deterministic plain Python against
`ground_truth/commitments.json`. No model output is trusted for any number.

## Architecture

```
email / slack / meetings          calendar (structured)
        |                                |
        v                                |
   [Cognee ingest]                       |
   commitments as entities               |
        |                                |
        +--------> [LINT] <--------------+
                     |
          +----------+----------+
          |                     |
   availability check    external resolver
   (Python, deterministic)  (Strands agent per
                            commitment -> Bright
                            Data MCP -> live web)
          |                     |
          +----------+----------+
                     v
              verdicts: OK / AT_RISK / BROKEN
                     |
          +----------+----------+
          v                     v
    draft action         user correction
                                |
                     distill session -> permanent graph
```

Session memory holds this run's observations and lookups. The permanent graph
holds confirmed commitments and the distilled rules about what counts as one.

### Cognee Cloud
[ ] note `cognee.serve` / `cognee.push` usage

## Reproduction

```bash
python3 scripts/score.py runs/baseline.json runs/improved.json
```

## Demo
- Script: `PITCH.md`
- Link: [ ]

## Links
- Repo: [ ]
