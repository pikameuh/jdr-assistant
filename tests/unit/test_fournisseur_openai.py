"""Couche 1 : traduction vers l'API OpenAI Responses (requête, sources vérifiées, erreurs), sans réseau."""

import json
from unittest.mock import MagicMock

import httpx2
import openai
import pytest

from agent_jdr.core.fournisseurs import creer_fournisseur
from agent_jdr.core.fournisseurs.base import ErreurFournisseur, IdentifiantsAbsents, ReponseIncomplete
from agent_jdr.core.fournisseurs.fournisseur_openai import (
    CONSIGNE_FORMAT,
    SCHEMA_REPONSE,
    FournisseurOpenAI,
    construire_requete,
    lire_reponse,
)
from tests.openai_factice import message, refus, reponse
from tests.reglages_test import CONFIG_TEST, CONSIGNES_REGLES
from tests.unit.test_rules_qa import GABARIT, GRENADE, PASSAGES

REGLAGES = CONFIG_TEST.questions_de_regles.model_copy(
    update={"fournisseur": "openai", "modele": "gpt-test-regles"}
)


def fournisseur(reglages=REGLAGES, **create):
    client = MagicMock()
    client.responses.create.configure_mock(**create)
    return FournisseurOpenAI(reglages, client), client


def json_reponse(*segments):
    return json.dumps(
        {"segments": [{"texte": t, "citations": [{"passage": p, "extrait": e} for p, e in c]} for t, c in segments]}
    )


# --- Requête ------------------------------------------------------------------------


def test_fabrique_choisit_openai():
    assert isinstance(creer_fournisseur(REGLAGES, MagicMock()), FournisseurOpenAI)


def test_parametres():
    f, _ = fournisseur()
    assert f.parametres() == {"model": "gpt-test-regles", "max_output_tokens": 2000}
    f, _ = fournisseur(REGLAGES.model_copy(update={"niveau_de_reflexion": "tres_eleve"}))
    assert f.parametres()["reasoning"] == {"effort": "xhigh"}


def test_requete_passages_numerotes_et_json_impose():
    f, _ = fournisseur()
    requete = construire_requete(f.parametres(), CONSIGNES_REGLES, PASSAGES, "Comment dévie une grenade ?")
    assert requete["instructions"] == f"{CONSIGNES_REGLES}\n\n{CONSIGNE_FORMAT}"
    (entree,) = requete["input"]
    assert entree["role"] == "user"
    assert entree["content"] == (
        f"[Passage 1] {GRENADE.reference()}\n{GRENADE.texte}\n\n"
        f"[Passage 2] {GABARIT.reference()}\n{GABARIT.texte}\n\n"
        "Question : Comment dévie une grenade ?"
    )
    assert requete["text"]["format"] == {
        "type": "json_schema",
        "name": "reponse_sourcee",
        "schema": SCHEMA_REPONSE,
        "strict": True,
    }


def test_schema_strict_valide():
    """Mode strict : chaque objet liste toutes ses propriétés dans `required` et interdit les autres."""

    def verifier(schema):
        if schema.get("type") == "object":
            assert schema["additionalProperties"] is False
            assert sorted(schema["required"]) == sorted(schema["properties"])
            for sous in schema["properties"].values():
                verifier(sous)
        if schema.get("type") == "array":
            verifier(schema["items"])

    verifier(SCHEMA_REPONSE)


# --- Sources vérifiées ----------------------------------------------------------------


def test_extraits_verifies_mot_pour_mot():
    texte = json_reponse(
        ("La grenade dévie.", [(1, "dévient selon le diagramme")]),
        ("Elle explose en fin de tour.", [(2, "explose à la fin du tour")]),
    )
    r = lire_reponse(texte, PASSAGES)
    assert r.texte == "La grenade dévie. Elle explose en fin de tour."
    assert [s.passage for s in r.sources] == [GRENADE, GABARIT]
    assert r.sources[0].extraits == ("dévient selon le diagramme",)
    assert [s.sources for s in r.segments] == [(1,), (2,)]
    assert r.extraits_ecartes == 0


