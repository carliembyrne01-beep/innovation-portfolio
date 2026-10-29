"""Framework rules: stages, health, quadrants and data-quality flags."""
from datetime import date, timedelta

# Stages as used in the Initiative Register, in order (keys match the register; labels are
# worded to fit any non-BAU work, not only technology). Objectives and gate evidence are a
# first draft from the framework notes ("intake should not require a business case; larger
# initiatives need stronger framing before resource, funding, scale or rollout decisions").
STAGES = [
    {"key": "Idea/concept", "label": "Idea / concept",
     "objective": "Capture the need or opportunity: what it is, who raised it, why it can't be handled as business as usual.",
     "gate": ["Need or opportunity in one or two sentences", "Named owner (even if provisional)", "Initiative type chosen", "Rough size of the time or resource needed"]},
    {"key": "Framing", "label": "Framing",
     "objective": "Shape it enough to decide whether it deserves time and resource to explore further.",
     "gate": ["Scope and what is out of scope", "Owner and sponsor confirmed", "First value / complexity score", "Dependencies and related initiatives named", "Decision needed to move on"]},
    {"key": "Discovery/Validation", "label": "Discovery / validation",
     "objective": "Test the riskiest assumptions with evidence before committing real resource.",
     "gate": ["Evidence the problem and value are real", "Key risks assessed (technical, commercial, safety, people)", "Effort, cost and who is needed", "Success criteria for a pilot or test"]},
    {"key": "Pilot/Trial", "label": "Pilot / test",
     "objective": "Prove it works in real conditions at small scale: a trial, a first site, a first review cycle.",
     "gate": ["Results against the success criteria", "How it will run and who supports it", "Readiness controls (RACI, safety, training)", "Go / no-go to deliver in full"]},
    {"key": "Active Deployment", "label": "Deliver / embed",
     "objective": "Deliver it in full, embed it in how WSG works and, where relevant, commercialise it.",
     "gate": ["Adoption and benefits tracked", "Old ways of working retired", "Ownership handed to business as usual (then Close → BAU)"]},
]
STAGE_KEYS = [s["key"] for s in STAGES]
_STAGE_ALIASES = {k.lower().replace(" ", ""): k for k in STAGE_KEYS}

DECISIONS = ["Stop", "Hold", "Continue", "Pivot", "Scale", "Close"]
DECISION_LABELS = {"Close": "Close → BAU"}
STAGE_MOVE = "Stage move"

# Initiative types: the register's "Portfolio Bucket" values.
TYPES = ["Strategic Workstream", "Product-Service", "Platform-System", "Operational Improvement",
         "Governance-Operating Model", "Commercial Partnership", "Data-Automation"]

# Effort / resource ask on a short scale, smallest first, with a weight for the resource view.
EFFORTS = ["Minimal", "Minor internal effort", "Material internal effort", "External / vendor cost", "Capital required", "Unknown"]
EFFORT_WEIGHT = {"Minimal": 1, "Minor internal effort": 2, "Material internal effort": 3, "External / vendor cost": 3, "Capital required": 4, "Unknown": 2}


def effort_from_text(text: str | None) -> str | None:
    """Map the register's free-text "Funding/Resource Ask" to the scale; the largest ask mentioned wins."""
    if not text or not text.strip():
        return None
    s = text.lower()
    for key, words in (("Capital required", ("capital",)), ("External / vendor cost", ("vendor", "external")),
                       ("Material internal effort", ("material",)), ("Minor internal effort", ("minor",)),
                       ("Minimal", ("minimal", "none", "nil")), ("Unknown", ("unknown", "tbc"))):
        if any(w in s for w in words):
            return key
    return "Unknown"


def split_people(text: str | None, aliases: dict | None = None) -> list[str]:
    """Turn owner text like "Carlie / Talha — confirm", "CB MM JT" or "Carlie/TQ" into names."""
    import re
    if not text:
        return []
    s = re.sub(r"(?i)\b(owner\s+)?(to\s+)?(be\s+)?confirm(ed)?\b|\btbc\b|\?", " ", text)
    s = s.replace("(", "/").replace(")", "/")
    s = s.replace("—", "/").replace(" - ", "/")
    parts = re.split(r"/|,|&|;|\band\b|\bwith\b", s)
    out = []
    for p in parts:
        p = p.strip(" .-")
        # "Technical owner", "Commercial owner" etc. are placeholders, not people.
        if not p or re.search(r"(?i)\bowner$|^owner\b|\blead$|\bsponsor$", p):
            continue
        toks = p.split()
        # "CB MM JT" = three people's initials
        if len(toks) > 1 and all(re.fullmatch(r"[A-Z]{2,3}", t) for t in toks):
            out.extend(toks)
        else:
            out.append(p)
    names, seen = [], set()
    for n in out:
        n = n[:1].upper() + n[1:] if n.islower() else n
        n = (aliases or {}).get(n.lower(), n)
        if n.lower() not in seen and len(n) > 1:
            seen.add(n.lower())
            names.append(n)
    return names

PRIORITIES = ["Critical", "High", "Medium", "Low"]
HEALTHS = ["Green", "Green/Amber", "Amber", "Amber/Red", "Red", "Grey"]
STATUSES = ["Proposed", "Proposed/In Review", "Active", "Active/In Review", "Watchlist", "On Hold", "Stopped", "Closed / BAU"]
UPDATE_TYPES = ["Owner Update", "Review", "Meeting", "Refresh", "Baseline Snapshot", "Capture Required", "Decision", "Stage move"]
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
    if latest_update is not None and latest_update.health and i.health and norm_health(latest_update.health) != i.health:
        out.append({"kind": "health_mismatch", "level": "amber", "text": f"Register health is {i.health} but the latest update says {latest_update.health}"})
    if not closed and i.next_review_date and i.next_review_date < today:
        days = (today - i.next_review_date).days
        out.append({"kind": "overdue", "level": "red", "text": f"Review overdue by {days} day{'s' if days != 1 else ''}"})
    if not closed and not i.next_review_date:
        out.append({"kind": "no_review", "level": "amber", "text": "No next review date"})
    if not closed and (latest_update is None or (latest_update.update_date and latest_update.update_date < today - timedelta(days=60))):
        out.append({"kind": "stale", "level": "amber", "text": "No update in the last 60 days" if latest_update else "No updates logged"})
    return out


# Health ranked best → worst, for "improved / worsened". Grey means not assessed, so it has no direction.
HEALTH_RANK = {"Green": 0, "Green/Amber": 1, "Amber": 2, "Amber/Red": 3, "Red": 4}


def health_direction(then: str | None, now: str | None) -> str:
    if then == now or now is None:
        return "same"
    if then not in HEALTH_RANK or now not in HEALTH_RANK:
        return "assessed" if then in (None, "Grey") and now in HEALTH_RANK else "same"
    return "better" if HEALTH_RANK[now] < HEALTH_RANK[then] else "worse"

