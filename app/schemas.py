from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator

STATUSES = ["Saved", "Applied", "Screening", "Interview", "Offer", "Rejected"]
RESPONSE_STATUSES = {"Screening", "Interview", "Offer", "Rejected"}


class ApplicationIn(BaseModel):
    company: str
    role: str
    location: Optional[str] = None
    url: Optional[str] = None
    status: str = "Saved"
    posting_text: str = ""
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        return v

    @field_validator("company", "role")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class ApplicationOut(BaseModel):
    id: int
    company: str
    role: str
    location: Optional[str]
    url: Optional[str]
    status: str
    skills: list[str]
    match_score: Optional[float]
    notes: Optional[str]
    applied_on: Optional[date]
    responded_on: Optional[date]
    last_update: date


class CVIn(BaseModel):
    text: str
