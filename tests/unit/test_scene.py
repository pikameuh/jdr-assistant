import pytest
from pydantic import ValidationError

from agent_jdr.core.scene import Scene


def scene():
    return Scene(
        lieu="Dock 7",
        moment="Cycle de nuit",
        ambiance="Néons qui grésillent",
        pnj_presents=("orla-venn",),
        pj_presents=("Kael",),
        enjeux="Obtenir une pile avant le départ",
        faits_etablis=("Kael a payé un verre à Orla",),
    )


def test_aller_retour_json():
    s = scene()
    assert Scene.depuis_json(s.vers_json()) == s


def test_avec_fait_ne_modifie_pas_l_original():
    s = scene()
    s2 = s.avec_fait("  Orla a baissé son prix  ")
    assert s.faits_etablis == ("Kael a payé un verre à Orla",)
    assert s2.faits_etablis[-1] == "Orla a baissé son prix"


def test_fait_vide_refuse():
    with pytest.raises(ValueError):
        scene().avec_fait("   ")


def test_scene_immuable():
    with pytest.raises(ValidationError):
        scene().lieu = "Ailleurs"


def test_lieu_obligatoire():
    with pytest.raises(ValidationError):
        Scene(lieu="", moment="Nuit")


def test_champ_inconnu_refuse():
    with pytest.raises(ValidationError):
        Scene.depuis_json('{"lieu": "a", "moment": "b", "meteo": "pluie"}')
