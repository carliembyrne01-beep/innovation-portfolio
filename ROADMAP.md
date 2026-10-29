# Initiative Portfolio — roadmap

Last updated: 29 Oct 2026

## Done

| Version | What |
|---|---|
| v0.1 | Replaced the four MS Lists: register, scoring, alignment, updates log. CSV import with a check report, and CSV export for Power BI. Overview, register, pipeline, value × complexity matrix, strategy alignment. Workshop mode for the monthly review (Stop / Hold / Continue / Pivot / Scale), open actions, decisions log, printable leadership pack |
| v0.2 | Renamed to Initiative Portfolio (any non-BAU work). Initiative type and effort / resource ask. Resource load view. Close → BAU decision. Generic stage wording. Move initiatives between stages, by dragging on the pipeline or from the stage strip, with a logged reason |
| v0.3 | Movement between reviews: Movement page, pipeline arrows, health-over-time strip, movement in Workshop mode and the leadership pack. Flag when the register's health differs from the latest update |
| v0.4 | Linked initiatives: "part of" (programme → parts, with a combined status), suggested parts from the register's Primary Route, related initiatives picked from the list |

## On hold

### Voting / polls to score initiatives
*Raised 29 Oct 2026. On hold at the user's request.*

Let several people score an initiative, instead of one person entering the score, and use the spread of scores to drive discussion.

- **Step 1: Microsoft Forms, no hosting needed.**
  - One form per scoring round, where each person scores the 10 factors (0–2).
  - The results CSV is imported into the app.
  - The app shows the average and the spread, and highlights the factors where people disagreed most.
  - The portfolio lead confirms the final score, which is saved as a normal score, with the votes kept as evidence.
- **Step 2: built-in voting, once hosted.**
  - People vote from their phones in the meeting, e.g. via a QR code on the big screen.
  - Results appear live in Workshop mode.
  - Each person's scores are kept against their Microsoft 365 sign-in.
- **Depends on:** central hosting and sign-in (see Next) for step 2. Step 1 can be built any time.

## Next (not started)

- **Central hosting:** one shared copy for the team instead of one per laptop (e.g. Azure App Service, with the database moved to PostgreSQL). Needs IT / security review.
- **Microsoft 365 sign-in:** named users in the update and decision history, instead of free text.
- **WSG portal:** a landing page with FLOW and Initiative Portfolio buttons.
- **Intake triage:** ideas from the intake form land in *Idea / concept* with a triage outcome (BAU, watchlist, quick scope, active initiative, park).
- **Business-case fields:** make cost, benefit and ROI editable in the app. They are currently imported and shown only.
- **Owners as people, not free text:** a people list, so the resource view no longer depends on name parsing and aliases.
