# Manuel de démarrage et de configuration

Assistant du meneur pour **Metal Adventures 1.5**. Ce manuel s'adresse à une personne qui n'est pas développeuse. Il suffit de savoir ouvrir un terminal et d'y copier des commandes.

## Sommaire

1. [À quoi sert l'assistant](#1-à-quoi-sert-lassistant)
2. [Ce qu'il faut avant de commencer](#2-ce-quil-faut-avant-de-commencer)
3. [Installation (une seule fois)](#3-installation-une-seule-fois)
4. [Les clés API (une seule fois)](#4-les-clés-api-une-seule-fois)
5. [Les livres de règles et l'index (une seule fois)](#5-les-livres-de-règles-et-lindex-une-seule-fois)
6. [L'interface web](#6-linterface-web)
7. [Parler à un PNJ](#7-parler-à-un-pnj)
8. [Poser une question de règles](#8-poser-une-question-de-règles)
9. [Régler l'assistant : le fichier config.yaml](#9-régler-lassistant--le-fichier-configyaml)
10. [Créer un PNJ](#10-créer-un-pnj)
11. [Combien ça coûte](#11-combien-ça-coûte)
12. [En cas de problème](#12-en-cas-de-problème)

---

## 1. À quoi sert l'assistant

Pendant une partie, l'assistant joue les **personnages non joueurs (PNJ)** à votre place. Vous tapez ce que dit le personnage d'un joueur ; le PNJ répond avec sa personnalité, sa façon de parler, ses objectifs et ses secrets. Quand sa réponse dépend d'une règle du jeu (un prix, un équipement, une procédure), il consulte lui-même les livres de règles, et l'assistant vous indique les pages consultées pour que vous puissiez vérifier.

L'assistant répond aussi aux **questions de règles** (« comment fonctionne la dispersion d'une grenade ? »), en citant les passages exacts des livres.

Tout se fait au choix dans le **navigateur** (l'interface web, [section 6](#6-linterface-web), la plus simple) ou dans le **terminal** (sections 7 et 8).

Les réponses sont rédigées par un modèle d'intelligence artificielle interrogé par Internet. Deux **fournisseurs** sont possibles : **Anthropic** (modèles Claude) et **OpenAI** (modèles GPT). Vous choisissez dans la configuration lequel joue les PNJ et lequel répond aux questions de règles ; ce peut être le même ou deux différents (voir [section 9](#9-régler-lassistant--le-fichier-configyaml)). Chaque réponse est payante (voir [section 11](#11-combien-ça-coûte)).

## 2. Ce qu'il faut avant de commencer

| Il vous faut | Pourquoi |
|---|---|
| Un ordinateur sous **Linux** ou **macOS** | L'assistant n'a pas été essayé sous Windows. |
| Un **terminal** | La fenêtre où l'on tape des commandes. Sous macOS : application « Terminal ». Sous Linux : « Terminal » dans le menu des applications. |
| Le **dossier du projet** | Fourni par votre équipe. Dans ce manuel, on suppose qu'il s'appelle `cosmos-demo`. |
| Les **deux livres PDF** de Metal Adventures 1.5 | Manuel des joueurs et Guide du Meneur, achetés légalement. Ils ne sont pas fournis avec le projet. |
| Un **compte Anthropic** et/ou un **compte OpenAI** avec des crédits | Selon le ou les fournisseurs choisis, pour obtenir une clé (voir [section 4](#4-les-clés-api-une-seule-fois)). Par défaut, l'assistant utilise Anthropic pour tout. |
| Une connexion **Internet** | Pour joindre le modèle. |

**Comment taper une commande.** Dans ce manuel, les commandes sont dans des cadres gris. Copiez la ligne, collez-la dans le terminal, puis appuyez sur **Entrée**. Les lignes qui commencent par `#` sont des explications : vous pouvez les copier aussi, le terminal les ignore.

**Toujours se placer dans le dossier du projet.** Avant toute commande de ce manuel, placez-vous dans le dossier du projet avec `cd` suivi de son emplacement, par exemple :

```sh
cd ~/cosmos-demo
```

Adaptez le chemin à l'endroit où se trouve votre dossier. Astuce : tapez `cd ` (avec l'espace), puis glissez le dossier depuis votre gestionnaire de fichiers dans le terminal ; son chemin s'écrit tout seul.

## 3. Installation (une seule fois)

L'assistant utilise un outil appelé **uv**, qui installe automatiquement tout le reste (Python et les bibliothèques nécessaires).

**Étape 1 : installer uv.** Vérifiez d'abord s'il est déjà présent :

```sh
uv --version
```

Si une ligne comme `uv 0.11.26` s'affiche, passez à l'étape 2. Si le terminal répond `command not found` ou `commande introuvable`, installez-le :

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Puis **fermez le terminal et rouvrez-en un nouveau**, pour qu'il trouve uv.

**Étape 2 : installer l'assistant.** Placez-vous dans le dossier du projet, puis :

```sh
uv sync
```

La première fois, le téléchargement peut prendre un moment. Si la commande se termine sans message d'erreur, l'installation est faite.

## 4. Les clés API (une seule fois)

Une **clé API** est un mot de passe qui permet à l'assistant d'interroger un fournisseur et de facturer votre compte. Il vous faut la clé de **chaque fournisseur utilisé** dans `config.yaml` : par défaut, seulement Anthropic. **Ne donnez jamais une clé à personne.**

Les clés se rangent dans un fichier propre au projet, **`secrets.yaml`**, à côté de `config.yaml`. Ce fichier reste sur votre ordinateur : il n'est jamais envoyé sur git. Il contient deux entrées, une par usage :

| Entrée | Utilisée par | Clé à mettre |
|---|---|---|
| `recherche-apikey` | les questions de règles (`uv run search`) | celle du fournisseur choisi dans la section `questions_de_regles` de `config.yaml` |
| `personas-apikey` | le dialogue avec les PNJ (`uv run parler`) | celle du fournisseur choisi dans la section `dialogue` de `config.yaml` |

Avec la configuration fournie, les deux usages passent par Anthropic : mettez la même clé Anthropic dans les deux entrées.

**Le plus simple : l'interface web.** Une fois la clé créée (étape 1), lancez l'interface ([section 6](#6-linterface-web)), cliquez sur **⚙** en haut à droite et collez la clé dans « Nouvelle clé API » de chaque usage, puis **Enregistrer**. Le fichier `secrets.yaml` est créé ou mis à jour pour vous : les étapes 2 et 3 ci-dessous sont alors inutiles.

### Étape 1 : créer la clé

**Clé Anthropic :**

1. Allez sur <https://console.anthropic.com> et connectez-vous (ou créez un compte).
2. Ajoutez des crédits ou un moyen de paiement dans la partie facturation de la console.
3. Ouvrez la page **API Keys**, puis cliquez sur **Create Key**. Donnez-lui un nom, par exemple `assistant-jdr`.
4. **Copiez la clé tout de suite** : elle commence par `sk-ant-` et ne sera plus affichée ensuite.

**Clé OpenAI (seulement si vous choisissez OpenAI) :**

1. Allez sur <https://platform.openai.com> et connectez-vous (ou créez un compte).
2. Ajoutez des crédits ou un moyen de paiement dans la partie facturation.
3. Ouvrez la page des clés API (**API keys**), puis créez une nouvelle clé. **Copiez-la tout de suite** : elle commence par `sk-`.

### Étape 2 : créer le fichier secrets.yaml

Le projet fournit un modèle, `secrets.exemple.yaml`. Dans le terminal, placé dans le dossier du projet, copiez-le sous le nom `secrets.yaml` :

```sh
cp -n secrets.exemple.yaml secrets.yaml
```

(`-n` : si `secrets.yaml` existe déjà, il n'est pas écrasé.)

### Étape 3 : y coller les clés

Ouvrez `secrets.yaml` avec un éditeur de texte. Collez chaque clé entre les guillemets, après les deux-points :

```yaml
recherche-apikey: "sk-ant-VOTRE_CLE"
personas-apikey: "sk-ant-VOTRE_CLE"
```

Enregistrez. Gardez les guillemets, ne changez pas les noms des entrées, et ne laissez pas d'espace en début de ligne.

### Étape 4 : vérifier

```sh
uv run search "faire le plein"
```

Si une réponse s'affiche, la clé `recherche-apikey` fonctionne (comme toute réponse du modèle, cette question est payante). Pour `personas-apikey`, lancez une conversation ([section 7](#7-parler-à-un-pnj)). En cas de message d'erreur, voir la [section 12](#12-en-cas-de-problème).

### Remplacer ou retirer une clé

Remplacez la clé dans `secrets.yaml` et enregistrez : elle sert dès la commande suivante. Si vous changez de fournisseur dans `config.yaml`, changez aussi la clé de l'usage concerné.

**Ancienne méthode, toujours acceptée.** Une entrée laissée vide (`""`) ou un fichier `secrets.yaml` absent : l'assistant cherche alors la clé dans la variable d'environnement du fournisseur (`ANTHROPIC_API_KEY` ou `OPENAI_API_KEY`), comme dans les versions précédentes. Une clé écrite dans `secrets.yaml` est prioritaire. Si vous passez au fichier, vous pouvez retirer la ligne `export …_API_KEY=…` de votre `~/.zshrc` (ou `~/.bashrc`).

**Emplacement du fichier.** Le réglage `secrets` de la section `fichiers` de `config.yaml` indique où se trouve le fichier ([section 9](#section-fichiers)). Si vous le déplacez hors du dossier du projet, assurez-vous de ne jamais le partager.

## 5. Les livres de règles et l'index (une seule fois)

L'assistant ne lit pas les PDF pendant la partie : il interroge un **index**, une version des livres préparée pour la recherche. Il faut le créer une fois.

**Étape 1 : placer les PDF.** Copiez les deux livres dans le dossier `rules/MA - Manuel des joueurs 1.5/` du projet, avec **exactement** ces noms de fichiers :

- `MA - Manuel des joueurs 1.5.pdf`
- `MA - Guide du Meneur 1.5.pdf`

**Étape 2 : créer l'index.**

```sh
uv run python -m agent_jdr.core.rules_index build
```

Cela prend quelques secondes et se termine par une ligne comme `2171 passages indexés dans …/data/rules.db`.

Vous n'aurez à refaire cette étape que si les PDF changent ou si l'équipe vous le demande après une mise à jour.

## 6. L'interface web

L'interface web regroupe tout dans une page de votre navigateur : questions de règles, dialogue avec les PNJ (avec historique sauvegardé), création de PNJ, réglages, clés API et ce manuel. Elle tourne sur votre ordinateur ; elle n'est pas accessible depuis Internet.

### Lancer l'interface

```sh
uv run web
```

Le navigateur s'ouvre tout seul sur la page `http://127.0.0.1:8000`. S'il ne s'ouvre pas, copiez cette adresse dans votre navigateur. Le terminal affiche `Interface web : http://127.0.0.1:8000  (Ctrl+C pour arrêter)` : **laissez-le ouvert** pendant toute la partie. Pour arrêter l'interface, revenez dans le terminal et appuyez sur **Ctrl+C**.

| Option | Effet |
|---|---|
| `--port 8001` | Utilise un autre port, si le 8000 est déjà pris (l'adresse devient `http://127.0.0.1:8001`). |
| `--sans-navigateur` | N'ouvre pas le navigateur automatiquement. |
| `--config essai.yaml` | Utilise un autre fichier de configuration ([section 9](#essayer-un-réglage-sans-toucher-au-fichier-principal)). |
| `--hote 0.0.0.0` | Rend l'interface accessible aux autres appareils du réseau local (une tablette à la table, par exemple). **Sans mot de passe** : toute personne du réseau pourrait modifier vos réglages et utiliser vos clés. À éviter sur un réseau public. |

En haut de la page : les onglets **Règles** et **PNJ**, puis deux boutons à droite : **?** ouvre ce manuel, **⚙** ouvre la configuration.

### Onglet Règles

Tapez votre question, puis **Expliquer** (ou la touche **Entrée** ; **Maj+Entrée** passe à la ligne). La réponse s'affiche avec des renvois `[1]`, `[2]` : cliquez sur un renvoi pour aller à sa source (livre, page, section, extrait exact). « Voir le passage complet » déplie le passage du livre. Les réponses s'empilent, la plus récente en haut.

- **Passages seulement** : liste les passages trouvés dans les livres, sans interroger le modèle (gratuit), comme `--brut` en terminal.
- **Passages des livres** : combien de passages envoyer au modèle pour cette question (comme `-n`). Laissé vide : le réglage `passages_envoyes` de la configuration.

### Onglet PNJ : les sessions

Une **session** est une conversation entre un PNJ et un personnage joueur, dans une scène. Elle est **sauvegardée** : vous pouvez fermer le navigateur, arrêter l'interface, et la reprendre plus tard là où vous l'aviez laissée.

1. Cliquez sur **+ Nouvelle session**, choisissez le PNJ, le nom du PJ qui parle, le lieu et le moment (l'ambiance et les enjeux sont facultatifs), puis **Créer**.
2. Tapez la réplique du PJ en bas, puis **Entrée** (ou **Envoyer**). La réponse du PNJ s'affiche quand le modèle a terminé. Sous la réponse, « Règles consultées » indique les pages lues par le PNJ, s'il en a lu.
3. **Scène & faits** affiche la scène et permet d'**ajouter un fait** (l'équivalent de `/fait`), par exemple « Kael pose une pile ouverte sur le comptoir ».

La liste à gauche montre toutes les sessions, la plus récente en haut ; cliquez sur une session pour la reprendre.

- **Effacer l'historique** : efface tous les échanges de la session, mais garde le PNJ, le PJ, la scène et les faits. Pratique pour rejouer une scène depuis le début.
- **Supprimer** : supprime la session entière. Une confirmation est demandée ; c'est définitif.

Si une réponse échoue (clé absente, refus du modèle, coupure réseau), un message rouge s'affiche dans la conversation, le tour **n'est pas enregistré** et votre texte est remis dans la zone de saisie : corrigez le problème ou reformulez, puis renvoyez.

Les sessions sont rangées dans le dossier `data/sessions` (réglage `dossier_des_sessions`), un fichier par session.

### Onglet PNJ : créer un PNJ

Cliquez sur **+ Nouveau PNJ** (ou sur « Créer un PNJ » dans la fenêtre de nouvelle session). Un formulaire s'ouvre, **déjà rempli avec un exemple** (le capitaine Rook) pour vous guider : remplacez chaque texte par celui de votre PNJ.

- **Partir de** : « Modèle guidé » (l'exemple), « Fiche vierge », ou « Copie de » un PNJ existant, pratique pour créer un PNJ proche d'un autre (le nom est alors à saisir).
- Les champs encore **identiques au point de départ sont surlignés** en jaune. Si vous en laissez, l'interface vous le signale avant de créer le PNJ.
- L'**identifiant** se remplit tout seul d'après le nom (`Zéphyr Malo` → `zephyr-malo`) ; c'est le nom du fichier de la fiche. Vous pouvez le modifier.
- Les listes (tics, exemples de répliques, objectifs, connaissances) : **+ Ajouter** ajoute une ligne, **✕** la retire ; les lignes laissées vides sont ignorées. Il faut au moins un objectif.
- **Secrets** : chaque secret a une condition de révélation. **Laissée vide, le PNJ ne révèle jamais ce secret.**

**Créer le PNJ** vérifie la fiche : un champ manquant ou incorrect est indiqué en rouge sous le champ, et rien n'est enregistré. Un PNJ qui existe déjà n'est jamais écrasé (choisissez un autre identifiant). Une fois le PNJ créé, la fenêtre de nouvelle session s'ouvre avec ce PNJ déjà choisi.

La fiche est enregistrée dans le dossier des PNJ (réglage `dossier_des_pnj`), au même format que celles de la [section 10](#10-créer-un-pnj) : vous pouvez ensuite la modifier avec un éditeur de texte. Pour changer l'exemple proposé, modifiez le fichier `agent_jdr/core/modele_pnj.yaml` (réglage `modele_de_pnj`).

### Configuration (bouton ⚙)

**Onglet « Modèles et clés API »** : une carte par usage, « Questions de règles » et « Dialogue avec les PNJ ». Pour chacun :

- **Fournisseur** et **Modèle** : menus déroulants. La liste des modèles, avec leur description et leur prix, vient du fichier `modeles.yaml` ([section 9](#choisir-le-fournisseur-et-le-modèle)).
- **Clé API actuelle** : affichée en partie masquée (par exemple `sk-an***AB`), jamais en entier. L'étiquette indique d'où elle vient : « fichier de secrets », le nom de la variable d'environnement (`ANTHROPIC_API_KEY` ou `OPENAI_API_KEY`), ou « aucune clé ».
- **Nouvelle clé API** : collez une clé pour la remplacer ; laissez vide pour garder l'actuelle. **Effacer la clé** la retire du fichier de secrets.
- **Enregistrer** : écrit le fournisseur et le modèle dans `config.yaml` (les commentaires du fichier sont conservés) et la clé dans `secrets.yaml`.

Si vous changez de fournisseur, saisissez aussi la clé de ce fournisseur : une clé Anthropic ne fonctionne pas chez OpenAI, et inversement.

**Onglet « Fichier config.yaml »** : le fichier complet, modifiable comme dans un éditeur de texte ([section 9](#9-régler-lassistant--le-fichier-configyaml)). La touche Tabulation y insère deux espaces. **Enregistrer le fichier** vérifie tout le fichier avant de l'écrire : en cas d'erreur, le message indique le réglage en cause et **rien n'est modifié**. **Annuler les modifications** revient au fichier enregistré.

Les changements faits depuis l'interface s'appliquent **tout de suite**, sans relancer `uv run web`. Si vous modifiez `config.yaml` à la main pendant que l'interface tourne, c'est pareil : la question ou la réplique suivante utilise le nouveau réglage.

## 7. Parler à un PNJ

Cette section décrit la commande à taper dans le terminal. Dans le navigateur, voir la [section 6](#onglet-pnj--les-sessions).

```sh
uv run parler orla-venn --lieu "Dock 7" --moment "Cycle de nuit" --pj Kael
```

| Élément | Signification |
|---|---|
| `orla-venn` | Le PNJ à jouer : nom de sa fiche, sans `.yaml` (voir [section 10](#10-créer-un-pnj)). Orla Venn est le PNJ d'exemple fourni. |
| `--lieu "…"` | Où se passe la scène. **Obligatoire.** |
| `--moment "…"` | Quand. **Obligatoire.** |
| `--pj …` | Le nom du personnage joueur qui parle. **Obligatoire.** |
| `--ambiance "…"` | L'atmosphère (facultatif), par exemple `--ambiance "Néons qui grésillent, odeur d'ozone"`. |
| `--enjeux "…"` | Ce qui se joue dans la scène (facultatif), par exemple `--enjeux "Kael doit repartir avant la patrouille"`. |

Mettez les textes qui contiennent des espaces **entre guillemets**.

**Pendant la conversation :**

```
Vous parlez à Orla Venn (anthropic, modèle : claude-sonnet-5-5).
/fait <texte> : ajouter un fait à la scène ; /quitter : sortir.
Kael > Combien pour une pile énergétique ?
Orla Venn > *tapote son terminal de poignet* …
    (règles consultées : Manuel des joueurs, p. 196 — …)
Kael >
```

- Tapez la réplique du personnage joueur, puis **Entrée**. Le PNJ répond quand le modèle a terminé (cela peut prendre un moment, surtout s'il consulte les livres).
- La ligne **(règles consultées : …)** n'apparaît que si le PNJ a consulté les livres. Elle indique les pages, pour vérifier au besoin.
- **`/fait <texte>`** ajoute un fait à la scène, que le PNJ prendra en compte. Exemple : `/fait Kael pose une pile ouverte sur le comptoir`. C'est ainsi que vous, meneur, faites évoluer la situation.
- **`/quitter`** termine la conversation. **Ctrl+D** aussi.
- Les flèches **haut** et **bas** rappellent vos lignes précédentes.

**Secrets.** Un PNJ ne révèle un secret que si la condition écrite dans sa fiche est remplie dans la scène. Pour l'essayer avec Orla : son secret sur les piles truquées ne sort que si un personnage prouve la fraude avec une pile ouverte devant elle (le `/fait` ci-dessus).

**Si une réponse échoue** (refus du modèle, coupure réseau), un message `Erreur : … (tour non enregistré)` s'affiche et la conversation continue : reformulez simplement.

**La conversation n'est pas sauvegardée.** Quand vous quittez, le PNJ oublie tout. Pour garder l'historique d'une conversation, utilisez l'interface web ([section 6](#onglet-pnj--les-sessions)).

## 8. Poser une question de règles

```sh
uv run search "expliques moi la dispersion d'une grenade"
```

L'assistant affiche une réponse en français, avec des renvois `[1]`, `[2]`, puis une section **Sources** : pour chaque renvoi, le livre, la page, la section et l'extrait exact utilisé. Il ne répond qu'à partir des livres ; s'il ne trouve pas, il le dit.

Les extraits sont toujours exacts, quel que soit le fournisseur. Avec Anthropic, ils viennent directement du service. Avec OpenAI, le modèle propose ses extraits et l'assistant vérifie chacun, mot pour mot, dans le passage cité : un extrait introuvable est retiré des sources, et une ligne le signale à la fin, par exemple `(1 extrait(s) cité(s) par le modèle introuvable(s) mot pour mot dans les passages : écarté(s) des sources.)`. Si cette ligne apparaît souvent, la réponse mérite d'être vérifiée dans le livre.

Deux variantes utiles :

```sh
# Utiliser plus de passages des livres pour une question large (ici 12)
uv run search "les vaisseaux et le carburant" -n 12

# Voir seulement les passages trouvés, sans interroger le modèle (gratuit)
uv run search "faire le plein" --brut
```

Astuce : la recherche porte sur les mots exacts des livres. Écrivez les termes en toutes lettres : « points de panache » plutôt que « PP ».

## 9. Régler l'assistant : le fichier config.yaml

Tous les réglages sont dans **un seul fichier** : `config.yaml`, à la racine du dossier du projet. Ouvrez-le avec un éditeur de texte simple (TextEdit en mode texte brut sous macOS, Éditeur de texte sous Linux), modifiez, enregistrez, puis relancez la commande : le changement est pris en compte. Vous pouvez aussi le modifier depuis l'interface web (bouton **⚙**, [section 6](#configuration-bouton-)).

**Avant toute modification, faites une copie de sauvegarde** du fichier, par exemple `config.yaml.sauvegarde`, pour pouvoir revenir en arrière.

### Les règles d'écriture

- Modifiez seulement ce qui se trouve **après les deux-points**.
- **Ne touchez pas aux espaces en début de ligne** : ils indiquent à quelle section appartient un réglage. Utilisez des espaces, jamais la touche Tabulation.
- Les lignes qui commencent par `#` sont des commentaires et sont ignorées.
- Si vous faites une erreur, la commande refuse de démarrer et indique le réglage en cause (voir [section 12](#12-en-cas-de-problème)).

### Section `dialogue` (commande `uv run parler`)

| Réglage | Rôle | Valeur fournie |
|---|---|---|
| `fournisseur` | Qui joue les PNJ : `anthropic` ou `openai`. | `anthropic` |
| `modele` | Le modèle qui joue les PNJ ; il doit appartenir au fournisseur choisi (voir le tableau ci-dessous). | `claude-sonnet-5-5` |
| `niveau_de_reflexion` | Combien le modèle réfléchit avant de répondre : `defaut`, `bas`, `moyen`, `eleve`, `tres_eleve`, `maximum`. Plus c'est élevé, plus c'est soigné, lent et cher. `defaut` = le réglage standard du modèle. | `defaut` |
| `longueur_max_reponse` | Taille maximale d'une réponse, réflexion comprise, en jetons (un jeton est un petit morceau de mot). Entre 1 et 128000. | `16000` |
| `recherches_max_par_replique` | Nombre maximal de consultations des livres pour une seule réplique. Au-delà, la réplique est abandonnée avec un message. Entre 1 et 20. | `4` |
| `passages_par_recherche` | Nombre de passages des livres transmis au PNJ à chaque consultation. Entre 1 et 50. | `5` |
| `consignes` | Les instructions données au modèle pour jouer un PNJ (voir plus bas). | texte fourni |

### Section `questions_de_regles` (commande `uv run search`)

| Réglage | Rôle | Valeur fournie |
|---|---|---|
| `fournisseur` | Qui répond aux questions de règles : `anthropic` ou `openai`. | `anthropic` |
| `modele` | Le modèle qui répond aux questions de règles ; il doit appartenir au fournisseur choisi. | `claude-sonnet-5-5` |
| `niveau_de_reflexion` | Comme ci-dessus. | `defaut` |
| `longueur_max_reponse` | Comme ci-dessus. | `16000` |
| `passages_envoyes` | Nombre de passages des livres envoyés au modèle pour chaque question. Entre 1 et 50. L'option `-n` le remplace pour une seule question. | `8` |
| `consignes` | Les instructions pour répondre aux questions de règles. | texte fourni |

### Section `fichiers`

| Réglage | Rôle | Valeur fournie |
|---|---|---|
| `index_des_regles` | L'index créé à la [section 5](#5-les-livres-de-règles-et-lindex-une-seule-fois). | `data/rules.db` |
| `dossier_des_pnj` | Le dossier qui contient les fiches PNJ. | `agent_jdr/core/personas` |
| `dossier_des_pdf` | Le dossier des livres PDF (utilisé seulement pour créer l'index). | `rules/MA - Manuel des joueurs 1.5` |
| `secrets` | Le fichier des clés API ([section 4](#4-les-clés-api-une-seule-fois)). | `secrets.yaml` |
| `dossier_des_sessions` | Le dossier où l'interface web garde les sessions de dialogue et leur historique ([section 6](#onglet-pnj--les-sessions)). | `data/sessions` |
| `catalogue_des_modeles` | La liste des modèles proposés par l'interface web, avec leur description et leur prix. | `modeles.yaml` |
| `modele_de_pnj` | La fiche d'exemple qui pré-remplit le formulaire « Nouveau PNJ » de l'interface web. | `agent_jdr/core/modele_pnj.yaml` |

Les chemins sont relatifs au dossier qui contient `config.yaml`. Un chemin commençant par `/` est un chemin complet.

### Choisir le fournisseur et le modèle

Chaque section (`dialogue`, `questions_de_regles`) a son propre `fournisseur` et son propre `modele`. Le modèle doit appartenir au fournisseur : un modèle Anthropic commence toujours par `claude-`, un modèle OpenAI jamais. Sinon, la commande refuse de démarrer et le signale.

Les modèles disponibles sont listés dans le fichier **`modeles.yaml`**, à la racine du projet. C'est la liste que propose l'interface web. Pour proposer un nouveau modèle dans l'interface, ajoutez un bloc `- nom: …` (avec `description` et `prix` si vous voulez) sous son fournisseur ; l'interface refuse un modèle absent de cette liste. Dans `config.yaml` modifié à la main, tout nom de modèle du bon fournisseur est accepté.

Modèles Anthropic (`fournisseur: anthropic`) :

| Modèle (valeur à écrire) | En résumé | Prix (entrée / sortie, par million de jetons) |
|---|---|---|
| `claude-haiku-5-5` | Rapide et très économique ; le plus susceptible de mal tenir un secret ou d'oublier de consulter les règles. | 0,10 $ / 0,50 $ |
| `claude-sonnet-5-5` | Bon équilibre qualité / prix. **Réglage fourni.** | 2 $ / 10 $ |
| `claude-opus-5-5` | Le plus soigné de la gamme Opus. | 4 $ / 20 $ |
| `claude-opus-4-8` | Génération précédente d'Opus. | 5 $ / 25 $ |

Modèles OpenAI (`fournisseur: openai`), d'après la page officielle d'OpenAI consultée le 2026-11-16 :

| Modèle (valeur à écrire) | En résumé | Prix (entrée / sortie, par million de jetons) |
|---|---|---|
| `gpt-6-luna` | Économique, pour les gros volumes. | 0,10 $ / 0,50 $ |
| `gpt-6.1-terra` | Rapide et efficace. | 1 $ / 5 $ |
| `gpt-6.1-sol` | Équilibre intelligence / coût. | 2 $ / 10 $ |
| `gpt-6-astra` | Le plus puissant d'OpenAI, le plus cher de ces deux listes. | 10 $ / 50 $ |

Les prix et les modèles évoluent : en cas de doute, vérifiez sur les sites des fournisseurs. Certains modèles n'acceptent pas tous les niveaux de réflexion ; le service le signale alors par une erreur au premier message (choisissez `defaut` pour l'éviter). Les modèles OpenAI n'ont pas encore été essayés en partie réelle avec cet assistant.

**Exemple : PNJ joués par OpenAI, questions de règles par Anthropic.**

```yaml
dialogue:
  fournisseur: openai
  modele: gpt-6.1-sol
  …

questions_de_regles:
  fournisseur: anthropic
  modele: claude-sonnet-5-5
  …
```

N'oubliez pas de mettre dans `secrets.yaml` la clé du fournisseur choisi pour cet usage ([section 4](#4-les-clés-api-une-seule-fois)). Au démarrage, `uv run parler` affiche le fournisseur et le modèle utilisés, par exemple `(openai, modèle : gpt-6.1-sol)` : c'est une bonne façon de vérifier que votre changement est pris en compte.

### Modifier les consignes

Les `consignes` sont le texte qui explique au modèle comment se comporter. Elles s'écrivent après `consignes: |`, **chaque ligne décalée de 4 espaces** :

```yaml
  consignes: |
    Tu incarnes un personnage non joueur (PNJ) …
    - Réponds en français …
```

Pour le dialogue, la fiche du PNJ et la description de la scène sont ajoutées automatiquement après vos consignes : inutile de les recopier.

Attention : une consigne mal formulée ne provoque **aucun message d'erreur**, mais peut dégrader le jeu du PNJ (il sort de son personnage, révèle ses secrets, invente des règles). Modifiez par petites touches, testez avec une courte conversation, et gardez votre copie de sauvegarde.

### Essayer un réglage sans toucher au fichier principal

Faites une copie du fichier, modifiez la copie, puis indiquez-la avec `--config` :

```sh
cp config.yaml essai.yaml
# … modifiez essai.yaml, par exemple le modèle …
uv run parler orla-venn --lieu "Dock 7" --moment "Nuit" --pj Kael --config essai.yaml
```

`--config` fonctionne aussi avec `uv run search`.

## 10. Créer un PNJ

Le plus simple est le formulaire de l'interface web, pré-rempli et vérifié à chaque champ ([section 6](#onglet-pnj--créer-un-pnj)). Cette section explique comment écrire une fiche à la main.

Chaque PNJ est un fichier texte `.yaml` dans le dossier `agent_jdr/core/personas/` (réglage `dossier_des_pnj`). Pour en écrire une à la main, **copiez la fiche d'exemple** et modifiez-la :

```sh
cp agent_jdr/core/personas/orla-venn.yaml agent_jdr/core/personas/capitaine-rook.yaml
```

Ouvrez la nouvelle fiche et remplacez le contenu :

| Champ | Obligatoire | Contenu |
|---|---|---|
| `id` | oui | Identifiant du PNJ, **identique au nom du fichier** sans `.yaml`. Uniquement des minuscules sans accents, des chiffres et des tirets entre les mots : `capitaine-rook`. |
| `nom` | oui | Nom affiché : `Capitaine Rook`. |
| `espece` | oui | `Humain`, etc. |
| `origine` | oui | D'où vient le personnage. |
| `role` | oui | Ce qu'il fait dans l'histoire. |
| `personnalite` | oui | Son caractère, en quelques phrases. |
| `parole` | oui | Sa façon de parler : `registre` (obligatoire), et si vous voulez `tics` (liste) et `exemples` de répliques (liste). |
| `objectifs` | oui | Ce qu'il veut. **Au moins un**, sous forme de liste. |
| `connaissances` | non | Ce qu'il sait (liste). |
| `secrets` | non | Liste de secrets. Chacun a un `contenu` et, si vous le voulez, une `condition_revelation` : la seule situation où il le révèle. **Sans condition, il ne le révèle jamais.** |
| `attitude_envers_pj` | oui | Comment il traite les personnages joueurs. |

Règles d'écriture :

- Une **liste** s'écrit avec un tiret par élément, décalé de 2 espaces sous le nom du champ.
- Un texte qui contient deux-points (`:`) ou qui commence par un guillemet doit être mis **entre guillemets** : `- "Une pile, capitaine ? Ça dépend."`.
- Pour un texte long sur plusieurs lignes, écrivez `>` après les deux-points, puis le texte sur les lignes suivantes, décalé de 2 espaces (voir `personnalite` dans la fiche d'Orla).
- Les fiches ne contiennent **pas de caractéristiques chiffrées** : pour les règles, le PNJ consulte les livres.

**Vérifier ses fiches** (gratuit, sans appel à un modèle) :

```sh
uv run python -c "from agent_jdr.core.config import charger_config; from agent_jdr.core.persona import charger_personas; print(list(charger_personas(charger_config().fichiers.dossier_des_pnj)))"
```

Si tout va bien, la liste des identifiants s'affiche : `['capitaine-rook', 'orla-venn']`. Sinon, un long message d'erreur s'affiche ; sa **dernière ligne** nomme le fichier et le champ en cause, par exemple `PersonaInvalide: capitaine-rook.yaml : role : Field required` (champ manquant). Le même message, plus court, s'affiche si vous lancez `uv run parler`.

Puis jouez-le :

```sh
uv run parler capitaine-rook --lieu "Passerelle" --moment "Avant le saut" --pj Kael
```

## 11. Combien ça coûte

Chaque réplique d'un PNJ et chaque question de règles est facturée sur votre compte chez le fournisseur choisi (Anthropic ou OpenAI), selon le nombre de **jetons** envoyés et reçus (voir les prix à la [section 9](#choisir-le-fournisseur-et-le-modèle)). Ce qui fait grimper la note :

- **le modèle** : c'est le premier levier ; par exemple, `claude-sonnet-5-5` et `gpt-6.1-sol` coûtent 5 fois moins que `gpt-6-astra`, et `claude-haiku-5-5` ou `gpt-6-luna` 100 fois moins ;
- **la longueur de la conversation** : à chaque réplique, toute la conversation depuis le début est renvoyée ; une très longue conversation coûte plus cher par réplique (les deux fournisseurs gardent en cache le début de la conversation, ce qui doit réduire ce coût ; l'économie réelle n'a pas encore été mesurée) ;
- **le niveau de réflexion** : plus il est élevé, plus le modèle produit de jetons ;
- **les consultations des livres** : chacune ajoute un aller-retour avec le modèle.

Le coût réel d'une partie n'a pas encore été mesuré. Pour le suivre, consultez les pages d'utilisation de la console Anthropic (<https://console.anthropic.com>) et de la plateforme OpenAI (<https://platform.openai.com>).

`uv run search "…" --brut`, le bouton **Passages seulement** de l'interface web, la création de PNJ et la vérification des fiches PNJ sont gratuits : ils n'interrogent aucun modèle.

## 12. En cas de problème

| Message affiché | Cause | Solution |
|---|---|---|
| `command not found: uv` ou `commande introuvable` | uv n'est pas installé, ou le terminal n'a pas été rouvert après l'installation. | [Section 3](#3-installation-une-seule-fois), puis rouvrir le terminal. |
| `Erreur : Aucun identifiant Anthropic trouvé : clé absente du fichier de secrets …` ou `Erreur : Aucune clé OpenAI trouvée : …`, suivi de `Renseignez la clé « … » dans …` | L'entrée nommée de `secrets.yaml` est vide, ou le fichier n'existe pas. | Collez la clé dans l'entrée indiquée, dans le fichier indiqué ([section 4](#4-les-clés-api-une-seule-fois), étapes 2 et 3). |
| `Identifiants Anthropic refusés : …` ou `Clé OpenAI refusée : …` | Clé mal copiée, supprimée, désactivée, ou d'un autre fournisseur que celui choisi dans `config.yaml` pour cet usage. | Recopiez la clé, ou créez-en une nouvelle et remplacez l'ancienne dans `secrets.yaml`. |
| `Erreur : configuration : secrets.yaml : réglages incorrects` (ou `Erreur de configuration : secrets.yaml : …` avec `search`) suivi de `… : réglage inconnu (faute de frappe ?)` | Nom d'entrée mal écrit dans `secrets.yaml`. | Écrivez exactement `recherche-apikey` et `personas-apikey`. |
| `… secrets.yaml : syntaxe YAML incorrecte` | Guillemet non fermé, espace en début de ligne ou tabulation dans `secrets.yaml`. | Corrigez la ligne indiquée (`line`), ou recopiez `secrets.exemple.yaml` et recollez les clés. |
| `Erreur : API Anthropic : …` ou `Erreur : API OpenAI : …` mentionnant le crédit ou la facturation | Crédits épuisés chez ce fournisseur. | Ajoutez des crédits sur son site. |
| `Erreur : API Anthropic : …` ou `Erreur : API OpenAI : …` mentionnant le modèle (`model`) | Nom de modèle mal écrit ou inexistant dans `config.yaml`. | Recopiez un nom exact du [tableau des modèles](#choisir-le-fournisseur-et-le-modèle). |
| `… : le modèle « … » n'est pas un modèle Anthropic …` ou `… est un modèle Anthropic, pas OpenAI …` | `fournisseur` et `modele` ne correspondent pas dans une section de `config.yaml`. | Mettez un modèle du bon fournisseur, ou changez le fournisseur. |
| `Erreur : Index des règles absent : … Le construire avec : …` | L'index n'a pas été créé, ou `index_des_regles` pointe au mauvais endroit. | [Section 5](#5-les-livres-de-règles-et-lindex-une-seule-fois). |
| Un long message qui se termine par `FileNotFoundError: PDF de règles introuvable : …` | Lors de la création de l'index, un PDF manque ou porte un autre nom. | Vérifiez l'emplacement et les noms exacts des PDF ([section 5](#5-les-livres-de-règles-et-lindex-une-seule-fois)). |
| `Erreur : PNJ inconnu « … ». Disponibles : …` | Faute de frappe dans le nom du PNJ, ou fiche absente du dossier. | Utilisez un des noms listés après « Disponibles ». |
| `Erreur : ….yaml : …` en lançant `parler` | Une fiche PNJ est mal remplie (même si ce n'est pas celle que vous lancez). | Corrigez le champ indiqué ([section 10](#10-créer-un-pnj)). |
| `Erreur : configuration : config.yaml : réglages incorrects` suivi d'une liste | Un réglage de `config.yaml` est mal écrit. Chaque ligne donne la section, le réglage et le problème. | Voir les exemples ci-dessous, ou revenez à votre copie de sauvegarde. |
| `Erreur : configuration : config.yaml : syntaxe YAML incorrecte` | Décalage d'espaces cassé, tabulation, ou guillemet non fermé. Le message indique la ligne (`line`) et la colonne (`column`). | Corrigez la ligne indiquée, ou revenez à votre copie de sauvegarde. |
| `parler: error: the following arguments are required: …` | Il manque un élément obligatoire de la commande. | Ajoutez ceux qui sont listés (`--lieu`, `--moment`, `--pj`, le nom du PNJ). |
| `Erreur : Le modèle a refusé de répondre.` | Le modèle a refusé de répondre (en partie : `(tour non enregistré …)`). | Reformulez. |
| `Erreur : Réponse tronquée : limite de longueur atteinte.` | La réponse dépassait `longueur_max_reponse`. | Augmentez ce réglage (OpenAI recommande de prévoir large pour ses modèles qui réfléchissent). |
| `Erreur : Réponse du modèle mal formée (JSON attendu).` | Avec OpenAI, la réponse à une question de règles n'avait pas le format imposé. | Relancez la question. |
| `Erreur : le port 8000 est déjà utilisé …` (avec `uv run web`) | L'interface est déjà lancée dans un autre terminal, ou un autre programme utilise ce port. | Utilisez l'interface déjà ouverte, ou lancez `uv run web --port 8001`. |
| Dans le navigateur : `Serveur injoignable. La commande « uv run web » est-elle toujours lancée ?` | Le terminal de l'interface a été fermé, ou Ctrl+C a été pressé. | Relancez `uv run web` et rechargez la page. |
| Dans le navigateur : `Configuration invalide (corrigez-la dans la fenêtre Config) : …` | `config.yaml` contient une erreur (le message indique laquelle). | Bouton **⚙**, onglet « Fichier config.yaml » : corrigez et enregistrez. |
| Dans le navigateur : `… Saisissez la clé dans la fenêtre Config (bouton ⚙ en haut à droite).` | Aucune clé pour cet usage, ou clé refusée. | Bouton **⚙** : collez la clé de l'usage concerné et **Enregistrer** ([section 6](#configuration-bouton-)). |
| Dans le navigateur : `Rien n'a été enregistré : …` | Le fichier `config.yaml` modifié, ou la clé saisie, contient une erreur. La suite du message indique laquelle. | Corrigez et enregistrez à nouveau ; le fichier n'a pas été touché. |
| Dans le navigateur : `Modèle « … » absent du catalogue pour …` | Ce modèle n'est pas listé dans `modeles.yaml`. | Choisissez un modèle du menu, ou ajoutez-le à `modeles.yaml` ([section 9](#choisir-le-fournisseur-et-le-modèle)). |
| Dans le formulaire « Nouveau PNJ » : `Fiche incomplète ou incorrecte : …`, et un message rouge sous des champs | Un champ obligatoire est vide, ou l'identifiant contient des majuscules, des accents ou des espaces. | Complétez les champs signalés. Si l'identifiant `existe déjà`, choisissez-en un autre. |
| `Erreur : Trop de recherches de règles (4) sans réplique finale.` | Le PNJ a cherché dans les livres sans trouver de quoi répondre. | Reformulez, ou augmentez `recherches_max_par_replique`. |

**Exemples de messages sur `config.yaml` :**

```
  - dialogue > modèle : réglage inconnu (faute de frappe ?)
```
Le nom du réglage est mal écrit (ici avec un accent) : il faut écrire `modele`.

```
  - dialogue > modele : réglage manquant
```
La ligne `modele:` a été effacée dans la section `dialogue`.

```
  - dialogue > niveau_de_reflexion : valeur non permise ; choix possibles : 'defaut', 'bas', 'moyen', 'eleve', 'tres_eleve' ou 'maximum'
```
Choisissez une des valeurs proposées, sans accent.

```
  - questions_de_regles > passages_envoyes : doit être au moins 1
```
La valeur est hors des limites indiquées dans les tableaux de la [section 9](#9-régler-lassistant--le-fichier-configyaml).

**Revenir au réglage d'origine.** Si vous n'avez pas fait de copie de sauvegarde et que le dossier du projet est suivi par git, cette commande remet `config.yaml` dans son état d'origine (vos modifications de ce fichier sont perdues) :

```sh
git checkout config.yaml
```
