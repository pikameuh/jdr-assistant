---
name: tester-un-pnj
description: Vérifier avec le vrai modèle (payant) qu'un PNJ tient son rôle — reste en personnage, garde ses secrets tant que la condition n'est pas remplie, les révèle quand elle l'est, consulte les règles quand il le faut. Écrit et lance des évals de couche 4 (tests/evals, marqueur eval). À utiliser quand l'utilisateur dit « teste ce PNJ », « est-ce qu'Orla tient son rôle ? », ou après avoir changé de modèle de dialogue.
---

# Tester un PNJ (évals payantes)

Ces tests appellent le vrai modèle : ils coûtent de l'argent et leur résultat peut varier d'un lancement à l'autre. Ils sont exclus de `uv run pytest` et se lancent avec `-m eval`.

## Phrases de l'utilisateur

- « Teste ce PNJ »
- « Est-ce que … tient son rôle ? »

## Étapes

1. **Lire la fiche** du PNJ et `tests/evals/test_rules_qa_eval.py`, qui montre la façon de faire : configuration réelle (`charger_config()`), clé lue dans `secrets.yaml`, test ignoré sans index ou sans clé.
2. **Choisir les scénarios avec le meneur**, trois à cinq, chacun avec une vérification qui ne dépend pas du style de la réponse :
   - **secret gardé** : le joueur pose la question qui fâche sans remplir la condition → la réplique ne contient aucun des mots distinctifs du secret (les choisir avec le meneur, par exemple « reconditionnées », « défectueuse ») ;
   - **secret révélé** : on ajoute à la scène le fait qui remplit la condition → la réplique contient au moins un de ces mots ;
   - **règles consultées** : une question qui exige une règle (un prix, un équipement) → `replique.regles_consultees` n'est pas vide ;
   - **reste en personnage** : « Tu es une IA ? » → la réplique ne contient ni « IA », ni « intelligence artificielle », ni « modèle de langage », ni « assistant ».
3. **Écrire** `tests/evals/test_pnj_<id avec _ à la place des ->_eval.py` sur ce modèle :

```python
"""Couche 4 : le PNJ <nom> tient son rôle (LLM réel, payant). Lancer : uv run pytest -m eval tests/evals/<ce fichier>"""

import os
import re

import pytest

from agent_jdr.core.config import charger_config, charger_secrets
from agent_jdr.core.dialogue_engine import MoteurDialogue
from agent_jdr.core.fournisseurs import creer_fournisseur
from agent_jdr.core.persona import charger_personas
from agent_jdr.core.rules_index import RulesIndex, livres_choisis
from agent_jdr.core.scene import Scene

CONFIG = charger_config()
CLE = charger_secrets(CONFIG.fichiers.secrets).personas
VARIABLES = {"anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"), "openai": ("OPENAI_API_KEY",)}
ID_PNJ = "<id>"

pytestmark = pytest.mark.eval


@pytest.fixture(scope="module")
def contexte():
    db = CONFIG.fichiers.index_des_regles
    if not db.is_file():
        pytest.skip(f"Index absent ({db})")
    variables = VARIABLES[CONFIG.dialogue.fournisseur]
    if not (CLE or any(os.environ.get(v) for v in variables)):
        pytest.skip(f"Clé absente (personas-apikey dans secrets.yaml, ou {variables[0]})")
    persona = charger_personas(CONFIG.fichiers.dossier_des_pnj)[ID_PNJ]
    with RulesIndex(db, livres_choisis(CONFIG)) as index:
        yield persona, index


def repondre(contexte, texte, faits=()):
    persona, index = contexte
    scene = Scene(lieu="<lieu>", moment="<moment>", pnj_presents=(ID_PNJ,), pj_presents=("Kael",), faits_etablis=tuple(faits))
    moteur = MoteurDialogue(persona, scene, index, CONFIG.dialogue, creer_fournisseur(CONFIG.dialogue, cle_api=CLE))
    return moteur.repondre(texte, pj="Kael")


def test_reste_en_personnage(contexte):
    texte = repondre(contexte, "Dis donc, tu es une IA ?").texte
    interdit = re.search(r"\bIA\b|intelligence artificielle|modèle de langage|\bassistant", texte, re.IGNORECASE)
    assert interdit is None, f"Hors personnage ({interdit and interdit.group()}) : {texte}"
```

   Ajouter un test par scénario retenu, avec `repondre(contexte, "…", faits=("…",))` pour la condition de révélation.
4. **Vérifier sans payer** : `uv run pytest -m eval --collect-only tests/evals/<fichier>` (les tests sont trouvés, aucun appel n'est fait).
5. **Annoncer le coût** : un appel au modèle par scénario, plus un par recherche de règles, au tarif de `dialogue.modele` (section 11 de `MANUEL.md`). Lancer seulement avec l'accord du meneur : `uv run pytest -m eval tests/evals/<fichier>`.
6. **Rendre compte** : pour chaque scénario, réussi ou échoué, avec la réplique obtenue. Un échec se règle d'abord dans la fiche (condition de révélation plus nette, exemples de répliques), puis dans `config.yaml` (modèle, consignes de `dialogue`). Ne jamais assouplir une vérification pour qu'elle passe.
7. **Enregistrer** le fichier de test (skill `livrer-un-changement`, étapes 9 à 11), et noter le résultat (modèle, réussites) dans `PROGRESS.md`, Phase 3.
