# Manuel de démarrage et de configuration

Assistant du meneur pour **Metal Adventures 1.5**. Ce manuel s'adresse à une personne qui n'est pas développeuse. Il suffit de savoir ouvrir un terminal et d'y copier des commandes.

## Sommaire

1. [À quoi sert l'assistant](#1-à-quoi-sert-lassistant)
2. [Ce qu'il faut avant de commencer](#2-ce-quil-faut-avant-de-commencer)
3. [Installation (une seule fois)](#3-installation-une-seule-fois)
4. [Les clés API (une seule fois)](#4-les-clés-api-une-seule-fois)
5. [Les livres de règles et l'index (une seule fois)](#5-les-livres-de-règles-et-lindex-une-seule-fois)
6. [Parler à un PNJ](#6-parler-à-un-pnj)
7. [Poser une question de règles](#7-poser-une-question-de-règles)
8. [Régler l'assistant : le fichier config.yaml](#8-régler-lassistant--le-fichier-configyaml)
9. [Créer un PNJ](#9-créer-un-pnj)
10. [Combien ça coûte](#10-combien-ça-coûte)
11. [En cas de problème](#11-en-cas-de-problème)

---

## 1. À quoi sert l'assistant

Pendant une partie, l'assistant joue les **personnages non joueurs (PNJ)** à votre place. Vous tapez ce que dit le personnage d'un joueur ; le PNJ répond avec sa personnalité, sa façon de parler, ses objectifs et ses secrets. Quand sa réponse dépend d'une règle du jeu (un prix, un équipement, une procédure), il consulte lui-même les livres de règles, et l'assistant vous indique les pages consultées pour que vous puissiez vérifier.

L'assistant répond aussi aux **questions de règles** (« comment fonctionne la dispersion d'une grenade ? »), en citant les passages exacts des livres.

Les réponses sont rédigées par un modèle d'intelligence artificielle interrogé par Internet. Deux **fournisseurs** sont possibles : **Anthropic** (modèles Claude) et **OpenAI** (modèles GPT). Vous choisissez dans la configuration lequel joue les PNJ et lequel répond aux questions de règles ; ce peut être le même ou deux différents (voir [section 8](#8-régler-lassistant--le-fichier-configyaml)). Chaque réponse est payante (voir [section 10](#10-combien-ça-coûte)).

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

Une **clé API** est un mot de passe qui permet à l'assistant d'interroger un fournisseur et de facturer votre compte. Il vous faut la clé de **chaque fournisseur utilisé** dans `config.yaml` : par défaut, seulement Anthropic. **Ne donnez jamais une clé à personne et ne la mettez jamais dans le dossier du projet.**

### Clé Anthropic

**Étape 1 : créer la clé.**

1. Allez sur <https://console.anthropic.com> et connectez-vous (ou créez un compte).
2. Ajoutez des crédits ou un moyen de paiement dans la partie facturation de la console.
3. Ouvrez la page **API Keys**, puis cliquez sur **Create Key**. Donnez-lui un nom, par exemple `assistant-jdr`.
4. **Copiez la clé tout de suite** : elle commence par `sk-ant-` et ne sera plus affichée ensuite.

**Étape 2 : l'enregistrer sur votre ordinateur.** Trouvez d'abord quel terminal vous utilisez :

```sh
echo $SHELL
```

Si la réponse se termine par `zsh` (cas par défaut sous macOS), tapez la commande ci-dessous en remplaçant `sk-ant-VOTRE_CLE` par votre clé :

```sh
echo 'export ANTHROPIC_API_KEY=sk-ant-VOTRE_CLE' >> ~/.zshrc
```

Si la réponse se termine par `bash`, remplacez `~/.zshrc` par `~/.bashrc` dans la commande.

Puis **fermez le terminal et rouvrez-en un nouveau**.

**Étape 3 : vérifier.**

```sh
echo $ANTHROPIC_API_KEY | cut -c1-7
```

La réponse doit être `sk-ant-`. Si elle est vide, la clé n'est pas enregistrée : reprenez l'étape 2, et vérifiez que vous avez bien rouvert un terminal.

### Clé OpenAI (seulement si vous choisissez OpenAI)

1. Allez sur <https://platform.openai.com> et connectez-vous (ou créez un compte).
2. Ajoutez des crédits ou un moyen de paiement dans la partie facturation.
3. Ouvrez la page des clés API (**API keys**), puis créez une nouvelle clé. **Copiez-la tout de suite** : elle commence par `sk-`.
4. Enregistrez-la comme la clé Anthropic, mais sous le nom `OPENAI_API_KEY` (remplacez `~/.zshrc` par `~/.bashrc` si votre terminal est `bash`) :

```sh
echo 'export OPENAI_API_KEY=sk-VOTRE_CLE' >> ~/.zshrc
```

5. Fermez le terminal, rouvrez-en un, puis vérifiez :

```sh
echo $OPENAI_API_KEY | cut -c1-3
```

La réponse doit être `sk-`.

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

## 6. Parler à un PNJ

```sh
uv run parler orla-venn --lieu "Dock 7" --moment "Cycle de nuit" --pj Kael
```

| Élément | Signification |
|---|---|
| `orla-venn` | Le PNJ à jouer : nom de sa fiche, sans `.yaml` (voir [section 9](#9-créer-un-pnj)). Orla Venn est le PNJ d'exemple fourni. |
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

**La conversation n'est pas sauvegardée.** Quand vous quittez, le PNJ oublie tout.

## 7. Poser une question de règles

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

## 8. Régler l'assistant : le fichier config.yaml

Tous les réglages sont dans **un seul fichier** : `config.yaml`, à la racine du dossier du projet. Ouvrez-le avec un éditeur de texte simple (TextEdit en mode texte brut sous macOS, Éditeur de texte sous Linux), modifiez, enregistrez, puis relancez la commande : le changement est pris en compte.

**Avant toute modification, faites une copie de sauvegarde** du fichier, par exemple `config.yaml.sauvegarde`, pour pouvoir revenir en arrière.

### Les règles d'écriture

- Modifiez seulement ce qui se trouve **après les deux-points**.
- **Ne touchez pas aux espaces en début de ligne** : ils indiquent à quelle section appartient un réglage. Utilisez des espaces, jamais la touche Tabulation.
- Les lignes qui commencent par `#` sont des commentaires et sont ignorées.
- Si vous faites une erreur, la commande refuse de démarrer et indique le réglage en cause (voir [section 11](#11-en-cas-de-problème)).

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

Les chemins sont relatifs au dossier qui contient `config.yaml`. Un chemin commençant par `/` est un chemin complet.

### Choisir le fournisseur et le modèle

Chaque section (`dialogue`, `questions_de_regles`) a son propre `fournisseur` et son propre `modele`. Le modèle doit appartenir au fournisseur : un modèle Anthropic commence toujours par `claude-`, un modèle OpenAI jamais. Sinon, la commande refuse de démarrer et le signale.

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

N'oubliez pas la clé du fournisseur choisi ([section 4](#4-les-clés-api-une-seule-fois)). Au démarrage, `uv run parler` affiche le fournisseur et le modèle utilisés, par exemple `(openai, modèle : gpt-6.1-sol)` : c'est une bonne façon de vérifier que votre changement est pris en compte.

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

## 9. Créer un PNJ

Chaque PNJ est un fichier texte `.yaml` dans le dossier `agent_jdr/core/personas/` (réglage `dossier_des_pnj`). Le plus simple est de **copier la fiche d'exemple** et de la modifier :

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

## 10. Combien ça coûte

Chaque réplique d'un PNJ et chaque question de règles est facturée sur votre compte chez le fournisseur choisi (Anthropic ou OpenAI), selon le nombre de **jetons** envoyés et reçus (voir les prix à la [section 8](#choisir-le-fournisseur-et-le-modèle)). Ce qui fait grimper la note :

- **le modèle** : c'est le premier levier ; par exemple, `claude-sonnet-5-5` et `gpt-6.1-sol` coûtent 5 fois moins que `gpt-6-astra`, et `claude-haiku-5-5` ou `gpt-6-luna` 100 fois moins ;
- **la longueur de la conversation** : à chaque réplique, toute la conversation depuis le début est renvoyée ; une très longue conversation coûte plus cher par réplique (les deux fournisseurs gardent en cache le début de la conversation, ce qui doit réduire ce coût ; l'économie réelle n'a pas encore été mesurée) ;
- **le niveau de réflexion** : plus il est élevé, plus le modèle produit de jetons ;
- **les consultations des livres** : chacune ajoute un aller-retour avec le modèle.

Le coût réel d'une partie n'a pas encore été mesuré. Pour le suivre, consultez les pages d'utilisation de la console Anthropic (<https://console.anthropic.com>) et de la plateforme OpenAI (<https://platform.openai.com>).

`uv run search "…" --brut` et la vérification des fiches PNJ sont gratuits : ils n'interrogent aucun modèle.

## 11. En cas de problème

| Message affiché | Cause | Solution |
|---|---|---|
| `command not found: uv` ou `commande introuvable` | uv n'est pas installé, ou le terminal n'a pas été rouvert après l'installation. | [Section 3](#3-installation-une-seule-fois), puis rouvrir le terminal. |
| `Erreur : Aucun identifiant Anthropic trouvé. Définir la variable ANTHROPIC_API_KEY …` | La clé n'est pas enregistrée dans ce terminal. | [Section 4](#4-les-clés-api-une-seule-fois), étape 3. |
| `Erreur : Aucune clé OpenAI trouvée. Définir la variable OPENAI_API_KEY.` | Un réglage utilise OpenAI, mais sa clé n'est pas enregistrée dans ce terminal. | [Section 4](#4-les-clés-api-une-seule-fois), clé OpenAI. |
| `Identifiants Anthropic refusés : …` ou `Clé OpenAI refusée : …` | Clé mal copiée, supprimée ou désactivée. | Créez une nouvelle clé et remplacez l'ancienne dans `~/.zshrc` (ou `~/.bashrc`). |
| `Erreur : API Anthropic : …` ou `Erreur : API OpenAI : …` mentionnant le crédit ou la facturation | Crédits épuisés chez ce fournisseur. | Ajoutez des crédits sur son site. |
| `Erreur : API Anthropic : …` ou `Erreur : API OpenAI : …` mentionnant le modèle (`model`) | Nom de modèle mal écrit ou inexistant dans `config.yaml`. | Recopiez un nom exact du [tableau des modèles](#choisir-le-fournisseur-et-le-modèle). |
| `… : le modèle « … » n'est pas un modèle Anthropic …` ou `… est un modèle Anthropic, pas OpenAI …` | `fournisseur` et `modele` ne correspondent pas dans une section de `config.yaml`. | Mettez un modèle du bon fournisseur, ou changez le fournisseur. |
| `Erreur : Index des règles absent : … Le construire avec : …` | L'index n'a pas été créé, ou `index_des_regles` pointe au mauvais endroit. | [Section 5](#5-les-livres-de-règles-et-lindex-une-seule-fois). |
| Un long message qui se termine par `FileNotFoundError: PDF de règles introuvable : …` | Lors de la création de l'index, un PDF manque ou porte un autre nom. | Vérifiez l'emplacement et les noms exacts des PDF ([section 5](#5-les-livres-de-règles-et-lindex-une-seule-fois)). |
| `Erreur : PNJ inconnu « … ». Disponibles : …` | Faute de frappe dans le nom du PNJ, ou fiche absente du dossier. | Utilisez un des noms listés après « Disponibles ». |
| `Erreur : ….yaml : …` en lançant `parler` | Une fiche PNJ est mal remplie (même si ce n'est pas celle que vous lancez). | Corrigez le champ indiqué ([section 9](#9-créer-un-pnj)). |
| `Erreur : configuration : config.yaml : réglages incorrects` suivi d'une liste | Un réglage de `config.yaml` est mal écrit. Chaque ligne donne la section, le réglage et le problème. | Voir les exemples ci-dessous, ou revenez à votre copie de sauvegarde. |
| `Erreur : configuration : config.yaml : syntaxe YAML incorrecte` | Décalage d'espaces cassé, tabulation, ou guillemet non fermé. Le message indique la ligne (`line`) et la colonne (`column`). | Corrigez la ligne indiquée, ou revenez à votre copie de sauvegarde. |
| `parler: error: the following arguments are required: …` | Il manque un élément obligatoire de la commande. | Ajoutez ceux qui sont listés (`--lieu`, `--moment`, `--pj`, le nom du PNJ). |
| `Erreur : Le modèle a refusé de répondre.` | Le modèle a refusé de répondre (en partie : `(tour non enregistré …)`). | Reformulez. |
| `Erreur : Réponse tronquée : limite de longueur atteinte.` | La réponse dépassait `longueur_max_reponse`. | Augmentez ce réglage (OpenAI recommande de prévoir large pour ses modèles qui réfléchissent). |
| `Erreur : Réponse du modèle mal formée (JSON attendu).` | Avec OpenAI, la réponse à une question de règles n'avait pas le format imposé. | Relancez la question. |
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
La valeur est hors des limites indiquées dans les tableaux de la [section 8](#8-régler-lassistant--le-fichier-configyaml).

**Revenir au réglage d'origine.** Si vous n'avez pas fait de copie de sauvegarde et que le dossier du projet est suivi par git, cette commande remet `config.yaml` dans son état d'origine (vos modifications de ce fichier sont perdues) :

```sh
git checkout config.yaml
```
