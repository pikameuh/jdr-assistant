import pytest

from agent_jdr.core.persona import DOSSIER_PERSONAS, charger_persona
from agent_jdr.core.prompt_builder import CONSIGNES, Tour, construire_prompt
from agent_jdr.core.scene import Scene

ORLA = charger_persona(DOSSIER_PERSONAS / "orla-venn.yaml")
SCENE = Scene(
    lieu="Dock 7",
    moment="Cycle de nuit",
    pnj_presents=("orla-venn",),
    pj_presents=("Kael",),
    faits_etablis=("Kael a payé d'avance",),
)
HISTORIQUE = [
    Tour("joueur", "Une pile, s'il vous plaît.", pj="Kael"),
    Tour("pnj", "Crédits ou promesses, capitaine ?"),
    Tour("joueur", "Crédits."),
]


def test_partie_stable_puis_scene():
    stable, variable = construire_prompt(ORLA, SCENE, HISTORIQUE)["system"]
    assert stable["text"].startswith(CONSIGNES)
    assert "Orla Venn" in stable["text"] and "Dock 7" not in stable["text"]
    assert "Dock 7" in variable["text"] and "Kael a payé d'avance" in variable["text"]


def test_partie_stable_identique_quelle_que_soit_la_scene():
    autre = SCENE.avec_fait("Une alarme retentit")
    a = construire_prompt(ORLA, SCENE, HISTORIQUE)["system"][0]
    b = construire_prompt(ORLA, autre, HISTORIQUE)["system"][0]
    assert a == b


def test_tous_les_champs_de_la_fiche_sont_rendus():
    texte = construire_prompt(ORLA, SCENE, HISTORIQUE)["system"][0]["text"]
    for valeur in (
        ORLA.espece, ORLA.origine, ORLA.role, ORLA.parole.registre,
        *ORLA.parole.tics, *ORLA.parole.exemples, *ORLA.objectifs,
        *ORLA.connaissances, ORLA.attitude_envers_pj,
    ):
        assert valeur.strip() in texte


def test_secrets_avec_leur_condition():
    texte = construire_prompt(ORLA, SCENE, HISTORIQUE)["system"][0]["text"]
    for s in ORLA.secrets:
        assert s.contenu in texte
        assert f"(révélation : {s.condition_revelation or 'jamais'})" in texte


def test_historique_converti_en_messages():
    messages = construire_prompt(ORLA, SCENE, HISTORIQUE)["messages"]
    assert messages == [
        {"role": "user", "content": "[Kael] Une pile, s'il vous plaît."},
        {"role": "assistant", "content": "Crédits ou promesses, capitaine ?"},
        {"role": "user", "content": "Crédits."},
    ]


def test_pnj_absent_de_la_scene():
    with pytest.raises(ValueError, match="pas présent"):
        construire_prompt(ORLA, SCENE.model_copy(update={"pnj_presents": ()}), HISTORIQUE)


@pytest.mark.parametrize(
    "historique",
    [[], [Tour("joueur", "Bonjour"), Tour("pnj", "Salut")]],
)
def test_historique_doit_finir_par_le_joueur(historique):
    with pytest.raises(ValueError, match="se terminer"):
        construire_prompt(ORLA, SCENE, historique)


def test_historique_doit_commencer_par_le_joueur():
    with pytest.raises(ValueError, match="commencer"):
        construire_prompt(ORLA, SCENE, [Tour("pnj", "Salut"), Tour("joueur", "Bonjour")])
