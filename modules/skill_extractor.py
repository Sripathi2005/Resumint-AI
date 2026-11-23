"""
Skill and Section Extractor Module.

Provides functions to:
- Load skill taxonomy with aliases from JSON.
- Extract canonical skills from cleaned text using boundary regex matching.
- Segment raw resume text into key sections (education, experience, projects, skills).
- Detect academic degrees and education keywords.
"""

import json
from functools import lru_cache
from pathlib import Path
import re
from typing import Dict, List, Optional


# Precompiled degree patterns for education keyword detection
DEGREE_PATTERNS = [
    ("B.Tech", re.compile(r"\b(?:b\.?\s*tech(?:nology)?|bachelor\s+of\s+technology)\b", re.IGNORECASE)),
    ("B.E", re.compile(r"\b(?:b\.e\.?|bachelor\s+of\s+engineering)\b", re.IGNORECASE)),
    ("B.E", re.compile(r"\bBE\b")),  # Case-sensitive for BE without dots to avoid 'be'
    ("M.Tech", re.compile(r"\b(?:m\.?\s*tech(?:nology)?|master\s+of\s+technology)\b", re.IGNORECASE)),
    ("M.E", re.compile(r"\b(?:m\.e\.?|master\s+of\s+engineering)\b", re.IGNORECASE)),
    ("M.E", re.compile(r"\bME\b")),  # Case-sensitive for ME without dots to avoid 'me'
    ("BSc", re.compile(r"\b(?:b\.?\s*sc(?:ience)?|bachelor\s+of\s+science)\b", re.IGNORECASE)),
    ("MSc", re.compile(r"\b(?:m\.?\s*sc(?:ience)?|master\s+of\s+science)\b", re.IGNORECASE)),
    ("BCA", re.compile(r"\b(?:b\.?\s*c\.?\s*a\.?|bca|bachelor\s+of\s+computer\s+applications?)\b", re.IGNORECASE)),
    ("MCA", re.compile(r"\b(?:m\.?\s*c\.?\s*a\.?|mca|master\s+of\s+computer\s+applications?)\b", re.IGNORECASE)),
    ("BBA", re.compile(r"\b(?:b\.?\s*b\.?\s*a\.?|bba|bachelor\s+of\s+business\s+administration)\b", re.IGNORECASE)),
    ("MBA", re.compile(r"\b(?:m\.?\s*b\.?\s*a\.?|mba|master\s+of\s+business\s+administration)\b", re.IGNORECASE)),
    ("B.Com", re.compile(r"\b(?:b\.?\s*com(?:merce)?|bachelor\s+of\s+commerce)\b", re.IGNORECASE)),
    ("M.Com", re.compile(r"\b(?:m\.?\s*com(?:merce)?|master\s+of\s+commerce)\b", re.IGNORECASE)),
    ("PhD", re.compile(r"\b(?:ph\.?\s*d\.?|doctorate|doctor\s+of\s+philosophy)\b", re.IGNORECASE)),
    ("Diploma", re.compile(r"\bdiploma\b", re.IGNORECASE)),
]

# Section heading detection patterns
SECTION_PATTERNS = {
    "education": [
        r"^education(?:al)?(?:\s+(?:background|qualifications?|details|profile|history|record))?$",
        r"^academic(?:\s+(?:background|qualifications?|details|record|profile|history))?$",
        r"^academics$",
        r"^qualifications?$",
    ],
    "experience": [
        r"^(?:work|professional|employment|industry|job)?\s*experience$",
        r"^work\s*history$",
        r"^employment(?:\s+(?:history|record))?$",
        r"^internships?(?:\s+experience)?$",
        r"^career(?:\s+(?:history|summary|profile|overview))?$",
    ],
    "projects": [
        r"^(?:key|technical|academic|personal|major|capstone|featured)?\s*projects?$",
        r"^project\s*(?:work|experience)?$",
        r"^portfolio$",
    ],
    "skills": [
        r"^(?:technical|key|core|professional|relevant|it)?\s*skills?(?:\s*(?:&|and)\s*(?:competencies|technologies|tools|abilities))?$",
        r"^technologies(?:\s*(?:&|and)\s*tools)?$",
        r"^tech(?:nical)?\s*stack$",
        r"^core\s*competencies$",
        r"^areas\s*of\s*expertise$",
        r"^tools\s*(?:&|and)\s*technologies$",
    ],
}


