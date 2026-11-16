---
name: apres-la-partie
description: Faire le bilan d'une séance de jeu et mettre à jour les fiches PNJ pour garder la campagne cohérente. À utiliser quand l'utilisateur dit « on a fini la séance », « fais le bilan de la partie », « mets à jour les PNJ après la partie », ou demande ce qu'un PNJ a dit ou révélé.
---

# Après la partie

Les conversations de l'interface web sont sauvegardées, une session par fichier JSON, dans `fichiers.dossier_des_sessions` de `config.yaml` (par défaut `data/sessions/`, hors git). La commande `uv run parler` ne sauvegarde rien : pour ces conversations-là, demander à l'utilisateur ses notes.

## Phrases de l'utilisateur

- « On a fini la séance »
- « Fais le bilan de la partie »
- « Mets à jour les PNJ après la partie »

## Étapes

1. **Trouver les sessions de la séance** : lister les fichiers JSON du dossier, triés par `modifie_le`. Proposer celles des dernières 24 h, ou demander la date de la séance. Format (`agent_jdr/core/sessions.py`, `SessionDialogue`) : `persona` (id de la fiche), `pj`, `scene` (`lieu`, `moment`, `faits_etablis`…), `historique` (tours `joueur` / `pnj`, avec `regles` consultées).
2. **Lire chaque session en entier** et la fiche du PNJ concerné. Ne pas modifier les fichiers de session.
3. **Bilan par PNJ**, court, en français :
   - ce qui s'est passé (faits établis et moments clés de la conversation) ;
   - les secrets révélés, en comparant ses répliques au `contenu` de chacun de ses `secrets`, en citant la réplique ;
   - ce que le PNJ a appris ou promis, et comment son attitude envers les PJ a évolué ;
   - les répliques qui sortent du personnage ou contredisent la fiche, à signaler au meneur ;
   - les règles consultées (références), si le meneur veut vérifier.
4. **Proposer les modifications de fiche**, champ par champ, avant / après. Exemples : secret révélé → le retirer des `secrets` et l'ajouter aux `connaissances` (ou le garder, au choix du meneur) ; attitude qui change → `attitude_envers_pj` ; objectif atteint → `objectifs`. N'appliquer qu'avec l'accord du meneur, champ par champ.
5. **Appliquer** dans le fichier YAML (identifiant inchangé), puis valider avec la commande gratuite de la section 10 de `MANUEL.md`.
6. **Garder une trace** si le meneur le souhaite : un résumé de séance en Markdown, à l'endroit choisi par le meneur. Ce résumé n'est versionné que sur demande.
7. **Enregistrer** les fiches modifiées dans un commit (`git add <fiches>`, message `Bilan de séance du <date> : <PNJ>`), sur la bonne branche (skill `synchroniser`, section « Rôle et branche »).
