# Avancement — Agent IA JDR

**Dernière mise à jour : 2026-11-15**

## Reprise rapide (lire en premier)
Phases 0 et 0.2 terminées. `data/rules.db` (FTS5, 2171 passages) se construit en ≈ 8 s. `search` répond aux questions de règles en français avec des sources citées (`core/rules_qa.py`, citations natives de l'API) ; `--brut` liste les passages sans LLM. 91 tests passent (`uv run pytest`, couches 1–3). **Éval couche 4 écrite mais jamais exécutée** : aucun identifiant Anthropic sur la machine de dev → à lancer avec `uv run pytest -m eval` dès qu'une clé est disponible. Prochaine étape : **Phase 1 — schéma persona YAML + état de scène + assembleur de prompt**.

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
- [ ] Schéma persona (YAML) + validation
- [ ] État de scène sérialisable
- [ ] Assembleur de prompt
- [ ] Tests unitaires (couche 1)

### Phase 2 — Moteur de dialogue
- [ ] Appel Opus 4.8 + tool use `rechercher_regle`
- [ ] Prompt caching sur la partie stable
- [ ] Tests d'orchestration mockés (couche 3)

### Phase 3 — Évals + CLI
- [ ] Jeu de scénarios d'évals (couche 4)
- [ ] CLI minimale

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

## Décisions ouvertes (pour plus tard)
- Persistance de l'état de scène pour le web (sérialisation + gestion de sessions).
- Streaming des réponses (variante *stream* du moteur).
- Éventuelle v2 vectorielle si la recherche FTS5 s'avère insuffisante.
- Format de sortie de `rechercher_regle` pour le LLM (référence + texte) et nombre de résultats : à fixer en phase 2. La phase 0.2 en pose une première version (blocs `document` avec citations) ; la phase 2 la reprendra ou la remplacera.
