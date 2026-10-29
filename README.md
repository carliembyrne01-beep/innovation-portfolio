# WSG Initiative Portfolio

One place for **every piece of work that needs time or resource outside business as usual**: technology, safety, governance, commercial and operational improvement alike. Use it to **keep the portfolio up to date**, **see it at a glance**, **see who is carrying the load**, and **run the monthly portfolio review**. It replaces the four MS Lists (Initiative Register, Scoring Component Model, Alignment / Value Pockets, Initiative Updates Log) and the Figma prototype.

Same simple setup as FLOW: Python only, no Docker, no admin rights, WSG branding. It is built as a standalone app so it can later sit behind a WSG portal button.

## Updating to a new version

Your data is in `backend/portfolio.db` and is never part of a download, so updating can't overwrite it.

1. Close the app's black window.
2. On GitHub: **Code → Download ZIP**, then unzip it.
3. Copy everything from the new folder **over** your existing folder and say yes to replacing files. Your `backend/portfolio.db` and `backend/backups/` stay as they are.
4. Start it again with `start_portfolio.bat`. Any new fields are added to your database automatically on start-up (a backup is taken first). There is no need to re-import.

## Run it

**Windows:** double-click `start_portfolio.bat`. The first run sets up Python (a minute or two), then your browser opens at **http://127.0.0.1:8001**. Keep the black window open while you use it.

**macOS / Linux:** `./start_portfolio.sh`

Your data lives in `backend/portfolio.db`. A backup is copied to `backend/backups/` every time the app starts and before every import (the newest 30 are kept). **The database and backups are never committed to git**, so real initiative data stays on your machine.

## First time: load your MS Lists data

1. In MS Lists, open each list → **Export → Export to CSV**.
2. In the app, go to **Import & export** and drop all four CSVs in at once.
3. Read the check report: every row is checked, and nothing loads yet.
4. Press **Load**.

Re-importing later updates rows by ID and never deletes anything.

The check fixes or flags known problems in the Lists data:

| What | What happens |
|---|---|
| Multi-choice values packed as `["Operations; Safety"]` | Split into separate values |
| Alignment rows with `INT-0019` instead of `INIT-0019` | Corrected from the row's own ID |
| The same value pocket listed twice for one initiative | Duplicate skipped |
| Hand-typed quadrant doesn't match the scores | Shown; the app always calculates the quadrant |
| Blank rows | Skipped |
| Owners / sponsors written as "— confirm", "TBC" or blank | Flagged on the initiative |

## Keeping it current (between meetings)

- **+ New initiative** (top right, on every page): just a name is enough to start; fill in the rest later.
- **Log update** (on every initiative): what's changed, health, movement, decision needed, next action, owner, due date, next review date. This one form keeps the register current: health, next action and review dates are updated from it. The previous open update is marked superseded, so the history stays tidy.
  - Tick **Working only** for sensitive context. Working notes never appear in the leadership pack.
