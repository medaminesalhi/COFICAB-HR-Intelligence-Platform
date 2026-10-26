import fitz  # PyMuPDF
import re
import os
import json

# === 1. Charger le fichier PDF ===
file_path = "./c7.pdf"
if not os.path.exists(file_path):
    raise FileNotFoundError(f"Fichier introuvable : {file_path}")

doc = fitz.open(file_path)
text = ""
for page in doc:
    text += page.get_text()

# === 2. Nettoyage du texte ===
lines = [line.strip() for line in text.split("\n") if line.strip()]
cleaned_text = " ".join(lines).lower()

# === 3. Extraction des infos personnelles ===
def extract_email(text):
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return match.group(0) if match else "Non trouvé"

def extract_phone(text):
    match = re.search(r"\+?\(?\d{2,4}\)?[\s.-]?\d{2,3}[\s.-]?\d{2,3}[\s.-]?\d{2,4}", text)
    return match.group(0) if match else "Non trouvé"

def extract_name(lines):
    for line in lines[:10]:
        # ligne entièrement en majuscules, sans chiffre, et sans mots techniques
        if line.isupper() and not any(char.isdigit() for char in line):
            if not any(word in line.lower() for word in ["experience", "education", "skills", "competences", "project"]):
                return line.strip().title()  # mettre en majuscule initiale
        # ligne avec 2 mots ayant la première lettre majuscule
        if re.match(r"[A-Z][a-z]+ [A-Z][a-z]+", line):
            return line.strip()
    return "Non trouvé"


def extract_address(lines):
    for line in lines:
        if any(kw in line.lower() for kw in ["cite", "rue", "avenue", "adresse", "tunis"]):
            return line
    return "Non trouvé"

# === 4. Détection du titre de poste ===
def extract_job_title(lines):
    keywords_job = ["data", "engineer", "developer", "devops", "cloud", "ai", "ml", "full stack", "frontend", "backend", "technicien", "ingénieur"]
    for line in lines[1:10]:
        if any(kw in line.lower() for kw in keywords_job):
            return line.strip()
    return "Non précisé"

def extract_from_filename(path):
    name = os.path.basename(path).lower()
    for kw in ["data", "engineer", "ml", "ai", "devops", "fullstack", "frontend", "backend"]:
        if kw in name:
            return kw.capitalize()
    return None

# === 5. Extraction des sections textuelles ===
def extract_section(lines, titles, stops, max_lines=12):
    section = []
    capture = False
    count = 0
    for line in lines:
        upper = line.upper()
        if any(title in upper for title in titles):
            capture = True
            continue
        if capture and (any(stop in upper for stop in stops) or count >= max_lines):
            break
        if capture:
            section.append(line)
            count += 1
    return " ".join(section).strip()

# === 6. Bloc compétences ===
def extract_competence_block(lines):
    competence_titles = ["COMPÉTENCES", "COMPÉTENCES TECHNIQUES", "SKILLS", "APTITUDES"]
    stop_titles = ["EXPERIENCE", "PARCOURS", "PROJETS", "FORMATION", "EDUCATION", "LANGUE", "LANGUAGES", "CERTIFICATIONS", "STAGE"]
    section = []
    capture = False
    for line in lines:
        upper = line.upper()
        if any(title in upper for title in competence_titles):
            capture = True
            section.append(line)
            continue
        if capture and any(stop in upper for stop in stop_titles):
            break
        if capture:
            section.append(line)
    return section

def parse_skills_from_lines(lines):
    skills = set()
    for line in lines:
        parts = re.split(r"[:,;•\-\n]\s*", line)
        for token in parts:
            token = token.strip().lower()
            if 2 <= len(token) <= 40 and not token.isdigit():
                skills.add(token)
    skills.discard("compétences")
    return sorted(skills)

# === 7. Mots-clés techniques (fallback) ===
tech_keywords = [
    "python", "java", "c++", "sql", "mysql", "pandas", "spark", "hadoop", "flink",
    "power bi", "scikit-learn", "matplotlib", "tensorflow", "zookeeper",
    "linux", "ubuntu", "docker", "talend", "ssh", "excel", "javascript", "html", "css"
]

def detect_skills(text, keywords):
    found = set()
    for kw in keywords:
        if kw.lower() in text:
            found.add(kw.lower())
    return sorted(found)

# === 8. Extractions ===
nom = extract_name(lines)
email = extract_email(cleaned_text)
tel = extract_phone(cleaned_text)
adresse = extract_address(lines)

job_title = extract_job_title(lines)
if job_title == "Non précisé":
    job_title = extract_from_filename(file_path) or "Non précisé"

sections = {
    "Formation": extract_section(lines, ["FORMATION", "EDUCATION", "DIPLOME"], ["EXPERIENCE", "COMPETENCE", "LANGUE"]),
    "Expérience": extract_section(lines, ["EXPERIENCE", "STAGE", "WORK", "PARCOURS PROFESSIONNEL"], ["FORMATION", "COMPETENCE", "LANGUE"]),
    "Langues": extract_section(lines, ["LANGUE", "LANGUAGES", "CERTIFICATIONS"], ["INTERET", "HOBBIES"]),
    "Centres d’intérêt": extract_section(lines, ["INTERET", "INTERESTS", "HOBBIES"], [""])
}

competence_lines = extract_competence_block(lines)
competences_bloc = parse_skills_from_lines(competence_lines)
competences_detectees = detect_skills(cleaned_text, tech_keywords)
competences = sorted(set(competences_bloc + competences_detectees))

# === 9. Résultat structuré ===
extracted_data = {
    "Nom": nom,
    "Titre du poste": job_title,
    "Email": email,
    "Téléphone": tel,
    "Adresse": adresse,
    "Formation": sections["Formation"],
    "Expérience": sections["Expérience"],
    "Langues": sections["Langues"],
    "Centres d’intérêt": sections["Centres d’intérêt"],
    "Compétences": competences
}

# === 10. Export JSON ===
with open("./cv_output.json", "w", encoding="utf-8") as f:
    json.dump(extracted_data, f, indent=2, ensure_ascii=False)

# === 11. Affichage terminal ===
for k, v in extracted_data.items():
    print(f"\n== {k} ==")
    if isinstance(v, list):
        print(", ".join(v))
    else:
        print(v)
