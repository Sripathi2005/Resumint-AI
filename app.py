"""
Flask Application for AI Resume Analyzer (Module 3).

Features:
- Resume upload (PDF only, max 5 MB).
- Automatic text extraction, hybrid role ranking, and prioritized gap analysis via pipeline.
- SQLite database storage for analysis records with parameterized queries (no PDF saved on disk).
- Dynamic Chart.js dashboard and market-demand learning checklist with localStorage persistence.
- Friendly error handling and custom 404 / 413 error templates.
"""

import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from database import (
    delete_analysis,
    delete_application,
    get_all_analyses,
    get_all_applications,
    get_analysis,
    get_application,
    get_application_counts,
    init_db,
    insert_analysis,
    insert_application,
    update_application,
)
from modules.job_matcher import load_jobs
from modules.pipeline import (
    _evaluate_qualifications,
    analyze_resume,
    categorize_skills,
    compare_resume_to_job,
)
from modules.recommender import learning_checklist, load_learning_resources
from modules.resume_parser import (
    CorruptedPDFError,
    EmptyPDFError,
    InvalidPDFError,
    ResumeNotFoundError,
    ResumeParserError,
)

# Initialize Flask App
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "resume-analyzer-dev-secret-key-309482")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

# Preload available role titles, job lookup, and beginner-friendly role profiles
from modules.recommender import (
    generate_career_roadmap,
    get_role_info,
    load_job_roles_info,
)

try:
    _JOBS_DF = load_jobs()
    AVAILABLE_ROLES: List[str] = sorted(_JOBS_DF["title"].unique().tolist())
    _JOBS_LOOKUP = {row["job_id"]: row.to_dict() for _, row in _JOBS_DF.iterrows()}
    _JOBS_TITLE_LOOKUP = {str(row["title"]).lower(): row.to_dict() for _, row in _JOBS_DF.iterrows()}
except Exception:
    _JOBS_DF = None
    AVAILABLE_ROLES = [
        "Backend Developer",
        "Business Analyst",
        "Cloud Engineer",
        "Cybersecurity Analyst",
        "Data Analyst",
        "Data Engineer",
        "Data Scientist",
        "Database Administrator",
        "DevOps Engineer",
        "Embedded Systems Engineer",
        "Frontend Developer",
        "Full Stack Developer",
        "Java Developer",
        "ML Engineer",
        "Mobile Developer",
        "Network Engineer",
        "PHP Developer",
        "Python Developer",
        "QA/Test Engineer",
        "Software Engineer",
        "UI/UX Designer",
    ]
    _JOBS_LOOKUP = {}
    _JOBS_TITLE_LOOKUP = {}


def _enrich_target_role(res_dict: Dict[str, Any]) -> None:
    """
    Ensure stored or fresh analysis results always include multi-platform
    learning recommendations, beginner-friendly role metadata, and a personalized
    sequential career roadmap (handles legacy SQLite rows gracefully).
    """
    target = res_dict.get("target_role")
    if not isinstance(target, dict):
        return

    role_title = target.get("title", "")
    detected_skills = res_dict.get("detected_skills", []) or []
    soft_skills = target.get("soft_skills", []) or []

    if not target.get("role_info"):
        target["role_info"] = get_role_info(role_title)
    if target.get("role_info") and not target.get("slug"):
        target["slug"] = target["role_info"].get("slug", "")

    checklist = target.get("learning_checklist")
    needs_checklist = (
        not checklist
        or not isinstance(checklist[0], dict)
        or "platform" not in checklist[0]
        or "resources" not in checklist[0]
        or "why_important" not in checklist[0]
    )
    if needs_checklist:
        target["learning_checklist"] = learning_checklist(
            target.get("missing", []),
            role_title=role_title,
            role_info=target.get("role_info"),
        )

    roadmap = target.get("career_roadmap")
    needs_roadmap = not roadmap or not roadmap.get("stages") or (
        roadmap["stages"][0].get("stage_status") in {"completed", "in_progress", "upcoming"}
    )
    if needs_roadmap and role_title:
        target["career_roadmap"] = generate_career_roadmap(
            role_title,
            detected_skills=detected_skills,
            detected_soft_skills=soft_skills,
        )
    if not target.get("qualification_check"):
        target["qualification_check"] = _evaluate_qualifications(
            res_dict.get("education", []) or [],
            soft_skills,
            target.get("role_info"),
        )

