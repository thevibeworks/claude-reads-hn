#!/usr/bin/env python3
"""Decide which contracted edition slot, if any, this run should publish.

The repo promises four editions a day at fixed hours. Two things dispatch this
workflow: a Cloudflare Worker that fires on time, and GitHub's own `schedule:`,
which on this repo runs a median 4 hours late (28 scheduled runs, 2026-09-03..09,
min 0h19m, max 4h54m). The old gate deduped on "an edition already exists for
this UTC hour" plus a cap of four a day, and a 4-hour-late run collides with
neither: it lands in an empty hour, the count is still under the cap, so it
publishes. The two triggers then spent the day's four editions between 01:00 and
11:00 UTC and the evening slot got nothing -- zero editions after 11:00 UTC on
five consecutive days, while every run stayed green.

So identity moves from "when did this run happen" to "which slot is it filling".
A run serves the latest slot at or before now; whoever arrives first fills it and
everyone else for that slot is a no-op. The late cron stops being a second
scheduler competing for budget and becomes what redundancy should be: it
publishes only when the Worker missed that slot.

MAX_LATE_HOURS bounds the back-fill. Floor assignment already caps lateness at
the gap to the next slot (5h between the daytime slots), so this only governs the
overnight gap: without it, a 00:30 run would fill yesterday's 16:00 slot with
today's front page, filed under yesterday.
"""

import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Keep in step with the `schedule:` block in hn-digest.yml and with the
# Cloudflare Worker's dispatch times: these hours are the published contract
# ("4x daily", 09:00/14:00/19:00/00:00 +8), and a trigger that fires for an hour
# no slot claims is a run that does nothing.
SLOTS = [int(h) for h in os.environ.get("EDITION_SLOTS", "1,6,11,16").split(",")]
MAX_LATE = timedelta(hours=float(os.environ.get("MAX_LATE_HOURS", "6")))
DIGESTS = Path("digests")


def slot_for(now: datetime) -> datetime:
    """The latest contracted slot at or before `now`, wrapping to yesterday."""
    today = now.replace(minute=0, second=0, microsecond=0)
    candidates = [today.replace(hour=h) for h in SLOTS]
    candidates += [c - timedelta(days=1) for c in candidates]
    return max(c for c in candidates if c <= now)


def published_slots(day: datetime) -> set[datetime]:
    """Slots already filled on `day`, by floor-assigning each edition's stamp.

    New editions are named for their slot, so the name alone would answer this.
    Editions written before this gate carry their wall-clock minute (0543, 1055),
    and a legacy file has to count against the slot it actually served or the
    cutover day publishes an extra edition.
    """
    filled = set()
    for path in sorted(DIGESTS.glob(f"{day:%Y/%m}/{day:%d}-*.org")):
        m = re.fullmatch(r"(\d{2})-(\d{2})(\d{2})", path.stem)
        if not m:
            continue
        stamp = day.replace(hour=int(m.group(2)), minute=int(m.group(3)))
        filled.add(slot_for(stamp))
    return filled


def main() -> int:
    now = datetime.now(timezone.utc)
    slot = slot_for(now)
    late = now - slot
    out = []

    def emit(**kw):
        out.extend(f"{k}={v}" for k, v in kw.items())

    print(f"now {now:%Y-%m-%dT%H:%MZ}; serving slot {slot:%Y-%m-%dT%H:%MZ} "
          f"({late.total_seconds() / 3600:.1f}h late); slots {SLOTS}")

    if late > MAX_LATE:
        print(f"slot {slot:%Y-%m-%dT%H:%MZ} is forfeit: "
              f"{late.total_seconds() / 3600:.1f}h late exceeds {MAX_LATE}")
        emit(skip="true")
    else:
        filled = published_slots(slot) | published_slots(slot + timedelta(days=1))
        if slot in filled:
            print(f"slot {slot:%Y-%m-%dT%H:%MZ} already published; nothing to do")
            emit(skip="true")
        else:
            print(f"slot {slot:%Y-%m-%dT%H:%MZ} is open, publishing")
            emit(
                skip="false",
                digest_date=f"{slot:%Y-%m-%dT%H:%M:00Z}",
                digest_path=f"digests/{slot:%Y/%m/%d-%H%M}.org",
                page_path=f"e/{slot:%Y/%m/%d-%H%M}.html",
                anchor=f"{slot:%m%d%H%M}",
                display=f"{slot:%Y-%m-%d %H:%M}",
            )

    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a") as fh:
            fh.write("\n".join(out) + "\n")
    else:
        print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
