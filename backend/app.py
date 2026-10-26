from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from datetime import timedelta
import psycopg2
from flask import request, jsonify
import psycopg2
import re
from datetime import datetime
from flask import request, jsonify
import joblib
import numpy as np
import os
import joblib
model2 = joblib.load("ia_recrutement_model.joblib")
skills_vectorizer2 = joblib.load("skills_vectorizer2.joblib")

def split_skills(text):
    return text.split(", ") if isinstance(text, str) else []
vectorizer = joblib.load("skills_vectorizer.joblib")
model = joblib.load("model_rh_optimized.joblib")

# 🔧 Initialisation app
app = Flask(__name__)
CORS(app)

# PostgreSQL config (pour SQLAlchemy)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:0000@localhost/projet_rh'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT config
app.config['JWT_SECRET_KEY'] = 'ton_super_secret'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# 🔐 Utilisateur RH
class Recruteur(db.Model):
    __tablename__ = 'recruteurs'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(255), nullable=False)
    nom = db.Column(db.String(255))
    role = db.Column(db.String(100))
    created_at = db.Column(db.DateTime)

    def verify_password(self, password):
        return bcrypt.verify(password, self.mot_de_passe)

# 🔐 Connexion RH
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify(success=False, message="Champs manquants"), 400

    recruteur = Recruteur.query.filter_by(email=email).first()
    if recruteur and recruteur.verify_password(password):
        token = create_access_token(identity=recruteur.email)
        return jsonify(success=True, token=token, user={"nom": recruteur.nom, "role": recruteur.role})
    else:
        return jsonify(success=False, message="Identifiants incorrects"), 401

# 🔌 Connexion DB brute (pour requêtes manuelles)
def get_conn():
    return psycopg2.connect(
        dbname="projet_rh",
        user="postgres",
        password="0000",
        host="localhost",
        port="5432"
    )

# 🔐 Exemple route protégée
@app.route('/api/profil-count', methods=['GET'])
@jwt_required()
def profil_count():
    current_user = get_jwt_identity()
    return jsonify(profil_count=120, email=current_user)

# 📊 Données du Dashboard RH
@app.route('/api/dashboard', methods=['GET'])
@jwt_required()
def dashboard_data():
    conn = get_conn()
    cur = conn.cursor()

    # 1. Nombre total de profils
    cur.execute("SELECT COUNT(*) FROM raw_profiles;")
    total_profils = cur.fetchone()[0]

    # 2. Profils recommandés
    cur.execute("SELECT COUNT(*) FROM scored_profiles WHERE prediction = 1;")
    nb_recommandes = cur.fetchone()[0]

    # 3. Moyenne du score
    cur.execute("SELECT ROUND(AVG(score)::numeric, 2) FROM scored_profiles;")
    moyenne_score = cur.fetchone()[0] or 0

    # 4. Derniers profils
    cur.execute("""
        SELECT fullname, jobtitle, score
        FROM scored_profiles ORDER BY id DESC LIMIT 3;
    """)
    nouveaux_profils = [
        {"fullname": f, "jobtitle": j, "score": float(s)}
        for f, j, s in cur.fetchall()
    ]

    # 5. Top métiers
    cur.execute("""
        SELECT jobtitle, COUNT(*) FROM raw_profiles
        GROUP BY jobtitle ORDER BY COUNT(*) DESC LIMIT 5;
    """)
    top_metiers = [{"jobtitle": jt, "total": t} for jt, t in cur.fetchall()]

    # 6. Villes
    cur.execute("""
        SELECT location, COUNT(*) FROM raw_profiles
        GROUP BY location ORDER BY COUNT(*) DESC;
    """)
    repartition_villes = [{"location": loc, "total": c} for loc, c in cur.fetchall()]

    # 7. Diplômes
    cur.execute("""
        SELECT schooldegree, COUNT(*) FROM raw_profiles
        GROUP BY schooldegree ORDER BY COUNT(*) DESC;
    """)
    niveau_etude = [{"schooldegree": d, "total": c} for d, c in cur.fetchall()]

    cur = conn.cursor()

    # ➕ Analyse des compétences

