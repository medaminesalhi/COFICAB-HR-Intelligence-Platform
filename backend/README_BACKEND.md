# Backend COFICAB — structure organisée (étape 1)

## Objectif de cette version

Cette copie organise les fichiers backend par responsabilité et sépare explicitement les deux workflows historiques :

- **Workflow actif pour notre apprentissage MLOps :** CV PDF + critères de poste → extraction → scoring CV–poste.
- **Workflow conservé hors du périmètre initial :** profils en base, préparation du dataset et dashboard historique.

Les routes API existantes sont conservées dans `app.py` pour limiter les risques de rupture. Le découpage de `app.py` en Blueprints/services sera une étape suivante, après tests de non-régression. Le projet original n'a pas été modifié.

## Arborescence

```text
backend/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── data/
│   ├── cv_matching/training/       # dataset supervisé CV–poste
│   └── profiles/                   # datasets de l'ancien workflow profils
│       ├── raw/
│       └── processed/
├── ml/
│   ├── cv_matching/                # workflow actif
│   │   ├── train_cv.py
│   │   ├── artifacts/               # modèle CV + vectoriseurs compatibles
│   │   └── extraction/scrap_pdf_cv.py
│   └── profiles_pipeline/           # workflow historique, conservé séparément
│       ├── data_pipeline/
│       ├── training/train_model.py
│       └── artifacts/
├── storage/                         # sorties locales non versionnées
└── tests/
```

Les CV PDF historiques, `cv_output.json` (qui contenait des informations personnelles) et `__pycache__` n'ont pas été copiés. `/api/scrape_cv` lit désormais le PDF en mémoire et ne l'enregistre pas durablement.

## Installation

Depuis ce dossier `backend/`, avec Python 3.11 ou 3.12 :

```bash
python -m venv .venv
# Windows PowerShell : .venv\\Scripts\\Activate.ps1
# Linux/macOS : source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copier `.env.example` vers `.env` et adapter les paramètres PostgreSQL/JWT. Ne jamais publier `.env`.

```powershell
Copy-Item .env.example .env
```

Puis lancer l'API depuis le dossier `backend/` :

```bash
python app.py
```

Le backend a besoin d'un serveur PostgreSQL et des tables attendues par les routes. Cette archive ne contient pas la base de données.

## Commandes du workflow CV–poste (notre périmètre MLOps)

Depuis le dossier `backend/` :

```bash
python -m ml.cv_matching.train_cv
python -m ml.cv_matching.extraction.scrap_pdf_cv chemin/vers/cv.pdf
pytest -q
```

Le script d'entraînement CV utilise `data/cv_matching/training/profils_training_balanced.csv` et écrit ses artefacts dans `ml/cv_matching/artifacts/`.

## Workflow profils historique (non prioritaire pour les premières phases)

Ces scripts sont conservés séparément afin de ne pas confondre les modèles et les datasets :

```bash
python -m ml.profiles_pipeline.data_pipeline.prepare_raw
python -m ml.profiles_pipeline.data_pipeline.import_csv_to_raw
python -m ml.profiles_pipeline.data_pipeline.prepare_ml_ready
python -m ml.profiles_pipeline.training.train_model
```

**Ne lance pas ces scripts sans sauvegarder la base et vérifier les tables.** Le code historique supprime/reconstruit des tables (`DELETE FROM raw_profiles`, vidage de `ml_ready_profiles`, `TRUNCATE TABLE scored_profiles`). Ces opérations doivent être corrigées avant usage en production.

## Configuration centralisée

`config.py` contient les chemins et paramètres partagés. Les identifiants sont lus depuis `.env` ou les variables d'environnement. Les artefacts CV et les artefacts du workflow profils sont rangés séparément afin de ne pas mélanger des modèles entraînés pour des objectifs différents.

Les versions de `requirements.txt` sont un point de départ basé sur l'inventaire fourni avec le projet ; elles doivent être testées avec les `.joblib` existants. Des modèles `joblib`/scikit-learn peuvent ne pas être compatibles entre versions.

## Limites connues — prochaines étapes

1. Vérifier la provenance et la définition du label `recrute` dans le dataset CV–poste.
2. Corriger le prétraitement de `train_cv.py` : les vectoriseurs sont actuellement ajustés avant le split train/test.
3. Mesurer une baseline fiable avant tout changement du modèle.
4. Découper `app.py` en Blueprints (`auth`, `profiles`, `cv_matching`) et services sans changer les contrats API.
5. Ajouter les tests d'intégration API et de compatibilité des artefacts.
6. Intégrer MLflow Tracking, puis le registre et les critères de promotion.
7. Ajouter CI, Docker et orchestration après stabilisation.

## Sécurité et données personnelles

Les CSV fournis sont des données de développement et peuvent contenir des informations de profils. Ils sont présents dans cette archive pour conserver le contexte du projet, mais `.gitignore` empêche leur ajout accidentel au dépôt. Ne les pousse pas vers un dépôt public. Les CV PDF historiques et le JSON extrait ont été omis. Vérifier les autorisations et la durée de conservation avant toute collecte ou annotation.
