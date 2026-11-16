"""Couche 1 : livres de règles (ajout d'un PDF, état, reconstruction de l'index)."""

import io

import pytest

from agent_jdr.core.livres import (
    ErreurIndexation,
    LivreRefuse,
    ajouter_pdf,
    etat_livres,
    reconstruire_index,
)
from agent_jdr.core.rules_index import Passage, RulesIndex, construire_index
from tests.pdf_factice import ecrire_pdf
from tests.reglages_test import ecrire_config

PDF = b"%PDF-1.7\n contenu factice"


def test_ajouter_pdf(tmp_path):
    chemin = ajouter_pdf(tmp_path / "livres", "Écran du meneur (v2).pdf", io.BytesIO(PDF))
    assert chemin.read_bytes() == PDF
    assert sorted(p.name for p in chemin.parent.iterdir()) == ["Écran du meneur (v2).pdf"]  # pas de fichier temporaire


@pytest.mark.parametrize("nom", ["../evil.pdf", "sous/livre.pdf", "livre.txt", "livre #2.pdf", ".cache.pdf", "a" * 150 + ".pdf"])
def test_nom_refuse(tmp_path, nom):
    with pytest.raises(LivreRefuse, match="Nom de fichier refusé"):
        ajouter_pdf(tmp_path, nom, io.BytesIO(PDF))
    assert list(tmp_path.iterdir()) == []


def test_pas_un_pdf(tmp_path):
    with pytest.raises(LivreRefuse, match="n'est pas un fichier PDF"):
        ajouter_pdf(tmp_path, "faux.pdf", io.BytesIO(b"<html>"))
    assert list(tmp_path.iterdir()) == []


def test_trop_gros(tmp_path):
    with pytest.raises(LivreRefuse, match="taille maximale"):
        ajouter_pdf(tmp_path, "gros.pdf", io.BytesIO(PDF + b"x" * 100), taille_max=50)
    assert list(tmp_path.iterdir()) == []


def test_jamais_d_ecrasement(tmp_path):
    (tmp_path / "livre.pdf").write_bytes(b"original")
    with pytest.raises(LivreRefuse, match="existe déjà"):
        ajouter_pdf(tmp_path, "livre.pdf", io.BytesIO(PDF))
    assert (tmp_path / "livre.pdf").read_bytes() == b"original"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["livre.pdf"]


def test_etat_livres(tmp_path):
    (tmp_path / "MA - Guide du Meneur 1.5.pdf").write_bytes(PDF)
    (tmp_path / "Nouveau.PDF").write_bytes(PDF)
    (tmp_path / "notes.txt").write_text("ignoré")
    db = tmp_path / "rules.db"
    construire_index([Passage("Guide du Meneur", 1, 1, "", "", "", "texte")] * 3, db)
    etat = {l.fichier: l for l in etat_livres(tmp_path, db, ("MA - Guide du Meneur 1.5.pdf", "Disparu.pdf"))}
    assert sorted(etat) == ["Disparu.pdf", "MA - Guide du Meneur 1.5.pdf", "Nouveau.PDF"]
    guide = etat["MA - Guide du Meneur 1.5.pdf"]
    assert (guide.livre, guide.passages, guide.utilise, guide.present, guide.taille) == ("Guide du Meneur", 3, True, True, len(PDF))
    assert (etat["Nouveau.PDF"].passages, etat["Nouveau.PDF"].utilise) == (None, False)  # non indexé, non coché
    assert (etat["Disparu.pdf"].present, etat["Disparu.pdf"].utilise) == (False, True)


def test_etat_sans_index(tmp_path):
    (tmp_path / "a.pdf").write_bytes(PDF)
    assert etat_livres(tmp_path, tmp_path / "absent.db", ())[0].passages is None


# --- Reconstruction (processus séparé, PDF réels générés) ---------------------------------


def config_livres(tmp_path):
    dossier = tmp_path / "livres"
    dossier.mkdir()
    db = tmp_path / "rules.db"
    return ecrire_config(tmp_path, fichiers={"dossier_des_pdf": str(dossier), "index_des_regles": str(db)}), dossier, db


def test_reconstruire_index(tmp_path):
    config, dossier, db = config_livres(tmp_path)
    ecrire_pdf(dossier / "Écran.pdf", ["Le carburant se paie au quai."])
    assert "1 passages indexés" in reconstruire_index(config)
    with RulesIndex(db) as idx:
        assert idx.passages_par_livre() == {"Écran": 1}


def test_reconstruire_pdf_abime_message_lisible_et_index_conserve(tmp_path):
    config, dossier, db = config_livres(tmp_path)
    construire_index([Passage("Ancien", 1, 1, "", "", "", "texte")], db)
    (dossier / "abime.pdf").write_bytes(b"%PDF-1.7 tronque")
    with pytest.raises(ErreurIndexation, match="PDF illisible : abime.pdf"):
        reconstruire_index(config)
    with RulesIndex(db) as idx:
        assert idx.passages_par_livre() == {"Ancien": 1}


def test_reconstruire_dossier_vide(tmp_path):
    config, _, _ = config_livres(tmp_path)
    with pytest.raises(ErreurIndexation, match="aucun PDF lisible"):
        reconstruire_index(config)
