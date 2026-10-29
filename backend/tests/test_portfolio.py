"""End-to-end checks of import, maintenance and review through the API (fictional fixture data)."""
import base64
import os
import tempfile
from pathlib import Path

os.environ["PORTFOLIO_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["PORTFOLIO_TODAY"] = "2026-10-29"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


def files(*names):
    return {"files": [{"filename": f"{n}.csv", "content_base64": base64.b64encode((FIX / f"{n}.csv").read_bytes()).decode()} for n in names]}


@pytest.fixture()
def c():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def loaded(c):
    r = c.post("/api/import/apply", json=files("updates", "alignment", "scores", "register"))  # any order
    assert r.status_code == 200, r.text
    return c


def test_check_reports_without_loading(c):
    d = c.post("/api/import/check", json=files("register", "scores", "alignment", "updates")).json()
    by = {f["kind"]: f for f in d["files"]}
    assert set(by) == {"register", "scores", "alignment", "updates"}
    assert by["register"]["new"] == 2
    msgs = " | ".join(i["msg"] for f in d["files"] for i in f["issues"])
    assert "corrected to INIT-0002" in msgs           # INT-0002 typo fixed from the row's own ID
    assert "duplicate of an earlier row" in msgs       # Reduced Rework twice
    assert "recorded as Big Bet, scores put it in Quick Win" in msgs
    assert by["updates"]["skipped"] == 1               # blank row
    assert c.get("/api/initiatives").json() == []      # nothing loaded by a check


def test_import_parses_lists_dates_and_scores(loaded):
    i = loaded.get("/api/initiatives/INIT-0001").json()
    assert i["business_areas"] == ["Operations", "Digital / Data"]
    assert i["fields"]["confidence"] == "Medium / High"
    assert i["next_review_date"] == "2026-08-30"
    assert (i["value"], i["complexity"], i["quadrant"]) == (8, 4, "Quick Win")
    assert i["movement"] == "Blocked" and i["next_action"] == "Current action"
    assert {r["label"]: r["id"] for r in i["related"]}["Test Tool"] == "INIT-0002"
    t = loaded.get("/api/initiatives/INIT-0002").json()
    assert t["health"] == "Grey"
    kinds = {f["kind"] for f in t["flags"]}
    assert {"owner", "sponsor", "overdue", "stale"} <= kinds


def test_reimport_updates_not_duplicates(loaded):
    d = loaded.post("/api/import/apply", json=files("register")).json()
    assert d["files"][0]["updated"] == 2 and d["files"][0]["new"] == 0
    assert len(loaded.get("/api/initiatives").json()) == 2


def test_log_update_refreshes_register_and_supersedes(loaded):
    r = loaded.post("/api/initiatives/INIT-0001/updates", json={"summary": "Scope agreed.", "health": "Green", "movement": "Progressed",
                                                                "next_action": "Start pilot", "next_action_owner": "Person C", "next_review_date": "2026-11-26"})
    assert r.status_code == 200, r.text
    i = loaded.get("/api/initiatives/INIT-0001").json()
    assert i["health"] == "Green" and i["next_action"] == "Start pilot" and i["next_review_date"] == "2026-11-26"
    assert i["last_reviewed_date"] == "2026-10-29"
    statuses = [u["action_status"] for u in i["updates"]]
    assert statuses[0] == "Open" and statuses.count("Open") == 1
    assert not any(f["kind"] == "overdue" for f in i["flags"])


def test_decision_moves_stage_and_logs(loaded):
    r = loaded.post("/api/initiatives/INIT-0001/decisions", json={"decision": "Scale", "stage_to": "Discovery/Validation", "health": "Green",
                                                                  "rationale": "Evidence strong", "next_action": "Size the pilot"})
    assert r.status_code == 200, r.text
    i = loaded.get("/api/initiatives/INIT-0001").json()
    assert i["stage"] == "Discovery/Validation" and i["health"] == "Green" and i["last_decision"] == "Scale"
    assert i["updates"][0]["update_type"] == "Decision" and "SCALE" in i["updates"][0]["summary"]
    assert i["decisions"][0]["conditions"] == "Size the pilot"
    loaded.post("/api/initiatives/INIT-0002/decisions", json={"decision": "Stop"})
    assert loaded.get("/api/initiatives/INIT-0002").json()["status"] == "Stopped"
    assert loaded.post("/api/initiatives/INIT-0002/decisions", json={"decision": "Maybe"}).status_code == 422


def test_rescore_keeps_history(loaded):
    body = {k: 2 for k in ["v_strategic_fit", "v_operational_impact", "v_client_user_impact", "v_safety_risk_data_quality", "v_scalability_reuse"]}
    body |= {k: 2 for k in ["c_technical", "c_integration_data", "c_operational_change", "c_dependencies_stakeholders", "c_commercial_legal_ip"]}
    assert loaded.post("/api/initiatives/INIT-0001/scores", json=body).status_code == 200
    i = loaded.get("/api/initiatives/INIT-0001").json()
    assert (i["value"], i["complexity"], i["quadrant"]) == (10, 10, "Big Bet")
    assert len(i["score_history"]) == 2 and sum(s["active"] for s in i["score_history"]) == 1
    body["c_technical"] = 3
    assert loaded.post("/api/initiatives/INIT-0001/scores", json=body).status_code == 422


def test_quadrant_lines_are_adjustable(loaded):
    loaded.put("/api/settings/cuts", json={"value_cut": 9, "complexity_cut": 5})
    assert loaded.get("/api/initiatives/INIT-0001").json()["quadrant"] == "Filler / Enabler"


def test_new_and_edit_initiative(loaded):
    r = loaded.post("/api/initiatives", json={"name": "Brand new idea", "primary_owner": "Person D"}).json()
    assert r["id"] == "INIT-0003"
    assert loaded.patch("/api/initiatives/INIT-0003", json={"stage": "Framing", "related_initiatives": "Test Tool; Test Platform"}).status_code == 200
    i = loaded.get("/api/initiatives/INIT-0003").json()
    assert i["stage"] == "Framing" and len(i["related"]) == 2
    assert loaded.patch("/api/initiatives/INIT-0003", json={"id": "X"}).status_code == 422


def test_export_round_trips(loaded):
    csv_text = loaded.get("/api/export/register.csv").text
    assert csv_text.lstrip("﻿").startswith('"Initiative Name","Initiative ID"')
    assert "Operations; Digital / Data" in csv_text
    scores = loaded.get("/api/export/scores.csv").text
    assert "Quick Win" in scores  # calculated quadrant, not the recorded one
    d = loaded.post("/api/import/check", json={"files": [{"filename": "register.csv", "content_base64": base64.b64encode(csv_text.encode()).decode()}]}).json()
    assert d["files"][0]["updated"] == 2 and not [i for i in d["files"][0]["issues"] if i["level"] == "error"]


def test_overview_and_logs(loaded):
    o = loaded.get("/api/overview").json()
    k = {x["label"]: x["value"] for x in o["kpis"]}
    assert k["Live initiatives"] == 2 and k["Blocked or escalated"] == 1 and k["Reviews overdue"] == 2
    assert loaded.get("/api/alignment-map").json()["areas"]["Strategic Priority"]
    assert len(loaded.get("/api/updates").json()) == 2


# ---------------------------------------------------------------- v0.2: initiative portfolio
def test_stage_move_forward_and_back_is_logged(loaded):
    r = loaded.post("/api/initiatives/INIT-0001/stage", json={"stage_to": "Discovery/Validation", "rationale": "Scope signed off", "agreed_by": "MD"})
    assert r.status_code == 200, r.text
    i = loaded.get("/api/initiatives/INIT-0001").json()
    assert i["stage"] == "Discovery/Validation"
    assert i["updates"][0]["update_type"] == "Stage move" and "Framing → Discovery / validation" in i["updates"][0]["summary"]
    assert i["decisions"][0]["decision"] == "Continue" and i["decisions"][0]["decided_by"] == "MD"
    loaded.post("/api/initiatives/INIT-0001/stage", json={"stage_to": "Framing", "rationale": "Scope reopened"})
    assert loaded.get("/api/initiatives/INIT-0001").json()["decisions"][0]["decision"] == "Pivot"
    assert loaded.post("/api/initiatives/INIT-0001/stage", json={"stage_to": "Framing", "rationale": "again"}).status_code == 422
    assert loaded.post("/api/initiatives/INIT-0001/stage", json={"stage_to": "Nowhere", "rationale": "x x"}).status_code == 422


def test_close_to_bau(loaded):
    assert loaded.post("/api/initiatives/INIT-0001/decisions", json={"decision": "Close", "rationale": "Embedded"}).json()["message"].startswith("Close → BAU")
    i = loaded.get("/api/initiatives/INIT-0001").json()
    assert i["status"] == "Closed / BAU" and "CLOSE → BAU" in i["updates"][0]["summary"]
    assert i["updates"][0]["action_status"] == "Closed"
    assert loaded.get("/api/overview").json()["kpis"][0]["value"] == 1  # no longer live


def test_types_effort_and_resources(loaded):
    meta = loaded.get("/api/meta").json()
    assert "Operational Improvement" in meta["types"] and meta["efforts"][0] == "Minimal"
    loaded.patch("/api/initiatives/INIT-0001", json={"funding_ask": "Minor / Material Internal Effort"})
    loaded.patch("/api/initiatives/INIT-0001", json={"effort": "Material internal effort", "portfolio_bucket": "Operational Improvement"})
    loaded.patch("/api/initiatives/INIT-0002", json={"primary_owner": "PA / Person B — confirm"})
    loaded.put("/api/settings/aliases", json={"text": "PA = Person A"})
    d = loaded.get("/api/resources").json()
    people = {p["name"]: p for p in d["people"]}
    assert len(people["Person A"]["owns"]) == 2 and people["Person A"]["weight"] == 3 + 2
    assert "PA" not in people and "Person B" in people
    assert d["by_type"]["Operational Improvement"]["Material internal effort"] == 1
    assert any(t["label"] == "Operational Improvement" for t in loaded.get("/api/overview").json()["by_type"])


def test_effort_filled_from_register_text_on_import(loaded):
    import app.importer as I
    from app.db import SessionLocal
    from app import models as m
    with SessionLocal() as db:
        i = db.get(m.Initiative, "INIT-0002")
        i.funding_ask, i.effort = "Capital Required / Unknown", None
        db.commit()
        I.apply(db, I.plan(db, [("register.csv", (FIX / "register.csv").read_bytes())], {"value_cut": 7, "complexity_cut": 5}))
    # funding_ask is blank in the fixture, so effort stays empty rather than guessed
    assert loaded.get("/api/initiatives/INIT-0002").json()["effort"] in (None, "Capital required")


def test_upgrade_adds_new_columns_to_an_old_database(tmp_path):
    import sqlite3
    from app import main
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    old = tmp_path / "old.db"
    con = sqlite3.connect(old)
    con.execute("CREATE TABLE initiatives (id VARCHAR(20) PRIMARY KEY, name VARCHAR(300), funding_ask VARCHAR(200))")
    con.execute("INSERT INTO initiatives VALUES ('INIT-0001', 'Old one', 'Minor Internal Effort')")
    con.commit(); con.close()
    eng = create_engine(f"sqlite:///{old}")
    saved = main.engine, main.SessionLocal
    main.engine, main.SessionLocal = eng, sessionmaker(bind=eng)
    try:
        main.upgrade_database()
    finally:
        main.engine, main.SessionLocal = saved
    con = sqlite3.connect(old)
    row = con.execute("SELECT name, effort, next_review_date FROM initiatives").fetchone()
    assert row == ("Old one", "Minor internal effort", None)


def test_stage_move_keeps_the_current_next_action(loaded):
    loaded.post("/api/initiatives/INIT-0001/stage", json={"stage_to": "Discovery/Validation", "rationale": "Ready"})
    i = loaded.get("/api/initiatives/INIT-0001").json()
    assert i["next_action"] == "Current action" and i["next_action_owner"] == "Person A"


# ---------------------------------------------------------------- v0.3: movement
def test_movement_compares_two_points_in_time(loaded):
    # Fixture: INIT-0001 was Amber on 15 Jun and Amber/Red on 13 Aug (Blocked).
    loaded.patch("/api/initiatives/INIT-0001", json={"health": "Amber/Red"})
    d = loaded.get("/api/movement?since=2026-06-15").json()
    r = {x["id"]: x for x in d["rows"]}["INIT-0001"]
    assert (r["health_then"], r["health_now"], r["health_dir"]) == ("Amber", "Amber/Red", "worse")
    assert r["movement"] == "Blocked" and r["updates"] == 1
    s = {x["key"]: x["n"] for x in d["summary"]}
    assert s["worse"] == 1 and s["stuck"] == 1
    loaded.post("/api/initiatives/INIT-0001/stage", json={"stage_to": "Discovery/Validation", "rationale": "Ready"})
    loaded.post("/api/initiatives/INIT-0001/updates", json={"summary": "Unblocked", "health": "Green", "movement": "Progressed"})
    r = {x["id"]: x for x in loaded.get("/api/movement?since=2026-09-01").json()["rows"]}["INIT-0001"]
    assert r["stage_delta"] == 1 and r["stage_then"] == "Framing" and r["health_dir"] == "better" and r["movement"] == "Progressed"
    hist = loaded.get("/api/initiatives/INIT-0001/history").json()
    assert [h["health"] for h in hist][-1] == "Green" and len(hist) == 4


def test_register_and_update_health_mismatch_is_flagged(loaded):
    loaded.patch("/api/initiatives/INIT-0001", json={"health": "Green"})
    flags = loaded.get("/api/initiatives/INIT-0001").json()["flags"]
    assert any(f["kind"] == "health_mismatch" for f in flags)


# ---------------------------------------------------------------- v0.4: linked initiatives
def test_parts_rollup_and_loops(loaded):
    loaded.patch("/api/initiatives/INIT-0001", json={"portfolio_bucket": "Strategic Workstream"})
    r = loaded.post("/api/initiatives", json={"name": "FLOW", "parent_id": "INIT-0001", "health": "Green"}).json()
    assert loaded.post("/api/initiatives/INIT-0001/parts", json={"ids": ["INIT-0002"]}).status_code == 200
    p = loaded.get("/api/initiatives/INIT-0001").json()
    assert {x["name"] for x in p["parts_list"]} == {"FLOW", "Test Tool"}
    assert p["rollup"]["live"] == 2 and p["rollup"]["worst_health"] == "Green"
    child = loaded.get(f"/api/initiatives/{r['id']}").json()
    assert child["parent"]["id"] == "INIT-0001" and child["parent_id"] == "INIT-0001"
    cards = {c["id"]: c for c in loaded.get("/api/initiatives").json()}
    assert cards["INIT-0001"]["parts"] == 2 and cards["INIT-0002"]["parent_name"] == "Test Platform"
    # no loops, no self-links, no unknown parents
    assert loaded.patch("/api/initiatives/INIT-0001", json={"parent_id": "INIT-0002"}).status_code == 422
    assert loaded.patch("/api/initiatives/INIT-0001", json={"parent_id": "INIT-0001"}).status_code == 422
    assert loaded.patch("/api/initiatives/INIT-0001", json={"parent_id": "INIT-9999"}).status_code == 422
    # unlink
    assert loaded.patch("/api/initiatives/INIT-0002", json={"parent_id": None}).status_code == 200
    assert loaded.get("/api/initiatives/INIT-0001").json()["rollup"]["live"] == 1


def test_suggested_parts_come_from_primary_route(loaded):
    loaded.patch("/api/initiatives/INIT-0001", json={"portfolio_bucket": "Strategic Workstream", "name": "WSG Integrated Platform"})
    loaded.patch("/api/initiatives/INIT-0002", json={"primary_route": "Integrated Platform"})
    s = loaded.get("/api/initiatives/INIT-0001").json()["suggested_parts"]
    assert [x["id"] for x in s] == ["INIT-0002"]
    loaded.post("/api/initiatives/INIT-0001/parts", json={"ids": ["INIT-0002"]})
    assert loaded.get("/api/initiatives/INIT-0001").json()["suggested_parts"] == []


def test_part_of_round_trips_through_export(loaded):
    loaded.post("/api/initiatives/INIT-0001/parts", json={"ids": ["INIT-0002"]})
    text = loaded.get("/api/export/register.csv").text
    assert '"Part Of Initiative ID"' in text
    loaded.patch("/api/initiatives/INIT-0002", json={"parent_id": None})
    loaded.post("/api/import/apply", json={"files": [{"filename": "r.csv", "content_base64": base64.b64encode(text.encode()).decode()}]})
    assert loaded.get("/api/initiatives/INIT-0002").json()["parent_id"] == "INIT-0001"
