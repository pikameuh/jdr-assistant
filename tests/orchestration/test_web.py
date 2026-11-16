"""Couche 3 : interface web (API HTTP), client Anthropic mocké."""

import re
from unittest.mock import MagicMock

import pytest
from anthropic.types import Message, TextBlock, ToolUseBlock, Usage
from fastapi.testclient import TestClient

from agent_jdr.core.config import CONFIG_DEFAUT, charger_config, charger_secrets
from agent_jdr.core.fournisseurs import creer_fournisseur
from agent_jdr.core.rules_index import Passage, construire_index
from agent_jdr.interfaces.web.app import creer_app
from tests.pdf_factice import ecrire_pdf
from tests.reglages_test import ecrire_config

PLEIN = Passage("Manuel des joueurs", 196, 196, "Voyage", "Faire le plein", "", "Une pile énergétique coûte cher.")
CLE_REGLES = "sk-ant-regles-0123456789"
CLE_PNJ = "sk-ant-personas-9876543210"


def _message(blocs, stop_reason="end_turn"):
    return Message(
        id="msg_test", type="message", role="assistant", model="claude-test", content=blocs,
        stop_reason=stop_reason, stop_sequence=None, usage=Usage(input_tokens=1, output_tokens=1),
    )


def texte(t):
    return _message([TextBlock(type="text", text=t)])


def recherche(requete):
    return _message([ToolUseBlock(type="tool_use", id="toolu_1", name="rechercher_regle", input={"requete": requete})], "tool_use")


class Fabrique:
    """Remplace `creer_fournisseur` : vrai adaptateur Anthropic, client SDK mocké."""

    def __init__(self):
        self.client = MagicMock()
        self.cles = []

    def reponses(self, *messages):
        self.client.messages.create.side_effect = list(messages)

    def __call__(self, reglages, cle_api=None):
        self.cles.append(cle_api)
        return creer_fournisseur(reglages, client=self.client, cle_api=cle_api)


@pytest.fixture
def chemin_config(tmp_path):
    db = tmp_path / "rules.db"
    construire_index([PLEIN], db)
    chemin = ecrire_config(
        tmp_path,
        secrets={"recherche-apikey": CLE_REGLES, "personas-apikey": CLE_PNJ},
        fichiers={"index_des_regles": str(db), "dossier_des_sessions": str(tmp_path / "sessions")},
    )
    return chemin


@pytest.fixture
def fabrique():
    return Fabrique()


@pytest.fixture
def web(chemin_config, fabrique):
    return TestClient(creer_app(chemin_config, fabrique), base_url="http://127.0.0.1")


def nouvelle_session(web, **champs):
    corps = {"persona": "orla-venn", "pj": "Kael", "lieu": "Dock 7", "moment": "Cycle de nuit", **champs}
    rep = web.post("/api/sessions", json=corps)
    assert rep.status_code == 201, rep.text
    return rep.json()


# --- Pages et sécurité -----------------------------------------------------------------


def test_page_d_accueil(web):
    rep = web.get("/")
    assert rep.status_code == 200 and "Assistant du meneur" in rep.text
    assert web.get("/static/app.js").status_code == 200


def test_hote_etranger_refuse(chemin_config, fabrique):
    client = TestClient(creer_app(chemin_config, fabrique), base_url="http://pirate.example")
    assert client.get("/api/config").status_code == 400


def test_manuel_en_html_avec_ancres_du_sommaire(web):
    html = web.get("/api/manuel").json()["html"]
    assert "<h1" in html and "<table>" in html
    liens = re.findall(r'href="#([^"]+)"', html)
    ids = set(re.findall(r'id="([^"]+)"', html))
    assert liens and set(liens) <= ids


# --- Configuration ---------------------------------------------------------------------


def test_config_cles_jamais_envoyees_en_clair(web):
    rep = web.get("/api/config")
    assert CLE_REGLES not in rep.text and CLE_PNJ not in rep.text
    usages = rep.json()["usages"]
    assert usages["questions_de_regles"]["cle_masquee"] == "sk-an***89"
    assert usages["dialogue"]["cle_masquee"] == "sk-an***10"
    assert usages["dialogue"]["cle_source"] == "fichier"
    assert "claude-sonnet-5-5" in [m["nom"] for m in rep.json()["catalogue"]["anthropic"]]


