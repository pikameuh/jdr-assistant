"""Couche 1 : création d'une fiche PNJ depuis un formulaire (interface web)."""

import pytest

from agent_jdr.core.config import charger_config
from agent_jdr.core.persona import (
    FicheRefusee,
    PersonaInconnu,
    charger_modele_de_fiche,
    charger_persona,
    creer_fiche,
    modifier_fiche,
    valider_fiche,
)

FICHE = {
    "id": "capitaine-rook", "nom": "Capitaine Rook", "espece": "Humain", "origine": "La flotte",
    "role": "Contrebandier", "personnalite": "Charmeur.", "attitude_envers_pj": "Méfiant.",
    "parole": {"registre": "Soutenu", "tics": ["", " Dit « affirmatif ». "], "exemples": []},
    "objectifs": ["Trouver un équipage", ""], "connaissances": [],
    "secrets": [{"contenu": "Déserteur", "condition_revelation": None}, {"contenu": "", "condition_revelation": ""}],
}


def test_formulaire_nettoye_et_valide():
    p = valider_fiche(FICHE)
    assert p.parole.tics == ("Dit « affirmatif ».",)
    assert p.objectifs == ("Trouver un équipage",)
    assert [s.contenu for s in p.secrets] == ["Déserteur"]


def test_creer_puis_relire(tmp_path):
    p = creer_fiche(tmp_path, FICHE)
    chemin = tmp_path / "capitaine-rook.yaml"
    assert charger_persona(chemin) == p
    texte = chemin.read_text(encoding="utf-8")
    assert "Capitaine Rook" in texte and "condition_revelation" not in texte  # pas de « null » inutile


def test_ne_jamais_ecraser(tmp_path):
    creer_fiche(tmp_path, FICHE)
    avant = (tmp_path / "capitaine-rook.yaml").read_text(encoding="utf-8")
    with pytest.raises(FicheRefusee) as e:
        creer_fiche(tmp_path, {**FICHE, "nom": "Autre"})
    assert "existe déjà" in e.value.erreurs["id"]
    assert (tmp_path / "capitaine-rook.yaml").read_text(encoding="utf-8") == avant


def test_erreurs_par_champ_en_francais():
    fiche = {**FICHE, "id": "Capitaine Rook", "role": "  ", "objectifs": [""], "parole": {"registre": ""}}
    with pytest.raises(FicheRefusee) as e:
        valider_fiche(fiche)
    assert e.value.erreurs == {
        "id": "minuscules sans accents, chiffres et tirets entre les mots (ex. capitaine-rook)",
        "role": "à remplir",
        "parole.registre": "à remplir",
        "objectifs": "à remplir",
    }
    assert "Façon" not in str(e.value) and "Parole > Registre : à remplir" in str(e.value)


def test_objectifs_vide_et_secret_sans_contenu():
    with pytest.raises(FicheRefusee) as e:
        valider_fiche({**FICHE, "secrets": [{"contenu": "", "condition_revelation": "Si payé"}]})
    assert e.value.erreurs == {"secrets.0.contenu": "à remplir (ou supprimez ce secret)"}


def test_champ_inconnu_refuse():
    with pytest.raises(FicheRefusee) as e:
        valider_fiche({**FICHE, "pv": 12})
    assert e.value.erreurs == {"pv": "champ inconnu"}


def test_modele_du_projet_devient_une_fiche_valide():
    modele = charger_modele_de_fiche(charger_config().fichiers.modele_de_pnj)
    assert "id" not in modele  # l'identifiant est déduit du nom par le formulaire
    assert valider_fiche({**modele, "id": "capitaine-rook"}).nom == modele["nom"]


# --- Modification d'une fiche ----------------------------------------------------------


def test_modifier_puis_relire(tmp_path):
    creer_fiche(tmp_path, FICHE)
    p = modifier_fiche(tmp_path, "capitaine-rook", {**FICHE, "nom": "Amiral Rook", "objectifs": ["Rentrer chez lui"]})
    relue = charger_persona(tmp_path / "capitaine-rook.yaml")
    assert relue == p and relue.nom == "Amiral Rook" and relue.objectifs == ("Rentrer chez lui",)
    assert (tmp_path / "capitaine-rook.yaml").read_text(encoding="utf-8").startswith("# Fiche PNJ modifiée")
    assert sorted(f.name for f in tmp_path.iterdir()) == ["capitaine-rook.yaml"]  # pas de fichier temporaire laissé


def test_modifier_sans_identifiant_garde_celui_du_fichier(tmp_path):
    creer_fiche(tmp_path, FICHE)
    assert modifier_fiche(tmp_path, "capitaine-rook", {**FICHE, "id": ""}).id == "capitaine-rook"


def test_modifier_identifiant_refuse(tmp_path):
    creer_fiche(tmp_path, FICHE)
    avant = (tmp_path / "capitaine-rook.yaml").read_text(encoding="utf-8")
    with pytest.raises(FicheRefusee) as e:
        modifier_fiche(tmp_path, "capitaine-rook", {**FICHE, "id": "autre-id"})
    assert "ne peut pas changer" in e.value.erreurs["id"]
    assert (tmp_path / "capitaine-rook.yaml").read_text(encoding="utf-8") == avant


def test_modifier_fiche_invalide_n_ecrit_rien(tmp_path):
    creer_fiche(tmp_path, FICHE)
    avant = (tmp_path / "capitaine-rook.yaml").read_text(encoding="utf-8")
    with pytest.raises(FicheRefusee) as e:
        modifier_fiche(tmp_path, "capitaine-rook", {**FICHE, "role": "  "})
    assert e.value.erreurs == {"role": "à remplir"}
    assert (tmp_path / "capitaine-rook.yaml").read_text(encoding="utf-8") == avant


@pytest.mark.parametrize("id_persona", ["inconnu", "../capitaine-rook", "Capitaine"])
def test_modifier_pnj_inconnu(tmp_path, id_persona):
    creer_fiche(tmp_path, FICHE)
    with pytest.raises(PersonaInconnu):
        modifier_fiche(tmp_path, id_persona, FICHE)
