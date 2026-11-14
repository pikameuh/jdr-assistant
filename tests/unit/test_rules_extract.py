"""Nettoyage et découpage du texte extrait des PDF (sans PDF, déterministe)."""

from collections import Counter

import pytest

from agent_jdr.core.rules_extract import (
    CORPS,
    EN_TETE,
    IGNORE,
    NUMERO,
    SOUS_TITRE,
    TITRE,
    Span,
    classer_ligne,
    decouper,
    est_residu,
    joindre_lignes,
    prolonge,
    texte_ligne,
    vocabulaire,
)

CHEVRON = Span(">>", "VariexOT-Regular", 20.0)
PUCE = Span(">>", "VariexOT-Bold", 9.5)


@pytest.mark.parametrize(
    ("spans", "role"),
    [
        ([Span("Les niveaux technologiques", "BalboaPlus-Fill", 12.0)], SOUS_TITRE),
        ([CHEVRON, Span(" Les niveaux technologiques", "BalboaPlus-Fill", 12.0)], SOUS_TITRE),
        ([Span("La technologie du Dernier Millénaire", "BalboaPlus-Fill", 14.0)], TITRE),
        ([Span("La légende", "MascotMVB-Rough1", 25.0)], TITRE),
        ([Span("Metal Technology >>", "BalboaPlus-Fill", 13.5)], EN_TETE),
        ([Span("118 ", "BalboaPlus-Fill", 18.0)], NUMERO),
        ([Span("Vous êtes capable de faire des miracles", "Starling-Book", 9.5)], CORPS),
        ([Span("Disponibilité : B", "BerlinSans-Roman", 9.0)], CORPS),
        ([Span("Ref. 15101", "Helvetica-Bold", 10.0)], IGNORE),
        ([Span("Metal Adventures - Nom Prénom - ref", "Helvetica", 15.0)], IGNORE),
        ([Span("C’est bon, on peut y aller !", "ViktorScript-Regular", 26.0)], IGNORE),
        ([Span("Stella Bell était une guerrière", "BalboaPlus-Fill", 11.0)], IGNORE),
        ([Span("Metal Technology", "BalboaPlus-Fill", 28.0)], IGNORE),
        ([CHEVRON], IGNORE),
    ],
)
def test_classer_ligne(spans, role):
    assert classer_ligne(spans) == role


def test_texte_ligne_puce_et_normalisation():
    spans = [PUCE, Span("  Âge de Métal\xa0: diﬀérent, scientiﬁque ", "Starling-Book", 9.5)]
    assert texte_ligne(spans) == "• Âge de Métal : différent, scientifique ❑"


def test_texte_ligne_retire_chevron_final_de_l_en_tete():
    assert texte_ligne([Span("Les compétences\xa0>>", "BalboaPlus-Fill", 13.5)]) == "Les compétences"


@pytest.mark.parametrize("texte", ["t", "u d t", "o s", "❑❑❑❑", "(", "  "])
def test_est_residu_vrai(texte):
    assert est_residu(texte)


@pytest.mark.parametrize("texte", ["B", "L :", "5 m", "M ? :", "à la", "= 25 K", "Durée : 1 heure"])
def test_est_residu_faux(texte):
    assert not est_residu(texte)


def test_joindre_lignes_recolle_les_cesures():
    vocab = Counter({"fonctionnement": 3})
    lignes = ["le vaisseau reste en fonction-", "nement normal."]
    assert joindre_lignes(lignes, vocab) == "le vaisseau reste en fonctionnement normal."


def test_joindre_lignes_garde_le_trait_d_union_des_mots_composes():
    vocab = Counter({"celui-ci": 12})
    lignes = ["La maintenance de celui-", "ci constitue sa charge."]
    assert joindre_lignes(lignes, vocab) == "La maintenance de celui-ci constitue sa charge."


def test_joindre_lignes_sans_cesure_insere_un_espace():
    assert joindre_lignes(["Au combat,", "il s’assure"], Counter()) == "Au combat, il s’assure"


def test_joindre_lignes_ne_recolle_pas_devant_une_majuscule():
    assert joindre_lignes(["Âge Stellaire-", "Dernier"], Counter()) == "Âge Stellaire- Dernier"


def test_vocabulaire_ignore_les_mots_de_bord_de_ligne():
    vocab = vocabulaire([["début celui-ci milieu fonc-"]])
    assert vocab == Counter({"celui-ci": 1, "milieu": 1})


@pytest.mark.parametrize(
    ("precedente", "suivante", "attendu"),
    [
        ("• Ligue des Planètes libres : les pirates y sont officielle-", "ment des criminels", True),
        ("de la Ligue des Planètes", "libres, très particulière.", True),
        ("standardiser…", "Les historiens et les scientifiques", False),
        ("au plus haut :", "• Âge de Métal", False),
    ],
)
def test_prolonge(precedente, suivante, attendu):
    assert prolonge(precedente, suivante) is attendu


def test_decouper_texte_court_inchange():
    assert decouper("Une phrase. Une autre.", taille_max=100) == ["Une phrase. Une autre."]


def test_decouper_coupe_aux_fins_de_phrase():
    phrases = [f"Phrase numéro {i} assez longue pour compter." for i in range(10)]
    morceaux = decouper(" ".join(phrases), taille_max=100)
    assert all(len(m) <= 100 for m in morceaux)
    assert " ".join(morceaux) == " ".join(phrases)
    assert all(m.endswith(".") for m in morceaux)


def test_decouper_garde_entiere_une_phrase_trop_longue():
    phrase = "Mot " * 50 + "fin."
    assert decouper(phrase, taille_max=20) == [phrase]
