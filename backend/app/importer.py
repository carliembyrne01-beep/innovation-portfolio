"""Import from (and export back to) the MS Lists CSV exports.

One column map per list drives both directions, so an exported CSV has the same
column names as the original list and existing Power BI reports keep working.
Each file is checked first (row-by-row report), then loaded. Loading updates
existing rows by ID and adds new ones; it never deletes.
"""
import csv
import io
import json
import re
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import logic as L
from . import models as m

# (CSV column, attribute, type). Types: str, list, first, joined, date, bool, int, float, stage, health, quadrant, skip
REGISTER = [
    ("Initiative Name", "name", "str"), ("Initiative ID", "id", "str"), ("Short Description", "short_description", "str"),
    ("Primary Owner", "primary_owner", "str"), ("Sponsor/exec lead", "sponsor", "str"), ("Business Area", "business_areas", "list"),
    ("Portfolio Bucket", "portfolio_bucket", "str"), ("Primary Route", "primary_route", "list"), ("Current Stage", "stage", "stage"),
    ("Value Type", "value_types", "list"), ("Portfolio Status", "portfolio_status", "str"), ("Priority", "priority", "str"),
    ("Overall Health", "health", "health"), ("Decision Needed", "decision_needed", "str"), ("Next Action", "next_action", "str"),
    ("Next Action Owner", "next_action_owner", "str"), ("Next Review Date", "next_review_date", "date"),
    ("Last Reviewed Date", "last_reviewed_date", "date"), ("Evidence Status", "evidence_status", "str"),
    ("Dependencies", "dependencies", "str"), ("WSG Strategic Priority Alignment", "strategic_alignment_text", "str"),
    ("Comments", "comments", "str"), ("Confidence Level", "confidence", "joined"),
    ("Integrated Platform Link", "integrated_platform_link", "str"), ("Commercial Decision Required", "commercial_decision_required", "str"),
    ("Client Impact", "client_impact", "str"), ("Funding/Resource Ask", "funding_ask", "str"),
    ("Related Initiatives", "related_initiatives", "list"),
]
SCORES = [
    ("Score ID", "id", "str"), ("Initiative ID", "initiative_id", "str"), ("Initiative Name", None, "skip"),
    ("Score Date", "score_date", "date"),
    ("Value Strategic Fit", "v_strategic_fit", "int"), ("Value Operational Impact", "v_operational_impact", "int"),
    ("Value Client User Impact", "v_client_user_impact", "int"), ("Value Safety Risk Data Quality", "v_safety_risk_data_quality", "int"),
    ("Value Scalability Reuse", "v_scalability_reuse", "int"), ("Intangible Value Total", "recorded_value_total", "int"),
    ("Complexity Technical", "c_technical", "int"), ("Complexity Integration Data", "c_integration_data", "int"),
    ("Complexity Operational Change", "c_operational_change", "int"),
    ("Complexity Dependencies Stakeholders", "c_dependencies_stakeholders", "int"),
    ("Complexity Commercial Legal IP", "c_commercial_legal_ip", "int"), ("Complexity Total", "recorded_complexity_total", "int"),
    ("Portfolio Quadrant", "recorded_quadrant", "quadrant"), ("Scoring Confidence", "confidence", "first"),
    ("Value Rationale", "value_rationale", "str"), ("Complexity Rationale", "complexity_rationale", "str"),
    ("Estimated One-Off Cost AUD", "est_one_off_cost_aud", "float"), ("Estimated Annual Run Cost AUD", "est_annual_run_cost_aud", "float"),
    ("Estimated Annual Benefit AUD", "est_annual_benefit_aud", "float"), ("Estimated Revenue Uplift AUD", "est_revenue_uplift_aud", "float"),
    ("Estimated Cost Avoidance AUD", "est_cost_avoidance_aud", "float"), ("Estimated ROI Percent", "est_roi_percent", "float"),
    ("Estimated Payback Months", "est_payback_months", "float"), ("Hours Saved Per Month", "hours_saved_per_month", "float"),
    ("Cycle Time Reduction Percent", "cycle_time_reduction_percent", "float"), ("Rework Reduction Percent", "rework_reduction_percent", "float"),
    ("Safety Exposure Reduction Count", "safety_exposure_reduction_count", "float"),
    ("Tangible Value Confidence", "tangible_confidence", "first"), ("Tangible Value Notes", "tangible_notes", "str"),
    ("Active Score", "active", "bool"), ("Review Required", "review_required", "bool"), ("Scored By", "scored_by", "str"),
    ("Scoring Version", "scoring_version", "str"), ("Notes", "notes", "str"),
]
ALIGNMENT = [
    ("Alignment ID", "id", "str"), ("Initiative ID", "initiative_id", "str"), ("Initiative Name", None, "skip"),
    ("Alignment Type", "alignment_type", "first"), ("Alignment Area", "area", "first"), ("Alignment Role", "role", "first"),
    ("Portfolio Bucket", None, "skip"), ("Initiative Priority", None, "skip"), ("Current Stage", None, "skip"),
    ("Portfolio Status", None, "skip"), ("Evidence Basis", "evidence_basis", "str"), ("Notes", "notes", "str"),
    ("Active", "active", "bool"), ("Review Required", "review_required", "bool"),
]
UPDATES = [
    ("Update ID", "id", "str"), ("Initiative ID", "initiative_id", "str"), ("Initiative Name", None, "skip"),
    ("Update Date", "update_date", "date"), ("Update Type", "update_type", "str"), ("Update Summary", "summary", "str"),
    ("Movement Since Last Update", "movement", "str"), ("Current Health", "health", "health"),
    ("Decision Needed", "decision_needed", "str"), ("Next Action", "next_action", "str"), ("Next Action Owner", "next_action_owner", "str"),
    ("Due Date", "due_date", "date"), ("Next Action Status", "action_status", "str"), ("Include in Align", "include_in_align", "bool"),
    ("Confidential/Working Only", "confidential", "bool"), ("Working Notes", "working_notes", "str"),
    ("Include in MD Update", "include_in_md_update", "bool"),
]

