# Backend COFICAB

## 1. Responsabilités

Le backend Flask fournit l'API utilisée par Angular. Le workflow prioritaire pour la suite MLOps est :

**CV PDF + critères du poste → extraction → prédiction CV–poste → revue RH.**

Le workflow de profils en base et son dashboard sont conservés dans `ml/profiles_pipeline/`, mais restent hors du périmètre MLOps initial.

## 2. Structure

```text
backend/
├── app.py                         # Factory Flask, configuration et enregistrement des routes
├── config.py                      # Chemins, PostgreSQL, JWT, CORS et limites d'upload
├── extensions.py                  # Extensions Flask partagées
├── models.py                      # Modèle SQLAlchemy Recruteur
├── db_utils.py                    # Connexion PostgreSQL transactionnelle
├── routes/
│   ├── auth.py                    # /api/login
│   ├── cv_matching.py             # /api/scrape_cv et /api/predict_match
│   ├── dashboard.py               # Dashboard historique
│   └── profiles.py                # Recherche, filtres et sauvegarde des profils
├── services/
│   ├── cv_extraction.py           # Extraction PDF partagée par API et CLI
│   └── cv_model_service.py        # Chargement en cache et inférence du modèle
├── ml/
│   ├── cv_matching/
│   │   ├── features.py             # Préparation commune des features train/inférence
│   │   ├── train_cv.py             # Entraîne un candidat, ne remplace pas le modèle actif
│   │   ├── extraction/scrap_pdf_cv.py
│   │   └── artifacts/              # Artefacts historiques actifs et candidats locaux
│   └── profiles_pipeline/          # Workflow historique séparé
├── data/                           # Datasets locaux de développement
├── storage/                        # Sorties locales ; CV temporaires non versionnés
└── tests/                          # Tests unitaires et tests API
```

## 3. Installation locale

Depuis ce dossier :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Modifiez `.env` avant de lancer le backend. Utilisez un mot de passe PostgreSQL valide et une clé JWT longue et aléatoire. En production, `APP_ENV=production` sans clé JWT configurée bloque le démarrage.

Démarrer l'API :

```powershell
python app.py
```

Test de santé : `http://127.0.0.1:5000/api/health`.

Les tables PostgreSQL doivent déjà exister. Cette archive ne contient pas de migration ou de dump SQL permettant de garantir le schéma de la base.

## 4. Endpoints

| Endpoint | Authentification | Fonction |
|---|---|---|
| `POST /api/login` | Non | Authentification du recruteur |
| `GET /api/health` | Non | Vérification de disponibilité de l'API |
| `POST /api/scrape_cv` | JWT | Extraction heuristique d'un CV PDF |
| `POST /api/predict_match` | JWT | Score indicatif CV–poste et sauvegarde de l'évaluation |
| `POST /api/save_profile` | JWT | Sauvegarde du profil extrait |
| `GET /api/dashboard` | JWT | Indicateurs du workflow historique |
| `POST /api/recherche-profils` | JWT | Recherche et filtres sur les profils |
| `GET /api/metiers` | JWT | Liste des métiers |
| `GET /api/diplomes` | JWT | Liste des diplômes |

Les réponses d'erreur utilisent `success: false` et `message`. Les PDF sont lus en mémoire par l'API ; la limite par défaut est 10 Mo. Les PDF scannés sans couche texte ne sont pas traités par OCR.

## 5. Modèle CV–poste

Le service de prédiction prend en charge deux modes :

1. le modèle historique et ses trois vectoriseurs, pour assurer la compatibilité avec l'archive actuelle ;
2. un pipeline scikit-learn unifié nommé `cv_matching_pipeline.joblib`, lorsqu'une version candidate aura été examinée et explicitement promue.

Les artefacts sont chargés en cache, pas à chaque requête. Pour appliquer une nouvelle version, redémarrez le backend après la promotion contrôlée. La version historique est indiquée `legacy-unversioned`, car aucun manifeste fiable n'était fourni avec les anciens artefacts.

### Entraîner un candidat

Depuis `backend/` :

```powershell
python -m ml.cv_matching.train_cv
```

Le script vérifie le schéma, sépare les données avant l'ajustement du prétraitement, utilise un `Pipeline`, calcule les métriques et écrit un candidat sous `ml/cv_matching/artifacts/candidates/`. Il ne remplace pas le modèle actif.

**Important :** le dataset actuel possède 500 lignes et une cible `recrute` équilibrée, mais la provenance de cette cible n'est pas documentée. Les métriques obtenues ne prouvent pas que le modèle prédit une compatibilité ou un recrutement réel. Validez la signification des labels et les données avant toute promotion.

## 6. Tests

```powershell
pytest -q
```

Les tests vérifient la configuration, la validation des colonnes/features, l'extraction PDF de base et les contrôles d'accès API. Les tests API sont ignorés si les dépendances Flask ne sont pas installées.

## 7. Sécurité

- Ne versionnez pas `.env`, les CV, les JSON d'extraction ou les CSV pouvant contenir des données personnelles.
- Les endpoints CV et les opérations de sauvegarde sont protégés par JWT.
- CORS est limité aux origines configurées dans `.env`.
- Les fichiers uploadés sont soumis à une limite de taille et l'API n'enregistre pas le PDF brut.
- Les erreurs serveur sont journalisées côté serveur sans renvoyer les détails d'exception au client.
- Le score est indicatif. Le recruteur conserve la décision finale.
- Pour une production réelle, prévoir politique de conservation, contrôle d'accès, gestion des secrets, limitation de débit, sauvegardes et audit de sécurité.

## 8. Limites connues et prochaines étapes MLOps

1. Confirmer la définition et l'origine des labels.
2. Vérifier la compatibilité des artefacts `.joblib` avec les versions de Python/scikit-learn installées.
3. Ajouter un schéma d'annotation RH pour les couples candidat–poste.
4. Intégrer MLflow Tracking puis le registre de modèles.
5. Ajouter les tests de non-régression, CI, Docker et orchestration.
6. Ajouter un monitoring de qualité et de dérive lorsque des données de référence sont disponibles.

Le workflow historique `profiles_pipeline` est conservé pour le contexte, mais son label `recrute` est dérivé de `nombrestage >= 2`. Son entraînement a été rendu explicitement expérimental et n'écrit plus dans les tables de scores actives par défaut.
