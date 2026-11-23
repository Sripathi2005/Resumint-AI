"""
Pipeline Module.

Integrates Module 1 (parsing, cleaning, skill/education/section extraction)
and Module 2 (job indexing, hybrid role ranking, gap analysis, and learning checklist)
into a single unified entry point for CLI and Web interfaces.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from modules.job_matcher import (
    _assign_tier,
    build_tfidf_index,
    hybrid_score,
    load_jobs,
    load_skill_implications,
    rank_roles,
    skill_overlap,
    text_similarity,
)
from modules.recommender import (
    get_role_info,
    get_skill_gap,
    learning_checklist,
)
from modules.resume_parser import (
    clean_text,
    extract_text,
)
from modules.skill_extractor import (
    extract_education_keywords,
    extract_sections,
    extract_skills,
    extract_soft_skills,
    load_skills,
)


def categorize_skills(
    skills: List[str],
    skills_path: Optional[Union[str, Path]] = None,
) -> Dict[str, List[str]]:
    """Group detected skills by canonical domain category for clean visualization."""
    if skills_path is None:
        skills_path = Path(__file__).resolve().parent.parent / "data" / "skills.json"
    else:
        skills_path = Path(skills_path)

    cat_lookup = {}
    if skills_path.is_file():
        try:
            with open(skills_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("skills", []):
                cat_lookup[item["name"].lower()] = item.get("category", "Other")
        except Exception:
            pass

    category_labels = {
        "languages": "Programming Languages",
        "frameworks": "Frameworks & Libraries",
        "databases": "Databases & Storage",
        "cloud": "Cloud & DevOps",
        "tools": "Developer Tools",
        "web": "Web Technologies",
        "ai_ml": "AI & Data Science",
        "embedded": "Embedded & Systems",
    }

    grouped: Dict[str, List[str]] = {}
    for s in skills:
        raw_cat = cat_lookup.get(s.lower(), "other")
        display_cat = category_labels.get(raw_cat.lower(), raw_cat.title())
        grouped.setdefault(display_cat, []).append(s)

    return grouped


def _evaluate_qualifications(
    detected_education: List[str],
    soft_skills: List[str],
    role_meta: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare extracted education & soft skills against role expectations."""
    quals = (role_meta or {}).get("qualifications", {})
    expected_edu = quals.get("education", "Bachelor's degree in Computer Science or related technical field")
    edu_lower = " ".join(e.lower() for e in (detected_education or []))
    bachelor_tokens = ["b.tech", "btech", "b.e", "be", "b.sc", "bsc", "bca", "bachelor", "m.tech", "mtech", "m.sc", "msc", "mca", "master", "phd", "degree"]
    diploma_tokens = ["diploma", "associate", "bootcamp"]

    if any(tok in edu_lower for tok in bachelor_tokens):
        edu_status = "Aligned (Degree keyword detected)"
        edu_aligned = True
    elif any(tok in edu_lower for tok in diploma_tokens) or detected_education:
        edu_status = "Partially Aligned (Relevant academic credentials found)"
        edu_aligned = True
    else:
        edu_status = "Not explicitly detected in resume text"
        edu_aligned = False

    role_soft = (role_meta or {}).get("soft_skills", [])
    user_soft_lower = {s.lower() for s in (soft_skills or [])}
    soft_matched = [s for s in role_soft if s.lower() in user_soft_lower]
    soft_missing = [s for s in role_soft if s.lower() not in user_soft_lower]

    return {
        "expected_education": expected_edu,
        "detected_education": detected_education or [],
        "education_aligned": edu_aligned,
        "education_status": edu_status,
        "typical_experience": quals.get("typical_experience", "0–2 years for entry/junior"),
        "salary_benchmark": quals.get("salary_benchmark", ""),
        "expectations": quals.get("expectations", []),
        "helpful_certifications": quals.get("helpful_certifications", []),
        "soft_matched": soft_matched,
        "soft_missing": soft_missing,
    }


