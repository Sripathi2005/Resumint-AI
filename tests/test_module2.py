"""
Test suite for Module 2: Job Matching and Recommender.
Uses plain Python asserts without heavy frameworks.
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.job_matcher import (
    build_tfidf_index,
    hybrid_score,
    load_jobs,
    rank_jobs,
    rank_roles,
    skill_overlap,
    text_similarity,
    validate_jobs_skills,
)
from modules.recommender import (
    get_skill_gap,
    learning_checklist,
)


def test_jobs_skills_exist_in_skills_json():
    """Verify that every single skill referenced in jobs.csv exists in skills.json."""
    # validate_jobs_skills raises ValueError if any skill is missing
    jobs_df = load_jobs()
    validate_jobs_skills(jobs_df)
    print("[PASS] test_jobs_skills_exist_in_skills_json")


def test_skill_overlap_handmade_example():
    """Verify skill_overlap correctly computes coverage, matched, and missing lists."""
    resume_skills = ["Python", "Docker", "SQL", "Git"]
    required_skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
    preferred_skills = ["SQL", "Redis"]

    overlap = skill_overlap(resume_skills, required_skills, preferred_skills)

    assert overlap["coverage"] == 0.5, f"Expected coverage 0.5, got {overlap['coverage']}"
    assert overlap["matched"] == ["Docker", "Python"], f"Unexpected matched: {overlap['matched']}"
    assert overlap["missing"] == ["FastAPI", "PostgreSQL"], f"Unexpected missing: {overlap['missing']}"
    assert overlap["preferred_matched"] == ["SQL"], f"Unexpected preferred_matched: {overlap['preferred_matched']}"

    # Edge case: empty required skills should return coverage 1.0
    empty_overlap = skill_overlap(resume_skills, [])
    assert empty_overlap["coverage"] == 1.0
    assert empty_overlap["matched"] == []
    assert empty_overlap["missing"] == []
    print("[PASS] test_skill_overlap_handmade_example")


def test_hybrid_score_boundaries_and_weights():
    """Verify hybrid_score stays strictly within [0, 100] and properly respects custom weights."""
    # Boundary tests
    assert hybrid_score(0.0, 0.0) == 0.0
    assert hybrid_score(1.0, 1.0) == 100.0
    assert 0.0 <= hybrid_score(0.5, 0.5) <= 100.0

    # Weight test: 100% skill weight
    score_skill_only = hybrid_score(text_sim=0.2, skill_cov=1.0, w_skill=1.0, w_text=0.0)
    assert score_skill_only == 100.0, f"Expected 100.0, got {score_skill_only}"

    # Weight test: 100% text weight
    score_text_only = hybrid_score(text_sim=0.2, skill_cov=1.0, w_skill=0.0, w_text=1.0)
    assert score_text_only == 20.0, f"Expected 20.0, got {score_text_only}"

    # Default weights: 0.6 * 1.0 + 0.4 * 0.5 = 0.6 + 0.2 = 0.8 -> 80.0
    default_score = hybrid_score(text_sim=0.5, skill_cov=1.0, w_skill=0.6, w_text=0.4)
    assert abs(default_score - 80.0) < 1e-4, f"Expected 80.0, got {default_score}"

    # Clamping test with out of bound floats
    clamped_high = hybrid_score(1.5, 1.2)
    assert clamped_high == 100.0, f"Expected clamped 100.0, got {clamped_high}"
    print("[PASS] test_hybrid_score_boundaries_and_weights")


def test_java_resume_ranks_java_developer_above_data_scientist():
    """Verify a resume with pure Java/Spring skills ranks Java Developer above Data Scientist."""
    jobs_df = load_jobs()
    vectorizer, matrix = build_tfidf_index(jobs_df)

    java_resume_text = (
        "Experienced software developer working with Java, Spring Boot, Spring Framework, "
        "and MySQL. Developed high throughput REST API services, configured Maven build plugins, "
        "and deployed containerized microservices."
    )
    java_skills = ["Java", "Spring Boot", "MySQL", "REST API", "Maven", "Docker"]

    ranked_roles = rank_roles(
        java_resume_text,
        java_skills,
        jobs_df,
        vectorizer,
        matrix,
        top_n=len(jobs_df["title"].unique()),
    )

    role_titles = [r["title"] for r in ranked_roles]
    assert "Java Developer" in role_titles
    assert "Data Scientist" in role_titles

    java_rank = role_titles.index("Java Developer")
    ds_rank = role_titles.index("Data Scientist")

    assert java_rank < ds_rank, f"Expected Java Developer (rank {java_rank}) to rank above Data Scientist (rank {ds_rank})"

    # Verify Java Developer has significantly higher final score than Data Scientist
    java_item = next(r for r in ranked_roles if r["title"] == "Java Developer")
    ds_item = next(r for r in ranked_roles if r["title"] == "Data Scientist")
    assert java_item["final_score"] > ds_item["final_score"] + 20.0, (
        f"Expected Java score ({java_item['final_score']}) >> DS score ({ds_item['final_score']})"
    )
    print("[PASS] test_java_resume_ranks_java_developer_above_data_scientist")


def test_zero_skills_resume_does_not_crash():
    """Verify a resume with zero known skills runs gracefully with low match scores."""
    jobs_df = load_jobs()
    vectorizer, matrix = build_tfidf_index(jobs_df)

    empty_resume_text = "I am a worker seeking employment in general administrative duties."
    empty_skills: list = []

    ranked = rank_roles(empty_resume_text, empty_skills, jobs_df, vectorizer, matrix, top_n=5)

    assert len(ranked) == 5, f"Expected 5 roles returned, got {len(ranked)}"
    for r in ranked:
        assert r["skill_score"] == 0.0, f"Expected 0.0 skill score, got {r['skill_score']}"
        assert r["final_score"] < 40.0, f"Expected low final score for empty skills, got {r['final_score']}"
        assert r["matched"] == []
        assert len(r["missing"]) > 0
    print("[PASS] test_zero_skills_resume_does_not_crash")


def test_recommender_gap_and_checklist():
    """Verify get_skill_gap sorts by demand and learning_checklist attaches categories."""
    jobs_df = load_jobs()
    sample_job = jobs_df.iloc[0]  # Python Developer with Python, SQL, Git

    # If candidate only has Python, missing are SQL and Git
    gap = get_skill_gap(resume_skills=["Python"], job_row=sample_job, jobs_df=jobs_df)
    assert set(gap) == set(sample_job["required_skills"]) - {"Python"}

    checklist = learning_checklist(gap)
    assert len(checklist) == len(gap)
    for item in checklist:
        assert "skill" in item
        assert "category" in item
        assert item["category"] in ["languages", "tools", "databases", "web", "cloud", "AI/ML", "frameworks", "embedded", "General"]
    print("[PASS] test_recommender_gap_and_checklist")


def test_ranking_and_gap_analysis_consistency():
    """Verify that ranking and detailed gap analysis use the exact same job_id and agree on missing skills."""
    from modules.resume_parser import clean_text, extract_text
    from modules.skill_extractor import extract_skills, load_skills

    resume_path = PROJECT_ROOT / "sample_resumes" / "java_backend.pdf"
    raw_text = extract_text(resume_path)
    cleaned = clean_text(raw_text)
    skill_lookup = load_skills()
    skills = extract_skills(cleaned, skill_lookup=skill_lookup, raw_text=raw_text)

    jobs_df = load_jobs()
    vectorizer, matrix = build_tfidf_index(jobs_df)

    ranked_roles = rank_roles(
        cleaned,
        skills,
        jobs_df,
        vectorizer,
        matrix,
        top_n=len(jobs_df["title"].unique()),
    )
    java_role = next(r for r in ranked_roles if r["title"] == "Java Developer")

    # Fetch the exact posting that was ranked for Java Developer
    winning_job_id = java_role["job_id"]
    winning_job_row = jobs_df[jobs_df["job_id"] == winning_job_id].iloc[0]

    # Perform gap analysis on that exact posting
    gap_missing = get_skill_gap(skills, winning_job_row, jobs_df=jobs_df)

    assert set(java_role["missing"]) == set(gap_missing), (
        f"Inconsistency bug: Ranked missing skills {java_role['missing']} != gap analysis missing skills {gap_missing} for {winning_job_id}"
    )
    print("[PASS] test_ranking_and_gap_analysis_consistency")


def test_skill_implications():
    """Verify skill implications: TypeScript satisfies JavaScript, PostgreSQL satisfies SQL, etc."""
    resume_skills = ["TypeScript", "PostgreSQL", "Spring Boot", "FastAPI"]
    required_skills = ["JavaScript", "SQL", "Java", "Python"]

    overlap = skill_overlap(resume_skills, required_skills)
    assert overlap["coverage"] == 1.0, f"Expected coverage 1.0, got {overlap['coverage']}"
    assert set(overlap["matched"]) == {"JavaScript", "SQL", "Java", "Python"}, f"Unexpected matched: {overlap['matched']}"
    assert overlap["missing"] == [], f"Expected empty missing, got {overlap['missing']}"
    print("[PASS] test_skill_implications")


def test_preferred_skills_tie_breaker():
    """Verify preferred skills break ties when final scores are within 1.0 point."""
    test_jobs = pd.DataFrame([
        {
            "job_id": "JOB_TIE_A",
            "title": "Backend Dev A",
            "category": "Software",
            "experience_level": "Entry-level",
            "description": "Python web services developer working on backend APIs and microservices architectures.",
            "required_skills": ["Python", "Docker"],
            "preferred_skills": ["Redis"],
        },
        {
            "job_id": "JOB_TIE_B",
            "title": "Backend Dev B",
            "category": "Software",
            "experience_level": "Entry-level",
            "description": "Python web services developer working on backend APIs and microservices systems.",
            "required_skills": ["Python", "Docker"],
            "preferred_skills": ["PostgreSQL", "Redis", "AWS"],
        }
    ])
    vectorizer, matrix = build_tfidf_index(test_jobs)
    resume_text = "Python backend developer with Docker, PostgreSQL, Redis, and AWS experience."
    resume_skills = ["Python", "Docker", "PostgreSQL", "Redis", "AWS"]

    ranked = rank_jobs(resume_text, resume_skills, test_jobs, vectorizer, matrix, top_n=2)
    # Both have 100% required skill match. JOB_TIE_B matches 3 preferred skills, JOB_TIE_A matches 1.
    assert ranked[0]["job_id"] == "JOB_TIE_B", f"Expected JOB_TIE_B to win tie-breaker, got {ranked[0]['job_id']}"
    print("[PASS] test_preferred_skills_tie_breaker")


def run_all_module2_tests():
    print("=" * 60)
    print("Running Module 2 Test Suite...")
    print("=" * 60)

    test_jobs_skills_exist_in_skills_json()
    test_skill_overlap_handmade_example()
    test_skill_implications()
    test_hybrid_score_boundaries_and_weights()
    test_preferred_skills_tie_breaker()
    test_java_resume_ranks_java_developer_above_data_scientist()
    test_zero_skills_resume_does_not_crash()
    test_recommender_gap_and_checklist()
    test_ranking_and_gap_analysis_consistency()

    print("=" * 60)
    print("ALL MODULE 2 TESTS PASSED SUCCESSFULLY! (9/9)")
    print("=" * 60)


if __name__ == "__main__":
    run_all_module2_tests()
