# Avancement — Agent IA JDR

**Dernière mise à jour : 2026-11-15**

## Reprise rapide (lire en premier)
Phases 0, 0.2, 1 et 2 terminées. **Toute la configuration est dans `config.yaml`** (modèles — `claude-sonnet-5-5` par défaut —, niveau de réflexion, longueurs, passages, consignes, chemins ; `core/config.py`). Règles : `data/rules.db` (FTS5), réponses sourcées via `uv run search "…"`. Fiches PNJ YAML (exemple `orla-venn`), scène, assembleur, moteur de dialogue (outil `rechercher_regle`, cache) et CLI `uv run parler orla-venn --lieu … --moment … --pj …`. 171 tests passent (`uv run pytest`, couches 1–3). **Rien n'a encore tourné sur le vrai modèle** (aucune clé API sur la machine de dev) : premier essai = `uv run parler …`, puis `uv run pytest -m eval`. Effet réel du cache non mesuré. Prochaine étape : **Phase 3 — évals de dialogue**, à faire tourner sur plusieurs modèles (Haiku 5.5, Sonnet 5.5, Opus) pour choisir le moins cher qui tient.

## État par phase

### Phase 0 — Règles (index FTS5)
- [x] Vérifier l'extraction `pdftotext` sur un échantillon des 2 PDF
- [x] Extraction + nettoyage complet
- [x] Découpage par section (avec réf. livre + page)
- [x] Construction de l'index FTS5 (`data/rules.db`)
- [x] Tests de récupération (couche 2)

### Phase 0.2 — Réponse aux questions de règles, avec sources
Objectif : `uv run python -m agent_jdr.core.rules_index search "expliques moi la dispersion d'une grenade"` affiche (1) une réponse en français, rédigée uniquement à partir des règles, puis (2) la liste de ce qui a servi à la produire : référence (livre, page, section) et extrait exact cité, pour vérification dans le PDF.

Hors périmètre : boucle tool use (le modèle relance lui-même la recherche), personas, historique de conversation, streaming. Ces points restent en phase 2.

- [x] Module `core/rules_qa.py` (cœur, sans IHM, réutilisable en phase 2) : question → recherche FTS5 (top-N passages) → un appel Opus 4.8 (`claude-opus-4-8`, thinking adaptatif) → réponse + sources.
- [x] Traçabilité par les **citations natives de l'API** : chaque passage envoyé comme bloc `document` texte, titre = `Passage.reference()`, `citations` activées. Les sources affichées sont les citations renvoyées (`cited_text` + passage d'origine), pas une liste déclarée par le modèle.
- [x] Consigne système : répondre en français, uniquement d'après les passages fournis ; dire explicitement quand les passages ne couvrent pas la question, sans inventer.
- [x] CLI : `search` affiche la réponse puis une section « Sources » numérotée (référence + extrait cité, dédoublonnées par passage). Option `--brut` : ancien comportement (liste des passages, sans appel LLM), pour le débogage de la recherche.
- [x] Dépendance `anthropic` ajoutée au projet ; identifiants absents → message d'erreur clair (pas de trace Python).
- [x] Tests unitaires (couche 1) : construction de la requête (documents, titres, consigne) ; rendu des sources depuis une réponse factice.
- [x] Tests d'orchestration (couche 3), client Anthropic mocké : les passages récupérés sont bien envoyés ; chaque citation est reliée au bon passage ; cas « aucun passage trouvé » (pas d'appel LLM).
- [x] Test de récupération (couche 2) : « dispersion d'une grenade » → Manuel des joueurs p. 174 (Dispersion et aire d'effet) en tête.
- [~] Éval (couche 4), un scénario : la question grenade obtient une réponse qui cite p. 174. Écrite (`tests/evals/`), **non exécutée** faute d'identifiants.
- [x] `CLAUDE.md` > Commandes : nouveau comportement de `search` et option `--brut`.

### Phase 1 — Persona + contexte + assembleur
- [x] Schéma persona (YAML) + validation : `core/persona.py` (pydantic, champs inconnus refusés, id = nom du fichier), erreurs `PersonaInvalide` lisibles. Un PNJ inventé : `core/personas/orla-venn.yaml`.
- [x] État de scène sérialisable : `core/scene.py` (immuable, `avec_fait`, `vers_json` / `depuis_json`).
- [x] Assembleur de prompt : `core/prompt_builder.py` (`construire_prompt(persona, scene, historique)`).
- [x] Tests unitaires (couche 1) : `test_persona.py`, `test_scene.py`, `test_prompt_builder.py` (28 tests).

