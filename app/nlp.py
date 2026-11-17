"""Skill extraction and CV-to-posting match score (no external APIs needed)."""
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "sql", "nosql",
    "react", "angular", "vue", "node.js", "fastapi", "flask", "django", "spring", "docker",
    "kubernetes", "aws", "azure", "gcp", "linux", "git", "ci/cd", "jenkins", "terraform",
    "rest", "graphql", "microservices", "postgresql", "mysql", "mongodb", "redis", "kafka",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "machine learning",
    "deep learning", "nlp", "data analysis", "data engineering", "etl", "power bi", "tableau",
    "excel", "agile", "scrum", "jira", "project management", "stakeholder management",
    "testing", "unit testing", "automation", "bash", "networking", "5g", "telecom",
    "communication", "problem solving", "teamwork", "documentation",
]


def extract_skills(text: str) -> list[str]:
    found = []
    for skill in SKILLS:
        pattern = r"(?<![A-Za-z0-9])" + re.escape(skill) + r"(?![A-Za-z0-9])"
        if re.search(pattern, text or "", flags=re.IGNORECASE):
            found.append(skill)
    return found


def match_score(cv_text: str, posting_text: str) -> float | None:
    """0-100: 60% skill coverage of the posting, 40% TF-IDF cosine similarity."""
    if not cv_text.strip() or not posting_text.strip():
        return None
    job_skills = set(extract_skills(posting_text))
    cv_skills = set(extract_skills(cv_text))
    try:
        vec = TfidfVectorizer(stop_words="english").fit_transform([cv_text, posting_text])
        cosine = float(cosine_similarity(vec[0], vec[1])[0][0])
    except ValueError:  # empty vocabulary
        cosine = 0.0
    coverage = len(job_skills & cv_skills) / len(job_skills) if job_skills else cosine
    return round(100 * (0.6 * coverage + 0.4 * cosine), 1)
