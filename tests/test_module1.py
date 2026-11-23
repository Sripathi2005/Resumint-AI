"""
Test suite for Module 1: Resume Parser and Skill Extractor.
Uses plain Python asserts without heavy frameworks.
"""

from pathlib import Path
import sys
import tempfile

import pymupdf

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.resume_parser import (
    CorruptedPDFError,
    EmptyPDFError,
    InvalidPDFError,
    ResumeNotFoundError,
    clean_text,
    extract_text,
)
from modules.skill_extractor import (
    extract_education_keywords,
    extract_sections,
    extract_skills,
    load_skills,
)


def test_alias_normalization():
    """Verify alias normalization (e.g. JS -> JavaScript, ReactJS -> React, Postgres -> PostgreSQL)."""
    text = "Candidate has hands-on experience in JS, ReactJS, and Postgres database."
    cleaned = clean_text(text)
    skills = extract_skills(cleaned)
    assert "JavaScript" in skills, f"Expected 'JavaScript' in {skills}"
    assert "React" in skills, f"Expected 'React' in {skills}"
    assert "PostgreSQL" in skills, f"Expected 'PostgreSQL' in {skills}"
    print("[PASS] test_alias_normalization")


def test_symbols_c_plus_plus_and_sharp():
    """Verify C++ and C# are properly preserved and detected."""
    text = "Proficient in C++, C#, and Node.js for backend microservices."
    cleaned = clean_text(text)
    assert "c++" in cleaned, f"Expected 'c++' in cleaned text: {cleaned}"
    assert "c#" in cleaned, f"Expected 'c#' in cleaned text: {cleaned}"
    assert "node.js" in cleaned, f"Expected 'node.js' in cleaned text: {cleaned}"

    skills = extract_skills(cleaned)
    assert "C++" in skills, f"Expected 'C++' in {skills}"
    assert "C#" in skills, f"Expected 'C#' in {skills}"
    assert "Node.js" in skills, f"Expected 'Node.js' in {skills}"
    # Verify 'C' is not falsely triggered just from 'C++'
    assert "C" not in skills, f"False positive 'C' detected in {skills}"
    print("[PASS] test_symbols_c_plus_plus_and_sharp")


def test_no_false_positive_go_in_good():
    """Verify 'good' or other words containing 'go' do not trigger 'Go'."""
    text = "A good developer with great algorithmic skills and goods delivery experience."
    cleaned = clean_text(text)
    skills = extract_skills(cleaned)
    assert "Go" not in skills, f"False positive 'Go' triggered in: {skills}"
    print("[PASS] test_no_false_positive_go_in_good")


def test_ambiguous_short_aliases():
    """Verify 'go', 'r', 'c' do not match normal English prose like 'go-to-market' or 'go beyond'."""
    prose_text = "We will go beyond expectations with innovative go-to-market strategies."
    cleaned_prose = clean_text(prose_text)
    prose_skills = extract_skills(cleaned_prose, raw_text=prose_text)
    assert "Go" not in prose_skills, f"False positive 'Go' matched in English prose: {prose_skills}"

    # Capitalized Go / R / C in raw text should match
    tech_text = "Proficient in Go, R, and C programming languages."
    cleaned_tech = clean_text(tech_text)
    tech_skills = extract_skills(cleaned_tech, raw_text=tech_text)
    assert "Go" in tech_skills, f"Expected 'Go' in {tech_skills}"
    assert "R" in tech_skills, f"Expected 'R' in {tech_skills}"
    assert "C" in tech_skills, f"Expected 'C' in {tech_skills}"

    # Inside Skills section, even lowercase 'go, r, c' are matched
    resume_skills_section = """
    Jane Doe
    Skills
    go, r, c, python
    """
    sec_cleaned = clean_text(resume_skills_section)
    sec_skills = extract_skills(sec_cleaned, raw_text=resume_skills_section)
    assert "Go" in sec_skills, f"Expected 'Go' in skills section: {sec_skills}"
    assert "R" in sec_skills, f"Expected 'R' in skills section: {sec_skills}"
    assert "C" in sec_skills, f"Expected 'C' in skills section: {sec_skills}"
    print("[PASS] test_ambiguous_short_aliases")


def test_longest_alias_first_spring_boot():
    """Verify longest alias matches first (Spring Boot matches before Spring)."""
    text = "Experienced in Spring Boot enterprise applications."
    cleaned = clean_text(text)
    skills = extract_skills(cleaned)
    assert "Spring Boot" in skills, f"Expected 'Spring Boot' in {skills}"
    # 'Spring Framework' should NOT trigger if candidate only wrote 'Spring Boot'
    assert "Spring Framework" not in skills, f"Unexpected 'Spring Framework' in {skills}"

    # If both are mentioned, both should be found
    both_text = "Proficient in Spring Framework and Spring Boot."
    both_skills = extract_skills(clean_text(both_text))
    assert "Spring Boot" in both_skills, f"Expected 'Spring Boot' in {both_skills}"
    assert "Spring Framework" in both_skills, f"Expected 'Spring Framework' in {both_skills}"
    print("[PASS] test_longest_alias_first_spring_boot")


def test_single_letter_r_not_in_words():
    """Verify 'r' is not falsely triggered inside words like 'programming'."""
    text = "Advanced computer programming and software development."
    skills = extract_skills(clean_text(text))
    assert "R" not in skills, f"False positive 'R' triggered in: {skills}"

    # But standalone 'R' language is detected
    r_text = "Data analysis using R and Python."
    r_skills = extract_skills(clean_text(r_text), raw_text=r_text)
    assert "R" in r_skills, f"Expected 'R' in {r_skills}"
    print("[PASS] test_single_letter_r_not_in_words")


