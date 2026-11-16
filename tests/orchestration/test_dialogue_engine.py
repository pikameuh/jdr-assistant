"""Couche 3 : moteur de dialogue et CLI `parler`, client Anthropic mocké."""

import builtins
from unittest.mock import MagicMock

import anthropic
import pytest
from anthropic.types import Message, TextBlock, ThinkingBlock, ToolUseBlock, Usage

from agent_jdr.core import dialogue_engine
from agent_jdr.core.config import charger_config
from agent_jdr.core.dialogue_engine import AUCUN_PASSAGE, OUTIL_REGLES, MoteurDialogue
from agent_jdr.core.fournisseurs.fournisseur_anthropic import FournisseurAnthropic
from agent_jdr.core.persona import charger_persona
from agent_jdr.core.prompt_builder import Tour
from agent_jdr.core.rules_index import Passage, RulesIndex, construire_index
from agent_jdr.core.fournisseurs.base import IdentifiantsAbsents, ReponseIncomplete
from agent_jdr.core.scene import Scene
from agent_jdr.interfaces import cli
from tests.reglages_test import CONFIG_TEST, CONSIGNES_DIALOGUE, ecrire_config

REGLAGES = CONFIG_TEST.dialogue
MAX_TOURS_OUTILS = REGLAGES.recherches_max_par_replique

ORLA = charger_persona(charger_config().fichiers.dossier_des_pnj / "orla-venn.yaml")
SCENE = Scene(lieu="Dock 7", moment="Cycle de nuit", pnj_presents=("orla-venn",), pj_presents=("Kael",))
PLEIN = Passage("Manuel des joueurs", 196, 196, "Voyage", "Faire le plein", "", "Une pile énergétique coûte cher.")


@pytest.fixture
def chemin_db(tmp_path):
    chemin = tmp_path / "rules.db"
    construire_index([PLEIN], chemin)
    return chemin


@pytest.fixture
def index(chemin_db):
    with RulesIndex(chemin_db) as idx:
        yield idx


def texte(t, stop_reason="end_turn"):
    return _message([TextBlock(type="text", text=t)], stop_reason)


def outil(*appels, name="rechercher_regle"):
    blocs = [
        ToolUseBlock(type="tool_use", id=f"toolu_{i}", name=name, input=entree)
        for i, entree in enumerate(appels)
    ]
    return _message(blocs, "tool_use")


def _message(blocs, stop_reason):
    return Message(
        id="msg_test",
        type="message",
        role="assistant",
        model="claude-opus-4-8",
        content=[ThinkingBlock(type="thinking", thinking="", signature="sig"), *blocs],
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=Usage(input_tokens=1, output_tokens=1),
    )


def moteur(index, *reponses):
    client = MagicMock()
    client.messages.create.side_effect = list(reponses)
    return MoteurDialogue(ORLA, SCENE, index, REGLAGES, FournisseurAnthropic(REGLAGES, client)), client


def appels(client):
    return [c.kwargs for c in client.messages.create.call_args_list]


# --- Paramètres d'appel ------------------------------------------------------------


def test_replique_simple_et_parametres(index):
    m, client = moteur(index, texte("Crédits ou promesses, capitaine ?"))
    replique = m.repondre("Une pile ?", pj="Kael")

    assert replique.texte == "Crédits ou promesses, capitaine ?"
    assert replique.regles_consultees == ()
    (params,) = appels(client)
    assert params["model"] == "claude-test-dialogue"
    assert params["max_tokens"] == 1000
    assert params["thinking"] == {"type": "adaptive"}
    assert "output_config" not in params  # niveau de réflexion « defaut »
    assert params["tools"] == [
        {
            "name": "rechercher_regle",
            "description": OUTIL_REGLES.description,
            "input_schema": OUTIL_REGLES.schema,
            "strict": True,
        }
    ]
    assert params["cache_control"] == {"type": "ephemeral"}
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in params["system"][1]
    assert params["system"][0]["text"].startswith(CONSIGNES_DIALOGUE + "\n\n")
    assert "Orla Venn" in params["system"][0]["text"]
    assert params["messages"] == [{"role": "user", "content": "[Kael] Une pile ?"}]
    assert m.historique == [
        Tour("joueur", "Une pile ?", pj="Kael"),
        Tour("pnj", "Crédits ou promesses, capitaine ?"),
    ]


