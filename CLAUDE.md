# Projet — Agent IA pour sessions de JDR (Metal Adventures 1.5)

Contexte **stable** du projet, chargé à chaque session. Pour l'avancement courant, voir `PROGRESS.md`.

## Objectif
Assistant du meneur pendant une partie : produire les répliques des PNJ en cohérence avec (a) leur personnalité, (b) le contexte de scène, (c) les règles du jeu, (d) les interactions du joueur. Exigences : maintenable, fiable, couvert par des tests.

## Workflow de session (IMPORTANT)
- **Début de session** : lire d'abord `PROGRESS.md` → section « Reprise rapide ».
- **Fin de session** : mettre à jour `PROGRESS.md` (état, cases à cocher, journal des décisions), puis committer.
- `CLAUDE.md` = stable (rarement modifié). `PROGRESS.md` = vivant (modifié chaque session).

## Stack (figée le 2026-11-14)
- Langage : **Python**.
- IHM : **CLI** et **interface web locale** (FastAPI + page HTML/JS sans étape de build ni CDN) → le cœur reste indépendant de l'IHM.
- Règles : **index SQLite FTS5** interrogé par un outil `rechercher_regle` (aucun service externe).
- LLM : **fournisseur et modèle choisis dans `config.yaml`**, séparément pour le dialogue et les questions de règles : Anthropic (API Messages ; défaut `claude-haiku-5-5` pour le dialogue, `claude-sonnet-5-5` pour les questions de règles) ou OpenAI (API Responses). Réflexion, cache, tool use dans les deux cas.

## Configuration
Tout réglage modifiable à la main est dans **`config.yaml`** (racine), noms en français, commentés, pensé pour un non-développeur : modèles, niveau de réflexion, longueurs, nombre de passages, **consignes données au modèle**, chemins. Aucune valeur par défaut cachée dans le code : un réglage manquant ou mal écrit est refusé avec un message en français. Le cœur reçoit ses réglages en paramètre ; seules les commandes lisent le fichier (`core/config.py`). Les tests utilisent leur propre configuration (`tests/reglages_test.py`), pour que l'édition de `config.yaml` ne les casse pas.

## Architecture
Règle de dépendance absolue : `interfaces/` dépend de `core/`, **jamais l'inverse**. Le web réutilise le `core/` tel quel. Seuls les modules `core/fournisseurs/fournisseur_*.py` importent un SDK (`anthropic`, `openai`) ; un test le vérifie.

```
config.yaml              # configuration (modèles, consignes, chemins)
modeles.yaml             # catalogue des modèles proposés par le web, par fournisseur
agent_jdr/
  core/                  # cœur réutilisable, zéro dépendance IHM
    config.py            # lecture + validation de config.yaml
    fournisseurs/        # seul endroit qui importe un SDK (anthropic, openai)
      base.py            # interface commune + erreurs communes
      fournisseur_anthropic.py  fournisseur_openai.py
    personas/            # PNJ en YAML (données versionnées), un fichier = un id
    persona.py           # schéma PNJ (pydantic) + chargement YAML
    scene.py             # état de scène (contexte), sérialisable
    rules_index.py       # construction + requête FTS5 (filtre par livres cochés : regles.livres_utilises)
    rules_extract.py     # PDF → passages (build seulement, seul import de PyMuPDF)
    livres.py            # état des PDF, ajout d'un PDF, reconstruction de l'index (processus séparé)
    historique.py        # historique des questions de règles (JSON, une par fichier)
    prompt_builder.py    # assemblage persona + scène + historique (format neutre)
    dialogue_engine.py   # boucle tool use, indépendante du fournisseur
    sessions.py          # sessions de dialogue persistantes (JSON, une par fichier)
    edition_config.py    # écriture de config.yaml / secrets.yaml (commentaires conservés, validation avant écriture) ; choix des livres
    modele_pnj.yaml      # fiche pré-remplie du formulaire « Nouveau PNJ »
  interfaces/
    cli.py               # client mince
    web/app.py           # API HTTP (FastAPI), client mince ; static/ = index.html, app.js, style.css
  data/rules.db          # index FTS5 généré depuis les PDF (régénérable)
  tests/
    unit/  retrieval/  orchestration/  evals/
```

## Stratégie de tests (4 couches)
1. **unit** — déterministe, sans LLM : personas (schéma), état de scène, assembleur, parsing.
2. **retrieval** — requête → passage attendu de l'index FTS5.
3. **orchestration** — client Anthropic mocké : bon appel de l'outil règles, boucle tool use, historique ; API web (`TestClient`, fabrique de fournisseur injectée).
4. **evals** — LLM réel, scénarios figés : reste en personnage, ne révèle pas ses secrets, consulte les règles au bon moment.

Couches 1–3 à chaque commit ; couche 4 à part (plus lente/coûteuse). Les couches 1–3 couvrent les deux fournisseurs (clients mockés, vrais types des SDK).

