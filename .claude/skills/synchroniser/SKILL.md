---
name: synchroniser
description: Collaboration git entre le mainteneur du projet et un contributeur non développeur. À utiliser quand l'utilisateur veut récupérer les mises à jour (« récupère les nouveautés », « mets le projet à jour »), est bloqué et veut de l'aide du mainteneur (« j'ai un problème bloquant », « envoie mon travail »), veut proposer ses modifications (« propose mes changements »), installe le projet pour la première fois depuis un dépôt, ou, côté mainteneur, veut récupérer le travail d'un contributeur. Aussi appelé par livrer-un-changement pour savoir sur quelle branche travailler.
---

# Synchroniser le travail avec git

Le dépôt partagé est le dépôt distant `origin` (GitHub ou Gitea, privé). La branche principale est `master`, tenue par le mainteneur. Un contributeur travaille en autonomie sur **une branche personnelle unique** et n'envoie son travail que sur sa propre décision (blocage ou proposition). Pour cette personne, la gestion des branches est invisible : ne jamais lui demander de taper une commande git, ne parler de branche que sur sa demande.

Restent hors de git (déjà dans `.gitignore`, ne jamais forcer) : `secrets.yaml`, les PDF de `rules/`, `data/rules.db`, `data/sessions/`, `data/historique/` et tout fichier généré. Les fiches PNJ, `config.yaml` et `modeles.yaml` sont partagés.

## Phrases de l'utilisateur

- « Installe le projet »
- « Récupère les nouveautés »
- « J'ai un problème bloquant »
- « Propose mes changements »
- « Récupère le travail de mon ami » (mainteneur)

## Rôle et branche

Lire `git config --local --get jdr.role`. S'il est vide, demander une seule fois : « Êtes-vous le mainteneur du projet, ou quelqu'un qui le reçoit et l'adapte à ses parties ? ». Puis :

- mainteneur : `git config --local jdr.role mainteneur` ; travail sur `master`.
- contributeur : demander son prénom, en faire un identifiant (minuscules, sans accents, tirets), puis `git config --local jdr.role contributeur` et `git config --local jdr.branche travail/<identifiant>`. Créer la branche depuis `origin/master` si elle n'existe pas (`git switch -c travail/<identifiant> origin/master`, ou depuis `master` sans dépôt distant). Si `user.name` ou `user.email` manquent, les demander et les enregistrer avec `--local`.

Contributeur : avant tout travail, vérifier qu'on est sur sa branche (`git branch --show-current`) ; sinon `git switch <branche>` (après avoir enregistré ou mis de côté les modifications en cours, avec son accord).

## Première installation (contributeur)

Si le projet n'est pas encore sur son ordinateur, l'utilisateur suit la section 13 de `MANUEL.md` (`git clone <adresse>`). Une fois dans le dossier : définir le rôle (ci-dessus), puis `uv sync`, puis le guider pour les clés (section 4 du manuel) et les PDF (section 5). Les PDF ne sont jamais dans le dépôt : chaque personne utilise ses propres exemplaires achetés.

## Récupérer les nouveautés (contributeur)

1. `git status` : s'il y a des modifications non enregistrées, les enregistrer d'abord (skill `livrer-un-changement`), ou demander.
2. `git fetch origin`. Si `origin/<sa branche>` existe et contient des commits absents de sa branche (une correction du mainteneur après un blocage), les intégrer d'abord : `git merge origin/<sa branche>`.
3. `git log --oneline HEAD..origin/master` : s'il n'y a rien de nouveau et rien n'a été intégré à l'étape 2, le dire et s'arrêter. Sinon `git merge origin/master` dans sa branche (jamais `rebase` : son historique a peut-être déjà été envoyé).
4. Conflit : le résoudre en gardant les deux intentions ; en cas de doute sur une fiche PNJ ou sur `config.yaml`, montrer les deux versions en français et lui demander laquelle garder. Si la résolution n'est pas sûre : `git merge --abort`, et proposer « Problème bloquant ».
5. `uv sync`. Si `agent_jdr/core/rules_extract.py` ou `agent_jdr/core/rules_index.py` ont changé, reconstruire l'index (`uv run python -m agent_jdr.core.rules_index build`).
6. `uv run pytest`. En cas d'échec, ne pas laisser l'utilisateur dans un état cassé : corriger si la cause est claire, sinon `git merge --abort` (avant commit) ou `git revert -m 1 HEAD` (après), puis « Problème bloquant ».
7. Résumer les nouveautés en français à partir de `git log` et du diff de `MANUEL.md` : ce qui change à l'usage, et ce qu'il reste à faire (nouvelle clé, nouveau réglage…).

## Problème bloquant (contributeur)

1. Enregistrer l'état actuel dans un commit sur sa branche, même si les tests échouent. C'est la seule exception à la règle de `livrer-un-changement` : ce commit n'entre pas dans `master` et sert à demander de l'aide. Première ligne : `[BLOQUÉ] <résumé>`. Corps : le résultat voulu, ce qui a été tenté, la sortie exacte de l'erreur ou des tests (copiée, pas résumée).
2. Demander son accord avant d'envoyer (« J'envoie votre travail au mainteneur ? »), puis `git push -u origin <branche>`.
3. Lui donner un message court à transmettre au mainteneur : nom de la branche, résumé du blocage, et le lien de comparaison (voir « Lien »).

## Proposer ses changements (contributeur)

Comme « Problème bloquant », mais les tests doivent passer (`uv run pytest`) et le commit ne porte pas `[BLOQUÉ]`. Après l'envoi, donner le lien pour ouvrir la demande de fusion, ou le message à transmettre au mainteneur qui l'ouvrira.

## Lien

Construire l'adresse web depuis `git remote get-url origin` (`git@hote:proprietaire/depot.git` ou `https://hote/proprietaire/depot.git` → `https://hote/proprietaire/depot`). GitHub et Gitea acceptent tous deux `https://hote/proprietaire/depot/compare/master...<branche>` pour ouvrir une demande de fusion. Sans dépôt distant (`origin` absent), le dire, et demander au mainteneur l'adresse à configurer (`git remote add origin <adresse>`).

## Récupérer le travail d'un contributeur (mainteneur)

1. `git fetch origin`, puis lister les branches `origin/travail/*` avec leur dernier commit (`git log -1 --format='%h %cr %s' <branche>`).
2. Pour un blocage : `git switch -c <branche> origin/<branche>` (ou `git switch <branche>` puis `git merge --ff-only origin/<branche>`), lire le commit `[BLOQUÉ]`, reproduire l'erreur, corriger sur cette branche, `uv run pytest`, puis, avec l'accord du mainteneur, `git push`. Le contributeur récupère la correction en disant « Récupère les nouveautés » (étape 2 de cette section).
3. Pour fusionner : relire le diff (`git diff master...origin/<branche>`), lancer `uv run pytest` sur la branche, puis fusionner dans `master` via la demande de fusion ou `git merge --no-ff`, avec son accord.

## Toujours

Toute action qui sort de l'ordinateur (`git push`), qui fusionne dans `master`, ou qui réécrit l'historique demande un accord explicite, à chaque fois. Jamais de `git push --force`, de `git reset --hard` ni de `git clean` sans demande expresse.