KINDS = {
    "register": {"label": "Initiative Register", "id_col": "Initiative ID", "key": "Current Stage", "cols": REGISTER, "model": m.Initiative, "order": 0},
    "scores": {"label": "Scoring Component Model", "id_col": "Score ID", "key": "Score ID", "cols": SCORES, "model": m.Score, "order": 1},
    "alignment": {"label": "Alignment / Value Pockets", "id_col": "Alignment ID", "key": "Alignment ID", "cols": ALIGNMENT, "model": m.Alignment, "order": 2},
    "updates": {"label": "Initiative Updates Log", "id_col": "Update ID", "key": "Update ID", "cols": UPDATES, "model": m.Update, "order": 3},
}


# ------------------------------------------------------------------ parsing
def read_csv(raw: bytes) -> tuple[list[str], list[dict]]:
    text = raw.decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return [], []
    heads = [h.strip() for h in rows[0]]
    out = []
    for n, r in enumerate(rows[1:], start=2):
        out.append({"_row": n, **{heads[i]: r[i] for i in range(min(len(heads), len(r)))}})
    return heads, out


def detect(heads: list[str]) -> str | None:
    for kind in ("updates", "scores", "alignment"):
        if KINDS[kind]["key"] in heads:
            return kind
    if "Initiative ID" in heads and "Current Stage" in heads and "Initiative Name" in heads:
        return "register"
    return None


def split_list(v: str) -> list[str]:
    """Lists exports hold multi-choice values as JSON arrays, sometimes with several
    choices packed into one item ("Operations; Safety"). Flatten both into one list."""
    v = (v or "").strip()
    if not v:
        return []
    items = None
    if v.startswith("["):
        try:
            items = [str(x) for x in json.loads(v)]
        except ValueError:
            items = None
    if items is None:
        items = [v]
    out, seen = [], set()
    for it in items:
        for part in re.split(r";", it):
            p = part.strip().strip(",").strip()
            if p and p.lower() not in seen:
                seen.add(p.lower())
                out.append(p)
    return out


def day_first(rows: list[dict], cols: list) -> bool:
    """MS Lists exports dates month-first (8/30/2026). Switch to day-first only if a value proves it."""
    for c, _a, t in cols:
        if t != "date":
            continue
        for r in rows:
            mt = re.match(r"^\s*(\d{1,2})/(\d{1,2})/(\d{2,4})", r.get(c) or "")
            if mt and int(mt.group(1)) > 12:
                return True
    return False


def parse_date(v: str, dayfirst: bool) -> date | None:
    v = (v or "").strip()
    if not v:
        return None
    fmts = ("%d/%m/%Y", "%m/%d/%Y") if dayfirst else ("%m/%d/%Y", "%d/%m/%Y")
    for f in (*fmts, "%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%d %b %Y"):
        try:
            return datetime.strptime(v.split(" ")[0] if "/" in v else v, f).date()
        except ValueError:
            pass
    raise ValueError(f"'{v}' isn't a date")


