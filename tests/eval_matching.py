"""
Evaluation Script for Resume Matching.

Evaluates matching accuracy against hand-labeled ground truth (tests/labels.json)
using a strict Train/Test split:
- Train Set (10 resumes): Used for behavioral analysis and weight tuning.
- Test Set (5 held-out resumes): Evaluated blindly on unseen, messy profiles.

Evaluates:
1. TF-IDF Text Similarity Only (w_skill=0.0, w_text=1.0)
2. Skill-Overlap Only (w_skill=1.0, w_text=0.0)
3. Balanced Hybrid (w_skill=0.5, w_text=0.5)
4. Default Hybrid (w_skill=0.6, w_text=0.4)
5. Tuned Hybrid (w_skill=0.7, w_text=0.3)
"""

import json
from pathlib import Path
import sys
from typing import Any, Dict, List

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.job_matcher import (
    build_tfidf_index,
    load_jobs,
    rank_roles,
)
from modules.resume_parser import (
    clean_text,
    extract_text,
)
from modules.skill_extractor import (
    extract_skills,
    load_skills,
)

# 10 resumes used to tune weights
TRAIN_SPLIT = [
    "sample_resumes/fresher_python.pdf",
    "sample_resumes/java_backend.pdf",
    "sample_resumes/frontend_developer.pdf",
    "sample_resumes/data_scientist.pdf",
    "sample_resumes/devops_engineer.pdf",
    "sample_resumes/mixed_student_py_java.pdf",
    "sample_resumes/career_switcher_data.pdf",
    "sample_resumes/cloud_sysadmin.pdf",
    "sample_resumes/embedded_iot_engineer.pdf",
    "sample_resumes/data_analyst_bi.pdf",
]

# 5 held-out unseen resumes (tested blindly)
TEST_SPLIT = [
    "sample_resumes/vague_fresher.pdf",
    "sample_resumes/qa_transitioning_dev.pdf",
    "sample_resumes/fullstack_django_react.pdf",
    "sample_resumes/ml_engineer_vision.pdf",
    "sample_resumes/my_real_developer_resume.pdf",
]


def load_ground_truth(labels_path: Path) -> Dict[str, List[str]]:
    """Load resume -> expected roles mapping from labels.json."""
    if not labels_path.is_file():
        raise FileNotFoundError(f"Labels file not found: {labels_path}")

    with open(labels_path, "r", encoding="utf-8") as f:
        raw_labels = json.load(f)

    clean_labels = {}
    for path_str, val in raw_labels.items():
        if isinstance(val, list):
            expected = val
        elif isinstance(val, dict):
            expected = val.get("expected_roles", [])
        else:
            expected = []
        clean_labels[path_str] = expected

    return clean_labels