## Commandes
Gestionnaire : **uv** (`pyproject.toml`). PyMuPDF est une dépendance de *build* uniquement (groupe `build`) : seul `core/rules_extract.py` l'importe, jamais l'agent en exécution. Le web reconstruit l'index en lançant `rules_index build` dans un processus séparé (`core/livres.py`).

- Installation : `uv sync` ; sous Windows, double-clic sur `installer-windows.bat` (installe uv, puis `uv sync`, crée `secrets.yaml` s'il manque, affiche `uv run web`). Fins de ligne CRLF imposées par `.gitattributes` ; vérifié par `tests/unit/test_installation_windows.py`.
- Construire l'index des règles (≈ 8 s) : `uv run python -m agent_jdr.core.rules_index build`
- Question de règles (réponse en français + sources citées, appel au modèle, nécessite la clé `recherche-apikey`) : `uv run python -m agent_jdr.core.rules_index search "expliques moi la dispersion d'une grenade"` (`-n 8` = passages envoyés au modèle)
- Débogage de la recherche (liste des passages, sans appel LLM) : `uv run python -m agent_jdr.core.rules_index search "faire le plein" --brut -n 5`
- Raccourci, mêmes options : `uv run search "faire le plein"` (entrée `[project.scripts]`).
- Parler à un PNJ (appel au modèle, nécessite la clé `personas-apikey`) : `uv run parler orla-venn --lieu "Dock 7" --moment "Cycle de nuit" --pj Kael` ; en partie : `/fait <texte>` ajoute un fait à la scène, `/quitter` sort.
- Interface web (navigateur, 127.0.0.1:8000) : `uv run web` (`--port`, `--sans-navigateur`, `--hote`). Règles + historique des recherches (`fichiers.historique_des_recherches`), sessions PNJ sauvegardées (`fichiers.dossier_des_sessions`), création et modification de PNJ, onglet Livres (cocher les livres utilisés → `regles.livres_utilises` de `config.yaml` ; ajout d'un PDF → réindexation), fenêtre Config (modèle, clés masquées, éditeur de `config.yaml`), aide = `MANUEL.md` rendu en HTML. Config relue à chaque requête. Pas d'authentification : `TrustedHostMiddleware` limite aux hôtes locaux ; les clés ne quittent jamais le serveur en clair.
- Toutes les commandes acceptent `--config autre.yaml`.
- Manuel utilisateur (non-développeur) : `MANUEL.md`. Le tenir à jour quand une commande, un réglage ou un message d'erreur change.
- Clés API : dans `secrets.yaml` (racine, ignoré par git ; modèle versionné `secrets.exemple.yaml`), une entrée par usage : `recherche-apikey` (`search`) et `personas-apikey` (`parler`). Chemin réglé par `fichiers.secrets` de `config.yaml`. Entrée vide ou fichier absent → repli sur `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`. Lu par `core/config.py` (`charger_secrets`), transmis au fournisseur par `creer_fournisseur(..., cle_api=…)`. Les tests des commandes utilisent `tests/reglages_test.py::ecrire_config`, jamais le vrai `secrets.yaml` (ni le vrai historique, ni les livres cochés par l'utilisateur).
- Tests couches 1–3 : `uv run pytest` (les tests de récupération reconstruisent l'index depuis les PDF dans un dossier temporaire ; ignorés si les PDF sont absents)
- Évals couche 4 (LLM réel, payant) : `uv run pytest -m eval` (exclues par défaut ; ignorées sans identifiants)
- Lint : _non configuré_

## Skills et collaboration
Skills du projet dans `.claude/skills/` (versionnés) : `livrer-un-changement` (garde-fou de toute modification), `diagnostic`, `creer-pnj-depuis-description`, `preparer-la-seance`, `apres-la-partie`, `tester-un-pnj` (évals payantes), `synchroniser` (git), `maj-manuel`. Un skill qui réagit à une phrase de l'utilisateur a une section `## Phrases de l'utilisateur` ; ces phrases sont recopiées mot pour mot dans `MANUEL.md`, section 13 (vérifié par `tests/unit/test_skills_manuel.py`).

Collaboration : dépôt distant `origin` (GitHub ou Gitea privé), branche `master` tenue par le mainteneur. Rôle de la personne dans `git config --local jdr.role` (`mainteneur` | `contributeur`) ; un contributeur travaille sur une branche personnelle unique (`git config --local jdr.branche`, `travail/<prénom>`), gérée par Claude sans que cette personne ait à s'en occuper, et n'envoie (`push`) qu'en cas de blocage ou de proposition. Hors git : `secrets.yaml`, PDF de `rules/`, `data/rules.db`, `data/sessions/`, `data/historique/`. `.claude/settings.json` autorise les commandes sans risque et interdit de lire `secrets.yaml`.

## Sources
Règles dans `rules/MA - Manuel des joueurs 1.5/` : **Guide du Meneur** (258 p.) + **Manuel des joueurs** (290 p.), FR. Gros binaires gardés hors git (voir `.gitignore`).
