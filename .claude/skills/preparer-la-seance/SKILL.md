---
name: preparer-la-seance
description: Préparer une séance de jeu à partir du scénario ou des notes du meneur — PNJ nécessaires, fiches manquantes, vérification que l'assistant est prêt, commandes du jour J. À utiliser quand l'utilisateur dit « je joue samedi », « prépare la séance », « voici mon scénario », ou demande si tout est prêt pour la partie.
---

# Préparer la séance

## Phrases de l'utilisateur

- « Prépare la séance »
- « Je joue samedi, voici mon scénario »
- « Est-ce que tout est prêt pour la partie ? »

## Étapes

1. **Lire le scénario** (texte collé, fichier indiqué, ou notes). Ne pas le recopier dans le dépôt sans demande.
2. **Lister les PNJ** qui parlent dans la séance, avec pour chacun : la scène où il apparaît, ce que les PJ peuvent vouloir de lui, ce qu'il cache.
3. **Comparer avec les fiches** de `fichiers.dossier_des_pnj` (`config.yaml`) :
   - fiche absente → proposer de la créer (skill `creer-pnj-depuis-description`, en reprenant ce que dit le scénario) ;
   - fiche présente mais en décalage avec le scénario (secret, objectif, attitude) → proposer la modification, avec l'accord du meneur.
4. **Règles probables** : repérer les situations du scénario qui demandent une règle (combat, poursuite spatiale, achat, piratage…) et vérifier par une recherche gratuite (`uv run search "<mots>" --brut -n 3`) que les livres cochés les couvrent. Signaler un livre nécessaire mais décoché (`regles.livres_utilises`).
5. **Vérifier que l'assistant est prêt**, sans appel payant : configuration, clés présentes, index, fiches valides, tests (skill `diagnostic`, étapes 2 à 8).
6. **Feuille du jour J**, courte, pour chaque scène : le PNJ, la commande ou la manipulation dans l'interface web (lieu, moment, PJ, enjeux), et les faits que le meneur pourra ajouter (`/fait …`) pour déclencher un secret. Rappeler que `uv run web` garde l'historique, contrairement à `uv run parler`.
7. **Coût** : rappeler le modèle de dialogue choisi (`dialogue.modele`) et que chaque réplique est payante (section 11 de `MANUEL.md`). Ne pas lancer d'essai payant sans accord ; proposer le skill `tester-un-pnj` pour les PNJ importants.
