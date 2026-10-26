import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import classification_report
from scipy.sparse import hstack
import joblib

# 🔹 Charger le dataset équilibré
df = pd.read_csv("profils_training_balanced.csv")

# 🔹 Vectorisation des textes
skills_vectorizer = CountVectorizer()
job_vectorizer = CountVectorizer()
location_vectorizer = CountVectorizer()

X_skills = skills_vectorizer.fit_transform(df['skills'] + " " + df['skills_rh'])
X_job = job_vectorizer.fit_transform(df['jobtitle'] + " " + df['poste_rh'])
X_loc = location_vectorizer.fit_transform(df['location'] + " " + df['location_rh'])

# 🔹 Ajouter les colonnes numériques
X_num = df[['experience', 'exp_min']].fillna(0).astype(int).values

# 🔹 Fusion des features
X = hstack([X_skills, X_job, X_loc, X_num])
y = df['recrute']

# 🔹 Split train/test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 🔹 Entraînement avec équilibrage de classe
model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
model.fit(X_train, y_train)

# 🔹 Évaluation
y_pred = model.predict(X_test)
print("📊 Rapport de classification :")
print(classification_report(y_test, y_pred))

# 🔹 Sauvegarde du modèle et des vectorizers
joblib.dump(model, "ia_recrutement_model.joblib")
joblib.dump(skills_vectorizer, "skills_vectorizer2.joblib")
joblib.dump(job_vectorizer, "job_vectorizer2.joblib")
joblib.dump(location_vectorizer, "location_vectorizer2.joblib")

print("✅ Modèle et vectorizers sauvegardés.")
