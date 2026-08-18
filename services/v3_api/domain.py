"""Contrats metier du service LIDAL Pulse V3.

La V3 est additive et ne depend pas des schemas historiques de ``api/``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class MonitorObjective(StrEnum):
    CUSTOMER_EXPERIENCE = "customer_experience"
    REPUTATION = "reputation"
    CAMPAIGN = "campaign"
    COMPETITION = "competition"
    ISSUE = "issue"


class TargetType(StrEnum):
    BRAND = "brand"
    ORGANIZATION = "organization"
    PRODUCT = "product"
    CAMPAIGN = "campaign"
    COMPETITOR = "competitor"
    SUBJECT = "subject"


class SourcePlatform(StrEnum):
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    GOOGLE_MAPS = "google_maps"


class SignalSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SignalStatus(StrEnum):
    NEW = "new"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    CONVERTED = "converted"


class WorkStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    RESOLVED = "resolved"
    CLOSED = "closed"


class MonitorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    objective: MonitorObjective
    target_type: TargetType
    target_name: str = Field(min_length=2, max_length=160)
    aliases: list[str] = Field(default_factory=list, max_length=50)
    exclusions: list[str] = Field(default_factory=list, max_length=50)
    languages: list[str] = Field(default_factory=lambda: ["fr", "ar", "darija"])
    territories: list[str] = Field(default_factory=lambda: ["DZ"])
    sources: list[SourcePlatform] = Field(min_length=1)
    competitors: list[str] = Field(default_factory=list, max_length=20)
    frequency_minutes: int = Field(default=360, ge=15, le=43_200)
    max_monthly_documents: int = Field(default=100_000, ge=100, le=5_000_000)
    max_monthly_cost_dzd: int = Field(default=50_000, ge=0, le=10_000_000)

    @model_validator(mode="after")
    def normalize_terms(self) -> "MonitorCreate":
        self.aliases = sorted({value.strip() for value in self.aliases if value.strip()})
        self.exclusions = sorted({value.strip() for value in self.exclusions if value.strip()})
        self.languages = sorted({value.strip().lower() for value in self.languages if value.strip()})
        self.territories = sorted({value.strip().upper() for value in self.territories if value.strip()})
        self.competitors = sorted({value.strip() for value in self.competitors if value.strip()})
        return self


class MonitorOut(MonitorCreate):
    id: str
    organization_id: str
    active: bool
    last_collected_at: datetime | None
    coverage_note: str | None
    created_at: datetime
    updated_at: datetime


class SignalTransition(BaseModel):
    status: SignalStatus
    reason: str = Field(min_length=3, max_length=500)


class CaseCreate(BaseModel):
    signal_id: str
    title: str = Field(min_length=3, max_length=240)
    priority: SignalSeverity
    owner_id: str | None = None
    owner_name: str | None = Field(default=None, max_length=160)
    due_at: datetime | None = None
    expected_outcome: str | None = Field(default=None, max_length=1_000)

    @model_validator(mode="after")
    def require_owner_and_due_date(self) -> "CaseCreate":
        if not self.owner_id and not self.owner_name:
            raise ValueError("un responsable est obligatoire")
        if self.due_at is None:
            raise ValueError("une echeance est obligatoire")
        return self


class ActionCreate(BaseModel):
    case_id: str
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=3, max_length=2_000)
    owner_id: str | None = None
    owner_name: str | None = Field(default=None, max_length=160)
    due_at: datetime | None = None
    expected_impact: str | None = Field(default=None, max_length=1_000)
    metric_id: str | None = Field(default=None, max_length=160)


class ActionTransition(BaseModel):
    status: WorkStatus
    result_value: float | None = None
    comment: str = Field(min_length=3, max_length=1_000)

    @model_validator(mode="after")
    def require_measured_result_when_complete(self) -> "ActionTransition":
        if self.status in {WorkStatus.RESOLVED, WorkStatus.CLOSED} and self.result_value is None:
            raise ValueError("result_value est obligatoire pour terminer une action")
        return self


class AgentReference(BaseModel):
    kind: Literal["metric", "observation", "mention"]
    id: str = Field(min_length=1, max_length=160)
    label: str = Field(min_length=1, max_length=240)


class AgentDraftRequest(BaseModel):
    draft_type: str = Field(pattern="^(explanation|comparison|case_summary|action_plan|report|response)$")
    references: list[AgentReference] = Field(min_length=1, max_length=50)
    instruction: str = Field(min_length=3, max_length=2_000)


class ReportCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    report_type: str = Field(pattern="^(daily|weekly|crisis|reputation|territory|product)$")
    period_start: datetime
    period_end: datetime

    @model_validator(mode="after")
    def validate_period(self) -> "ReportCreate":
        if self.period_end <= self.period_start:
            raise ValueError("period_end doit etre posterieur a period_start")
        return self
