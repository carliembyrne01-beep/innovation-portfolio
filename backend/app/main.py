"""WSG Initiative Portfolio — every non-BAU initiative: register, scoring, stage-gate reviews, decisions and resource load.

Start:   uvicorn app.main:app --reload     (from the backend folder)
Open:    http://127.0.0.1:8001
API docs: http://127.0.0.1:8001/docs
"""
import base64
import os
import shutil
from collections import Counter
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import importer as I
from . import logic as L
from . import models as m
from .db import DB_PATH, Base, SessionLocal, engine, get_db

VERSION = "0.2.0"
STATIC = Path(__file__).resolve().parent / "static"


def today() -> date:
    t = os.environ.get("PORTFOLIO_TODAY")
    return date.fromisoformat(t) if t else date.today()


def backup_database(keep: int = 30) -> str | None:
    """Copy the database to backend/backups/ before anything that changes a lot of data."""
    if not Path(DB_PATH).exists():
        return None
    folder = Path(DB_PATH).parent / "backups"
    folder.mkdir(exist_ok=True)
    dest = folder / f"{Path(DB_PATH).stem}_{datetime.now():%Y%m%d-%H%M%S}.db"
    shutil.copy2(DB_PATH, dest)
    for old in sorted(folder.glob(f"{Path(DB_PATH).stem}_*.db"))[:-keep]:
        old.unlink()
    return str(dest)


@asynccontextmanager
async def lifespan(_app):
    # Real data: never drop anything. Back up on start, then create any missing tables.
    backup_database()
    Base.metadata.create_all(bind=engine)
    upgrade_database()
    yield


