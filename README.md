# Job Application Tracker

Track applications on a status board, paste job descriptions to extract required skills, score each
posting against your CV, and see response rate, time-to-reply and skills gaps.

## Run locally
```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000 (API docs at /docs).

## Run with Docker
```
docker build -t job-tracker .
docker run -p 8000:8000 -v tracker-data:/srv job-tracker
```

## Test
```
pytest -q
```

## How the match score works
60% skill coverage (skills in the posting that also appear in your CV) + 40% TF-IDF cosine similarity.
Edit the `SKILLS` list in `app/nlp.py` to add skills for your field.