def test_historique_renvoye_au_tour_suivant(index):
    m, client = moteur(index, texte("Bonsoir."), texte("400 crédits."))
    m.repondre("Bonsoir.", pj="Kael")
    m.repondre("Combien ?", pj="Kael")
    assert appels(client)[1]["messages"] == [
        {"role": "user", "content": "[Kael] Bonsoir."},
        {"role": "assistant", "content": "Bonsoir."},
        {"role": "user", "content": "[Kael] Combien ?"},
    ]


def test_fait_ajoute_change_la_scene_pas_la_partie_stable(index):
    m, client = moteur(index, texte("a"), texte("b"))
    m.repondre("Un.")
    m.scene = m.scene.avec_fait("Une alarme retentit")
    m.repondre("Deux.")
    premier, second = appels(client)
    assert premier["system"][0] == second["system"][0]
    assert "Une alarme retentit" in second["system"][1]["text"]
    assert "Une alarme retentit" not in premier["system"][1]["text"]


# --- Boucle tool use -----------------------------------------------------------------


def test_recherche_de_regle_puis_replique(index):
    demande = outil({"requete": "pile énergétique"})
    m, client = moteur(index, demande, texte("Ça coûte cher, capitaine."))
    replique = m.repondre("Combien pour une pile ?")

    assert replique.texte == "Ça coûte cher, capitaine."
    assert replique.regles_consultees == (PLEIN,)
    second = appels(client)[1]["messages"]
    assert second[1] == {"role": "assistant", "content": demande.content}  # réflexion comprise
    (resultat,) = second[2]["content"]
    assert resultat["type"] == "tool_result" and resultat["tool_use_id"] == "toolu_0"
    assert resultat["content"][0]["text"].startswith("Manuel des joueurs, p. 196 — Faire le plein\n")
    assert "is_error" not in resultat
    # L'historique ne garde que la réplique finale.
    assert m.historique[-1] == Tour("pnj", "Ça coûte cher, capitaine.")


def test_appels_paralleles_resultats_dans_un_seul_message(index):
    m, client = moteur(index, outil({"requete": "pile"}, {"requete": "xylophone"}), texte("ok"))
    m.repondre("?")
    resultats = appels(client)[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in resultats] == ["toolu_0", "toolu_1"]
    assert resultats[1]["content"] == [{"type": "text", "text": AUCUN_PASSAGE}]


@pytest.mark.parametrize("entree", [{}, {"requete": "  "}, {"requete": 3}])
def test_entree_invalide_signalee_au_modele(index, entree):
    m, client = moteur(index, outil(entree), texte("ok"))
    m.repondre("?")
    (resultat,) = appels(client)[1]["messages"][-1]["content"]
    assert resultat["is_error"] is True


def test_outil_inconnu_signale_au_modele(index):
    m, client = moteur(index, outil({"x": 1}, name="autre"), texte("ok"))
    m.repondre("?")
    (resultat,) = appels(client)[1]["messages"][-1]["content"]
    assert resultat["is_error"] is True and "autre" in resultat["content"][0]["text"]


def test_trop_de_recherches(index):
    demandes = [outil({"requete": "pile"}) for _ in range(MAX_TOURS_OUTILS + 1)]
    m, client = moteur(index, *demandes)
    with pytest.raises(ReponseIncomplete, match="Trop de recherches"):
        m.repondre("?")
    assert client.messages.create.call_count == MAX_TOURS_OUTILS + 1
    assert m.historique == []


# --- Erreurs : l'historique reste inchangé ----------------------------------------------


@pytest.mark.parametrize(
    ("reponse", "attendu"),
    [
        (texte("", "refusal"), "refusé"),
        (texte("coupé", "max_tokens"), "tronquée"),
        (_message([], "end_turn"), "aucune réplique"),
    ],
)
def test_reponse_incomplete(index, reponse, attendu):
    m, _ = moteur(index, reponse)
    with pytest.raises(ReponseIncomplete, match=attendu):
        m.repondre("?")
    assert m.historique == []