def convert(v: str, t: str, dayfirst: bool, canon: dict):
    v = (v or "").strip()
    if t == "str":
        return v or None
    if t == "list":
        return [canon.setdefault(x.lower(), x) for x in split_list(v)]
    if t == "first":
        items = split_list(v)
        return items[0] if items else None
    if t == "joined":
        return " / ".join(split_list(v)) or None
    if t == "date":
        return parse_date(v, dayfirst)
    if t == "bool":
        return v.lower() in ("true", "yes", "y", "1")
    if t == "int":
        return int(float(v)) if v else None
    if t == "float":
        return float(v.replace(",", "").replace("$", "")) if v else None
    if t == "stage":
        return L.norm_stage(v)
    if t == "health":
        return L.norm_health(v)
    if t == "quadrant":
        items = split_list(v)
        return L.norm_quadrant(items[0]) if items else None
    return None


# ------------------------------------------------------------------ check / load
def plan(db: Session, files: list[tuple[str, bytes]], cuts: dict) -> list[dict]:
    """Parse and check every file. Returns one report per file, with the parsed records attached."""
    parsed = []
    for name, raw in files:
        heads, rows = read_csv(raw)
        kind = detect(heads)
        parsed.append({"filename": name, "kind": kind, "heads": heads, "rows": rows})
    parsed.sort(key=lambda p: KINDS[p["kind"]]["order"] if p["kind"] else 99)

    known_ids = set(db.scalars(select(m.Initiative.id)).all())
    canon: dict = {}
    reports = []
    for p in parsed:
        rep = {"filename": p["filename"], "kind": p["kind"], "label": None, "rows": 0, "new": 0, "updated": 0,
               "skipped": 0, "issues": [], "records": []}
        reports.append(rep)
        if not p["kind"]:
            rep["issues"].append({"row": 1, "level": "error", "msg": "Couldn't tell which list this is. Expected the Initiative Register, Scoring, Alignment or Updates Log export."})
            continue
        spec = KINDS[p["kind"]]
        rep["label"] = spec["label"]
        missing = [c for c, a, t in spec["cols"] if t != "skip" and c not in p["heads"]]
        if missing:
            rep["issues"].append({"row": 1, "level": "warning", "msg": "Columns not in this file (left blank): " + ", ".join(missing)})
        dayfirst = day_first(p["rows"], spec["cols"])
        existing = set(db.scalars(select(spec["model"].id)).all())
        seen_ids, seen_align = set(), set()
        for r in p["rows"]:
            n = r["_row"]
            rid = (r.get(spec["id_col"]) or "").strip()
            if not rid:
                if any((r.get(c) or "").strip() for c, a, t in spec["cols"] if t not in ("bool", "skip")):
                    rep["issues"].append({"row": n, "level": "error", "msg": f"No {spec['id_col']} — row skipped"})
                rep["skipped"] += 1
                continue
            rep["rows"] += 1
            rec, bad = {}, False
            for c, a, t in spec["cols"]:
                if t == "skip" or c not in r:
                    continue
                try:
                    rec[a] = convert(r[c], t, dayfirst, canon)
                except ValueError as e:
                    rep["issues"].append({"row": n, "level": "warning", "msg": f"{c}: {e} — left blank"})
                    rec[a] = None
            if rid in seen_ids:
                rep["issues"].append({"row": n, "level": "error", "msg": f"{rid} appears twice in this file — second copy skipped"})
                rep["skipped"] += 1
                continue
            seen_ids.add(rid)

            if p["kind"] == "register":
                if not rec.get("name"):
                    rep["issues"].append({"row": n, "level": "error", "msg": f"{rid} has no name — skipped"}); bad = True
                if rec.get("stage") and rec["stage"] not in L.STAGE_KEYS:
                    rep["issues"].append({"row": n, "level": "warning", "msg": f"{rid}: stage '{rec['stage']}' isn't one of the five framework stages"})
                if L.needs_confirming(rec.get("primary_owner")):
                    rep["issues"].append({"row": n, "level": "info", "msg": f"{rid}: owner still to confirm ('{rec.get('primary_owner') or 'blank'}')"})
                if not bad:
                    known_ids.add(rid)
            else:
                iid = rec.get("initiative_id")
                if iid not in known_ids:
                    # Typos like "INT-0019": recover the initiative from the row's own ID (ALIGN-INIT-0019-SP-04).
                    mt = re.search(r"INIT-\d{4}", rid)
                    if mt and mt.group(0) in known_ids:
                        rep["issues"].append({"row": n, "level": "warning", "msg": f"{rid}: Initiative ID '{iid}' corrected to {mt.group(0)}"})
                        iid = rec["initiative_id"] = mt.group(0)
                if iid not in known_ids:
                    rep["issues"].append({"row": n, "level": "error", "msg": f"{rid}: initiative {iid or '(blank)'} isn't in the register — skipped"}); bad = True
            if p["kind"] == "scores" and not bad:
                vt = sum(rec.get(k) or 0 for k in m.Score.VALUE)
                ct = sum(rec.get(k) or 0 for k in m.Score.COMPLEXITY)
                if rec.get("recorded_value_total") not in (None, vt):
                    rep["issues"].append({"row": n, "level": "warning", "msg": f"{rid}: value total recorded as {rec['recorded_value_total']} but components add to {vt} — using {vt}"})
                if rec.get("recorded_complexity_total") not in (None, ct):
                    rep["issues"].append({"row": n, "level": "warning", "msg": f"{rid}: complexity total recorded as {rec['recorded_complexity_total']} but components add to {ct} — using {ct}"})
                calc = L.quadrant(vt, ct, cuts)
                if rec.get("recorded_quadrant") and rec["recorded_quadrant"] != calc:
                    rep["issues"].append({"row": n, "level": "info", "msg": f"{rid}: recorded as {rec['recorded_quadrant']}, scores put it in {calc} (value {vt}, complexity {ct})"})
                for k in m.Score.VALUE + m.Score.COMPLEXITY:
                    if rec.get(k) is not None and not 0 <= rec[k] <= 2:
                        rep["issues"].append({"row": n, "level": "warning", "msg": f"{rid}: component score {rec[k]} is outside 0–2"})
            if p["kind"] == "alignment" and not bad:
                key = (rec.get("initiative_id"), rec.get("alignment_type"), (rec.get("area") or "").lower())
                if key in seen_align:
                    rep["issues"].append({"row": n, "level": "warning", "msg": f"{rid}: duplicate of an earlier row ({rec.get('area')}) — skipped"}); bad = True
                seen_align.add(key)
                if not rec.get("area"):
                    rep["issues"].append({"row": n, "level": "error", "msg": f"{rid}: no alignment area — skipped"}); bad = True
            if bad:
                rep["skipped"] += 1
                continue
            rep["new" if rid not in existing else "updated"] += 1
            rep["records"].append(rec)
    return reports


