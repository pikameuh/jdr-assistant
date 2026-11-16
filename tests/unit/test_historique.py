"""Couche 1 : historique des questions de règles (un fichier JSON par recherche)."""

import pytest

from agent_jdr.core.historique import Historique, RechercheInconnue

REPONSE = {
    "segments": [{"texte": "La grenade dévie de 1D6 mètres.", "sources": [1]}],
    "sources": [{"reference": "Manuel des joueurs, p. 174 — Dispersion", "extraits": [], "texte": "…"}],
}
PASSAGES = {"passages": [{"reference": "Manuel des joueurs, p. 196 — Faire le plein", "texte": "…", "score": -3.2}]}


@pytest.fixture
def historique(tmp_path):
    return Historique(tmp_path / "historique")


def test_ajouter_lire_lister(historique):
    a = historique.ajouter("  Dispersion d'une grenade ? ", "reponse", REPONSE)
    b = historique.ajouter("Faire le plein", "passages", PASSAGES)
    assert a.question == "Dispersion d'une grenade ?"
    assert historique.lire(a.id) == a
    assert [r.id for r in historique.lister()] == [b.id, a.id]  # la plus récente d'abord


@pytest.mark.parametrize(
    "filtre, attendu",
    [
        ("GRENADE", ["grenade"]),  # majuscules ignorées
        ("devie", ["grenade"]),  # accents ignorés, texte de la réponse
        ("p. 196", ["plein"]),  # référence d'un passage
        ("grenade plein", []),  # tous les mots doivent apparaître
        ("", ["plein", "grenade"]),
    ],
)
def test_rechercher(historique, filtre, attendu):
    historique.ajouter("Dispersion d'une grenade", "reponse", REPONSE)
    historique.ajouter("Faire le plein", "passages", PASSAGES)
    trouves = [r.question.split()[-1] for r in historique.lister(filtre)]
    assert trouves == attendu


def test_supprimer_et_vider(historique):
    a = historique.ajouter("a", "reponse", REPONSE)
    historique.ajouter("b", "reponse", REPONSE)
    historique.supprimer(a.id)
    with pytest.raises(RechercheInconnue):
        historique.lire(a.id)
    with pytest.raises(RechercheInconnue):
        historique.supprimer(a.id)
    assert historique.vider() == 1
    assert historique.lister() == []


def test_dossier_absent_et_fichier_abime(historique):
    assert historique.lister() == [] and historique.vider() == 0
    historique.ajouter("a", "reponse", REPONSE)
    (historique.dossier / ("0" * 32 + ".json")).write_text("pas du json", encoding="utf-8")
    assert [r.question for r in historique.lister()] == ["a"]


@pytest.mark.parametrize("id_recherche", ["../config", "abc", "0" * 31 + "g"])
def test_identifiant_incorrect(historique, id_recherche):
    with pytest.raises(RechercheInconnue):
        historique.lire(id_recherche)