def load_skills(path: Optional[str | Path] = None) -> Dict[str, str]:
    """
    Load skills from JSON file and construct an alias -> canonical name lookup table.

    Args:
        path: Path to skills.json. If None, defaults to data/skills.json relative
              to project root.

    Returns:
        Dictionary mapping lowercased alias to canonical skill name.
    """
    if path is None:
        path = Path(__file__).resolve().parent.parent / "data" / "skills.json"
    else:
        path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Skills definition file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lookup: Dict[str, str] = {}
    for item in data.get("skills", []):
        canonical_name = item.get("name", "").strip()
        if not canonical_name:
            continue

        # Add canonical name lowercased
        lookup[canonical_name.lower()] = canonical_name

        # Add all aliases
        for alias in item.get("aliases", []):
            alias_clean = alias.strip().lower()
            if alias_clean:
                # Retain primary mapping if already present
                if alias_clean not in lookup:
                    lookup[alias_clean] = canonical_name

    return lookup


@lru_cache(maxsize=None)
def _build_alias_pattern(alias: str) -> re.Pattern:
    """
    Build a word-boundary regex for a skill alias, correctly handling symbols
    such as +, #, ., -, /.
    """
    escaped = re.escape(alias)

    # Prefix boundary
    if alias.startswith("."):
        prefix = r"(?<![a-zA-Z0-9_.])"
    else:
        prefix = r"(?<![a-zA-Z0-9_])"

    # Suffix boundary
    if alias.endswith("+"):
        suffix = r"(?![a-zA-Z0-9_+])"
    elif alias.endswith("#"):
        suffix = r"(?![a-zA-Z0-9_#])"
    elif len(alias) == 1 and alias.isalpha():
        # Single-letter skills (like 'c' or 'r') should not match if immediately
        # followed by +, #, or a word character (e.g. avoid 'c' matching inside 'c++' or 'c#')
        suffix = r"(?![a-zA-Z0-9_+#])"
    else:
        suffix = r"(?![a-zA-Z0-9_])"

    return re.compile(prefix + escaped + suffix, re.IGNORECASE)


AMBIGUOUS_CASE_PATTERNS = {
    "go": re.compile(r"\bGo\b"),
    "r": re.compile(r"\bR\b"),
    "c": re.compile(r"\bC(?![a-zA-Z0-9_+#])"),
    "excel": re.compile(r"\bExcel\b"),
}


def extract_skills(
    clean_text: str,
    skill_lookup: Optional[Dict[str, str]] = None,
    raw_text: Optional[str] = None,
) -> List[str]:
    """
    Extract canonical skills from text using boundary regex matching.

    Matches longest aliases first (e.g., 'spring boot' before 'spring') and
    masks matched spans to avoid false-positive sub-matches. Short ambiguous
    aliases ('go', 'r', 'c') are validated against original-case text or
    restricted to the Skills section to prevent false positives from common
    English prose (e.g. 'go beyond', 'go-to-market').

    Args:
        clean_text: Cleaned and normalized resume text.
        skill_lookup: Optional dictionary mapping alias -> canonical name.
                      If None, loaded from default data/skills.json.
        raw_text: Optional original uncleaned text preserving casing and sections.

    Returns:
        Sorted list of unique canonical skill names detected.
    """
    if not clean_text:
        return []

    if skill_lookup is None:
        skill_lookup = load_skills()

    # If raw_text not explicitly passed but clean_text contains uppercase characters,
    # use it as raw_text for case-sensitive verification of ambiguous aliases
    if raw_text is None and any(c.isupper() for c in clean_text):
        raw_text = clean_text

    # Pre-extract skills section if raw_text is provided
    skills_section_text = ""
    if raw_text:
        sections = extract_sections(raw_text)
        skills_section_text = sections.get("skills", "")

    # Sort aliases descending by length to match longest aliases first
    sorted_aliases = sorted(skill_lookup.keys(), key=lambda a: (len(a), a), reverse=True)

    detected_skills = set()
    working_text = clean_text

    for alias in sorted_aliases:
        pattern = _build_alias_pattern(alias)
        if pattern.search(working_text):
            # Special check for short ambiguous aliases (go, r, c)
            if alias in AMBIGUOUS_CASE_PATTERNS:
                case_pat = AMBIGUOUS_CASE_PATTERNS[alias]
                is_valid = False

                # 1. Valid if alias occurs in the designated Skills section (case-insensitive)
                if skills_section_text and pattern.search(skills_section_text):
                    is_valid = True
                # 2. Valid if alias matches original-cased text with proper capitalization
                elif raw_text and case_pat.search(raw_text):
                    is_valid = True
                # 3. If raw_text wasn't passed, check if clean_text still has original casing
                elif case_pat.search(clean_text):
                    is_valid = True

                if not is_valid:
                    # Do not treat as skill; mask to prevent infinite search
                    working_text = pattern.sub(lambda m: " " * len(m.group(0)), working_text)
                    continue

            canonical = skill_lookup[alias]
            detected_skills.add(canonical)
            # Mask out the matched occurrences with equal-length spaces so shorter
            # aliases do not erroneously match within this already-claimed token
            working_text = pattern.sub(lambda m: " " * len(m.group(0)), working_text)

    return sorted(list(detected_skills))


