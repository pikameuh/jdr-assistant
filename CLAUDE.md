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
- LLM : **Claude Opus 4.8** (`claude-opus-4-8`), adaptive thinking, prompt caching, tool use.

## Architecture
Règle de dépendance absolue : `interfaces/` dépend de `core/`, **jamais l'inverse**. Le web réutilisera le `core/` tel quel.

```
agent_jdr/
  core/                  # cœur réutilisable, zéro dépendance IHM
    personas/            # PNJ en YAML (données versionnées)
    scene.py             # état de scène (contexte), sérialisable
    rules_index.py       # construction + requête FTS5
    prompt_builder.py    # assemblage persona + scène + règles + historique
    dialogue_engine.py   # appel Opus 4.8, tool use, prompt caching
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

Couches 1–3 à chaque commit ; couche 4 à part (plus lente/coûteuse).

## Commandes
_À compléter quand l'outillage sera posé (install, lancement tests, lint, construction de l'index)._

## Sources
Règles dans `rules/MA - Manuel des joueurs 1.5/` : **Guide du Meneur** (258 p.) + **Manuel des joueurs** (290 p.), FR. Gros binaires gardés hors git (voir `.gitignore`).