def evaluate_matching(labels_file: str = "tests/labels.json") -> Dict[str, Any]:
    """Run evaluation across all variants with train/test separation."""
    labels_path = Path(labels_file)
    ground_truth = load_ground_truth(labels_path)

    jobs_df = load_jobs()
    vectorizer, matrix = build_tfidf_index(jobs_df)
    skill_lookup = load_skills()

    # Pre-extract all resumes
    resume_data = {}
    for rel_path, expected_roles in ground_truth.items():
        full_path = PROJECT_ROOT / rel_path
        raw_text = extract_text(full_path)
        cleaned = clean_text(raw_text)
        skills = extract_skills(cleaned, skill_lookup=skill_lookup, raw_text=raw_text)
        resume_data[rel_path] = {
            "cleaned": cleaned,
            "skills": skills,
            "expected_roles": expected_roles,
            "is_train": rel_path in TRAIN_SPLIT,
        }

    # Weight configurations to benchmark
    variants = [
        {"name": "TF-IDF Only", "w_skill": 0.0, "w_text": 1.0},
        {"name": "Skill-Overlap Only", "w_skill": 1.0, "w_text": 0.0},
        {"name": "Balanced Hybrid", "w_skill": 0.5, "w_text": 0.5},
        {"name": "Default Hybrid (60/40)", "w_skill": 0.6, "w_text": 0.4},
        {"name": "Tuned Hybrid (70/30)", "w_skill": 0.7, "w_text": 0.3},
    ]

    results_summary = []
    per_variant_details = []

    print("=" * 80)
    print("AI RESUME ANALYZER - BENCHMARK & EVALUATION")
    print(f"Total Resumes: {len(resume_data)} (Train: {len(TRAIN_SPLIT)}, Test Held-Out: {len(TEST_SPLIT)})")
    print("=" * 80)

    for var in variants:
        name = var["name"]
        ws = var["w_skill"]
        wt = var["w_text"]

        train_top1 = 0
        train_top3 = 0
        train_total = 0

        test_top1 = 0
        test_top3 = 0
        test_total = 0

        var_logs = []

        for rel_path, data in resume_data.items():
            expected = data["expected_roles"]
            ranked = rank_roles(
                data["cleaned"],
                data["skills"],
                jobs_df,
                vectorizer,
                matrix,
                top_n=3,
                w_skill=ws,
                w_text=wt,
            )

            predicted_titles = [r["title"] for r in ranked]
            top1_hit = predicted_titles[0] in expected if predicted_titles else False
            top3_hit = any(t in expected for t in predicted_titles)

            is_train = data["is_train"]
            if is_train:
                train_total += 1
                if top1_hit:
                    train_top1 += 1
                if top3_hit:
                    train_top3 += 1
            else:
                test_total += 1
                if top1_hit:
                    test_top1 += 1
                if top3_hit:
                    test_top3 += 1

            var_logs.append({
                "resume": rel_path,
                "is_train": is_train,
                "expected": expected,
                "top3": predicted_titles,
                "top1_hit": top1_hit,
                "top3_hit": top3_hit,
            })

        train_top1_acc = (train_top1 / train_total * 100.0) if train_total else 0.0
        train_top3_acc = (train_top3 / train_total * 100.0) if train_total else 0.0

        test_top1_acc = (test_top1 / test_total * 100.0) if test_total else 0.0
        test_top3_acc = (test_top3 / test_total * 100.0) if test_total else 0.0

        overall_top1 = ((train_top1 + test_top1) / len(resume_data)) * 100.0
        overall_top3 = ((train_top3 + test_top3) / len(resume_data)) * 100.0

        results_summary.append({
            "Variant": name,
            "w_skill": ws,
            "w_text": wt,
            "Train Top-1": f"{train_top1_acc:.1f}% ({train_top1}/{train_total})",
            "Train Top-3": f"{train_top3_acc:.1f}% ({train_top3}/{train_total})",
            "Test Top-1": f"{test_top1_acc:.1f}% ({test_top1}/{test_total})",
            "Test Top-3": f"{test_top3_acc:.1f}% ({test_top3}/{test_total})",
            "Overall Top-1": f"{overall_top1:.1f}% ({train_top1 + test_top1}/{len(resume_data)})",
            "Overall Top-3": f"{overall_top3:.1f}% ({train_top3 + test_top3}/{len(resume_data)})",
        })
        per_variant_details.append({"variant": name, "logs": var_logs})

    # Print detailed predictions for Tuned Hybrid
    tuned_group = next(g for g in per_variant_details if "Tuned" in g["variant"])
    print(f"\n--- Detailed Predictions for [{tuned_group['variant']}] ---")
    for log in tuned_group["logs"]:
        fname = Path(log["resume"]).name
        split_tag = "TRAIN" if log["is_train"] else "TEST (HELD-OUT)"
        exp_str = ", ".join(log["expected"])
        pred_str = ", ".join(log["top3"])
        status = "TOP-1 HIT" if log["top1_hit"] else ("TOP-3 HIT" if log["top3_hit"] else "MISS")
        print(f"  [{split_tag:15s}] {fname:28s} | Expected: [{exp_str}]")
        print(f"                    Predictions: [{pred_str}] -> {status}")

    # Print final Markdown comparison table
    print("\n" + "=" * 90)
    print("PROJECT REPORT COMPARISON TABLE (TRAIN vs TEST)")
    print("=" * 90)
    print("| Matching Variant        | w_sk | w_tx | Train Top-1 | Train Top-3 | Test Top-1 (Unseen) | Test Top-3 | Overall Top-1 |")
    print("|:------------------------|:----:|:----:|:-----------:|:-----------:|:-------------------:|:----------:|:-------------:|")
    for r in results_summary:
        print(
            f"| {r['Variant']:24s} | {r['w_skill']:.1f}  | {r['w_text']:.1f}  "
            f"| {r['Train Top-1']:^11s} | {r['Train Top-3']:^11s} "
            f"| {r['Test Top-1']:^19s} | {r['Test Top-3']:^10s} "
            f"| {r['Overall Top-1']:^13s} |"
        )
    print("=" * 90)

    return {"summary": results_summary, "details": per_variant_details}


if __name__ == "__main__":
    evaluate_matching()
