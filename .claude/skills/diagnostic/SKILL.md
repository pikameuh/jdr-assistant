---
name: diagnostic
description: Trouver et réparer ce qui empêche l'assistant de fonctionner. À utiliser quand l'utilisateur dit que quelque chose ne marche plus, colle un message d'erreur ou une trace Python, ou que la commande parler, search, web, l'index des règles ou les tests échouent.
---

# Diagnostic

L'utilisateur peut ne pas savoir lire une trace Python. Le but : trouver la cause réelle, réparer si c'est sans risque, et sinon dire en français quoi faire.

## Phrases de l'utilisateur

- « Ça ne marche plus »
- « J'ai une erreur »
- « Vérifie que tout est prêt »

## Règle absolue sur les clés

Ne jamais afficher, lire à l'écran ni recopier le contenu de `secrets.yaml` ou d'une variable `*_API_KEY`. Pour savoir si une clé est présente, utiliser seulement :

```sh
uv run python -c "from agent_jdr.core.config import charger_config, charger_secrets as s; c=charger_config(); k=s(c.fichiers.secrets); print('recherche :', 'présente' if k.recherche else 'absente'); print('personas :', 'présente' if k.personas else 'absente')"
```

## Ordre des vérifications

S'arrêter à la première qui échoue, la réparer, puis reprendre depuis le début.

1. **Le message.** Si l'utilisateur a collé une erreur, la chercher d'abord dans le tableau de la section 12 de `MANUEL.md` : la solution y est peut-être déjà écrite.
2. **Dossier et outils** : on est bien à la racine du projet (`pyproject.toml` présent) ; `uv --version` répond.
3. **Installation** : `uv sync`.
4. **Configuration** : `uv run python -c "from agent_jdr.core.config import charger_config; charger_config(); print('config.yaml : correct')"`. En cas d'erreur, le message en français indique le réglage fautif. Comparer avec `git diff config.yaml` pour voir ce qui a été changé à la main.
5. **Clés** : la commande ci-dessus. Clé absente → section 4 du manuel. Clé refusée → seul l'utilisateur peut la remplacer (fenêtre ⚙ de l'interface web, ou `secrets.yaml`).
6. **Livres et index** : les PDF sont dans `fichiers.dossier_des_pdf` ; l'index existe (`fichiers.index_des_regles`) ; au moins un livre coché (`regles.livres_utilises`). Recherche gratuite de contrôle : `uv run search "faire le plein" --brut -n 3`. Index absent ou ancien → `uv run python -m agent_jdr.core.rules_index build`.
7. **Fiches PNJ** : la commande de vérification de la section 10 du manuel.
8. **Tests** : `uv run pytest`. Un échec ici après une mise à jour ou une modification relève du code : voir `git log --oneline -5` et `git status` pour savoir ce qui a changé.
9. **Interface web** : port occupé → `uv run web --port 8001` ; sinon lancer `uv run web --sans-navigateur` et lire la sortie du terminal.

Un appel payant au modèle (`uv run search "…"` sans `--brut`, `uv run parler`) ne se lance qu'avec l'accord de l'utilisateur, et seulement quand toutes les vérifications gratuites passent.

## Réparer

- Réparer soi-même : `uv sync`, la reconstruction de l'index, une faute de frappe dans `config.yaml` ou dans une fiche (montrer la correction avant de l'écrire).
- Toute réparation du code passe par le skill `livrer-un-changement`.
- Cause introuvable, ou réparation risquée → skill `synchroniser`, section « Problème bloquant ».
- Si le message d'erreur n'était pas dans la section 12 du manuel, l'y ajouter (skill `maj-manuel`).

## Compte rendu

En français, sans jargon : ce qui n'allait pas, ce qui a été fait, ce qu'il reste à faire de son côté.
