# Resumint AI 🚀
### AI-Powered Resume Analyzer, Job Recommendation & Career-Readiness Platform

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.x-black?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![scikit-learn](https://img.shields.io/badge/NLP-scikit--learn%20TF--IDF-orange?logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![PyMuPDF](https://img.shields.io/badge/Parser-PyMuPDF-red)](https://pymupdf.readthedocs.io/)
[![Bootstrap](https://img.shields.io/badge/Frontend-Bootstrap%205-purple?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Resumint AI** is a production-ready, privacy-focused web application designed to help job seekers, students, and career switchers bridge the gap between their current skills and industry expectations. 

Powered by natural language processing (NLP), hybrid semantic text similarity, and a dataset of real Kaggle tech job postings, Resumint AI provides explainable job recommendations, single-job benchmark comparisons, and personalized sequential career roadmaps.

---

## 🌟 Core Features

Resumint AI features three distinct, independent workflows:

### 1. 📄 Analyze Resume – General Job Recommendations
* **Automated Skill Extraction**: Uses regular expression boundary parsing and NLP normalization to identify **230+ technical skills**, **18 soft skills**, and degree/academic credentials from uploaded PDF resumes (handling complex symbols like `C++`, `C#`, and `.NET` accurately).
* **Hybrid Match Engine**: Evaluates candidate resumes against indexed IT job postings using a tuned hybrid scoring function:
  $$\text{Score} = w_{\text{skill}} \cdot \text{Skill Coverage} + w_{\text{text}} \cdot \text{TF-IDF Cosine Similarity}$$
* **Top 5 Job Matches**: Ranks best-fitting roles, displays match percentages, shows matched competencies vs. missing skills, and provides instant direct search links to active market openings on **LinkedIn**, **Indeed**, and **Google Jobs**.

### 2. 🎯 Explore Job Benchmarks – Compare Resume Against a Selected Job
* **Strict Single-Job Evaluation**: Rather than recommending alternative roles, this mode evaluates candidate preparation strictly against the specific job posting selected (e.g. `Backend Developer (JOB_032)`).
* **Resume-to-Job Match Percentage**: Computes exact skill coverage and description similarity against that specific job's requirements.
* **Skills You Already Have vs. Missing Skills**: Clean breakdown of satisfied requirements and missing technologies.
* **Curated Learning Recommendations**: For every missing skill, recommends **2–3 verified, real learning resources** (prioritizing free courses and platforms such as freeCodeCamp, Coursera, Mozilla MDN, W3Schools, Harvard CS50, and official documentation) with course descriptions and direct working links.
* **Actionable Improvement Suggestions**: Generates customized guidance on high-priority technical topics to master, recommended portfolio projects, and technical interview focal points.

### 3. 🗺️ Role Explorer & Sequential Career Roadmaps
* **21 Tech Career Guides**: Deep-dive into roles across Software Engineering, Data & AI, Cloud & DevOps, Cybersecurity, Systems, and Product Design.
* **Beginner-Friendly Overviews**: Explains what professionals actually do day-to-day, core responsibilities, and expected tools.
* **Sequential Career Preparation Roadmaps**: 4-stage structured learning paths (`Stage 1: Core Fundamentals` → `Stage 4: Advanced & Scalable Architecture`) dynamically marked with:
  - **Already Known** (directly detected or satisfied through skill implications, e.g., PostgreSQL implies SQL)
  - **Need to Learn** with estimated durations and direct course links.

### 4. 📊 Visual Dashboard & Application Tracker
* **Interactive Chart.js Visualizations**: Multi-role radar charts, skill domain distributions, and competency breakdown bars.
* **Application Tracker (CRUD)**: Track live job applications across statuses (`Saved`, `Applied`, `Interviewing`, `Offer`, `Rejected`) with notes, links, and dates.
* **Local History & Privacy**: Analyses are stored locally in an SQLite database. Uploaded resume PDFs are processed in temporary memory and deleted immediately to preserve user confidentiality.

---

## 🛠️ Tech Stack & Architecture

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+, Flask 3.x | Lightweight, high-performance web routing & templating |
| **WSGI Server** | Gunicorn | Production-ready HTTP server for cloud deployments |
| **Resume Parser** | PyMuPDF (fitz) | Fast, text-layer PDF parsing with error handling |
| **NLP & ML Engine** | scikit-learn, NumPy | TF-IDF vectorization, cosine similarity, hybrid scoring |
| **Data Processing** | pandas | Integrated Kaggle datasets parsing and query filtering |
| **Database** | SQLite3 (stdlib) | Zero-configuration local database for history & applications |
| **Frontend** | Jinja2, Bootstrap 5.3, Bootstrap Icons, Chart.js | Modern, responsive, mobile-friendly interface |

---

## 📂 Project Directory Structure

```text
Resumint-AI/
├── app.py                      # Core Flask application, routes, and error handlers
├── database.py                 # SQLite database access layer (analyses & applications)
├── requirements.txt            # Clean production Python dependencies
├── Procfile                    # Deployment entry point for Render, Railway, Heroku
├── Dockerfile                  # Production container definition (Python 3.11-slim)
├── .gitignore                  # Git exclusion rules
├── data/                       # Integrated Kaggle datasets & skill taxonomies
│   ├── jobs.csv                # 147 clean job postings across 21 technical roles
│   ├── skills.json             # 234 canonical technical skills grouped by category
│   ├── soft_skills.json        # 18 normalized soft skill definitions
│   ├── job_roles_info.json     # Beginner-friendly role guides & roadmaps for 21 roles
│   └── learning_resources.json # 159 verified learning courses & platforms
├── modules/                    # Core business logic & AI algorithms
│   ├── resume_parser.py        # PDF text extraction & validation
│   ├── skill_extractor.py      # Regex boundary extraction for technical/soft skills
│   ├── job_matcher.py          # TF-IDF indexing, skill overlap & hybrid ranking
│   ├── recommender.py          # Missing skill explanations & roadmap generator
│   └── pipeline.py             # End-to-end integration for general & benchmark modes
├── static/                     # Static web assets
│   ├── css/style.css           # Custom modern UI styling
│   └── js/dashboard.js         # Interactive Chart.js and dynamic checklist scripts
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Shared layout, navbar, and footer
│   ├── index.html              # Feature 1: Analyze Resume upload interface
│   ├── results.html            # Feature 1: General Job Recommendations results
│   ├── jobs.html               # Feature 2: Explore Job Benchmarks catalog
│   ├── compare_job.html        # Feature 2: Selected job resume upload interface
│   ├── job_comparison_result.html # Feature 2: Dedicated job match analysis
│   ├── roles.html              # Feature 3: Role Explorer & Roadmaps view
│   ├── dashboard.html          # Interactive visual analytics dashboard
│   ├── applications.html       # Job Application Tracker (CRUD)
│   ├── history.html            # Stored analysis history
│   └── 404.html / 413.html     # Friendly error pages
└── tests/                      # Automated test suite
    ├── test_app.py             # Route, upload validation, and CRUD tests
    ├── test_enhancements.py    # Kaggle integration & 3-feature workflow tests
    ├── test_module1.py         # Parsing & skill extraction unit tests
    ├── test_module2.py         # Hybrid ranking & tie-breaker unit tests
    └── eval_matching.py        # Ground-truth evaluation across 15 benchmark resumes
```

---

## ⚡ Quick Start / Local Installation

### Prerequisites
* Python 3.10, 3.11, or 3.12 installed on your machine.
* `git` installed.

### 1. Clone the Repository
```bash
git clone https://github.com/Sripathi2005/Resumint-AI.git
cd Resumint-AI
```

### 2. Create and Activate a Virtual Environment
* **Windows (Command Prompt / PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```
* **macOS / Linux**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## 🧪 Running Automated Tests

Run the full automated test suite to verify extraction, matching, and web workflows:

```bash
# Run Flask web route and feature workflow tests
python -m unittest tests.test_app tests.test_enhancements -v

# Run NLP extraction tests
python tests/test_module1.py

# Run hybrid matching and recommender tests
python tests/test_module2.py

# Run accuracy benchmark across 15 ground-truth test resumes
python tests/eval_matching.py
```

---

## 🚢 Deployment Guide

### Deploy to Render.com (Recommended — Free)
1. Fork or push this repository to your GitHub account.
2. Sign in to [Render](https://render.com) and click **New +** → **Web Service**.
3. Connect your `Resumint-AI` repository.
4. Set the configuration:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --workers 2 --threads 4 --timeout 120`
5. Under **Environment Variables**, add:
   - `SECRET_KEY`: `<generate-a-secure-random-string>`
6. Click **Create Web Service**. Your app will be live with free automatic SSL!

### Deploy with Docker
```bash
# Build the Docker container
docker build -t resumint-ai .

# Run the container
docker run -d -p 5000:5000 -e SECRET_KEY="your-secret-key" --name resumint resumint-ai
```

---

## 🔒 Privacy & Security

* **Zero Long-Term Resume Storage**: Uploaded resume files are parsed in temporary memory and permanently deleted immediately after processing (`tempfile` + `os.remove`).
* **File Upload Protections**: Strict file extension verification (`.pdf` only), 0-byte file detection, and a 5 MB upload payload limit (`MAX_CONTENT_LENGTH`).
* **Input Sanitization**: File names are sanitized via `werkzeug.utils.secure_filename`. Parameterized SQL queries prevent SQL injection.

---

## 👨‍💻 Author & Contributions

* **Repository**: [https://github.com/Sripathi2005/Resumint-AI](https://github.com/Sripathi2005/Resumint-AI)
* **Author**: Sripathi ([@Sripathi2005](https://github.com/Sripathi2005))
* Contributions, issues, and feature requests are welcome! Feel free to open an issue or submit a pull request.

---

## 📄 License
This project is open-source and licensed under the [MIT License](LICENSE).
