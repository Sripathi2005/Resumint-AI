"""
Offline ETL script to clean, filter, and integrate relevant Kaggle datasets
from `resume datasets/` into the AI Resume Analyzer application data files:
  - data/skills.json        (expanded IT/Data/Mobile/Security/Design taxonomy)
  - data/soft_skills.json   (curated soft skills from skills_database.json & job_roles.csv)
  - data/jobs.csv           (cleaned, deduplicated, role-balanced job benchmarks)
  - data/job_roles_info.json (beginner-friendly career info & sequential roadmaps)

Excluded by design:
  - resume datasets/training_data.csv (verified synthetic cross-domain label noise)
  - resume datasets/test_resumes.json (synthetic QA fixtures)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from modules.skill_extractor import extract_skills, load_skills  # noqa: E402
from modules.job_matcher import validate_jobs_skills  # noqa: E402

KAGGLE_DIR = ROOT_DIR / "resume datasets"
DATA_DIR = ROOT_DIR / "data"


# ---------------------------------------------------------------------------
# 1. Taxonomy Expansion (skills.json + soft_skills.json)
# ---------------------------------------------------------------------------

EXTRA_TECH_SKILLS = [
    {"name": "Objective-C", "category": "languages", "aliases": ["objective-c", "objective c", "objc"]},
    {"name": "NoSQL", "category": "databases", "aliases": ["nosql", "no-sql"]},
    {"name": "Tableau", "category": "AI/ML", "aliases": ["tableau", "tableau desktop", "tableau server"]},
    {"name": "Power BI", "category": "AI/ML", "aliases": ["power bi", "powerbi", "microsoft power bi"]},
    {"name": "Microsoft Excel", "category": "tools", "aliases": ["microsoft excel", "ms excel", "excel"]},
    {"name": "Data Analysis", "category": "AI/ML", "aliases": ["data analysis", "data analytics", "exploratory data analysis"]},
    {"name": "Statistics", "category": "AI/ML", "aliases": ["statistics", "statistical analysis", "probability and statistics"]},
    {"name": "Hadoop", "category": "tools", "aliases": ["hadoop", "apache hadoop", "hdfs"]},
    {"name": "Apache Spark", "category": "AI/ML", "aliases": ["apache spark", "spark", "pyspark"]},
    {"name": "ETL", "category": "tools", "aliases": ["etl", "etl pipelines", "extract transform load"]},
    {"name": "Data Warehousing", "category": "databases", "aliases": ["data warehousing", "data warehouse", "dimensional modeling"]},
    {"name": "Data Modeling", "category": "databases", "aliases": ["data modeling", "data modelling", "er modeling"]},
    {"name": "dbt", "category": "tools", "aliases": ["dbt", "data build tool"]},
    {"name": "Android", "category": "frameworks", "aliases": ["android", "android app development"]},
    {"name": "Android SDK", "category": "tools", "aliases": ["android sdk", "android studio", "jetpack compose"]},
    {"name": "iOS", "category": "frameworks", "aliases": ["ios", "ios development", "apple ios"]},
    {"name": "SwiftUI", "category": "frameworks", "aliases": ["swiftui", "swift ui"]},
    {"name": "Xcode", "category": "tools", "aliases": ["xcode"]},
    {"name": "Selenium", "category": "tools", "aliases": ["selenium", "selenium webdriver"]},
    {"name": "Playwright", "category": "tools", "aliases": ["playwright"]},
    {"name": "Cypress", "category": "tools", "aliases": ["cypress", "cypress.io"]},
    {"name": "JUnit", "category": "tools", "aliases": ["junit", "junit5"]},
    {"name": "Unit Testing", "category": "tools", "aliases": ["unit testing", "unit tests"]},
    {"name": "Test Automation", "category": "tools", "aliases": ["test automation", "automated testing", "qa automation"]},
    {"name": "Manual Testing", "category": "tools", "aliases": ["manual testing", "functional testing", "regression testing"]},
    {"name": "Figma", "category": "web", "aliases": ["figma"]},
    {"name": "WordPress", "category": "web", "aliases": ["wordpress", "wp"]},
    {"name": "Wireframing", "category": "web", "aliases": ["wireframing", "wireframes"]},
    {"name": "Prototyping", "category": "web", "aliases": ["prototyping", "interactive prototypes"]},
    {"name": "UI/UX Design", "category": "web", "aliases": ["ui/ux", "ui/ux design", "ux design", "ui design", "user experience"]},
    {"name": "Design Systems", "category": "web", "aliases": ["design systems", "component library"]},
    {"name": "User Research", "category": "web", "aliases": ["user research", "usability testing"]},
    {"name": "Cybersecurity", "category": "tools", "aliases": ["cybersecurity", "cyber security", "information security"]},
    {"name": "Penetration Testing", "category": "tools", "aliases": ["penetration testing", "pentesting", "ethical hacking"]},
    {"name": "Network Security", "category": "tools", "aliases": ["network security", "vpn", "zero trust"]},
    {"name": "Encryption", "category": "tools", "aliases": ["encryption", "cryptography", "tls/ssl"]},
    {"name": "Firewalls", "category": "tools", "aliases": ["firewalls", "firewall", "waf"]},
    {"name": "SIEM", "category": "tools", "aliases": ["siem", "security information and event management"]},
    {"name": "Risk Assessment", "category": "tools", "aliases": ["risk assessment", "risk analysis", "risk management"]},
    {"name": "Vulnerability Assessment", "category": "tools", "aliases": ["vulnerability assessment", "vulnerability scanning"]},
    {"name": "TCP/IP", "category": "tools", "aliases": ["tcp/ip", "dns", "dhcp", "http/https"]},
    {"name": "Cisco", "category": "tools", "aliases": ["cisco", "ccna", "routing and switching"]},
    {"name": "Networking", "category": "tools", "aliases": ["networking", "computer networks", "lan/wan"]},
    {"name": "Agile", "category": "tools", "aliases": ["agile", "agile methodology"]},
    {"name": "Scrum", "category": "tools", "aliases": ["scrum"]},
    {"name": "System Design", "category": "frameworks", "aliases": ["system design", "software architecture", "distributed systems"]},
    {"name": "Pytest", "category": "tools", "aliases": ["pytest"]},
    {"name": "Jest", "category": "tools", "aliases": ["jest"]},
    {"name": "Redux", "category": "frameworks", "aliases": ["redux", "redux toolkit"]},
    {"name": "Confluence", "category": "tools", "aliases": ["confluence"]},
    {"name": "Jupyter", "category": "tools", "aliases": ["jupyter", "jupyter notebook", "jupyterlab"]},
    {"name": "Embedded Linux", "category": "embedded", "aliases": ["embedded linux", "yocto"]},
    {"name": "CAN Bus", "category": "embedded", "aliases": ["can bus", "controller area network"]},
    {"name": "MQTT", "category": "embedded", "aliases": ["mqtt"]},
    {"name": "Hibernate", "category": "frameworks", "aliases": ["hibernate", "jpa hibernate"]},
    {"name": "Data Visualization", "category": "AI/ML", "aliases": ["data visualization", "data viz"]},
]


def update_skills_taxonomy() -> Dict[str, str]:
    """Update data/skills.json with clean Kaggle technical skills and generate data/soft_skills.json."""
    skills_path = DATA_DIR / "skills.json"
    with open(skills_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    skills_list = data.get("skills", [])
    by_name = {s["name"].lower(): s for s in skills_list}

    # Fix overly broad aliases identified during Kaggle inspection
    if "next.js" in by_name:
        by_name["next.js"]["aliases"] = [a for a in by_name["next.js"]["aliases"] if a.lower() != "next"]
    if "computer vision" in by_name:
        by_name["computer vision"]["aliases"] = [a for a in by_name["computer vision"]["aliases"] if a.lower() != "cv"]

    added = 0
    for entry in EXTRA_TECH_SKILLS:
        key = entry["name"].lower()
        if key not in by_name:
            skills_list.append(entry)
            by_name[key] = entry
            added += 1

    data["skills"] = skills_list
    with open(skills_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Build soft_skills.json from Kaggle skills_database.json ("Soft Skills") + job_roles.csv
    soft_db_path = KAGGLE_DIR / "skills_database.json"
    soft_names: List[str] = []
    if soft_db_path.is_file():
        with open(soft_db_path, "r", encoding="utf-8") as f:
            sdb = json.load(f)
        soft_names.extend(sdb.get("Soft Skills", []))

    extra_soft = [
        "Communication",
        "Problem Solving",
        "Teamwork",
        "Collaboration",
        "Analytical Thinking",
        "Attention to Detail",
        "Leadership",
        "Time Management",
        "Critical Thinking",
        "Adaptability",
        "Project Management",
        "Presentation",
        "Troubleshooting",
        "Mentoring",
    ]
    seen_soft = set()
    soft_entries = []
    alias_overrides = {
        "Communication": ["communication", "written communication", "verbal communication"],
        "Problem Solving": ["problem solving", "problem-solving"],
        "Teamwork": ["teamwork", "team player", "team collaboration"],
        "Collaboration": ["collaboration", "cross-functional collaboration"],
        "Analytical Thinking": ["analytical thinking", "analytical skills", "analytical mindset"],
        "Attention to Detail": ["attention to detail", "detail-oriented", "detail oriented"],
        "Leadership": ["leadership", "team lead", "technical leadership"],
        "Time Management": ["time management", "prioritization"],
        "Critical Thinking": ["critical thinking"],
        "Adaptability": ["adaptability", "fast learner"],
        "Project Management": ["project management", "stakeholder management"],
        "Presentation": ["presentation", "data storytelling", "storytelling"],
        "Troubleshooting": ["troubleshooting", "root cause analysis"],
        "Mentoring": ["mentoring", "coaching", "code reviews"],
    }
    for name in extra_soft + soft_names:
        clean_name = name.strip()
        if clean_name and clean_name.lower() not in seen_soft:
            seen_soft.add(clean_name.lower())
            soft_entries.append({
                "name": clean_name,
                "category": "Soft Skills",
                "aliases": alias_overrides.get(clean_name, [clean_name.lower()]),
            })

    with open(DATA_DIR / "soft_skills.json", "w", encoding="utf-8") as f:
        json.dump({"skills": soft_entries}, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"[skills.json] Total={len(skills_list)} (added {added}), [soft_skills.json] Total={len(soft_entries)}")
    return load_skills(skills_path)


# ---------------------------------------------------------------------------
# 2. Text Cleaning Utilities for Kaggle Postings
# ---------------------------------------------------------------------------

NOISE_LINE_PATTERNS = [
    r"(?i)job\s*types?\s*:",
    r"(?i)salary\s*:",
    r"(?i)schedule\s*:",
    r"(?i)experience\s*:\s*total work",
    r"(?i)speak with the employer",
    r"(?i)covid-?19",
    r"(?i)benefits\s*:",
    r"(?i)supplemental pay",
    r"(?i)ability to commute",
    r"(?i)education\s*:\s*bachelor",
    r"[₹$]\s?\d[\d,\.\-–kKlL ]*",
    r"\+?\d[\d\-\s]{8,}\d",
    r"https?://\S+",
    r"\S+@\S+",
]


def clean_kaggle_posting(raw: str, max_len: int = 520) -> str:
    """Clean raw Kaggle job posting text into crisp, readable benchmark descriptions."""
    if not isinstance(raw, str):
        return ""
    text = raw.replace("<br>", ". ").replace("<br/>", ". ").replace("•", " ")
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if any(re.search(pat, s) for pat in NOISE_LINE_PATTERNS):
            continue
        lines.append(s)

    joined = " ".join(lines)
    # Strip boilerplate leading labels
    joined = re.sub(r"^(?:job description|description|about the role|position summary)\s*[:\-–]*\s*", "", joined, flags=re.IGNORECASE)
    joined = re.sub(r"\s+", " ", joined).strip()
    # Fix missing capitalization after sentence start if lowercased (like data.csv)
    if joined and joined[0].islower():
        joined = joined[0].upper() + joined[1:]

    if len(joined) > max_len:
        cut = joined[:max_len]
        last_period = max(cut.rfind(". "), cut.rfind("; "))
        if last_period >= 180:
            joined = cut[: last_period + 1].strip()
        else:
            joined = cut.rsplit(" ", 1)[0].strip() + "."
    if joined and joined[-1] not in ".!?":
        joined += "."
    return joined


def is_clean_english_posting(raw: str) -> bool:
    """Filter out sparse, salary-spam, or garbled Kaggle postings."""
    if not isinstance(raw, str) or len(raw.strip()) < 180:
        return False
    bad_markers = ["₹", "per month", "per year", "+91", "walk-in", "urgent hiring"]
    lower = raw.lower()
    if sum(m in lower for m in bad_markers) >= 2:
        return False
    # Check reasonable ratio of ASCII letters
    alpha = sum(c.isalpha() for c in raw)
    return alpha / max(len(raw), 1) >= 0.55


# ---------------------------------------------------------------------------
# 3. Kaggle Job Benchmark Extraction & Curation (data/jobs.csv)
# ---------------------------------------------------------------------------

def build_jobs_dataset(skill_lookup: Dict[str, str]) -> pd.DataFrame:
    """
    Build clean, role-balanced data/jobs.csv integrating:
      - resume datasets/job_title_des.csv
      - resume datasets/data.csv
      - resume datasets/job_description.csv
      - resume datasets/job_roles.csv
      - resume datasets/resume_data.csv
    Maintains compatibility with existing 12 benchmark roles (JOB_001..JOB_084)
    and adds 9 additional real-world IT roles from Kaggle (JOB_085..JOB_147).
    """
    valid_skills = set(skill_lookup.values())

    jtd_df = pd.read_csv(KAGGLE_DIR / "job_title_des.csv")
    data_df = pd.read_csv(KAGGLE_DIR / "data.csv")
    jd_df = pd.read_csv(KAGGLE_DIR / "job_description.csv")
    jr_df = pd.read_csv(KAGGLE_DIR / "job_roles.csv")
    rd_df = pd.read_csv(KAGGLE_DIR / "resume_data.csv", encoding="utf-8")
    rd_df.columns = [c.lstrip("\ufeff") for c in rd_df.columns]

    def sample_kaggle_jtd(
        kaggle_titles: List[str],
        domain_must_have: set,
        allowed_skills: Optional[set] = None,
        n: int = 4,
    ) -> List[Tuple[str, List[str], List[str], str]]:
        """Extract cleanest postings from job_title_des.csv matching domain skills."""
        sub = jtd_df[jtd_df["Job Title"].isin(kaggle_titles)]
        candidates = []
        seen_prefixes = set()
        for _, row in sub.iterrows():
            raw = str(row.get("Job Description", ""))
            if not is_clean_english_posting(raw):
                continue
            cleaned = clean_kaggle_posting(raw, max_len=650)
            if len(cleaned) < 150:
                continue
            prefix = cleaned[:80].lower()
            if prefix in seen_prefixes:
                continue
            detected_full = extract_skills(cleaned, skill_lookup=skill_lookup, raw_text=cleaned)
            if not (set(detected_full) & domain_must_have):
                continue
            if allowed_skills is not None:
                pool = [s for s in detected_full if s in allowed_skills]
            else:
                pool = detected_full
            if len(pool) < 5:
                continue
            pool.sort(key=lambda s: (0 if s in domain_must_have else 1, s))
            seen_prefixes.add(prefix)
            # Score richness based on overlap with domain_must_have + clean prose
            richness = len(set(pool) & domain_must_have) * 3 + min(len(pool), 8)
            req = pool[:5]
            pref = pool[5:9]
            candidates.append((richness, cleaned, req, pref, "Kaggle job_title_des.csv"))
            if len(candidates) >= max(n * 5, 18):
                break

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [(c[1], c[2], c[3], c[4]) for c in candidates[:n]]

    def sample_kaggle_data_csv(
        title_pattern: str,
        domain_must_have: set,
        allowed_skills: set,
        n: int = 4,
    ) -> List[Tuple[str, List[str], List[str], str]]:
        """Extract clean analyst postings from data.csv."""
        sub = data_df[data_df["Job Title"].str.contains(title_pattern, case=False, na=False)]
        candidates = []
        seen_prefixes = set()
        for _, row in sub.iterrows():
            raw = str(row.get("Description", ""))
            if len(raw.strip()) < 200:
                continue
            cleaned = clean_kaggle_posting(raw, max_len=650)
            prefix = cleaned[:80].lower()
            if prefix in seen_prefixes:
                continue
            detected_full = extract_skills(cleaned, skill_lookup=skill_lookup, raw_text=cleaned)
            pool = [s for s in detected_full if s in allowed_skills]
            if not (set(pool) & domain_must_have) or len(pool) < 5:
                continue
            pool.sort(key=lambda s: (0 if s in domain_must_have else 1, s))
            seen_prefixes.add(prefix)
            richness = len(set(pool) & domain_must_have) * 3 + min(len(pool), 8)
            candidates.append((richness, cleaned, pool[:5], pool[5:9], "Kaggle data.csv"))
            if len(candidates) >= max(n * 5, 18):
                break
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [(c[1], c[2], c[3], c[4]) for c in candidates[:n]]

    def get_jd_text(jd_title: str) -> str:
        """Build clean composite summary from job_description.csv."""
        sub = jd_df[jd_df["Job Title"] == jd_title]
        if sub.empty:
            return ""
        r = sub.iloc[0]
        desc = clean_kaggle_posting(str(r.get("Job Description", "")), max_len=240)
        resp = clean_kaggle_posting(str(r.get("Key Responsibilities", "")), max_len=260)
        return f"{desc} Key responsibilities: {resp}".strip()

    # Helper to construct deterministic validated records
    # Note: Every required/preferred skill list below is grounded in the Kaggle datasets
    # (job_title_des.csv, data.csv, job_roles.csv, job_description.csv, resume_data.csv)
    # and strictly validated against data/skills.json.

    role_blueprints = [
        # ---- 12 Core Benchmark Roles (JOB_001 .. JOB_084) ----
        {
            "title": "Python Developer",
            "category": "Software Engineering",
            "kaggle_jtd": (["Django Developer"], {"Python", "Django", "Flask", "FastAPI"}, {"Python", "Django", "Flask", "FastAPI", "PostgreSQL", "MySQL", "SQL", "Docker", "Git", "REST API", "Linux", "Redis", "Pytest"}),
            "curated_kaggle": [
                ("Entry-level", "Build scalable Python web backends, SQLite/PostgreSQL database applications, HTML templates, and automated scripts using Python, SQL, Git, and Flask or Django.", ["Python", "SQL", "Git", "HTML5", "CSS3"], ["Flask", "Django", "Docker", "Pytest"], "Kaggle job_roles.csv + job_title_des.csv"),
                ("Junior", "Develop Python microservices and automated workflows with FastAPI, Flask, PostgreSQL, Redis, Linux scripting, and CI/CD pipelines.", ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"], ["Flask", "Redis", "Linux", "CI/CD"], "Kaggle job_title_des.csv"),
                ("Mid-level", "Architect backend web services with Python, Django REST Framework, MySQL, asynchronous task queues, and automated Pytest suites.", ["Python", "Django", "Flask", "MySQL", "REST API", "Pytest"], ["AWS", "Docker", "Git", "Redis"], "Kaggle job_title_des.csv + job_roles.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Junior", "Mid-level", "Entry-level", "Mid-level", "Junior"],
        },
        {
            "title": "Java Developer",
            "category": "Software Engineering",
            "kaggle_jtd": (["Java Developer"], {"Java", "Spring Boot", "Spring Framework"}, {"Java", "Spring Boot", "Spring Framework", "Hibernate", "SQL", "MySQL", "PostgreSQL", "Maven", "Gradle", "Docker", "Git", "REST API", "Microservices", "JUnit", "Apache Kafka"}),
            "curated_kaggle": [
                ("Entry-level", "Design and maintain enterprise Java backend applications using Spring Boot, Hibernate ORM, SQL databases, Maven, and JUnit.", ["Java", "Spring Boot", "SQL", "Maven", "Git"], ["Hibernate", "JUnit", "Docker"], "Kaggle job_roles.csv (Java Backend Developer)"),
                ("Junior", "Build resilient REST APIs and microservices in Java and Spring Framework integrating PostgreSQL, Docker containers, and CI/CD.", ["Java", "Spring Framework", "Spring Boot", "REST API", "PostgreSQL"], ["Microservices", "Docker", "Apache Kafka"], "Kaggle job_title_des.csv + job_roles.csv"),
                ("Mid-level", "Develop high-throughput Java server systems with Spring Boot, Microservices architecture, Apache Kafka messaging, MySQL, and Gradle.", ["Java", "Spring Boot", "Microservices", "SQL", "Apache Kafka", "Docker"], ["Gradle", "JUnit", "Kubernetes"], "Kaggle job_roles.csv + job_title_des.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Entry-level", "Mid-level", "Junior"],
        },
        {
            "title": "Full Stack Developer",
            "category": "Web Development",
            "kaggle_jtd": (["Full Stack Developer"], {"JavaScript", "React", "Node.js", "Python", "Django", "Angular"}, {"JavaScript", "TypeScript", "React", "Angular", "Node.js", "Express.js", "Python", "Django", "HTML5", "CSS3", "SQL", "PostgreSQL", "MongoDB", "MySQL", "REST API", "Git", "Docker", "AWS"}),
            "curated_kaggle": [
                ("Entry-level", get_jd_text("Full-Stack Engineer") or "Design end-to-end web applications combining React interfaces with Python Django or Node.js REST APIs and SQL databases.", ["JavaScript", "React", "Node.js", "HTML5", "CSS3", "SQL"], ["Git", "REST API", "PostgreSQL"], "Kaggle job_description.csv + job_roles.csv"),
                ("Junior", "Develop full-stack features using React, TypeScript, Python Django REST Framework, PostgreSQL, Docker, and Git workflows.", ["React", "Python", "Django", "PostgreSQL", "REST API", "Git"], ["TypeScript", "Docker", "AWS"], "Kaggle resume_data.csv + job_roles.csv"),
                ("Mid-level", "Architect modern JavaScript and TypeScript full-stack applications using Next.js, Node.js, Express.js, MongoDB, and CI/CD.", ["JavaScript", "TypeScript", "React", "Node.js", "Express.js", "MongoDB"], ["Next.js", "Docker", "AWS", "CI/CD"], "Kaggle job_title_des.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Entry-level", "Mid-level", "Junior"],
        },
        {
            "title": "Frontend Developer",
            "category": "Web Development",
            "kaggle_jtd": (["JavaScript Developer"], {"JavaScript", "React", "Angular", "Vue.js", "HTML5", "CSS3"}, {"JavaScript", "TypeScript", "React", "Angular", "Vue.js", "Next.js", "HTML5", "CSS3", "Tailwind CSS", "Redux", "Responsive Design", "REST API", "Git", "Figma", "Jest"}),
            "curated_kaggle": [
                ("Entry-level", get_jd_text("Frontend Engineer") or "Build responsive browser interfaces with HTML5, CSS3, modern JavaScript, React, and REST API integration.", ["JavaScript", "HTML5", "CSS3", "React", "Git"], ["Responsive Design", "Tailwind CSS", "Figma"], "Kaggle job_description.csv + job_roles.csv"),
                ("Junior", "Create reusable single-page application components with React, TypeScript, Redux state management, Tailwind CSS, and Jest testing.", ["React", "TypeScript", "JavaScript", "HTML5", "CSS3", "Redux"], ["Jest", "Next.js", "Figma"], "Kaggle job_roles.csv (React Developer)"),
                ("Mid-level", "Lead client-side architecture using TypeScript, Angular or Vue.js, performance optimization, Responsive Design, and unit testing.", ["JavaScript", "TypeScript", "Angular", "HTML5", "CSS3", "Responsive Design"], ["Vue.js", "Jest", "Git"], "Kaggle job_title_des.csv + job_roles.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Junior", "Mid-level", "Entry-level", "Mid-level", "Junior"],
        },
        {
            "title": "Backend Developer",
            "category": "Software Engineering",
            "kaggle_jtd": (["Backend Developer", "Node js developer"], {"Node.js", "Express.js", "Python", "Java", "Go", "REST API"}, {"Node.js", "Express.js", "Python", "Django", "FastAPI", "Java", "Go", "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQL", "REST API", "GraphQL", "Docker", "Microservices", "Git", "AWS"}),
            "curated_kaggle": [
                ("Entry-level", get_jd_text("Backend Engineer") or "Develop server-side logic, relational databases, and scalable REST APIs using Node.js, Python, and SQL.", ["Node.js", "Python", "SQL", "REST API", "Git"], ["Express.js", "PostgreSQL", "Docker"], "Kaggle job_description.csv + job_roles.csv"),
                ("Junior", "Engineer Node.js and Express.js backend APIs backed by MongoDB, PostgreSQL, Redis caching, and JWT authentication.", ["Node.js", "Express.js", "JavaScript", "MongoDB", "REST API"], ["Redis", "PostgreSQL", "Docker"], "Kaggle job_title_des.csv (Node js developer)"),
                ("Mid-level", "Build distributed backend microservices in Go, Python FastAPI, PostgreSQL, GraphQL, Docker, and Kubernetes.", ["Go", "Python", "PostgreSQL", "Microservices", "Docker", "REST API"], ["FastAPI", "GraphQL", "Redis", "Kubernetes"], "Kaggle job_roles.csv + job_title_des.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Entry-level", "Mid-level", "Junior"],
        },
        {
            "title": "Data Analyst",
            "category": "Data & Analytics",
            "kaggle_data_csv": ("Data Analyst", {"Tableau", "Power BI", "Data Analysis", "Microsoft Excel", "Statistics"}, {"SQL", "Python", "Pandas", "NumPy", "Matplotlib", "Seaborn", "Tableau", "Power BI", "Microsoft Excel", "Data Analysis", "Statistics", "ETL", "Data Modeling", "Snowflake", "Google BigQuery", "Data Visualization", "PostgreSQL", "MySQL"}),
            "curated_kaggle": [
                ("Entry-level", get_jd_text("Data & Analytics Consultant") or "Clean business datasets, write SQL queries, and create interactive Tableau and Power BI KPI dashboards.", ["SQL", "Microsoft Excel", "Tableau", "Power BI", "Data Analysis"], ["Python", "Statistics", "Data Visualization"], "Kaggle job_description.csv + data.csv"),
                ("Junior", "Analyze business datasets and uncover trends using SQL, Python Pandas, NumPy, Matplotlib, Seaborn, and Statistics.", ["SQL", "Python", "Pandas", "NumPy", "Statistics", "Matplotlib"], ["Seaborn", "Data Analysis", "Data Visualization"], "Kaggle data.csv + job_roles.csv"),
                ("Junior", "Perform exploratory data analysis and stakeholder BI reporting with SQL, Python Pandas, Power BI, Statistics, and Microsoft Excel.", ["SQL", "Python", "Pandas", "Data Analysis", "Power BI", "Microsoft Excel"], ["Tableau", "Matplotlib", "Data Visualization"], "Kaggle data.csv + job_roles.csv"),
                ("Mid-level", "Build automated analytics reporting with Google BigQuery, Snowflake, SQL data modeling, dbt, Tableau, and Python.", ["SQL", "Python", "Tableau", "Google BigQuery", "Data Modeling", "ETL"], ["Snowflake", "dbt", "Power BI"], "Kaggle data.csv + resume_data.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Junior", "Mid-level", "Entry-level", "Mid-level", "Junior"],
        },
        {
            "title": "Data Scientist",
            "category": "Data Science & AI",
            "kaggle_jtd": (["Machine Learning"], {"Machine Learning", "Python", "Scikit-Learn", "Pandas", "Statistics"}, {"Python", "R", "SQL", "Pandas", "NumPy", "Scikit-Learn", "Machine Learning", "Statistics", "Data Analysis", "Data Visualization", "Matplotlib", "Seaborn", "TensorFlow", "NLP", "Jupyter"}),
            "curated_kaggle": [
                ("Entry-level", "Perform exploratory data analysis, statistical hypothesis testing, and predictive modeling using Python, Machine Learning, Pandas, NumPy, SQL, and Scikit-Learn.", ["Python", "Machine Learning", "Scikit-Learn", "Pandas", "Statistics", "SQL"], ["NumPy", "Matplotlib", "Jupyter"], "Kaggle job_roles.csv (Data Scientist)"),
                ("Junior", "Build classification and regression models, engineer features, and communicate business insights via Python, Machine Learning, Scikit-Learn, R, and SQL.", ["Python", "Machine Learning", "Scikit-Learn", "Statistics", "SQL", "Data Analysis"], ["R", "Pandas", "Data Visualization"], "Kaggle job_roles.csv + resume_data.csv"),
                ("Mid-level", "Develop statistical and NLP forecasting systems using Python, Machine Learning, TensorFlow, PyTorch, Scikit-Learn, Apache Spark, and SQL.", ["Python", "Machine Learning", "Statistics", "Scikit-Learn", "TensorFlow", "SQL"], ["NLP", "Apache Spark", "PyTorch"], "Kaggle resume_data.csv (Data Science Engineer)"),
                ("Senior", "Lead end-to-end experimentation, causal inference, feature engineering, and production ML analytics pipelines across Python and BigQuery.", ["Python", "Machine Learning", "Statistics", "Pandas", "SQL", "Scikit-Learn"], ["TensorFlow", "Google BigQuery", "Data Visualization"], "Kaggle job_roles.csv + job_title_des.csv"),
                ("Junior", "Apply machine learning, feature selection, and visualization techniques in Python, Jupyter, Matplotlib, Seaborn, and Scikit-Learn.", ["Python", "Machine Learning", "Scikit-Learn", "Pandas", "NumPy", "Matplotlib"], ["Seaborn", "Statistics", "SQL"], "Kaggle job_roles.csv + job_title_des.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Entry-level", "Senior", "Mid-level"],
        },
        {
            "title": "ML Engineer",
            "category": "Data Science & AI",
            "kaggle_jtd": (["Machine Learning"], {"Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Python"}, {"Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Keras", "Scikit-Learn", "Computer Vision", "NLP", "Docker", "FastAPI", "AWS", "MLflow", "Kubernetes", "SQL"}),
            "curated_kaggle": [
                ("Entry-level", "Train and evaluate supervised and deep learning models using Python, Scikit-Learn, PyTorch, TensorFlow, and Docker APIs.", ["Python", "Machine Learning", "PyTorch", "TensorFlow", "Scikit-Learn"], ["Deep Learning", "Docker", "SQL"], "Kaggle job_roles.csv + resume_data.csv"),
                ("Junior", "Build production machine learning inference services with Python, PyTorch, Keras, FastAPI, Docker, and cloud deployment.", ["Python", "Deep Learning", "PyTorch", "TensorFlow", "Docker", "FastAPI"], ["Keras", "MLflow", "AWS"], "Kaggle resume_data.csv (ML & AI Engineer)"),
                ("Mid-level", "Design scalable NLP and Computer Vision model training pipelines using PyTorch, Hugging Face, MLflow, Kubernetes, and AWS.", ["Python", "Deep Learning", "PyTorch", "Computer Vision", "NLP", "Docker"], ["Hugging Face", "MLflow", "Kubernetes"], "Kaggle resume_data.csv + job_roles.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Mid-level", "Entry-level", "Senior"],
        },
        {
            "title": "DevOps Engineer",
            "category": "Cloud & DevOps",
            "kaggle_jtd": (["DevOps Engineer"], {"Docker", "Kubernetes", "CI/CD", "AWS", "Linux", "Terraform", "Jenkins"}, {"Docker", "Kubernetes", "CI/CD", "AWS", "Linux", "Terraform", "Ansible", "Jenkins", "GitHub Actions", "Bash", "Python", "Git", "Prometheus", "Grafana", "Microsoft Azure"}),
            "curated_kaggle": [
                ("Entry-level", get_jd_text("DevOps Engineer") or "Automate build, test, and deployment pipelines with Linux, Git, Docker, CI/CD, AWS, and Bash scripting.", ["Linux", "Docker", "CI/CD", "AWS", "Git", "Bash"], ["Python", "Jenkins", "Terraform"], "Kaggle job_description.csv + job_roles.csv"),
                ("Junior", "Manage containerized microservices using Docker, Kubernetes, Terraform Infrastructure as Code, GitHub Actions, and Prometheus monitoring.", ["Docker", "Kubernetes", "Terraform", "CI/CD", "Linux"], ["GitHub Actions", "Prometheus", "Grafana"], "Kaggle resume_data.csv + job_roles.csv"),
                ("Mid-level", "Architect resilient cloud delivery pipelines with AWS, Ansible, Terraform, Kubernetes, Jenkins, Python, and observability stacks.", ["AWS", "Kubernetes", "Docker", "Terraform", "Ansible", "CI/CD"], ["Jenkins", "Python", "Grafana"], "Kaggle job_title_des.csv + resume_data.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Mid-level", "Entry-level", "Senior"],
        },
        {
            "title": "Cloud Engineer",
            "category": "Cloud & DevOps",
            "curated_kaggle": [
                ("Entry-level", get_jd_text("Cloud Engineer") or "Deploy and manage cloud virtual networks, storage, compute instances, and IAM security across AWS, Azure, or GCP.", ["AWS", "Linux", "Docker", "Git", "System Design"], ["Microsoft Azure", "Terraform", "Networking"], "Kaggle job_description.csv (Cloud Engineer)"),
                ("Junior", "Provision scalable cloud environments with AWS, Microsoft Azure, Terraform, Docker, Kubernetes, and Bash automation.", ["AWS", "Microsoft Azure", "Terraform", "Docker", "Linux"], ["Kubernetes", "Bash", "CI/CD"], "Kaggle job_description.csv + job_roles.csv"),
                ("Mid-level", "Design fault-tolerant multi-region architectures on Google Cloud Platform and AWS using Terraform, Kubernetes, and Network Security.", ["AWS", "Google Cloud Platform", "Terraform", "Kubernetes", "Networking"], ["Network Security", "Docker", "Python"], "Kaggle job_roles.csv (Cloud Architect)"),
                ("Junior", "Migrate on-premise workloads to AWS and Azure, configuring Serverless compute, managed PostgreSQL, monitoring, and cost optimization.", ["AWS", "Microsoft Azure", "Linux", "Python", "SQL"], ["Docker", "Terraform", "Network Security"], "Kaggle job_description.csv (Cloud Implementation)"),
                ("Mid-level", "Manage cloud IAM, VPC routing, Firewalls, container orchestration on Kubernetes, and automated backups with Python and CI/CD.", ["AWS", "Kubernetes", "Linux", "Network Security", "CI/CD"], ["Firewalls", "Python", "Terraform"], "Kaggle job_description.csv + job_roles.csv"),
                ("Entry-level", "Support cloud operations using AWS core services, Linux administration, Docker containers, TCP/IP networking, and GitOps.", ["AWS", "Linux", "Docker", "TCP/IP", "Git"], ["Bash", "Python", "CI/CD"], "Kaggle job_roles.csv + job_description.csv"),
                ("Senior", "Architect enterprise hybrid cloud platforms spanning AWS, Azure, GCP, Terraform, Kubernetes, and zero-trust security controls.", ["AWS", "Microsoft Azure", "Google Cloud Platform", "Terraform", "Kubernetes", "System Design"], ["Cybersecurity", "CI/CD", "Ansible"], "Kaggle job_roles.csv (Cloud Architect)"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Mid-level", "Entry-level", "Senior"],
        },
        {
            "title": "Embedded Systems Engineer",
            "category": "Embedded & Hardware",
            "curated_kaggle": [
                ("Entry-level", get_jd_text("Embedded Software Engineer") or "Write low-level embedded C and C++ firmware for microcontrollers, sensors, and IoT hardware using Embedded Linux and RTOS.", ["C", "C++", "Embedded C", "Microcontrollers", "Embedded Linux"], ["Arduino", "STM32", "RTOS"], "Kaggle job_description.csv + job_roles.csv"),
                ("Junior", "Develop real-time microcontroller firmware in Embedded C and C++ with ARM Cortex, STM32, SPI/I2C/UART protocols, and FreeRTOS.", ["C", "C++", "Embedded C", "STM32", "RTOS"], ["ARM Architecture", "UART", "SPI", "I2C"], "Kaggle job_roles.csv (Embedded Systems Engineer)"),
                ("Mid-level", "Design Embedded Linux drivers, board bring-up, CAN bus automotive firmware, and hardware debugging using C, C++, and Python.", ["C", "C++", "Embedded Linux", "Linux", "RTOS"], ["CAN Bus", "Raspberry Pi", "Git"], "Kaggle job_description.csv (Firmware Engineer)"),
                ("Junior", "Program ESP32, Arduino, and STM32 IoT devices interfacing sensors over MQTT, I2C, SPI, and UART with low-power optimization.", ["Embedded C", "C", "ESP32", "Microcontrollers", "Arduino"], ["MQTT", "I2C", "SPI", "UART"], "Kaggle job_description.csv + job_roles.csv"),
                ("Mid-level", "Architect deterministic RTOS multitasking systems for industrial hardware with C++, ARM Architecture, Embedded Linux, and hardware-in-the-loop tests.", ["C++", "C", "RTOS", "ARM Architecture", "Embedded Linux"], ["Python", "Git", "Linux"], "Kaggle job_roles.csv + job_description.csv"),
                ("Entry-level", "Write and debug C/C++ firmware modules, read hardware schematics/datasheets, and validate UART/SPI interfaces on microcontrollers.", ["C", "C++", "Microcontrollers", "UART", "Git"], ["Arduino", "STM32", "Embedded C"], "Kaggle job_description.csv (Embedded Software Engineer)"),
                ("Senior", "Lead embedded architecture, Embedded Linux kernel customization, VHDL/FPGA co-design, real-time constraints, and firmware CI pipelines.", ["C", "C++", "Embedded Linux", "RTOS", "ARM Architecture", "Microcontrollers"], ["VHDL", "Linux", "Python"], "Kaggle job_description.csv (Hardware/Firmware)"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Mid-level", "Entry-level", "Senior"],
        },
        {
            "title": "QA/Test Engineer",
            "category": "Quality Assurance",
            "curated_kaggle": [
                ("Entry-level", get_jd_text("QA Automation Engineer") or "Write automated UI and API tests with Selenium, Python, SQL, Manual Testing, and Postman integrated into CI/CD pipelines.", ["Test Automation", "Selenium", "Manual Testing", "SQL", "Python"], ["Git", "REST API", "Postman", "Jira"], "Kaggle job_description.csv + job_roles.csv"),
                ("Junior", "Develop end-to-end browser and API automation frameworks using Playwright, Cypress, JavaScript, Postman API testing, and Git.", ["Test Automation", "Playwright", "Cypress", "JavaScript", "REST API", "Postman"], ["Git", "CI/CD", "Jira"], "Kaggle job_description.csv (QA Automation Engineer)"),
                ("Mid-level", "Architect scalable Java Selenium and Python Pytest API automation suites with Postman, Linux, Git, and Jira tracking.", ["Test Automation", "Python", "Pytest", "REST API", "Postman", "Git"], ["Selenium", "Linux", "Jira", "CI/CD"], "Kaggle job_roles.csv (Software Test Engineer)"),
                ("Junior", "Execute test plans, regression testing, API contract validation, SQL database checks, and automated Jest/Cypress test cases.", ["Manual Testing", "Test Automation", "Cypress", "SQL", "REST API"], ["Postman", "Jest", "Jira", "Git"], "Kaggle job_roles.csv + job_description.csv"),
                ("Mid-level", "Lead quality engineering strategy covering load testing, Playwright end-to-end automation, Docker test environments, and Agile QA.", ["Test Automation", "Playwright", "CI/CD", "Docker", "Agile"], ["Python", "JavaScript", "Unit Testing"], "Kaggle job_description.csv + job_roles.csv"),
                ("Entry-level", "Design structured test cases, log defect reports in Jira, validate web features via Manual Testing, and automate smoke checks in Selenium.", ["Manual Testing", "Selenium", "Jira", "SQL", "Git"], ["Python", "Unit Testing", "Postman"], "Kaggle job_roles.csv (QA Engineer)"),
                ("Senior", "Establish shift-left QA automation standards across Selenium, Playwright, Java JUnit, Python Pytest, REST APIs, and CI/CD gates.", ["Test Automation", "Selenium", "Playwright", "Pytest", "CI/CD", "REST API"], ["JUnit", "Docker", "Agile"], "Kaggle job_description.csv + job_roles.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Mid-level", "Entry-level", "Senior"],
        },
        # ---- 9 Additional Kaggle Tech Roles (JOB_085 .. JOB_147) ----
        {
            "title": "Software Engineer",
            "category": "Software Engineering",
            "kaggle_jtd": (["Software Engineer"], {"Java", "Python", "C++", "Git", "SQL", "System Design"}, {"Python", "Java", "C++", "JavaScript", "Git", "SQL", "REST API", "Docker", "Linux", "System Design", "Unit Testing", "Agile", "AWS"}),
            "curated_kaggle": [
                ("Entry-level", get_jd_text("Software Engineer") or "Design, develop, test, and maintain reliable software systems using Python, Java, C++, Git, SQL, and unit testing.", ["Python", "Java", "C++", "Git", "SQL", "Unit Testing"], ["REST API", "Agile", "Docker"], "Kaggle job_description.csv + job_roles.csv"),
                ("Junior", "Implement modular backend and application features in Java, Python, C++, REST APIs, and automated testing in Agile sprints.", ["Java", "Python", "C++", "REST API", "Git", "Unit Testing"], ["Linux", "Agile", "SQL"], "Kaggle job_roles.csv (Software Engineer)"),
                ("Mid-level", "Design scalable software architecture using System Design, Python, Java, PostgreSQL, Docker, and CI/CD engineering practices.", ["Python", "Java", "System Design", "SQL", "Docker", "Git"], ["AWS", "CI/CD", "Agile"], "Kaggle job_title_des.csv + job_description.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Entry-level", "Mid-level", "Senior"],
        },
        {
            "title": "Data Engineer",
            "category": "Data & Analytics",
            "curated_kaggle": [
                ("Entry-level", "Build reliable ETL pipelines, SQL data models, and cloud data warehouses using Python, SQL, Apache Spark, and Docker.", ["Python", "SQL", "ETL", "Data Warehousing", "Apache Spark"], ["Data Modeling", "Git", "Docker"], "Kaggle job_roles.csv (Data Engineer)"),
                ("Junior", "Develop batch and streaming data pipelines with Python, Apache Spark, Hadoop, SQL, and AWS or Azure cloud storage.", ["Python", "Apache Spark", "Hadoop", "SQL", "ETL"], ["AWS", "Microsoft Azure", "Data Modeling"], "Kaggle job_roles.csv + resume_data.csv"),
                ("Mid-level", "Design modern lakehouse analytics platforms using dbt, Snowflake, Apache Spark, Airflow-style ETL orchestration, and SQL optimization.", ["SQL", "Python", "Apache Spark", "ETL", "Data Warehousing", "dbt"], ["Snowflake", "Google BigQuery", "Docker"], "Kaggle resume_data.csv + job_roles.csv"),
                ("Junior", "Integrate relational and NoSQL data sources into Azure and BigQuery data warehouses using Python, ETL tools, and SQL.", ["Python", "SQL", "ETL", "Microsoft Azure", "Data Modeling"], ["Power BI", "Data Warehousing", "MongoDB"], "Kaggle resume_data.csv (Data Engineer)"),
                ("Mid-level", "Build event-driven data ingestion with Apache Kafka, Apache Spark, Python, PostgreSQL, Kubernetes, and automated data quality tests.", ["Python", "Apache Spark", "Apache Kafka", "SQL", "ETL"], ["PostgreSQL", "Docker", "AWS"], "Kaggle job_roles.csv + resume_data.csv"),
                ("Entry-level", "Transform raw CSV, JSON, and transactional records into clean analytical tables using Python, Pandas, SQL, and Data Modeling.", ["Python", "Pandas", "SQL", "ETL", "Data Modeling"], ["Data Warehousing", "Git", "Linux"], "Kaggle job_roles.csv"),
                ("Senior", "Architect enterprise data warehouse platforms spanning Snowflake, BigQuery, Apache Spark, dbt, Hadoop, and governance automation.", ["SQL", "Python", "Apache Spark", "Data Warehousing", "dbt", "Snowflake"], ["Google BigQuery", "Hadoop", "AWS"], "Kaggle job_roles.csv (Data Warehouse Architect)"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Mid-level", "Entry-level", "Senior"],
        },
        {
            "title": "Database Administrator",
            "category": "Databases & Infrastructure",
            "kaggle_jtd": (["Database Administrator"], {"SQL", "PostgreSQL", "MySQL", "Microsoft SQL Server", "Oracle Database", "Linux"}, {"SQL", "PostgreSQL", "MySQL", "Microsoft SQL Server", "Oracle Database", "MongoDB", "Redis", "NoSQL", "Linux", "AWS", "Data Modeling", "ETL"}),
            "curated_kaggle": [
                ("Entry-level", "Administer relational and NoSQL databases covering SQL query tuning, backups, replication, and security across MySQL, PostgreSQL, and MongoDB.", ["SQL", "MySQL", "PostgreSQL", "MongoDB", "Linux"], ["Microsoft SQL Server", "Data Modeling"], "Kaggle job_roles.csv + resume_data.csv"),
                ("Junior", "Manage high-availability SQL Server, Oracle Database, PostgreSQL, Redis, and Elasticsearch clusters including index rebuilding and recovery.", ["SQL", "Microsoft SQL Server", "Oracle Database", "Linux", "Redis"], ["Elasticsearch", "MongoDB", "ETL"], "Kaggle resume_data.csv (DBA)"),
                ("Mid-level", "Optimize enterprise database performance, schema design, partitioning, and cloud RDS migrations on AWS and PostgreSQL.", ["SQL", "PostgreSQL", "Microsoft SQL Server", "AWS", "Linux"], ["NoSQL", "Data Modeling", "Oracle Database"], "Kaggle job_title_des.csv + job_roles.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Entry-level", "Mid-level", "Senior"],
        },
        {
            "title": "Cybersecurity Analyst",
            "category": "Security & Networking",
            "curated_kaggle": [
                ("Entry-level", "Monitor security logs with SIEM tools, conduct vulnerability assessments, investigate alerts, and apply TCP/IP network security controls.", ["Cybersecurity", "Network Security", "SIEM", "Vulnerability Assessment", "Linux"], ["TCP/IP", "Firewalls", "Risk Assessment"], "Kaggle job_roles.csv (Cybersecurity/SOC Analyst)"),
                ("Junior", get_jd_text("Cybersecurity Engineer") or "Implement defense-in-depth controls, penetration testing, encryption, firewalls, and secure cloud configurations.", ["Cybersecurity", "Penetration Testing", "Network Security", "Encryption", "Firewalls"], ["Linux", "Python", "AWS"], "Kaggle job_description.csv + job_roles.csv"),
                ("Mid-level", "Conduct threat analysis, risk assessment, penetration testing, SIEM correlation, and Python security automation.", ["Cybersecurity", "Penetration Testing", "Risk Assessment", "SIEM", "Python"], ["Vulnerability Assessment", "Network Security", "Linux"], "Kaggle job_roles.csv (Cybersecurity Specialist)"),
                ("Junior", "Analyze firewall logs, harden Linux systems, verify TLS encryption, and remediate application vulnerabilities.", ["Cybersecurity", "Linux", "Firewalls", "Encryption", "Vulnerability Assessment"], ["TCP/IP", "Networking", "SQL"], "Kaggle job_roles.csv + job_description.csv"),
                ("Mid-level", "Perform cloud security architecture reviews, IAM hardening, incident response, SIEM detection engineering, and risk mitigation.", ["Cybersecurity", "Network Security", "AWS", "SIEM", "Risk Assessment"], ["Docker", "Kubernetes", "Python"], "Kaggle job_description.csv (Cybersecurity Risk)"),
                ("Entry-level", "Learn SOC triage, vulnerability scanning, TCP/IP packet inspection, Linux hardening, and core cybersecurity frameworks.", ["Cybersecurity", "TCP/IP", "Vulnerability Assessment", "Linux", "Networking"], ["Firewalls", "SIEM", "Python"], "Kaggle job_roles.csv (SOC Analyst)"),
                ("Senior", "Lead enterprise penetration testing, zero-trust network architecture, cryptography standards, and automated incident response.", ["Cybersecurity", "Penetration Testing", "Network Security", "Encryption", "Risk Assessment"], ["AWS", "SIEM", "Firewalls"], "Kaggle job_roles.csv + job_description.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Mid-level", "Entry-level", "Senior"],
        },
        {
            "title": "Mobile Developer",
            "category": "Mobile Development",
            "kaggle_jtd": (["Flutter Developer", "iOS Developer"], {"Flutter", "Dart", "Swift", "Kotlin", "Android", "iOS"}, {"Flutter", "Dart", "Swift", "SwiftUI", "Objective-C", "Kotlin", "Java", "Android", "Android SDK", "iOS", "Xcode", "React Native", "REST API", "Firebase Firestore", "Git"}),
            "curated_kaggle": [
                ("Entry-level", get_jd_text("Mobile Engineer (iOS/Android)") or "Build cross-platform and native mobile applications using Flutter, Dart, Swift or Kotlin, REST APIs, and Git.", ["Flutter", "Dart", "REST API", "Git", "iOS"], ["Android", "Firebase Firestore", "Swift"], "Kaggle job_description.csv + job_roles.csv"),
                ("Junior", "Develop native Android apps with Kotlin, Java, Android SDK, REST API integration, and local database persistence.", ["Kotlin", "Java", "Android", "Android SDK", "REST API"], ["Git", "Firebase Firestore", "Unit Testing"], "Kaggle job_roles.csv (Mobile Developer Android)"),
                ("Mid-level", "Engineer native iOS apps in Swift, SwiftUI, Objective-C, and Xcode with smooth UI animations and CI/CD deployment.", ["Swift", "SwiftUI", "iOS", "Xcode", "REST API"], ["Objective-C", "Git", "CI/CD"], "Kaggle resume_data.csv (Senior iOS Engineer)"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Entry-level", "Mid-level", "Senior"],
        },
        {
            "title": "UI/UX Designer",
            "category": "Design & Product",
            "curated_kaggle": [
                ("Entry-level", get_jd_text("UX Designer (User Experience)") or "Conduct user research, craft wireframes and interactive Figma prototypes, and run usability tests for intuitive digital products.", ["Figma", "UI/UX Design", "Wireframing", "Prototyping", "User Research"], ["Design Systems", "Responsive Design", "HTML5"], "Kaggle job_description.csv + job_roles.csv"),
                ("Junior", get_jd_text("UI Designer (User Interface)") or "Design pixel-perfect web and mobile interfaces, reusable Figma design systems, typography hierarchies, and responsive layouts.", ["Figma", "UI/UX Design", "Design Systems", "Prototyping", "Responsive Design"], ["Wireframing", "CSS3", "HTML5"], "Kaggle job_description.csv (UI Designer)"),
                ("Mid-level", "Translate user journeys and usability research into end-to-end Figma prototypes, component libraries, and accessible HTML5/CSS3 specs.", ["Figma", "UI/UX Design", "User Research", "Design Systems", "Wireframing"], ["Prototyping", "HTML5", "CSS3"], "Kaggle job_roles.csv (UX Designer)"),
                ("Junior", "Create low- and high-fidelity wireframes, interactive click-through prototypes in Figma, and responsive design handoffs for developers.", ["Figma", "Wireframing", "Prototyping", "UI/UX Design", "Responsive Design"], ["User Research", "Design Systems", "Agile"], "Kaggle job_roles.csv (UI Designer)"),
                ("Mid-level", "Lead product discovery interviews, usability studies, design systems governance in Figma, and cross-functional Agile sprints.", ["Figma", "User Research", "Design Systems", "UI/UX Design", "Agile"], ["Prototyping", "Wireframing", "Tailwind CSS"], "Kaggle job_description.csv (Product Designer)"),
                ("Entry-level", "Learn core UI/UX principles, user flows, Figma components, responsive grids, and basic HTML5/CSS3 collaboration.", ["Figma", "UI/UX Design", "Wireframing", "HTML5", "CSS3"], ["Prototyping", "Responsive Design", "User Research"], "Kaggle job_roles.csv + job_description.csv"),
                ("Senior", "Own cross-platform design systems, UX strategy, qualitative/quantitative user research, and design-engineering integration.", ["Figma", "UI/UX Design", "Design Systems", "User Research", "Prototyping"], ["Wireframing", "Responsive Design", "Agile"], "Kaggle job_description.csv + job_roles.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Mid-level", "Entry-level", "Senior"],
        },
        {
            "title": "Business Analyst",
            "category": "Data & Analytics",
            "kaggle_data_csv": ("Business Analyst", {"SQL", "Microsoft Excel", "Tableau", "Power BI", "Data Analysis"}, {"SQL", "Microsoft Excel", "Tableau", "Power BI", "Data Analysis", "Agile", "Scrum", "Jira", "Data Modeling", "Statistics", "Python", "Confluence"}),
            "curated_kaggle": [
                ("Entry-level", "Gather business requirements, write SQL queries, build Excel and Power BI reports, and collaborate in Agile/Scrum teams.", ["SQL", "Microsoft Excel", "Data Analysis", "Power BI", "Agile"], ["Jira", "Tableau", "Scrum"], "Kaggle job_roles.csv + data.csv"),
                ("Junior", "Translate stakeholder KPIs into functional specs, Jira user stories, SQL analytics, and interactive Tableau dashboards.", ["SQL", "Tableau", "Jira", "Data Analysis", "Microsoft Excel"], ["Power BI", "Agile", "Confluence"], "Kaggle data.csv + job_description.csv"),
                ("Mid-level", "Bridge business strategy and engineering teams using SQL data analysis, Data Modeling, Power BI, Agile Scrum, and ETL validation.", ["SQL", "Data Analysis", "Power BI", "Data Modeling", "Agile", "Scrum"], ["Python", "Tableau", "Jira"], "Kaggle data.csv + job_roles.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Entry-level", "Mid-level", "Senior"],
        },
        {
            "title": "Network Engineer",
            "category": "Security & Networking",
            "curated_kaggle": [
                ("Entry-level", get_jd_text("Network Engineer") or "Configure switches, routers, firewalls, and TCP/IP networks while troubleshooting LAN/WAN and Linux connectivity.", ["Networking", "TCP/IP", "Cisco", "Firewalls", "Linux"], ["Network Security", "Troubleshooting" if False else "AWS", "Bash"], "Kaggle job_description.csv + job_roles.csv"),
                ("Junior", "Maintain Cisco routing and switching, VLANs, VPN tunnels, firewall policies, and continuous network performance monitoring.", ["Cisco", "Networking", "TCP/IP", "Firewalls", "Network Security"], ["Linux", "Bash", "Python"], "Kaggle resume_data.csv + job_roles.csv"),
                ("Mid-level", "Design enterprise LAN/WAN and cloud VPC network architectures, automate Cisco configurations with Python, and harden perimeter firewalls.", ["Cisco", "Networking", "TCP/IP", "Network Security", "Python"], ["Firewalls", "AWS", "Linux"], "Kaggle job_roles.csv (Network Engineer)"),
                ("Junior", "Troubleshoot ISP/enterprise router configurations, DNS/DHCP services, BGP/OSPF routing, and Linux server networking.", ["Networking", "TCP/IP", "Linux", "Cisco", "Network Security"], ["Firewalls", "Bash", "AWS"], "Kaggle resume_data.csv (Network Support Engineer)"),
                ("Mid-level", "Implement hybrid cloud networking across AWS VPCs, on-premise Cisco hardware, zero-trust Firewalls, and SIEM telemetry.", ["Networking", "Network Security", "AWS", "Cisco", "Firewalls"], ["TCP/IP", "SIEM", "Linux"], "Kaggle job_description.csv + job_roles.csv"),
                ("Entry-level", "Support network operations including TCP/IP subnetting, switch patching, basic firewall rules, and Linux diagnostics.", ["Networking", "TCP/IP", "Linux", "Firewalls", "Cisco"], ["Network Security", "Git", "Bash"], "Kaggle job_roles.csv + job_title_des.csv"),
                ("Senior", "Architect fault-tolerant global backbone networks, SD-WAN, automated Ansible/Python network provisioning, and security compliance.", ["Networking", "Cisco", "Network Security", "TCP/IP", "Python", "Ansible"], ["Firewalls", "AWS", "Linux"], "Kaggle job_roles.csv + job_description.csv"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Mid-level", "Entry-level", "Senior"],
        },
        {
            "title": "PHP Developer",
            "category": "Web Development",
            "kaggle_jtd": (["PHP Developer"], {"PHP", "Laravel", "MySQL", "JavaScript"}, {"PHP", "Laravel", "Symfony", "MySQL", "PostgreSQL", "HTML5", "CSS3", "JavaScript", "jQuery", "REST API", "Git", "WordPress", "Docker", "Linux"}),
            "curated_kaggle": [
                ("Entry-level", "Build dynamic server-rendered web applications and REST APIs with PHP, Laravel, MySQL, HTML5, CSS3, and JavaScript.", ["PHP", "Laravel", "MySQL", "HTML5", "CSS3"], ["JavaScript", "Git", "REST API"], "Kaggle job_roles.csv + job_title_des.csv"),
                ("Junior", "Maintain WordPress and custom PHP web portals integrating MySQL databases, jQuery, Responsive Design, and Git version control.", ["PHP", "WordPress", "MySQL", "HTML5", "CSS3", "JavaScript"], ["jQuery", "Git", "Responsive Design"], "Kaggle job_title_des.csv (Wordpress/PHP Developer)"),
                ("Mid-level", "Architect modern PHP Symfony and Laravel microservices backed by MySQL, Redis caching, Docker containers, and automated tests.", ["PHP", "Laravel", "Symfony", "MySQL", "REST API", "Docker"], ["Redis", "Git", "Linux"], "Kaggle job_roles.csv (PHP Developer)"),
            ],
            "experience_cycle": ["Entry-level", "Junior", "Mid-level", "Junior", "Entry-level", "Mid-level", "Junior"],
        },
    ]

    rows = []
    job_counter = 1

    for bp in role_blueprints:
        role_rows = []
        title = bp["title"]
        category = bp["category"]
        curated = list(bp.get("curated_kaggle", []))

        # Fill up to 7 rows per role: prioritize genuine cleaned postings from job_title_des.csv / data.csv!
        need_from_kaggle = max(0, 7 - len(curated))
        extracted_items = []
        if "kaggle_jtd" in bp and need_from_kaggle > 0:
            k_titles, must, allowed = bp["kaggle_jtd"]
            extracted_items = sample_kaggle_jtd(k_titles, must, allowed, n=need_from_kaggle)
        elif "kaggle_data_csv" in bp and need_from_kaggle > 0:
            pat, must, allowed = bp["kaggle_data_csv"]
            extracted_items = sample_kaggle_data_csv(pat, must, allowed, n=need_from_kaggle)

        # Put curated Entry-level benchmark first (guarantees JOB_001 is clean Entry-level Python Developer),
        # then interleave genuine Kaggle postings, then remaining curated postings
        combined = []
        if curated:
            combined.append(("curated", curated[0]))
        for item in extracted_items:
            combined.append(("kaggle", item))
        for c in curated[1:]:
            combined.append(("curated", c))

        # Pad cleanly if Kaggle returned slightly fewer than need_from_kaggle
        idx = 0
        while len(combined) < 7 and curated:
            combined.append(("curated", curated[idx % len(curated)]))
            idx += 1

        exp_cycle = bp.get("experience_cycle", ["Entry-level", "Junior", "Mid-level", "Junior", "Entry-level", "Mid-level", "Senior"])

        for i, (kind, payload) in enumerate(combined[:7]):
            exp_level = exp_cycle[i % len(exp_cycle)]
            if kind == "curated":
                exp_override, desc, req, pref, src = payload
                # Keep JOB_001 explicitly Entry-level
                if job_counter == 1 or i == 0:
                    exp_level = exp_override
            else:
                desc, req, pref, src = payload

            req_clean = [s for s in req if s in valid_skills]
            pref_clean = [s for s in pref if s in valid_skills and s not in req_clean]

            role_rows.append({
                "job_id": f"JOB_{job_counter:03d}",
                "title": title,
                "category": category,
                "experience_level": exp_level,
                "description": desc,
                "required_skills": "|".join(req_clean),
                "preferred_skills": "|".join(pref_clean),
                "source_dataset": src,
            })
            job_counter += 1

        rows.extend(role_rows)

    out_df = pd.DataFrame(rows)
    validate_jobs_skills(out_df)
    out_df.to_csv(DATA_DIR / "jobs.csv", index=False, encoding="utf-8")
    print(f"[jobs.csv] Wrote {len(out_df)} validated postings across {out_df['title'].nunique()} roles.")
    return out_df


# ---------------------------------------------------------------------------
# 4. Beginner-Friendly Role Information & Sequential Career Roadmaps
# ---------------------------------------------------------------------------

def _split_br_bullets(raw: str) -> List[str]:
    if not isinstance(raw, str) or not raw.strip():
        return []
    parts = re.split(r"<br\s*/?>|\n", raw)
    cleaned = []
    for p in parts:
        s = re.sub(r"^[•\-\*\s]+", "", p).strip()
        if s:
            cleaned.append(s)
    return cleaned


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def build_job_roles_info(jobs_df: pd.DataFrame) -> Dict[str, dict]:
    """
    Create data/job_roles_info.json combining Kaggle job_description.csv, job_roles.csv,
    and resume_data.csv with beginner-friendly explanations and ordered learning roadmaps.
    """
    jd_df = pd.read_csv(KAGGLE_DIR / "job_description.csv")
    jr_df = pd.read_csv(KAGGLE_DIR / "job_roles.csv")
    rd_df = pd.read_csv(KAGGLE_DIR / "resume_data.csv", encoding="utf-8")
    rd_df.columns = [c.lstrip("\ufeff") for c in rd_df.columns]

    def jd_lookup(title: str) -> Optional[pd.Series]:
        sub = jd_df[jd_df["Job Title"] == title]
        return sub.iloc[0] if not sub.empty else None

    def jr_lookup(title: str) -> Optional[pd.Series]:
        sub = jr_df[jr_df["Job Title"] == title]
        return sub.iloc[0] if not sub.empty else None

    def rd_resp(role_name: str) -> List[str]:
        sub = rd_df[rd_df["job_position_name"] == role_name]
        if sub.empty:
            return []
        raw = str(sub.iloc[0].get("responsibilities.1", ""))
        return [s.strip() for s in raw.splitlines() if s.strip()][:8]

    # Rich beginner-friendly educational content & ordered career roadmaps per role
    # Sourced & enriched from Kaggle job_description.csv, job_roles.csv, resume_data.csv
    role_specs = {
        "Python Developer": {
            "jd_title": "Backend Engineer",
            "jr_title": "Python Developer",
            "beginner_summary": "A Python Developer uses the Python programming language to build web backends, APIs, data automation scripts, and server applications cleanly and quickly.",
            "overview": "Python Developers power server-side web apps, REST APIs, and workflow automation using Python's clean syntax and mature web frameworks like Django, Flask, and FastAPI.",
            "what_they_do": "Think of a web app or mobile app: whenever you log in, save a form, or request data, a Python Developer wrote the backend code running on the server that processes that request, talks to the database, and returns the response.",
            "day_to_day": [
                "Write clean, readable Python code for APIs, backend features, and automation scripts.",
                "Build and maintain web services using frameworks like Django, Flask, or FastAPI.",
                "Design database schemas and write queries in PostgreSQL, MySQL, or SQL.",
                "Write automated unit tests with Pytest and debug issues using logs and Git.",
                "Package applications with Docker and collaborate via GitHub pull requests.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Python", "SQL", "HTML5", "CSS3", "Bash"],
                "frameworks_libraries": ["Django", "Flask", "FastAPI", "Pytest", "Celery"],
                "databases_data": ["PostgreSQL", "MySQL", "SQLite", "Redis"],
                "tools_platforms": ["Git", "Docker", "REST API", "Linux", "AWS"],
            },
            "soft_skills": ["Problem Solving", "Analytical Thinking", "Communication", "Collaboration", "Attention to Detail"],
            "certifications": ["freeCodeCamp Scientific Computing with Python", "PCAP Certified Associate in Python Programming", "AWS Certified Cloud Practitioner"],
            "career_growth": [
                "Junior Python Developer (0–2 yrs): Focus on Python fundamentals, Django/Flask APIs, SQL, and Git workflows.",
                "Mid-Level Python / Backend Engineer (2–5 yrs): Own full services, caching (Redis), async queues, Docker, and cloud deployment.",
                "Senior Python / Staff Engineer (5+ yrs): Design distributed microservices, mentor developers, and set architecture standards.",
                "Adjacent Paths: Backend Developer, Full Stack Developer, Data Engineer, or ML Engineer.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Python Core & Version Control", "duration": "4–6 weeks", "description": "Master Python syntax, data structures, OOP, virtual environments, and Git collaboration.", "skills": ["Python", "Git"]},
                {"stage": 2, "title": "Databases & Web Fundamentals", "duration": "3–4 weeks", "description": "Learn relational database design, SQL querying, HTTP fundamentals, and REST APIs.", "skills": ["SQL", "PostgreSQL", "REST API"]},
                {"stage": 3, "title": "Python Web Frameworks", "duration": "4–6 weeks", "description": "Build full backend APIs with Django and high-speed services with FastAPI or Flask.", "skills": ["Django", "FastAPI", "Flask"]},
                {"stage": 4, "title": "Testing, Containers & Deployment", "duration": "3–4 weeks", "description": "Automate testing with Pytest, containerize with Docker, and deploy on Linux/AWS.", "skills": ["Pytest", "Docker", "Linux", "AWS"]},
            ],
        },
        "Java Developer": {
            "jd_title": "Backend Engineer",
            "jr_title": "Java Backend Developer",
            "beginner_summary": "A Java Developer builds reliable, large-scale enterprise software, banking backends, and cloud microservices using Java and the Spring Boot ecosystem.",
            "overview": "Java remains one of the world's most trusted languages for mission-critical backends, e-commerce platforms, and financial systems thanks to strong typing, performance, and Spring Boot.",
            "what_they_do": "Java Developers turn business requirements into structured object-oriented backend services that handle thousands of concurrent users reliably—connecting APIs, enterprise databases, and message queues.",
            "day_to_day": [
                "Build RESTful APIs and microservices using Java and Spring Boot.",
                "Map Java objects to relational databases with Hibernate/JPA and optimize SQL queries.",
                "Write automated unit and integration tests using JUnit and Mockito.",
                "Manage builds with Maven or Gradle and review teammates' code in Git.",
                "Containerize services with Docker and monitor production microservice health.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Java", "SQL"],
                "frameworks_libraries": ["Spring Boot", "Spring Framework", "Hibernate", "JUnit"],
                "databases_data": ["PostgreSQL", "MySQL", "Oracle Database", "Redis"],
                "tools_platforms": ["Maven", "Gradle", "Docker", "Git", "Kafka", "REST API"],
            },
            "soft_skills": ["Problem Solving", "Attention to Detail", "Teamwork", "Communication", "Analytical Thinking"],
            "certifications": ["Oracle Certified Professional: Java SE Developer", "VMware Spring Certified Professional", "AWS Certified Developer"],
            "career_growth": [
                "Junior Java Developer (0–2 yrs): Build Spring Boot CRUD APIs, SQL integrations, and JUnit tests.",
                "Java Backend / Microservices Engineer (2–5 yrs): Work with Kafka event streaming, Docker/Kubernetes, and distributed caching.",
                "Senior Java Engineer / Solutions Architect (5+ yrs): Lead enterprise architecture and high-throughput system design.",
                "Adjacent Paths: Backend Developer, Software Engineer, Cloud Architect, Android Kotlin Developer.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Core Java & OOP Foundations", "duration": "5–7 weeks", "description": "Master Java syntax, OOP design, collections, streams, exception handling, and Git.", "skills": ["Java", "Git"]},
                {"stage": 2, "title": "SQL & Build Tooling", "duration": "3–4 weeks", "description": "Learn relational database modeling, SQL queries, and dependency builds with Maven.", "skills": ["SQL", "PostgreSQL", "Maven"]},
                {"stage": 3, "title": "Spring Boot & APIs", "duration": "5–6 weeks", "description": "Build production REST APIs, authentication, and database access using Spring Boot and Hibernate.", "skills": ["Spring Boot", "Hibernate", "REST API"]},
                {"stage": 4, "title": "Testing, Microservices & Containers", "duration": "4 weeks", "description": "Verify reliability with JUnit and scale distributed services using Docker and Microservices.", "skills": ["JUnit", "Docker", "Microservices"]},
            ],
        },
        "Full Stack Developer": {
            "jd_title": "Full-Stack Engineer",
            "jr_title": "Full Stack Developer",
            "rd_title": "Full Stack Developer (Python,React js)",
            "beginner_summary": "A Full Stack Developer builds both the visible frontend website users click on and the behind-the-scenes backend server and database.",
            "overview": "Full Stack Developers bridge user experience and server architecture—capable of taking an entire web product from UI layout all the way to API logic, database storage, and cloud hosting.",
            "what_they_do": "In a single feature—like adding a shopping cart or user dashboard—a Full Stack Developer creates the interactive React UI in the browser, builds the Node.js or Python API endpoints, stores the items in PostgreSQL/MongoDB, and deploys everything online.",
            "day_to_day": [
                "Build interactive frontend components with React or TypeScript plus responsive HTML5/CSS3.",
                "Create RESTful backend endpoints using Node.js/Express or Python/Django.",
                "Design and query relational (PostgreSQL/MySQL) or NoSQL (MongoDB) databases.",
                "Write full-stack tests, debug browser-to-server requests, and manage Git branches.",
                "Containerize apps with Docker and deploy updates via CI/CD pipelines.",
            ],
            "languages_frameworks_tools": {
                "languages": ["JavaScript", "TypeScript", "Python", "HTML5", "CSS3", "SQL"],
                "frameworks_libraries": ["React", "Next.js", "Node.js", "Express.js", "Django", "Tailwind CSS"],
                "databases_data": ["PostgreSQL", "MongoDB", "MySQL", "Redis"],
                "tools_platforms": ["Git", "REST API", "Docker", "AWS", "CI/CD"],
            },
            "soft_skills": ["Problem Solving", "Adaptability", "Communication", "Collaboration", "Time Management"],
            "certifications": ["Meta Front-End / Back-End Developer Certificate", "freeCodeCamp Full Stack Curriculum", "AWS Cloud Practitioner"],
            "career_growth": [
                "Junior Full Stack Developer (0–2 yrs): Ship web features across HTML/CSS/React and Node.js or Python APIs.",
                "Mid-Level Full Stack Engineer (2–5 yrs): Own product modules end-to-end including database tuning, auth, TypeScript, and Docker.",
                "Lead Engineer / Technical Architect (5+ yrs): Guide product architecture, performance, and cross-functional teams.",
                "Adjacent Paths: Frontend Developer, Backend Developer, Software Engineer, Tech Lead.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Web Basics & JavaScript", "duration": "4–6 weeks", "description": "Learn semantic HTML5, modern CSS3 layouts, core JavaScript, and Git.", "skills": ["HTML5", "CSS3", "JavaScript", "Git"]},
                {"stage": 2, "title": "Modern Frontend Framework", "duration": "5–6 weeks", "description": "Build dynamic interactive interfaces with React and strong typing with TypeScript.", "skills": ["React", "TypeScript"]},
                {"stage": 3, "title": "Backend APIs & Databases", "duration": "5–6 weeks", "description": "Build REST APIs with Node.js/Express or Python/Django backed by PostgreSQL or MongoDB.", "skills": ["Node.js", "Express.js", "SQL", "PostgreSQL", "REST API"]},
                {"stage": 4, "title": "Containers & Cloud Deployment", "duration": "3–4 weeks", "description": "Deploy full-stack apps reliably using Docker, CI/CD, and cloud hosting.", "skills": ["Docker", "AWS", "CI/CD"]},
            ],
        },
        "Frontend Developer": {
            "jd_title": "Frontend Engineer",
            "jr_title": "Frontend Developer",
            "beginner_summary": "A Frontend Developer crafts everything users see and interact with in a web browser—layouts, buttons, animations, forms, and fast responsive pages.",
            "overview": "Frontend Developers bring designs to life in browsers on laptops and phones. They combine visual polish with JavaScript engineering so websites feel snappy, intuitive, and accessible.",
            "what_they_do": "Working closely with UI/UX designers and backend teams, Frontend Developers turn Figma mockups into responsive HTML/CSS/React code and connect UI state to live backend APIs.",
            "day_to_day": [
                "Translate UI/UX wireframes into responsive, accessible HTML5 and CSS3 components.",
                "Build interactive single-page applications in React, TypeScript, Angular, or Next.js.",
                "Connect frontend views to backend REST or GraphQL APIs and manage application state.",
                "Optimize Core Web Vitals, page load speed, and cross-browser compatibility.",
                "Write UI component tests with Jest or Playwright and collaborate via Git.",
            ],
            "languages_frameworks_tools": {
                "languages": ["JavaScript", "TypeScript", "HTML5", "CSS3"],
                "frameworks_libraries": ["React", "Next.js", "Angular", "Vue.js", "Tailwind CSS", "Redux"],
                "databases_data": ["REST API", "GraphQL", "JSON"],
                "tools_platforms": ["Git", "Figma", "Jest", "Responsive Design"],
            },
            "soft_skills": ["Attention to Detail", "Communication", "Collaboration", "Problem Solving", "Adaptability"],
            "certifications": ["Meta Front-End Developer Professional Certificate", "freeCodeCamp Front End Development Libraries"],
            "career_growth": [
                "Junior Frontend Developer (0–2 yrs): Master HTML/CSS, JavaScript, Responsive Design, and React components.",
                "Mid-Level Frontend Engineer (2–5 yrs): Lead TypeScript architecture, Next.js SSR, state management, and web performance.",
                "Senior / Staff Frontend Architect (5+ yrs): Build company design systems and micro-frontends.",
                "Adjacent Paths: Full Stack Developer, UI/UX Designer, Mobile Developer (React Native).",
            ],
            "roadmap": [
                {"stage": 1, "title": "HTML, CSS & Responsive Web", "duration": "3–4 weeks", "description": "Master Flexbox, Grid, accessibility, Responsive Design, and Tailwind CSS.", "skills": ["HTML5", "CSS3", "Responsive Design", "Tailwind CSS"]},
                {"stage": 2, "title": "Core JavaScript & Git", "duration": "4–5 weeks", "description": "Understand DOM manipulation, async/await, Fetch APIs, ES6+, and Git workflows.", "skills": ["JavaScript", "Git"]},
                {"stage": 3, "title": "React & TypeScript", "duration": "5–6 weeks", "description": "Build reusable components, state/hooks, and type-safe web apps with React and TypeScript.", "skills": ["React", "TypeScript", "REST API"]},
                {"stage": 4, "title": "Production Next.js & Testing", "duration": "3–4 weeks", "description": "Add SSR/routing with Next.js, component testing with Jest, and UI collaboration via Figma.", "skills": ["Next.js", "Jest", "Figma"]},
            ],
        },
        "Backend Developer": {
            "jd_title": "Backend Engineer",
            "jr_title": "Backend Developer",
            "beginner_summary": "A Backend Developer builds the invisible engine behind websites and apps—servers, APIs, business rules, authentication, and databases.",
            "overview": "While users only see the frontend UI, Backend Developers design the secure server logic, data pipelines, and APIs that store records safely and keep apps fast under heavy traffic.",
            "what_they_do": "Backend Developers architect databases, implement authentication/permissions, expose documented REST or GraphQL APIs, optimize slow SQL queries, and ensure servers handle traffic spikes cleanly.",
            "day_to_day": [
                "Design server architectures and build RESTful or GraphQL APIs using Node.js, Python, Java, or Go.",
                "Model relational (PostgreSQL, MySQL) and NoSQL (MongoDB, Redis) data stores.",
                "Implement secure login, role permissions, input validation, and rate limiting.",
                "Profile slow queries, add caching layers, and write automated API tests.",
                "Deploy containerized backend microservices via Docker, Linux, and cloud providers.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Python", "JavaScript", "Java", "Go", "SQL"],
                "frameworks_libraries": ["Node.js", "Express.js", "Django", "FastAPI", "Spring Boot"],
                "databases_data": ["PostgreSQL", "MongoDB", "MySQL", "Redis", "NoSQL"],
                "tools_platforms": ["REST API", "GraphQL", "Docker", "Microservices", "Git", "AWS"],
            },
            "soft_skills": ["Analytical Thinking", "Problem Solving", "Communication", "Troubleshooting", "Teamwork"],
            "certifications": ["Meta Back-End Developer Certificate", "freeCodeCamp Back End Development and APIs"],
            "career_growth": [
                "Junior Backend Developer (0–2 yrs): Write API routes, database queries, and authentication flows.",
                "Mid-Level Backend Engineer (2–5 yrs): Own caching, message queues, microservices, and SQL performance optimization.",
                "Senior / Principal Backend Engineer (5+ yrs): Architect high-availability distributed systems serving millions.",
                "Adjacent Paths: Full Stack Developer, Python/Java Developer, Cloud Engineer, Data Engineer.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Server Language & Git", "duration": "4–5 weeks", "description": "Choose Node.js (JavaScript) or Python and master core programming and Git.", "skills": ["Node.js", "Python", "Git"]},
                {"stage": 2, "title": "Databases & Modeling", "duration": "4 weeks", "description": "Learn relational schemas with PostgreSQL/SQL alongside document caching with MongoDB or Redis.", "skills": ["SQL", "PostgreSQL", "MongoDB", "Redis"]},
                {"stage": 3, "title": "APIs, Auth & Frameworks", "duration": "5 weeks", "description": "Build RESTful and GraphQL services using Express.js or FastAPI with secure authentication.", "skills": ["Express.js", "FastAPI", "REST API"]},
                {"stage": 4, "title": "Scaling, Docker & Microservices", "duration": "4 weeks", "description": "Containerize services with Docker and learn distributed Microservices and System Design.", "skills": ["Docker", "Microservices", "System Design"]},
            ],
        },
        "Data Analyst": {
            "jd_title": "Data & Analytics Consultant",
            "jr_title": "Data Analyst",
            "beginner_summary": "A Data Analyst turns messy spreadsheets and database records into clear charts, KPI dashboards, and business answers that help companies make smart decisions.",
            "overview": "Data Analysts act as detectives for a company's numbers—cleaning raw sales, product, or customer datasets, spotting trends, and presenting findings visually to non-technical teams.",
            "what_they_do": "Instead of building heavy AI models, a Data Analyst writes SQL queries to pull facts out of databases, cleans anomalies in Python/Excel, calculates key business metrics, and builds interactive Tableau or Power BI dashboards.",
            "day_to_day": [
                "Query company databases with SQL to extract accurate business datasets.",
                "Clean missing or duplicate values using Excel, SQL, or Python Pandas.",
                "Analyze trends, funnel conversion, and performance KPIs using descriptive statistics.",
                "Design interactive dashboards in Tableau or Power BI for leadership teams.",
                "Present actionable insights clearly using charts and storytelling.",
            ],
            "languages_frameworks_tools": {
                "languages": ["SQL", "Python", "R"],
                "frameworks_libraries": ["Pandas", "NumPy", "Matplotlib", "Seaborn"],
                "databases_data": ["PostgreSQL", "MySQL", "Google BigQuery", "Snowflake", "Microsoft Excel"],
                "tools_platforms": ["Tableau", "Power BI", "Data Analysis", "Statistics", "Data Visualization"],
            },
            "soft_skills": ["Analytical Thinking", "Presentation", "Communication", "Attention to Detail", "Problem Solving"],
            "certifications": ["Google Data Analytics Professional Certificate", "Microsoft Power BI Data Analyst (PL-300)", "Tableau Desktop Specialist"],
            "career_growth": [
                "Junior Data Analyst (0–2 yrs): Master Excel, SQL queries, basic statistics, and dashboard creation.",
                "Senior Data / BI Analyst (2–4 yrs): Automate Python/dbt transformations, own stakeholder metrics, and guide product decisions.",
                "Analytics Manager / Lead (4+ yrs): Lead BI strategy across departments.",
                "Adjacent Paths: Business Analyst, Data Scientist, Data Engineer.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Spreadsheets & Data Thinking", "duration": "2–3 weeks", "description": "Learn pivot tables, lookups, KPI thinking, and structured data analysis in Excel.", "skills": ["Microsoft Excel", "Data Analysis"]},
                {"stage": 2, "title": "SQL Query Mastery", "duration": "4 weeks", "description": "Write joins, aggregations, window functions, and CTEs to extract data directly from databases.", "skills": ["SQL", "PostgreSQL"]},
                {"stage": 3, "title": "BI Dashboards & Storytelling", "duration": "4 weeks", "description": "Turn numbers into clear interactive dashboards using Tableau and Power BI.", "skills": ["Tableau", "Power BI", "Data Visualization"]},
                {"stage": 4, "title": "Python & Statistical Analysis", "duration": "4–5 weeks", "description": "Automate larger analyses with Python Pandas and apply statistics for A/B testing.", "skills": ["Python", "Pandas", "Statistics"]},
            ],
        },
        "Data Scientist": {
            "jr_title": "Data Scientist",
            "beginner_summary": "A Data Scientist combines statistics, programming, and machine learning to uncover hidden patterns and predict future outcomes—like forecasting customer churn or demand.",
            "overview": "Going deeper than traditional reporting, Data Scientists run experiments, build predictive statistical and ML models in Python, and translate complex mathematical findings into business strategy.",
            "what_they_do": "A Data Scientist formulates measurable hypotheses, queries large SQL data warehouses, explores feature relationships in Jupyter notebooks, trains Scikit-learn predictive models, validates accuracy, and shares recommendations.",
            "day_to_day": [
                "Extract and clean large datasets using SQL, Python Pandas, and NumPy.",
                "Conduct statistical analysis and design A/B experiments to test product changes.",
                "Build predictive regression, classification, and clustering models with Scikit-learn.",
                "Visualize correlations, model errors, and business impact via Matplotlib/Seaborn.",
                "Present findings and model recommendations clearly to stakeholders.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Python", "SQL", "R"],
                "frameworks_libraries": ["Pandas", "NumPy", "Scikit-Learn", "TensorFlow", "Matplotlib", "Seaborn"],
                "databases_data": ["PostgreSQL", "Google BigQuery", "Snowflake"],
                "tools_platforms": ["Jupyter", "Machine Learning", "Statistics", "Data Analysis", "Git"],
            },
            "soft_skills": ["Analytical Thinking", "Critical Thinking", "Presentation", "Communication", "Problem Solving"],
            "certifications": ["IBM Data Science Professional Certificate", "DeepLearning.AI Machine Learning Specialization"],
            "career_growth": [
                "Junior Data Scientist (0–2 yrs): Focus on SQL, Python Pandas, statistics, and Scikit-Learn modeling.",
                "Senior Data Scientist (2–5 yrs): Lead A/B experimentation, causal inference, and high-value predictive systems.",
                "Principal Data Scientist / Head of Data Science (5+ yrs): Shape company-wide AI and data strategy.",
                "Adjacent Paths: ML Engineer, Data Analyst, Quantitative Analyst.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Python & Data Wrangling", "duration": "4 weeks", "description": "Master Python, Jupyter notebooks, NumPy arrays, and Pandas dataframes.", "skills": ["Python", "Pandas", "NumPy", "Jupyter"]},
                {"stage": 2, "title": "SQL, Statistics & Visualization", "duration": "4–5 weeks", "description": "Query analytical warehouses with SQL and learn probability, distributions, and plotting.", "skills": ["SQL", "Statistics", "Data Visualization"]},
                {"stage": 3, "title": "Core Machine Learning", "duration": "6 weeks", "description": "Build supervised and unsupervised predictive models and validate them using Scikit-Learn.", "skills": ["Machine Learning", "Scikit-Learn"]},
                {"stage": 4, "title": "Deep Learning & Applied AI", "duration": "5 weeks", "description": "Expand into neural networks, NLP, or big data workflows with TensorFlow and Git.", "skills": ["TensorFlow", "Natural Language Processing", "Git"]},
            ],
        },
        "ML Engineer": {
            "jr_title": "Machine Learning Engineer",
            "rd_title": "Machine Learning (ML) Engineer",
            "beginner_summary": "A Machine Learning Engineer takes AI and machine learning models out of notebooks and engineers them into reliable, fast software running in real apps.",
            "overview": "Sitting at the intersection of Software Engineering and AI research, ML Engineers build training pipelines, optimize deep neural networks, and deploy scalable inference APIs used by millions.",
            "what_they_do": "While Data Scientists often explore datasets and prototype models, ML Engineers write production Python code in PyTorch or TensorFlow, track experiments with MLflow, wrap models inside FastAPI/Docker services, and monitor accuracy in production.",
            "day_to_day": [
                "Build end-to-end ML training, evaluation, and feature pipelines in Python.",
                "Train deep learning models for NLP, recommendations, or computer vision in PyTorch/TensorFlow.",
                "Package models behind low-latency REST APIs using FastAPI and Docker.",
                "Track experiments, model versions, and drift using MLflow.",
                "Scale training and deployment pipelines on cloud GPUs (AWS/GCP) and Kubernetes.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Python", "SQL", "C++"],
                "frameworks_libraries": ["PyTorch", "TensorFlow", "Scikit-Learn", "Hugging Face", "FastAPI"],
                "databases_data": ["PostgreSQL", "Pandas", "NumPy"],
                "tools_platforms": ["Machine Learning", "Deep Learning", "Docker", "MLflow", "Kubernetes", "AWS"],
            },
            "soft_skills": ["Problem Solving", "Analytical Thinking", "Collaboration", "Adaptability", "Communication"],
            "certifications": ["DeepLearning.AI Machine Learning Specialization", "Deep Learning Specialization", "AWS Certified Machine Learning Specialty"],
            "career_growth": [
                "Junior ML Engineer (0–2 yrs): Build Python ML pipelines, Scikit-Learn/PyTorch models, and Docker inference APIs.",
                "Senior ML / MLOps Engineer (2–5 yrs): Optimize LLM/deep learning training, vector search, and scalable serving.",
                "Staff AI Architect (5+ yrs): Lead generative AI and enterprise ML platform architecture.",
                "Adjacent Paths: Data Scientist, AI Engineer, Backend Software Engineer.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Python Engineering & Math Base", "duration": "4–5 weeks", "description": "Write clean production Python, NumPy linear algebra, Pandas data prep, and Git.", "skills": ["Python", "NumPy", "Pandas", "Git"]},
                {"stage": 2, "title": "Classical Machine Learning", "duration": "5 weeks", "description": "Learn feature engineering, tree ensembles, and validation metrics in Scikit-Learn.", "skills": ["Machine Learning", "Scikit-Learn"]},
                {"stage": 3, "title": "Deep Learning Frameworks", "duration": "6–8 weeks", "description": "Train neural networks, NLP, and vision models with PyTorch and TensorFlow.", "skills": ["Deep Learning", "PyTorch", "TensorFlow"]},
                {"stage": 4, "title": "MLOps, APIs & Cloud Serving", "duration": "4–5 weeks", "description": "Serve models via FastAPI and Docker and track experiments cleanly with MLflow.", "skills": ["FastAPI", "Docker", "MLflow", "AWS"]},
            ],
        },
        "DevOps Engineer": {
            "jd_title": "DevOps Engineer",
            "jr_title": "DevOps Engineer",
            "rd_title": "DevOps Engineer",
            "beginner_summary": "A DevOps Engineer automates how code goes from a developer's laptop onto live servers—making software releases fast, repeatable, and reliable.",
            "overview": "DevOps bridges software development (Dev) and IT operations (Ops). Instead of manually copying files onto servers, DevOps Engineers build automated CI/CD pipelines, containers, and Infrastructure as Code.",
            "what_they_do": "Whenever an engineer pushes new code to GitHub, pipelines built by the DevOps Engineer automatically run tests, build a Docker image, deploy it cleanly into Kubernetes on AWS, and alert the team if latency spikes.",
            "day_to_day": [
                "Build and maintain automated CI/CD pipelines using GitHub Actions or Jenkins.",
                "Containerize services with Docker and orchestrate workloads on Kubernetes.",
                "Define cloud servers, networks, and permissions cleanly as code using Terraform or Ansible.",
                "Set up system monitoring, logs, and alerts with Prometheus and Grafana.",
                "Manage Linux servers, Bash/Python automation scripts, and cloud security.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Bash", "Python", "SQL"],
                "frameworks_libraries": ["Terraform", "Ansible"],
                "databases_data": ["Linux", "Prometheus", "Grafana"],
                "tools_platforms": ["Docker", "Kubernetes", "CI/CD", "AWS", "Jenkins", "GitHub Actions", "Git"],
            },
            "soft_skills": ["Troubleshooting", "Collaboration", "Communication", "Problem Solving", "Adaptability"],
            "certifications": ["AWS Certified DevOps Engineer", "Certified Kubernetes Administrator (CKA)", "HashiCorp Certified: Terraform Associate"],
            "career_growth": [
                "Junior DevOps Engineer (0–2 yrs): Automate builds with Linux, Git, Docker, and CI/CD tools.",
                "Mid-Level DevOps / SRE Engineer (2–5 yrs): Manage Kubernetes production clusters, Terraform IaC, and observability.",
                "Principal Platform Architect (5+ yrs): Design internal developer platforms for whole organizations.",
                "Adjacent Paths: Cloud Engineer, Site Reliability Engineer (SRE), Platform Engineer.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Linux, Networking & Scripting", "duration": "4 weeks", "description": "Become comfortable in the Linux terminal, Bash scripting, Python automation, and Git.", "skills": ["Linux", "Bash", "Python", "Git"]},
                {"stage": 2, "title": "Containers & Orchestration", "duration": "5 weeks", "description": "Package apps reliably with Docker containers and scale clusters using Kubernetes.", "skills": ["Docker", "Kubernetes"]},
                {"stage": 3, "title": "CI/CD Pipelines", "duration": "3–4 weeks", "description": "Automate testing and zero-downtime deployments with GitHub Actions or Jenkins.", "skills": ["CI/CD", "GitHub Actions", "Jenkins"]},
                {"stage": 4, "title": "Cloud, IaC & Monitoring", "duration": "4–5 weeks", "description": "Provision AWS infrastructure with Terraform and observe health with Prometheus and Grafana.", "skills": ["AWS", "Terraform", "Prometheus", "Grafana"]},
            ],
        },
        "Cloud Engineer": {
            "jd_title": "Cloud Engineer",
            "jr_title": "Cloud Architect",
            "beginner_summary": "A Cloud Engineer designs, secures, and runs an organization's servers, databases, and apps on cloud platforms like AWS, Microsoft Azure, or Google Cloud.",
            "overview": "Modern companies rent elastic computing power from cloud providers instead of maintaining physical server rooms. Cloud Engineers build scalable, cost-efficient, and secure cloud environments.",
            "what_they_do": "A Cloud Engineer sets up virtual private networks, storage buckets, serverless APIs, identity permissions (IAM), managed databases, and automated backups so apps stay online globally.",
            "day_to_day": [
                "Configure virtual networks, compute instances, load balancers, and managed databases on AWS, Azure, or GCP.",
                "Automate cloud infrastructure provisioning with Terraform and Python/Bash scripts.",
                "Migrate legacy servers safely into containerized or serverless cloud architectures.",
                "Enforce cloud IAM permissions, firewall policies, and encryption standards.",
                "Monitor cloud usage, uptime metrics, and optimize monthly cloud infrastructure bills.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Python", "Bash", "SQL"],
                "frameworks_libraries": ["Terraform", "Docker", "Kubernetes"],
                "databases_data": ["PostgreSQL", "Linux"],
                "tools_platforms": ["AWS", "Microsoft Azure", "Google Cloud Platform", "Networking", "Network Security", "CI/CD"],
            },
            "soft_skills": ["Problem Solving", "Communication", "Troubleshooting", "Analytical Thinking", "Collaboration"],
            "certifications": ["AWS Certified Solutions Architect – Associate", "Microsoft Certified: Azure Administrator", "Google Associate Cloud Engineer"],
            "career_growth": [
                "Cloud Support / Junior Cloud Engineer (0–2 yrs): Manage VMs, storage, IAM, and Linux networking on AWS/Azure.",
                "Cloud Engineer (2–5 yrs): Design Infrastructure as Code (Terraform), Kubernetes clusters, and security hardening.",
                "Cloud Solutions Architect (5+ yrs): Design multi-cloud enterprise architectures.",
                "Adjacent Paths: DevOps Engineer, Cybersecurity Engineer, Solutions Architect.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Linux, Networking & Git", "duration": "4 weeks", "description": "Understand Linux administration, TCP/IP routing, DNS, firewalls, and Git.", "skills": ["Linux", "TCP/IP", "Networking", "Git"]},
                {"stage": 2, "title": "Core Cloud Platform (AWS/Azure)", "duration": "5–6 weeks", "description": "Master cloud compute, IAM security, VPC networking, and managed storage/databases.", "skills": ["AWS", "Microsoft Azure", "Network Security"]},
                {"stage": 3, "title": "Containers & Cloud Automation", "duration": "4–5 weeks", "description": "Automate deployments with Docker, Python scripting, and CI/CD workflows.", "skills": ["Docker", "Python", "CI/CD"]},
                {"stage": 4, "title": "Infrastructure as Code & Scaling", "duration": "4 weeks", "description": "Manage repeatable cloud infrastructure via Terraform and Kubernetes.", "skills": ["Terraform", "Kubernetes"]},
            ],
        },
        "Embedded Systems Engineer": {
            "jd_title": "Embedded Software Engineer",
            "jr_title": "Embedded Systems Engineer",
            "beginner_summary": "An Embedded Systems Engineer writes fast, compact software that controls real physical hardware—like smartwatches, medical monitors, drones, cars, and IoT sensors.",
            "overview": "Unlike web developers building apps on high-RAM laptops, Embedded Engineers program tiny microcontrollers directly in C/C++, managing every byte of memory and communicating directly with electronics.",
            "what_they_do": "Embedded Engineers read chip datasheets, write hardware drivers in Embedded C/C++ over protocols like I2C, SPI, and UART, run real-time operating systems (RTOS) or Embedded Linux, and debug boards with logic analyzers.",
            "day_to_day": [
                "Write low-level firmware in C, Embedded C, and C++ for STM32, ARM, or ESP32 microcontrollers.",
                "Read hardware schematics and sensor datasheets to implement SPI, I2C, UART, or CAN Bus drivers.",
                "Build concurrent real-time tasks using FreeRTOS or Embedded Linux.",
                "Debug hardware-software timing issues, optimize RAM/flash footprint, and lower battery usage.",
                "Write Python test harnesses for automated hardware-in-the-loop validation.",
            ],
            "languages_frameworks_tools": {
                "languages": ["C", "C++", "Embedded C", "Python"],
                "frameworks_libraries": ["RTOS", "Embedded Linux", "Arduino"],
                "databases_data": ["UART", "SPI", "I2C", "CAN Bus", "MQTT"],
                "tools_platforms": ["Microcontrollers", "STM32", "ESP32", "ARM", "Raspberry Pi", "Git"],
            },
            "soft_skills": ["Analytical Thinking", "Problem Solving", "Attention to Detail", "Troubleshooting", "Collaboration"],
            "certifications": ["ARM Accredited Engineer", "Embedded Linux Foundation Certifications"],
            "career_growth": [
                "Junior Firmware / Embedded Engineer (0–2 yrs): Write C/Embedded C drivers for MCUs (STM32/ESP32) and serial buses.",
                "Embedded Systems Engineer (2–5 yrs): Architect RTOS scheduling, Embedded Linux BSPs, and IoT/automotive systems.",
                "Principal Firmware Architect (5+ yrs): Lead hardware/software co-design across product families.",
                "Adjacent Paths: Firmware Engineer, Robotics Engineer, IoT Systems Architect.",
            ],
            "roadmap": [
                {"stage": 1, "title": "C, C++ & Computer Architecture", "duration": "5–6 weeks", "description": "Master pointers, bitwise registers, memory layout, and modular Embedded C/C++.", "skills": ["C", "C++", "Embedded C", "Git"]},
                {"stage": 2, "title": "Microcontrollers & Hardware Buses", "duration": "4–5 weeks", "description": "Program GPIO, interrupts, timers, and UART/SPI/I2C sensors on STM32 or ESP32.", "skills": ["Microcontrollers", "STM32", "UART", "SPI", "I2C"]},
                {"stage": 3, "title": "Real-Time Operating Systems", "duration": "4–5 weeks", "description": "Design deterministic multitasking firmware with tasks, queues, and semaphores using RTOS.", "skills": ["RTOS", "ARM Architecture"]},
                {"stage": 4, "title": "Embedded Linux & Connectivity", "duration": "4–5 weeks", "description": "Build Embedded Linux services and IoT protocols like MQTT or automotive CAN Bus.", "skills": ["Embedded Linux", "MQTT", "Python"]},
            ],
        },
        "QA/Test Engineer": {
            "jd_title": "QA Automation Engineer",
            "jr_title": "Software Test Engineer",
            "beginner_summary": "A QA/Test Engineer protects users from broken software by systematically hunting down bugs, testing edge cases, and writing code that tests applications automatically.",
            "overview": "Quality Assurance Engineers make sure software behaves reliably before customers ever see it. Modern QA blends thoughtful manual exploration with automated test scripts running on every code commit.",
            "what_they_do": "Before a product launches, QA Engineers write test plans, test APIs and SQL database state, reproduce bugs cleanly for developers, and code end-to-end automated suites using Selenium, Playwright, or Cypress.",
            "day_to_day": [
                "Review product features to write clear test plans and edge-case test scenarios.",
                "Develop automated browser tests in Selenium, Playwright, or Cypress using Python or JavaScript.",
                "Test backend REST APIs and validate underlying data state with SQL queries.",
                "Integrate automated regression suites into GitHub Actions or Jenkins CI/CD pipelines.",
                "Log reproducible bug tickets in Jira and verify fixes alongside developers.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Python", "JavaScript", "Java", "SQL"],
                "frameworks_libraries": ["Selenium", "Playwright", "Cypress", "Pytest", "JUnit", "Jest"],
                "databases_data": ["REST API", "PostgreSQL", "MySQL"],
                "tools_platforms": ["Test Automation", "Manual Testing", "Unit Testing", "Jira", "CI/CD", "Git"],
            },
            "soft_skills": ["Attention to Detail", "Critical Thinking", "Communication", "Problem Solving", "Collaboration"],
            "certifications": ["ISTQB Certified Tester Foundation Level (CTFL)", "freeCodeCamp Quality Assurance Certification"],
            "career_growth": [
                "Junior QA Analyst (0–2 yrs): Learn structured test design, manual testing, bug reporting, SQL, and basic automation.",
                "QA Automation Engineer / SDET (2–5 yrs): Architect Playwright/Selenium frameworks, API testing, and CI/CD test gates.",
                "QA Lead / Quality Engineering Manager (5+ yrs): Define org-wide release quality strategy.",
                "Adjacent Paths: Software Engineer, DevOps Engineer, Business Analyst.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Testing Foundations & Bug Tracking", "duration": "2–3 weeks", "description": "Learn SDLC testing types, test case design, defect lifecycles, Jira, and Git.", "skills": ["Manual Testing", "Jira", "Git"]},
                {"stage": 2, "title": "Programming & SQL Basics", "duration": "4 weeks", "description": "Learn Python or JavaScript scripting plus SQL queries to validate backend data.", "skills": ["Python", "JavaScript", "SQL"]},
                {"stage": 3, "title": "UI & API Test Automation", "duration": "5 weeks", "description": "Build automated browser tests with Playwright or Selenium and verify REST APIs.", "skills": ["Test Automation", "Selenium", "Playwright", "REST API"]},
                {"stage": 4, "title": "Test Frameworks & CI/CD", "duration": "3 weeks", "description": "Run Pytest or Cypress suites automatically inside CI/CD pipelines on every push.", "skills": ["Pytest", "Cypress", "CI/CD"]},
            ],
        },
        # ---- 9 New Kaggle-Derived IT Career Roles ----
        "Software Engineer": {
            "jd_title": "Software Engineer",
            "jr_title": "Software Engineer",
            "beginner_summary": "A Software Engineer applies computer science principles to design, build, test, and maintain all kinds of software—from desktop utilities to large cloud platforms.",
            "overview": "Software Engineering is the broad, foundational discipline of building reliable software systems. Engineers write maintainable code, solve algorithmic problems, test thoroughly, and collaborate on team codebases.",
            "what_they_do": "A Software Engineer takes complex user needs, breaks them into clean software components, chooses appropriate data structures and languages (Python, Java, C++, TypeScript), writes unit tests, reviews peers' code, and maintains live systems.",
            "day_to_day": [
                "Design modular application components and write clean, maintainable code.",
                "Debug complex defects across application code, APIs, and databases.",
                "Write unit and integration tests and participate in constructive Git code reviews.",
                "Collaborate with product managers and designers in Agile sprints.",
                "Document architecture decisions and improve system performance and reliability.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Python", "Java", "C++", "JavaScript", "SQL"],
                "frameworks_libraries": ["Spring Boot", "Django", "React", "Node.js", "System Design"],
                "databases_data": ["PostgreSQL", "MySQL", "Redis"],
                "tools_platforms": ["Git", "REST API", "Docker", "Unit Testing", "Linux", "Agile"],
            },
            "soft_skills": ["Problem Solving", "Communication", "Teamwork", "Analytical Thinking", "Adaptability"],
            "certifications": ["Harvard CS50x Computer Science", "AWS Certified Developer – Associate"],
            "career_growth": [
                "Associate Software Engineer (0–2 yrs): Deliver scoped features cleanly, learn Git code review and unit testing.",
                "Senior Software Engineer (3–6 yrs): Own system design, performance tuning, and mentoring junior engineers.",
                "Staff / Principal Engineer (6+ yrs): Architect multi-team systems and set technical direction.",
                "Adjacent Paths: Backend Developer, Full Stack Developer, DevOps Engineer, Engineering Manager.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Programming & Problem Solving", "duration": "5–6 weeks", "description": "Master one core language cleanly (Python or Java) along with data structures and Git.", "skills": ["Python", "Java", "Git"]},
                {"stage": 2, "title": "Databases, APIs & Testing", "duration": "4–5 weeks", "description": "Build SQL persistence, REST APIs, and automated unit tests.", "skills": ["SQL", "REST API", "Unit Testing"]},
                {"stage": 3, "title": "Architecture & System Design", "duration": "4–5 weeks", "description": "Understand caching, modular System Design, and Linux environments.", "skills": ["System Design", "Linux"]},
                {"stage": 4, "title": "Containers & Agile Delivery", "duration": "3–4 weeks", "description": "Ship software continuously using Docker, CI/CD, and Agile practices.", "skills": ["Docker", "CI/CD", "Agile"]},
            ],
        },
        "Data Engineer": {
            "jd_title": "Data & Analytics Consultant",
            "jr_title": "Data Engineer",
            "rd_title": "Data Engineer",
            "beginner_summary": "A Data Engineer builds the automated plumbing that moves, cleans, and stores massive amounts of raw data so analysts and AI models always have trustworthy information.",
            "overview": "Before Data Analysts can build dashboards or ML Engineers can train models, raw logs and app databases must be collected, cleaned, and organized. Data Engineers build those scalable ETL pipelines and cloud data warehouses.",
            "what_they_do": "A Data Engineer extracts data from production databases, APIs, and event streams (Kafka), transforms messy formats into structured analytical tables via SQL, Python, dbt, and Apache Spark, and monitors pipeline health daily.",
            "day_to_day": [
                "Design and maintain scalable ETL/ELT pipelines in Python, SQL, and Apache Spark.",
                "Model clean star-schema and analytical tables inside Snowflake, BigQuery, or PostgreSQL.",
                "Transform raw data reliably with dbt and automated data quality checks.",
                "Monitor pipeline failures, optimize slow SQL/Spark jobs, and manage cloud storage.",
                "Partner with Data Analysts and Data Scientists to deliver reliable datasets.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Python", "SQL"],
                "frameworks_libraries": ["Apache Spark", "Pandas", "Hadoop", "Kafka", "dbt"],
                "databases_data": ["Snowflake", "Google BigQuery", "PostgreSQL", "Data Warehousing", "Data Modeling"],
                "tools_platforms": ["ETL", "Docker", "AWS", "Microsoft Azure", "Git"],
            },
            "soft_skills": ["Analytical Thinking", "Problem Solving", "Communication", "Attention to Detail", "Troubleshooting"],
            "certifications": ["Google Cloud Professional Data Engineer", "AWS Certified Data Engineer – Associate", "Databricks Data Engineer Associate"],
            "career_growth": [
                "Junior Data Engineer (0–2 yrs): Write SQL/Python ETL scripts, learn data modeling and cloud warehouses.",
                "Senior Data Engineer (2–5 yrs): Architect distributed Spark/Kafka streaming pipelines and lakehouses.",
                "Staff Data Architect (5+ yrs): Own enterprise data governance and multi-petabyte platforms.",
                "Adjacent Paths: Data Scientist, ML Engineer, Analytics Engineer, Database Administrator.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Advanced SQL & Python Scripting", "duration": "4–5 weeks", "description": "Master complex SQL joins/window functions, Python file processing, Pandas, and Git.", "skills": ["SQL", "Python", "Pandas", "Git"]},
                {"stage": 2, "title": "Data Modeling & Warehousing", "duration": "4 weeks", "description": "Learn dimensional Data Modeling, ETL patterns, and cloud Data Warehousing.", "skills": ["Data Modeling", "Data Warehousing", "ETL"]},
                {"stage": 3, "title": "Big Data & Modern ELT Stack", "duration": "5–6 weeks", "description": "Process large datasets with Apache Spark and manage transformations cleanly with dbt and Snowflake.", "skills": ["Apache Spark", "dbt", "Snowflake"]},
                {"stage": 4, "title": "Streaming, Containers & Cloud", "duration": "4 weeks", "description": "Build event pipelines with Apache Kafka, package jobs in Docker, and run on AWS/Azure.", "skills": ["Apache Kafka", "Docker", "AWS"]},
            ],
        },
        "Database Administrator": {
            "jd_title": "Backend Engineer",
            "jr_title": "Database Administrator",
            "rd_title": "Database Administrator (DBA)",
            "beginner_summary": "A Database Administrator (DBA) is the guardian of a company's databases—making sure critical customer and business records stay fast, backed up, and safe from loss or breaches.",
            "overview": "Databases hold the crown jewels of every software company. DBAs specialize in installing, tuning, backing up, securing, and scaling relational and NoSQL databases so applications never lose data or stall.",
            "what_they_do": "DBAs monitor database CPU and disk health, analyze slow SQL queries and add proper indexes, test disaster-recovery backups, manage primary-replica failover clusters, and control user access permissions.",
            "day_to_day": [
                "Tune slow SQL queries, rebuild indexes, and optimize schemas for high traffic.",
                "Manage high-availability replication, clustering, and automated backup/restore tests.",
                "Monitor database performance across PostgreSQL, MySQL, SQL Server, Oracle, or MongoDB.",
                "Enforce database access permissions, auditing, and encryption policies.",
                "Assist backend teams with safe schema migrations and capacity planning.",
            ],
            "languages_frameworks_tools": {
                "languages": ["SQL", "Bash", "Python"],
                "frameworks_libraries": ["Data Modeling", "ETL"],
                "databases_data": ["PostgreSQL", "MySQL", "Microsoft SQL Server", "Oracle Database", "MongoDB", "Redis", "NoSQL"],
                "tools_platforms": ["Linux", "AWS", "Data Warehousing", "Git"],
            },
            "soft_skills": ["Attention to Detail", "Troubleshooting", "Analytical Thinking", "Communication", "Critical Thinking"],
            "certifications": ["Microsoft Certified: Azure Database Administrator Associate", "Oracle Database Administration Certified Professional", "AWS Certified Database"],
            "career_growth": [
                "Junior DBA (0–2 yrs): Manage backups, SQL tuning, user permissions, and PostgreSQL/MySQL operations.",
                "Senior DBA / Database Reliability Engineer (2–5 yrs): Lead zero-downtime sharding, multi-region failover, and cloud migrations.",
                "Data Infrastructure Architect (5+ yrs): Design enterprise-wide data persistence strategy.",
                "Adjacent Paths: Data Engineer, Backend Developer, Cloud Engineer, Site Reliability Engineer.",
            ],
            "roadmap": [
                {"stage": 1, "title": "SQL Mastery & Relational Design", "duration": "4 weeks", "description": "Learn normalization, Data Modeling, joins, transactions, and ACID guarantees.", "skills": ["SQL", "Data Modeling"]},
                {"stage": 2, "title": "Core RDBMS Administration", "duration": "5 weeks", "description": "Administer PostgreSQL, MySQL, and Microsoft SQL Server including backups and indexing.", "skills": ["PostgreSQL", "MySQL", "Microsoft SQL Server"]},
                {"stage": 3, "title": "NoSQL & Caching Systems", "duration": "3–4 weeks", "description": "Add document and in-memory database skills with MongoDB and Redis.", "skills": ["MongoDB", "Redis", "NoSQL"]},
                {"stage": 4, "title": "Linux, High Availability & Cloud", "duration": "4 weeks", "description": "Automate maintenance on Linux servers and manage scalable RDS clusters on AWS.", "skills": ["Linux", "Bash", "AWS"]},
            ],
        },
        "Cybersecurity Analyst": {
            "jd_title": "Cybersecurity Engineer",
            "jr_title": "Cybersecurity Analyst",
            "beginner_summary": "A Cybersecurity Analyst acts as a digital defender—monitoring systems for threats, spotting security weaknesses before hackers do, and protecting data and networks.",
            "overview": "Cybersecurity Analysts defend companies against data breaches, ransomware, and unauthorized access. They combine networking fundamentals with security tools to detect intrusions, assess vulnerabilities, and harden software.",
            "what_they_do": "In a Security Operations Center (SOC) or product security team, analysts inspect alerts in SIEM dashboards, scan apps and servers for known vulnerabilities, run ethical penetration tests, and respond rapidly to incidents.",
            "day_to_day": [
                "Monitor network logs and security alerts using SIEM platforms to spot suspicious activity.",
                "Run vulnerability scans and risk assessments across servers, networks, and cloud accounts.",
                "Verify firewall rules, VPN access, encryption certificates, and Linux server hardening.",
                "Conduct ethical penetration tests and review application code for common flaws (OWASP Top 10).",
                "Document incident investigations and recommend clear remediation steps to engineers.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Python", "Bash", "SQL"],
                "frameworks_libraries": ["Cybersecurity", "Network Security", "Penetration Testing"],
                "databases_data": ["SIEM", "Vulnerability Assessment", "Risk Assessment"],
                "tools_platforms": ["Linux", "TCP/IP", "Networking", "Firewalls", "Encryption", "AWS"],
            },
            "soft_skills": ["Critical Thinking", "Attention to Detail", "Troubleshooting", "Communication", "Analytical Thinking"],
            "certifications": ["Google Cybersecurity Professional Certificate", "CompTIA Security+", "Certified Ethical Hacker (CEH)"],
            "career_growth": [
                "SOC / Junior Cybersecurity Analyst (0–2 yrs): Triage security alerts, scan vulnerabilities, and monitor SIEM logs.",
                "Cybersecurity Engineer / Penetration Tester (2–5 yrs): Lead ethical hacking, cloud security architecture, and threat hunting.",
                "Principal Security Architect / CISO (5+ yrs): Direct enterprise risk and defense strategy.",
                "Adjacent Paths: Network Engineer, Cloud Security Engineer, DevSecOps Engineer.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Networking & Linux Fundamentals", "duration": "4–5 weeks", "description": "Understand TCP/IP packets, DNS, HTTP, firewalls, and Linux command-line administration.", "skills": ["Networking", "TCP/IP", "Linux"]},
                {"stage": 2, "title": "Core Security & Defense", "duration": "4–5 weeks", "description": "Learn cryptography basics, encryption, firewall hardening, and core cybersecurity threats.", "skills": ["Cybersecurity", "Network Security", "Encryption", "Firewalls"]},
                {"stage": 3, "title": "SOC Operations, SIEM & Scanning", "duration": "4–5 weeks", "description": "Detect intrusions in SIEM logs and run Vulnerability & Risk Assessments.", "skills": ["SIEM", "Vulnerability Assessment", "Risk Assessment"]},
                {"stage": 4, "title": "Penetration Testing & Scripting", "duration": "5 weeks", "description": "Automate log checks in Python/Bash and practice ethical penetration testing.", "skills": ["Penetration Testing", "Python", "AWS"]},
            ],
        },
        "Mobile Developer": {
            "jd_title": "Mobile Engineer (iOS/Android)",
            "jr_title": "Mobile Developer Android",
            "rd_title": "Senior iOS Engineer",
            "beginner_summary": "A Mobile Developer builds iPhone and Android apps—creating smooth touch interfaces, offline storage, camera/GPS features, and fast mobile experiences.",
            "overview": "Mobile Developers create apps that live in billions of pockets. Teams either build natively using Swift (iOS) and Kotlin (Android), or cross-platform apps targeting both from a single codebase with Flutter or React Native.",
            "what_they_do": "A Mobile Developer implements clean phone screens, hooks up REST APIs and push notifications, handles local offline data storage, optimizes battery/memory usage, and publishes updates to the Apple App Store and Google Play.",
            "day_to_day": [
                "Design responsive mobile UI screens using Flutter, SwiftUI, Jetpack Compose, or React Native.",
                "Connect mobile apps to backend REST APIs, authentication, and Firebase cloud services.",
                "Integrate device hardware features such as camera, GPS, biometrics, and notifications.",
                "Debug device-specific layout issues and optimize frame rates, memory, and startup speed.",
                "Write unit/UI tests and ship releases through App Store and Google Play pipelines.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Dart", "Swift", "Kotlin", "Java", "JavaScript", "Objective-C"],
                "frameworks_libraries": ["Flutter", "SwiftUI", "React Native", "Android", "iOS"],
                "databases_data": ["Firebase Firestore", "SQLite", "REST API"],
                "tools_platforms": ["Android SDK", "Xcode", "Git", "CI/CD", "Unit Testing"],
            },
            "soft_skills": ["Attention to Detail", "Problem Solving", "Collaboration", "Communication", "Adaptability"],
            "certifications": ["Meta Android / iOS Developer Professional Certificate", "Google Associate Android Developer"],
            "career_growth": [
                "Junior Mobile Developer (0–2 yrs): Build UI screens, navigation, and REST API connections in Flutter, Kotlin, or Swift.",
                "Senior Mobile Engineer (2–5 yrs): Architect offline sync, animations, native modules, and CI/CD store automation.",
                "Staff Mobile Architect (5+ yrs): Lead mobile platform standards across iOS and Android teams.",
                "Adjacent Paths: Frontend Developer, Full Stack Developer, UI/UX Designer.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Core Language & Git", "duration": "4 weeks", "description": "Master Dart (for cross-platform Flutter) or Swift/Kotlin alongside Git workflows.", "skills": ["Dart", "Swift", "Kotlin", "Git"]},
                {"stage": 2, "title": "Mobile UI & App Navigation", "duration": "5 weeks", "description": "Build multi-screen layouts and state management with Flutter, iOS SwiftUI, or Android SDK.", "skills": ["Flutter", "iOS", "Android", "Android SDK"]},
                {"stage": 3, "title": "APIs & Cloud Persistence", "duration": "4 weeks", "description": "Fetch remote data via REST APIs and sync real-time state with Firebase Firestore.", "skills": ["REST API", "Firebase Firestore"]},
                {"stage": 4, "title": "Testing, Tooling & Release", "duration": "3 weeks", "description": "Debug profiles in Xcode or Android Studio and automate builds with CI/CD.", "skills": ["Xcode", "Unit Testing", "CI/CD"]},
            ],
        },
        "UI/UX Designer": {
            "jd_title": "UX Designer (User Experience)",
            "jr_title": "UX Designer",
            "beginner_summary": "A UI/UX Designer shapes how websites and apps look and feel—researching real users, sketching easy-to-follow screens in Figma, and making technology enjoyable to use.",
            "overview": "UI/UX Design blends psychology, product thinking, and visual craft. UX (User Experience) ensures a product is logical and easy to use, while UI (User Interface) makes every screen visually clear, cohesive, and appealing.",
            "what_they_do": "Before developers write code, UI/UX Designers interview users, sketch user flows and wireframes, assemble reusable Figma component libraries, test interactive prototypes with real people, and hand off clean specifications to engineers.",
            "day_to_day": [
                "Conduct user interviews, usability tests, and competitor research to spot user friction.",
                "Map user journeys, information architecture, and low-fidelity wireframes.",
                "Craft high-fidelity, responsive screens and reusable design systems in Figma.",
                "Build clickable prototypes to test ideas rapidly before engineering begins.",
                "Collaborate closely with Frontend Developers and Product Managers during implementation.",
            ],
            "languages_frameworks_tools": {
                "languages": ["HTML5", "CSS3"],
                "frameworks_libraries": ["Responsive Design", "Tailwind CSS"],
                "databases_data": [],
                "tools_platforms": ["Figma", "UI/UX Design", "Wireframing", "Prototyping", "User Research", "Design Systems", "Agile"],
            },
            "soft_skills": ["Communication", "Collaboration", "Critical Thinking", "Attention to Detail", "Problem Solving"],
            "certifications": ["Google UX Design Professional Certificate", "Interaction Design Foundation (IxDF) Certificates"],
            "career_growth": [
                "Junior UI/UX Designer (0–2 yrs): Practice wireframing, Figma visual craft, usability testing, and portfolio case studies.",
                "Product Designer (2–5 yrs): Own end-to-end UX research, metrics-driven flows, and company Design Systems.",
                "Lead / Principal Product Designer (5+ yrs): Shape multi-product design strategy.",
                "Adjacent Paths: Frontend Developer, UX Researcher, Product Manager.",
            ],
            "roadmap": [
                {"stage": 1, "title": "UX Thinking & User Research", "duration": "3–4 weeks", "description": "Understand human-centered design, user personas, accessibility, and usability testing.", "skills": ["UI/UX Design", "User Research"]},
                {"stage": 2, "title": "Wireframing & Information Architecture", "duration": "3 weeks", "description": "Turn user needs into clear screen flows and low-fidelity wireframes.", "skills": ["Wireframing", "Responsive Design"]},
                {"stage": 3, "title": "Figma UI Craft & Prototyping", "duration": "5 weeks", "description": "Design pixel-accurate visual screens, interactive flows, and component libraries in Figma.", "skills": ["Figma", "Prototyping", "Design Systems"]},
                {"stage": 4, "title": "Developer Handoff & Web Basics", "duration": "3 weeks", "description": "Understand HTML5/CSS3 constraints and Agile sprints so designs build accurately.", "skills": ["HTML5", "CSS3", "Agile"]},
            ],
        },
        "Business Analyst": {
            "jd_title": "Data & Analytics Consultant",
            "jr_title": "Business Analyst",
            "beginner_summary": "A Business Analyst translates between business teams and tech teams—analyzing processes, querying data, writing clear requirements, and tracking project KPIs.",
            "overview": "Software projects fail when engineers build the wrong thing. Business Analysts investigate company workflows, interview stakeholders, examine SQL/Excel data, and define clear specifications that bridge business goals and software delivery.",
            "what_they_do": "On a typical project, a Business Analyst meets business leads to understand problems, checks revenue/funnel data using SQL and Power BI, writes structured user stories in Jira, and validates delivered features before launch.",
            "day_to_day": [
                "Interview stakeholders to clarify business goals, bottlenecks, and functional requirements.",
                "Document clear user stories, acceptance criteria, and workflow diagrams in Jira/Confluence.",
                "Analyze operational data with Excel, SQL, Tableau, or Power BI to back decisions with facts.",
                "Coordinate Agile sprint planning and user acceptance testing (UAT) with QA and dev teams.",
                "Track post-launch KPIs and recommend process improvements.",
            ],
            "languages_frameworks_tools": {
                "languages": ["SQL", "Python"],
                "frameworks_libraries": ["Agile", "Scrum"],
                "databases_data": ["Microsoft Excel", "PostgreSQL", "Data Modeling"],
                "tools_platforms": ["Power BI", "Tableau", "Data Analysis", "Jira", "Confluence"],
            },
            "soft_skills": ["Communication", "Analytical Thinking", "Presentation", "Problem Solving", "Collaboration"],
            "certifications": ["IIBA Entry Certificate in Business Analysis (ECBA)", "Google Data Analytics Certificate", "Certified Scrum Product Owner (CSPO)"],
            "career_growth": [
                "Junior Business Analyst (0–2 yrs): Document user stories, map processes, analyze Excel/SQL data, and join Agile rituals.",
                "Senior Business Systems Analyst (2–5 yrs): Lead complex domain modeling, BI KPI design, and cross-team roadmaps.",
                "Product Manager / Lead Consultant (5+ yrs): Own product vision and business outcomes.",
                "Adjacent Paths: Data Analyst, Product Manager, Scrum Master, Technology Consultant.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Excel & Analytical Problem Solving", "duration": "3 weeks", "description": "Master business KPI modeling, pivot analysis, and structured process mapping.", "skills": ["Microsoft Excel", "Data Analysis"]},
                {"stage": 2, "title": "SQL & Data Modeling", "duration": "4 weeks", "description": "Pull data independently with SQL and understand relational Data Modeling.", "skills": ["SQL", "Data Modeling"]},
                {"stage": 3, "title": "Agile Requirements & Jira", "duration": "3 weeks", "description": "Write crisp Agile user stories, manage backlogs in Jira, and document in Confluence.", "skills": ["Agile", "Scrum", "Jira", "Confluence"]},
                {"stage": 4, "title": "BI Reporting & Dashboards", "duration": "4 weeks", "description": "Communicate insights to leadership cleanly with Power BI and Tableau.", "skills": ["Power BI", "Tableau"]},
            ],
        },
        "Network Engineer": {
            "jd_title": "Network Engineer",
            "jr_title": "Network Engineer",
            "rd_title": "Network Support Engineer",
            "beginner_summary": "A Network Engineer designs and keeps computer networks running—routers, switches, Wi-Fi, VPNs, and cloud connections that let every computer talk securely.",
            "overview": "Without reliable networking, no website, cloud server, or office can function. Network Engineers architect physical and cloud networks, configure routers and firewalls, and quickly diagnose connectivity bottlenecks.",
            "what_they_do": "A Network Engineer plans IP addressing and subnets, configures Cisco switches and routing protocols, enforces firewall and VPN security policies, monitors packet loss, and automates repetitive network updates with Python.",
            "day_to_day": [
                "Configure routers, switches, VLANs, VPN gateways, and wireless infrastructure.",
                "Monitor bandwidth, latency, and packet health and resolve outage alerts quickly.",
                "Implement firewall rules, access control lists, and network segmentation.",
                "Support DNS, DHCP, TCP/IP routing, and hybrid connectivity to AWS/Azure cloud VPCs.",
                "Document network topology diagrams and automate device backups using Python or Linux scripts.",
            ],
            "languages_frameworks_tools": {
                "languages": ["Python", "Bash"],
                "frameworks_libraries": ["Ansible"],
                "databases_data": [],
                "tools_platforms": ["Networking", "TCP/IP", "Cisco", "Firewalls", "Network Security", "Linux", "AWS"],
            },
            "soft_skills": ["Troubleshooting", "Analytical Thinking", "Communication", "Attention to Detail", "Teamwork"],
            "certifications": ["Cisco Certified Network Associate (CCNA)", "CompTIA Network+", "AWS Certified Advanced Networking"],
            "career_growth": [
                "Network Support / NOC Technician (0–2 yrs): Troubleshoot connectivity, subnetting, switch ports, and basic Cisco/Linux configs.",
                "Network Engineer (2–5 yrs): Design enterprise routing, firewall policies, and cloud VPC architectures.",
                "Network Architect / Cloud Networking Lead (5+ yrs): Lead automated global network engineering.",
                "Adjacent Paths: Cybersecurity Analyst, Cloud Engineer, Systems Administrator.",
            ],
            "roadmap": [
                {"stage": 1, "title": "TCP/IP & Networking Foundations", "duration": "4 weeks", "description": "Master the OSI model, IPv4/IPv6 subnetting, DNS, DHCP, and packet troubleshooting.", "skills": ["Networking", "TCP/IP"]},
                {"stage": 2, "title": "Routing, Switching & Linux", "duration": "5 weeks", "description": "Configure VLANs, OSPF/BGP concepts, Cisco IOS CLI, and Linux network diagnostics.", "skills": ["Cisco", "Linux"]},
                {"stage": 3, "title": "Network Security & Firewalls", "duration": "4 weeks", "description": "Implement firewalls, VPN tunnels, ACLs, and perimeter Network Security controls.", "skills": ["Firewalls", "Network Security"]},
                {"stage": 4, "title": "Automation & Cloud Networking", "duration": "4 weeks", "description": "Automate network tasks with Python/Ansible and connect on-prem networks to AWS VPCs.", "skills": ["Python", "Ansible", "AWS"]},
            ],
        },
        "PHP Developer": {
            "jr_title": "PHP Developer",
            "beginner_summary": "A PHP Developer builds dynamic websites, e-commerce stores, and content-driven web backends using PHP, Laravel, WordPress, and MySQL.",
            "overview": "PHP powers a huge share of the web—including WordPress sites and thousands of modern SaaS applications built with Laravel and Symfony. PHP Developers ship practical database-driven web products rapidly.",
            "what_they_do": "A PHP Developer writes server-side PHP logic, builds clean MVC apps with Laravel, creates REST APIs, designs MySQL tables, and styles interactive pages using HTML5, CSS3, and JavaScript.",
            "day_to_day": [
                "Develop web applications, plugins, and backend APIs in modern PHP and Laravel/Symfony.",
                "Design and optimize MySQL databases and Eloquent ORM queries.",
                "Build responsive frontend views integrating HTML5, CSS3, and JavaScript.",
                "Customize WordPress themes/plugins or build bespoke Laravel dashboards.",
                "Write tests, debug server logs, and manage deployments via Git and Docker.",
            ],
            "languages_frameworks_tools": {
                "languages": ["PHP", "JavaScript", "HTML5", "CSS3", "SQL"],
                "frameworks_libraries": ["Laravel", "Symfony", "jQuery", "WordPress", "Responsive Design"],
                "databases_data": ["MySQL", "PostgreSQL", "Redis"],
                "tools_platforms": ["Git", "REST API", "Docker", "Linux"],
            },
            "soft_skills": ["Problem Solving", "Communication", "Attention to Detail", "Time Management", "Collaboration"],
            "certifications": ["Laravel Certification", "Zend Certified PHP Engineer"],
            "career_growth": [
                "Junior PHP Developer (0–2 yrs): Build web pages, WordPress sites, and MySQL CRUD features in PHP.",
                "Laravel / Full-Stack PHP Engineer (2–5 yrs): Architect APIs, queues, caching, and Laravel SaaS backends.",
                "Senior Web Architect (5+ yrs): Lead high-traffic PHP platforms and full-stack teams.",
                "Adjacent Paths: Full Stack Developer, Backend Developer, WordPress Architect.",
            ],
            "roadmap": [
                {"stage": 1, "title": "Web Frontend Basics & Git", "duration": "3–4 weeks", "description": "Learn HTML5, CSS3, JavaScript fundamentals, and Git version control.", "skills": ["HTML5", "CSS3", "JavaScript", "Git"]},
                {"stage": 2, "title": "Core PHP & MySQL", "duration": "4–5 weeks", "description": "Master OOP PHP, forms/sessions, and relational database queries with MySQL.", "skills": ["PHP", "MySQL", "SQL"]},
                {"stage": 3, "title": "Laravel & WordPress Development", "duration": "5 weeks", "description": "Build modern MVC backends and REST APIs with Laravel and customize WordPress.", "skills": ["Laravel", "WordPress", "REST API"]},
                {"stage": 4, "title": "Deployment & Scaling", "duration": "3 weeks", "description": "Containerize and run PHP apps cleanly with Docker, Linux, and Redis caching.", "skills": ["Docker", "Linux", "Redis"]},
            ],
        },
    }

    roles_info: Dict[str, dict] = {}
    for title, spec in role_specs.items():
        role_df = jobs_df[jobs_df["title"] == title]
        jd_row = jd_lookup(spec.get("jd_title", ""))
        jr_row = jr_lookup(spec.get("jr_title", ""))
        rd_bullets = rd_resp(spec["rd_title"]) if spec.get("rd_title") else []

        # Aggregate canonical required & preferred skills seen in jobs_df for this role
        req_counts: Dict[str, int] = {}
        for lst in role_df["required_skills"]:
            items = [x.strip() for x in lst.split("|") if x.strip()] if isinstance(lst, str) else list(lst or [])
            for s in items:
                req_counts[s] = req_counts.get(s, 0) + 1
        top_req = [s for s, _ in sorted(req_counts.items(), key=lambda kv: (-kv[1], kv[0]))]

        # Qualifications from job_roles.csv + job_description.csv
        edu_req = str(jr_row.get("Education Requirement", "")).replace("|", " or ") if jr_row is not None else "Bachelor's degree in Computer Science, IT, or equivalent practical portfolio"
        exp_years = int(jr_row.get("Experience Years", 1)) if jr_row is not None and pd.notna(jr_row.get("Experience Years")) else 1
        salary_range = str(jr_row.get("Salary Range", "Competitive entry-to-mid range")) if jr_row is not None else "Competitive entry-to-mid range"
        if "$" not in salary_range and salary_range and salary_range[0].isdigit():
            salary_range = "$" + salary_range

        jd_qual_bullets = _split_br_bullets(str(jd_row.get("Required Skills & Qualifications", ""))) if jd_row is not None else []
        jd_resp_bullets = _split_br_bullets(str(jd_row.get("Key Responsibilities", ""))) if jd_row is not None else []

        # Merge responsibilities cleanly (Kaggle job_description + resume_data + curated)
        day_to_day = list(spec["day_to_day"])
        if jd_resp_bullets:
            # Put unique clean Kaggle bullets in day_to_day first if not redundant
            merged_resp = []
            seen_lower = set()
            for b in jd_resp_bullets + day_to_day + rd_bullets:
                norm = b.lower()[:40]
                if norm not in seen_lower and len(b) > 15:
                    seen_lower.add(norm)
                    merged_resp.append(b)
            day_to_day = merged_resp[:6]

        sources = sorted(set(role_df["source_dataset"].tolist())) if "source_dataset" in role_df.columns else []
        if jd_row is not None:
            sources.append("Kaggle job_description.csv")
        if jr_row is not None:
            sources.append("Kaggle job_roles.csv")
        if rd_bullets:
            sources.append("Kaggle resume_data.csv")
        sources = sorted(set(sources))

        category = str(role_df.iloc[0]["category"]) if not role_df.empty else "Technology"

        roles_info[title] = {
            "title": title,
            "slug": _slugify(title),
            "category": category,
            "beginner_summary": spec["beginner_summary"],
            "overview": spec["overview"],
            "what_they_do": spec["what_they_do"],
            "day_to_day_responsibilities": day_to_day,
            "technical_skills": {
                "core_skills": top_req[:10],
                "languages_frameworks_tools": spec["languages_frameworks_tools"],
            },
            "soft_skills": spec["soft_skills"],
            "qualifications": {
                "education": edu_req,
                "typical_experience": f"0–{max(2, exp_years)} years for entry/junior; varies by seniority",
                "salary_benchmark": f"{salary_range} (US benchmark from Kaggle job_roles.csv)",
                "expectations": jd_qual_bullets[:4] if jd_qual_bullets else [
                    f"Solid grasp of core stack ({', '.join(top_req[:4])})",
                    "Portfolio of practical projects or GitHub repositories",
                    "Comfort collaborating with Git and writing clean code/docs",
                ],
                "helpful_certifications": spec["certifications"],
            },
            "career_growth": spec["career_growth"],
            "learning_roadmap": spec["roadmap"],
            "data_sources": sources,
        }

    with open(DATA_DIR / "job_roles_info.json", "w", encoding="utf-8") as f:
        json.dump(roles_info, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"[job_roles_info.json] Generated beginner-friendly profiles & roadmaps for {len(roles_info)} roles.")
    return roles_info


def main() -> None:
    skill_lookup = update_skills_taxonomy()
    jobs_df = build_jobs_dataset(skill_lookup)
    build_job_roles_info(jobs_df)
    print("All Kaggle datasets integrated cleanly.")


if __name__ == "__main__":
    main()
