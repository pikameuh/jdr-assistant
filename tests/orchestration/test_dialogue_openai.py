"""Couche 3 : moteur de dialogue et commandes avec le fournisseur OpenAI, client mocké."""

import builtins
import json
import pathlib
from unittest.mock import MagicMock

import openai
import pytest

from agent_jdr.core import rules_index
from agent_jdr.core.config import charger_config
from agent_jdr.core.dialogue_engine import OUTIL_REGLES, MoteurDialogue
from agent_jdr.core.fournisseurs.base import ReponseIncomplete
from agent_jdr.core.fournisseurs.fournisseur_openai import FournisseurOpenAI
from agent_jdr.core.persona import charger_persona
from agent_jdr.core.prompt_builder import Tour
from agent_jdr.core.rules_index import Passage, RulesIndex, construire_index
from agent_jdr.core.scene import Scene
from agent_jdr.interfaces import cli
from tests.openai_factice import appel, message, raisonnement, reponse
from tests.reglages_test import CONFIG_TEST, CONSIGNES_DIALOGUE, ecrire_config

REGLAGES = CONFIG_TEST.dialogue.model_copy(update={"fournisseur": "openai", "modele": "gpt-test-dialogue"})
ORLA = charger_persona(charger_config().fichiers.dossier_des_pnj / "orla-venn.yaml")
SCENE = Scene(lieu="Dock 7", moment="Nuit", pnj_presents=("orla-venn",), pj_presents=("Kael",))
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


def moteur(index, *reponses):
    client = MagicMock()
    client.responses.create.side_effect = list(reponses)
    return MoteurDialogue(ORLA, SCENE, index, REGLAGES, FournisseurOpenAI(REGLAGES, client)), client


def appels(client):
    return [c.kwargs for c in client.responses.create.call_args_list]


def test_replique_simple_et_parametres(index):
    m, client = moteur(index, reponse(message("Crédits ou promesses, capitaine ?")))
    replique = m.repondre("Une pile ?", pj="Kael")

    assert replique.texte == "Crédits ou promesses, capitaine ?"
    (params,) = appels(client)
    assert params["model"] == "gpt-test-dialogue"
    assert params["max_output_tokens"] == 1000
    assert "reasoning" not in params
    assert params["instructions"].startswith(CONSIGNES_DIALOGUE + "\n\n")
    stable, scene = params["instructions"].split("\n\n# Scène en cours\n")
    assert "Orla Venn" in stable and "Dock 7" in scene
    assert params["tools"] == [
        {
            "type": "function",
            "name": "rechercher_regle",
            "description": OUTIL_REGLES.description,
            "parameters": OUTIL_REGLES.schema,
            "strict": True,
        }
    ]
    assert params["input"] == [{"role": "user", "content": "[Kael] Une pile ?"}]
    assert m.historique[-1] == Tour("pnj", "Crédits ou promesses, capitaine ?")


def test_historique_au_tour_suivant(index):
    m, client = moteur(index, reponse(message("Bonsoir.")), reponse(message("400 crédits.")))
    m.repondre("Bonsoir.", pj="Kael")
    m.repondre("Combien ?", pj="Kael")
    assert appels(client)[1]["input"] == [
        {"role": "user", "content": "[Kael] Bonsoir."},
        {"role": "assistant", "content": "Bonsoir."},
        {"role": "user", "content": "[Kael] Combien ?"},
    ]


def test_boucle_outils_renvoie_raisonnement_et_resultats(index):
    premiere = reponse(raisonnement(), appel("call_1", json.dumps({"requete": "pile énergétique"})))
    m, client = moteur(index, premiere, reponse(message("Ça coûte cher, capitaine.")))
    replique = m.repondre("Combien pour une pile ?")

    assert replique.texte == "Ça coûte cher, capitaine."
    assert replique.regles_consultees == (PLEIN,)
    entree = appels(client)[1]["input"]
    # Entrée initiale, puis tous les éléments renvoyés (raisonnement compris), puis le résultat.
    assert entree[1:3] == premiere.output
    sortie = entree[3]
    assert sortie["type"] == "function_call_output" and sortie["call_id"] == "call_1"
    assert sortie["output"].startswith("Manuel des joueurs, p. 196 — Faire le plein\n")


def test_arguments_illisibles_signales_au_modele(index):
    m, client = moteur(index, reponse(appel("call_1", "{pas du json")), reponse(message("ok")))
    m.repondre("?")
    assert appels(client)[1]["input"][-1]["output"].startswith("Erreur : ")


