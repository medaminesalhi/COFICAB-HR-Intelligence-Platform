from pathlib import Path
import pandas as pd
from config import PROFILE_RAW_DATA_DIR, PROFILE_PROCESSED_DATA_DIR

# 📥 Charger le fichier brut (à adapter selon ton chemin local)
input_path = PROFILE_RAW_DATA_DIR / "profils_final_avec_skills.csv"
df = pd.read_csv(input_path)

# ✅ Étape 1 : Supprimer les doublons
df.drop_duplicates(inplace=True)

# ✅ Étape 2 : Supprimer les lignes incomplètes sur les colonnes importantes
df.dropna(subset=[
    "fullName", "jobTitle", "company", "location", 
    "school", "schoolDegree", "anneeDiplome", "nombreStage", "motorise", "skills"
], inplace=True)

# ✅ Étape 3 : Nettoyer les chaînes de texte
text_columns = ["fullName", "jobTitle", "company", "location", "school", "schoolDegree", "motorise", "skills"]
for col in text_columns:
    df[col] = df[col].astype(str).str.strip()

# Uniformiser la casse de "motorise"
df["motorise"] = df["motorise"].str.capitalize()  # Oui / Non

# ✅ Étape 4 : Corriger les types numériques
df["anneeDiplome"] = df["anneeDiplome"].astype(int)
df["nombreStage"] = df["nombreStage"].astype(int)

# ✅ Étape 5 : Remplacer les NaN restants par des chaînes vides
df.fillna("", inplace=True)

# ✅ Étape 6 : Sauvegarder le fichier propre
output_path = PROFILE_PROCESSED_DATA_DIR / "profils_nettoyes.csv"
output_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output_path, index=False)

print(f"✅ Fichier nettoyé enregistré : {output_path}")
