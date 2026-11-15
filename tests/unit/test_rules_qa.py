"""Couche 1 : construction de la requête et rendu des sources, sans LLM."""

import pytest

from agent_jdr.core.rules_index import Passage
from agent_jdr.core.rules_qa import (
    CONSIGNE_SYSTEME,
    MODELE,
    ReponseIncomplete,
    formater_reponse,
    lire_reponse,
    construire_requete,
)

GRENADE = Passage(
    "Manuel des joueurs", 174, 174, "Le combat à distance", "Le combat à distance",
    "Dispersion et aire d’effet", "Les grenades dévient selon le diagramme de dispersion.",
)
GABARIT = Passage(
    "Manuel des joueurs", 237, 237, "La technologie courante", "", "",
    "Une grenade explose à la fin du tour où elle a été lancée.",
)
PASSAGES = [GRENADE, GABARIT]


def test_requete_un_document_par_passage_avec_citations():
    requete = construire_requete("Comment dévie une grenade ?", PASSAGES)
    contenu = requete["messages"][0]["content"]
    documents = [b for b in contenu if b["type"] == "document"]
    assert [d["title"] for d in documents] == [p.reference() for p in PASSAGES]
    assert [d["source"]["data"] for d in documents] == [p.texte for p in PASSAGES]
    assert all(d["citations"] == {"enabled": True} for d in documents)
    assert all(d["source"]["type"] == "text" for d in documents)
    # La question vient après les documents.
    assert contenu[-1] == {"type": "text", "text": "Comment dévie une grenade ?"}


def test_requete_modele_reflexion_et_consigne():
    requete = construire_requete("q", PASSAGES)
    assert requete["model"] == MODELE == "claude-opus-4-8"
    assert requete["thinking"] == {"type": "adaptive"}
    assert requete["system"] == CONSIGNE_SYSTEME
    assert "français" in CONSIGNE_SYSTEME
    assert "uniquement sur les documents fournis" in CONSIGNE_SYSTEME
    assert "dis-le explicitement" in CONSIGNE_SYSTEME


def test_sources_issues_des_citations_dedoublonnees_par_passage(message_factice):
    message = message_factice([
        "La grenade ",
        ("dévie selon le diagramme", [(0, "dévient selon le diagramme de dispersion")]),
        (" et explose en fin de tour", [(1, "explose à la fin du tour"), (0, "dévient selon le diagramme de dispersion")]),
        ".",
    ])
    reponse = lire_reponse(message, PASSAGES)
    assert reponse.texte == "La grenade dévie selon le diagramme et explose en fin de tour."
    assert [s.passage for s in reponse.sources] == [GRENADE, GABARIT]
    assert reponse.sources[0].extraits == ("dévient selon le diagramme de dispersion",)
    assert [seg.sources for seg in reponse.segments] == [(), (1,), (2, 1), ()]


def test_passage_non_cite_absent_des_sources(message_factice):
    message = message_factice([("Elle explose.", [(1, "explose à la fin du tour")])])
    reponse = lire_reponse(message, PASSAGES)
    assert [s.passage for s in reponse.sources] == [GABARIT]


def test_citation_hors_bornes_refusee(message_factice):
    with pytest.raises(ValueError):
        lire_reponse(message_factice([("x", [(5, "y")])]), PASSAGES)


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_reponse_incomplete_signalee(message_factice, stop_reason):
    with pytest.raises(ReponseIncomplete):
        lire_reponse(message_factice(["x"], stop_reason=stop_reason), PASSAGES)


def test_formatage_renvois_et_section_sources(message_factice):
    message = message_factice([
        ("La grenade dévie.", [(0, "dévient selon le\ndiagramme")]),
        (" Elle explose en fin de tour.", [(1, "explose à la fin du tour")]),
    ])
    texte = formater_reponse(lire_reponse(message, PASSAGES))
    assert texte == (
        "La grenade dévie. [1] Elle explose en fin de tour. [2]\n"
        "\n"
        "Sources\n"
        "[1] Manuel des joueurs, p. 174 — Le combat à distance > Dispersion et aire d’effet\n"
        "    « dévient selon le diagramme »\n"
        "[2] Manuel des joueurs, p. 237\n"
        "    « explose à la fin du tour »"
    )


def test_formatage_sans_citation_pas_de_section_sources(message_factice):
    texte = formater_reponse(lire_reponse(message_factice(["Les passages ne couvrent pas ce point."]), PASSAGES))
    assert texte == "Les passages ne couvrent pas ce point."