def test_espaces_normalises():
    r = lire_reponse(json_reponse(("x", [(1, "dévient   selon\nle diagramme")])), PASSAGES)
    assert r.sources[0].extraits == ("dévient selon le diagramme",)


@pytest.mark.parametrize(
    "citation",
    [
        (1, "dévient selon la table"),  # extrait inventé
        (2, "dévient selon le diagramme"),  # bon extrait, mauvais passage
        (3, "dévient"),  # passage inexistant
        (0, "dévient"),  # numérotation à partir de 1
        (1, "   "),  # extrait vide
    ],
)
def test_extrait_introuvable_ecarte(citation):
    r = lire_reponse(json_reponse(("La grenade dévie.", [citation])), PASSAGES)
    assert r.sources == ()
    assert r.segments[0].sources == ()
    assert r.extraits_ecartes == 1


def test_mix_garde_les_bons_extraits():
    r = lire_reponse(
        json_reponse(("x", [(1, "dévient selon le diagramme"), (1, "inventé")])), PASSAGES
    )
    assert r.sources[0].extraits == ("dévient selon le diagramme",)
    assert r.extraits_ecartes == 1


def test_separation_entre_segments():
    r = lire_reponse(json_reponse(("Un.", []), ("Deux", []), (", trois.", []), (" Quatre.", [])), PASSAGES)
    assert r.texte == "Un. Deux, trois. Quatre."


@pytest.mark.parametrize("texte", ["pas du json", '{"autre": 1}', '{"segments": [{"texte": 3}]}'])
def test_json_mal_forme(texte):
    with pytest.raises(ReponseIncomplete, match="mal formée"):
        lire_reponse(texte, PASSAGES)


def test_reponse_sourcee_de_bout_en_bout():
    texte = json_reponse(("Elle dévie.", [(1, "dévient selon le diagramme")]))
    f, client = fournisseur(return_value=reponse(message(texte)))
    r = f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")
    assert r.sources[0].passage == GRENADE
    assert client.responses.create.call_args.kwargs["model"] == "gpt-test-regles"


# --- Erreurs -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rep", "attendu"),
    [
        (reponse(status="incomplete", raison="max_output_tokens"), "tronquée"),
        (reponse(status="incomplete", raison="content_filter"), "refusé"),
        (reponse(status="incomplete", raison="max_messages"), r"incomplète \(max_messages\)"),
        (reponse(refus()), "refusé"),
    ],
)
def test_reponse_incomplete(rep, attendu):
    f, _ = fournisseur(return_value=rep)
    with pytest.raises(ReponseIncomplete, match=attendu):
        f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")


def test_echec_de_la_reponse():
    rep = reponse(status="failed")
    rep.error = MagicMock(message="server_error")
    f, _ = fournisseur(return_value=rep)
    with pytest.raises(ErreurFournisseur, match="échec de la réponse \\(server_error\\)"):
        f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")


def test_cle_absente(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_ADMIN_KEY", raising=False)
    f = FournisseurOpenAI(REGLAGES)
    with pytest.raises(IdentifiantsAbsents, match="OPENAI_API_KEY"):
        f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")


def _erreur_http(classe, statut, message):
    requete = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    return classe(message, response=httpx2.Response(statut, request=requete), body=None)


def test_cle_refusee():
    f, _ = fournisseur(side_effect=_erreur_http(openai.AuthenticationError, 401, "Incorrect API key"))
    with pytest.raises(IdentifiantsAbsents, match="Clé OpenAI refusée"):
        f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")


def test_erreur_api_convertie():
    f, _ = fournisseur(side_effect=_erreur_http(openai.NotFoundError, 404, "model gpt-x does not exist"))
    with pytest.raises(ErreurFournisseur, match="API OpenAI : model gpt-x does not exist"):
        f.repondre_avec_sources(CONSIGNES_REGLES, PASSAGES, "q")


def test_cle_api_transmise_au_sdk(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    recus = []

    def faux_openai(**kw):
        recus.append(kw)
        return MagicMock()

    monkeypatch.setattr(openai, "OpenAI", faux_openai)
    FournisseurOpenAI(REGLAGES, cle_api="sk-fichier")._client_ou_defaut()
    assert recus == [{"api_key": "sk-fichier"}]
