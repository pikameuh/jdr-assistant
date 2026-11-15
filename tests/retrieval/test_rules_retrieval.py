"""Couche 2 : requête → passage attendu, sur l'index construit depuis les vrais PDF.

Les pages attendues sont établies indépendamment de l'extracteur (sortie de
`pdftotext` et sommaire imprimé des livres). Ignoré si les PDF sont absents.
"""

import re

import pytest

from agent_jdr.core.config import charger_config
from agent_jdr.core.rules_index import RulesIndex, construire_index

pytestmark = pytest.mark.retrieval

MJ, GDM = "Manuel des joueurs", "Guide du Meneur"
TOP = 3


@pytest.fixture(scope="module")
def passages():
    dossier = charger_config().fichiers.dossier_des_pdf
    if not dossier.is_dir():
        pytest.skip(f"PDF de règles absents ({dossier})")
    from agent_jdr.core.rules_extract import extraire_regles

    return extraire_regles(dossier)


@pytest.fixture(scope="module")
def index(passages, tmp_path_factory):
    chemin = tmp_path_factory.mktemp("index") / "rules.db"
    construire_index(passages, chemin)
    with RulesIndex(chemin) as idx:
        yield idx


@pytest.mark.parametrize(
    ("requete", "livre", "page"),
    [
        ("comment fonctionne Scotty special de l'ingénieur", MJ, 60),
        ("difficulté d'un test", MJ, 45),
        ("test d'initiative", MJ, 44),
        ("niveaux technologiques", MJ, 118),
        ("rafistoler la coque", MJ, 131),
        ("la battlegrid", MJ, 152),
        ("tir localisé sur un vaisseau, coup critique", MJ, 168),
        ("faire le plein du vaisseau", MJ, 196),
        ("actions sociales : donner une consigne", MJ, 225),
        ("planète de classe M ou géante gazeuse", GDM, 39),
        ("comment provoquer un retour de flamme en dépensant des dés MF", GDM, 93),
        ("créer un PNJ", GDM, 114),
        ("apparence et caractère de Stella Bell", GDM, 126),
    ],
)
def test_requete_trouve_le_passage_attendu(index, requete, livre, page):
    resultats = index.rechercher(requete, limite=TOP)
    trouves = [r.passage.reference() for r in resultats]
    assert any(
        r.passage.livre == livre and r.passage.page <= page <= r.passage.page_fin for r in resultats
    ), f"{livre} p. {page} absent du top {TOP} : {trouves}"


def test_dispersion_grenade_en_tete(index):
    """Question de référence de la phase 0.2 : la règle de dispersion doit arriver en premier."""
    premier = index.rechercher("expliques moi la dispersion d'une grenade")[0].passage
    assert (premier.livre, premier.page, premier.sous_section) == (
        MJ, 174, "Dispersion et aire d’effet"
    ), premier.reference()


def test_deux_livres_indexes(passages):
    livres = {p.livre for p in passages}
    assert livres == {MJ, GDM}


def test_aucune_donnee_personnelle_ni_reference_de_commande(passages):
    texte = "\n".join(p.texte for p in passages)
    assert "15101" not in texte
    # Filigrane nominatif de la page 1 : « Metal Adventures - <acheteur> - ref ».
    assert not re.search(r"Metal Adventures\s+-\s+[^\n]+-\s+ref", texte)


def test_pages_liminaires_exclues(passages):
    assert min(p.page for p in passages) == 4
    assert not any(re.search(r"\.{10,} p\. \d+", p.texte) for p in passages), "sommaire indexé"


def test_taille_des_passages(passages):
    assert max(len(p.texte) for p in passages) <= 1500
    assert all(p.page <= p.page_fin for p in passages)


def test_cesures_et_mots_composes(passages):
    texte = "\n".join(p.texte for p in passages)
    assert "celui-ci" in texte
    assert "celuici" not in texte
    assert "fonctionnement" in texte
    # Pas de double passe : « Scotty special » apparaît une seule fois dans sa section.
    scotty = [p for p in passages if "Scotty special" in p.texte and p.page == 60]
    assert len(scotty) == 1 and scotty[0].texte.count("Scotty special") == 1
