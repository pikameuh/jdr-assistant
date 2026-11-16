"""Couche 1 : sessions de dialogue persistantes (sans LLM)."""

import pytest

from agent_jdr.core.config import charger_config
from agent_jdr.core.persona import charger_persona
from agent_jdr.core.scene import Scene
from agent_jdr.core.sessions import (
    DepotSessions,
    SessionDialogue,
    SessionInconnue,
    TourEnregistre,
    nouvelle_session,
)

ORLA = charger_persona(charger_config().fichiers.dossier_des_pnj / "orla-venn.yaml")
SCENE = Scene(lieu="Dock 7", moment="Cycle de nuit", pnj_presents=("orla-venn",), pj_presents=("Kael",))


def session_avec_historique() -> SessionDialogue:
    s = nouvelle_session(ORLA, " Kael ", SCENE)
    return s.model_copy(update={"historique": (
        TourEnregistre(locuteur="joueur", texte="Bonsoir.", pj="Kael"),
        TourEnregistre(locuteur="pnj", texte="*lève les yeux* Quoi ?", regles=("Manuel des joueurs, p. 196",)),
    )})


def test_nouvelle_session():
    s = nouvelle_session(ORLA, " Kael ", SCENE)
    assert (s.persona, s.pj, s.historique) == ("orla-venn", "Kael", ())
    assert len(s.id) == 32 and s.cree_le == s.modifie_le


def test_tours_pour_le_moteur():
    tours = session_avec_historique().tours()
    assert [(t.locuteur, t.texte, t.pj) for t in tours] == [
        ("joueur", "Bonsoir.", "Kael"), ("pnj", "*lève les yeux* Quoi ?", None)
    ]


def test_sans_historique_garde_scene_et_faits():
    s = session_avec_historique().avec_fait("Kael a payé")
    vide = s.sans_historique()
    assert vide.historique == ()
    assert (vide.id, vide.persona, vide.pj, vide.scene) == (s.id, s.persona, s.pj, s.scene)
    assert vide.scene.faits_etablis == ("Kael a payé",)
    assert vide.modifie_le >= s.modifie_le


def test_fait_vide_refuse():
    with pytest.raises(ValueError, match="vide"):
        session_avec_historique().avec_fait("  ")


def test_depot_aller_retour(tmp_path):
    depot = DepotSessions(tmp_path / "sessions")
    assert depot.lister() == []
    s = session_avec_historique()
    depot.enregistrer(s)
    assert depot.lire(s.id) == s
    assert depot.lister() == [s]
    depot.supprimer(s.id)
    assert depot.lister() == []
    with pytest.raises(SessionInconnue):
        depot.lire(s.id)
    with pytest.raises(SessionInconnue):
        depot.supprimer(s.id)


def test_depot_liste_la_plus_recente_d_abord(tmp_path):
    depot = DepotSessions(tmp_path)
    ancienne = nouvelle_session(ORLA, "Kael", SCENE)
    recente = nouvelle_session(ORLA, "Mira", SCENE).avec_fait("plus récent")
    depot.enregistrer(ancienne)
    depot.enregistrer(recente)
    assert [s.pj for s in depot.lister()] == ["Mira", "Kael"]


@pytest.mark.parametrize("id_session", ["../config", "x" * 32, "", "A" * 32])
def test_depot_refuse_les_identifiants_douteux(tmp_path, id_session):
    with pytest.raises(SessionInconnue):
        DepotSessions(tmp_path).lire(id_session)


def test_depot_ignore_les_fichiers_illisibles(tmp_path):
    depot = DepotSessions(tmp_path)
    (tmp_path / ("0" * 32 + ".json")).write_text("{pas du json", encoding="utf-8")
    s = nouvelle_session(ORLA, "Kael", SCENE)
    depot.enregistrer(s)
    assert depot.lister() == [s]
