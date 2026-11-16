"""Construction et requête de l'index FTS5 sur des passages synthétiques."""

import pytest

from agent_jdr.core.rules_index import (
    Passage,
    RulesIndex,
    construire_index,
    nom_du_livre,
    requete_fts,
)


def passage(texte, section="", sous_section="", livre="Manuel des joueurs", page=10, page_fin=None):
    return Passage(livre, page, page_fin or page, "Chapitre", section, sous_section, texte)


@pytest.fixture
def index(tmp_path):
    passages = [
        passage("Le test d’initiative se résout au début du combat.", "Combat", "Initiative", page=44),
        passage("Le vaisseau consomme du carburant.", "Voyages", "Faire le plein", page=196),
        passage("Une règle sur les vaisseaux et le plein de carburant.", "Divers", page=12),
        passage("Les PNJ ont une personnalité.", "Création de PNJ", livre="Guide du Meneur", page=114),
    ]
    chemin = tmp_path / "rules.db"
    assert construire_index(passages, chemin) == 4
    with RulesIndex(chemin) as idx:
        yield idx


def test_requete_fts_retire_mots_vides_et_pluriels():
    assert requete_fts("Comment faire le plein des vaisseaux ?") == '"plein"* OR "vaisseau"*'


def test_requete_fts_sans_terme_utile():
    assert requete_fts("comment le faire ?") is None
    assert requete_fts("") is None


def test_requete_fts_neutralise_la_syntaxe_fts():
    # Guillemets, opérateurs et parenthèses ne doivent pas casser la requête.
    assert requete_fts('initiative" OR (NEAR') == '"initiative"* OR "or"* OR "near"*'


def test_recherche_insensible_aux_accents(index):
    resultats = index.rechercher("resout initiative")
    assert resultats[0].passage.page == 44


def test_recherche_privilegie_le_titre_de_section(index):
    resultats = index.rechercher("faire le plein du vaisseau")
    assert [r.passage.page for r in resultats][:2] == [196, 12]


def test_recherche_respecte_la_limite(index):
    assert len(index.rechercher("vaisseau plein carburant", limite=1)) == 1


def test_recherche_vide(index):
    assert index.rechercher("le la les") == []


def test_nombre_passages(index):
    assert index.nombre_passages() == 4


def test_index_absent(tmp_path):
    with pytest.raises(FileNotFoundError, match="rules_index build"):
        RulesIndex(tmp_path / "absent.db")


def test_reconstruction_remplace_l_index(tmp_path):
    chemin = tmp_path / "rules.db"
    construire_index([passage("ancien")], chemin)
    construire_index([passage("nouveau"), passage("autre")], chemin)
    with RulesIndex(chemin) as idx:
        assert idx.nombre_passages() == 2
        assert idx.rechercher("ancien") == []
    assert not (tmp_path / "rules.db.tmp").exists()


@pytest.mark.parametrize(
    ("p", "attendu"),
    [
        (passage("x", "L’Ingénieur", "Scotty special", page=60), "Manuel des joueurs, p. 60 — L’Ingénieur > Scotty special"),
        (passage("x", "Création de PNJ", page=114, page_fin=115), "Manuel des joueurs, p. 114-115 — Création de PNJ"),
        (passage("x", page=4), "Manuel des joueurs, p. 4"),
    ],
)
def test_reference(p, attendu):
    assert p.reference() == attendu


def test_raccourci_search_transmet_les_arguments(monkeypatch):
    from agent_jdr.core import rules_index

    recus = []
    monkeypatch.setattr(rules_index, "main", lambda argv: recus.append(argv) or 0)
    monkeypatch.setattr("sys.argv", ["search", "faire le plein", "--brut", "-n", "3"])
    assert rules_index.search_cli() == 0
    assert recus == [["search", "faire le plein", "--brut", "-n", "3"]]


# --- Filtre par livre (livres cochés) ----------------------------------------------------


def test_filtre_par_livre(tmp_path):
    chemin = tmp_path / "rules.db"
    construire_index([
        passage("Le carburant coûte cher.", "Voyages", page=196),
        passage("Le carburant des PNJ.", "PNJ", livre="Guide du Meneur", page=114),
    ], chemin)
    def livres(filtre):
        with RulesIndex(chemin, filtre) as idx:
            return sorted(r.passage.livre for r in idx.rechercher("carburant"))
    assert livres(None) == ["Guide du Meneur", "Manuel des joueurs"]
    assert livres(["Guide du Meneur"]) == ["Guide du Meneur"]
    assert livres([]) == []
    with RulesIndex(chemin, []) as idx:
        assert idx.passages_par_livre() == {"Guide du Meneur": 1, "Manuel des joueurs": 1}  # sans filtre


def test_nom_du_livre():
    assert nom_du_livre("MA - Guide du Meneur 1.5.pdf") == "Guide du Meneur"
    assert nom_du_livre("Écran du meneur.pdf") == "Écran du meneur"