def upgrade_database():
    """Add columns introduced by newer versions to an existing database, and fill them in. Never drops anything."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    with engine.begin() as conn:
        for t in Base.metadata.sorted_tables:
            if not insp.has_table(t.name):
                continue  # create_all makes whole new tables; this only adds columns
            have = {c["name"] for c in insp.get_columns(t.name)}
            for col in t.columns:
                if col.name not in have:
                    conn.execute(text(f"ALTER TABLE {t.name} ADD COLUMN {col.name} {col.type.compile(engine.dialect)}"))
    with SessionLocal() as db:
        for i in db.scalars(select(m.Initiative).where(m.Initiative.effort.is_(None), m.Initiative.funding_ask.is_not(None))).all():
            i.effort = L.effort_from_text(i.funding_ask)
        db.commit()


app = FastAPI(title="WSG Initiative Portfolio", version=VERSION, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.exception_handler(HTTPException)
async def _plain_errors(_request: Request, exc: HTTPException):
    return JSONResponse({"message": exc.detail if isinstance(exc.detail, str) else "Request failed"}, status_code=exc.status_code)


@app.get("/", include_in_schema=False)
def spa():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION}


# ---------------------------------------------------------------- helpers
def iso(v):
    return v.isoformat() if v else None


def get_cuts(db: Session) -> dict:
    cuts = dict(L.DEFAULT_CUTS)
    for s in db.scalars(select(m.Setting).where(m.Setting.key.in_(cuts.keys()))).all():
        cuts[s.key] = int(s.value)
    return cuts


def get_init(db: Session, iid: str) -> m.Initiative:
    i = db.get(m.Initiative, iid)
    if not i:
        raise HTTPException(404, f"Initiative {iid} not found")
    return i


def active_scores(db) -> dict:
    return {s.initiative_id: s for s in db.scalars(select(m.Score).where(m.Score.active == True)).all()}  # noqa: E712


def latest_updates(db) -> dict:
    out = {}
    for u in db.scalars(select(m.Update).order_by(m.Update.update_date, m.Update.created_at, m.Update.id)).all():
        out[u.initiative_id] = u
    return out


def primary_priorities(db) -> dict:
    out = {}
    for a in db.scalars(select(m.Alignment).where(m.Alignment.active == True, m.Alignment.alignment_type == "Strategic Priority")  # noqa: E712
                        .order_by(m.Alignment.id)).all():
        out.setdefault(a.initiative_id, []).append({"area": a.area, "role": a.role})
    return out


def score_dict(s: m.Score | None, cuts: dict) -> dict | None:
    if not s:
        return None
    d = {c.name: getattr(s, c.name) for c in m.Score.__table__.columns}
    d["score_date"] = iso(s.score_date)
    d["value_total"], d["complexity_total"] = s.value_total, s.complexity_total
    d["quadrant"] = L.quadrant(s.value_total, s.complexity_total, cuts)
    return d


def last_decisions(db) -> dict:
    out = {}
    for x in db.scalars(select(m.Decision).order_by(m.Decision.decision_date, m.Decision.id)).all():
        out[x.initiative_id] = x
    return out


def card(i: m.Initiative, s, u, prio, cuts, dec=None) -> dict:
    # The register's "Next Action" cell carries dated history; the latest update holds the current one.
    use_u = u is not None and (u.action_status or "Open") != "Superseded"
    return {
        "id": i.id, "name": i.name, "short_description": i.short_description, "owner": i.primary_owner, "sponsor": i.sponsor,
        "bucket": i.portfolio_bucket, "effort": i.effort, "business_areas": i.business_areas or [], "routes": i.primary_route or [],
        "value_types": i.value_types or [], "stage": i.stage, "stage_index": L.stage_index(i.stage),
        "status": i.portfolio_status, "priority": i.priority, "health": i.health, "health_class": L.health_class(i.health),
        "next_review_date": iso(i.next_review_date), "last_reviewed_date": iso(i.last_reviewed_date),
        "evidence_status": i.evidence_status, "confidence": i.confidence,
        "value": s.value_total if s else None, "complexity": s.complexity_total if s else None,
        "quadrant": L.quadrant(s.value_total, s.complexity_total, cuts) if s else None,
        "recorded_quadrant": s.recorded_quadrant if s else None, "score_confidence": s.confidence if s else None,
        "movement": u.movement if u else None, "latest_update_date": iso(u.update_date) if u else None,
        "latest_update_summary": u.summary if u else None,
        "decision_needed": (u.decision_needed if use_u and u.decision_needed else i.decision_needed),
        "next_action": (u.next_action if use_u and u.next_action else i.next_action),
        "next_action_owner": (u.next_action_owner if use_u and u.next_action_owner else i.next_action_owner),
        "next_action_due": iso(u.due_date) if use_u else None,
        "priorities": prio or [],
        "last_decision": dec.decision if dec else None, "last_decision_date": iso(dec.decision_date) if dec else None,
        "flags": L.flags(i, s, u, cuts, today()),
    }


def all_cards(db) -> list[dict]:
    cuts, sc, up, pr, dc = get_cuts(db), active_scores(db), latest_updates(db), primary_priorities(db), last_decisions(db)
    inits = db.scalars(select(m.Initiative).order_by(m.Initiative.id)).all()
    return [card(i, sc.get(i.id), up.get(i.id), pr.get(i.id), cuts, dc.get(i.id)) for i in inits]


def update_dict(u: m.Update, names: dict | None = None) -> dict:
    d = {c.name: getattr(u, c.name) for c in m.Update.__table__.columns}
    for k in ("update_date", "due_date", "created_at"):
        d[k] = iso(d[k])
    d["health_class"] = L.health_class(u.health)
    if names is not None:
        d["initiative_name"] = names.get(u.initiative_id)
    return d


def decision_dict(x: m.Decision, names: dict | None = None) -> dict:
    d = {c.name: getattr(x, c.name) for c in m.Decision.__table__.columns}
    d["decision_date"], d["created_at"] = iso(x.decision_date), iso(x.created_at)
    if names is not None:
        d["initiative_name"] = names.get(x.initiative_id)
    return d


def names_map(db) -> dict:
    return dict(db.execute(select(m.Initiative.id, m.Initiative.name)).all())


def next_seq_id(db, model, prefix: str) -> str:
    n = 1
    while db.get(model, f"{prefix}-{n:02d}"):
        n += 1
    return f"{prefix}-{n:02d}"


# ---------------------------------------------------------------- reference
@app.get("/api/meta")
def meta(db: Session = Depends(get_db)):
    inits = db.scalars(select(m.Initiative)).all()
    distinct = lambda vals: sorted({v for v in vals if v}, key=str.lower)  # noqa: E731
    areas = db.execute(select(m.Alignment.alignment_type, m.Alignment.area).distinct()).all()
    return {
        "version": VERSION, "today": today().isoformat(), "stages": L.STAGES, "decisions": L.DECISIONS,
        "priorities": L.PRIORITIES, "healths": L.HEALTHS,
        "statuses": distinct(L.STATUSES + [i.portfolio_status for i in inits]),
        "update_types": L.UPDATE_TYPES, "movements": L.MOVEMENTS, "quadrants": L.QUADRANTS,
        "value_labels": L.VALUE_LABELS, "complexity_labels": L.COMPLEXITY_LABELS, "cuts": get_cuts(db),
        "buckets": distinct(L.TYPES + [i.portfolio_bucket for i in inits]), "types": L.TYPES,
        "efforts": L.EFFORTS, "decision_labels": L.DECISION_LABELS, "aliases": get_aliases(db),
        "business_areas": distinct(a for i in inits for a in (i.business_areas or [])),
        "owners": distinct(i.primary_owner for i in inits),
        "strategic_priorities": distinct(a for t, a in areas if t == "Strategic Priority"),
        "value_pockets": distinct(a for t, a in areas if t == "Value Pocket"),
        "counts": {"initiatives": len(inits), "updates": db.scalar(select(func.count()).select_from(m.Update)),
                   "scores": db.scalar(select(func.count()).select_from(m.Score))},
    }


# ---------------------------------------------------------------- overview
@app.get("/api/overview")
def overview(db: Session = Depends(get_db)):
    cards = all_cards(db)
    live = [c for c in cards if c["status"] not in ("Stopped", "Closed / BAU")]
    t = today()
    overdue = [c for c in live if c["next_review_date"] and c["next_review_date"] < t.isoformat()]
    red = [c for c in live if c["health"] in ("Red", "Amber/Red")]
    blocked = [c for c in live if c["movement"] in ("Blocked", "Escalated")]
    capture = [c for c in live if c["movement"] == "Needs capture" or c["stage_index"] <= 0 and not c["value"]]
    owner_gaps = [c for c in live if any(f["kind"] in ("owner", "sponsor") for f in c["flags"])]
    decisions_open = [c for c in live if c["decision_needed"]]
    by_stage = [{"key": s["key"], "label": s["label"], "items": [c for c in live if c["stage"] == s["key"]]} for s in L.STAGES]
    other = [c for c in live if c["stage_index"] < 0]
    if other:
        by_stage.append({"key": "other", "label": "No / other stage", "items": other})
    tc = Counter(c["bucket"] or "Not set" for c in live)
    hc = Counter(c["health"] or "Grey" for c in live)
    qc = Counter(c["quadrant"] or "Not scored" for c in live)
    mc = Counter(c["movement"] or "No update" for c in live)
    pc = Counter(c["priority"] or "—" for c in live)

    # Attention: worst first. Red health, blocked/escalated, critical with overdue review.
    def weight(c):
        w = 0
        w += {"Red": 50, "Amber/Red": 40, "Amber": 10}.get(c["health"], 0)
        w += {"Blocked": 30, "Escalated": 30}.get(c["movement"], 0)
        w += {"Critical": 20, "High": 10}.get(c["priority"], 0)
        w += 5 * sum(1 for f in c["flags"] if f["level"] == "red")
        return -w
    attention = sorted([c for c in live if c in red or c in blocked or (c["priority"] == "Critical")], key=weight)[:8]

    names = names_map(db)
    recent = db.scalars(select(m.Update).order_by(m.Update.update_date.desc(), m.Update.id.desc()).limit(12)).all()
    decisions = db.scalars(select(m.Decision).order_by(m.Decision.decision_date.desc(), m.Decision.id.desc()).limit(8)).all()
    return {
        "today": t.isoformat(),
        "kpis": [
            {"label": "Live initiatives", "value": len(live), "note": f"{len(cards) - len(live)} stopped or closed", "rag": "info", "link": "#/register"},
            {"label": "Critical / High priority", "value": sum(1 for c in live if c["priority"] in ("Critical", "High")),
             "note": f"{pc.get('Critical', 0)} critical", "rag": "info", "link": "#/register?priority=Critical"},
            {"label": "Red or Amber/Red", "value": len(red), "note": "health in the register", "rag": "red" if red else "green", "link": "#/register?health=bad"},
            {"label": "Blocked or escalated", "value": len(blocked), "note": "movement at last update", "rag": "red" if blocked else "green", "link": "#/register?movement=blocked"},
            {"label": "Reviews overdue", "value": len(overdue), "note": "next review date passed", "rag": "amber" if overdue else "green", "link": "#/register?flag=overdue"},
            {"label": "Owner / sponsor to confirm", "value": len(owner_gaps), "note": "named as 'confirm', TBC or blank", "rag": "amber" if owner_gaps else "green", "link": "#/register?flag=owner"},
            {"label": "Decisions logged", "value": db.scalar(select(func.count()).select_from(m.Decision)), "note": f"{len(decisions_open)} initiatives waiting on a decision", "rag": "info", "link": "#/decisions"},
            {"label": "Need capture", "value": len(capture), "note": "not ready to score or route", "rag": "amber" if capture else "green", "link": "#/register?movement=capture"},
        ],
        "by_type": [{"label": k, "n": v} for k, v in sorted(tc.items(), key=lambda kv: -kv[1])],
        "by_stage": by_stage, "health": [{"label": h, "n": hc.get(h, 0), "cls": L.health_class(h)} for h in L.HEALTHS],
        "quadrants": [{"label": q, "n": qc.get(q, 0)} for q in L.QUADRANTS + ["Not scored"]],
        "movement": [{"label": k, "n": v} for k, v in mc.most_common()],
        "attention": attention,
        "recent_updates": [update_dict(u, names) for u in recent],
        "recent_decisions": [decision_dict(x, names) for x in decisions],
        "cuts": get_cuts(db),
    }


# ---------------------------------------------------------------- initiatives
@app.get("/api/initiatives")
def list_initiatives(db: Session = Depends(get_db)):
    return all_cards(db)


@app.get("/api/initiatives/{iid}")
def initiative_detail(iid: str, db: Session = Depends(get_db)):
    i = get_init(db, iid)
    cuts = get_cuts(db)
    scores = db.scalars(select(m.Score).where(m.Score.initiative_id == iid).order_by(m.Score.score_date.desc(), m.Score.id.desc())).all()
    active = next((s for s in scores if s.active), None)
    updates = db.scalars(select(m.Update).where(m.Update.initiative_id == iid).order_by(m.Update.update_date.desc(), m.Update.created_at.desc(), m.Update.id.desc())).all()
    aligns = db.scalars(select(m.Alignment).where(m.Alignment.initiative_id == iid).order_by(m.Alignment.id)).all()
    decisions = db.scalars(select(m.Decision).where(m.Decision.initiative_id == iid).order_by(m.Decision.decision_date.desc(), m.Decision.id.desc())).all()
    pr = [{"area": a.area, "role": a.role} for a in aligns if a.alignment_type == "Strategic Priority" and a.active]
    c = card(i, active, updates[0] if updates else None, pr, cuts, decisions[0] if decisions else None)
    # Resolve "related initiatives" text to initiatives where the name matches.
    by_name = {n.lower(): k for k, n in names_map(db).items()}
    related = []
    for r in i.related_initiatives or []:
        hit = by_name.get(r.lower()) or next((k for n, k in by_name.items() if k != iid and (r.lower() in n or n in r.lower()) and len(r) > 3), None)
        related.append({"label": r, "id": hit})
    fields = {col.name: getattr(i, col.name) for col in m.Initiative.__table__.columns}
    for k in ("next_review_date", "last_reviewed_date", "created_at", "updated_at"):
        fields[k] = iso(fields[k])
    return {
        **c, "fields": fields, "related": related,
        "score": score_dict(active, cuts), "score_history": [score_dict(s, cuts) for s in scores],
        "alignments": [{c2.name: getattr(a, c2.name) for c2 in m.Alignment.__table__.columns} for a in aligns],
        "updates": [update_dict(u) for u in updates], "decisions": [decision_dict(x) for x in decisions],
    }


class InitiativeIn(BaseModel):
    name: str = Field(min_length=2)
    short_description: str | None = None
    primary_owner: str | None = None
    sponsor: str | None = None
    portfolio_bucket: str | None = None
    business_areas: list[str] = []
    value_types: list[str] = []
    stage: str | None = "Idea/concept"
    portfolio_status: str | None = "Proposed"
    priority: str | None = "Medium"
    health: str | None = "Grey"
    decision_needed: str | None = None
    next_action: str | None = None
    next_action_owner: str | None = None
    next_review_date: date | None = None
    evidence_status: str | None = None
    dependencies: str | None = None
    effort: str | None = None
    related_initiatives: list[str] = []


@app.post("/api/initiatives")
def create_initiative(x: InitiativeIn, db: Session = Depends(get_db)):
    nums = [int(k.split("-")[1]) for k in db.scalars(select(m.Initiative.id)).all() if k.startswith("INIT-") and k.split("-")[1].isdigit()]
    iid = f"INIT-{(max(nums) + 1 if nums else 1):04d}"
    i = m.Initiative(id=iid, **x.model_dump())
    db.add(i)
    db.commit()
    return {"id": iid, "message": f"{iid} {x.name} added to the register"}


EDITABLE = {"name", "short_description", "primary_owner", "sponsor", "portfolio_bucket", "business_areas", "value_types", "primary_route",
            "stage", "portfolio_status", "priority", "health", "decision_needed", "next_action", "next_action_owner",
            "next_review_date", "last_reviewed_date", "evidence_status", "dependencies", "comments", "confidence",
            "integrated_platform_link", "commercial_decision_required", "client_impact", "funding_ask", "effort", "related_initiatives"}


@app.patch("/api/initiatives/{iid}")
def edit_initiative(iid: str, body: dict, db: Session = Depends(get_db)):
    i = get_init(db, iid)
    bad = set(body) - EDITABLE
    if bad:
        raise HTTPException(422, "Can't edit: " + ", ".join(sorted(bad)))
    for k, v in body.items():
        if k in ("next_review_date", "last_reviewed_date"):
            v = date.fromisoformat(v) if v else None
        if k in ("business_areas", "value_types", "primary_route", "related_initiatives") and isinstance(v, str):
            v = I.split_list(v)
        setattr(i, k, v if v != "" else None)
    db.commit()
    return {"message": f"{i.name} saved"}


class UpdateIn(BaseModel):
    update_type: str = "Owner Update"
    update_date: date | None = None
    summary: str = Field(min_length=3)
    movement: str | None = None
    health: str | None = None
    decision_needed: str | None = None
    next_action: str | None = None
    next_action_owner: str | None = None
    due_date: date | None = None
    working_notes: str | None = None
    confidential: bool = False
    include_in_md_update: bool = True
    include_in_align: bool = True
    supersede_previous: bool = True
    next_review_date: date | None = None


@app.post("/api/initiatives/{iid}/updates")
def add_update(iid: str, x: UpdateIn, db: Session = Depends(get_db)):
    i = get_init(db, iid)
    d = x.update_date or today()
    uid = next_seq_id(db, m.Update, f"UPD-{iid}-{d.isoformat()}")
    if not x.next_action:
        # No new action given: carry the current open one forward so it isn't lost when this update supersedes it.
        prev = db.scalars(select(m.Update).where(m.Update.initiative_id == iid, m.Update.action_status == "Open", m.Update.next_action.is_not(None))
                          .order_by(m.Update.update_date.desc(), m.Update.created_at.desc())).first()
        if prev:
            x.next_action, x.next_action_owner, x.due_date = prev.next_action, x.next_action_owner or prev.next_action_owner, x.due_date or prev.due_date
    if x.supersede_previous:
        for old in db.scalars(select(m.Update).where(m.Update.initiative_id == iid, m.Update.action_status == "Open")).all():
            old.action_status = "Superseded"
            old.working_notes = ((old.working_notes or "") + f"\n\nSuperseded by {uid}").strip()
    db.add(m.Update(id=uid, initiative_id=iid, update_date=d, update_type=x.update_type, summary=x.summary, movement=x.movement,
                    health=x.health, decision_needed=x.decision_needed, next_action=x.next_action, next_action_owner=x.next_action_owner,
                    due_date=x.due_date, action_status="Open", include_in_align=x.include_in_align, confidential=x.confidential,
                    working_notes=x.working_notes, include_in_md_update=x.include_in_md_update))
    # Keep the register current: the update is the source of the "now" fields.
    if x.health:
        i.health = x.health
    if x.decision_needed is not None:
        i.decision_needed = x.decision_needed or None
    if x.next_action:
        i.next_action, i.next_action_owner = x.next_action, x.next_action_owner
    if x.next_review_date:
        i.next_review_date = x.next_review_date
    i.last_reviewed_date = d
    db.commit()
    return {"id": uid, "message": f"Update logged for {i.name}"}


class UpdateEdit(BaseModel):
    action_status: str | None = None
    include_in_md_update: bool | None = None
    confidential: bool | None = None


@app.patch("/api/updates/{uid}")
def edit_update(uid: str, x: UpdateEdit, db: Session = Depends(get_db)):
    u = db.get(m.Update, uid)
    if not u:
        raise HTTPException(404, "Update not found")
    for k, v in x.model_dump(exclude_none=True).items():
        setattr(u, k, v)
    db.commit()
    return {"message": "Update saved"}


class ScoreIn(BaseModel):
    v_strategic_fit: int = Field(ge=0, le=2)
    v_operational_impact: int = Field(ge=0, le=2)
    v_client_user_impact: int = Field(ge=0, le=2)
    v_safety_risk_data_quality: int = Field(ge=0, le=2)
    v_scalability_reuse: int = Field(ge=0, le=2)
    c_technical: int = Field(ge=0, le=2)
    c_integration_data: int = Field(ge=0, le=2)
    c_operational_change: int = Field(ge=0, le=2)
    c_dependencies_stakeholders: int = Field(ge=0, le=2)
    c_commercial_legal_ip: int = Field(ge=0, le=2)
    confidence: str | None = "Medium"
    value_rationale: str | None = None
    complexity_rationale: str | None = None
    scored_by: str | None = None
    notes: str | None = None
    review_required: bool = False


@app.post("/api/initiatives/{iid}/scores")
def add_score(iid: str, x: ScoreIn, db: Session = Depends(get_db)):
    i = get_init(db, iid)
    d = today()
    sid = next_seq_id(db, m.Score, f"SCORE-{iid}-{d.isoformat()}")
    for old in db.scalars(select(m.Score).where(m.Score.initiative_id == iid, m.Score.active == True)).all():  # noqa: E712
        old.active = False
    s = m.Score(id=sid, initiative_id=iid, score_date=d, active=True, scoring_version="v0.3 portfolio app", **x.model_dump())
    s.recorded_value_total, s.recorded_complexity_total = s.value_total, s.complexity_total
    s.recorded_quadrant = L.quadrant(s.value_total, s.complexity_total, get_cuts(db))
    db.add(s)
    db.commit()
    return {"id": sid, "message": f"{i.name} re-scored: value {s.value_total}, complexity {s.complexity_total} → {s.recorded_quadrant}"}


class DecisionIn(BaseModel):
    decision: str
    decision_date: date | None = None
    rationale: str | None = None
    conditions: str | None = None
    decided_by: str | None = None
    forum: str | None = None
    stage_to: str | None = None
    health: str | None = None
    next_review_date: date | None = None
    next_action: str | None = None
    next_action_owner: str | None = None


def stage_label(k):
    n = L.stage_index(k)
    return L.STAGES[n]["label"] if n >= 0 else (k or "no stage")


@app.post("/api/initiatives/{iid}/decisions")
def add_decision(iid: str, x: DecisionIn, db: Session = Depends(get_db), update_type: str = "Decision"):
    i = get_init(db, iid)
    if x.decision not in L.DECISIONS:
        raise HTTPException(422, "Decision must be one of " + ", ".join(L.DECISIONS))
    d = x.decision_date or today()
    stage_from = i.stage
    db.add(m.Decision(initiative_id=iid, decision_date=d, decision=x.decision, stage_from=stage_from, stage_to=x.stage_to or stage_from,
                      rationale=x.rationale, conditions=x.conditions or x.next_action, decided_by=x.decided_by, forum=x.forum))
    if x.stage_to and x.stage_to != i.stage:
        i.stage = x.stage_to
    if x.decision == "Stop":
        i.portfolio_status = "Stopped"
    elif x.decision == "Hold":
        i.portfolio_status = "On Hold"
    elif x.decision == "Close":
        i.portfolio_status = "Closed / BAU"
    elif i.portfolio_status in ("On Hold", "Stopped", "Proposed", "Proposed/In Review"):
        i.portfolio_status = "Active"
    if x.next_review_date:
        i.next_review_date = x.next_review_date
    # Log it in the update history too, so the log stays the one complete record.
    moved = f"Stage: {stage_label(stage_from)} → {stage_label(i.stage)}." if i.stage != stage_from else ""
    label = L.DECISION_LABELS.get(x.decision, x.decision).upper()
    summary = (f"{moved} {x.rationale or ''}" if update_type == L.STAGE_MOVE else f"Decision: {label}. {moved} {x.rationale or ''}").strip()
    logged = add_update(iid, UpdateIn(update_type=update_type, update_date=d, summary=summary, decision_needed="", health=x.health,
                             movement="Progressed" if x.decision in ("Continue", "Scale", "Close") else "Changed Scope" if x.decision == "Pivot" else "No change",
                             next_action=x.next_action or x.conditions, next_action_owner=x.next_action_owner,
                             next_review_date=x.next_review_date), db)
    if x.decision in ("Stop", "Close"):
        # Finished work has no open action left.
        db.get(m.Update, logged["id"]).action_status = "Closed"
        db.commit()
    if update_type == L.STAGE_MOVE:
        return {"message": f"{i.name} moved to {stage_label(i.stage)}"}
    return {"message": f"{L.DECISION_LABELS.get(x.decision, x.decision)} recorded for {i.name}"}


class StageMoveIn(BaseModel):
    stage_to: str
    rationale: str = Field(min_length=3)
    agreed_by: str | None = None
    next_review_date: date | None = None
    next_action: str | None = None
    next_action_owner: str | None = None


@app.post("/api/initiatives/{iid}/stage")
def move_stage(iid: str, x: StageMoveIn, db: Session = Depends(get_db)):
    """Move an initiative to another stage (passing a gate, or stepping back). Logged as a decision and an update."""
    i = get_init(db, iid)
    if x.stage_to not in L.STAGE_KEYS:
        raise HTTPException(422, "Unknown stage")
    if x.stage_to == i.stage:
        raise HTTPException(422, f"{i.name} is already in {stage_label(i.stage)}")
    forward = L.stage_index(x.stage_to) > L.stage_index(i.stage)
    return add_decision(iid, DecisionIn(decision="Continue" if forward else "Pivot", stage_to=x.stage_to, rationale=x.rationale,
                                        decided_by=x.agreed_by, next_review_date=x.next_review_date, next_action=x.next_action,
                                        next_action_owner=x.next_action_owner, forum="Stage move"), db, update_type=L.STAGE_MOVE)


class AlignmentIn(BaseModel):
    alignment_type: str
    area: str = Field(min_length=2)
    role: str = "Supporting"


@app.post("/api/initiatives/{iid}/alignments")
def add_alignment(iid: str, x: AlignmentIn, db: Session = Depends(get_db)):
    get_init(db, iid)
    code = "SP" if x.alignment_type == "Strategic Priority" else "VP"
    aid = next_seq_id(db, m.Alignment, f"ALIGN-{iid}-{code}")
    db.add(m.Alignment(id=aid, initiative_id=iid, alignment_type=x.alignment_type, area=x.area, role=x.role, active=True,
                       evidence_basis="Added in portfolio app"))
    db.commit()
    return {"message": f"{x.area} added"}


@app.delete("/api/alignments/{aid}")
def remove_alignment(aid: str, db: Session = Depends(get_db)):
    a = db.get(m.Alignment, aid)
    if not a:
        raise HTTPException(404, "Alignment not found")
    a.active = False
    db.commit()
    return {"message": f"{a.area} removed"}


# ---------------------------------------------------------------- logs
@app.get("/api/updates")
def list_updates(db: Session = Depends(get_db)):
    names = names_map(db)
    rows = db.scalars(select(m.Update).order_by(m.Update.update_date.desc(), m.Update.id.desc())).all()
    return [update_dict(u, names) for u in rows]


@app.get("/api/decisions")
def list_decisions(db: Session = Depends(get_db)):
    names = names_map(db)
    rows = db.scalars(select(m.Decision).order_by(m.Decision.decision_date.desc(), m.Decision.id.desc())).all()
    return [decision_dict(x, names) for x in rows]


@app.get("/api/alignment-map")
def alignment_map(db: Session = Depends(get_db)):
    cards = {c["id"]: c for c in all_cards(db)}
    rows = db.scalars(select(m.Alignment).where(m.Alignment.active == True)).all()  # noqa: E712
    out = {"Strategic Priority": {}, "Value Pocket": {}}
    for a in rows:
        if a.initiative_id not in cards or a.alignment_type not in out:
            continue
        cell = out[a.alignment_type].setdefault(a.area, {})
        prev = cell.get(a.initiative_id)
        if prev != "Primary":
            cell[a.initiative_id] = a.role or "Supporting"
    return {"initiatives": list(cards.values()),
            "areas": {t: [{"area": k, "links": v, "primary": sum(1 for r in v.values() if r == "Primary"), "total": len(v)}
                          for k, v in sorted(d.items(), key=lambda kv: -len(kv[1]))] for t, d in out.items()}}


# ---------------------------------------------------------------- settings
def get_aliases(db) -> dict:
    """Name aliases, e.g. "CB = Carlie", so one person isn't counted twice in the resource view."""
    s = db.get(m.Setting, "aliases")
    out = {}
    for line in (s.value if s else "").splitlines():
        if "=" in line:
            short, full = line.split("=", 1)
            if short.strip() and full.strip():
                out[short.strip().lower()] = full.strip()
    return out