def apply(db: Session, reports: list[dict]) -> dict:
    counts = {}
    for rep in reports:
        if not rep["kind"]:
            continue
        model = KINDS[rep["kind"]]["model"]
        for rec in rep["records"]:
            obj = db.get(model, rec["id"])
            if obj is None:
                obj = model(id=rec["id"])
                db.add(obj)
            for k, v in rec.items():
                if k != "id":
                    setattr(obj, k, v)
        db.flush()
        counts[rep["label"]] = len(rep["records"])
    # One active score per initiative: keep the latest active one.
    for iid in db.scalars(select(m.Score.initiative_id).distinct()).all():
        scores = db.scalars(select(m.Score).where(m.Score.initiative_id == iid, m.Score.active == True)  # noqa: E712
                            .order_by(m.Score.score_date.desc(), m.Score.id.desc())).all()
        for s in scores[1:]:
            s.active = False
    db.commit()
    return counts


# ------------------------------------------------------------------ export
def export_csv(db: Session, kind: str, cuts: dict) -> str:
    spec = KINDS[kind]
    names = {i.id: i.name for i in db.scalars(select(m.Initiative)).all()}
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL)
    w.writerow([c for c, a, t in spec["cols"] if t != "skip" or c == "Initiative Name"])
    for obj in db.scalars(select(spec["model"]).order_by(spec["model"].id)).all():
        row = []
        for c, a, t in spec["cols"]:
            if t == "skip":
                if c == "Initiative Name":
                    row.append(names.get(obj.initiative_id, ""))
                continue
            v = getattr(obj, a)
            if a == "recorded_value_total":
                v = obj.value_total
            elif a == "recorded_complexity_total":
                v = obj.complexity_total
            elif a == "recorded_quadrant":
                v = L.quadrant(obj.value_total, obj.complexity_total, cuts)
            if isinstance(v, list):
                v = "; ".join(v)
            elif isinstance(v, bool):
                v = "True" if v else "False"
            elif isinstance(v, date):
                v = v.isoformat()
            elif isinstance(v, float) and v.is_integer():
                v = int(v)
            row.append("" if v is None else v)
        w.writerow(row)
    return buf.getvalue()
