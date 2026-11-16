---
name: creer-pnj-depuis-description
description: Créer ou enrichir une fiche PNJ (YAML de agent_jdr/core/personas) à partir d'une description libre, d'un extrait de scénario ou de notes de partie. À utiliser quand l'utilisateur dit « crée-moi un PNJ… », « fais une fiche pour… », colle la description d'un personnage, ou demande d'améliorer la fiche d'un PNJ existant.
---

# Créer une fiche PNJ depuis une description

Le formulaire web (onglet PNJ) existe déjà. Ce skill sert quand l'utilisateur part d'un texte libre, ou veut de l'aide pour écrire un PNJ qui tient en partie, surtout ses secrets.

## Phrases de l'utilisateur

- « Crée-moi un PNJ … »
- « Fais une fiche pour ce personnage : … »
- « Améliore la fiche de … »

## Étapes

1. **Lire le schéma** : `agent_jdr/core/persona.py` (classe `Persona`) et la fiche d'exemple `agent_jdr/core/personas/orla-venn.yaml`. Les champs inconnus sont refusés. Le dossier des fiches est `fichiers.dossier_des_pnj` de `config.yaml`.
2. **Extraire** de la description tout ce qui remplit un champ. Ne rien inventer en silence : ce qui est déduit est signalé comme proposition.
3. **Poser les questions qui manquent**, en une seule fois et au plus cinq, en priorité :
   - ce que le PNJ veut (`objectifs`, au moins un) ;
   - ses `secrets`, et pour chacun la **condition de révélation**. Rappeler qu'un secret sans condition n'est **jamais** révélé. Une bonne condition est observable dans la scène (« si un PJ montre la pile ouverte »), pas un état d'âme (« s'il a confiance ») ;
   - sa façon de parler (`parole.registre`, un ou deux `tics`, deux `exemples` de répliques) ;
   - son attitude envers les PJ.
4. **Univers** : Metal Adventures (space opera, pirates de l'espace). Pour une espèce, un lieu, une organisation ou un objet du jeu, vérifier dans les livres avec la recherche gratuite `uv run search "<mots>" --brut -n 5`, et le dire si rien ne le confirme. Pas de caractéristiques chiffrées dans la fiche : le PNJ consulte les règles lui-même.
5. **Identifiant** : minuscules sans accents, chiffres, tirets (`capitaine-rook`) ; il est aussi le nom du fichier. Vérifier qu'aucune fiche ne porte déjà ce nom. Ne jamais écraser une fiche existante sans accord ; pour modifier une fiche, l'identifiant ne change pas (les sessions y font référence).
6. **Écrire la fiche** `<dossier_des_pnj>/<id>.yaml`, avec un commentaire d'en-tête d'une ligne (origine de la fiche). Respecter les règles d'écriture YAML de la section 10 de `MANUEL.md` : guillemets autour d'un texte qui contient `:` ou commence par un guillemet.
7. **Valider** (gratuit) avec la commande de la section 10 du manuel. Corriger jusqu'à ce que l'identifiant apparaisse dans la liste.
8. **Montrer la fiche** en résumé (qui il est, ce qu'il veut, ce qu'il cache et quand il le lâche). Proposer, sans la lancer, une réplique d'essai payante : `uv run parler <id> --lieu "…" --moment "…" --pj <nom>`, ou l'onglet PNJ de l'interface web. Proposer aussi le skill `tester-un-pnj`.
9. **Enregistrer** : la fiche est partagée avec le dépôt. La committer seule (`git add <fichier>`), sur la bonne branche (skill `synchroniser`, section « Rôle et branche »), avec le message `PNJ : <nom>`. Pas de tests ni de mise à jour du manuel pour une simple fiche.
