# 3-minute demo script

Lead with the conflict. Never with the extraction — "it finds your action items"
makes you indistinguishable from two other teams in the room.

---

**[0:00-0:25] The problem**

> "The things you're on the hook for don't live in any app. They live in
> sentences. 'I'll send you the pricing by Friday' is an email body — not a task,
> not a calendar event. No system owns it, so nothing tracks it, and nothing
> notices when you can't keep it."

**[0:25-0:55] Baseline run — let it be wrong**

Run the naive extraction. Show the score.

> "Here's what a normal personal brain does. Ten items. Four of them are real.
> It grabbed 'we should grab coffee sometime.' It grabbed Raj's action item, not
> mine. It grabbed a W-9 I already sent. F1 of 0.53 — and every status says OK."

**[0:55-1:50] Lint — the two catches**

> "Now lint. First: I promised Marcus the pricing deck by Friday the 25th. My
> calendar says I'm on PTO the 24th and 25th. One side of that is prose in an
> email, the other is a calendar object. **Google Calendar will never catch this**
> — the promise isn't a calendar object and never will be. There's no join."

> "Second, and this is the one nothing in my stack could ever find: I committed
> to shipping our support assistant on the OpenAI Assistants API. Bright Data
> checks it live — that API was sunset on August 26th. I made a commitment,
> three weeks later, to build on something that was already dead. My data is
> perfectly self-consistent and completely wrong."

> "It also checked Miro, which is being acquired by Bending Spoons. That one it
> leaves alone — changed, but not broken. It's not an alarm machine."

**[1:50-2:30] Self-improvement — the scored part**

Give it three corrections. Rerun.

> "I tell it three things. Hedged language isn't a commitment. Raj's items aren't
> mine. The W-9 is closed. Those distill out of session memory into the permanent
> graph as rules — so they hold for every future run, not just this one."

Show the diff:

```
            f1: 0.53  ->  0.91   (+0.38)
 lint_accuracy: 0.50  ->  1.00   (+0.50)
```

> "Same corpus. Same question. The brain got better, and that's a number, not a
> vibe — computed in plain Python. The model never scores itself."

**[2:30-2:50] Action**

> "And here's the draft to Marcus moving it to Monday the 28th, because it knows
> I'm back on the 28th."

**[2:50-3:00] Close**

> "Everyone's brain can remember. Second Guess notices when you're wrong."

---

## Objections, pre-loaded

**"Doesn't my calendar already do this?"**
> Calendars reconcile calendar conflicts. This joins *prose* to everything else.
> The promise in an email body is not a calendar object and never will be.

**"Is this real data?"**
> The corpus is seeded and the conflicts are planted — say it out loud. The
> external facts are real and verified live: the Assistants API sunset and the
> Miro acquisition both actually happened.

**"Where's the memory, versus just running an LLM over files?"**
> The corrections persist. Run it tomorrow on new email and it already knows
> hedges aren't commitments and Raj's items aren't mine. That's the distillation
> from session into the permanent graph.
