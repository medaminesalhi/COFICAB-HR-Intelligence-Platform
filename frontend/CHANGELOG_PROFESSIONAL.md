# Rapport des corrections — COFICAB

## Objectif

Cette version prépare le projet à une évolution MLOps sans intégrer encore MLflow, Docker ou un orchestrateur. Le workflow CV–poste reste prioritaire et les routes métier historiques sont conservées.

## Corrections apportées

### Backend

- Transformation de `app.py` en point d'entrée avec `create_app()` et enregistrement de Blueprints.
- Séparation des routes `auth`, `cv_matching`, `dashboard` et `profiles`.
- Ajout d'utilitaires PostgreSQL avec fermeture de connexion, commit et rollback garantis.
- Réponses d'erreur plus uniformes ; détails d'exceptions non renvoyés au client.
- Configuration centralisée de la base, du JWT, des origines CORS et de la taille maximale des requêtes.
- Refus d'un secret JWT manquant ou trop court en production et refus de `FLASK_DEBUG=true` en production.
- Protection JWT des routes d'extraction, de scoring et de sauvegarde des CV.
- Validation de l'upload PDF (format, taille, contenu), lecture en mémoire et message explicite pour les PDF sans couche texte.
- Extraction CV partagée entre l'API et la CLI ; l'export JSON contenant des données personnelles est désormais opt-in.
- Chargement du modèle en cache plutôt qu'à chaque requête.
- Compatibilité avec les artefacts historiques et prise en charge future d'un pipeline scikit-learn unifié.
- Matching des compétences par expressions complètes plutôt que par mots isolés.
- Séparation de la prédiction ML et de la règle métier historique ; le score est présenté comme indicatif.
- Correction du filtre « profils recommandés uniquement » : une case décochée n'exclut plus les profils non recommandés.
- Correction du score affiché pour les derniers profils du dashboard.
- Remplacement des erreurs serveur détaillées par des messages génériques côté client.
- Import historique de profils rendu idempotent sans suppression de `raw_profiles`.
- Préparation de `ml_ready_profiles` avec upsert plutôt qu'effacement intégral.
- Entraînement historique de profils rendu expérimental, avec cible dérivée documentée et sans écriture dans `scored_profiles`.
- Entraînement CV corrigé pour ajuster le prétraitement uniquement sur le train ; les résultats sont sauvegardés comme candidat et ne remplacent pas le modèle actif.
- Version scikit-learn épinglée à `1.5.1`, version enregistrée dans les avertissements de chargement des artefacts livrés.

### Frontend

- Centralisation de l'URL API sous `/api`.
- Ajout du proxy Angular de développement vers Flask.
- Ajout d'un interceptor JWT et d'un guard pour les pages RH.
- Suppression des URL localhost codées en dur dans les composants.
- Correction de l'acceptation de fichiers : l'interface n'accepte que les PDF, comme le backend.
- Ajout d'une limite de 10 Mo côté navigateur, cohérente avec le backend.
- Libération de l'URL de prévisualisation PDF lors du changement de fichier et de la destruction du composant.
- Déconnexion sans effacer toutes les données du stockage navigateur.
- Mise à jour du titre et de la langue du document HTML, ajout des métadonnées et correction du chemin du logo public.
- Affichage du score comme indicateur de modèle et rappel que la décision finale appartient au RH.

### Documentation et tests

- README racine et README backend réécrits.
- `.gitignore` racine ajouté pour les secrets, fichiers temporaires, builds et datasets locaux.
- Tests unitaires ajoutés pour les features, labels, extraction PDF et contrôles d'accès API.
- `requirements.txt` explicite `bcrypt` pour la vérification des hashes passlib.

## Vérifications effectuées dans l'environnement de travail

- Compilation syntaxique Python : réussie.
- Tests unitaires disponibles : **9 réussis**.
- Tests API Flask : **1 module ignoré**, car Flask et ses extensions ne sont pas installés dans l'environnement de vérification.
- Vérification syntaxique TypeScript via transpilation : réussie.
- Build Angular complet : non exécuté, car `npm ci` n'a pas pu récupérer les dépendances (résolution réseau indisponible dans l'environnement).
- Test de fumée du modèle historique : une prédiction a été produite, mais l'environnement local a signalé que les artefacts ont été entraînés avec scikit-learn 1.5.1 alors que l'environnement de vérification utilise 1.8.0. La dépendance a été alignée sur 1.5.1 ; il faudra réinstaller les dépendances et retester sur Python 3.11/3.12.

## Points à confirmer avant toute utilisation réelle

1. Le schéma exact de la base PostgreSQL et la présence de toutes les tables attendues.
2. L'origine et le sens métier de la cible `recrute` dans le dataset CV–poste.
3. La qualité réelle des annotations RH et la représentativité des données.
4. Le fonctionnement de l'authentification avec un compte RH existant.
5. Le build Angular et les tests API dans l'environnement local après installation des dépendances.
6. Les politiques de conservation et de protection des données personnelles.

## Étape suivante

Une fois cette version vérifiée dans l'environnement local, démarrer le parcours MLOps par la baseline du modèle CV–poste, puis ajouter MLflow Tracking. Le réentraînement automatisé et la promotion en production viendront seulement après validation de la cible, des métriques et des critères d'acceptation.
