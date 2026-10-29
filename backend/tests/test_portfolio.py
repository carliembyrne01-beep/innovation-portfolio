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