### Phase 2 — Moteur de dialogue
- [x] Appel Opus 4.8 + tool use `rechercher_regle` : `core/dialogue_engine.py`, `MoteurDialogue.repondre` → `Replique` (texte + règles consultées). Boucle limitée à 4 tours de recherche ; refus, troncature, réplique vide → `ReponseIncomplete` ; l'historique ne garde que les tours réussis.
- [x] Prompt caching sur la partie stable : `cache_control` sur `system[0]` (consignes + persona) + cache automatique en fin de conversation. **Non mesuré** (pas de clé).
- [x] Tests d'orchestration mockés (couche 3) : `tests/orchestration/test_dialogue_engine.py` (22 tests, moteur + CLI).
- [x] Avancé depuis la phase 3 (demande utilisateur) : CLI `uv run parler` (`interfaces/cli.py`), commandes `/fait` et `/quitter`.

### Phase 3 — Évals + CLI
- [ ] Jeu de scénarios d'évals (couche 4)
- [x] CLI minimale (faite en phase 2 : `uv run parler`)

## Notes techniques — PDF Metal Adventures 1.5
- Texte de chaque page dessiné **deux fois** (passe propre + passe fragmentée superposée) → dédoublonnage des caractères par (caractère, x, y).
- Pas de table des matières intégrée : structure lue par la police. BalboaPlus 14 pt = section, 12 pt = sous-section, 13,5 pt = titre courant de page, 18 pt = numéro de page, 28/48 pt = bandeaux, 11 pt = nouvelles d'intro (écartées). ViktorScript = citations d'illustration (écartées).
- Page imprimée = page PDF − 1 (constant sur les deux livres). Pages imprimées 0–3 (couverture, crédits, sommaire) exclues.
- Helvetica = « Ref. 15101 » et filigrane nominatif de l'acheteur (page 1) → supprimés ; un test vérifie leur absence.
- Césures : recollées ; trait d'union gardé si la forme composée est plus fréquente dans le corpus (« celui-ci »).
- Passages ≤ 1500 caractères, coupés aux fins de phrase ; une section par passage.

## Limites connues (phase 0)
- Pas de synonymes ni d'abréviations : « PP » ne trouve pas « points de panache ». L'agent devra reformuler (à prévoir dans la description de l'outil, phase 2).
- Requêtes très larges (« Stella Bell ») : renvoient des sections pertinentes mais pas forcément la page d'introduction. Les requêtes précises fonctionnent.
- 5 césures restent non recollées, quand un encadré coupe la phrase. Quelques lignes de tableau ou d'encadré sont rattachées à la sous-section voisine (ordre du flux PDF).
- Le texte d'ambiance (nouvelles d'intro, citations) n'est pas indexé.