def test_config_cle_depuis_l_environnement(tmp_path, fabrique, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-environnement-42")
    web = TestClient(creer_app(ecrire_config(tmp_path), fabrique), base_url="http://127.0.0.1")
    usage = web.get("/api/config").json()["usages"]["dialogue"]
    assert (usage["cle_source"], usage["cle_masquee"]) == ("environnement", "sk-an***42")


def test_choisir_modele_et_cle(web, chemin_config):
    rep = web.put("/api/config/usage", json={
        "section": "dialogue", "fournisseur": "openai", "modele": "gpt-6.1-sol", "cle": "sk-openai-nouvelle-77",
    })
    assert rep.status_code == 200, rep.text
    assert rep.json()["usages"]["dialogue"]["cle_masquee"] == "sk-op***77"
    config = charger_config(chemin_config)
    assert (config.dialogue.fournisseur, config.dialogue.modele) == ("openai", "gpt-6.1-sol")
    assert config.questions_de_regles.modele == charger_config(CONFIG_DEFAUT).questions_de_regles.modele
    secrets = charger_secrets(config.fichiers.secrets)
    assert (secrets.personas, secrets.recherche) == ("sk-openai-nouvelle-77", CLE_REGLES)


def test_cle_none_inchangee_et_vide_effacee(web, chemin_config):
    corps = {"section": "questions_de_regles", "fournisseur": "anthropic", "modele": "claude-haiku-5-5"}
    assert web.put("/api/config/usage", json={**corps, "cle": None}).status_code == 200
    fichier = charger_config(chemin_config).fichiers.secrets
    assert charger_secrets(fichier).recherche == CLE_REGLES
    usage = web.put("/api/config/usage", json={**corps, "cle": ""}).json()["usages"]["questions_de_regles"]
    assert charger_secrets(fichier).recherche is None
    assert usage["modele"] == "claude-haiku-5-5"


def test_modele_hors_catalogue_refuse(web, chemin_config):
    avant = chemin_config.read_text(encoding="utf-8")
    rep = web.put("/api/config/usage", json={"section": "dialogue", "fournisseur": "anthropic", "modele": "claude-inconnu"})
    assert rep.status_code == 422 and "catalogue" in rep.json()["erreur"]
    assert chemin_config.read_text(encoding="utf-8") == avant


def test_cle_invalide_n_ecrit_rien(web, chemin_config):
    avant = chemin_config.read_text(encoding="utf-8")
    rep = web.put("/api/config/usage", json={
        "section": "dialogue", "fournisseur": "openai", "modele": "gpt-6.1-sol", "cle": "sk avec espace",
    })
    assert rep.status_code == 422 and "Rien n'a été enregistré" in rep.json()["erreur"]
    assert chemin_config.read_text(encoding="utf-8") == avant


def test_editeur_texte_valide_puis_enregistre(web, chemin_config):
    texte = web.get("/api/config").json()["texte"]
    rep = web.put("/api/config", json={"texte": texte.replace("passages_envoyes: 8", "passages_envoyes: 11")})
    assert rep.status_code == 200
    assert charger_config(chemin_config).questions_de_regles.passages_envoyes == 11


def test_editeur_texte_invalide_n_ecrit_rien(web, chemin_config):
    avant = chemin_config.read_text(encoding="utf-8")
    rep = web.put("/api/config", json={"texte": avant.replace("passages_envoyes: 8", "passages_envoyes: beaucoup")})
    assert rep.status_code == 422
    assert "passages_envoyes : doit être un nombre entier" in rep.json()["erreur"]
    assert chemin_config.read_text(encoding="utf-8") == avant


def test_config_casse_lisible_et_reparable(web, chemin_config):
    bon = chemin_config.read_text(encoding="utf-8")
    chemin_config.write_text(bon.replace("dialogue:", "dialog:", 1), encoding="utf-8")
    etat = web.get("/api/config").json()
    assert etat["usages"] is None and "réglage inconnu" in etat["erreur"] and etat["texte"]
    rep = web.post("/api/regles", json={"question": "plein", "brut": True})
    assert rep.status_code == 409 and "Configuration invalide" in rep.json()["erreur"]
    assert web.put("/api/config", json={"texte": bon}).status_code == 200
    assert web.post("/api/regles", json={"question": "plein", "brut": True}).status_code == 200


# --- Questions de règles ---------------------------------------------------------------


def test_regles_brut_sans_appel_llm(web, fabrique):
    passages = web.post("/api/regles", json={"question": "pile énergétique", "brut": True}).json()["passages"]
    assert passages[0]["reference"] == PLEIN.reference()
    assert fabrique.cles == [] and not fabrique.client.messages.create.called


def test_regles_reponse_et_sources(web, fabrique, message_factice):
    fabrique.reponses(message_factice([("Ça coûte cher.", [(0, "coûte cher")])]))
    rep = web.post("/api/regles", json={"question": "prix pile énergétique", "passages": 3})
    assert rep.status_code == 200, rep.text
    r = rep.json()
    assert r["segments"] == [{"texte": "Ça coûte cher.", "sources": [1]}]
    assert r["sources"][0]["reference"] == PLEIN.reference()
    assert r["sources"][0]["extraits"] == ["coûte cher"]
    assert fabrique.cles == [CLE_REGLES]


def test_regles_question_vide(web):
    rep = web.post("/api/regles", json={"question": ""})
    assert rep.status_code == 422 and "question" in rep.json()["erreur"]


def test_regles_identifiants_refuses(web, fabrique):
    fabrique.client.messages.create.side_effect = TypeError(
        "Could not resolve authentication method. Expected either api_key or auth_token to be set."
    )
    rep = web.post("/api/regles", json={"question": "pile énergétique"})
    assert rep.status_code == 401 and "fenêtre Config" in rep.json()["erreur"]


def test_regles_index_absent(tmp_path, fabrique):
    config = ecrire_config(tmp_path, fichiers={"index_des_regles": str(tmp_path / "absent.db")})
    web = TestClient(creer_app(config, fabrique), base_url="http://127.0.0.1")
    rep = web.post("/api/regles", json={"question": "plein", "brut": True})
    assert rep.status_code == 409 and "rules_index build" in rep.json()["erreur"]


# --- PNJ et sessions -------------------------------------------------------------------


def test_personas(web):
    assert [p["id"] for p in web.get("/api/personas").json()] == ["orla-venn"]


def test_session_complete(web, fabrique):
    s = nouvelle_session(web, ambiance="Néons", enjeux="Une pile")
    assert s["persona_nom"] == "Orla Venn" and s["historique"] == []
    assert s["scene"]["pj_presents"] == ["Kael"] and s["scene"]["pnj_presents"] == ["orla-venn"]

    fabrique.reponses(recherche("prix pile"), texte("*croise les bras* Trois cents crédits."))
    rep = web.post(f"/api/sessions/{s['id']}/messages", json={"texte": "Combien la pile ?"})
    assert rep.status_code == 200, rep.text
    historique = rep.json()["historique"]
    assert [(t["locuteur"], t["texte"]) for t in historique] == [
        ("joueur", "Combien la pile ?"), ("pnj", "*croise les bras* Trois cents crédits."),
    ]
    assert historique[0]["pj"] == "Kael" and historique[1]["regles"] == [PLEIN.reference()]
    assert fabrique.cles == [CLE_PNJ]

    # L'historique est conservé (relu depuis le disque) et renvoyé au modèle au tour suivant.
    assert web.get(f"/api/sessions/{s['id']}").json()["historique"] == historique
    fabrique.reponses(texte("Non."))
    web.post(f"/api/sessions/{s['id']}/messages", json={"texte": "Un rabais ?"})
    messages = fabrique.client.messages.create.call_args.kwargs["messages"]
    assert "Combien la pile ?" in str(messages[0]) and "Trois cents crédits" in str(messages[1])

    liste = web.get("/api/sessions").json()
    assert [(x["id"], x["echanges"], x["persona_nom"]) for x in liste] == [(s["id"], 2, "Orla Venn")]


def test_fait_ajoute_a_la_scene(web):
    s = nouvelle_session(web)
    rep = web.post(f"/api/sessions/{s['id']}/faits", json={"fait": "Kael a payé"})
    assert rep.json()["scene"]["faits_etablis"] == ["Kael a payé"]
    assert web.post(f"/api/sessions/{s['id']}/faits", json={"fait": "   "}).status_code == 422


def test_effacer_historique_garde_la_session(web, fabrique):
    s = nouvelle_session(web)
    web.post(f"/api/sessions/{s['id']}/faits", json={"fait": "Kael a payé"})
    fabrique.reponses(texte("Bonsoir."))
    web.post(f"/api/sessions/{s['id']}/messages", json={"texte": "Bonsoir"})
    rep = web.delete(f"/api/sessions/{s['id']}/historique")
    assert rep.status_code == 200
    assert rep.json()["historique"] == [] and rep.json()["scene"]["faits_etablis"] == ["Kael a payé"]
    assert web.get(f"/api/sessions/{s['id']}").json()["historique"] == []


def test_supprimer_session(web):
    s = nouvelle_session(web)
    assert web.delete(f"/api/sessions/{s['id']}").status_code == 204
    assert web.get(f"/api/sessions/{s['id']}").status_code == 404
    assert web.delete(f"/api/sessions/{s['id']}").status_code == 404
    assert web.get("/api/sessions").json() == []


def test_erreur_du_modele_n_enregistre_rien(web, fabrique):
    s = nouvelle_session(web)
    fabrique.reponses(texte("   "))
    rep = web.post(f"/api/sessions/{s['id']}/messages", json={"texte": "Bonsoir"})
    assert rep.status_code == 502 and "aucune réplique" in rep.json()["erreur"]
    assert web.get(f"/api/sessions/{s['id']}").json()["historique"] == []


def test_pnj_inconnu_et_session_inconnue(web):
    rep = web.post("/api/sessions", json={"persona": "personne", "pj": "K", "lieu": "L", "moment": "M"})
    assert rep.status_code == 404
    assert web.get("/api/sessions/" + "0" * 32).status_code == 404
    assert web.get("/api/sessions/..%2Fconfig").status_code == 404
    assert web.post("/api/sessions", json={"persona": "orla-venn", "pj": "", "lieu": "L", "moment": "M"}).status_code == 422


def test_sessions_rangees_dans_le_dossier_configure(web, chemin_config):
    s = nouvelle_session(web)
    assert (charger_config(chemin_config).fichiers.dossier_des_sessions / f"{s['id']}.json").is_file()


# --- Création de PNJ -------------------------------------------------------------------


@pytest.fixture
def web_pnj(tmp_path, fabrique):
    """Dossier des PNJ temporaire (copie d'Orla), pour ne jamais écrire dans le vrai dossier."""
    dossier = tmp_path / "personas"
    dossier.mkdir()
    orla = charger_config().fichiers.dossier_des_pnj / "orla-venn.yaml"
    (dossier / "orla-venn.yaml").write_text(orla.read_text(encoding="utf-8"), encoding="utf-8")
    config = ecrire_config(tmp_path, fichiers={"dossier_des_pnj": str(dossier), "dossier_des_sessions": str(tmp_path / "s")})
    return TestClient(creer_app(config, fabrique), base_url="http://127.0.0.1"), dossier


def test_modele_et_copie_de_fiche(web_pnj):
    web, _ = web_pnj
    assert web.get("/api/personas/modele").json()["nom"] == "Capitaine Rook"
    orla = web.get("/api/personas/orla-venn").json()
    assert orla["parole"]["tics"] and orla["secrets"][0]["condition_revelation"]
    assert web.get("/api/personas/inconnu").status_code == 404


def test_creer_pnj_puis_lui_parler(web_pnj):
    web, dossier = web_pnj
    fiche = {**web.get("/api/personas/modele").json(), "id": "capitaine-rook"}
    rep = web.post("/api/personas", json={"fiche": fiche})
    assert rep.status_code == 201 and rep.json()["id"] == "capitaine-rook"
    assert (dossier / "capitaine-rook.yaml").is_file()
    assert "capitaine-rook" in [p["id"] for p in web.get("/api/personas").json()]
    assert nouvelle_session(web, persona="capitaine-rook")["persona_nom"] == "Capitaine Rook"


def test_creer_pnj_erreurs_par_champ(web_pnj):
    web, dossier = web_pnj
    rep = web.post("/api/personas", json={"fiche": {"id": "x", "nom": "X"}})
    assert rep.status_code == 422
    assert rep.json()["champs"]["role"] == "à remplir" and rep.json()["champs"]["parole.registre"] == "à remplir"
    assert sorted(p.name for p in dossier.iterdir()) == ["orla-venn.yaml"]


def test_creer_pnj_existant_refuse(web_pnj):
    web, dossier = web_pnj
    avant = (dossier / "orla-venn.yaml").read_text(encoding="utf-8")
    fiche = {**web.get("/api/personas/orla-venn").json(), "nom": "Imposteur"}
    rep = web.post("/api/personas", json={"fiche": fiche})
    assert rep.status_code == 409 and "existe déjà" in rep.json()["champs"]["id"]
    assert (dossier / "orla-venn.yaml").read_text(encoding="utf-8") == avant


# --- Modification de PNJ ---------------------------------------------------------------


def test_modifier_pnj_puis_session_a_jour(web_pnj):
    web, dossier = web_pnj
    session = nouvelle_session(web)
    fiche = {**web.get("/api/personas/orla-venn").json(), "nom": "Orla Venn-Kade"}
    rep = web.put("/api/personas/orla-venn", json={"fiche": fiche})
    assert rep.status_code == 200 and rep.json()["nom"] == "Orla Venn-Kade"
    assert web.get("/api/personas/orla-venn").json()["nom"] == "Orla Venn-Kade"
    assert web.get(f"/api/sessions/{session['id']}").json()["persona_nom"] == "Orla Venn-Kade"
    assert sorted(p.name for p in dossier.iterdir()) == ["orla-venn.yaml"]


def test_modifier_pnj_erreurs(web_pnj):
    web, dossier = web_pnj
    avant = (dossier / "orla-venn.yaml").read_text(encoding="utf-8")
    fiche = web.get("/api/personas/orla-venn").json()
    rep = web.put("/api/personas/orla-venn", json={"fiche": {**fiche, "personnalite": ""}})
    assert rep.status_code == 422 and rep.json()["champs"] == {"personnalite": "à remplir"}
    rep = web.put("/api/personas/orla-venn", json={"fiche": {**fiche, "id": "autre"}})
    assert rep.status_code == 422 and "ne peut pas changer" in rep.json()["champs"]["id"]
    assert web.put("/api/personas/inconnu", json={"fiche": fiche}).status_code == 404
    assert (dossier / "orla-venn.yaml").read_text(encoding="utf-8") == avant


# --- Historique des recherches ---------------------------------------------------------


def test_historique_enregistre_rouvre_recherche_supprime(web, fabrique, message_factice, tmp_path):
    fabrique.reponses(message_factice([("Ça coûte cher.", [(0, "coûte cher")])]))
    r1 = web.post("/api/regles", json={"question": "prix pile énergétique"}).json()
    r2 = web.post("/api/regles", json={"question": "pile énergétique", "brut": True}).json()
    liste = web.get("/api/historique").json()
    assert [(e["id"], e["mode"]) for e in liste] == [(r2["id_historique"], "passages"), (r1["id_historique"], "reponse")]
    assert liste[1]["apercu"] == "Ça coûte cher."
    detail = web.get(f"/api/historique/{r1['id_historique']}").json()
    assert detail["question"] == "prix pile énergétique"
    assert detail["resultat"]["segments"] == r1["segments"] and detail["resultat"]["livres"] == r1["livres"]
    assert [e["id"] for e in web.get("/api/historique", params={"q": "COUTE"}).json()] == [r1["id_historique"]]
    assert web.delete(f"/api/historique/{r1['id_historique']}").status_code == 204
    assert web.get(f"/api/historique/{r1['id_historique']}").status_code == 404
    assert web.delete(f"/api/historique/{r1['id_historique']}").status_code == 404
    assert web.delete("/api/historique").json() == {"supprimees": 1}
    assert web.get("/api/historique").json() == []
    assert (tmp_path / "historique").is_dir()  # rangé dans le dossier configuré (temporaire)


def test_historique_n_enregistre_pas_les_echecs(web, fabrique):
    fabrique.client.messages.create.side_effect = TypeError(
        "Could not resolve authentication method. Expected either api_key or auth_token to be set."
    )
    assert web.post("/api/regles", json={"question": "pile énergétique"}).status_code == 401
    assert web.get("/api/historique").json() == []


# --- Livres de règles ------------------------------------------------------------------


@pytest.fixture
def web_livres(tmp_path, fabrique):
    """Dossier des livres et index temporaires, un PDF réel déjà indexé."""
    dossier = tmp_path / "livres"
    dossier.mkdir()
    ecrire_pdf(dossier / "Ancien.pdf", ["Le carburant se paie au quai."])
    db = tmp_path / "rules.db"
    config = ecrire_config(
        tmp_path,
        fichiers={"dossier_des_pdf": str(dossier), "index_des_regles": str(db)},
        regles={"livres_utilises": ["Ancien.pdf"]},
    )
    web = TestClient(creer_app(config, fabrique), base_url="http://127.0.0.1")
    assert web.post("/api/livres/indexation").status_code == 200
    return web, dossier, config


def test_livres_etat(web_livres):
    web, dossier, _ = web_livres
    etat = web.get("/api/livres").json()
    assert etat["index_present"] and etat["dossier"] == str(dossier)
    assert [(l["fichier"], l["passages"], l["utilise"]) for l in etat["livres"]] == [("Ancien.pdf", 1, True)]


def test_decocher_un_livre_persiste_et_filtre_la_recherche(web_livres):
    web, _, config = web_livres
    question = {"question": "carburant", "brut": True}
    assert len(web.post("/api/regles", json=question).json()["passages"]) == 1
    etat = web.put("/api/livres/choix", json={"fichiers": []}).json()
    assert [l["utilise"] for l in etat["livres"]] == [False]
    assert charger_config(config).regles.livres_utilises == ()  # écrit dans config.yaml
    rep = web.post("/api/regles", json=question)
    assert rep.status_code == 409 and "onglet Livres" in rep.json()["erreur"]
    web.put("/api/livres/choix", json={"fichiers": ["Ancien.pdf"]})
    assert len(web.post("/api/regles", json=question).json()["passages"]) == 1


def test_choisir_un_livre_inconnu_refuse(web_livres):
    web, _, config = web_livres
    rep = web.put("/api/livres/choix", json={"fichiers": ["Inexistant.pdf"]})
    assert rep.status_code == 422 and "Inexistant.pdf" in rep.json()["erreur"]
    assert charger_config(config).regles.livres_utilises == ("Ancien.pdf",)


def test_ajouter_pdf_indexe_et_coche(web_livres, tmp_path):
    web, dossier, config = web_livres
    pdf = ecrire_pdf(tmp_path / "source.pdf", ["Les pirates attaquent au cycle de nuit."]).read_bytes()
    rep = web.post("/api/livres", params={"nom": "Écran du meneur.pdf"}, content=pdf, headers={"Content-Type": "application/pdf"})
    assert rep.status_code == 201, rep.text
    assert "2 passages indexés" in rep.json()["message"]
    assert (dossier / "Écran du meneur.pdf").read_bytes() == pdf
    assert charger_config(config).regles.livres_utilises == ("Ancien.pdf", "Écran du meneur.pdf")
    passages = web.post("/api/regles", json={"question": "pirates", "brut": True}).json()["passages"]
    assert passages[0]["reference"].startswith("Écran du meneur, p. 1")


def test_ajouter_pdf_sans_texte_signale(web_livres, tmp_path):
    web, _, _ = web_livres
    pdf = ecrire_pdf(tmp_path / "vide.pdf", [""]).read_bytes()
    rep = web.post("/api/livres", params={"nom": "Scan.pdf"}, content=pdf, headers={"Content-Type": "application/pdf"})
    assert rep.status_code == 201 and "aucun texte trouvé" in rep.json()["message"]


def test_ajouter_pdf_illisible_retire_et_index_conserve(web_livres):
    web, dossier, config = web_livres
    rep = web.post("/api/livres", params={"nom": "Abime.pdf"}, content=b"%PDF-1.7 tronque", headers={"Content-Type": "application/pdf"})
    assert rep.status_code == 502
    assert "PDF illisible : Abime.pdf" in rep.json()["erreur"] and "pas été ajouté" in rep.json()["erreur"]
    assert sorted(p.name for p in dossier.iterdir()) == ["Ancien.pdf"]
    assert charger_config(config).regles.livres_utilises == ("Ancien.pdf",)
    assert [l["passages"] for l in web.get("/api/livres").json()["livres"]] == [1]


@pytest.mark.parametrize(
    "nom, contenu, type_, statut, message",
    [
        ("a.pdf", b"%PDF-1.7", "text/plain", 415, "application/pdf"),
        ("a.pdf", b"<html>", "application/pdf", 422, "pas un fichier PDF"),
        ("../a.pdf", b"%PDF-1.7", "application/pdf", 422, "Nom de fichier refusé"),
        ("Ancien.pdf", b"%PDF-1.7", "application/pdf", 422, "existe déjà"),
    ],
)
def test_ajouter_pdf_refuse(web_livres, nom, contenu, type_, statut, message):
    web, dossier, _ = web_livres
    rep = web.post("/api/livres", params={"nom": nom}, content=contenu, headers={"Content-Type": type_})
    assert rep.status_code == statut and message in rep.json()["erreur"]
    assert sorted(p.name for p in dossier.iterdir()) == ["Ancien.pdf"]
    assert (dossier / "Ancien.pdf").read_bytes().startswith(b"%PDF-")
