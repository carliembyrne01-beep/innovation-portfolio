"""Initiative Portfolio data model.

Mirrors the four MS Lists the framework started in, joined by Initiative ID:

  Initiative Register   -> Initiative
  Scoring Component     -> Score         (history; one is active per initiative)
  Alignment / Value     -> Alignment     (strategic priorities and value pockets)
  Initiative Updates    -> Update        (dated log; replaces history packed into register cells)

and adds Decision (the Stop / Hold / Continue / Pivot / Scale record from a review)
and Setting (matrix cut-off lines).
"""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def now():
    return datetime.now().replace(microsecond=0)


class Initiative(Base):
    __tablename__ = "initiatives"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # INIT-0001
    name: Mapped[str] = mapped_column(String(300))
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sponsor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    business_areas: Mapped[list] = mapped_column(JSON, default=list)
    portfolio_bucket: Mapped[str | None] = mapped_column(String(100), nullable=True)
    primary_route: Mapped[list] = mapped_column(JSON, default=list)
    stage: Mapped[str | None] = mapped_column(String(60), nullable=True)
    value_types: Mapped[list] = mapped_column(JSON, default=list)
    portfolio_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(30), nullable=True)
    health: Mapped[str | None] = mapped_column(String(30), nullable=True)
    decision_needed: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action_owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_reviewed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    evidence_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dependencies: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategic_alignment_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(60), nullable=True)
    integrated_platform_link: Mapped[str | None] = mapped_column(String(200), nullable=True)
    commercial_decision_required: Mapped[str | None] = mapped_column(String(200), nullable=True)
    client_impact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    funding_ask: Mapped[str | None] = mapped_column(String(200), nullable=True)
    effort: Mapped[str | None] = mapped_column(String(40), nullable=True)  # L.EFFORTS scale
    parent_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)  # "part of" another initiative
    related_initiatives: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Score(Base):
    __tablename__ = "scores"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)  # SCORE-INIT-0001-2026-06-17-01
    initiative_id: Mapped[str] = mapped_column(ForeignKey("initiatives.id"), index=True)
    score_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    v_strategic_fit: Mapped[int] = mapped_column(Integer, default=0)
    v_operational_impact: Mapped[int] = mapped_column(Integer, default=0)
    v_client_user_impact: Mapped[int] = mapped_column(Integer, default=0)
    v_safety_risk_data_quality: Mapped[int] = mapped_column(Integer, default=0)
    v_scalability_reuse: Mapped[int] = mapped_column(Integer, default=0)
    c_technical: Mapped[int] = mapped_column(Integer, default=0)
    c_integration_data: Mapped[int] = mapped_column(Integer, default=0)
    c_operational_change: Mapped[int] = mapped_column(Integer, default=0)
    c_dependencies_stakeholders: Mapped[int] = mapped_column(Integer, default=0)
    c_commercial_legal_ip: Mapped[int] = mapped_column(Integer, default=0)
    recorded_value_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_complexity_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_quadrant: Mapped[str | None] = mapped_column(String(40), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(30), nullable=True)
    value_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    complexity_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    est_one_off_cost_aud: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_annual_run_cost_aud: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_annual_benefit_aud: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_revenue_uplift_aud: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_cost_avoidance_aud: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_roi_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_payback_months: Mapped[float | None] = mapped_column(Float, nullable=True)
    hours_saved_per_month: Mapped[float | None] = mapped_column(Float, nullable=True)
    cycle_time_reduction_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    rework_reduction_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    safety_exposure_reduction_count: Mapped[float | None] = mapped_column(Float, nullable=True)
    tangible_confidence: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tangible_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    scored_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    scoring_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    VALUE = ["v_strategic_fit", "v_operational_impact", "v_client_user_impact", "v_safety_risk_data_quality", "v_scalability_reuse"]
    COMPLEXITY = ["c_technical", "c_integration_data", "c_operational_change", "c_dependencies_stakeholders", "c_commercial_legal_ip"]

    @property
    def value_total(self) -> int:
        return sum(getattr(self, k) or 0 for k in self.VALUE)

    @property
    def complexity_total(self) -> int:
        return sum(getattr(self, k) or 0 for k in self.COMPLEXITY)


class Alignment(Base):
    __tablename__ = "alignments"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)  # ALIGN-INIT-0001-SP-01
    initiative_id: Mapped[str] = mapped_column(ForeignKey("initiatives.id"), index=True)
    alignment_type: Mapped[str] = mapped_column(String(40))  # Strategic Priority | Value Pocket
    area: Mapped[str] = mapped_column(String(120))
    role: Mapped[str | None] = mapped_column(String(30), nullable=True)  # Primary | Supporting
    evidence_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)


class Update(Base):
    __tablename__ = "updates"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)  # UPD-INIT-0001-2026-06-15-01
    initiative_id: Mapped[str] = mapped_column(ForeignKey("initiatives.id"), index=True)
    update_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    update_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    movement: Mapped[str | None] = mapped_column(String(60), nullable=True)
    health: Mapped[str | None] = mapped_column(String(30), nullable=True)
    decision_needed: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action_owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    action_status: Mapped[str | None] = mapped_column(String(30), nullable=True)  # Open | Closed | Superseded
    include_in_align: Mapped[bool] = mapped_column(Boolean, default=False)
    confidential: Mapped[bool] = mapped_column(Boolean, default=False)
    working_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    include_in_md_update: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    initiative_id: Mapped[str] = mapped_column(ForeignKey("initiatives.id"), index=True)
    decision_date: Mapped[date] = mapped_column(Date)
    decision: Mapped[str] = mapped_column(String(20))  # Stop | Hold | Continue | Pivot | Scale
    stage_from: Mapped[str | None] = mapped_column(String(60), nullable=True)
    stage_to: Mapped[str | None] = mapped_column(String(60), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    forum: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(String(400))
