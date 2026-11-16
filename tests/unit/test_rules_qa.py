"""Couche 1 : assemblage des sources et rendu texte, indépendants du fournisseur."""

import pytest

from agent_jdr.core.rules_index import Passage
from agent_jdr.core.rules_qa import assembler_reponse, formater_reponse

GRENADE = Passage(
    "Manuel des joueurs", 174, 174, "Le combat à distance", "Le combat à distance",
    "Dispersion et aire d’effet", "Les grenades dévient selon le diagramme de dispersion.",
)
GABARIT = Passage(
    "Manuel des joueurs", 237, 237, "La technologie courante", "", "",
    "Une grenade explose à la fin du tour où elle a été lancée.",
)
PASSAGES = [GRENADE, GABARIT]


def test_sources_dedoublonnees_par_passage():
    reponse = assembler_reponse(
        [
            ("La grenade ", []),
            ("dévie selon le diagramme", [(0, "dévient selon le diagramme de dispersion")]),
            (" et explose en fin de tour", [(1, "explose à la fin du tour"), (0, "dévient selon le diagramme de dispersion")]),
            (".", []),
        ],
        PASSAGES,
    )
    assert reponse.texte == "La grenade dévie selon le diagramme et explose en fin de tour."
    assert [s.passage for s in reponse.sources] == [GRENADE, GABARIT]
    assert reponse.sources[0].extraits == ("dévient selon le diagramme de dispersion",)
    assert [seg.sources for seg in reponse.segments] == [(), (1,), (2, 1), ()]


def test_passage_non_cite_absent_des_sources():
    reponse = assembler_reponse([("Elle explose.", [(1, "explose à la fin du tour")])], PASSAGES)
    assert [s.passage for s in reponse.sources] == [GABARIT]


def test_citation_hors_bornes_refusee():
    with pytest.raises(ValueError):
        assembler_reponse([("x", [(5, "y")])], PASSAGES)


def test_formatage_renvois_et_section_sources():
    reponse = assembler_reponse(
        [
            ("La grenade dévie.", [(0, "dévient selon le\ndiagramme")]),
            (" Elle explose en fin de tour.", [(1, "explose à la fin du tour")]),
        ],
        PASSAGES,
    )
    assert formater_reponse(reponse) == (
        "La grenade dévie. [1] Elle explose en fin de tour. [2]\n"
        "\n"
        "Sources\n"
        "[1] Manuel des joueurs, p. 174 — Le combat à distance > Dispersion et aire d’effet\n"
        "    « dévient selon le diagramme »\n"
        "[2] Manuel des joueurs, p. 237\n"
        "    « explose à la fin du tour »"
    )


def test_formatage_sans_citation_pas_de_section_sources():
    reponse = assembler_reponse([("Les passages ne couvrent pas ce point.", [])], PASSAGES)
    assert formater_reponse(reponse) == "Les passages ne couvrent pas ce point."


def test_formatage_signale_les_extraits_ecartes():
    reponse = assembler_reponse([("Elle explose.", [(1, "explose à la fin du tour")])], PASSAGES, 2)
    assert formater_reponse(reponse).endswith(
        "\n\n(2 extrait(s) cité(s) par le modèle introuvable(s) mot pour mot dans les passages : "
        "écarté(s) des sources.)"
    )