def test_trop_de_recherches(index):
    demandes = [reponse(appel(f"c{i}", '{"requete": "pile"}')) for i in range(REGLAGES.recherches_max_par_replique + 1)]
    m, _ = moteur(index, *demandes)
    with pytest.raises(ReponseIncomplete, match="Trop de recherches"):
        m.repondre("?")
    assert m.historique == []


def test_reponse_tronquee_historique_inchange(index):
    m, _ = moteur(index, reponse(status="incomplete", raison="max_output_tokens"))
    with pytest.raises(ReponseIncomplete, match="tronquée"):
        m.repondre("?")
    assert m.historique == []


# --- Commandes, avec une configuration qui choisit OpenAI ---------------------------------------


def config_openai(tmp_path, dialogue=True, regles=True, secrets=None):
    openai_ = {"fournisseur": "openai", "modele": "gpt-6.1-sol"}
    sections = {}
    if dialogue:
        sections["dialogue"] = openai_
    if regles:
        sections["questions_de_regles"] = openai_
    return ecrire_config(tmp_path, secrets, **sections)


def test_cli_parler_avec_openai(monkeypatch, tmp_path, chemin_db, capsys):
    client = MagicMock()
    client.responses.create.side_effect = [reponse(message("Bonsoir, capitaine."))]
    monkeypatch.setattr(openai, "OpenAI", lambda: client)
    lignes = iter(["Bonsoir."])

    def faux_input(invite):
        try:
            return next(lignes)
        except StopIteration:
            raise EOFError from None  # Ctrl+D

    monkeypatch.setattr(builtins, "input", faux_input)
    code = cli.main(["orla-venn", "--lieu", "a", "--moment", "b", "--pj", "K",
                     "--db", str(chemin_db), "--config", str(config_openai(tmp_path))])
    assert code == 0
    sortie = capsys.readouterr().out
    assert "(openai, modèle : gpt-6.1-sol)" in sortie
    assert "Orla Venn > Bonsoir, capitaine." in sortie
    assert appels(client)[0]["model"] == "gpt-6.1-sol"


def test_cli_search_avec_openai(monkeypatch, tmp_path, chemin_db, capsys):
    texte = json.dumps({"segments": [{"texte": "Ça coûte cher.", "citations": [{"passage": 1, "extrait": "coûte cher"}]}]})
    client = MagicMock()
    client.responses.create.return_value = reponse(message(texte))
    monkeypatch.setattr(openai, "OpenAI", lambda: client)
    code = rules_index.main(["search", "pile", "--db", str(chemin_db), "--config", str(config_openai(tmp_path))])
    assert code == 0
    assert capsys.readouterr().out == (
        "Ça coûte cher. [1]\n\nSources\n[1] Manuel des joueurs, p. 196 — Faire le plein\n    « coûte cher »\n"
    )


def test_cli_sans_cle_openai(monkeypatch, tmp_path, chemin_db, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_ADMIN_KEY", raising=False)
    code = rules_index.main(["search", "pile", "--db", str(chemin_db), "--config", str(config_openai(tmp_path))])
    assert code == 1
    erreur = capsys.readouterr().err
    assert erreur.startswith(
        "Erreur : Aucune clé OpenAI trouvée : clé absente du fichier de secrets "
        "et variable OPENAI_API_KEY non définie."
    )
    assert "« recherche-apikey »" in erreur
    assert "Traceback" not in erreur


def test_cli_cles_openai_par_usage(monkeypatch, tmp_path, chemin_db, capsys):
    cles = []
    client = MagicMock()
    client.responses.create.side_effect = [reponse(message("Bonsoir, capitaine."))]

    def faux_openai(**kw):
        cles.append(kw.get("api_key"))
        return client

    monkeypatch.setattr(openai, "OpenAI", faux_openai)
    entrees = iter(["Bonsoir.", "/quitter"])
    monkeypatch.setattr(builtins, "input", lambda invite: next(entrees))
    config = config_openai(tmp_path, secrets={"recherche-apikey": "sk-regles", "personas-apikey": "sk-pnj"})
    code = cli.main(["orla-venn", "--lieu", "a", "--moment", "b", "--pj", "K",
                     "--db", str(chemin_db), "--config", str(config)])
    assert code == 0
    assert cles == ["sk-pnj"]


# --- Isolation : seuls les modules fournisseur_* importent un SDK ---------------------------------


def test_seuls_les_fournisseurs_importent_un_sdk():
    racine = pathlib.Path(cli.__file__).parents[1]
    for fichier in racine.rglob("*.py"):
        if fichier.name.startswith("fournisseur_"):
            continue
        code = fichier.read_text(encoding="utf-8")
        for sdk in ("anthropic", "openai"):
            assert f"import {sdk}" not in code and f"from {sdk}" not in code, (fichier, sdk)