# 1️⃣ Top 10 des compétences globales
    cur.execute("SELECT skills, jobtitle FROM raw_profiles WHERE skills IS NOT NULL;")
    rows = cur.fetchall()

    from collections import Counter, defaultdict

    global_skills_counter = Counter()
    skills_by_job = defaultdict(Counter)

    for skills_str, jobtitle in rows:
        if not skills_str: continue
        skills = [s.strip() for s in skills_str.split(",") if s.strip()]
        global_skills_counter.update(skills)
        skills_by_job[jobtitle].update(skills)

    top_skills = [{"skill": k, "count": v} for k, v in global_skills_counter.most_common(10)]

    # 2️⃣ Répartition des compétences par métier (5 métiers max × 5 skills max)
    skills_per_job = []
    for job, counter in list(skills_by_job.items())[:5]:  # top 5 jobs
        top = counter.most_common(5)
        skills_per_job.append({
            "job": job,
            "skills": [{"skill": s, "count": c} for s, c in top]
        })

    return jsonify({
        "totalProfils": total_profils,
        "nbRecommandes": nb_recommandes,
        "moyenneScore": moyenne_score,
        "nouveauxProfils": nouveaux_profils,
        "topMetiers": top_metiers,
        "repartitionVilles": repartition_villes,
        "niveauEtude": niveau_etude,
        "topSkills": top_skills,
        "skillsPerJob": skills_per_job

    })

@app.route('/api/recherche-profils', methods=['POST'])
@jwt_required()
def recherche_profils():
    data = request.get_json()

    # 🔍 Récupérer et normaliser les filtres reçus
    nom = data.get('nom', '').lower()
    jobtitle = data.get('jobtitle', '').lower()
    location = data.get('location', '').lower()
    schooldegree = data.get('schooldegree', '').lower()
    recommande = data.get('recommande', None)
    min_score = data.get('score', 0)
    skills = data.get('skills', [])

    # 🗃️ Connexion BD
    conn = get_conn()
    cur = conn.cursor()

    # 📦 Construire requête SQL dynamique
    query = """
        SELECT fullname, jobtitle, location, schooldegree, score, prediction, competences
        FROM scored_profiles
        WHERE LOWER(fullname) LIKE %s
          AND LOWER(jobtitle) LIKE %s
          AND LOWER(location) LIKE %s
          AND LOWER(schooldegree) LIKE %s
          AND score >= %s
    """
    params = [
        f'%{nom}%',
        f'%{jobtitle}%',
        f'%{location}%',
        f'%{schooldegree}%',
        min_score
    ]

    if recommande is not None:
        query += " AND prediction = %s"
        params.append(1 if recommande else 0)

    # ✅ Traitement des compétences cochées
    if skills:
        for skill in skills:
            query += " AND competences ILIKE %s"
            params.append(f'%{skill}%')

    # 🚀 Exécution de la requête
    cur.execute(query, params)
    rows = cur.fetchall()

    # 🔄 Fermeture de la connexion
    cur.close()
    conn.close()

    # ✅ Formatage clair des résultats JSON
    profils = [{
        "fullname": r[0],
        "jobtitle": r[1],
        "location": r[2],
        "schooldegree": r[3],
        "score": float(r[4]),
        "prediction": bool(r[5]),
        "competences": [s.strip() for s in r[6].split(",")] if r[6] else []
    } for r in rows]

    return jsonify(profils=profils)


@app.route('/api/metiers', methods=['GET'])
@jwt_required()
def get_metiers():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT jobtitle FROM scored_profiles WHERE jobtitle IS NOT NULL ORDER BY jobtitle ASC;")
    metiers = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(metiers=metiers)

@app.route('/api/diplomes', methods=['GET'])
@jwt_required()
def get_diplomes():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT schooldegree FROM scored_profiles WHERE schooldegree IS NOT NULL ORDER BY schooldegree ASC;")
    diplomes = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(diplomes=diplomes)



