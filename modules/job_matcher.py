"""
Job Matcher Module.

Provides functions to:
- Load and parse job postings and validate required skills against skills.json.
- Build and query TF-IDF index for job descriptions and required skills.
- Compute text cosine similarity and structured skill overlap.
- Calculate hybrid match score (weighted combination of text similarity and skill coverage).
- Rank individual job postings and aggregated job roles.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Custom token pattern that preserves symbols critical for tech skills (c++, c#, node.js, .net)
TOKEN_PATTERN = r"(?u)c\+\+|c\#|node\.js|\.net|\b[a-zA-Z0-9_]+\b"


def validate_jobs_skills(
    jobs: Union[pd.DataFrame, str, Path],
    skills_path: Optional[Union[str, Path]] = None,
) -> None:
    """
    Validate that every required and preferred skill in the jobs dataset
    matches an exact canonical skill name in skills.json.

    Raises:
        ValueError: If any unrecognized skill is found.
    """
    if skills_path is None:
        skills_path = Path(__file__).resolve().parent.parent / "data" / "skills.json"
    else:
        skills_path = Path(skills_path)

    with open(skills_path, "r", encoding="utf-8") as f:
        skills_data = json.load(f)
    valid_skill_names = {s["name"] for s in skills_data.get("skills", [])}

    if isinstance(jobs, (str, Path)):
        df = pd.read_csv(jobs)
    else:
        df = jobs

    invalid_skills = set()
    for _, row in df.iterrows():
        # Check required_skills
        req = row.get("required_skills", "")
        if isinstance(req, str) and req.strip():
            for s in req.split("|"):
                s_clean = s.strip()
                if s_clean and s_clean not in valid_skill_names:
                    invalid_skills.add(s_clean)
        elif isinstance(req, list):
            for s in req:
                if s not in valid_skill_names:
                    invalid_skills.add(s)

        # Check preferred_skills
        pref = row.get("preferred_skills", "")
        if isinstance(pref, str) and pref.strip():
            for s in pref.split("|"):
                s_clean = s.strip()
                if s_clean and s_clean not in valid_skill_names:
                    invalid_skills.add(s_clean)
        elif isinstance(pref, list):
            for s in pref:
                if s not in valid_skill_names:
                    invalid_skills.add(s)

    if invalid_skills:
        raise ValueError(
            f"Validation Failed: The following skills in jobs dataset do not exist in skills.json: {sorted(list(invalid_skills))}"
        )


def load_jobs(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """
    Load job postings from CSV and parse pipe-separated skill fields into Python lists.

    Args:
        path: Path to jobs.csv. If None, defaults to data/jobs.csv.

    Returns:
        DataFrame with required_skills and preferred_skills as lists of strings.
    """
    if path is None:
        path = Path(__file__).resolve().parent.parent / "data" / "jobs.csv"
    else:
        path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Jobs file not found at: {path}")

    df = pd.read_csv(path)

    # Validate skills against skills.json
    validate_jobs_skills(df)

    def _parse_skills(val: Any) -> List[str]:
        if isinstance(val, list):
            return val
        if not isinstance(val, str) or not val.strip():
            return []
        return [s.strip() for s in val.split("|") if s.strip()]

    df["required_skills"] = df["required_skills"].apply(_parse_skills)
    df["preferred_skills"] = df["preferred_skills"].apply(_parse_skills)

    return df


def build_tfidf_index(jobs_df: pd.DataFrame) -> Tuple[TfidfVectorizer, Any]:
    """
    Fit a TF-IDF vectorizer and build document matrix on job descriptions
    and required skills text.

    Uses:
    - ngram_range=(1, 2)
    - stop_words='english'
    - sublinear_tf=True
    - token_pattern that keeps c++, c#, node.js, .net

    Args:
        jobs_df: DataFrame containing 'description' and 'required_skills' columns.

    Returns:
        Tuple of (fitted TfidfVectorizer, sparse job document matrix).
    """
    corpus = []
    for _, row in jobs_df.iterrows():
        desc = str(row.get("description", ""))
        req_skills = " ".join(row.get("required_skills", []))
        combined = f"{desc} {req_skills}".strip().lower()
        corpus.append(combined)

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
        token_pattern=TOKEN_PATTERN,
    )
    job_matrix = vectorizer.fit_transform(corpus)
    return vectorizer, job_matrix


def text_similarity(
    resume_clean_text: str,
    vectorizer: TfidfVectorizer,
    job_matrix: Any,
) -> np.ndarray:
    """
    Compute cosine similarity between cleaned resume text and all indexed job postings.

    Args:
        resume_clean_text: Cleaned resume text string.
        vectorizer: Fitted TfidfVectorizer instance.
        job_matrix: Document term matrix of job postings.

    Returns:
        1D numpy array of cosine similarities in range [0.0, 1.0].
    """
    if not resume_clean_text.strip():
        return np.zeros(job_matrix.shape[0])

    resume_vec = vectorizer.transform([resume_clean_text.lower()])
    sims = cosine_similarity(resume_vec, job_matrix)[0]
    return np.clip(sims, 0.0, 1.0)


def load_skill_implications(path: Optional[Union[str, Path]] = None) -> Dict[str, List[str]]:
    """
    Load skill implications map (e.g. TypeScript implies JavaScript, PostgreSQL implies SQL).
    """
    if path is None:
        path = Path(__file__).resolve().parent.parent / "data" / "skill_implications.json"
    else:
        path = Path(path)

    if not path.is_file():
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("implications", {})


def skill_overlap(
    resume_skills: List[str],
    required: List[str],
    preferred: Optional[List[str]] = None,
    implications: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Calculate structured skill overlap metrics, taking into account skill implications
    (e.g., candidate knowing TypeScript satisfies JavaScript; PostgreSQL satisfies SQL).

    Args:
        resume_skills: List of skills detected in candidate resume.
        required: List of required skills for the job.
        preferred: Optional list of preferred skills for the job.
        implications: Optional map of skill -> implied skills. If None, loaded from data/skill_implications.json.

    Returns:
        Dictionary containing:
        - 'coverage': float [0.0, 1.0] (matched required / total required)
        - 'matched': list of matched required skills
        - 'missing': list of missing required skills
        - 'preferred_matched': list of matched preferred skills
    """
    if implications is None:
        implications = load_skill_implications()

    # Expand candidate skills with implied skills
    effective_skills = set(resume_skills)
    for s in resume_skills:
        for implied_skill in implications.get(s, []):
            effective_skills.add(implied_skill)

    req_set = set(required)
    pref_set = set(preferred or [])

    matched = sorted([s for s in req_set if s in effective_skills])
    missing = sorted([s for s in req_set if s not in effective_skills])
    pref_matched = sorted([s for s in pref_set if s in effective_skills])

    coverage = len(matched) / len(req_set) if req_set else 1.0

    return {
        "coverage": float(coverage),
        "matched": matched,
        "missing": missing,
        "preferred_matched": pref_matched,
    }


