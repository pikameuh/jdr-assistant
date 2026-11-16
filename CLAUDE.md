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
- IHM : **CLI d'abord, back-end web ensuite** → le cœur doit rester indépendant de l'IHM.
- Règles : **index SQLite FTS5** interrogé par un outil `rechercher_regle` (aucun service externe).
- LLM : **fournisseur et modèle choisis dans `config.yaml`**, séparément pour le dialogue et les questions de règles : Anthropic (API Messages ; défaut `claude-sonnet-5-5`) ou OpenAI (API Responses). Réflexion, cache, tool use dans les deux cas.

## Configuration
Tout réglage modifiable à la main est dans **`config.yaml`** (racine), noms en français, commentés, pensé pour un non-développeur : modèles, niveau de réflexion, longueurs, nombre de passages, **consignes données au modèle**, chemins. Aucune valeur par défaut cachée dans le code : un réglage manquant ou mal écrit est refusé avec un message en français. Le cœur reçoit ses réglages en paramètre ; seules les commandes lisent le fichier (`core/config.py`). Les tests utilisent leur propre configuration (`tests/reglages_test.py`), pour que l'édition de `config.yaml` ne les casse pas.

## Architecture
Règle de dépendance absolue : `interfaces/` dépend de `core/`, **jamais l'inverse**. Le web réutilisera le `core/` tel quel. Seuls les modules `core/fournisseurs/fournisseur_*.py` importent un SDK (`anthropic`, `openai`) ; un test le vérifie.

```
config.yaml              # configuration (modèles, consignes, chemins)
agent_jdr/
  core/                  # cœur réutilisable, zéro dépendance IHM
    config.py            # lecture + validation de config.yaml
    fournisseurs/        # seul endroit qui importe un SDK (anthropic, openai)
      base.py            # interface commune + erreurs communes
      fournisseur_anthropic.py  fournisseur_openai.py
    personas/            # PNJ en YAML (données versionnées), un fichier = un id
    persona.py           # schéma PNJ (pydantic) + chargement YAML
    scene.py             # état de scène (contexte), sérialisable
    rules_index.py       # construction + requête FTS5
    prompt_builder.py    # assemblage persona + scène + historique (format neutre)
    dialogue_engine.py   # boucle tool use, indépendante du fournisseur
  interfaces/
    cli.py               # client mince (v1)
    # web/               # plus tard, même core
  data/rules.db          # index FTS5 généré depuis les PDF (régénérable)
  tests/
    unit/  retrieval/  orchestration/  evals/
```

## Stratégie de tests (4 couches)
1. **unit** — déterministe, sans LLM : personas (schéma), état de scène, assembleur, parsing.
2. **retrieval** — requête → passage attendu de l'index FTS5.
3. **orchestration** — client Anthropic mocké : bon appel de l'outil règles, boucle tool use, historique.
4. **evals** — LLM réel, scénarios figés : reste en personnage, ne révèle pas ses secrets, consulte les règles au bon moment.

Couches 1–3 à chaque commit ; couche 4 à part (plus lente/coûteuse). Les couches 1–3 couvrent les deux fournisseurs (clients mockés, vrais types des SDK).

## Commandes
Gestionnaire : **uv** (`pyproject.toml`). PyMuPDF est une dépendance de *build* uniquement (groupe `build`) : seul `core/rules_extract.py` l'importe, jamais l'agent en exécution.

- Installation : `uv sync`
- Construire l'index des règles (≈ 8 s) : `uv run python -m agent_jdr.core.rules_index build`
- Question de règles (réponse en français + sources citées, appel au modèle, nécessite la clé `recherche-apikey`) : `uv run python -m agent_jdr.core.rules_index search "expliques moi la dispersion d'une grenade"` (`-n 8` = passages envoyés au modèle)
- Débogage de la recherche (liste des passages, sans appel LLM) : `uv run python -m agent_jdr.core.rules_index search "faire le plein" --brut -n 5`
- Raccourci, mêmes options : `uv run search "faire le plein"` (entrée `[project.scripts]`).
- Parler à un PNJ (appel au modèle, nécessite la clé `personas-apikey`) : `uv run parler orla-venn --lieu "Dock 7" --moment "Cycle de nuit" --pj Kael` ; en partie : `/fait <texte>` ajoute un fait à la scène, `/quitter` sort.
- Toutes les commandes acceptent `--config autre.yaml`.
- Manuel utilisateur (non-développeur) : `MANUEL.md`. Le tenir à jour quand une commande, un réglage ou un message d'erreur change.
- Clés API : dans `secrets.yaml` (racine, ignoré par git ; modèle versionné `secrets.exemple.yaml`), une entrée par usage : `recherche-apikey` (`search`) et `personas-apikey` (`parler`). Chemin réglé par `fichiers.secrets` de `config.yaml`. Entrée vide ou fichier absent → repli sur `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`. Lu par `core/config.py` (`charger_secrets`), transmis au fournisseur par `creer_fournisseur(..., cle_api=…)`. Les tests des commandes utilisent `tests/reglages_test.py::ecrire_config`, jamais le vrai `secrets.yaml`.
- Tests couches 1–3 : `uv run pytest` (les tests de récupération reconstruisent l'index depuis les PDF dans un dossier temporaire ; ignorés si les PDF sont absents)
- Évals couche 4 (LLM réel, payant) : `uv run pytest -m eval` (exclues par défaut ; ignorées sans identifiants)
- Lint : _non configuré_

## Sources
Règles dans `rules/MA - Manuel des joueurs 1.5/` : **Guide du Meneur** (258 p.) + **Manuel des joueurs** (290 p.), FR. Gros binaires gardés hors git (voir `.gitignore`).
