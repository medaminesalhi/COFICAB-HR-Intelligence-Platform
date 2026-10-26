import pandas as pd
import psycopg2
from sklearn.preprocessing import LabelEncoder

# Connexion PostgreSQL
conn = psycopg2.connect(
    dbname="projet_rh",
    user="postgres",
    password="0000",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# 📥 Lire depuis raw_profiles
df = pd.read_sql("SELECT * FROM raw_profiles", conn)

# ✅ Nettoyer les skills : texte brut
df["skills"] = df["skills"].fillna("").astype(str).str.strip()

# 🧠 Calcul des features supplémentaires
df["annee_experience"] = 2025 - df["anneediplome"]

def est_mobile(row):
    location = str(row["location"]).lower()
    motorise = str(row["motorise"]).lower()
    return 1 if "tunis" not in location or motorise == "oui" else 0

df["mobilite"] = df.apply(est_mobile, axis=1)

# 🧠 Encodage LabelEncoder sur colonnes texte
cols_to_encode = ["jobtitle", "company", "location", "school", "schooldegree", "motorise"]
encoders = {}
for col in cols_to_encode:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col].astype(str))
    encoders[col] = le

# 🧠 Simplification niveau d’étude
def simplifier_niveau(code):
    try:
        txt = encoders["schooldegree"].inverse_transform([code])[0].lower()
        if "licence" in txt:
            return "Licence"
        elif "master" in txt or "mba" in txt or "ingénieur" in txt:
            return "Master"
        else:
            return "Autre"
    except:
        return "Autre"

df["niveau_etude"] = df["schooldegree"].apply(simplifier_niveau)

# 🧠 Profil senior + cible
df["profil_senior"] = df.apply(lambda row: 1 if row["annee_experience"] >= 3 and row["nombrestage"] >= 2 else 0, axis=1)
df["recrute"] = df["nombrestage"].apply(lambda x: 1 if x >= 2 else 0)

# ✅ Construction du dataframe final
df_final = df[[
    "id", "jobtitle", "company", "location", "school",
    "schooldegree", "anneediplome", "nombrestage", "motorise",
    "annee_experience", "mobilite", "niveau_etude", "profil_senior", "recrute", "skills"
]]

# 🔁 Vider la table ml_ready_profiles
cur.execute("DELETE FROM ml_ready_profiles;")

# ✅ Insertion dans PostgreSQL
for row in df_final.itertuples(index=False):
    cur.execute("""
        INSERT INTO ml_ready_profiles (
            id, jobtitle, company, location, school,
            schooldegree, anneediplome, nombrestage, motorise,
            annee_experience, mobilite, niveau_etude, profil_senior, recrute, skills
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, tuple(row))

# 🔐 Commit et fermer
conn.commit()
cur.close()
conn.close()

print("✅ Table ml_ready_profiles remplie avec succès (skills inclus).")
