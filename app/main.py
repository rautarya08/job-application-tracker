from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import nlp
from .database import Base, engine, get_db
from .models import Application, CVProfile
from .schemas import RESPONSE_STATUSES, STATUSES, ApplicationIn, ApplicationOut, CVIn

Base.metadata.create_all(engine)

app = FastAPI(title="Job Application Tracker")
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_cv_text(db: Session) -> str:
    cv = db.get(CVProfile, 1)
    return cv.text if cv else ""


def to_out(a: Application) -> ApplicationOut:
    return ApplicationOut(
        id=a.id, company=a.company, role=a.role, location=a.location, url=a.url,
        status=a.status, skills=[s for s in a.skills.split(",") if s],
        match_score=a.match_score, notes=a.notes, applied_on=a.applied_on,
        responded_on=a.responded_on, last_update=a.last_update,
    )


def apply_status_rules(a: Application, new_status: str) -> None:
    if new_status != a.status or a.last_update is None:
        a.last_update = date.today()
    a.status = new_status
    if new_status != "Saved" and a.applied_on is None:
        a.applied_on = date.today()
    if new_status in RESPONSE_STATUSES and a.responded_on is None:
        a.responded_on = date.today()


def score_posting(a: Application, cv_text: str) -> None:
    a.skills = ",".join(nlp.extract_skills(a.posting_text))
    a.match_score = nlp.match_score(cv_text, a.posting_text)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    rows = db.scalars(select(Application).order_by(Application.last_update.desc(), Application.id.desc()))
    return [to_out(a) for a in rows]


@app.post("/api/applications", response_model=ApplicationOut, status_code=201)
def create_application(payload: ApplicationIn, db: Session = Depends(get_db)):
    a = Application(
        company=payload.company, role=payload.role, location=payload.location,
        url=payload.url, posting_text=payload.posting_text, notes=payload.notes,
        status="Saved", last_update=date.today(),
    )
    apply_status_rules(a, payload.status)
    score_posting(a, get_cv_text(db))
    db.add(a)
    db.commit()
    db.refresh(a)
    return to_out(a)


@app.put("/api/applications/{app_id}", response_model=ApplicationOut)
def update_application(app_id: int, payload: ApplicationIn, db: Session = Depends(get_db)):
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(404, "Application not found")
    text_changed = payload.posting_text != a.posting_text
    a.company, a.role, a.location = payload.company, payload.role, payload.location
    a.url, a.notes, a.posting_text = payload.url, payload.notes, payload.posting_text
    apply_status_rules(a, payload.status)
    if text_changed:
        score_posting(a, get_cv_text(db))
    db.commit()
    db.refresh(a)
    return to_out(a)


class StatusIn(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid(cls, v: str) -> str:
        if v not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        return v


@app.patch("/api/applications/{app_id}/status", response_model=ApplicationOut)
def move_application(app_id: int, payload: StatusIn, db: Session = Depends(get_db)):
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(404, "Application not found")
    apply_status_rules(a, payload.status)
    db.commit()
    db.refresh(a)
    return to_out(a)


@app.delete("/api/applications/{app_id}", status_code=204)
def delete_application(app_id: int, db: Session = Depends(get_db)):
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(404, "Application not found")
    db.delete(a)
    db.commit()


@app.get("/api/cv")
def read_cv(db: Session = Depends(get_db)):
    return {"text": get_cv_text(db)}


@app.put("/api/cv")
def save_cv(payload: CVIn, db: Session = Depends(get_db)):
    cv = db.get(CVProfile, 1) or CVProfile(id=1)
    cv.text = payload.text
    db.add(cv)
    for a in db.scalars(select(Application)):  # rescore everything against the new CV
        score_posting(a, payload.text)
    db.commit()
    return {"text": cv.text}


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    apps = list(db.scalars(select(Application)))
    by_status = {s: 0 for s in STATUSES}
    for a in apps:
        by_status[a.status] += 1
    submitted = [a for a in apps if a.status != "Saved"]
    responded = [a for a in apps if a.responded_on]
    waits = [(a.responded_on - a.applied_on).days for a in responded if a.applied_on]
    this_monday = date.today() - timedelta(days=date.today().weekday())
    weekly = []
    for i in range(7, -1, -1):
        start = this_monday - timedelta(weeks=i)
        end = start + timedelta(days=7)
        count = sum(1 for a in submitted if a.applied_on and start <= a.applied_on < end)
        weekly.append({"week_start": start.isoformat(), "count": count})
    return {
        "total": len(apps),
        "submitted": len(submitted),
        "by_status": by_status,
        "response_rate": round(100 * len(responded) / len(submitted), 1) if submitted else None,
        "avg_days_to_response": round(sum(waits) / len(waits), 1) if waits else None,
        "weekly": weekly,
    }


@app.get("/api/skills-gap")
def skills_gap(db: Session = Depends(get_db)):
    cv_skills = set(nlp.extract_skills(get_cv_text(db)))
    counts = Counter()
    for a in db.scalars(select(Application)):
        counts.update(s for s in a.skills.split(",") if s)
    return [
        {"skill": s, "postings": n, "on_cv": s in cv_skills}
        for s, n in counts.most_common(15)
    ]


@app.get("/api/follow-ups", response_model=list[ApplicationOut])
def follow_ups(days: int = 7, db: Session = Depends(get_db)):
    cutoff = date.today() - timedelta(days=days)
    rows = db.scalars(
        select(Application).where(Application.status == "Applied", Application.last_update <= cutoff)
    )
    return [to_out(a) for a in rows]
