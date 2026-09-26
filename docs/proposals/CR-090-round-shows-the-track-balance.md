# CR-090 — The round shows each person's last track, and the balance across tracks

| | |
|---|---|
| **Status** | **Proposed 2026-09-25** |
| **Contract** | none — `build_agenda.py` behaviour and one optional config key, no schema break |
| **Date** | 2026-09-25 |
| **Area** | `ops` (`build_agenda.py`), `ops-config` (`carry_forward`) |
| **Related CRs** | CR-084 (the track is handed on, not re-answered), CR-042 (`tracks:` in the config), CR-082 (one way to make an agenda) |

## What happens

CR-084 made the round **hand on** each person's track: the agenda reads the previous note's round
table and prefills the first column, marked *(carried)*, so the room confirms in a word instead of
restating.

But the hand-on only runs when the project **does not** declare `tracks:`:

```python
if tracks:
    first = ""                     # declared axis: stated in the room, never prefilled
elif cols:
    carried_track = prior_track.get(...)
```

So the projects that care most about the track axis, the ones that declared it, get a blank column
every morning. The reason for blanking was sound: CR-084 found the column prefilled from `areas`, which
put non-track values under a *Track* heading. That fix went one step too far. It removed the **wrong**
source (areas) and the **right** one (what the person said last session) together.

A second gap sits on top. The round reports people one at a time, so nobody sees the **spread**. On one
series, every person who reported worked on the same track for a week while two of the four declared
tracks had no line at all, and nothing in the agenda showed it. The note had the data; the agenda never
added it up.

## Proposal

**1. With `tracks:` declared, carry the last track into its own column.**

The first column stays blank and is still stated in the room. A second column, **Last track**, shows
what the previous note recorded, marked *(carried)*. The two are kept apart on purpose: one is today's
answer, the other is yesterday's, and merging them is how a carried value comes to read as a
confirmed one.

```
|        | Track | Last track          | Owed into today |
|--------|-------|---------------------|-----------------|
| Ann    |       | web app *(carried)* | ...             |
| Bo     |       | website *(carried)* | ...             |
```

Only values that match a declared track are carried. Anything else (an area, free text) is dropped,
which keeps the CR-084 fix intact.

**2. Print one balance line above the round.**

Counted from the previous note's round table, over the declared tracks, **zeros included**:

```
Last session by track: web app 4 · website 0 · onboarding 1 · offboarding 0
- website and offboarding had no one. Intended, or unbalanced?
```

It is a question, not a verdict. A track with nobody on it can be correct (the work is waiting on
something else) or a sign that the room has narrowed to one surface. Only the room can tell which, so
the line asks.

**3. Optional: a window longer than one session.**

`carry_forward.balance_window: 5` counts the last N notes instead of the last one. One session is
noise; five show a drift. Default `1`, so nothing changes unless a project asks.

## What the note must carry

The mechanism reads a round table in the note, `| <person> | <track> | ... |`. That is already the
CR-084 shape. **A note without a round table produces no Last-track column and no balance line**, and
the agenda says so in its sources block (`round: not recorded in <note>`) rather than printing an empty
column that looks like a quiet day.

## Not in scope

- **Deciding balance.** No thresholds, no warnings on skew. A project can be right to put everyone on
  one track for a week.
- **Tracks per item.** The carry-forward items already name their track in the note; counting those is
  a different question (where the *open* work sits) and can be its own CR if wanted.

## Verification

1. A project with `tracks:` declared and a previous note with a round table: the agenda shows
   *Last track* filled and marked *(carried)*, and the *Track* column blank.
2. A previous note whose round table holds a non-track value: that cell is not carried.
3. The balance line lists every declared track, including those at 0.
4. A previous note with no round table: no Last-track column, and the sources block says
   `round: not recorded`.
5. A project without `tracks:`: behaviour unchanged from CR-084.