class AliasesIn(BaseModel):
    text: str = Field(max_length=4000)


@app.put("/api/settings/aliases")
def set_aliases(x: AliasesIn, db: Session = Depends(get_db)):
    s = db.get(m.Setting, "aliases") or m.Setting(key="aliases", value="")
    s.value = x.text.strip()
    db.add(s)
    db.commit()
    return {"message": f"{len(get_aliases(db))} name aliases saved"}


@app.get("/api/resources")
def resources(db: Session = Depends(get_db)):
    """Who is carrying what: live initiatives each person owns or sponsors, their open actions, and effort weight."""
    aliases = get_aliases(db)
    cards = [c for c in all_cards(db) if c["status"] not in ("Stopped", "Closed / BAU")]
    people: dict = {}

    def person(n):
        return people.setdefault(n, {"name": n, "owns": [], "sponsors": [], "actions": [], "weight": 0})
    for c in cards:
        brief = {"id": c["id"], "name": c["name"], "effort": c["effort"], "priority": c["priority"], "health_class": c["health_class"],
                 "stage": c["stage"], "type": c["bucket"]}
        for n in L.split_people(c["owner"], aliases):
            p = person(n)
            p["owns"].append(brief)
            p["weight"] += L.EFFORT_WEIGHT.get(c["effort"] or "Unknown", 2)
        for n in L.split_people(c["sponsor"], aliases):
            person(n)["sponsors"].append(brief)
        if c["next_action"]:
            for n in L.split_people(c["next_action_owner"], aliases):
                person(n)["actions"].append({"id": c["id"], "name": c["name"], "action": c["next_action"], "due": c["next_action_due"]})
    t = today().isoformat()
    for p in people.values():
        p["overdue"] = sum(1 for a in p["actions"] if a["due"] and a["due"] < t)
    rows = sorted(people.values(), key=lambda p: (-p["weight"], -len(p["actions"]), p["name"].lower()))
    by_type = {}
    for c in cards:
        r = by_type.setdefault(c["bucket"] or "Not set", {e: 0 for e in L.EFFORTS + ["Not set"]})
        r[c["effort"] or "Not set"] += 1
    return {"people": rows, "by_type": by_type, "efforts": L.EFFORTS, "aliases": "\n".join(f"{k.upper() if len(k) <= 3 else k} = {v}" for k, v in aliases.items()),
            "unowned": [{"id": c["id"], "name": c["name"]} for c in cards if not L.split_people(c["owner"], aliases)]}


