---
name: maj-manuel
description: Tenir MANUEL.md (manuel non-développeur) à jour. À utiliser dès qu'une modification du projet change ce que voit ou fait l'utilisateur — commande, option, réglage de config.yaml, fichier de secrets, message d'erreur, installation, format d'une fiche PNJ, coût ou dépannage — avant de considérer la tâche terminée et avant de committer.
---

# Mettre à jour MANUEL.md

`MANUEL.md` est le seul document destiné à l'utilisateur (non-développeur). Une modification qui change son expérience n'est pas terminée tant que le manuel ne la reflète pas.

## Quand le manuel doit changer

Vérifier le manuel si la modification touche l'un de ces points (section du manuel entre parenthèses) :

| Changement | Section de `MANUEL.md` |
|---|---|
| Prérequis, installation, `uv sync`, dépendances | 2, 3 |
| Clés API, `secrets.yaml`, `secrets.exemple.yaml`, variables d'environnement | 4 |
| PDF des règles, `rules_index build`, `data/rules.db` | 5 |
| Commande `parler` : options, commandes en partie (`/fait`, `/quitter`…), affichage | 6 |
| Commande `search` : options (`-n`, `--brut`…), affichage des sources | 7 |
| `config.yaml` : réglage ajouté, renommé, retiré, valeurs admises, fournisseurs, modèles, consignes, `--config` | 8 |
| Schéma des fiches PNJ (`core/persona.py`, `core/personas/`) | 9 |
| Modèle par défaut, nombre d'appels, cache, tarifs | 10 |
| Message d'erreur ajouté, modifié ou corrigé ; anomalie connue résolue | 11 |
| Toute section ajoutée ou retirée | Sommaire |

Ne demandent pas de mise à jour : refactorisation interne sans effet visible, tests, `PROGRESS.md`, `CLAUDE.md`.

En cas de doute, lire la section concernée et comparer avec le nouveau comportement.

## Comment le mettre à jour

1. Lire la section concernée en entier avant de la modifier.
2. Écrire pour un non-développeur : phrases courtes, français simple, pas de jargon, exemples de commandes à copier-coller.
3. Vérifier chaque commande, option et message d'erreur cité en l'exécutant en local (ou en le lisant dans le code). Ne rien citer de mémoire.
4. Ce qui dépend d'un vrai modèle et n'a pas pu être exécuté (durée, coût, cache) est signalé comme non mesuré.
5. Une ligne par paragraphe : ne jamais couper une ligne Markdown à une largeur de colonne.
6. Mettre à jour le sommaire si une section est ajoutée, renommée ou retirée.
7. Faire la mise à jour dans le même commit que la modification du code.

## Compte rendu

Dans la réponse finale, dire en une ligne soit quelles sections de `MANUEL.md` ont été modifiées, soit pourquoi le manuel n'avait pas à changer.
