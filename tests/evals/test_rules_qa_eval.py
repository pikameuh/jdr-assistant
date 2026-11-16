"""Couche 4 : LLM réel sur un scénario figé. Lent et payant : exclu par défaut.

Lancer avec : uv run pytest -m eval
Nécessite l'index `data/rules.db` et la clé du fournisseur choisi : entrée
`recherche-apikey` de secrets.yaml, ou variable d'environnement du fournisseur.
"""

import os

import pytest

from agent_jdr.core.config import charger_config, charger_secrets
from agent_jdr.core.fournisseurs import creer_fournisseur
from agent_jdr.core.rules_index import RulesIndex
from agent_jdr.core.rules_qa import repondre

# Les évals mesurent la configuration réelle (modèle, consignes, clés) du projet.
CONFIG = charger_config()
CLE = charger_secrets(CONFIG.fichiers.secrets).recherche
VARIABLES = {"anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"), "openai": ("OPENAI_API_KEY",)}

pytestmark = pytest.mark.eval


@pytest.fixture(scope="module")
def index():
    db = CONFIG.fichiers.index_des_regles
    if not db.is_file():
        pytest.skip(f"Index absent ({db})")
    variables = VARIABLES[CONFIG.questions_de_regles.fournisseur]
    if not (CLE or any(os.environ.get(v) for v in variables)):
        pytest.skip(f"Clé absente (recherche-apikey dans secrets.yaml, ou {variables[0]})")
    with RulesIndex(db) as idx:
        yield idx


def test_grenade_cite_la_page_174(index):
    reglages = CONFIG.questions_de_regles
    fournisseur = creer_fournisseur(reglages, cle_api=CLE)
    reponse = repondre("expliques moi la dispersion d'une grenade", index, reglages, fournisseur)
    assert reponse.texte.strip()
    cites = [(s.passage.livre, s.passage.page) for s in reponse.sources]
    assert ("Manuel des joueurs", 174) in cites, f"p. 174 non citée ; sources : {cites}"
    # Chaque extrait cité figure mot pour mot dans son passage d'origine.
    for source in reponse.sources:
        for extrait in source.extraits:
            assert extrait in source.passage.texte
