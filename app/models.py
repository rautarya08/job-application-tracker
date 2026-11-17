from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str]
    role: Mapped[str]
    location: Mapped[Optional[str]]
    url: Mapped[Optional[str]]
    status: Mapped[str] = mapped_column(default="Saved")
    posting_text: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    match_score: Mapped[Optional[float]]
    notes: Mapped[Optional[str]] = mapped_column(Text)
    applied_on: Mapped[Optional[date]]
    responded_on: Mapped[Optional[date]]
    last_update: Mapped[date] = mapped_column(default=date.today)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))


class CVProfile(Base):
    __tablename__ = "cv_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, default="")
