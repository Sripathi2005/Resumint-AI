"""
Recommender Module.

Provides functions to:
- Compute prioritized skill gaps for target jobs based on dataset-wide demand.
- Build structured learning roadmaps with curated platforms, official tutorials,
  key topics to master, and portfolio project ideas.
"""

from collections import Counter
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from modules.job_matcher import load_skill_implications


def get_skill_gap(
    resume_skills: List[str],
    job_row: Union[pd.Series, Dict[str, Any], str],
    jobs_df: Optional[pd.DataFrame] = None,
) -> List[str]:
    """
    Calculate missing required skills for a target job, sorted by how many jobs
    in the dataset require each skill (most in-demand skills first).

    Args:
        resume_skills: List of skills detected in candidate resume.
        job_row: Target job posting (pd.Series, Dict, or job_id string).
        jobs_df: Optional DataFrame of all jobs to compute market-wide demand.

    Returns:
        List of missing skill names sorted descending by demand frequency.
    """
    if isinstance(job_row, str):
        if jobs_df is not None:
            matching = jobs_df[jobs_df["job_id"] == job_row]
            if not matching.empty:
                job_row = matching.iloc[0]
            else:
                matching_title = jobs_df[jobs_df["title"].str.lower() == job_row.lower()]
                if not matching_title.empty:
                    job_row = matching_title.iloc[0]
                else:
                    return []
        else:
            return []

    req_skills = job_row.get("required_skills", [])
    if isinstance(req_skills, str):
        req_skills = [s.strip() for s in req_skills.split("|") if s.strip()]

    implications = load_skill_implications()
    expanded_skills = set(resume_skills)
    for sk in resume_skills:
        expanded_skills.update(implications.get(sk, []))

    missing = [s for s in req_skills if s not in expanded_skills]

    if not missing:
        return []

    # If jobs_df is provided, calculate market demand frequency
    if jobs_df is not None and not jobs_df.empty:
        demand_counter: Counter = Counter()
        for _, row in jobs_df.iterrows():
            skills = row.get("required_skills", [])
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split("|") if s.strip()]
            demand_counter.update(skills)

        # Sort by demand count descending, then alphabetically
        missing.sort(key=lambda s: (-demand_counter[s], s))
    else:
        missing.sort()

    return missing


