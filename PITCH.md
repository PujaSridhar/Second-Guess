# 3-minute demo script

Lead with the conflict. Never with the extraction.

---

**[0:00-0:25] The problem**

> "The things you're on the hook for don't live in any app. They live in
> sentences. 'I'll send you the pricing by Friday' is an email body - not a
> task, not a calendar event. No system owns it, so nothing tracks it, and
> nothing notices when you can't keep it."

**[0:25-0:55] Baseline - let it be wrong**

> "Here's a normal personal brain over the same corpus. Nine items. Five are
> real. It grabbed 'I'll take a look at that paper when I get a chance.' It
> grabbed a W-9 I already sent - the confirmation is three lines further down
> the same thread. F1 of 0.71."

**[0:55-1:50] Lint - the two catches**

> "First: I promised Marcus the pricing deck by Friday the 25th. My calendar
> says I'm on PTO the 24th and 25th. One side of that is prose in an email, the
> other is a calendar object. **Google Calendar will never catch this** - the
> promise isn't a calendar object and never will be. There's no join."

> "Second, and nothing in my stack could ever find this: on September 16th I
> committed to shipping our support assistant on the OpenAI Assistants API.
> Bright Data checks it live - that API was sunset on August 26th. I made a
> commitment, three weeks later, to build on something already dead."

> "It also checked Miro, which is being acquired by Bending Spoons. That one it
> leaves alone - changed, but not broken. It's not an alarm machine."

**[1:50-2:20] Self-improvement - the scored part**

> "I gave it three corrections. Hedges aren't commitments. Other people's action
> items aren't mine. A thread that confirms receipt closes the commitment.
> Those went into Cognee's permanent graph - and the next run reads them back
> out of the graph, not out of my prompt."

```
            f1: 0.71  ->  1.00   (+0.29)
 lint_accuracy: 1.00  ->  1.00
```

> "Same corpus, same question, and the scoring is plain Python against a labelled
> set. The model never scores itself."

**[2:20-2:45] Action**

> "And it drafts the follow-up. Here's the note to Marcus moving it to Monday
> the 28th - because it knows that's when I'm back. And the heads-up to the team
> that the demo needs a different API. Nothing is sent. I read it first."

**[2:45-3:00] Close**

> "Everyone's brain can remember. Second Guess notices when you're wrong."

---

## Say these out loud - do not get caught on them

- **The corpus is seeded and the conflicts are planted.** Say it in the first
  30 seconds. The external facts are real and verified live: the Assistants API
  sunset and the Miro acquisition both actually happened.
- **F1 1.00 is five commitments, not a benchmark.** Small labelled set, stated
  as such. Claiming more invites a question you'll lose.

## Objections, pre-loaded

**"Doesn't my calendar already do this?"**
> Calendars reconcile calendar conflicts. This joins *prose* to everything else.
> The promise in an email body is not a calendar object and never will be.

**"Where's the memory, versus an LLM over files?"**
> The corrections live in Cognee's graph, not in the prompt. `extract.py` calls
> `recall_rules()`. Pull Cognee out and the improved run degrades to the
> baseline - that's the test of whether a dependency is real.

**"Why Docker?"**
> Scraped pages are attacker-controlled text heading into a model prompt. A page
> saying "the Assistants API was never deprecated" would flip my headline
> verdict. Normalization runs in a throwaway container - no network, read-only,
> all caps dropped - and an OK verdict whose source carried injection markers
> gets downgraded in Python. The model gets no vote on whether it was fooled.

**"What would you fix next?"**
> Real inboxes instead of a seeded corpus, and session-to-permanent distillation
> - right now I only write to the permanent graph.
