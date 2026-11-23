"""
Test suite for Flask web application (Module 3).

Tests:
1. Upload valid PDF -> 302 redirect and analysis saved in SQLite.
2. Follow redirect to /results/<id> -> 200, displays headline skill match & tiers.
3. Non-PDF rejected with friendly message.
4. Empty file rejected.
5. Oversized file (> 5 MB) rejected with 413.
6. History lists the analysis.
7. Delete removes the analysis record.
8. Dashboard page loads with visual containers.
9. 404 page handles non-existent IDs gracefully.
"""

import io
from pathlib import Path
import sys
import tempfile
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app
from database import (
    get_all_applications,
    get_analysis,
    get_application,
    get_application_counts,
    init_db,
)

SAMPLE_RESUMES_DIR = Path(__file__).resolve().parent.parent / "sample_resumes"


class TestApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure app for testing
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

    def setUp(self):
        # Ensure schema exists before each test
        init_db()

    def test_01_index_page(self):
        """Home page should load with status 200, display resume upload form and no target role selector."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"AI Resume Analyzer", response.data)
        self.assertIn(b"Analyze Resume", response.data)
        self.assertNotIn(b"<select", response.data)
        self.assertNotIn(b"target_role", response.data)

    def test_02_upload_valid_pdf(self):
        """Valid PDF upload should analyze resume, persist row, and redirect to results."""
        sample_pdf = SAMPLE_RESUMES_DIR / "java_backend.pdf"
        self.assertTrue(sample_pdf.exists(), f"Sample PDF missing: {sample_pdf}")

        with open(sample_pdf, "rb") as f:
            pdf_bytes = f.read()

        response = self.client.post(
            "/analyze",
            data={
                "resume": (io.BytesIO(pdf_bytes), "java_backend.pdf"),
            },
            content_type="multipart/form-data",
        )

        # Should redirect to /results/<analysis_id>
        self.assertEqual(response.status_code, 302)
        location = response.headers.get("Location", "")
        self.assertIn("/results/", location)

        # Extract analysis ID
        analysis_id = int(location.split("/results/")[-1])

        # Verify database record exists
        record = get_analysis(analysis_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["filename"], "java_backend.pdf")
        self.assertIn("Java", record["detected_skills"])

        # Follow redirect to results page
        res_page = self.client.get(location)
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b"Headline Skill Match", res_page.data)
        self.assertIn(b"Context similarity", res_page.data)
        self.assertIn(b"Top 5 Role Matches", res_page.data)

    def test_03_non_pdf_rejected(self):
        """Non-PDF file (e.g. .txt) must be rejected with a friendly message."""
        txt_content = b"Candidate Name: John Doe\nSkills: Python, React"
        response = self.client.post(
            "/analyze",
            data={
                "resume": (io.BytesIO(txt_content), "candidate_resume.txt"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Only PDF files (.pdf) are accepted", response.data)

    def test_04_empty_pdf_rejected(self):
        """Empty 0-byte upload should be rejected with a friendly message."""
        response = self.client.post(
            "/analyze",
            data={
                "resume": (io.BytesIO(b""), "empty_resume.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The uploaded file is empty", response.data)

    def test_05_oversized_file_rejected(self):
        """File larger than 5 MB must trigger 413 Request Entity Too Large."""
        # 5.5 MB payload
        large_payload = b"%PDF-1.4\n" + (b"A" * (5500000))
        response = self.client.post(
            "/analyze",
            data={
                "resume": (io.BytesIO(large_payload), "large_resume.pdf"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 413)
        self.assertIn(b"Resume Exceeds 5 MB Limit", response.data)

    def test_06_history_and_delete(self):
        """History lists past analyses, and delete action removes them."""
        # Upload a resume first
        sample_pdf = SAMPLE_RESUMES_DIR / "fresher_python.pdf"
        with open(sample_pdf, "rb") as f:
            pdf_bytes = f.read()

        upload_res = self.client.post(
            "/analyze",
            data={
                "resume": (io.BytesIO(pdf_bytes), "fresher_python.pdf"),
                "target_role": "Best fit across all roles",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(upload_res.status_code, 302)
        analysis_id = int(upload_res.headers.get("Location", "").split("/results/")[-1])

        # Check history page
        hist_res = self.client.get("/history")
        self.assertEqual(hist_res.status_code, 200)
        self.assertIn(b"fresher_python.pdf", hist_res.data)

        # Delete the analysis
        del_res = self.client.post(f"/delete/{analysis_id}", follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        self.assertIn(b"Analysis record deleted successfully", del_res.data)

        # Verify record no longer exists in DB
        self.assertIsNone(get_analysis(analysis_id))

    def test_07_dashboard_view(self):
        """Dashboard page renders canvas elements and dataset container."""
        sample_pdf = SAMPLE_RESUMES_DIR / "data_analyst_bi.pdf"
        with open(sample_pdf, "rb") as f:
            pdf_bytes = f.read()

        upload_res = self.client.post(
            "/analyze",
            data={
                "resume": (io.BytesIO(pdf_bytes), "data_analyst.pdf"),
                "target_role": "Data Analyst",
            },
            content_type="multipart/form-data",
        )
        analysis_id = int(upload_res.headers.get("Location", "").split("/results/")[-1])

        dash_res = self.client.get(f"/dashboard/{analysis_id}")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"rolesBarChart", dash_res.data)
        self.assertIn(b"skillsDoughnutChart", dash_res.data)
        self.assertIn(b"checklist-items-container", dash_res.data)
        self.assertIn(b"id=\"dashboard-data\"", dash_res.data)

    def test_08_not_found_handling(self):
        """Non-existent analysis ID returns 404 page."""
        response = self.client.get("/results/999999")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"404", response.data)
        self.assertIn(b"Analysis or Page Not Found", response.data)

    def test_09_jobs_catalog_and_filtering(self):
        """Verify /jobs page loads and supports filtering by title, experience, and skill."""
        # 1. Base /jobs catalog loads all jobs
        resp_all = self.client.get("/jobs")
        self.assertEqual(resp_all.status_code, 200)
        self.assertIn(b"Browse Stored Job Catalog", resp_all.data)
        self.assertIn(b"JOB_001", resp_all.data)

        # 2. Filter by title / category
        resp_title = self.client.get("/jobs?title_category=Python")
        self.assertEqual(resp_title.status_code, 200)
        self.assertIn(b"Python Developer", resp_title.data)

        # 3. Filter by experience
        resp_exp = self.client.get("/jobs?experience=Entry-level")
        self.assertEqual(resp_exp.status_code, 200)
        self.assertIn(b"Entry-level", resp_exp.data)

        # 4. Filter by skill
        resp_skill = self.client.get("/jobs?skill=Docker")
        self.assertEqual(resp_skill.status_code, 200)
        self.assertIn(b"Docker", resp_skill.data)

    def test_10_application_tracker_crud(self):
        """Verify full lifecycle of job application tracking: create, view, edit, filter, delete."""
        # 1. View /applications
        resp_view = self.client.get("/applications")
        self.assertEqual(resp_view.status_code, 200)
        self.assertIn(b"Job Application Tracker", resp_view.data)

        # 2. Add an application
        add_resp = self.client.post(
            "/applications/add",
            data={
                "job_title": "Full Stack Engineer",
                "company": "Acme Corp",
                "status": "Applied",
                "applied_date": "2026-10-28",
                "notes": "Passed screen, tech round scheduled.",
                "link": "https://example.com/jobs/123",
            },
            follow_redirects=True,
        )
        self.assertEqual(add_resp.status_code, 200)
        self.assertIn(b"Full Stack Engineer", add_resp.data)
        self.assertIn(b"Acme Corp", add_resp.data)

        # Verify in DB
        apps = get_all_applications(status_filter="Applied")
        acme_app = next((a for a in apps if a["company"] == "Acme Corp"), None)
        self.assertIsNotNone(acme_app)
        app_id = acme_app["id"]

        # 3. Edit application status to Interviewing
        edit_resp = self.client.post(
            f"/applications/edit/{app_id}",
            data={
                "job_title": "Full Stack Engineer",
                "company": "Acme Corp",
                "status": "Interviewing",
                "applied_date": "2026-10-28",
                "notes": "Completed round 1.",
                "link": "https://example.com/jobs/123",
            },
            follow_redirects=True,
        )
        self.assertEqual(edit_resp.status_code, 200)
        self.assertIn(b"Application record updated successfully", edit_resp.data)

        # Check DB reflects updated status
        updated = get_application(app_id)
        self.assertEqual(updated["status"], "Interviewing")

        # 4. Filter by status
        filter_resp = self.client.get("/applications?status=Interviewing")
        self.assertEqual(filter_resp.status_code, 200)
        self.assertIn(b"Acme Corp", filter_resp.data)

        # 5. Delete application
        del_resp = self.client.post(f"/applications/delete/{app_id}", follow_redirects=True)
        self.assertEqual(del_resp.status_code, 200)
        self.assertIn(b"Application record deleted", del_resp.data)
        self.assertIsNone(get_application(app_id))

    def test_11_application_invalid_inputs(self):
        """Verify validation prevents empty or excessively long inputs."""
        # Missing job_title
        resp_no_title = self.client.post(
            "/applications/add",
            data={"job_title": "", "company": "Google", "status": "Applied"},
            follow_redirects=True,
        )
        self.assertIn(b"Job title is required", resp_no_title.data)

        # Missing company
        resp_no_comp = self.client.post(
            "/applications/add",
            data={"job_title": "Backend Dev", "company": "", "status": "Applied"},
            follow_redirects=True,
        )
        self.assertIn(b"Company name is required", resp_no_comp.data)

        # Title exceeds max length (200 chars)
        long_title = "A" * 205
        resp_long_title = self.client.post(
            "/applications/add",
            data={"job_title": long_title, "company": "Valid Company", "status": "Applied"},
            follow_redirects=True,
        )
        self.assertIn(b"cannot exceed 200 characters", resp_long_title.data)


if __name__ == "__main__":
    unittest.main()
