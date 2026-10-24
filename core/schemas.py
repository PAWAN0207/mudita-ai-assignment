
from typing import Literal

from pydantic import BaseModel, Field


# Assignment 1: Sales Assistant

class LeadQualification(BaseModel):
    status: Literal[
        "qualified",
        "not_qualified",
        "needs_more_information",
    ]

    evidence: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)

    service_interest: str | None = None
    budget_inr: int | None = Field(default=None, ge=0)
    timeline_days: int | None = Field(default=None, ge=0)


class SalesConversationResponse(BaseModel):
    reply: str
    extracted_facts: dict = Field(default_factory=dict)
    follow_up_required: bool = False


# Assignment 2: Multi-Agent Coordinator

class SourceFact(BaseModel):
    fact_id: str
    text: str
    source_reference: str
    confidence: Literal["high", "medium", "low"]


class IntakeOutput(BaseModel):
    decisions: list[SourceFact] = Field(default_factory=list)
    requirements: list[SourceFact] = Field(default_factory=list)
    constraints: list[SourceFact] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class PlannedTask(BaseModel):
    task_id: str
    title: str
    owner: str | None = None
    deadline: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    supported_facts: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)



class ReviewIssue(BaseModel):
    task_id: str | None = None
    issue: str
    correction: str


class ReviewOutput(BaseModel):
    approved: bool
    issues: list[ReviewIssue] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)