def hybrid_score(
    text_sim: float,
    skill_cov: float,
    w_skill: float = 0.6,
    w_text: float = 0.4,
) -> float:
    """
    Calculate composite hybrid match score scaled from 0 to 100.

    Args:
        text_sim: Text cosine similarity in [0.0, 1.0].
        skill_cov: Skill coverage in [0.0, 1.0].
        w_skill: Weight assigned to skill coverage (default: 0.6).
        w_text: Weight assigned to text similarity (default: 0.4).

    Returns:
        Score between 0.0 and 100.0.
    """
    total_w = w_skill + w_text
    if total_w <= 0:
        return 0.0

    raw = (w_skill * skill_cov + w_text * text_sim) / total_w
    return float(np.clip(raw * 100.0, 0.0, 100.0))


def _assign_tier(skill_score: float) -> str:
    """Assign human-readable qualification tier based on skill coverage percentage."""
    if skill_score >= 80.0:
        return "Strong Match"
    elif skill_score >= 50.0:
        return "Moderate Match"
    else:
        return "Growth Potential"


def rank_jobs(
    resume_clean_text: str,
    resume_skills: List[str],
    jobs_df: pd.DataFrame,
    vectorizer: TfidfVectorizer,
    matrix: Any,
    top_n: int = 5,
    w_skill: float = 0.6,
    w_text: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Score and rank individual job postings for a candidate resume.
    Uses number of preferred skills matched as a tie-breaker when final scores
    differ by less than 1.0 point.

    Args:
        resume_clean_text: Cleaned resume text string.
        resume_skills: List of skills detected on resume.
        jobs_df: Jobs DataFrame.
        vectorizer: Fitted TfidfVectorizer.
        matrix: Job TF-IDF matrix.
        top_n: Number of top job postings to return.
        w_skill: Weight for skill coverage.
        w_text: Weight for text similarity.

    Returns:
        List of dictionaries with keys: job_id, title, text_score,
        skill_score, final_score, matched, missing, preferred_matched, tier.
    """
    import functools

    sims = text_similarity(resume_clean_text, vectorizer, matrix)
    implications = load_skill_implications()
    results = []

    for i, (_, row) in enumerate(jobs_df.iterrows()):
        req = row["required_skills"]
        pref = row.get("preferred_skills", [])
        overlap = skill_overlap(resume_skills, req, pref, implications=implications)

        t_sim = float(sims[i])
        s_cov = overlap["coverage"]
        f_score = hybrid_score(t_sim, s_cov, w_skill=w_skill, w_text=w_text)
        skill_score_pct = round(s_cov * 100.0, 2)

        results.append({
            "job_id": row["job_id"],
            "title": row["title"],
            "category": str(row.get("category", "")),
            "experience_level": str(row.get("experience_level", "")),
            "description": str(row.get("description", "")),
            "required_skills": req,
            "preferred_skills": pref,
            "text_score": round(t_sim * 100.0, 2),
            "skill_score": skill_score_pct,
            "final_score": round(f_score, 2),
            "matched": overlap["matched"],
            "missing": overlap["missing"],
            "preferred_matched": overlap["preferred_matched"],
            "pref_matched_count": len(overlap["preferred_matched"]),
            "tier": _assign_tier(skill_score_pct),
        })

    def _compare_jobs(a, b):
        # Primary: Final score
        diff = a["final_score"] - b["final_score"]
        # If final scores differ by less than 1.0 point, break tie using preferred skills matched
        if abs(diff) < 1.0:
            pref_diff = a["pref_matched_count"] - b["pref_matched_count"]
            if pref_diff != 0:
                return 1 if pref_diff > 0 else -1
            # If preferred matched count is also equal, use exact diff
            if diff != 0:
                return 1 if diff > 0 else -1
            return 0
        return 1 if diff > 0 else -1

    results.sort(key=functools.cmp_to_key(_compare_jobs), reverse=True)
    return results[:top_n]


def rank_roles(
    resume_clean_text: str,
    resume_skills: List[str],
    jobs_df: pd.DataFrame,
    vectorizer: TfidfVectorizer,
    matrix: Any,
    top_n: int = 5,
    w_skill: float = 0.6,
    w_text: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Score and rank aggregated job roles (best-scoring posting per role title).
    Ensures candidate sees distinct roles rather than multiple postings of the same title.

    Args:
        resume_clean_text: Cleaned resume text.
        resume_skills: Candidate's detected skills.
        jobs_df: Jobs DataFrame.
        vectorizer: Fitted vectorizer.
        matrix: Job document matrix.
        top_n: Maximum number of distinct roles to return.
        w_skill: Skill weight.
        w_text: Text weight.

    Returns:
        List of role recommendation dicts sorted by final_score descending.
    """
    all_ranked = rank_jobs(
        resume_clean_text,
        resume_skills,
        jobs_df,
        vectorizer,
        matrix,
        top_n=len(jobs_df),
        w_skill=w_skill,
        w_text=w_text,
    )

    seen_titles = set()
    unique_roles = []

    for item in all_ranked:
        title = item["title"]
        if title not in seen_titles:
            seen_titles.add(title)
            unique_roles.append(item)
            if len(unique_roles) >= top_n:
                break

    return unique_roles
