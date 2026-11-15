"""Couche 4 : LLM réel sur un scénario figé. Lent et payant : exclu par défaut.

Lancer avec : uv run pytest -m eval
Nécessite l'index `data/rules.db` et des identifiants Anthropic.
"""

import os

import pytest

from agent_jdr.core.rules_index import DB_DEFAUT, RulesIndex
from agent_jdr.core.rules_qa import repondre

pytestmark = pytest.mark.eval


@pytest.fixture(scope="module")
def index():
    if not DB_DEFAUT.is_file():
        pytest.skip(f"Index absent ({DB_DEFAUT})")
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        pytest.skip("Identifiants Anthropic absents (ANTHROPIC_API_KEY)")
    with RulesIndex(DB_DEFAUT) as idx:
        yield idx


def test_grenade_cite_la_page_174(index):
    reponse = repondre("expliques moi la dispersion d'une grenade", index)
    assert reponse.texte.strip()
    cites = [(s.passage.livre, s.passage.page) for s in reponse.sources]
    assert ("Manuel des joueurs", 174) in cites, f"p. 174 non citée ; sources : {cites}"
    # Chaque extrait cité figure mot pour mot dans son passage d'origine.
    for source in reponse.sources:
        for extrait in source.extraits:
            assert extrait in source.passage.texte
