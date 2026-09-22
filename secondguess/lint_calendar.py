"""Availability lint - fully deterministic, no LLM, no network.

This is the half of lint that catches "you promised Friday and you're out
Friday". One side of that fact is prose in an email; the other is a calendar
object. No single app owns both, which is the entire reason this exists.
"""
import json
from datetime import date, datetime, timedelta

from .config import AT_RISK, AT_RISK_BUFFER_DAYS, DATA, OK


def _d(value):
    """Parse an ISO date or datetime string down to a date."""
    if isinstance(value, date):
        return value
    text = str(value)
    if "T" in text:
        return datetime.fromisoformat(text).date()
    return date.fromisoformat(text)


def busy_days(calendar_path=None):
    """Return {date: reason} for every day the owner is unavailable.

    Only all-day events flagged busy count as unavailability. A one-hour
    meeting does not make you unable to send a deck.
    """
    path = calendar_path or (DATA / "calendar" / "calendar.json")
    cal = json.loads(path.read_text())
    out = {}
    for ev in cal["events"]:
        if not (ev.get("all_day") and ev.get("busy")):
            continue
        start, end = _d(ev["start"]), _d(ev["end"])
        day = start
        while day < end:            # end is exclusive for all-day events
            out[day] = ev["title"]
            day += timedelta(days=1)
    return out


def next_free_day(after, busy, limit=30):
    """First weekday on or after `after` that is not busy."""
    day = after
    for _ in range(limit):
        if day.weekday() < 5 and day not in busy:
            return day
        day += timedelta(days=1)
    return None


def check(commitment, busy=None):
    """Return (status, explanation, suggested_date).

    A commitment with no due date cannot collide with anything, so it passes.
    """
    busy = busy_days() if busy is None else busy
    due = commitment.get("due_date")
    if not due:
        return OK, "No due date - nothing to collide with.", None

    due = _d(due)
    window = {due + timedelta(days=n) for n in range(-AT_RISK_BUFFER_DAYS, 1)}
    hit = sorted(d for d in window if d in busy)
    if not hit:
        return OK, f"Due {due.isoformat()}; owner is available.", None

    reason = busy[hit[0]]
    suggested = next_free_day(max(busy) + timedelta(days=1), busy)
    return (
        AT_RISK,
        f"Due {due.isoformat()}, but the calendar shows '{reason}' on "
        f"{hit[0].isoformat()}. The promise is in prose; the conflict is in "
        f"structured data. Nothing joins them today.",
        suggested.isoformat() if suggested else None,
    )


if __name__ == "__main__":
    busy = busy_days()
    print(f"unavailable days: {[d.isoformat() for d in sorted(busy)]}\n")
    for c in json.loads((DATA.parent / "ground_truth" / "commitments.json").read_text())["commitments"]:
        status, why, suggested = check(c, busy)
        flag = "  " if status == OK else "!!"
        print(f"{flag} [{status:8}] {c['key']}")
        print(f"      {why}")
        if suggested:
            print(f"      -> suggest {suggested}")
        print()