def test_identifiants_absents(index):
    m, client = moteur(index)
    client.messages.create.side_effect = TypeError("Could not resolve authentication method.")
    with pytest.raises(IdentifiantsAbsents):
        m.repondre("?")
    assert m.historique == []


def test_replique_vide_refusee(index):
    m, client = moteur(index)
    with pytest.raises(ValueError):
        m.repondre("   ")
    client.messages.create.assert_not_called()


def test_pnj_absent_de_la_scene(index):
    m, client = moteur(index)
    m.scene = m.scene.model_copy(update={"pnj_presents": ()})
    with pytest.raises(ValueError, match="pas présent"):
        m.repondre("?")
    client.messages.create.assert_not_called()


# --- CLI ---------------------------------------------------------------------------


def lancer_cli(monkeypatch, chemin_db, lignes, *reponses, persona="orla-venn"):
    client = MagicMock()
    client.messages.create.side_effect = list(reponses)
    monkeypatch.setattr(anthropic, "Anthropic", lambda: client)
    entrees = iter(lignes)
    config = ecrire_config(chemin_db.parent)

    def faux_input(invite):
        try:
            return next(entrees)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr(builtins, "input", faux_input)
    code = cli.main(
        [persona, "--lieu", "Dock 7", "--moment", "Nuit", "--pj", "Kael", "--db", str(chemin_db),
         "--config", str(config)]
    )
    return code, client


def test_cli_conversation(monkeypatch, chemin_db, capsys):
    code, client = lancer_cli(
        monkeypatch,
        chemin_db,
        ["/fait Kael a payé un verre", "Une pile ?", "/quitter", "jamais lu"],
        outil({"requete": "pile énergétique"}),
        texte("Ça coûte cher, capitaine."),
    )
    assert code == 0
    sortie = capsys.readouterr().out
    assert "(fait ajouté : Kael a payé un verre)" in sortie
    assert "Orla Venn > Ça coûte cher, capitaine." in sortie
    assert "(règles consultées : Manuel des joueurs, p. 196 — Faire le plein)" in sortie
    premier = appels(client)[0]
    assert "Kael a payé un verre" in premier["system"][1]["text"]
    assert premier["messages"] == [{"role": "user", "content": "[Kael] Une pile ?"}]


def test_cli_erreur_de_reponse_puis_reprise(monkeypatch, chemin_db, capsys):
    code, client = lancer_cli(
        monkeypatch, chemin_db, ["Un ?", "Deux ?"], texte("", "refusal"), texte("Réponse.")
    )
    assert code == 0
    capture = capsys.readouterr()
    assert "tour non enregistré" in capture.err
    assert "Orla Venn > Réponse." in capture.out
    # Le tour refusé n'est pas dans l'historique du second appel.
    assert appels(client)[1]["messages"] == [{"role": "user", "content": "[Kael] Deux ?"}]


def test_cli_sans_identifiants(monkeypatch, chemin_db, capsys):
    client = MagicMock()
    client.messages.create.side_effect = TypeError("Could not resolve authentication method.")
    monkeypatch.setattr(anthropic, "Anthropic", lambda: client)
    monkeypatch.setattr(builtins, "input", lambda invite: "Bonjour")
    config = ecrire_config(chemin_db.parent)
    code = cli.main(["orla-venn", "--lieu", "a", "--moment", "b", "--pj", "K", "--db", str(chemin_db),
                     "--config", str(config)])
    assert code == 1
    erreur = capsys.readouterr().err
    assert erreur.startswith("Erreur : Aucun identifiant Anthropic trouvé")
    assert f"Renseignez la clé « personas-apikey » dans {chemin_db.parent / 'secrets.yaml'}" in erreur


