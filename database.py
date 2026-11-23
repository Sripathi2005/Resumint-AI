"""
Database layer for AI Resume Analyzer.

Uses Python standard library sqlite3 without an ORM.
Manages SQLite storage in instance/resume_analyzer.db using parameterized queries.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Union

DEFAULT_DB_DIR = Path(__file__).resolve().parent / "instance"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "resume_analyzer.db"


def get_db(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Obtain a SQLite database connection with row factory configured."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """Initialize analyses and applications table schemas if they do not already exist."""
    conn = get_db(db_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    filename TEXT NOT NULL,
                    target_role TEXT,
                    detected_skills TEXT NOT NULL,
                    results TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    status TEXT NOT NULL,
                    applied_date TEXT,
                    notes TEXT,
                    link TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
    finally:
        conn.close()


def insert_analysis(
    filename: str,
    target_role: Optional[str],
    detected_skills: List[str],
    results: Dict[str, Any],
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """
    Insert a completed resume analysis record.

    Args:
        filename: Name of the uploaded resume PDF.
        target_role: Selected target role or 'Best fit across all roles'.
        detected_skills: List of detected skill names.
        results: Full analysis results dictionary.
        db_path: Optional custom database file path.

    Returns:
        The integer primary key (id) of the inserted analysis.
    """
    conn = get_db(db_path)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    skills_json = json.dumps(detected_skills)
    results_json = json.dumps(results)

    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO analyses (created_at, filename, target_role, detected_skills, results)
                VALUES (?, ?, ?, ?, ?)
                """,
                (now_str, filename, target_role or "Best fit across all roles", skills_json, results_json),
            )
            inserted_id = cursor.lastrowid
            return int(inserted_id)
    finally:
        conn.close()


def get_analysis(
    analysis_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve an analysis by its ID, decoding JSON fields.

    Returns:
        Dictionary representation of analysis record, or None if not found.
    """
    conn = get_db(db_path)
    try:
        row = conn.execute(
            "SELECT id, created_at, filename, target_role, detected_skills, results FROM analyses WHERE id = ?",
            (analysis_id,),
        ).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "filename": row["filename"],
            "target_role": row["target_role"],
            "detected_skills": json.loads(row["detected_skills"]),
            "results": json.loads(row["results"]),
        }
    finally:
        conn.close()


def get_all_analyses(
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve all historical analyses ordered by creation date descending.
    """
    conn = get_db(db_path)
    try:
        rows = conn.execute(
            """
            SELECT id, created_at, filename, target_role, detected_skills, results
            FROM analyses
            ORDER BY id DESC
            """
        ).fetchall()

        analyses = []
        for r in rows:
            res_dict = json.loads(r["results"])
            if res_dict.get("comparison_type") == "job_benchmark":
                top_role_title = res_dict.get("title", "Job Benchmark")
                top_skill_score = res_dict.get("match_pct", 0.0)
                top_tier = res_dict.get("tier", "Match")
            else:
                top_roles = res_dict.get("top_roles", [])
                top_role_title = top_roles[0]["title"] if top_roles else "N/A"
                top_skill_score = top_roles[0]["skill_score"] if top_roles else 0.0
                top_tier = top_roles[0].get("tier", "Match") if top_roles else "N/A"

            analyses.append({
                "id": r["id"],
                "created_at": r["created_at"],
                "filename": r["filename"],
                "target_role": r["target_role"],
                "detected_skills": json.loads(r["detected_skills"]),
                "top_role_title": top_role_title,
                "top_skill_score": top_skill_score,
                "top_tier": top_tier,
                "results": res_dict,
            })
        return analyses
    finally:
        conn.close()


def delete_analysis(
    analysis_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Delete an analysis record by its primary key ID.

    Returns:
        True if record was deleted, False if no row existed.
    """
    conn = get_db(db_path)
    try:
        with conn:
            cursor = conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()


VALID_STATUSES = ["Saved", "Applied", "Interviewing", "Offer", "Rejected"]


def insert_application(
    job_title: str,
    company: str,
    status: str,
    applied_date: Optional[str] = None,
    notes: Optional[str] = None,
    link: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """
    Insert a tracked job application.

    Returns:
        Integer ID of the inserted application record.
    """
    if status not in VALID_STATUSES:
        status = "Saved"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO applications (job_title, company, status, applied_date, notes, link, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_title.strip()[:200],
                    company.strip()[:200],
                    status,
                    (applied_date.strip()[:50] if applied_date else None),
                    (notes.strip()[:2000] if notes else None),
                    (link.strip()[:500] if link else None),
                    now_str,
                ),
            )
            return int(cursor.lastrowid)
    finally:
        conn.close()


def get_application(
    application_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve an application by its ID."""
    conn = get_db(db_path)
    try:
        row = conn.execute(
            """
            SELECT id, job_title, company, status, applied_date, notes, link, created_at
            FROM applications
            WHERE id = ?
            """,
            (application_id,),
        ).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "job_title": row["job_title"],
            "company": row["company"],
            "status": row["status"],
            "applied_date": row["applied_date"],
            "notes": row["notes"],
            "link": row["link"],
            "created_at": row["created_at"],
        }
    finally:
        conn.close()


def get_all_applications(
    status_filter: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve all applications ordered by creation date descending,
    optionally filtered by status.
    """
    conn = get_db(db_path)
    try:
        if status_filter and status_filter in VALID_STATUSES:
            rows = conn.execute(
                """
                SELECT id, job_title, company, status, applied_date, notes, link, created_at
                FROM applications
                WHERE status = ?
                ORDER BY id DESC
                """,
                (status_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, job_title, company, status, applied_date, notes, link, created_at
                FROM applications
                ORDER BY id DESC
                """
            ).fetchall()

        return [
            {
                "id": r["id"],
                "job_title": r["job_title"],
                "company": r["company"],
                "status": r["status"],
                "applied_date": r["applied_date"],
                "notes": r["notes"],
                "link": r["link"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def update_application(
    application_id: int,
    job_title: str,
    company: str,
    status: str,
    applied_date: Optional[str] = None,
    notes: Optional[str] = None,
    link: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Update an existing job application record."""
    if status not in VALID_STATUSES:
        status = "Saved"

    conn = get_db(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE applications
                SET job_title = ?, company = ?, status = ?, applied_date = ?, notes = ?, link = ?
                WHERE id = ?
                """,
                (
                    job_title.strip()[:200],
                    company.strip()[:200],
                    status,
                    (applied_date.strip()[:50] if applied_date else None),
                    (notes.strip()[:2000] if notes else None),
                    (link.strip()[:500] if link else None),
                    application_id,
                ),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_application(
    application_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Delete an application record by its ID."""
    conn = get_db(db_path)
    try:
        with conn:
            cursor = conn.execute("DELETE FROM applications WHERE id = ?", (application_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()


def get_application_counts(db_path: Optional[Union[str, Path]] = None) -> Dict[str, int]:
    """Retrieve counts for all applications and each status category."""
    conn = get_db(db_path)
    try:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) as count
            FROM applications
            GROUP BY status
            """
        ).fetchall()

        counts = {status: 0 for status in VALID_STATUSES}
        total = 0
        for r in rows:
            st = r["status"]
            cnt = r["count"]
            if st in counts:
                counts[st] = cnt
            total += cnt

        counts["Total"] = total
        return counts
    finally:
        conn.close()