# Ensure DB schema is initialized
with app.app_context():
    init_db()


@app.route("/", methods=["GET"])
def index():
    """
    Feature 1: Analyze Resume – General Job Recommendations.
    Render home page with resume upload form (no target role selection).
    """
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Feature 1: Handle resume upload for general job recommendations.
    Extracts skills from resume, compares against all available job postings in database,
    and redirects to results page displaying top matching job roles.
    """
    if "resume" not in request.files:
        flash("No resume file was submitted. Please select a PDF file.", "error")
        return redirect(url_for("index"))

    file = request.files["resume"]
    if not file or file.filename == "":
        flash("No file was selected. Please choose a PDF file to upload.", "error")
        return redirect(url_for("index"))

    filename = file.filename
    # Strict validation: accept only .pdf
    if not filename.lower().endswith(".pdf"):
        flash("Only PDF files (.pdf) are accepted. Please upload a valid PDF document.", "error")
        return redirect(url_for("index"))

    safe_name = secure_filename(filename) or "uploaded_resume.pdf"

    # Save to a secure temporary location for processing
    temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(temp_fd)

    try:
        file.save(temp_path)

        # Check for 0-byte file
        if os.path.getsize(temp_path) == 0:
            flash("The uploaded file is empty (0 bytes). Please upload a valid resume PDF.", "error")
            return redirect(url_for("index"))

        # Run general job recommendation matching across all jobs in dataset
        analysis_result = analyze_resume(
            pdf_path=temp_path,
            role=None,
            top_n=5,
            jobs_df=_JOBS_DF,
            job_id=None,
        )

        # Persist structured record into SQLite
        analysis_id = insert_analysis(
            filename=safe_name,
            target_role="Best fit across all roles",
            detected_skills=analysis_result.get("detected_skills", []),
            results=analysis_result,
        )

        return redirect(url_for("results", analysis_id=analysis_id))

    except InvalidPDFError:
        flash("The uploaded file is not a valid PDF document. Please verify the file and try again.", "error")
        return redirect(url_for("index"))
    except CorruptedPDFError:
        flash("The PDF file appears corrupted or unreadable. Please check the file and try again.", "error")
        return redirect(url_for("index"))
    except EmptyPDFError:
        flash(
            "No extractable text was found in this PDF. It may be a scanned image without a text layer. "
            "Please upload a text-based PDF.",
            "error",
        )
        return redirect(url_for("index"))
    except ResumeNotFoundError:
        flash("The uploaded resume file could not be accessed. Please try uploading again.", "error")
        return redirect(url_for("index"))
    except ResumeParserError as rpe:
        flash(f"Resume parsing issue: {str(rpe)}", "error")
        return redirect(url_for("index"))
    except Exception:
        flash("An unexpected error occurred while analyzing the resume. Please try again with another file.", "error")
        return redirect(url_for("index"))
    finally:
        # Close uploaded stream if open
        try:
            file.close()
        except Exception:
            pass
        # Guarantee privacy: delete temporary PDF immediately after processing
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@app.route("/jobs/compare/<job_id>", methods=["GET", "POST"])
def compare_job(job_id: str):
    """
    Feature 2: Explore Job Benchmarks – Compare Resume Against a Selected Job.
    GET: Render dedicated resume upload interface for the selected job posting.
    POST: Compare uploaded resume directly against this exact job posting's requirements.
    """
    clean_jid = str(job_id).strip()
    job = _JOBS_LOOKUP.get(clean_jid)
    if not job:
        # Try case-insensitive lookup
        for k, v in _JOBS_LOOKUP.items():
            if str(k).lower() == clean_jid.lower():
                job = v
                break

    if not job:
        flash(f"Job posting '{job_id}' was not found in the database.", "error")
        return redirect(url_for("jobs_catalog"))

    if request.method == "GET":
        return render_template("compare_job.html", job=job)

    # POST: handle resume upload and evaluate against this job
    if "resume" not in request.files:
        flash("No resume file was submitted. Please select a PDF file.", "error")
        return redirect(url_for("compare_job", job_id=job["job_id"]))

    file = request.files["resume"]
    if not file or file.filename == "":
        flash("No file was selected. Please choose a PDF file to upload.", "error")
        return redirect(url_for("compare_job", job_id=job["job_id"]))

    filename = file.filename
    if not filename.lower().endswith(".pdf"):
        flash("Only PDF files (.pdf) are accepted. Please upload a valid PDF document.", "error")
        return redirect(url_for("compare_job", job_id=job["job_id"]))

    safe_name = secure_filename(filename) or "uploaded_resume.pdf"
    temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(temp_fd)

    try:
        file.save(temp_path)
        if os.path.getsize(temp_path) == 0:
            flash("The uploaded file is empty (0 bytes). Please upload a valid resume PDF.", "error")
            return redirect(url_for("compare_job", job_id=job["job_id"]))

        # Execute dedicated comparison strictly against this job posting
        comparison_result = compare_resume_to_job(
            pdf_path=temp_path,
            job_id=job["job_id"],
            jobs_df=_JOBS_DF,
        )

        analysis_id = insert_analysis(
            filename=safe_name,
            target_role=f"Job Benchmark: {job['title']} ({job['job_id']})",
            detected_skills=comparison_result.get("detected_skills", []),
            results=comparison_result,
        )

        return redirect(url_for("job_comparison_result", comparison_id=analysis_id))

    except InvalidPDFError:
        flash("The uploaded file is not a valid PDF document. Please verify the file and try again.", "error")
        return redirect(url_for("compare_job", job_id=job["job_id"]))
    except CorruptedPDFError:
        flash("The PDF file appears corrupted or unreadable. Please check the file and try again.", "error")
        return redirect(url_for("compare_job", job_id=job["job_id"]))
    except EmptyPDFError:
        flash("No extractable text was found in this PDF. Please upload a text-based PDF.", "error")
        return redirect(url_for("compare_job", job_id=job["job_id"]))
    except ResumeParserError as rpe:
        flash(f"Resume parsing issue: {str(rpe)}", "error")
        return redirect(url_for("compare_job", job_id=job["job_id"]))
    except Exception:
        flash("An unexpected error occurred while analyzing the resume against the selected job.", "error")
        return redirect(url_for("compare_job", job_id=job["job_id"]))
    finally:
        try:
            file.close()
        except Exception:
            pass
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@app.route("/jobs/compare/results/<int:comparison_id>", methods=["GET"])
def job_comparison_result(comparison_id: int):
    """Display dedicated comparison results for Feature 2 (Selected Job Benchmark)."""
    return results(comparison_id)


@app.route("/results/<int:analysis_id>", methods=["GET"])
def results(analysis_id: int):
    """
    Display results:
    - If this analysis was a dedicated job comparison (Feature 2), render job_comparison_result.html.
    - Otherwise, render general job recommendations (Feature 1) in results.html.
    """
    analysis = get_analysis(analysis_id)
    if not analysis:
        abort(404)

    res_dict = analysis.get("results", {})

    # Feature 2: Dedicated Job Benchmark Comparison Result
    if res_dict.get("comparison_type") == "job_benchmark":
        return render_template(
            "job_comparison_result.html",
            analysis=analysis,
            comparison=res_dict,
        )

    # Feature 1: General Job Recommendations
    # Ensure skills_by_category is populated
    if "skills_by_category" not in res_dict:
        res_dict["skills_by_category"] = categorize_skills(analysis.get("detected_skills", []))

    # Enrich top_roles with description if missing
    for role in res_dict.get("top_roles", []):
        if not role.get("description"):
            lookup = _JOBS_LOOKUP.get(role.get("job_id")) or _JOBS_TITLE_LOOKUP.get(str(role.get("title", "")).lower())
            if lookup:
                role["description"] = lookup.get("description", "")
                role["category"] = lookup.get("category", "")
                role["experience_level"] = lookup.get("experience_level", "")
                role["required_skills"] = lookup.get("required_skills", [])
                role["preferred_skills"] = lookup.get("preferred_skills", [])

    # Ensure target_role has rich multi-platform learning checklist, role info & roadmap
    _enrich_target_role(res_dict)

    return render_template("results.html", analysis=analysis)


@app.route("/dashboard/<int:analysis_id>", methods=["GET"])
def dashboard(analysis_id: int):
    """Display Chart.js visualization, interactive role switching, and learning roadmap."""
    analysis = get_analysis(analysis_id)
    if not analysis:
        abort(404)

    res_dict = analysis.get("results", {})
    if res_dict.get("comparison_type") == "job_benchmark":
        flash("The multi-role visual dashboard is for general resume analyses. Showing your job comparison results below.", "info")
        return redirect(url_for("job_comparison_result", comparison_id=analysis_id))

    # Ensure skills_by_category is populated
    if "skills_by_category" not in res_dict:
        res_dict["skills_by_category"] = categorize_skills(analysis.get("detected_skills", []))

    # Enrich all_roles with description if missing
    for role in res_dict.get("all_roles", []):
        if not role.get("description"):
            lookup = _JOBS_LOOKUP.get(role.get("job_id")) or _JOBS_TITLE_LOOKUP.get(str(role.get("title", "")).lower())
            if lookup:
                role["description"] = lookup.get("description", "")
                role["category"] = lookup.get("category", "")
                role["experience_level"] = lookup.get("experience_level", "")
                role["required_skills"] = lookup.get("required_skills", [])
                role["preferred_skills"] = lookup.get("preferred_skills", [])

    _enrich_target_role(res_dict)
    learning_resources = load_learning_resources()

    return render_template(
        "dashboard.html",
        analysis=analysis,
        learning_resources=learning_resources,
    )


@app.route("/roles")
@app.route("/roles/<role_slug>")
def roles_explorer(role_slug: Optional[str] = None):
    """
    Job Role Explorer & Personalized Career Roadmap view (Requirement 3).
    Allows students to explore beginner-friendly IT role details standalone or
    personalize the sequential learning roadmap against an uploaded resume analysis.
    """
    roles_info = load_job_roles_info()
    all_roles = sorted(roles_info.values(), key=lambda r: r.get("title", ""))

    # Group roles by category for easy browsing
    roles_by_category: Dict[str, List[Dict[str, Any]]] = {}
    for role in all_roles:
        cat = role.get("category", "Technology")
        roles_by_category.setdefault(cat, []).append(role)

    # Optional pre-selected role via path slug or ?role=... query param
    requested_role = role_slug or request.args.get("role", "").strip()
    selected_role = get_role_info(requested_role) if requested_role else None
    if selected_role is None and all_roles:
        selected_role = get_role_info("Python Developer") or all_roles[0]

    # Optional resume analysis context to personalize known vs missing skills
    analyses = get_all_analyses()[:25]
    raw_aid = request.args.get("analysis_id", "").strip()
    selected_analysis = None
    detected_skills: List[str] = []
    detected_soft_skills: List[str] = []

    if raw_aid.isdigit():
        selected_analysis = get_analysis(int(raw_aid))
    elif analyses and request.args.get("latest") == "1":
        selected_analysis = get_analysis(analyses[0]["id"])

    if selected_analysis and isinstance(selected_analysis.get("results"), dict):
        res_data = selected_analysis["results"]
        detected_skills = res_data.get("detected_skills", []) or []
        target = res_data.get("target_role") or {}
        detected_soft_skills = target.get("soft_skills", []) or []

    roadmap = (
        generate_career_roadmap(
            selected_role["title"],
            detected_skills=detected_skills,
            detected_soft_skills=detected_soft_skills,
        )
        if selected_role
        else None
    )

    return render_template(
        "roles.html",
        all_roles=all_roles,
        roles_by_category=roles_by_category,
        selected_role=selected_role,
        roadmap=roadmap,
        analyses=analyses,
        selected_analysis=selected_analysis,
        detected_skills=detected_skills,
    )


@app.route("/api/role-roadmap")
def api_role_roadmap():
    """Return role metadata and personalized roadmap as JSON for dynamic updates."""
    role_param = request.args.get("role", "").strip()
    role_info = get_role_info(role_param)
    if not role_info:
        return jsonify({"error": "Role not found"}), 404

    detected_skills: List[str] = []
    detected_soft_skills: List[str] = []
    raw_aid = request.args.get("analysis_id", "").strip()

    if raw_aid.isdigit():
        analysis = get_analysis(int(raw_aid))
        if analysis and isinstance(analysis.get("results"), dict):
            res_data = analysis["results"]
            detected_skills = res_data.get("detected_skills", []) or []
            target = res_data.get("target_role") or {}
            detected_soft_skills = target.get("soft_skills", []) or []
    elif request.args.get("skills", "").strip():
        detected_skills = [s.strip() for s in request.args.get("skills", "").split(",") if s.strip()]

    roadmap = generate_career_roadmap(
        role_info["title"],
        detected_skills=detected_skills,
        detected_soft_skills=detected_soft_skills,
    )
    return jsonify({
        "role_info": role_info,
        "roadmap": roadmap,
        "detected_skills": detected_skills,
    })


@app.route("/jobs", methods=["GET"])
def jobs_catalog():
    """Browse and filter jobs in data/jobs.csv by title/category, experience level, and required skill."""
    title_category = request.args.get("title_category", "").strip()
    experience = request.args.get("experience", "All").strip()
    skill = request.args.get("skill", "").strip()

    filtered = _JOBS_DF.copy()

    if title_category:
        tc_lower = title_category.lower()
        filtered = filtered[
            filtered["title"].astype(str).str.lower().str.contains(tc_lower, na=False) |
            filtered["category"].astype(str).str.lower().str.contains(tc_lower, na=False)
        ]

    if experience and experience != "All":
        filtered = filtered[filtered["experience_level"].astype(str).str.lower() == experience.lower()]

    if skill:
        s_lower = skill.lower()
        def has_skill(req_list):
            if isinstance(req_list, list):
                return any(s_lower in str(s).lower() for s in req_list)
            return s_lower in str(req_list).lower()
        filtered = filtered[filtered["required_skills"].apply(has_skill)]

    jobs_list = filtered.to_dict(orient="records")
    exp_levels = sorted(_JOBS_DF["experience_level"].unique().tolist()) if not _JOBS_DF.empty else []

    return render_template(
        "jobs.html",
        jobs=jobs_list,
        total_jobs=len(_JOBS_DF),
        experience_levels=exp_levels,
        filter_title_category=title_category,
        filter_experience=experience,
        filter_skill=skill,
    )


@app.route("/applications", methods=["GET"])
def applications():
    """List tracked applications with status counts and optional status filter."""
    status_filter = request.args.get("status", "").strip()
    prefill_title = request.args.get("add_title", "").strip()

    counts = get_application_counts()
    apps = get_all_applications(status_filter=status_filter if status_filter and status_filter != "All" else None)

    return render_template(
        "applications.html",
        applications=apps,
        counts=counts,
        current_status=status_filter,
        prefill_title=prefill_title,
    )


@app.route("/applications/add", methods=["POST"])
def add_application_route():
    """Create a new job application tracking entry with input validation."""
    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    status = request.form.get("status", "Applied").strip()
    applied_date = request.form.get("applied_date", "").strip()
    link = request.form.get("link", "").strip()
    notes = request.form.get("notes", "").strip()

    if not job_title:
        flash("Job title is required.", "error")
        return redirect(url_for("applications"))
    if len(job_title) > 200:
        flash("Job title cannot exceed 200 characters.", "error")
        return redirect(url_for("applications"))

    if not company:
        flash("Company name is required.", "error")
        return redirect(url_for("applications"))
    if len(company) > 200:
        flash("Company name cannot exceed 200 characters.", "error")
        return redirect(url_for("applications"))

    if status not in ["Saved", "Applied", "Interviewing", "Offer", "Rejected"]:
        status = "Saved"

    if len(link) > 500:
        flash("Application URL cannot exceed 500 characters.", "error")
        return redirect(url_for("applications"))

    if len(notes) > 2000:
        flash("Notes cannot exceed 2000 characters.", "error")
        return redirect(url_for("applications"))

    insert_application(
        job_title=job_title,
        company=company,
        status=status,
        applied_date=applied_date or None,
        notes=notes or None,
        link=link or None,
    )

    flash(f"Application for '{job_title}' at '{company}' tracked successfully.", "success")
    return redirect(url_for("applications"))


@app.route("/applications/edit/<int:app_id>", methods=["POST"])
def edit_application_route(app_id: int):
    """Update an existing job application tracking entry."""
    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    status = request.form.get("status", "Saved").strip()
    applied_date = request.form.get("applied_date", "").strip()
    link = request.form.get("link", "").strip()
    notes = request.form.get("notes", "").strip()

    if not job_title or not company:
        flash("Job title and company name are required.", "error")
        return redirect(url_for("applications"))

    if len(job_title) > 200 or len(company) > 200:
        flash("Input exceeds maximum length limit of 200 characters.", "error")
        return redirect(url_for("applications"))

    if len(link) > 500 or len(notes) > 2000:
        flash("Link or notes exceed maximum character limit.", "error")
        return redirect(url_for("applications"))

    updated = update_application(
        application_id=app_id,
        job_title=job_title,
        company=company,
        status=status,
        applied_date=applied_date or None,
        notes=notes or None,
        link=link or None,
    )

    if updated:
        flash("Application record updated successfully.", "success")
    else:
        flash("Application record not found.", "warning")
    return redirect(url_for("applications"))


@app.route("/applications/delete/<int:app_id>", methods=["POST"])
def delete_application_route(app_id: int):
    """Delete a tracked application entry."""
    deleted = delete_application(app_id)
    if deleted:
        flash("Application record deleted.", "info")
    else:
        flash("Application record not found.", "warning")
    return redirect(url_for("applications"))


@app.route("/history", methods=["GET"])
def history():
    """Display previous resume analyses with links and delete options."""
    analyses = get_all_analyses()
    return render_template("history.html", analyses=analyses)


@app.route("/delete/<int:analysis_id>", methods=["POST"])
def delete(analysis_id: int):
    """Delete an analysis record from SQLite."""
    deleted = delete_analysis(analysis_id)
    if deleted:
        flash("Analysis record deleted successfully.", "success")
    else:
        flash("Analysis record not found.", "warning")
    return redirect(url_for("history"))


@app.errorhandler(404)
def page_not_found(e):
    """Render friendly custom 404 page."""
    return render_template("404.html"), 404


@app.errorhandler(413)
def request_entity_too_large(e):
    """Render friendly custom 413 page for files exceeding 5 MB."""
    return render_template("413.html"), 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