## Journal des décisions
- **2026-11-14** — Stack : Python. IHM : CLI puis web. Règles : FTS5. LLM : Opus 4.8.
- **2026-11-14** — Cœur découplé de l'IHM (`interfaces/` → `core/`) pour permettre le web sans refonte.
- **2026-11-14** — Pas de RAG vectoriel en v1 (FTS5 suffit ; réversible derrière la même interface `rechercher_regle`).
- **2026-11-14** — Dispositif de suivi : `CLAUDE.md` (stable) + `PROGRESS.md` (vivant) + git.
- **2026-11-14** — Outillage : uv + pytest. Extraction PDF par **PyMuPDF** (choix utilisateur) plutôt que `pdftotext` : il faut la police pour repérer les titres. Licence AGPL acceptable car limitée au build (groupe `build`, jamais importée à l'exécution).
- **2026-11-14** — Recherche : termes en OU, préfixe + retrait du pluriel, accents ignorés (`unicode61 remove_diacritics 2`), bm25 avec poids section/sous-section ×4, chapitre ×2. Essai « tous les termes d'abord » : sans gain, écarté.
- **2026-11-14** — Tests de récupération : l'index est reconstruit depuis les PDF dans un dossier temporaire (teste le code courant, pas un `rules.db` périmé). Pages attendues établies hors extracteur (`pdftotext`, sommaire imprimé).

- **2026-11-15** — Ajout d'une phase 0.2 avant la phase 1 (demande utilisateur) : répondre aux questions de règles, pas seulement localiser les sections. Sources vérifiables par les citations natives de l'API (texte cité exact + passage d'origine) plutôt que par une liste rédigée par le modèle.

- **2026-11-15** — Phase 0.2 : modèle `claude-opus-4-8` (figé par CLAUDE.md), thinking adaptatif explicite, un appel non streamé (`max_tokens` 16000). 8 passages envoyés par défaut (`-n`). Sources = citations `char_location` regroupées par passage, dans l'ordre de première citation ; renvois `[n]` dans le texte. Réponse refusée ou tronquée → erreur explicite. Sans identifiants, le SDK lève `TypeError` (pas une erreur API) : interceptée sur son message et convertie en `IdentifiantsAbsents`. Évals exclues par défaut (`addopts = -m 'not eval'`).
- **2026-11-15** — Raccourci `uv run search "…"` : entrée `[project.scripts]` vers `rules_index.search_cli`, qui délègue à `main(["search", …])` (une seule analyse d'arguments). Clé API lue depuis l'environnement (`ANTHROPIC_API_KEY`), pas de `.env` chargé par le code.
- **2026-11-15** — Phase 1 (choix utilisateur) : fiche PNJ **narrative seulement** (identité, personnalité, parole, objectifs, connaissances, secrets avec condition de révélation, attitude envers les PJ) ; pas de stats chiffrées, les règles passent par l'outil en phase 2. Scène : lieu, moment, ambiance, PNJ/PJ présents, enjeux, faits établis. Un PNJ d'exemple inventé. Validation par pydantic (déjà tiré par `anthropic`, désormais dépendance directe, avec `pyyaml`). Assembleur sans modèle ni outil ni `cache_control` (phase 2) ; `system[0]` = consignes + persona (identique d'une scène à l'autre, testé), `system[1]` = scène. Tours du joueur → `user` préfixés `[PJ]`, tours du PNJ → `assistant` ; l'historique doit commencer et finir par le joueur.
- **2026-11-15** — Phase 2 : modèle `claude-opus-4-8` (CLAUDE.md), thinking adaptatif, non streamé, `max_tokens` 16000, effort par défaut. Outil `rechercher_regle` strict (`requete` seule) ; résultat = 5 passages en blocs texte « référence + texte », sans citations (le PNJ parle en personnage ; les références consultées sont affichées au meneur par la CLI). Entrée invalide ou outil inconnu → `tool_result` avec `is_error`, pas d'exception. Blocs de réflexion renvoyés tels quels pendant la boucle ; seul le texte final entre dans l'historique. Consigne ajoutée : consulter les règles avant toute réplique qui en dépend, n'inventer aucun chiffre. `rules_qa.appeler_api` factorise la conversion des erreurs d'identifiants (partagée par les deux usages). CLI avancée de la phase 3 à la demande de l'utilisateur.
- **2026-11-15** — Configuration centralisée (demande utilisateur) : `config.yaml` à la racine, YAML (même format que les fiches PNJ), noms français, sections `dialogue`, `questions_de_regles`, `fichiers`. Modèle par défaut **Sonnet 5.5** partout (choix utilisateur, 2,5× moins cher qu'Opus 4.8 ; à confirmer par les évals). Consignes déplacées du code vers la configuration (choix utilisateur) ; conséquence : les tests unitaires ne vérifient plus le contenu des consignes (texte désormais éditable), seulement qu'elles sont transmises telles quelles — la qualité des consignes relève des évals. Niveau de réflexion en mots (`defaut` = paramètre `effort` non envoyé). Aucune valeur par défaut dans le code ; erreurs traduites en français. Options `--db`, `--personas`, `-n`, `--config` conservées pour remplacer ponctuellement un réglage. `rules_index` importe la configuration seulement dans `main` (recherche toujours sans dépendance hors bibliothèque standard).
- **2026-11-15** — Non fait, à décider : repli automatique vers un autre modèle en cas de refus (paramètre `fallbacks`, bêta). Aujourd'hui, un refus donne un message clair et le tour n'est pas enregistré.

## Décisions ouvertes (pour plus tard)
- Persistance de l'état de scène pour le web (sérialisation + gestion de sessions).
- Streaming des réponses (variante *stream* du moteur).
- Éventuelle v2 vectorielle si la recherche FTS5 s'avère insuffisante.