def load_learning_resources(path: Optional[Union[str, Path]] = None) -> Dict[str, Dict[str, Any]]:
    """Load curated learning resources from skill_learning_resources.json."""
    if path is None:
        path = Path(__file__).resolve().parent.parent / "data" / "skill_learning_resources.json"
    else:
        path = Path(path)

    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "skills" in data and isinstance(data["skills"], dict):
                    return data["skills"]
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _fallback_resources(skill: str, category: str) -> List[Dict[str, str]]:
    """Provide curated non-fake category learning portals when a rare skill lacks a custom entry."""
    cat_defaults = {
        "languages": [
            {
                "platform": "freeCodeCamp",
                "title": f"{skill} & Core Programming Foundations",
                "description": "Free interactive coding curriculum strengthening language syntax and algorithms.",
                "url": "https://www.freecodecamp.org/learn",
                "cost": "Free",
            },
            {
                "platform": "roadmap.sh",
                "title": "Software Engineering Learning Paths",
                "description": "Step-by-step developer paths and reference documentation.",
                "url": "https://roadmap.sh/",
                "cost": "Free",
            },
        ],
        "databases": [
            {
                "platform": "freeCodeCamp",
                "title": "Relational Database & Data Modeling Track",
                "description": f"Free hands-on SQL and schema design foundations supporting {skill}.",
                "url": "https://www.freecodecamp.org/learn/relational-database/",
                "cost": "Free",
            },
            {
                "platform": "roadmap.sh",
                "title": "Database Engineering Roadmap",
                "description": "Guided milestones for indexing, queries, and storage concepts.",
                "url": "https://roadmap.sh/postgresql-dba",
                "cost": "Free",
            },
        ],
        "cloud": [
            {
                "platform": "AWS Skill Builder",
                "title": "Cloud & Infrastructure Digital Training",
                "description": f"Free cloud fundamentals and architecture tracks relevant to {skill}.",
                "url": "https://explore.skillbuilder.aws",
                "cost": "Free",
            },
            {
                "platform": "Microsoft Learn",
                "title": "Microsoft Cloud Training Paths",
                "description": "Free self-paced modules covering cloud infrastructure and operations.",
                "url": "https://learn.microsoft.com/en-us/training/",
                "cost": "Free",
            },
        ],
        "AI/ML": [
            {
                "platform": "Kaggle Learn",
                "title": "Data Science & Machine Learning Micro-Courses",
                "description": f"Hands-on Python, SQL, Pandas, and ML notebooks supporting {skill}.",
                "url": "https://www.kaggle.com/learn",
                "cost": "Free",
            },
            {
                "platform": "roadmap.sh",
                "title": "AI & Data Scientist Roadmap",
                "description": "Curated step-by-step progression through analytics and ML modeling.",
                "url": "https://roadmap.sh/ai-and-data-scientist",
                "cost": "Free",
            },
        ],
        "web": [
            {
                "platform": "MDN Web Docs",
                "title": "Learn Web Development Guides",
                "description": f"Mozilla's comprehensive web technology tutorials relevant to {skill}.",
                "url": "https://developer.mozilla.org/en-US/docs/Learn",
                "cost": "Free",
            },
            {
                "platform": "freeCodeCamp",
                "title": "Responsive Web Design & Frontend Libraries",
                "description": "Project-based interactive lessons on modern web interfaces.",
                "url": "https://www.freecodecamp.org/learn/responsive-web-design/",
                "cost": "Free",
            },
        ],
    }
    return cat_defaults.get(
        category,
        [
            {
                "platform": "roadmap.sh",
                "title": f"{skill} & Engineering Learning Paths",
                "description": f"Structured developer roadmaps and curated references covering {skill}.",
                "url": "https://roadmap.sh/",
                "cost": "Free",
            },
            {
                "platform": "Microsoft Learn",
                "title": "Developer & IT Skills Training Portal",
                "description": "Free self-paced engineering, cloud, and tooling learning modules.",
                "url": "https://learn.microsoft.com/en-us/training/",
                "cost": "Free",
            },
        ],
    )