def _generate_improvement_suggestions(
    job_title: str,
    matched_skills: List[str],
    missing_skills: List[str],
    required_skills: List[str],
    experience_level: str = "",
    role_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate actionable, practical improvement suggestions to help a candidate
    become qualified and competitive for a specific target job posting.
    """
    total_req = len(required_skills)
    matched_count = len(matched_skills)
    missing_count = len(missing_skills)
    coverage_pct = round((matched_count / total_req * 100.0) if total_req > 0 else 0.0, 1)

    if missing_count == 0:
        summary = (
            f"Outstanding match! Your resume currently demonstrates all {matched_count} required "
            f"competencies for this {job_title} position (100% skill coverage)."
        )
        actions = [
            f"Highlight specific production achievements using {', '.join(matched_skills[:4])} prominently in your experience bullet points.",
            "Prepare detailed code walkthroughs and system architecture explanations for technical interviews.",
            "Demonstrate familiarity with team collaboration, code reviews, CI/CD, and automated testing.",
        ]
        proj = (
            f"Build and deploy an end-to-end production application combining {', '.join(matched_skills[:3])} "
            f"with automated test coverage, Docker containerization, and a live demo link."
        )
        interview_focus = (
            f"System design, database optimization, scalability patterns, and behavioral questions "
            f"relevant to {experience_level or 'this level'} {job_title} positions."
        )
    else:
        summary = (
            f"You currently satisfy {matched_count} of {total_req} required competencies ({coverage_pct}% coverage) "
            f"for this {job_title} position. Closing the gap on {missing_count} missing skill"
            f"{'' if missing_count == 1 else 's'} will significantly improve your qualification alignment."
        )

        actions = []
        priority_skills = missing_skills[:3]
        actions.append(
            f"Prioritize mastering {', '.join(priority_skills)}: These are core requirements for this specific posting. "
            f"Dedicate structured study time to learn their core concepts and practical workflows."
        )

        if matched_skills:
            actions.append(
                f"Leverage your existing strength in {', '.join(matched_skills[:2])} to accelerate learning "
                f"{priority_skills[0] if priority_skills else 'missing tools'} through hands-on project integration."
            )
        else:
            actions.append(
                f"Start with fundamentals: Begin by building small exercises using {priority_skills[0]} before "
                f"combining multiple frameworks."
            )

        exp_str = (experience_level or "Junior / Entry-level").lower()
        if "senior" in exp_str or "lead" in exp_str:
            actions.append(
                "Emphasize architectural decision-making, system scalability, and leadership experience on your resume."
            )
        elif "mid" in exp_str:
            actions.append(
                "Focus on building independent features, database schema design, and writing comprehensive unit/integration tests."
            )
        else:
            actions.append(
                "For entry/junior roles, employers value strong fundamentals, clean readable code, and enthusiasm to learn new tools quickly."
            )

        sample_missing = priority_skills[0] if priority_skills else "the missing technology"
        sample_matched = matched_skills[0] if matched_skills else "standard tools"
        proj = (
            f"Create a portfolio project that directly combines your known skills ({sample_matched}) "
            f"with your target missing competency ({sample_missing}). Deploy it online with a GitHub README "
            f"documenting the architecture, API endpoints, and design decisions."
        )

        interview_focus = (
            f"Review common technical interview questions for {', '.join(missing_skills[:3])}, "
            f"and be ready to explain how {job_title}s use them in day-to-day development."
        )

    return {
        "summary": summary,
        "coverage_pct": coverage_pct,
        "priority_actions": actions,
        "project_recommendation": proj,
        "interview_focus": interview_focus,
    }


def compare_resume_to_job(
    pdf_path: Union[str, Path],
    job_id: str,
    jobs_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Feature 2: Compare resume strictly against a single selected job posting.

    Does NOT rank or recommend other jobs.
    Evaluates exact required skills, description similarity, skill gap,
    learning recommendations, and improvement suggestions for the specified job_id.
    """
    path = Path(pdf_path)

    # 1. Module 1: Extraction
    raw_text = extract_text(path)
    cleaned_text = clean_text(raw_text)
    skill_lookup = load_skills()
    detected_skills = extract_skills(cleaned_text, skill_lookup=skill_lookup, raw_text=raw_text)
    skills_by_category = categorize_skills(detected_skills)
    education = extract_education_keywords(raw_text)
    sections = extract_sections(raw_text)
    soft_skills = extract_soft_skills(cleaned_text, raw_text=raw_text)

    # 2. Locate the exact selected job posting
    if jobs_df is None:
        jobs_df = load_jobs()

    clean_jid = str(job_id).strip().lower()
    matched_rows = jobs_df[jobs_df["job_id"].astype(str).str.strip().str.lower() == clean_jid]
    if matched_rows.empty:
        raise ValueError(f"Job posting with ID '{job_id}' was not found in the database.")

    job_row = matched_rows.iloc[0]
    canonical_job_id = str(job_row["job_id"])
    job_title = str(job_row["title"])
    category = str(job_row.get("category", ""))
    experience_level = str(job_row.get("experience_level", ""))
    company = str(job_row.get("company", "")) if "company" in job_row and pd.notna(job_row.get("company")) else ""
    description = str(job_row.get("description", ""))
    required_skills = list(job_row["required_skills"])
    preferred_skills = list(job_row.get("preferred_skills", [])) if job_row.get("preferred_skills") is not None else []

    # 3. Exact skill overlap for this job posting
    implications = load_skill_implications()
    overlap = skill_overlap(detected_skills, required_skills, preferred_skills, implications=implications)
    matched_skills = overlap["matched"]
    missing_skills = overlap["missing"]
    preferred_matched = overlap["preferred_matched"]
    coverage = overlap["coverage"]
    skill_match_pct = round(coverage * 100.0, 1)

    # 4. Context text similarity with this exact job's description
    vectorizer, matrix = build_tfidf_index(jobs_df)
    job_pos = jobs_df.index.get_loc(job_row.name)
    t_sim = float(text_similarity(cleaned_text, vectorizer, matrix[job_pos : job_pos + 1])[0])
    text_score_pct = round(t_sim * 100.0, 1)
    overall_match_pct = round(hybrid_score(t_sim, coverage, w_skill=0.7, w_text=0.3) * 100.0, 1)

    # 5. Learning recommendations for missing skills (2-3 verified resources per missing skill)
    role_meta = get_role_info(job_title)
    rec_checklist = learning_checklist(
        missing_skills,
        role_title=job_title,
        role_info=role_meta,
    )

    # 6. Improvement suggestions
    improvement_suggestions = _generate_improvement_suggestions(
        job_title=job_title,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        required_skills=required_skills,
        experience_level=experience_level,
        role_info=role_meta,
    )

    return {
        "comparison_type": "job_benchmark",
        "job_id": canonical_job_id,
        "title": job_title,
        "company": company,
        "category": category,
        "experience_level": experience_level,
        "description": description,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "detected_skills": detected_skills,
        "skills_by_category": skills_by_category,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "preferred_matched": preferred_matched,
        "match_pct": skill_match_pct,
        "overall_match_pct": overall_match_pct,
        "text_score_pct": text_score_pct,
        "tier": _assign_tier(skill_match_pct),
        "learning_recommendations": rec_checklist,
        "improvement_suggestions": improvement_suggestions,
        "education": education,
        "soft_skills": soft_skills,
        "sections": sections,
        "filename": path.name,
    }


def analyze_resume(
    pdf_path: Union[str, Path],
    role: Optional[str] = None,
    top_n: int = 5,
    w_skill: float = 0.6,
    w_text: float = 0.4,
    jobs_df: Optional[pd.DataFrame] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute full resume analysis pipeline:
    1. Parse PDF, clean text, extract detected skills, education keywords, and sections.
    2. Rank top roles using hybrid matching with preferred-skill tie-breaking and qualification tiers.
    3. Generate detailed skill gap analysis and prioritized learning checklist
       for the requested role (or the top-ranked role) using the exact same job_id.

    Args:
        pdf_path: Path to the resume PDF file.
        role: Optional target role name for gap analysis. If None or empty, defaults to top role.
        top_n: Number of top roles to return (default: 5).
        w_skill: Skill weight (default: 0.6).
        w_text: Text weight (default: 0.4).
        jobs_df: Optional preloaded jobs DataFrame for efficiency.

    Returns:
        Dictionary with keys:
        - 'filename': str
        - 'detected_skills': list[str]
        - 'skills_by_category': dict[str, list[str]]
        - 'education': list[str]
        - 'sections': dict[str, str]
        - 'top_roles': list[dict] (job_id, title, skill_score, text_score, final_score, matched, missing, tier)
        - 'target_role': dict (gap analysis for the chosen or top role with same job_id)
    """
    path = Path(pdf_path)

    # 1. Module 1: Extraction
    raw_text = extract_text(path)
    cleaned_text = clean_text(raw_text)
    skill_lookup = load_skills()
    detected_skills = extract_skills(cleaned_text, skill_lookup=skill_lookup, raw_text=raw_text)
    skills_by_category = categorize_skills(detected_skills)
    education = extract_education_keywords(raw_text)
    sections = extract_sections(raw_text)

    # 2. Module 2: Job Matching
    if jobs_df is None:
        jobs_df = load_jobs()

    vectorizer, matrix = build_tfidf_index(jobs_df)

    # Rank all unique roles in the dataset
    all_ranked_roles = rank_roles(
        cleaned_text,
        detected_skills,
        jobs_df,
        vectorizer,
        matrix,
        top_n=len(jobs_df["title"].unique()),
        w_skill=w_skill,
        w_text=w_text,
    )

    top_roles = all_ranked_roles[:top_n]

    # 3. Gap / Readiness Analysis for Chosen Job/Role (or Top Role in auto mode)
    from modules.recommender import generate_career_roadmap, get_role_info
    from modules.skill_extractor import extract_soft_skills

    chosen_role_info = None
    target_job_id = job_id.strip() if job_id and job_id.strip() else None
    target_role_name = role.strip() if role and role.strip() else None
    is_explicit_role = bool(target_role_name and target_role_name.lower() != "best fit across all roles")
    evaluation_scope = "auto_top_match"
    posting_count = 1
    soft_skills = extract_soft_skills(cleaned_text, raw_text=raw_text)

    if target_job_id:
        for pos, (_, jrow) in enumerate(jobs_df.iterrows()):
            if str(jrow.get("job_id", "")).strip().lower() == target_job_id.lower():
                if not target_role_name or str(jrow.get("title", "")).lower() == target_role_name.lower():
                    req = jrow["required_skills"]
                    pref = jrow.get("preferred_skills", [])
                    overlap = skill_overlap(detected_skills, req, pref, implications=load_skill_implications())
                    t_sim = float(text_similarity(cleaned_text, vectorizer, matrix[pos : pos + 1])[0])
                    s_cov = overlap["coverage"]
                    f_score = hybrid_score(t_sim, s_cov, w_skill=w_skill, w_text=w_text)
                    skill_score_pct = round(s_cov * 100.0, 2)
                    chosen_role_info = {
                        "job_id": jrow["job_id"],
                        "title": jrow["title"],
                        "category": str(jrow.get("category", "")),
                        "experience_level": str(jrow.get("experience_level", "")),
                        "description": str(jrow.get("description", "")),
                        "required_skills": req,
                        "preferred_skills": pref,
                        "text_score": round(t_sim * 100.0, 2),
                        "skill_score": skill_score_pct,
                        "final_score": round(f_score, 2),
                        "matched": overlap["matched"],
                        "missing": overlap["missing"],
                        "preferred_matched": overlap["preferred_matched"],
                        "tier": _assign_tier(skill_score_pct),
                    }
                    evaluation_scope = "specific_job"
                    break

    if chosen_role_info is None and is_explicit_role:
        # Role-wide Career-Readiness Evaluation: aggregate expected skills & context across
        # Kaggle job postings + job_roles_info.json rather than a single arbitrary posting.
        role_df = jobs_df[jobs_df["title"].str.lower() == target_role_name.lower()]
        canonical_role_title = str(role_df.iloc[0]["title"]) if not role_df.empty else target_role_name
        role_meta_lookup = get_role_info(canonical_role_title)
        ranked_match = next(
            (r for r in all_ranked_roles if r["title"].lower() == target_role_name.lower()),
            None,
        )

        if not role_df.empty:
            posting_count = len(role_df)
            core_skills = (role_meta_lookup or {}).get("technical_skills", {}).get("core_skills", [])
            if not core_skills:
                freq: Dict[str, int] = {}
                for sk_list in role_df["required_skills"]:
                    for sk in sk_list:
                        freq[sk] = freq.get(sk, 0) + 1
                core_skills = [s for s, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:10]]

            pref_union: List[str] = []
            seen_pref = set(core_skills)
            for p_list in role_df["preferred_skills"]:
                for sk in (p_list or []):
                    if sk not in seen_pref:
                        seen_pref.add(sk)
                        pref_union.append(sk)

            overlap = skill_overlap(
                detected_skills,
                core_skills,
                pref_union,
                implications=load_skill_implications(),
            )
            role_positions = [pos for pos, idx in enumerate(jobs_df.index) if idx in role_df.index]
            sims = text_similarity(cleaned_text, vectorizer, matrix[role_positions]) if role_positions else [0.0]
            t_sim = float(max(sims)) if len(sims) else 0.0
            s_cov = overlap["coverage"]
            f_score = hybrid_score(t_sim, s_cov, w_skill=w_skill, w_text=w_text)
            skill_score_pct = round(s_cov * 100.0, 2)
            rep_row = role_df.iloc[0]

            chosen_role_info = {
                "job_id": ranked_match["job_id"] if ranked_match else str(rep_row["job_id"]),
                "title": canonical_role_title,
                "category": str(rep_row.get("category", "")),
                "experience_level": f"Aggregated across {posting_count} Kaggle postings",
                "description": (role_meta_lookup or {}).get("overview") or str(rep_row.get("description", "")),
                "required_skills": list(core_skills),
                "preferred_skills": pref_union[:10],
                "text_score": round(t_sim * 100.0, 2),
                "skill_score": skill_score_pct,
                "final_score": round(f_score, 2),
                "matched": overlap["matched"],
                "missing": overlap["missing"],
                "preferred_matched": overlap["preferred_matched"],
                "tier": _assign_tier(skill_score_pct),
            }
            evaluation_scope = "role_benchmark"
        elif ranked_match is not None:
            chosen_role_info = ranked_match
            evaluation_scope = "role_benchmark"

    # Fallback to top role only in general recommendation mode (or unknown role name)
    if chosen_role_info is None and top_roles:
        chosen_role_info = top_roles[0]
        evaluation_scope = "auto_top_match"

    target_gap_data = None
    if chosen_role_info is not None:
        role_title_final = chosen_role_info["title"]
        role_meta = get_role_info(role_title_final)
        req_for_gap = chosen_role_info.get("required_skills")
        if not req_for_gap:
            job_row = jobs_df[jobs_df["job_id"] == chosen_role_info["job_id"]].iloc[0]
            req_for_gap = job_row["required_skills"]
            chosen_role_info["preferred_skills"] = job_row.get("preferred_skills", [])
            chosen_role_info["category"] = str(job_row.get("category", ""))
            chosen_role_info["experience_level"] = str(job_row.get("experience_level", ""))
            chosen_role_info["description"] = str(job_row.get("description", ""))

        missing_skills = get_skill_gap(
            detected_skills,
            {"required_skills": req_for_gap},
            jobs_df=jobs_df,
        )
        checklist = learning_checklist(
            missing_skills,
            role_title=role_title_final,
            role_info=role_meta,
        )
        roadmap = generate_career_roadmap(
            role_title_final,
            detected_skills=detected_skills,
            detected_soft_skills=soft_skills,
        )
        qual_check = _evaluate_qualifications(education, soft_skills, role_meta)

        target_gap_data = {
            "title": role_title_final,
            "slug": role_meta.get("slug", "") if role_meta else "",
            "job_id": chosen_role_info["job_id"],
            "evaluation_scope": evaluation_scope,
            "posting_count": posting_count,
            "category": chosen_role_info.get("category", ""),
            "experience_level": chosen_role_info.get("experience_level", ""),
            "description": chosen_role_info.get("description", ""),
            "skill_score": chosen_role_info["skill_score"],
            "text_score": chosen_role_info["text_score"],
            "final_score": chosen_role_info["final_score"],
            "tier": chosen_role_info["tier"],
            "required_skills": list(req_for_gap),
            "preferred_skills": list(chosen_role_info.get("preferred_skills", [])),
            "matched": chosen_role_info["matched"],
            "missing": missing_skills,
            "learning_checklist": checklist,
            "soft_skills": soft_skills,
            "career_roadmap": roadmap,
            "role_info": role_meta,
            "qualification_check": qual_check,
        }

    return {
        "filename": path.name,
        "detected_skills": detected_skills,
        "skills_by_category": skills_by_category,
        "education": education,
        "sections": sections,
        "top_roles": top_roles,
        "all_roles": all_ranked_roles,
        "target_role": target_gap_data,
    }