def test_cli_parler_utilise_la_cle_personas(monkeypatch, chemin_db, capsys):
    cles = []
    client = MagicMock()
    client.messages.create.return_value = texte("Bonsoir.")

    def faux_anthropic(**kw):
        cles.append(kw.get("api_key"))
        return client

    monkeypatch.setattr(anthropic, "Anthropic", faux_anthropic)
    entrees = iter(["Bonsoir ?", "/quitter"])
    monkeypatch.setattr(builtins, "input", lambda invite: next(entrees))
    config = ecrire_config(
        chemin_db.parent, {"recherche-apikey": "sk-ant-regles", "personas-apikey": " sk-ant-pnj "}
    )
    code = cli.main(["orla-venn", "--lieu", "a", "--moment", "b", "--pj", "K", "--db", str(chemin_db),
                     "--config", str(config)])
    assert code == 0
    assert cles == ["sk-ant-pnj"]
    assert "sk-ant" not in capsys.readouterr().out


def test_cli_fichier_de_secrets_incorrect(monkeypatch, chemin_db, capsys):
    config = ecrire_config(chemin_db.parent, {"personas-api-key": "sk-ant-x"})
    code = cli.main(["orla-venn", "--lieu", "a", "--moment", "b", "--pj", "K", "--config", str(config)])
    assert code == 1
    erreur = capsys.readouterr().err
    assert "secrets.yaml : réglages incorrects" in erreur
    assert "personas-api-key : réglage inconnu (faute de frappe ?)" in erreur
    assert "sk-ant-x" not in erreur


def test_cli_pnj_inconnu(monkeypatch, chemin_db, capsys):
    code, _ = lancer_cli(monkeypatch, chemin_db, [], persona="inconnu")
    assert code == 1
    assert "Disponibles : orla-venn" in capsys.readouterr().err


def test_cli_index_absent(monkeypatch, tmp_path, capsys):
    code, _ = lancer_cli(monkeypatch, tmp_path / "absent.db", [])
    assert code == 1
    assert "Index des règles absent" in capsys.readouterr().err


def test_le_coeur_ne_depend_pas_des_interfaces():
    import pathlib

    racine = pathlib.Path(dialogue_engine.__file__).parent
    for fichier in racine.rglob("*.py"):
        assert "agent_jdr.interfaces" not in fichier.read_text(encoding="utf-8"), fichier


# --- Réglages de la configuration ----------------------------------------------------


def test_niveau_de_reflexion_transmis(index):
    client = MagicMock()
    client.messages.create.side_effect = [texte("ok")]
    reglages = REGLAGES.model_copy(update={"niveau_de_reflexion": "eleve"})
    MoteurDialogue(ORLA, SCENE, index, reglages, FournisseurAnthropic(reglages, client)).repondre("?")
    assert appels(client)[0]["output_config"] == {"effort": "high"}


def test_passages_par_recherche_transmis():
    faux_index = MagicMock()
    faux_index.rechercher.return_value = []
    client = MagicMock()
    client.messages.create.side_effect = [outil({"requete": "pile"}), texte("ok")]
    m = MoteurDialogue(ORLA, SCENE, faux_index, REGLAGES, FournisseurAnthropic(REGLAGES, client))
    m.repondre("?")
    faux_index.rechercher.assert_called_once_with("pile", REGLAGES.passages_par_recherche)


def test_cli_affiche_le_modele_de_la_config(monkeypatch, chemin_db, capsys):
    lancer_cli(monkeypatch, chemin_db, [])
    reglages = charger_config().dialogue
    assert f"({reglages.fournisseur}, modèle : {reglages.modele})" in capsys.readouterr().out


@pytest.mark.parametrize("commande", ["parler", "search"])
def test_cli_config_invalide(tmp_path, capsys, commande):
    from agent_jdr.core import rules_index

    mauvaise = tmp_path / "config.yaml"
    mauvaise.write_text("dialogue: {}\n", encoding="utf-8")
    if commande == "parler":
        code = cli.main(["orla-venn", "--lieu", "a", "--moment", "b", "--pj", "K", "--config", str(mauvaise)])
    else:
        code = rules_index.main(["search", "q", "--config", str(mauvaise)])
    assert code == 1
    erreur = capsys.readouterr().err
    assert "configuration" in erreur and "dialogue > modele" in erreur
    assert "Traceback" not in erreur
