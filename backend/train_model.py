import pandas as pd
import psycopg2
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from scipy.sparse import hstack, csr_matrix
import joblib

# Connexion PostgreSQL
conn = psycopg2.connect(
    dbname="projet_rh",
    user="postgres",
    password="0000",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# Lecture des données
print("[INFO] Lecture des données...")
df = pd.read_sql("SELECT * FROM ml_ready_profiles", conn)

# Encoder niveau_etude
def encoder_niveau_etude(text):
    if not isinstance(text, str):
        return 0
    text = text.lower()
    if "ing" in text:
        return 3
    elif "master" in text or "mba" in text:
        return 2
    elif "licence" in text:
        return 1
    else:
        return 0

df["niveau_etude_enc"] = df["schooldegree"].apply(encoder_niveau_etude)

# Vectoriser les skills (TF-IDF)
print("[INFO] Vectorisation des skills (TF-IDF)...")
def split_skills(text):
    return text.split(", ") if isinstance(text, str) else []

vectorizer = TfidfVectorizer(tokenizer=split_skills, max_features=200)
X_skills = vectorizer.fit_transform(df["skills"].astype(str))

# Sauvegarde du vectorizer
joblib.dump(vectorizer, "skills_vectorizer.joblib")

# Features numériques/encodées
X_numeric = df[[
    "jobtitle", "company", "location", "school", "schooldegree",
    "anneediplome", "nombrestage", "motorise", "annee_experience",
    "mobilite", "niveau_etude_enc", "profil_senior"
]]

# Normalisation
scaler = StandardScaler()
X_numeric_scaled = scaler.fit_transform(X_numeric)
joblib.dump(scaler, "numeric_scaler.joblib")

# Fusion des features finales
X_final = hstack([csr_matrix(X_numeric_scaled), X_skills])
y = df["recrute"]

# Split train/test
X_train, X_test, y_train, y_test = train_test_split(
    X_final, y, test_size=0.2, random_state=42, stratify=y
)

# Entraînement amélioré du modèle avec paramètres optimisés
print("[INFO] Entraînement optimisé du RandomForest...")
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    class_weight='balanced'
)
model.fit(X_train, y_train)

# Evaluation
print("[RESULT] Evaluation du modèle :")
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))
print("[RESULT] Précision globale :", accuracy_score(y_test, y_pred))

# Sauvegarde du modèle
joblib.dump(model, "model_rh_optimized.joblib")
print("[INFO] Modèle sauvegardé sous model_rh_optimized.joblib")

# Prédictions
predictions = model.predict(X_final)
probas = model.predict_proba(X_final)[:, 1]
df["prediction"] = predictions
df["score"] = probas

# Nettoyage de la table scored_profiles
cur.execute("TRUNCATE TABLE scored_profiles;")

# Lecture des données depuis raw_profiles
raw_df = pd.read_sql("SELECT id, fullname, jobtitle, company, location, school, schooldegree, nombrestage, motorise FROM raw_profiles", conn)

# Fusion
df_merge = pd.merge(df, raw_df, on="id", how="left")

# Insertion dans scored_profiles
print("[INFO] Insertion dans scored_profiles...")
for _, row in df_merge.iterrows():
    cur.execute("""
        INSERT INTO scored_profiles (
            id, fullname, jobtitle, company, location, school,
            schooldegree, nombrestage, motorise, score, model_version, prediction
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        int(row["id"]),
        row["fullname"],
        row["jobtitle_y"],
        row["company_y"],
        row["location_y"],
        row["school_y"],
        row["schooldegree_y"],
        int(row["nombrestage_y"]),
        row["motorise_y"],
        float(row["score"]),
        "v3",
        int(row["prediction"])
    ))

conn.commit()
cur.close()
conn.close()

print("[INFO] Modèle amélioré entraîné et scores insérés dans scored_profiles.")