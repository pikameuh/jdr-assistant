# Avancement — Agent IA JDR

**Dernière mise à jour : 2026-11-14**

## Reprise rapide (lire en premier)
Rien n'est encore codé. Prochaine étape : **Phase 0 — extraction des PDF → index FTS5 + tests de récupération**. Avant d'indexer, vérifier que `pdftotext` produit un texte exploitable sur un échantillon des deux PDF, et remonter le résultat.

## État par phase

### Phase 0 — Règles (index FTS5)
- [ ] Vérifier l'extraction `pdftotext` sur un échantillon des 2 PDF
- [ ] Extraction + nettoyage complet
- [ ] Découpage par section (avec réf. livre + page)
- [ ] Construction de l'index FTS5 (`data/rules.db`)
- [ ] Tests de récupération (couche 2)

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

## Journal des décisions
- **2026-11-14** — Stack : Python. IHM : CLI puis web. Règles : FTS5. LLM : Opus 4.8.
- **2026-11-14** — Cœur découplé de l'IHM (`interfaces/` → `core/`) pour permettre le web sans refonte.
- **2026-11-14** — Pas de RAG vectoriel en v1 (FTS5 suffit ; réversible derrière la même interface `rechercher_regle`).
- **2026-11-14** — Dispositif de suivi : `CLAUDE.md` (stable) + `PROGRESS.md` (vivant) + git.

## Décisions ouvertes (pour plus tard)
- Persistance de l'état de scène pour le web (sérialisation + gestion de sessions).
- Streaming des réponses (variante *stream* du moteur).
- Éventuelle v2 vectorielle si la recherche FTS5 s'avère insuffisante.
