---
name: livrer-un-changement
description: Garde-fou de toute modification du projet (code, config.yaml, modeles.yaml, interface web, tests) demandée en langage courant — « ajoute », « change », « corrige », « je voudrais que… », « fais en sorte que… ». À utiliser avant d'écrire la première ligne et jusqu'au commit. L'utilisateur peut ne pas savoir programmer : ce skill remplace sa relecture du code. Ne concerne pas la création d'une fiche PNJ seule (voir creer-pnj-depuis-description).
---

# Livrer un changement sans relecture technique

La personne qui demande peut ne pas savoir lire du code. Elle juge le résultat, pas le diff. Le changement doit donc être juste, testé, documenté et réversible sans qu'elle ait à intervenir.

## Phrases de l'utilisateur

- « Ajoute … »
- « Change … »
- « Corrige … »
- « Je voudrais que l'assistant … »
- « Annule le dernier changement »

## Étapes

1. **Situer le travail dans git** (skill `synchroniser`, section « Rôle et branche ») : lire `git config --local --get jdr.role`. Rôle absent → poser la question une fois et l'enregistrer. Rôle `contributeur` → travailler sur sa branche personnelle (`git config --local --get jdr.branche`), jamais sur `master`. Ne pas parler de branches à l'utilisateur, sauf sur sa demande.
2. **Partir d'un état propre** : `git status`. Si des modifications non enregistrées existent, demander s'il faut les garder (commit à part) avant de commencer.
3. **Reformuler la demande en français simple**, avec ce qui changera côté utilisateur (ce qui s'affichera, ce qu'il faudra taper) et ce qui ne changera pas. Si la demande est ambiguë, poser la question avant d'agir. Si elle demande un réglage qui existe déjà (`config.yaml`, onglet Livres, fenêtre Config), le dire et montrer où, au lieu de coder.
4. **Respecter `CLAUDE.md`** : `interfaces/` dépend de `core/`, jamais l'inverse ; seuls `core/fournisseurs/fournisseur_*.py` importent un SDK ; aucun réglage par défaut caché dans le code (tout réglage modifiable va dans `config.yaml`, validé, avec un message d'erreur en français) ; les tests utilisent `tests/reglages_test.py`, jamais le vrai `config.yaml` ni `secrets.yaml`.
5. **Écrire les tests** dans la bonne couche (`tests/unit`, `tests/retrieval`, `tests/orchestration`). Un comportement nouveau sans test n'est pas livré.
6. **Lancer `uv run pytest`** et lire le résultat. Si un test échoue, corriger le code. Ne jamais supprimer, affaiblir ou ignorer un test pour le faire passer. Si l'échec ne se résout pas, s'arrêter et proposer le skill `synchroniser` (section « Problème bloquant »).
7. **Vérifier en vrai** quand c'est gratuit : lancer la commande touchée (`uv run search … --brut`, `uv run web --sans-navigateur` puis une requête locale, validation des fiches). Ne lancer un appel payant au modèle qu'avec son accord explicite.
8. **Manuel** : appliquer le skill `maj-manuel`.
9. **`PROGRESS.md`** : mettre à jour l'état et le journal des décisions (date absolue).
10. **Commit** : ajouter les fichiers un par un (`git add <chemin>`, jamais `git add -A` ni `.`). Vérifier qu'aucun fichier ignoré n'est forcé (`secrets.yaml`, `rules/`, `data/`). Message de commit en français, première ligne lisible par un non-développeur.
11. **Compte rendu** en quelques lignes : ce qui a changé côté utilisateur, comment l'essayer, le nombre de tests passés, les sections du manuel modifiées, et comment annuler (« dites : annule le dernier changement »).

## Annuler un changement

Si l'utilisateur demande d'annuler : `git log --oneline -5`, lui montrer le commit visé en une phrase, puis, avec son accord, `git revert <commit>` (jamais `git reset --hard`, qui détruit l'historique). Relancer `uv run pytest`.
