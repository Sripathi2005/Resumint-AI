"""
Test suite verifying:
1. Kaggle dataset integration (jobs.csv, skills.json, soft_skills.json, job_roles_info.json).
2. Multi-platform learning recommendations (2-3 curated, free-first resources per missing skill).
3. Job role beginner-friendly information & sequential personalized career roadmap + Flask routes.
"""

import io
import json
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app
from database import get_analysis, init_db
from modules.job_matcher import load_jobs, validate_jobs_skills
from modules.recommender import (
    generate_career_roadmap,
    get_role_info,
    learning_checklist,
    load_job_roles_info,
    load_learning_resources,
)
from modules.skill_extractor import extract_soft_skills, load_skills, load_soft_skills

DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_RESUMES_DIR = PROJECT_ROOT / "sample_resumes"


class TestKaggleIntegrationAndFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

    def setUp(self):
        init_db()

    def test_01_kaggle_jobs_and_roles_integrity(self):
        """jobs.csv and job_roles_info.json must align cleanly with all 21 roles and skills.json."""
        jobs_df = load_jobs()
        self.assertGreaterEqual(len(jobs_df), 140)
        self.assertGreaterEqual(jobs_df["title"].nunique(), 20)
        self.assertIn("source_dataset", jobs_df.columns)
        validate_jobs_skills(jobs_df)

        roles_info = load_job_roles_info()
        job_titles = set(jobs_df["title"].unique())
        self.assertEqual(job_titles, set(roles_info.keys()))

        with open(DATA_DIR / "skills.json", encoding="utf-8") as f:
            valid_skills = {item["name"] for item in json.load(f)["skills"]}
        for title, info in roles_info.items():
            self.assertTrue(info.get("beginner_summary"), f"Missing beginner_summary for {title}")
            self.assertTrue(info.get("overview"), f"Missing overview for {title}")
            self.assertTrue(info.get("what_they_do"), f"Missing what_they_do for {title}")
            self.assertGreaterEqual(len(info.get("day_to_day_responsibilities", [])), 4)
            self.assertGreaterEqual(len(info.get("career_growth", [])), 3)
            self.assertGreaterEqual(len(info.get("soft_skills", [])), 3)

            # Verify core_skills are full skill names (not sliced characters)
            core = info.get("technical_skills", {}).get("core_skills", [])
            self.assertTrue(core, f"Empty core_skills for {title}")
            for s in core:
                self.assertIn(s, valid_skills, f"Invalid core skill '{s}' in {title}")

            # Verify 4-stage sequential roadmap uses canonical skills
            stages = info.get("learning_roadmap", [])
            self.assertEqual(len(stages), 4, f"Expected 4 stages for {title}")
            for idx, st in enumerate(stages, start=1):
                self.assertEqual(st["stage"], idx)
                for sk in st["skills"]:
                    self.assertIn(sk, valid_skills, f"Unknown stage skill '{sk}' in {title}")

    def test_02_soft_skills_extraction(self):
        """Soft skills taxonomy should load from data/soft_skills.json and extract cleanly."""
        taxonomy = load_soft_skills()
        self.assertGreaterEqual(len(taxonomy), 15)
        sample_text = (
            "Strong problem solving skills, clear written communication, "
            "and cross-functional collaboration under tight deadlines."
        )
        detected = extract_soft_skills(sample_text, taxonomy)
        self.assertIn("Problem Solving", detected)
        self.assertIn("Communication", detected)
        self.assertIn("Collaboration", detected)

    def test_03_multi_platform_learning_resources_coverage(self):
        """Every skill used in jobs.csv & roadmaps must have 2-3 verified real learning resources."""
        resources = load_learning_resources()
        jobs_df = load_jobs()
        roles_info = load_job_roles_info()

        required_skills = set()
        for lst in jobs_df["required_skills"]:
            required_skills.update(lst)
        for info in roles_info.values():
            for st in info.get("learning_roadmap", []):
                required_skills.update(st.get("skills", []))

        for sk in required_skills:
            self.assertIn(sk, resources, f"Skill '{sk}' missing from skill_learning_resources.json")
            entry = resources[sk]
            res_list = entry.get("resources", [])
            self.assertGreaterEqual(len(res_list), 2, f"Expected >=2 resources for {sk}")
            self.assertLessEqual(len(res_list), 3, f"Expected <=3 resources for {sk}")
            for res in res_list:
                self.assertTrue(res.get("platform"))
                self.assertTrue(res.get("title"))
                self.assertTrue(res.get("description"))
                url = res.get("url", "")
                self.assertTrue(url.startswith("http"), f"Bad URL for {sk}: {url}")
                self.assertNotIn("google.com/search", url)

        # Verify learning_checklist returns resources list per missing skill
        checklist = learning_checklist(["React", "Docker", "Kubernetes"])
        self.assertEqual(len(checklist), 3)
        for item in checklist:
            self.assertGreaterEqual(len(item["resources"]), 2)

    def test_04_personalized_career_roadmap_generation(self):
        """Roadmap generator should mark known (direct + implied) vs missing skills with courses."""
        roadmap = generate_career_roadmap(
            "Backend Developer",
            detected_skills=["Python", "PostgreSQL", "Git"],
            detected_soft_skills=["Communication"],
        )
        self.assertIsNotNone(roadmap)
        self.assertEqual(roadmap["role_title"], "Backend Developer")
        self.assertEqual(len(roadmap["stages"]), 4)

        all_stage_skills = {}
        for st in roadmap["stages"]:
            for sk in st["skills"]:
                all_stage_skills[sk["name"]] = sk

        self.assertEqual(all_stage_skills["Python"]["status"], "known")
        self.assertEqual(all_stage_skills["Git"]["status"], "known")
        # PostgreSQL should automatically satisfy SQL via skill_implications.json
        self.assertEqual(all_stage_skills["SQL"]["status"], "known")
        self.assertEqual(all_stage_skills["SQL"]["matched_via"], "PostgreSQL")

        # Missing skill e.g. Docker should attach 2-3 learning resources
        self.assertEqual(all_stage_skills["Docker"]["status"], "missing")
        self.assertGreaterEqual(len(all_stage_skills["Docker"]["resources"]), 2)

    def test_05_roles_explorer_and_api_routes(self):
        """New /roles, /roles/<slug>, and /api/role-roadmap routes must work end-to-end."""
        resp = self.client.get("/roles")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Job Role Explorer", resp.data)
        self.assertIn(b"Cybersecurity Analyst", resp.data)

        resp_slug = self.client.get("/roles/data-scientist")
        self.assertEqual(resp_slug.status_code, 200)
        self.assertIn(b"Data Scientist", resp_slug.data)
        self.assertIn(b"What Professionals Actually Do", resp_slug.data)
        self.assertIn(b"Day-to-Day Responsibilities", resp_slug.data)
        self.assertIn(b"Career Progression Path", resp_slug.data)

        # Every role slug must render cleanly without Jinja errors
        for title, info in load_job_roles_info().items():
            r_page = self.client.get(f"/roles/{info['slug']}")
            self.assertEqual(r_page.status_code, 200, f"Failed rendering /roles/{info['slug']}")
            self.assertIn(title.encode("utf-8"), r_page.data)

        api_resp = self.client.get("/api/role-roadmap?role=Frontend%20Developer&skills=HTML5,CSS3,Git")
        self.assertEqual(api_resp.status_code, 200)
        payload = json.loads(api_resp.data)
        self.assertEqual(payload["role_info"]["title"], "Frontend Developer")
        self.assertGreaterEqual(payload["roadmap"]["known_skills_count"], 3)
        self.assertIn("React", payload["roadmap"]["missing_skills"])

    def test_06_upload_results_and_personalized_role_roadmap(self):
        """Uploading a PDF should populate multi-resource learning cards and personalized /roles roadmap."""
        sample_pdf = SAMPLE_RESUMES_DIR / "java_backend.pdf"
        self.assertTrue(sample_pdf.exists())
        with open(sample_pdf, "rb") as f:
            pdf_bytes = f.read()

        resp = self.client.post(
            "/analyze",
            data={
                "resume": (io.BytesIO(pdf_bytes), "java_backend.pdf"),
                "target_role": "Backend Developer",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 302)
        analysis_id = int(resp.headers["Location"].split("/results/")[-1])

        try:
            # Verify /results renders role guide preview and multi-platform recommendations
            res_page = self.client.get(f"/results/{analysis_id}")
            self.assertEqual(res_page.status_code, 200)
            self.assertIn(b"Explore Full Role Guide", res_page.data)
            self.assertIn(b"Recommended Learning Resources", res_page.data)

            # Verify /roles/<slug>?analysis_id=<id> personalizes known vs need-to-learn skills
            role_page = self.client.get(f"/roles/backend-developer?analysis_id={analysis_id}")
            self.assertEqual(role_page.status_code, 200)
            self.assertIn(b"Already Known", role_page.data)
            self.assertIn(b"java_backend.pdf", role_page.data)
        finally:
            self.client.post(f"/delete/{analysis_id}")
            self.assertIsNone(get_analysis(analysis_id))

    def test_07_compare_resume_targets_selected_job(self):
        """Feature 2: Selecting Compare Resume on a job opens upload interface and compares strictly against that job."""
        # 1. Verify /jobs includes link to /jobs/compare/<job_id>
        jobs_page = self.client.get("/jobs?title_category=Backend")
        self.assertEqual(jobs_page.status_code, 200)
        self.assertIn(b"/jobs/compare/JOB_032", jobs_page.data)

        # 2. Open dedicated upload interface for JOB_032
        compare_page = self.client.get("/jobs/compare/JOB_032")
        self.assertEqual(compare_page.status_code, 200)
        self.assertIn(b"Backend Developer", compare_page.data)
        self.assertIn(b"JOB_032", compare_page.data)
        self.assertIn(b"Compare Resume Against This Job", compare_page.data)

        # 3. Upload resume to compare against this exact job
        sample_pdf = SAMPLE_RESUMES_DIR / "fresher_python.pdf"
        with open(sample_pdf, "rb") as f:
            pdf_bytes = f.read()

        resp = self.client.post(
            "/jobs/compare/JOB_032",
            data={
                "resume": (io.BytesIO(pdf_bytes), "fresher_python.pdf"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 302)
        analysis_id = int(resp.headers["Location"].split("/")[-1])

        try:
            rec = get_analysis(analysis_id)
            comp = rec["results"]
            self.assertEqual(comp["comparison_type"], "job_benchmark")
            self.assertEqual(comp["job_id"], "JOB_032")
            self.assertEqual(comp["title"], "Backend Developer")
            self.assertIn("match_pct", comp)
            self.assertIn("matched_skills", comp)
            self.assertIn("missing_skills", comp)
            self.assertIn("learning_recommendations", comp)
            self.assertIn("improvement_suggestions", comp)

            # Results page must render dedicated job match analysis (A, B, C, D, E)
            res_page = self.client.get(f"/jobs/compare/results/{analysis_id}")
            self.assertEqual(res_page.status_code, 200)
            self.assertIn(b"Job Match Analysis", res_page.data)
            self.assertIn(b"JOB_032", res_page.data)
            self.assertIn(b"Backend Developer", res_page.data)
            self.assertIn(b"Skills You Already Have", res_page.data)
            self.assertIn(b"Missing Skills", res_page.data)
            self.assertIn(b"Where to Learn Your Missing Skills", res_page.data)
            self.assertIn(b"Improvement Suggestions", res_page.data)

            # Must NOT recommend top 5 roles in Feature 2
            self.assertNotIn(b"Top 5 Role Matches", res_page.data)
        finally:
            self.client.post(f"/delete/{analysis_id}")
            self.assertIsNone(get_analysis(analysis_id))

    def test_08_missing_skill_explanations_and_roadmap_stages(self):
        """Missing skills include beginner-friendly what_it_is + role-specific why_important and normalized roadmap statuses."""
        role_info = get_role_info("Backend Developer")
        self.assertIsNotNone(role_info)

        checklist = learning_checklist(
            ["Docker", "PostgreSQL"],
            role_title="Backend Developer",
            role_info=role_info,
        )
        self.assertEqual(len(checklist), 2)
        for item in checklist:
            self.assertTrue(item.get("what_it_is"), f"Missing what_it_is for {item['skill']}")
            self.assertTrue(item.get("why_important"), f"Missing why_important for {item['skill']}")
            self.assertIn("Backend Developer", item["why_important"])
            self.assertGreaterEqual(len(item["resources"]), 2)

        roadmap = generate_career_roadmap(
            "Backend Developer",
            detected_skills=["Python", "SQL", "Git"],
            detected_soft_skills=["Problem Solving"],
        )
        self.assertGreaterEqual(len(roadmap["stages"]), 3)
        self.assertTrue(roadmap["recommended_next_stage"].startswith("Stage "))
        for stage in roadmap["stages"]:
            self.assertIn(stage["stage_status"], {"Completed", "In Progress", "Upcoming"})
            for sk in stage["skills"]:
                self.assertTrue(sk.get("what_it_is"))
                self.assertTrue(sk.get("why_important"))

    def test_09_target_role_career_readiness_independent_of_job_recommendation(self):
        """Feature 1: General Job Recommendations runs independently without target role selection."""
        sample_pdf = SAMPLE_RESUMES_DIR / "fresher_python.pdf"
        with open(sample_pdf, "rb") as f:
            pdf_bytes = f.read()

        # Feature 1 workflow: upload resume directly on Analyze Resume
        resp = self.client.post(
            "/analyze",
            data={
                "resume": (io.BytesIO(pdf_bytes), "fresher_python.pdf"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 302)
        auto_id = int(resp.headers["Location"].split("/results/")[-1])

        try:
            rec_auto = get_analysis(auto_id)
            self.assertEqual(rec_auto["target_role"], "Best fit across all roles")
            top_roles = rec_auto["results"]["top_roles"]
            self.assertGreaterEqual(len(top_roles), 3)

            res_auto = self.client.get(f"/results/{auto_id}")
            self.assertEqual(res_auto.status_code, 200)
            self.assertIn(b"Best Immediate Match", res_auto.data)
            self.assertIn(b"Top 5 Role Matches", res_auto.data)
            self.assertIn(b"Career Fit Explorer", res_auto.data)
            self.assertIn(b"Skills Found in Your Resume", res_auto.data)
        finally:
            self.client.post(f"/delete/{auto_id}")
            self.assertIsNone(get_analysis(auto_id))


if __name__ == "__main__":
    unittest.main()
