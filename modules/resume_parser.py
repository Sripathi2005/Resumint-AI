"""
Resume Parser Module.

Provides functions to extract raw text from PDF files using PyMuPDF and clean
the text for skill and section extraction.
"""

from pathlib import Path
import re
from typing import Union

import pymupdf


class ResumeParserError(Exception):
    """Base exception for all resume parsing errors."""
    pass


class ResumeNotFoundError(ResumeParserError, FileNotFoundError):
    """Raised when the resume file is not found on the filesystem."""
    pass


ResumeFileNotFoundError = ResumeNotFoundError


class InvalidPDFError(ResumeParserError, ValueError):
    """Raised when the input file is not a PDF or has an invalid structure."""
    pass


class CorruptedPDFError(ResumeParserError):
    """Raised when the PDF file is corrupted or cannot be read."""
    pass


class EmptyPDFError(ResumeParserError):
    """Raised when the PDF contains no extractable text layer (e.g. scanned image)."""
    pass


EmptyPDFTextError = EmptyPDFError
EmptyTextError = EmptyPDFError


def extract_text(pdf_path: Union[str, Path]) -> str:
    """
    Extract text content from a PDF file using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file (str or Path object).

    Returns:
        Extracted raw text combined from all pages.

    Raises:
        ResumeNotFoundError: If the file does not exist.
        InvalidPDFError: If the file is not a PDF.
        CorruptedPDFError: If the PDF is corrupted.
        EmptyPDFError: If the PDF contains no extractable text layer.
    """
    path = Path(pdf_path)

    if not path.exists() or not path.is_file():
        raise ResumeNotFoundError(f"Resume file not found: {pdf_path}")

    if path.suffix.lower() != ".pdf":
        raise InvalidPDFError(f"File is not a PDF (expected .pdf extension): {pdf_path}")

    # Inspect PDF header bytes
    try:
        with open(path, "rb") as f:
            header_sample = f.read(1024)
            if b"%PDF-" not in header_sample:
                raise InvalidPDFError(f"File does not have a valid PDF header: {pdf_path}")
    except (InvalidPDFError, ResumeNotFoundError):
        raise
    except Exception as e:
        raise CorruptedPDFError(f"Could not read PDF file header: {pdf_path}. Details: {e}") from e

    try:
        doc = pymupdf.open(str(path))
    except pymupdf.FileDataError as e:
        raise CorruptedPDFError(f"Corrupted or unreadable PDF: {pdf_path}. Details: {e}") from e
    except Exception as e:
        raise CorruptedPDFError(f"Failed to open PDF document: {pdf_path}. Details: {e}") from e

    try:
        text_pages = []
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text_pages.append(page_text)
    except Exception as e:
        raise CorruptedPDFError(f"Failed to read text from PDF pages: {pdf_path}. Details: {e}") from e
    finally:
        doc.close()

    raw_text = "\n".join(text_pages).strip()
    if not raw_text:
        raise EmptyPDFError(
            f"PDF contains no extractable text layer (likely scanned or empty): {pdf_path}"
        )

    return raw_text


def clean_text(text: str) -> str:
    """
    Clean and normalize text for skill matching.

    Performs:
    - Lowercasing
    - Removal of non-printable characters
    - Normalization of bullet characters and list symbols
    - Replacement of structural punctuation while keeping symbols critical
      for programming skills (+, #, ., -, /)
    - Normalization of multiple whitespaces into a single space

    Args:
        text: Raw text string.

    Returns:
        Cleaned, normalized text string.
    """
    if not text:
        return ""

    # 1. Lowercase
    text = text.lower()

    # 2. Remove non-printable characters (keep printable and standard whitespace)
    text = "".join(ch for ch in text if ch.isprintable() or ch in " \t\n\r")

    # 3. Replace common bullet characters with space
    bullet_pattern = re.compile(
        r"[\u2022\u2023\u2043\u2219\u25cb\u25cf\u25aa\u25fe\u25b8\u25b9\u25c6\uf0b7\uf0a7•●○■▪▫–—]"
    )
    text = bullet_pattern.sub(" ", text)

    # Replace standalone hyphens or asterisks that serve as bullets
    text = re.sub(r"(?:^|\s)[-\*](?=\s|$)", " ", text)

    # 4. Remove punctuation while preserving symbols for skills (+, #, ., -, /)
    text = re.sub(r"[,:;()\[\]{}|\"\'`~!?@$%^&=*<>\\]", " ", text)

    # 5. Clean ellipses and sentence-ending periods, preserving internal dots in skills (.net, node.js)
    text = re.sub(r"\.{2,}", " ", text)
    # A dot followed by space or end of string is a sentence terminator
    text = re.sub(r"(?<=[a-zA-Z0-9+#])\.(?=\s|$)", " ", text)
    # Standalone dots
    text = re.sub(r"(?<=\s)\.(?=\s|$)", " ", text)

    # 6. Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text
