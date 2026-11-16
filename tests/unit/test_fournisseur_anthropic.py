"""Couche 1 : traduction vers l'API Anthropic (requête, citations, erreurs), sans réseau."""

from unittest.mock import MagicMock

import anthropic
import httpx2
import pytest

from agent_jdr.core.fournisseurs import creer_fournisseur
from agent_jdr.core.fournisseurs.base import ErreurFournisseur, IdentifiantsAbsents, ReponseIncomplete
from agent_jdr.core.fournisseurs.fournisseur_anthropic import (
    FournisseurAnthropic,
    construire_requete,
    lire_reponse,
)
from tests.reglages_test import CONFIG_TEST, CONSIGNES_REGLES
from tests.unit.test_rules_qa import GABARIT, GRENADE, PASSAGES

REGLAGES = CONFIG_TEST.questions_de_regles


def fournisseur(reglages=REGLAGES, **create):
    client = MagicMock()
    client.messages.create.configure_mock(**create)
    return FournisseurAnthropic(reglages, client), client


def test_requete_un_document_par_passage_avec_citations():
    f, _ = fournisseur()
    requete = construire_requete(f.parametres(), CONSIGNES_REGLES, PASSAGES, "Comment dévie une grenade ?")
    contenu = requete["messages"][0]["content"]
    documents = [b for b in contenu if b["type"] == "document"]
    assert [d["title"] for d in documents] == [p.reference() for p in PASSAGES]
    assert [d["source"]["data"] for d in documents] == [p.texte for p in PASSAGES]
    assert all(d["citations"] == {"enabled": True} for d in documents)
    assert contenu[-1] == {"type": "text", "text": "Comment dévie une grenade ?"}
    assert requete["system"] == CONSIGNES_REGLES


def test_parametres_de_la_configuration():
    f, _ = fournisseur()
    assert f.parametres() == {"model": "claude-test-regles", "max_tokens": 2000, "thinking": {"type": "adaptive"}}


def test_niveau_de_reflexion():
    f, _ = fournisseur(REGLAGES.model_copy(update={"niveau_de_reflexion": "bas"}))
    assert f.parametres()["output_config"] == {"effort": "low"}


def test_reponse_sourcee_depuis_les_citations_natives(message_factice):
    message = message_factice([
        "La grenade ",
        ("dévie", [(0, "dévient selon le diagramme de dispersion")]),
        (" et explose", [(1, "explose à la fin du tour")]),
    ])
    f, client = fournisseur(return_value=message)
    reponse = f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")
    assert reponse.texte == "La grenade dévie et explose"
    assert [s.passage for s in reponse.sources] == [GRENADE, GABARIT]
    assert client.messages.create.call_args.kwargs["system"] == CONSIGNES_REGLES


def test_lire_reponse_ignore_la_reflexion(message_factice):
    assert lire_reponse(message_factice(["ok"]), PASSAGES).texte == "ok"


@pytest.mark.parametrize(("stop_reason", "attendu"), [("refusal", "refusé"), ("max_tokens", "tronquée")])
def test_reponse_incomplete(message_factice, stop_reason, attendu):
    f, _ = fournisseur(return_value=message_factice(["x"], stop_reason=stop_reason))
    with pytest.raises(ReponseIncomplete, match=attendu):
        f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")


def test_sans_identifiants():
    f, _ = fournisseur(side_effect=TypeError("Could not resolve authentication method."))
    with pytest.raises(IdentifiantsAbsents, match="ANTHROPIC_API_KEY"):
        f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")


def test_autre_typeerror_non_masquee():
    f, _ = fournisseur(side_effect=TypeError("autre chose"))
    with pytest.raises(TypeError, match="autre chose"):
        f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")


def _erreur_http(classe, statut, message):
    requete = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return classe(message, response=httpx2.Response(statut, request=requete), body=None)


def test_cle_refusee():
    f, _ = fournisseur(side_effect=_erreur_http(anthropic.AuthenticationError, 401, "invalid x-api-key"))
    with pytest.raises(IdentifiantsAbsents, match="refusés"):
        f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")


def test_erreur_api_convertie():
    f, _ = fournisseur(side_effect=_erreur_http(anthropic.NotFoundError, 404, "model: claude-x"))
    with pytest.raises(ErreurFournisseur, match="API Anthropic : model: claude-x"):
        f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")


@pytest.mark.parametrize(("cle", "attendu"), [("sk-ant-fichier", {"api_key": "sk-ant-fichier"}), (None, {})])
def test_cle_api_transmise_au_sdk(monkeypatch, message_factice, cle, attendu):
    recus = []
    client = MagicMock()
    client.messages.create.return_value = message_factice(["ok"])

    def faux_anthropic(**kw):
        recus.append(kw)
        return client

    monkeypatch.setattr(anthropic, "Anthropic", faux_anthropic)
    f = creer_fournisseur(REGLAGES, cle_api=cle)
    f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")
    f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")
    assert recus == [attendu]  # sans clé : le SDK lit ANTHROPIC_API_KEY ; client créé une fois
