# COFICAB HR Intelligence Platform

Plateforme d'aide au recrutement qui permet d'extraire les informations d'un CV PDF, de comparer un candidat aux critères d'un poste et de présenter une évaluation indicative au recruteur.

> Le score du modèle est un indicateur d'aide à l'analyse. La décision finale de recrutement doit rester humaine. La signification du label historique `recrute` doit être confirmée avant de présenter le modèle comme un modèle de compatibilité validé.

## Architecture actuelle

- **Frontend :** Angular 20, TypeScript, Chart.js / ng2-charts.
- **Backend :** Flask, Flask-JWT-Extended, Flask-SQLAlchemy.
- **Base de données :** PostgreSQL.
- **Extraction CV :** PyMuPDF et heuristiques de texte (les PDF scannés nécessitent une étape OCR non incluse).
- **Modèle CV–poste :** scikit-learn, `joblib`, artefacts historiques dans `backend/ml/cv_matching/artifacts/`.
- **Workflow historique de profils :** conservé séparément dans `backend/ml/profiles_pipeline/`.

## Prérequis

- Node.js compatible avec Angular 20 (Node 20.19+ ou 22.12+ recommandé).
- Python 3.11 ou 3.12 pour correspondre aux versions épinglées dans `backend/requirements.txt`.
- PostgreSQL et les tables métier existantes.
- Une base de données initialisée avec le schéma attendu par les endpoints. Cette archive ne contient pas de dump SQL.

## Démarrage local

### 1. Backend

Dans un terminal :

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Modifie `backend/.env` : mot de passe PostgreSQL, clé JWT longue et aléatoire, et origines CORS autorisées. Ne publie jamais ce fichier.

Puis démarre Flask :

```powershell
python app.py
```

L'API est disponible par défaut sur `http://127.0.0.1:5000`. Vérifie `http://127.0.0.1:5000/api/health`.

### 2. Frontend

Dans un autre terminal à la racine :

```powershell
npm ci
npm start
```

Le serveur Angular écoute normalement sur `http://localhost:4200`. `proxy.conf.json` transmet les appels `/api` à Flask. En production, configure un reverse proxy équivalent ; ne conserve pas une URL localhost dans le frontend.

### 3. Tests backend

Depuis `backend/` :

```powershell
pytest -q
```

Certains tests d'API requièrent les dépendances de `requirements.txt`. Les tests unitaires de préparation des features et d'extraction n'ont pas besoin d'une connexion PostgreSQL.

## Workflow prioritaire : CV–poste

1. Authentification du recruteur.
2. Import d'un PDF.
3. Extraction heuristique des informations, à vérifier par l'utilisateur.
4. Saisie des critères du poste.
5. Prédiction avec le modèle disponible et calcul de la règle historique distinctement.
6. Présentation du score indicatif, des compétences communes et des compétences non identifiées.
7. Enregistrement de l'évaluation, si la base est disponible.

Les routes d'extraction, de scoring et de sauvegarde sont protégées par JWT. L'API n'enregistre pas le PDF uploadé par la route d'extraction.

## Démarrage MLOps : ordre prévu

1. Auditer la cible `recrute` et documenter sa provenance.
2. Corriger la préparation et l'évaluation pour éviter les fuites de données.
3. Créer un pipeline scikit-learn unique et reproductible.
4. Ajouter MLflow Tracking et un registre de modèles.
5. Automatiser les tests avec pytest et GitHub Actions.
6. Conteneuriser avec Docker Compose.
7. Orchestrer l'entraînement conditionnel et ajouter le monitoring.

Le script `python -m ml.cv_matching.train_cv` écrit un **candidat de modèle** dans `backend/ml/cv_matching/artifacts/candidates/`. Il ne remplace pas le modèle actif. Le label actuel est historique et sa signification doit être validée avant toute promotion.

## Points à vérifier avant une utilisation réelle

- Compatibilité des artefacts `joblib` avec la version de scikit-learn installée.
- Disponibilité et schéma des tables PostgreSQL : `recruteurs`, `raw_profiles`, `scored_profiles`, `scraped_profiles`, `ml_ready_temp`, `evaluations_ia`.
- Origine des labels et représentativité du dataset.
- Politique de conservation et d'accès aux CV et aux informations personnelles.
- Limites des heuristiques d'extraction : elles ne remplacent pas une validation humaine ni un moteur OCR pour les PDF scannés.
