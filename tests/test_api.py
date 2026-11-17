import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from datetime import date, timedelta  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app import nlp  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Application  # noqa: E402

client = TestClient(app)

POSTING = "We need a Python and SQL developer with Docker, Git and 5G telecom knowledge. Agile team."
CV = "MSc in AI. Built projects in Python, SQL and Docker. Used Git daily and worked in an Agile team."


def test_extract_skills():
    skills = nlp.extract_skills("Experience with C++, Node.js and CI/CD; no gopher skills")
    assert {"c++", "node.js", "ci/cd"} <= set(skills)
    assert "go" not in skills


def test_match_score_range():
    score = nlp.match_score(CV, POSTING)
    assert 0 < score <= 100
    assert nlp.match_score("", POSTING) is None


def test_create_and_validate():
    bad = client.post("/api/applications", json={"company": " ", "role": "Dev"})
    assert bad.status_code == 422
    bad_status = client.post("/api/applications", json={"company": "A", "role": "B", "status": "Nope"})
    assert bad_status.status_code == 422
    ok = client.post("/api/applications", json={"company": "Ericsson", "role": "Intern", "posting_text": POSTING})
    assert ok.status_code == 201
    assert "python" in ok.json()["skills"]


def test_cv_rescoring_and_skills_gap():
    client.put("/api/cv", json={"text": CV})
    apps = client.get("/api/applications").json()
    assert all(a["match_score"] is not None for a in apps if a["skills"])
    gap = {g["skill"]: g["on_cv"] for g in client.get("/api/skills-gap").json()}
    assert gap["python"] is True
    assert gap["5g"] is False


def test_status_flow_and_stats():
    created = client.post("/api/applications", json={"company": "GagaMuller", "role": "PM", "status": "Applied"}).json()
    assert created["applied_on"] == date.today().isoformat()
    moved = client.patch(f"/api/applications/{created['id']}/status", json={"status": "Interview"}).json()
    assert moved["responded_on"] == date.today().isoformat()
    stats = client.get("/api/stats").json()
    assert stats["submitted"] >= 1 and stats["response_rate"] > 0
    assert len(stats["weekly"]) == 8


def test_follow_ups_and_delete():
    created = client.post("/api/applications", json={"company": "Old Co", "role": "Dev", "status": "Applied"}).json()
    with SessionLocal() as db:
        db.get(Application, created["id"]).last_update = date.today() - timedelta(days=10)
        db.commit()
    due = [a["id"] for a in client.get("/api/follow-ups").json()]
    assert created["id"] in due
    assert client.delete(f"/api/applications/{created['id']}").status_code == 204
    assert client.delete(f"/api/applications/{created['id']}").status_code == 404
