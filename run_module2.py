"""
AI Resume Analyzer - Module 2 CLI Runner.

Usage:
    python run_module2.py sample_resumes/java_backend.pdf
    python run_module2.py sample_resumes/java_backend.pdf --role "Java Developer"
"""

import argparse
from pathlib import Path
import sys

from modules.pipeline import analyze_resume
from modules.resume_parser import ResumeParserError


def main():
    parser = argparse.ArgumentParser(description="AI Resume Analyzer - Module 2 Job Matcher & Recommender")
    parser.add_argument("resume_path", type=str, help="Path to resume PDF file")
    parser.add_argument("--role", type=str, default=None, help="Target role for detailed skill gap analysis")
    parser.add_argument("--top_n", type=int, default=5, help="Number of top roles to display (default: 5)")
    parser.add_argument("--w_skill", type=float, default=0.6, help="Weight for skill coverage (default: 0.6)")
    parser.add_argument("--w_text", type=float, default=0.4, help="Weight for text similarity (default: 0.4)")
    args = parser.parse_args()

    pdf_path = Path(args.resume_path)
    if not pdf_path.is_file():
        print(f"[ERROR] Resume file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 75)
    print("AI RESUME ANALYZER - RESUME ANALYSIS & ROLE RECOMMENDATIONS")
    print(f"Target Resume: {pdf_path.resolve()}")
    print("=" * 75)

    try:
        data = analyze_resume(
            pdf_path,
            role=args.role,
            top_n=args.top_n,
            w_skill=args.w_skill,
            w_text=args.w_text,
        )
    except ResumeParserError as e:
        print(f"[ERROR] Failed to parse resume: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Analysis pipeline failure: {e}", file=sys.stderr)
        sys.exit(2)

    # 1. Profile Summary
    skills = data["detected_skills"]
    edu = data["education"]
    print(f"\n[1/3] Candidate Profile Extracted:")
    print(f"      - Detected Skills: {', '.join(skills) if skills else 'None'}")
    print(f"      - Education      : {', '.join(edu) if edu else 'None detected'}")

    # 2. Ranked Roles
    top_roles = data["top_roles"]
    print(f"\n[2/3] Top {len(top_roles)} Recommended Roles (w_skill={args.w_skill}, w_text={args.w_text}):\n")
    for i, role in enumerate(top_roles, 1):
        matched_str = ", ".join(role["matched"]) if role["matched"] else "None"
        missing_str = ", ".join(role["missing"]) if role["missing"] else "None"
        tier_str = role.get("tier", "Match")
        print(f"  #{i} {role['title'].upper()} (Job ID: {role['job_id']}) -> [{tier_str}]")
        print(f"      Headline Skill Match : {role['skill_score']:.1f}%")
        print(f"      - Context Similarity : {role['text_score']:.1f}%")
        print(f"      - Composite Score    : {role['final_score']:.1f}%")
        print(f"      - Matched Skills     : [{matched_str}]")
        print(f"      - Missing Skills     : [{missing_str}]")
        print()

    # 3. Gap Analysis
    target = data.get("target_role")
    if target:
        print("=" * 75)
        print(f"DETAILED GAP ANALYSIS FOR: '{target['title']}' (Job ID: {target['job_id']})")
        print("=" * 75)
        print(f"Qualification Tier     : {target.get('tier', 'Match')}")
        print(f"Skill Match Headline   : {target['skill_score']:.1f}%")
        print(f"Context Similarity     : {target['text_score']:.1f}%")
        print(f"Required Skills        : {', '.join(target['required_skills'])}")
        if target.get("preferred_skills"):
            print(f"Preferred Skills       : {', '.join(target['preferred_skills'])}")
        print(f"Missing Required Skills: {', '.join(target['missing']) if target['missing'] else 'None (100% required skills matched!)'}\n")

        checklist = target.get("learning_checklist", [])
        if checklist:
            print("Recommended Learning Checklist (Prioritized by Market Demand):")
            for item in checklist:
                print(f"  [ ] {item['skill']} (Category: {item['category']})")
        else:
            print("Great job! No skill gaps detected for this role.")
        print("=" * 75)


if __name__ == "__main__":
    main()