@app.route('/api/save_profile', methods=['POST'])
def save_profile():
    data = request.get_json()

    # 🔹 Données scrappées
    nom = data.get("nom", "").strip().title()
    jobtitle = data.get("jobtitle", "").strip().lower()
    email = data.get("email", "").strip().lower()
    telephone = data.get("telephone", "")
    adresse = data.get("adresse", "")
    competences = ", ".join(data.get("competences", [])) if isinstance(data.get("competences"), list) else data.get("competences", "")
    competences = competences.lower().strip()
    formation = data.get("formation", "")
    experience = data.get("experience", "")
    langues = data.get("langues", "")
    centres = data.get("centres", "")

    # 🔹 Données du formulaire IA
    poste_rh = data.get("poste_rh", "")
    skills_rh = data.get("skills_rh", "")
    location_rh = data.get("location_rh", "")
    exp_min = data.get("exp_min", 0)
    exp_candidat = data.get("exp_candidat", 0)

    try:
        conn = psycopg2.connect(
            dbname="projet_rh",
            user="postgres",
            password="0000",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()

        # ➕ Insert complet dans scraped_profiles (historique)
        cur.execute("""
            INSERT INTO scraped_profiles
            (nom, jobtitle, email, telephone, adresse, competences, formation, experience, langues, centres,
             poste_rh, skills_rh, location_rh, exp_min, exp_candidat)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            nom, jobtitle, email, telephone, adresse, competences, formation, experience, langues, centres,
            poste_rh, skills_rh, location_rh, exp_min, exp_candidat
        ))

        # ➕ Insert dans ml_ready_temp (préparation pour IA)
        cur.execute("""
            INSERT INTO ml_ready_temp
            (nom, competences, location, experience, poste, skills_rh, location_rh, exp_min)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            nom, competences, adresse, exp_candidat, poste_rh, skills_rh, location_rh, exp_min
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"success": True, "message": "Profil enregistré et prêt pour IA."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/scrape_cv', methods=['POST'])
def scrape_cv():
    import fitz, os, re
    from flask import request, jsonify
    from werkzeug.utils import secure_filename

    if 'cv' not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    file = request.files['cv']
    filename = secure_filename(file.filename)
    filepath = os.path.join("temp_cv", filename)
    os.makedirs("temp_cv", exist_ok=True)
    file.save(filepath)

    doc = fitz.open(filepath)
    text = "".join([page.get_text() for page in doc])
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    cleaned_text = " ".join(lines).lower()

    def extract_email(text):
        match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        return match.group(0) if match else "Non trouvé"

    def extract_phone(text):
        match = re.search(r"\+?\(?\d{2,4}\)?[\s.-]?\d{2,3}[\s.-]?\d{2,3}[\s.-]?\d{2,4}", text)
        return match.group(0) if match else "Non trouvé"

    def extract_name(lines):
        for line in lines[:10]:
            if line.isupper() and not any(char.isdigit() for char in line):
                if not any(w in line.lower() for w in ["experience", "education", "skills", "project"]):
                    return line.strip().title()
            if re.match(r"[A-Z][a-z]+ [A-Z][a-z]+", line):
                return line.strip()
        return "Non trouvé"

    def extract_job_title(lines):
        keywords_job = ["data", "engineer", "developer", "devops", "cloud", "ai", "ml", "full stack", "frontend", "backend", "technicien", "ingénieur"]
        for line in lines[1:10]:
            if any(kw in line.lower() for kw in keywords_job):
                return line.strip()
        return "Non précisé"

    def extract_address(lines):
        for line in lines:
            if any(kw in line.lower() for kw in ["cite", "rue", "avenue", "adresse", "tunis"]):
                return line
        return "Non trouvé"

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

    def extract_competence_block(lines):
        competence_titles = ["COMPÉTENCES", "COMPÉTENCES TECHNIQUES", "SKILLS", "APTITUDES"]
        stop_titles = ["EXPERIENCE", "PARCOURS", "PROJETS", "FORMATION", "EDUCATION", "LANGUE"]
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
            parts = re.split(r"[:,;•\\-\\n]\\s*", line)
            for token in parts:
                token = token.strip().lower()
                if 2 <= len(token) <= 40 and not token.isdigit():
                    skills.add(token)
        skills.discard("compétences")
        return sorted(skills)

    def detect_skills(text, keywords):
        return sorted({kw for kw in keywords if kw.lower() in text})

    tech_keywords = [
        "python", "java", "c++", "sql", "mysql", "pandas", "spark", "hadoop", "flink",
        "power bi", "scikit-learn", "matplotlib", "tensorflow", "zookeeper",
        "linux", "ubuntu", "docker", "talend", "ssh", "excel", "javascript", "html", "css"
    ]

    nom = extract_name(lines)
    email = extract_email(cleaned_text)
    tel = extract_phone(cleaned_text)
    adresse = extract_address(lines)
    job_title = extract_job_title(lines)

    sections = {
        "Formation": extract_section(lines, ["FORMATION", "EDUCATION"], ["EXPERIENCE", "COMPETENCE"]),
        "Expérience": extract_section(lines, ["EXPERIENCE", "STAGE"], ["FORMATION", "COMPETENCE"]),
        "Langues": extract_section(lines, ["LANGUE", "LANGUAGES"], ["INTERET", "HOBBIES"]),
        "Centres d’intérêt": extract_section(lines, ["INTERET", "HOBBIES"], [""])
    }

    competence_lines = extract_competence_block(lines)
    competences_bloc = parse_skills_from_lines(competence_lines)
    competences_detectees = detect_skills(cleaned_text, tech_keywords)
    competences = sorted(set(competences_bloc + competences_detectees))

    extracted_data = {
        "nom": nom,
        "jobtitle": job_title,
        "email": email,
        "telephone": tel,
        "adresse": adresse,
        "formation": sections["Formation"],
        "experience": sections["Expérience"],
        "langues": sections["Langues"],
        "centres": sections["Centres d’intérêt"],
        "competences": competences
    }
    return jsonify(extracted_data)
@app.route('/api/predict_match', methods=['POST'])
def predict_match():
    import joblib
    import numpy as np
    from scipy.sparse import hstack
    import psycopg2
    import re

    # === 🔁 Charger modèle + vectorizers ===
    model2 = joblib.load("ia_recrutement_model.joblib")
    skills_vectorizer2 = joblib.load("skills_vectorizer2.joblib")
    job_vectorizer2 = joblib.load("job_vectorizer2.joblib")
    location_vectorizer2 = joblib.load("location_vectorizer2.joblib")

    # === 📥 Données reçues ===
    data = request.get_json()
    candidat = data.get("candidat", {})
    criteres = data.get("criteres", {})

    # === 🧽 Nettoyage texte ===
    def normalize_text(val):
        if isinstance(val, list):
            return " ".join([str(v).strip().lower() for v in val])
        return str(val).strip().lower()
    

    

    def clean_text(text):
        return re.sub(r"[^\w\s]", " ", text).lower()

    def normalize_skills(raw):
        if isinstance(raw, list):
            raw = " ".join(raw)
        raw = raw.lower()
        raw = re.sub(r"[^\w\s]", " ", raw)  # supprime ponctuation
        raw = re.sub(r"\s+", " ", raw)      # espaces multiples
        tokens = [t.strip() for t in raw.split(" ") if len(t.strip()) > 1]
        return set(tokens)

    # === ✅ Matching des compétences ===
    candidat_list = normalize_skills(candidat.get("competences", []))
    rh_list = normalize_skills(criteres.get("skills", ""))

    matching_skills = candidat_list & rh_list
    nb_match = len(matching_skills)

    # === 🔠 Concaténation pour IA ===
    skills_text = clean_text(normalize_text(candidat.get("competences", [])) + " " + normalize_text(criteres.get("skills", "")))
    job_text = clean_text(normalize_text(candidat.get("jobtitle", "")) + " " + normalize_text(criteres.get("poste", "")))
    location_text = clean_text(normalize_text(candidat.get("location", "")) + " " + normalize_text(criteres.get("location", "")))

    # === 🔢 Numériques ===
    try:
        exp_candidat = int(candidat.get("experience", 0))
    except:
        exp_candidat = 0
    try:
        exp_min = int(criteres.get("experience", 0))
    except:
        exp_min = 0

    # === 📊 Vectorisation ===
    X_skills = skills_vectorizer2.transform([skills_text])
    X_job = job_vectorizer2.transform([job_text])
    X_loc = location_vectorizer2.transform([location_text])
    X_num = np.array([[exp_candidat, exp_min]])
    X = hstack([X_skills, X_job, X_loc, X_num])

    # === 🧠 Prédiction IA ===
    prediction = model2.predict(X)[0]
    proba = model2.predict_proba(X)[0][1]
    score_ia = round(proba * 100)

    # === ✅ Logique RH (3 compétences suffisent)
    logique_rh = nb_match >= 3
    is_recommande = bool(prediction) or logique_rh

    # === 💬 Message final explicatif
    message = f"""
🔍 Résultat IA :
📌 Score IA : {score_ia}% de compatibilité.
🧠 Compétences communes détectées : {nb_match} sur {len(rh_list)} attendues.
"""

    if matching_skills:
        message += "✅ Compétences correspondantes : " + ", ".join(sorted(matching_skills)) + "\n"

    if is_recommande:
        message += "✅ Résultat : Ce profil est recommandé pour ce poste."
    else:
        message += "❌ Résultat : Ce profil ne répond pas suffisamment aux critères."

    # === 🗃️ Stockage PostgreSQL
    try:
        conn = psycopg2.connect(
            dbname="projet_rh",
            user="postgres",
            password="0000",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO evaluations_ia (
                nom, jobtitle, email, telephone, adresse,
                competences, formation, experience, langues, centres,
                poste_rh, skills_rh, location_rh, exp_min, exp_candidat,
                score_ia, recommande
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            candidat.get("nom", ""), candidat.get("jobtitle", ""), candidat.get("email", ""), candidat.get("telephone", ""),
            candidat.get("adresse", ""), normalize_text(candidat.get("competences", [])),
            candidat.get("formation", ""), candidat.get("experience", ""), candidat.get("langues", ""), candidat.get("centres", ""),
            criteres.get("poste", ""), criteres.get("skills", ""), criteres.get("location", ""),
            exp_min, exp_candidat, score_ia, is_recommande
        ))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("❌ Erreur stockage Postgre :", e)

    # === 🔁 Retour final
    return jsonify({
        "success": True,
        "recommande": is_recommande,
        "score": score_ia,
        "message": message.strip()
    })



# ✅ Lancement du serveur
if __name__ == '__main__':
    app.run(debug=True)