def extract_sections(raw_text: str) -> Dict[str, str]:
    """
    Extract key resume sections (education, experience, projects, skills)
    by detecting common section headings.

    Missing sections return empty strings.

    Args:
        raw_text: Raw resume text.

    Returns:
        Dictionary with keys: 'education', 'experience', 'projects', 'skills'.
    """
    sections: Dict[str, List[str]] = {
        "education": [],
        "experience": [],
        "projects": [],
        "skills": [],
    }

    if not raw_text:
        return {k: "" for k in sections}

    lines = raw_text.splitlines()
    current_section: Optional[str] = None

    for raw_line in lines:
        line_stripped = raw_line.strip()
        if not line_stripped:
            continue

        # Clean line to identify potential heading
        # Remove leading list bullets, numbers, dashes, hashes
        cleaned_line = re.sub(r"^[\d\.\-\*#•●\s]+", "", line_stripped).strip()

        # Check if line contains a colon, e.g. 'Technical Skills: Python, Java'
        heading_candidate = cleaned_line
        inline_content = ""
        if ":" in cleaned_line:
            left, _, right = cleaned_line.partition(":")
            # If left part is short (heading-like), test it as heading
            if len(left.strip().split()) <= 5:
                heading_candidate = left.strip()
                inline_content = right.strip()

        # Strip trailing punctuation
        normalized_heading = heading_candidate.rstrip(":-_ ").strip().lower()

        detected_section_key: Optional[str] = None
        # Headings are short (<= 5 words and <= 45 chars)
        if 0 < len(normalized_heading) <= 45 and len(normalized_heading.split()) <= 5:
            for sec_key, pattern_list in SECTION_PATTERNS.items():
                for pat in pattern_list:
                    if re.match(pat, normalized_heading, re.IGNORECASE):
                        detected_section_key = sec_key
                        break
                if detected_section_key:
                    break

        if detected_section_key:
            current_section = detected_section_key
            if inline_content:
                sections[current_section].append(inline_content)
        elif current_section:
            sections[current_section].append(line_stripped)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


def extract_education_keywords(text: str) -> List[str]:
    """
    Detect degree keywords (e.g. B.Tech, B.E, M.Tech, BSc, MCA, MBA).

    Args:
        text: Text to search for degrees.

    Returns:
        Sorted list of unique detected degree names.
    """
    if not text:
        return []

    detected_degrees = set()
    for degree_name, pattern in DEGREE_PATTERNS:
        if pattern.search(text):
            detected_degrees.add(degree_name)

    return sorted(list(detected_degrees))


def load_soft_skills(path: Optional[str | Path] = None) -> Dict[str, str]:
    """
    Load soft skills taxonomy from data/soft_skills.json.
    Returns mapping of lowercased alias -> canonical soft skill name.
    """
    if path is None:
        path = Path(__file__).resolve().parent.parent / "data" / "soft_skills.json"
    else:
        path = Path(path)

    if not path.is_file():
        return {}

    return load_skills(path)


def extract_soft_skills(
    clean_text: str,
    soft_lookup: Optional[Dict[str, str]] = None,
    raw_text: Optional[str] = None,
) -> List[str]:
    """
    Extract canonical soft/professional skills without affecting technical skill matching.
    """
    if not clean_text:
        return []
    if soft_lookup is None:
        soft_lookup = load_soft_skills()
    if not soft_lookup:
        return []
    return extract_skills(clean_text, skill_lookup=soft_lookup, raw_text=raw_text)