def _load_skill_categories(skills_path: Optional[Union[str, Path]] = None) -> Dict[str, str]:
    if skills_path is None:
        skills_path = Path(__file__).resolve().parent.parent / "data" / "skills.json"
    else:
        skills_path = Path(skills_path)

    category_map: Dict[str, str] = {}
    if skills_path.is_file():
        try:
            with open(skills_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for s in data.get("skills", []):
                category_map[s["name"].lower()] = s.get("category", "General")
        except Exception:
            pass
    return category_map


_SKILL_SUMMARIES: Dict[str, str] = {
    "Python": "A versatile, readable programming language widely used for web backends, APIs, automation, and data engineering.",
    "JavaScript": "The core programming language of the web used to build interactive browser interfaces and Node.js backend services.",
    "TypeScript": "A strongly typed superset of JavaScript that catches bugs early and scales large frontend and backend codebases.",
    "Java": "A fast, strongly typed object-oriented language widely adopted for enterprise backend services, Android apps, and microservices.",
    "Go": "A compiled systems and backend language designed by Google for high concurrency, cloud tooling, and fast microservices.",
    "SQL": "Structured Query Language—the standard way to query, filter, join, and manage data inside relational databases.",
    "PostgreSQL": "An enterprise-grade open-source relational database known for reliability, complex SQL queries, indexing, and JSON support.",
    "MySQL": "One of the most widely deployed open-source relational databases powering web backends and SaaS applications.",
    "MongoDB": "A popular NoSQL document database storing flexible JSON-like records instead of rigid SQL table rows.",
    "Redis": "An ultra-fast in-memory data store used for API caching, user sessions, rate limiting, and background queues.",
    "NoSQL": "Non-relational databases designed for flexible schemas, horizontal scaling, and high-throughput unstructured or document data.",
    "Node.js": "A runtime environment allowing developers to execute JavaScript on the server side to build scalable network APIs.",
    "Express.js": "A minimalist, fast Node.js web framework used to define API routes, middleware, and server-side request handling.",
    "Django": "A full-featured Python web framework providing ORM database models, authentication, admin tools, and REST APIs out of the box.",
    "Flask": "A lightweight Python micro-framework ideal for building clean REST APIs and modular web services.",
    "FastAPI": "A modern high-performance Python API framework with automatic data validation and OpenAPI interactive docs.",
    "Spring Boot": "A widely used Java framework that simplifies building production-ready microservices and enterprise REST APIs.",
    "Hibernate": "A Java Object-Relational Mapping (ORM) library that maps Java classes directly to relational database tables.",
    "React": "A component-based JavaScript library created by Meta for building responsive, stateful single-page web interfaces.",
    "Angular": "A full-featured TypeScript frontend framework with built-in routing, dependency injection, and form validation.",
    "Vue.js": "An approachable progressive JavaScript framework for building reactive user interfaces and single-page applications.",
    "Next.js": "A full-stack React framework adding server-side rendering, file-based routing, and production performance optimizations.",
    "HTML5": "The standard markup language defining headings, forms, semantic structure, and accessibility on web pages.",
    "CSS3": "Cascading Style Sheets controlling visual layout, Flexbox/Grid positioning, typography, and responsive mobile design.",
    "Tailwind CSS": "A utility-first CSS framework enabling rapid custom UI styling directly inside HTML/JSX markup.",
    "REST API": "Representational State Transfer APIs—standard HTTP endpoints (GET, POST, PUT, DELETE) allowing clients and servers to exchange JSON data.",
    "GraphQL": "A flexible API query language letting frontend clients request the exact fields they need from a single endpoint.",
    "Git": "Distributed version control system used by software teams to track code history, branch features, and collaborate via pull requests.",
    "GitHub": "Cloud platform hosting Git repositories with pull requests, code reviews, issue tracking, and CI/CD automation.",
    "Docker": "A containerization tool that packages an app, libraries, and runtime together so it runs identically on any laptop or server.",
    "Kubernetes": "An automated container orchestration system for deploying, scaling, and healing multi-container cloud workloads.",
    "Microservices": "An architectural style breaking large backends into small, independently deployable services communicating via APIs or events.",
    "System Design": "Designing scalable software architecture covering caching, load balancing, database partitioning, queues, and fault tolerance.",
    "AWS": "Amazon Web Services—the largest public cloud platform offering managed compute, storage, databases, networking, and IAM security.",
    "Microsoft Azure": "Microsoft's public cloud platform widely used in enterprise web apps, Active Directory identity, and analytics pipelines.",
    "Google Cloud Platform": "Google's cloud suite known for Kubernetes Engine, BigQuery analytics, Cloud Run, and AI infrastructure.",
    "CI/CD": "Continuous Integration and Continuous Delivery pipelines that automatically test and deploy code changes safely.",
    "GitHub Actions": "Native automation tool inside GitHub repositories used to run automated tests, linters, Docker builds, and deployments.",
    "Jenkins": "A widely used open-source automation server for orchestrating custom build, test, and deployment pipelines.",
    "Terraform": "Infrastructure as Code (IaC) tool allowing teams to declare cloud servers, networks, and permissions in versioned files.",
    "Ansible": "Agentless IT automation tool used to configure servers, deploy software, and keep environments consistent.",
    "Linux": "The dominant operating system running cloud servers, Docker containers, developer tooling, and production backends.",
    "Bash": "Unix shell scripting language used to automate Linux server administration, file processing, and deployment workflows.",
    "Machine Learning": "Statistical algorithms that learn patterns from historical data to make predictions, classifications, or recommendations.",
    "Deep Learning": "Multi-layer neural network techniques powering computer vision, speech recognition, and modern language models.",
    "Scikit-Learn": "Python's foundational library for classical machine learning models, preprocessing pipelines, and model evaluation.",
    "TensorFlow": "Google's open-source end-to-end framework for training and deploying deep neural networks at scale.",
    "PyTorch": "A flexible deep learning framework favored across AI research and production NLP/vision systems.",
    "Pandas": "Python's essential tabular data manipulation library for cleaning, filtering, grouping, and analyzing datasets.",
    "NumPy": "Foundational Python numerical computing library providing fast multi-dimensional arrays and linear algebra operations.",
    "Statistics": "Probability distributions, hypothesis testing, confidence intervals, and A/B testing foundations for data decisions.",
    "Data Analysis": "Inspecting, cleaning, transforming, and interpreting raw datasets to answer business or product questions.",
    "Data Visualization": "Turning numeric trends into clear charts and executive dashboards so teams can spot patterns immediately.",
    "Power BI": "Microsoft's business intelligence tool for building interactive KPI dashboards and connecting enterprise data sources.",
    "Tableau": "Visual analytics platform used to turn complex datasets into interactive business dashboards and stories.",
    "Microsoft Excel": "Industry-standard spreadsheet software for pivot tables, XLOOKUP modeling, financial summaries, and quick data analysis.",
    "Natural Language Processing": "Techniques enabling software to understand, classify, summarize, and generate human text.",
    "Pytest": "Modern Python testing framework used to write clean automated unit tests, fixtures, and API test suites.",
    "JUnit": "The standard unit-testing framework in the Java ecosystem for verifying methods, services, and regression safety.",
    "Jest": "Fast JavaScript testing framework commonly used for unit tests and React/Node component testing.",
    "Selenium": "Browser automation framework used by QA engineers to automate end-to-end web UI regression tests.",
    "Playwright": "Modern cross-browser end-to-end testing framework engineered for fast, reliable automated UI verification.",
    "Cypress": "JavaScript-focused end-to-end testing framework providing interactive time-travel debugging for modern web apps.",
    "Agile": "Iterative software delivery methodology centered on short sprints, continuous feedback, and cross-functional teamwork.",
    "Scrum": "A structured Agile framework defining sprint planning, standups, retrospectives, and Product Owner / Scrum Master roles.",
    "Jira": "Issue-tracking and project management tool software teams use to plan sprints, bugs, and feature backlogs.",
    "Figma": "Collaborative browser-based design tool used to create wireframes, design systems, interactive prototypes, and developer handoffs.",
    "Network Security": "Defending networks, servers, and cloud environments against unauthorized access, exploits, and data breaches.",
    "Cybersecurity": "Protecting systems, APIs, identities, and sensitive data from threats, vulnerabilities, and cyberattacks.",
    "Unit Testing": "Writing automated tests for small code functions/modules to verify behavior and catch regressions before release.",
    "Apache Kafka": "Distributed event-streaming platform used to process real-time logs, telemetry, and microservice messages at high scale.",
}


def _explain_skill_for_role(
    skill: str,
    category: str,
    topics: str,
    role_title: Optional[str] = None,
    role_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Generate beginner-friendly explanations of what a missing skill is
    and why it matters specifically for the target career role.
    """
    cat_intros = {
        "languages": f"{skill} is a programming or query language used to express logic, handle data, and build reliable software components.",
        "frameworks": f"{skill} is a development framework or library providing prebuilt structure, APIs, and reusable patterns to ship features faster.",
        "databases": f"{skill} is a data storage or caching technology used to persist records reliably and retrieve data quickly.",
        "web": f"{skill} is a core web technology responsible for structuring content, styling interfaces, or enabling browser/server communication.",
        "cloud": f"{skill} is a cloud or infrastructure platform for hosting, automating, containerizing, and scaling software in production.",
        "tools": f"{skill} is an engineering workflow or quality tool teams use for version control, testing, automation, monitoring, or collaboration.",
        "AI/ML": f"{skill} is an analytics, statistical, or machine learning capability used to extract insights and build predictive models.",
        "embedded": f"{skill} is a low-level hardware, microcontroller, firmware, or communication protocol skill for connected physical devices.",
    }
    what_it_is = _SKILL_SUMMARIES.get(skill) or cat_intros.get(
        category,
        f"{skill} is a specialized competency ({category}) focused on {topics}.",
    )

    role_label = (role_info or {}).get("title") or role_title or "this technical role"
    cat_role_reasons = {
        "languages": f"In a {role_label} role, fluency in {skill} is foundational for implementing daily features, solving technical problems, and maintaining team codebases.",
        "frameworks": f"Employers hiring {role_label}s expect hands-on experience with {skill} because real-world projects rely on its architecture rather than building everything from scratch.",
        "databases": f"{role_label}s depend on {skill} to store application or analytical data cleanly, prevent bottlenecks, and keep queries fast under real usage.",
        "web": f"Mastering {skill} helps a {role_label} build standards-compliant, responsive interfaces or seamless client-server interactions.",
        "cloud": f"Modern {role_label} teams deploy and operate applications using {skill} so systems stay scalable, automated, and reliable in production.",
        "tools": f"Using {skill} effectively lets a {role_label} ship tested changes safely, collaborate smoothly with engineers, and debug issues quickly.",
        "AI/ML": f"For a {role_label}, {skill} bridges raw data and actionable decisions—enabling accurate modeling, evaluation, and measurable impact.",
        "embedded": f"{role_label}s rely on {skill} to interact directly with sensors, microcontrollers, timing constraints, and real hardware devices.",
    }
    why_important = cat_role_reasons.get(
        category,
        f"Demonstrating {skill} strengthens your readiness for {role_label} interviews and directly maps to core job description expectations ({topics}).",
    )
    return {"what_it_is": what_it_is, "why_important": why_important}


def learning_checklist(
    missing_skills: List[str],
    skills_path: Optional[Union[str, Path]] = None,
    resources_path: Optional[Union[str, Path]] = None,
    role_title: Optional[str] = None,
    role_info: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Generate an actionable learning checklist for missing skills, attaching
    canonical taxonomy categories, plain-English explanations (what it is & why
    it matters for the target role), 2-3 verified learning platform resources,
    key topics to master, and portfolio project suggestions.
    """
    if not missing_skills:
        return []

    category_map = _load_skill_categories(skills_path)
    resources_db = load_learning_resources(resources_path)

    checklist = []
    for skill in missing_skills:
        cat = category_map.get(skill.lower(), "General")
        res = resources_db.get(skill, {})
        res_list = res.get("resources") if isinstance(res.get("resources"), list) and res.get("resources") else None

        if not res_list:
            if res.get("url") and res.get("platform"):
                res_list = [
                    {
                        "platform": res["platform"],
                        "title": f"{skill} Guided Resource",
                        "description": res.get("topics", f"Learn core {skill} fundamentals."),
                        "url": res["url"],
                        "cost": "Free",
                    }
                ] + _fallback_resources(skill, cat)[:1]
            else:
                res_list = _fallback_resources(skill, cat)

        primary = res_list[0]
        platform = res.get("platform") or " / ".join(r["platform"] for r in res_list[:2])
        url = res.get("url") or primary["url"]
        topics = res.get("topics", f"Core syntax, standard architecture, and industry best practices in {skill}")
        project = res.get("project", f"Build a practical demo application integrating {skill} to showcase on your resume")
        est_time = res.get("est_time", "1-2 weeks")
        expl = _explain_skill_for_role(skill, cat, topics, role_title=role_title, role_info=role_info)

        checklist.append({
            "skill": skill,
            "category": cat,
            "platform": platform,
            "url": url,
            "topics": topics,
            "project": project,
            "est_time": est_time,
            "what_it_is": expl["what_it_is"],
            "why_important": expl["why_important"],
            "resources": res_list[:3],
        })

    return checklist


def load_job_roles_info(path: Optional[Union[str, Path]] = None) -> Dict[str, Dict[str, Any]]:
    """Load structured role information and sequential roadmaps from data/job_roles_info.json."""
    if path is None:
        path = Path(__file__).resolve().parent.parent / "data" / "job_roles_info.json"
    else:
        path = Path(path)

    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def get_role_info(role_identifier: str, path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Find a role profile by exact title, case-insensitive title, or URL slug."""
    roles = load_job_roles_info(path)
    if not role_identifier:
        return None
    if role_identifier in roles:
        return roles[role_identifier]
    norm = role_identifier.strip().lower()
    for title, info in roles.items():
        if title.lower() == norm or str(info.get("slug", "")).lower() == norm:
            return info
    return None


def generate_career_roadmap(
    role_title: str,
    detected_skills: Optional[List[str]] = None,
    detected_soft_skills: Optional[List[str]] = None,
    skills_path: Optional[Union[str, Path]] = None,
    resources_path: Optional[Union[str, Path]] = None,
    roles_info_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Build a personalized, sequential career roadmap for a chosen job role.

    Each stage shows ordered skills marked as 'known' (directly detected or
    satisfied via skill implications) or 'missing', and attaches 2-3 verified
    learning platform recommendations to every missing skill.
    """
    role_info = get_role_info(role_title, path=roles_info_path)
    if not role_info:
        return None

    detected_list = list(detected_skills or [])
    direct_set = set(detected_list)
    implications = load_skill_implications()

    # Track direct matches vs implied matches so UI can explain e.g. SQL (via PostgreSQL)
    implied_by: Dict[str, str] = {}
    for sk in detected_list:
        for parent in implications.get(sk, []):
            if parent not in direct_set and parent not in implied_by:
                implied_by[parent] = sk

    category_map = _load_skill_categories(skills_path)
    resources_db = load_learning_resources(resources_path)

    raw_stages = sorted(role_info.get("learning_roadmap", []), key=lambda s: int(s.get("stage", 0)))
    personalized_stages = []
    total_skills = 0
    known_skills_count = 0
    missing_skill_names: List[str] = []
    next_recommended_stage = None

    for stage in raw_stages:
        stage_skills = []
        stage_known = 0
        for sk in stage.get("skills", []):
            total_skills += 1
            if sk in direct_set:
                status = "known"
                matched_via = None
                known_skills_count += 1
                stage_known += 1
            elif sk in implied_by:
                status = "known"
                matched_via = implied_by[sk]
                known_skills_count += 1
                stage_known += 1
            else:
                status = "missing"
                matched_via = None
                if sk not in missing_skill_names:
                    missing_skill_names.append(sk)

            cat = category_map.get(sk.lower(), "General")
            res = resources_db.get(sk, {})
            res_list = res.get("resources") if isinstance(res.get("resources"), list) and res.get("resources") else _fallback_resources(sk, cat)
            topics = res.get("topics", f"Core concepts and hands-on workflow in {sk}")
            expl = _explain_skill_for_role(sk, cat, topics, role_title=role_info["title"], role_info=role_info)

            stage_skills.append({
                "name": sk,
                "category": cat,
                "status": status,
                "matched_via": matched_via,
                "est_time": res.get("est_time", "1-2 weeks"),
                "topics": topics,
                "what_it_is": expl["what_it_is"],
                "why_important": expl["why_important"],
                "project": res.get("project", f"Build a practical mini-project using {sk}"),
                "resources": res_list[:3],
            })

        st_total = len(stage_skills)
        pct = round((stage_known / st_total) * 100) if st_total > 0 else 0
        st_num = stage.get("stage")
        st_title = stage.get("title", "")
        if st_total > 0 and stage_known == st_total:
            stage_status = "Completed"
        elif stage_known > 0 or (next_recommended_stage is None):
            stage_status = "In Progress"
            if next_recommended_stage is None and stage_known < st_total:
                next_recommended_stage = f"Stage {st_num}: {st_title}"
        else:
            stage_status = "Upcoming"

        if next_recommended_stage is None and stage_status != "Completed":
            next_recommended_stage = f"Stage {st_num}: {st_title}"

        personalized_stages.append({
            "stage": stage.get("stage"),
            "title": stage.get("title", ""),
            "duration": stage.get("duration", ""),
            "description": stage.get("description", ""),
            "known_count": stage_known,
            "total_count": st_total,
            "progress_pct": pct,
            "stage_status": stage_status,
            "skills": stage_skills,
        })

    readiness_pct = round((known_skills_count / total_skills) * 100) if total_skills > 0 else 0

    role_soft = role_info.get("soft_skills", [])
    user_soft_set = {s.lower() for s in (detected_soft_skills or [])}
    soft_breakdown = [
        {"name": s, "known": s.lower() in user_soft_set}
        for s in role_soft
    ]

    return {
        "role_title": role_info["title"],
        "slug": role_info.get("slug", ""),
        "category": role_info.get("category", ""),
        "total_skills": total_skills,
        "known_skills_count": known_skills_count,
        "missing_skills_count": max(0, total_skills - known_skills_count),
        "missing_skills": missing_skill_names,
        "readiness_pct": readiness_pct,
        "recommended_next_stage": next_recommended_stage,
        "stages": personalized_stages,
        "soft_skills": soft_breakdown,
    }