def test_empty_pdf_raises_error():
    """Verify empty text PDF raises EmptyPDFError."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = Path(f.name)

    try:
        # Create a valid PDF document with 1 blank page (no text)
        doc = pymupdf.open()
        doc.new_page()
        doc.save(str(temp_path))
        doc.close()

        raised = False
        try:
            extract_text(temp_path)
        except EmptyPDFError:
            raised = True
        except Exception as e:
            assert False, f"Expected EmptyPDFError, got {type(e).__name__}: {e}"

        assert raised, "Expected EmptyPDFError was not raised for empty PDF."
        print("[PASS] test_empty_pdf_raises_error")
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_non_pdf_raises_error():
    """Verify non-PDF file raises InvalidPDFError."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"This is a text file, not a PDF.")
        temp_txt_path = Path(f.name)

    try:
        raised = False
        try:
            extract_text(temp_txt_path)
        except InvalidPDFError:
            raised = True
        except Exception as e:
            assert False, f"Expected InvalidPDFError, got {type(e).__name__}: {e}"

        assert raised, "Expected InvalidPDFError was not raised for .txt file."
        print("[PASS] test_non_pdf_raises_error")
    finally:
        if temp_txt_path.exists():
            temp_txt_path.unlink()


def test_corrupted_pdf_raises_error():
    """Verify corrupted PDF raises CorruptedPDFError or InvalidPDFError."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        # Invalid PDF header and content
        f.write(b"not a valid pdf binary content")
        temp_corrupted = Path(f.name)

    try:
        raised = False
        try:
            extract_text(temp_corrupted)
        except (InvalidPDFError, CorruptedPDFError):
            raised = True
        except Exception as e:
            assert False, f"Expected InvalidPDFError or CorruptedPDFError, got {type(e).__name__}: {e}"

        assert raised, "Expected exception was not raised for corrupted file."
        print("[PASS] test_corrupted_pdf_raises_error")
    finally:
        if temp_corrupted.exists():
            temp_corrupted.unlink()


def test_file_not_found_raises_error():
    """Verify non-existent file raises ResumeNotFoundError."""
    non_existent = Path("does_not_exist_12345.pdf")
    raised = False
    try:
        extract_text(non_existent)
    except ResumeNotFoundError:
        raised = True
    assert raised, "Expected ResumeNotFoundError was not raised for non-existent file."
    print("[PASS] test_file_not_found_raises_error")


def test_extract_sections():
    """Verify resume sections are properly extracted and missing sections return empty strings."""
    sample_resume_text = """
    Jane Smith
    Email: jane@example.com

    Education
    B.Tech in Computer Science, 2024
    GPA: 8.9/10

    Experience
    Software Engineer at Acme Corp (2022-Present)
    - Designed and implemented microservices in Go and Python.

    Skills
    Python, C++, Docker, Kubernetes, PostgreSQL

    Projects
    AI Resume Analyzer
    - Built resume parser and skill matcher.
    """
    sections = extract_sections(sample_resume_text)
    assert "education" in sections
    assert "experience" in sections
    assert "projects" in sections
    assert "skills" in sections
    assert "B.Tech in Computer Science" in sections["education"]
    assert "Software Engineer at Acme Corp" in sections["experience"]
    assert "AI Resume Analyzer" in sections["projects"]
    assert "Python, C++, Docker" in sections["skills"]

    # Test missing section returns empty string
    partial_text = """
    Jane Smith
    Education:
    BSc in IT
    """
    partial_sections = extract_sections(partial_text)
    assert partial_sections["projects"] == ""
    assert partial_sections["experience"] == ""
    assert partial_sections["skills"] == ""
    assert "BSc in IT" in partial_sections["education"]
    print("[PASS] test_extract_sections")


def test_education_keywords():
    """Verify detection of degrees like B.Tech, B.E, M.Tech, BSc, MCA, MBA."""
    text = "Candidate has completed B.Tech in CSE, followed by M.Tech and later an MBA. Colleague completed BSc and MCA."
    degrees = extract_education_keywords(text)
    for expected in ["B.Tech", "M.Tech", "MBA", "BSc", "MCA"]:
        assert expected in degrees, f"Expected {expected} in {degrees}"

    # Verify B.E detection
    be_text = "Graduated with B.E in Electronics and Communication."
    be_degrees = extract_education_keywords(be_text)
    assert "B.E" in be_degrees, f"Expected B.E in {be_degrees}"

    # Verify English word 'be' does not trigger B.E
    no_be_text = "I will be joining next month."
    no_be_degrees = extract_education_keywords(no_be_text)
    assert "B.E" not in no_be_degrees, f"False positive 'B.E' triggered in {no_be_degrees}"
    print("[PASS] test_education_keywords")


def run_all_tests():
    """Run all module 1 test cases."""
    print("=" * 60)
    print("Running Module 1 Test Suite...")
    print("=" * 60)

    test_alias_normalization()
    test_symbols_c_plus_plus_and_sharp()
    test_no_false_positive_go_in_good()
    test_ambiguous_short_aliases()
    test_longest_alias_first_spring_boot()
    test_single_letter_r_not_in_words()
    test_empty_pdf_raises_error()
    test_non_pdf_raises_error()
    test_corrupted_pdf_raises_error()
    test_file_not_found_raises_error()
    test_extract_sections()
    test_education_keywords()

    print("=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! (12/12)")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
