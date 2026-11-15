"""Couche 3 : orchestration recherche → appel API → réponse, client Anthropic mocké."""

from unittest.mock import MagicMock

import anthropic
import pytest

from agent_jdr.core import rules_index, rules_qa
from agent_jdr.core.rules_index import Passage, RulesIndex, construire_index
from tests.reglages_test import CONFIG_TEST

REGLAGES = CONFIG_TEST.questions_de_regles


def passage(texte, section, page):
    return Passage("Manuel des joueurs", page, page, "Combat", section, "", texte)


@pytest.fixture
def chemin_db(tmp_path):
    chemin = tmp_path / "rules.db"
    construire_index(
        [
            passage("Une grenade dévie selon le diagramme de dispersion.", "Dispersion", 174),
            passage("Le vaisseau consomme du carburant.", "Faire le plein", 196),
        ],
        chemin,
    )
    return chemin


@pytest.fixture
def index(chemin_db):
    with RulesIndex(chemin_db) as idx:
        yield idx


def client_mock(message):
    client = MagicMock()
    client.messages.create.return_value = message
    return client


def test_passages_recuperes_envoyes_au_modele(index, message_factice):
    client = client_mock(message_factice(["ok"]))
    reponse = rules_qa.repondre("dispersion d'une grenade", index, REGLAGES, client=client)

    client.messages.create.assert_called_once()
    kwargs = client.messages.create.call_args.kwargs
    documents = [b for b in kwargs["messages"][0]["content"] if b["type"] == "document"]
    assert [d["title"] for d in documents] == [p.reference() for p in reponse.passages_fournis]
    assert documents[0]["title"] == "Manuel des joueurs, p. 174 — Dispersion"
    assert kwargs["model"] == "claude-test-regles"


def test_citation_reliee_au_bon_passage(index, message_factice):
    # Deux passages trouvés ; le modèle ne cite que le second document envoyé.
    question = "grenade dispersion carburant"
    envoyes = [r.passage for r in index.rechercher(question, 8)]
    assert len(envoyes) == 2
    client = client_mock(message_factice([("Ça consomme.", [(1, envoyes[1].texte)])]))

    reponse = rules_qa.repondre(question, index, REGLAGES, client=client)
    assert [s.passage for s in reponse.sources] == [envoyes[1]]
    assert reponse.sources[0].extraits == (envoyes[1].texte,)


def test_aucun_passage_pas_d_appel(index):
    client = MagicMock()
    reponse = rules_qa.repondre("xylophone", index, REGLAGES, client=client)
    client.messages.create.assert_not_called()
    assert reponse.texte == rules_qa.MESSAGE_AUCUN_PASSAGE
    assert reponse.sources == ()


def test_limite_transmise_a_la_recherche(index, message_factice):
    client = client_mock(message_factice(["ok"]))
    reponse = rules_qa.repondre("grenade dispersion carburant", index, REGLAGES, client=client, limite=1)
    assert len(reponse.passages_fournis) == 1


def test_identifiants_absents_message_clair(index):
    client = MagicMock()
    client.messages.create.side_effect = TypeError(
        "Could not resolve authentication method. Expected one of api_key, auth_token, ..."
    )
    with pytest.raises(rules_qa.IdentifiantsAbsents, match="ANTHROPIC_API_KEY"):
        rules_qa.repondre("grenade", index, REGLAGES, client=client)


def test_autre_typeerror_non_masquee(index):
    client = MagicMock()
    client.messages.create.side_effect = TypeError("autre chose")
    with pytest.raises(TypeError, match="autre chose"):
        rules_qa.repondre("grenade", index, REGLAGES, client=client)


# --- CLI --------------------------------------------------------------------------


def test_cli_brut_sans_appel_llm(chemin_db, capsys, monkeypatch):
    monkeypatch.setattr(anthropic, "Anthropic", MagicMock(side_effect=AssertionError("appel LLM")))
    assert rules_index.main(["search", "grenade", "--brut", "--db", str(chemin_db)]) == 0
    sortie = capsys.readouterr().out
    assert "Manuel des joueurs, p. 174 — Dispersion" in sortie


def test_cli_affiche_reponse_et_sources(chemin_db, capsys, monkeypatch, message_factice):
    message = message_factice([("Elle dévie.", [(0, "dévie selon le diagramme")])])
    monkeypatch.setattr(anthropic, "Anthropic", lambda: client_mock(message))
    assert rules_index.main(["search", "grenade", "--db", str(chemin_db)]) == 0
    sortie = capsys.readouterr().out
    assert sortie.startswith("Elle dévie. [1]")
    assert "Sources\n[1] Manuel des joueurs, p. 174 — Dispersion\n    « dévie selon le diagramme »" in sortie


def test_cli_sans_identifiants_pas_de_trace(chemin_db, capsys, monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HOME", str(chemin_db.parent))  # aucun profil `ant` sur disque
    monkeypatch.setenv("XDG_CONFIG_HOME", str(chemin_db.parent))
    assert rules_index.main(["search", "grenade", "--db", str(chemin_db)]) == 1
    erreur = capsys.readouterr().err
    assert erreur.startswith("Erreur : Aucun identifiant Anthropic trouvé")
    assert "Traceback" not in erreur
