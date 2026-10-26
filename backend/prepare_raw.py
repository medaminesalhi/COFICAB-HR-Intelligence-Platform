import pandas as pd

# 📥 Charger le fichier brut (à adapter selon ton chemin local)
df = pd.read_csv("c:/Users/Lenovo/projet/backend/profils_final_avec_skills.csv")

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
df.to_csv("c:/Users/Lenovo/projet/backend/profils_nettoyes.csv", index=False)

print("✅ Fichier nettoyé enregistré sous profils_nettoyes.csv")