- **Re-score**: click 0 / 1 / 2 for each of the 10 factors. The totals and quadrant update as you click. Old scores are kept as history.
- **Edit details**: owner, sponsor, stage, priority, initiative type, effort / resource ask, business areas, dependencies, related initiatives.
- **Move along the stages**, in either of two ways. Both ask *why* (with the current stage's evidence checklist to tick), who agreed it and the next review date, and log the move in the updates and decisions history.
  - On the **Stage pipeline**, drag a card to another stage.
  - On an initiative, click a stage in the stage strip → **Move to this stage**, or use the **Move to … →** button at the top.
- **Open actions** lists each initiative's current next action. Press **Done** when it's complete.
- **Find an initiative** (top bar): type part of a name or ID.

## The monthly review meeting

**Before the meeting**
1. Ask owners for updates, then **Log update** for each (or have owners do it).
2. Open **Overview** for flags: reviews overdue, owners to confirm, blocked or red.
3. Open **Movement** to see what changed since the last review.
4. Open **Leadership pack** → **Print / save as PDF** to send as the pre-read. It includes the movement summary, and only updates flagged *Include in MD update*, and never working-only notes.

**In the meeting (on the big screen)**
1. Open **Workshop mode** and pick the set:
   - *Red, blocked or critical*: start here if time is short.
   - *Review due*: everything whose review date has passed.
   - *All live* or *Needs capture*.
2. For each initiative you see the stage, the decision needed, the latest update, flags and what the current gate expects.
3. Choose **Stop / Hold / Continue / Pivot / Scale / Close → BAU** and set the stage, health and next review date. Add the rationale and the next action with an owner. Use the **type** filter to review one kind of work at a time, e.g. only Governance-Operating Model items.
4. Press **Record & next →**. The list on the right ticks off each one decided today.
5. **Log update only** if there's no decision to make; **Skip** to come back later.

**After the meeting**
- **Leadership pack** opens with *Decisions and stage moves since* (default: the last month). Print it as the meeting record.
- **Decisions log** and **Open actions** show what was agreed and who owns it.

## Views

| Page | What it shows |
|---|---|
| Overview | Headline numbers, stage funnel, breakdown by type, health, quadrants, what needs attention, latest updates and decisions |
| Register | Every initiative with filters (stage, health, priority, bucket, status, owner, quadrant), search and sortable columns |
| Stage pipeline | Board by stage; coloured edge = health. Drag a card to move it to another stage; filter by type |
| Value × complexity | Matrix of active scores. Drag the sliders to move the quadrant lines, then save. The defaults (value ≥ 7, complexity ≥ 5) match 20 of the 21 quadrants recorded in Lists |
| Strategy alignment | Initiatives × strategic priorities / value pockets (primary vs supporting), plus gaps |
| Movement | What changed between a past review and today: stage moves, health improved / worsened, progress reported (progressed, blocked, escalated, no change), new, closed and initiatives with no update. Pick the review date to compare with; click a tile to filter. Also shown as arrows on the pipeline, as a health-over-time strip on each initiative, in Workshop mode and in the leadership pack |
| Resource load | Each person's live initiatives (weighted by effort size), sponsorships and open / overdue actions, plus effort by type. Names come from the owner and action-owner fields. Use *Same person, different names?* to merge initials with names, e.g. `CB = Carlie` |
| Initiative page | Stage strip with each gate's evidence, flags, key facts, scoring, alignment, update history, decisions, every register field |

## Power BI

**Import & export → Export** downloads each list as CSV with the **same column names as the MS Lists**, so existing Power BI reports can point at these files instead. Multi-choice values are separated by `; `. The quadrant column is the calculated one. The register export has one extra column at the end, *Effort Level*.

## The framework in the app

- **Stages:** Idea / concept → Framing → Discovery / validation → Pilot / test → Deliver / embed. These are the five stages in the register (stored as *Idea/concept … Active Deployment*), worded to fit any kind of non-BAU work. Each stage has an objective and the evidence expected before moving on. These are a first draft; edit them in `backend/app/logic.py` (`STAGES`).
- **Initiative type:** the register's *Portfolio Bucket*: Strategic Workstream, Product-Service, Platform-System, Operational Improvement, Governance-Operating Model, Commercial Partnership, Data-Automation.
- **Effort / resource ask:** Minimal · Minor internal effort · Material internal effort · External / vendor cost · Capital required · Unknown. Filled in automatically from the register's *Funding / resource ask* text; change it with Edit details. It is exported as an extra *Effort Level* column.
- **Scoring:** five value factors and five complexity factors, each 0–2 (totals out of 10).
- **Quadrant:** calculated from the scores: Quick Win, Big Bet, Filler / Enabler or Money Pit / Park.
- **Decisions:** Stop · Hold · Continue · Pivot · Scale · Close → BAU.
  - A decision is written to the decisions log and the updates log.
  - It can move the stage and set health and the next review date.
  - *Stop* sets the status to Stopped; *Hold* sets it to On Hold; *Close → BAU* sets it to Closed / BAU (finished and handed over).
  - Stop and Close also close the initiative's open action.

## For developers

```
backend/app/main.py      API (FastAPI) — /docs for the interactive API reference
backend/app/models.py    data model: Initiative, Score, Alignment, Update, Decision, Setting
backend/app/importer.py  MS Lists CSV import/export (one column map drives both)
backend/app/logic.py     stages, health, quadrant and flag rules
backend/app/static/      front end: plain HTML/CSS/JS, no build step (WSG brand from FLOW's app.css)
backend/tests/           pytest, using fictional fixture CSVs with the real column headers
```

Run the tests: `cd backend && .venv/bin/python -m pytest -q` (Windows: `.venv\Scripts\python -m pytest -q`).

## Roadmap

What's done, on hold and next is in [ROADMAP.md](ROADMAP.md).
