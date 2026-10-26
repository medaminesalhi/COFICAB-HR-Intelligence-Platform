import pandas as pd
import psycopg2

# Charger le fichier nettoyé
df = pd.read_csv("c:/Users/Lenovo/projet/backend/profils_nettoyes.csv")

# Connexion à PostgreSQL
conn = psycopg2.connect(
    dbname="projet_rh",
    user="postgres",
    password="0000",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# Vider la table (optionnel mais recommandé avant réinsertion complète)
cur.execute("DELETE FROM raw_profiles;")

# Insérer les données avec la colonne skills incluse
for _, row in df.iterrows():
    cur.execute("""
        INSERT INTO raw_profiles (
            fullName, jobTitle, company, location, jobDateRange,
            school, schoolDegree, schoolDateRange,
            anneeDiplome, nombreStage, motorise, skills
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        row['fullName'],
        row['jobTitle'],
        row['company'],
        row['location'],
        row.get('jobDateRange', ''),  # au cas où c'est vide
        row['school'],
        row['schoolDegree'],
        row.get('schoolDateRange', ''),  # idem
        int(row['anneeDiplome']),
        int(row['nombreStage']),
        row['motorise'],
        row['skills']
    ))

# Commit et fermeture
conn.commit()
cur.close()
conn.close()

print("✅ Données insérées dans la base projet_rh (table raw_profiles avec skills).")
