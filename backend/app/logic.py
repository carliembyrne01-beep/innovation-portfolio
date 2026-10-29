"""Framework rules: stages, health, quadrants and data-quality flags."""
from datetime import date, timedelta

# Stages as used in the Initiative Register, in order. Objectives and gate evidence are a
# first draft from the framework notes ("intake should not require a business case; larger
# initiatives need stronger framing before resource, funding, scale or rollout decisions").
STAGES = [
    {"key": "Idea/concept", "label": "Idea / concept",
     "objective": "Capture the signal: what problem or opportunity, who raised it, why it matters.",
     "gate": ["Problem or opportunity in one or two sentences", "Named owner (even if provisional)", "Portfolio bucket and route chosen"]},
    {"key": "Framing", "label": "Framing",
     "objective": "Shape it enough to decide whether to spend effort finding out more.",
     "gate": ["Scope and what is out of scope", "Owner and sponsor confirmed", "First component score", "Dependencies and related initiatives named", "Decision needed to move on"]},
    {"key": "Discovery/Validation", "label": "Discovery / validation",
     "objective": "Test the riskiest assumptions with evidence before committing resource.",
     "gate": ["Evidence against the value case", "Technical / commercial / IP risks assessed", "Cost and resource estimate", "Success criteria for a pilot"]},
    {"key": "Pilot/Trial", "label": "Pilot / trial",
     "objective": "Prove it works in the real operating environment, at small scale.",
     "gate": ["Trial evidence against success criteria", "Operating and support model", "Readiness controls (RACI, safety, training)", "Go / no-go for deployment"]},
    {"key": "Active Deployment", "label": "Active deployment",
     "objective": "Roll out, embed and, where relevant, commercialise.",
     "gate": ["Adoption and benefits tracked", "Old tools / processes retired", "Ownership moved to business-as-usual"]},
]
STAGE_KEYS = [s["key"] for s in STAGES]
_STAGE_ALIASES = {k.lower().replace(" ", ""): k for k in STAGE_KEYS}

DECISIONS = ["Stop", "Hold", "Continue", "Pivot", "Scale"]
PRIORITIES = ["Critical", "High", "Medium", "Low"]
HEALTHS = ["Green", "Green/Amber", "Amber", "Amber/Red", "Red", "Grey"]
STATUSES = ["Proposed", "Proposed/In Review", "Active", "Active/In Review", "Watchlist", "On Hold", "Stopped", "Closed / BAU"]
UPDATE_TYPES = ["Owner Update", "Review", "Meeting", "Refresh", "Baseline Snapshot", "Capture Required", "Decision"]
MOVEMENTS = ["Progressed", "No change", "Blocked", "Escalated", "Changed Scope", "Needs capture"]
QUADRANTS = ["Quick Win", "Big Bet", "Filler / Enabler", "Money Pit / Park"]

VALUE_LABELS = {"v_strategic_fit": "Strategic fit", "v_operational_impact": "Operational impact", "v_client_user_impact": "Client / user impact",
                "v_safety_risk_data_quality": "Safety, risk & data quality", "v_scalability_reuse": "Scalability & reuse"}
COMPLEXITY_LABELS = {"c_technical": "Technical", "c_integration_data": "Integration & data", "c_operational_change": "Operational change",
                     "c_dependencies_stakeholders": "Dependencies & stakeholders", "c_commercial_legal_ip": "Commercial, legal & IP"}

# Cut-offs that reproduce the quadrants already recorded in the scoring list (20 of 21 match).
DEFAULT_CUTS = {"value_cut": 7, "complexity_cut": 5}


def norm_stage(v: str | None) -> str | None:
    if not v:
        return None
    return _STAGE_ALIASES.get(v.strip().lower().replace(" ", ""), v.strip())


def stage_index(v: str | None) -> int:
    return STAGE_KEYS.index(v) if v in STAGE_KEYS else -1


def norm_health(v: str | None) -> str | None:
    if not v:
        return None
    s = v.strip().lower().replace(" ", "")
    if s.startswith("grey") or s in ("unknown", "gray"):
        return "Grey"
    for h in HEALTHS:
        if h.lower() == s:
            return h
    return v.strip()


def health_class(h: str | None) -> str:
    return {"Green": "green", "Green/Amber": "ga", "Amber": "amber", "Amber/Red": "ar", "Red": "red"}.get(h or "", "grey")


def quadrant(value: int, complexity: int, cuts: dict) -> str:
    hv, hc = value >= cuts["value_cut"], complexity >= cuts["complexity_cut"]
    return {(True, False): "Quick Win", (True, True): "Big Bet", (False, False): "Filler / Enabler", (False, True): "Money Pit / Park"}[(hv, hc)]


def norm_quadrant(v: str | None) -> str | None:
    if not v:
        return None
    s = v.lower()
    for q in QUADRANTS:
        if q.split(" ")[0].lower() in s:
            return q
    return v


def needs_confirming(v: str | None) -> bool:
    if not v or not v.strip():
        return True
    s = v.lower()
    return any(w in s for w in ("confirm", "tbc", "to be confirmed", "owner to", "?"))


def flags(i, score, latest_update, cuts: dict, today: date) -> list[dict]:
    """Plain-English data-quality and attention flags for one initiative."""
    out = []
    closed = i.portfolio_status in ("Stopped", "Closed / BAU")
    if needs_confirming(i.primary_owner):
        out.append({"kind": "owner", "level": "amber", "text": "Owner to confirm"})
    if needs_confirming(i.sponsor):
        out.append({"kind": "sponsor", "level": "amber", "text": "Sponsor to confirm"})
    if i.stage and i.stage not in STAGE_KEYS:
        out.append({"kind": "stage", "level": "amber", "text": f"Stage '{i.stage}' isn't one of the five framework stages"})
    if not i.stage:
        out.append({"kind": "stage", "level": "amber", "text": "No stage set"})
    if score is None:
        out.append({"kind": "score", "level": "grey", "text": "Not scored yet"})
    else:
        calc = quadrant(score.value_total, score.complexity_total, cuts)
        if score.recorded_quadrant and score.recorded_quadrant != calc:
            out.append({"kind": "quadrant", "level": "grey", "text": f"Recorded as {score.recorded_quadrant}; scores put it in {calc}"})
        if score.review_required:
            out.append({"kind": "score_review", "level": "grey", "text": "Score marked for review"})
    if not closed and i.next_review_date and i.next_review_date < today:
        days = (today - i.next_review_date).days
        out.append({"kind": "overdue", "level": "red", "text": f"Review overdue by {days} day{'s' if days != 1 else ''}"})
    if not closed and not i.next_review_date:
        out.append({"kind": "no_review", "level": "amber", "text": "No next review date"})
    if not closed and (latest_update is None or (latest_update.update_date and latest_update.update_date < today - timedelta(days=60))):
        out.append({"kind": "stale", "level": "amber", "text": "No update in the last 60 days" if latest_update else "No updates logged"})
    return out
