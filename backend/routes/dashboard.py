"""Endpoints de synthèse du dashboard historique des profils."""
from collections import Counter, defaultdict

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from db_utils import database_connection

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api")


@dashboard_bp.get("/profil-count")
@jwt_required()
def profil_count():
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM raw_profiles;")
            count = int(cursor.fetchone()[0])
    return jsonify(profil_count=count, email=get_jwt_identity())


@dashboard_bp.get("/dashboard")
@jwt_required()
def dashboard_data():
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM raw_profiles;")
            total_profiles = int(cursor.fetchone()[0] or 0)

            cursor.execute("SELECT COUNT(*) FROM scored_profiles WHERE prediction = 1;")
            recommended = int(cursor.fetchone()[0] or 0)

            cursor.execute("SELECT AVG(score) FROM scored_profiles;")
            average_score = float(cursor.fetchone()[0] or 0)

            cursor.execute("""
                SELECT fullname, jobtitle, score
                FROM scored_profiles
                ORDER BY id DESC
                LIMIT 3;
            """)
            recent_profiles = [
                {"fullname": name or "Non renseigné", "jobtitle": title or "Non renseigné",
                 "score": round(float(score or 0) * 100, 1)}
                for name, title, score in cursor.fetchall()
            ]

            cursor.execute("""
                SELECT jobtitle, COUNT(*) AS total
                FROM raw_profiles
                WHERE jobtitle IS NOT NULL AND BTRIM(jobtitle) <> ''
                GROUP BY jobtitle
                ORDER BY total DESC, jobtitle ASC
                LIMIT 5;
            """)
            top_jobs = [
                {"jobtitle": title, "total": int(total)}
                for title, total in cursor.fetchall()
            ]

            cursor.execute("""
                SELECT location, COUNT(*) AS total
                FROM raw_profiles
                WHERE location IS NOT NULL AND BTRIM(location) <> ''
                GROUP BY location
                ORDER BY total DESC, location ASC
                LIMIT 12;
            """)
            cities = [
                {"location": location, "total": int(total)}
                for location, total in cursor.fetchall()
            ]

            cursor.execute("""
                SELECT schooldegree, COUNT(*) AS total
                FROM raw_profiles
                WHERE schooldegree IS NOT NULL AND BTRIM(schooldegree) <> ''
                GROUP BY schooldegree
                ORDER BY total DESC, schooldegree ASC
                LIMIT 12;
            """)
            education = [
                {"schooldegree": degree, "total": int(total)}
                for degree, total in cursor.fetchall()
            ]

            cursor.execute("SELECT skills, jobtitle FROM raw_profiles WHERE skills IS NOT NULL;")
            skill_rows = cursor.fetchall()

    global_counter = Counter()
    skills_by_job = defaultdict(Counter)
    for skills_value, job_title in skill_rows:
        if not skills_value:
            continue
        skills = [item.strip() for item in str(skills_value).split(",") if item.strip()]
        global_counter.update(skills)
        if job_title:
            skills_by_job[str(job_title)].update(skills)

    top_skills = [
        {"skill": skill, "count": int(count)}
        for skill, count in global_counter.most_common(10)
    ]
    top_job_names = [item["jobtitle"] for item in top_jobs]
    skills_per_job = [
        {
            "job": job,
            "skills": [
                {"skill": skill, "count": int(count)}
                for skill, count in skills_by_job[job].most_common(5)
            ],
        }
        for job in top_job_names
    ]

    return jsonify({
        "totalProfils": total_profiles,
        "nbRecommandes": recommended,
        "moyenneScore": round(average_score, 4),
        "nouveauxProfils": recent_profiles,
        "topMetiers": top_jobs,
        "repartitionVilles": cities,
        "niveauEtude": education,
        "topSkills": top_skills,
        "skillsPerJob": skills_per_job,
    })