class CutsIn(BaseModel):
    value_cut: int = Field(ge=1, le=10)
    complexity_cut: int = Field(ge=1, le=10)


@app.put("/api/settings/cuts")
def set_cuts(x: CutsIn, db: Session = Depends(get_db)):
    for k, v in x.model_dump().items():
        s = db.get(m.Setting, k) or m.Setting(key=k, value="")
        s.value = str(v)
        db.add(s)
    db.commit()
    return {"message": f"Quadrant lines saved: high value ≥ {x.value_cut}, high complexity ≥ {x.complexity_cut}"}


# ---------------------------------------------------------------- import / export
class FileIn(BaseModel):
    filename: str
    content_base64: str


class ImportIn(BaseModel):
    files: list[FileIn]


def _files(x: ImportIn):
    out = []
    for f in x.files:
        if not f.filename.lower().endswith(".csv"):
            raise HTTPException(422, f"{f.filename}: export the list as CSV (MS Lists → Export → Export to CSV)")
        out.append((f.filename, base64.b64decode(f.content_base64)))
    return out


def _public(reports):
    return [{k: v for k, v in r.items() if k != "records"} for r in reports]


@app.post("/api/import/check")
def import_check(x: ImportIn, db: Session = Depends(get_db)):
    return {"files": _public(I.plan(db, _files(x), get_cuts(db)))}


@app.post("/api/import/apply")
def import_apply(x: ImportIn, db: Session = Depends(get_db)):
    reports = I.plan(db, _files(x), get_cuts(db))
    backup = backup_database()
    counts = I.apply(db, reports)
    msg = "Loaded " + ", ".join(f"{n} from {k}" for k, n in counts.items()) if counts else "Nothing to load"
    return {"message": msg, "backup": Path(backup).name if backup else None, "files": _public(reports)}


@app.get("/api/export/{kind}.csv")
def export(kind: str, db: Session = Depends(get_db)):
    if kind not in I.KINDS:
        raise HTTPException(404, "Unknown list")
    body = I.export_csv(db, kind, get_cuts(db))
    name = I.KINDS[kind]["label"].replace(" / ", "_").replace(" ", "_")
    return Response(body.encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="WSG_{name}_{today():%Y%m%d}.csv"'})
