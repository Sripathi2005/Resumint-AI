"""
AI Resume Analyzer - Module 1 CLI Runner.

Usage:
    python run_module1.py <path_to_pdf>
    python run_module1.py sample_resumes/sample_resume.pdf
"""

from pathlib import Path
import sys

from modules.resume_parser import (
    ResumeParserError,
    clean_text,
    extract_text,
)
from modules.skill_extractor import (
    extract_education_keywords,
    extract_sections,
    extract_skills,
    load_skills,
)


def run_pipeline(pdf_path: str) -> None:
    """Execute Module 1 pipeline for a given resume PDF."""
    path = Path(pdf_path)
    print("=" * 70)
    print(f"AI RESUME ANALYZER - MODULE 1: RESUME PARSER & SKILL EXTRACTOR")
    print(f"Target PDF: {path.resolve()}")
    print("=" * 70)

    try:
        # Step 1: Extract text from PDF
        print("\n[1/4] Extracting raw text with PyMuPDF...")
        raw_text = extract_text(path)
        print(f"      Extracted {len(raw_text)} characters across document.")

        # Step 2: Clean and normalize text
        print("\n[2/4] Normalizing and cleaning text...")
        cleaned = clean_text(raw_text)
        print(f"      Cleaned text length: {len(cleaned)} characters.")

        # Step 3: Extract skills
        print("\n[3/4] Extracting skills from taxonomy...")
        skill_lookup = load_skills()
        detected_skills = extract_skills(cleaned, skill_lookup=skill_lookup, raw_text=raw_text)

        print(f"\n      >>> DETECTED SKILLS ({len(detected_skills)} found):")
        if detected_skills:
            for i, skill in enumerate(detected_skills, 1):
                print(f"          {i:2d}. {skill}")
        else:
            print("          None detected.")

        # Step 4: Extract education keywords & sections
        print("\n[4/4] Extracting education keywords and sections...")
        education_keywords = extract_education_keywords(raw_text)
        sections = extract_sections(raw_text)

        print(f"\n      >>> EDUCATION KEYWORDS ({len(education_keywords)} found):")
        if education_keywords:
            for deg in education_keywords:
                print(f"          - {deg}")
        else:
            print("          None detected.")

        print(f"\n      >>> SECTIONS FOUND:")
        for sec_name, content in sections.items():
            status = "FOUND" if content else "NOT FOUND (empty)"
            preview = ""
            if content:
                first_line = content.splitlines()[0]
                preview = f" -> \"{first_line[:60]}...\"" if len(first_line) > 60 else f" -> \"{first_line}\""
            print(f"          - {sec_name.capitalize():12s}: [{status}]{preview}")

        print("\n" + "=" * 70)
        print("Analysis completed successfully.")
        print("=" * 70)

    except ResumeParserError as e:
        print(f"\n[ERROR] Resume Parser Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}", file=sys.stderr)
        sys.exit(2)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python run_module1.py <path_to_resume.pdf>")
        print("Example: python run_module1.py sample_resumes/sample_resume.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    run_pipeline(pdf_path)


if __name__ == "__main__":
    main()
