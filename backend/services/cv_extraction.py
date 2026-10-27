"""Extraction heuristique de CV PDF.

Cette extraction est volontairement conservatrice : les champs restent à vérifier
par un utilisateur, et un PDF scanné nécessite une étape OCR distincte.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

import fitz


TECHNICAL_SKILLS = (
    "python", "java", "c++", "c#", "sql", "mysql", "postgresql", "pandas",
    "numpy", "spark", "hadoop", "flink", "power bi", "scikit-learn",
    "matplotlib", "tensorflow", "pytorch", "zookeeper", "linux", "ubuntu",
    "docker", "talend", "ssh", "excel", "javascript", "typescript", "html",
    "css", "node.js", "react", "angular", "aws", "azure", "gcp", "airflow",
    "etl", "kubernetes", "mlflow", "git", "jenkins", "terraform", "ansible",
    "mongodb", "redis", "kafka", "tableau", "fastapi", "flask", "django",
    "rest api", "ci/cd", "machine learning", "deep learning", "nlp",
)

SECTION_HEADERS = {
    "formation": ("FORMATION", "EDUCATION", "DIPLOMES", "DIPLÔMES"),
    "experience": ("EXPERIENCE", "EXPÉRIENCE", "STAGE", "WORK EXPERIENCE", "PARCOURS PROFESSIONNEL"),
    "langues": ("LANGUE", "LANGUES", "LANGUAGES"),
    "centres": ("CENTRES D'INTERET", "CENTRES D’INTÉRÊT", "INTERESTS", "HOBBIES"),
}
SECTION_STOPS = {
    "formation": ("EXPERIENCE", "EXPÉRIENCE", "COMPETENCES", "COMPÉTENCES", "SKILLS"),
    "experience": ("FORMATION", "EDUCATION", "COMPETENCES", "COMPÉTENCES", "SKILLS", "LANGUES"),
    "langues": ("INTERETS", "INTÉRÊTS", "CENTRES D'INTERET", "HOBBIES"),
    "centres": ("REFERENCES", "RÉFÉRENCES", "COMPETENCES", "COMPÉTENCES", "FORMATION", "EXPERIENCE"),
}


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).casefold()


def _extract_section(lines: list[str], section_name: str, max_lines: int = 20) -> str:
    headers = tuple(_fold(x) for x in SECTION_HEADERS[section_name])
    stops = tuple(_fold(x) for x in SECTION_STOPS[section_name])
    capturing = False
    result: list[str] = []
    for line in lines:
        folded = _fold(line.strip())
        matching_header = next(
            (header for header in headers
             if folded == header or folded.startswith(header + " ") or folded.startswith(header + ":")),
            None,
        )
        if matching_header:
            capturing = True
            # Supports headers and content on the same line.
            if folded.startswith(matching_header + ":"):
                content = line.split(":", 1)[1].strip()
                if content:
                    result.append(content)
            continue
        if capturing and any(folded == stop or folded.startswith(stop + " ") for stop in stops):
            break
        if capturing and line.strip():
            result.append(line.strip())
            if len(result) >= max_lines:
                break
    return " ".join(result).strip()


def _extract_name(lines: list[str]) -> str:
    ignored = (
        "curriculum vitae", "resume", "cv", "experience", "education", "skills", "competences",
        "engineer", "developer", "analyst", "technicien", "ingénieur", "data", "devops",
        "cloud", "backend", "frontend", "machine learning", "software",
    )
    for line in lines[:8]:
        candidate = line.strip()
        if not candidate or len(candidate) > 70 or any(ch.isdigit() for ch in candidate):
            continue
        folded = _fold(candidate)
        if any(word in folded for word in ignored):
            continue
        words = candidate.split()
        if 2 <= len(words) <= 4 and all(any(ch.isalpha() for ch in word) for word in words):
            if candidate.isupper() or all(word[:1].isupper() for word in words):
                return candidate.title() if candidate.isupper() else candidate
    return "Non trouvé"


def _extract_skills(text: str, lines: list[str]) -> list[str]:
    folded = _fold(text)
    found = set()
    for skill in TECHNICAL_SKILLS:
        pattern = r"(?<![a-z0-9])" + re.escape(_fold(skill)) + r"(?![a-z0-9])"
        if re.search(pattern, folded):
            found.add(skill)
    # Enrichissement limité à la section de compétences, sans considérer tout le CV
    # comme une liste de compétences.
    capturing = False
    for line in lines:
        folded_line = _fold(line.strip())
        if folded_line in {"competences", "competences techniques", "skills", "technical skills", "aptitudes"}:
            capturing = True
            continue
        if capturing and any(
            folded_line.startswith(_fold(header))
            for header in ("experience", "formation", "education", "projets", "certifications", "langues")
        ):
            break
        if capturing:
            for token in re.split(r"[,;|•\u2022]", line):
                token = token.strip(" \t-–—:")
                if 2 <= len(token) <= 40 and len(token.split()) <= 4 and not re.search(r"https?://", token, re.I):
                    # Avoid returning entire sentences as skill labels.
                    if not re.search(r"[.!?]", token):
                        found.add(token.casefold())
    return sorted(found)


def extract_cv_from_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """Extrait des champs basiques depuis un PDF contenant du texte."""
    if not isinstance(pdf_bytes, (bytes, bytearray)) or not pdf_bytes:
        raise ValueError("Le fichier PDF est vide.")
    if not bytes(pdf_bytes).lstrip().startswith(b"%PDF-"):
        raise ValueError("Le fichier fourni n'est pas un PDF valide.")

    try:
        with fitz.open(stream=bytes(pdf_bytes), filetype="pdf") as document:
            text = "\n".join(page.get_text("text") for page in document)
    except Exception as exc:
        raise ValueError("Le PDF est illisible ou endommagé.") from exc

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or not text.strip():
        raise ValueError(
            "Aucun texte n'a pu être extrait. Le PDF est peut-être scanné ; une étape OCR est nécessaire."
        )

    flat_text = " ".join(lines)
    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", flat_text, re.I)
    phone_match = re.search(
        r"(?<!\w)(?:\+?\d{1,3}[ .()-]*)?(?:\d[ .()-]*){7,13}\d(?!\w)",
        flat_text,
    )

    title = "Non précisé"
    title_keywords = (
        "data engineer", "data scientist", "data analyst", "developer", "developpeur",
        "développeur", "devops", "cloud engineer", "software engineer", "machine learning",
        "ingénieur", "engineer", "technicien", "backend", "frontend",
    )
    for line in lines[1:12]:
        if any(keyword in _fold(line) for keyword in title_keywords):
            title = line[:120]
            break

    address = "Non trouvé"
    address_keywords = ("adresse", "address", "rue ", "avenue ", "cite ", "cité ")
    for line in lines:
        if any(keyword in _fold(line) for keyword in address_keywords):
            address = line[:180]
            break

    return {
        "nom": _extract_name(lines),
        "jobtitle": title,
        "email": email_match.group(0) if email_match else "Non trouvé",
        "telephone": phone_match.group(0).strip() if phone_match else "Non trouvé",
        "adresse": address,
        "formation": _extract_section(lines, "formation"),
        "experience": _extract_section(lines, "experience"),
        "langues": _extract_section(lines, "langues"),
        "centres": _extract_section(lines, "centres"),
        "competences": _extract_skills(text, lines),
    }
