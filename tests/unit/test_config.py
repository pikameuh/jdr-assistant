"""Couche 1 : lecture et validation de config.yaml."""

from pathlib import Path

import pytest
import yaml

from agent_jdr.core.config import (
    CONFIG_DEFAUT,
    NIVEAUX_DE_REFLEXION,
    ConfigInvalide,
    charger_config,
)


@pytest.fixture
def donnees():
    """Contenu du config.yaml livré, sous forme de dictionnaire modifiable."""
    return yaml.safe_load(CONFIG_DEFAUT.read_text(encoding="utf-8"))


def ecrire(dossier, donnees):
    chemin = dossier / "config.yaml"
    chemin.write_text(yaml.safe_dump(donnees, allow_unicode=True), encoding="utf-8")
    return chemin


def test_config_livree_valide():
    config = charger_config()
    assert config.dialogue.modele == "claude-sonnet-5-5"
    assert config.questions_de_regles.modele == "claude-sonnet-5-5"
    assert config.dialogue.consignes and config.questions_de_regles.consignes
    assert config.fichiers.index_des_regles == CONFIG_DEFAUT.parent / "data" / "rules.db"


def test_chemins_relatifs_au_dossier_du_fichier(tmp_path, donnees):
    donnees["fichiers"]["dossier_des_pnj"] = "mes_pnj"
    donnees["fichiers"]["dossier_des_pdf"] = "/absolu/pdf"
    config = charger_config(ecrire(tmp_path, donnees))
    assert config.fichiers.dossier_des_pnj == tmp_path.resolve() / "mes_pnj"
    assert config.fichiers.dossier_des_pdf == Path("/absolu/pdf")


@pytest.mark.parametrize(("niveau", "effort"), list(NIVEAUX_DE_REFLEXION.items()))
def test_niveau_de_reflexion(tmp_path, donnees, niveau, effort):
    donnees["dialogue"]["niveau_de_reflexion"] = niveau
    params = charger_config(ecrire(tmp_path, donnees)).dialogue.parametres_modele()
    if effort is None:
        assert "output_config" not in params
    else:
        assert params["output_config"] == {"effort": effort}


def test_reglage_manquant_nomme(tmp_path, donnees):
    del donnees["dialogue"]["modele"]
    with pytest.raises(ConfigInvalide, match="dialogue > modele : réglage manquant"):
        charger_config(ecrire(tmp_path, donnees))


def test_reglage_mal_orthographie_refuse(tmp_path, donnees):
    donnees["dialogue"]["modèle"] = donnees["dialogue"].pop("modele")
    with pytest.raises(ConfigInvalide, match=r"dialogue > modèle : réglage inconnu \(faute de frappe \?\)"):
        charger_config(ecrire(tmp_path, donnees))


def test_niveau_inconnu_liste_les_valeurs_permises(tmp_path, donnees):
    donnees["questions_de_regles"]["niveau_de_reflexion"] = "fort"
    with pytest.raises(ConfigInvalide, match="valeur non permise ; choix possibles : 'defaut', 'bas', 'moyen'"):
        charger_config(ecrire(tmp_path, donnees))


@pytest.mark.parametrize(
    ("section", "cle", "valeur", "message"),
    [
        ("dialogue", "modele", "gpt-4", "nom de modèle incorrect"),
        ("dialogue", "longueur_max_reponse", 0, "doit être au moins 1"),
        ("dialogue", "longueur_max_reponse", 200000, "doit être au plus 128000"),
        ("dialogue", "recherches_max_par_replique", 0, "doit être au moins 1"),
        ("dialogue", "passages_par_recherche", "cinq", "doit être un nombre entier"),
        ("questions_de_regles", "passages_envoyes", 0, "doit être au moins 1"),
        ("questions_de_regles", "consignes", "   ", "ne doit pas être vide"),
        ("fichiers", "index_des_regles", 3, "doit être un texte"),
    ],
)
def test_valeur_incorrecte(tmp_path, donnees, section, cle, valeur, message):
    donnees[section][cle] = valeur
    with pytest.raises(ConfigInvalide, match=f"{section} > {cle} : {message}"):
        charger_config(ecrire(tmp_path, donnees))


def test_syntaxe_yaml_incorrecte(tmp_path):
    chemin = tmp_path / "config.yaml"
    chemin.write_text("dialogue:\n  modele: [ouvert\n", encoding="utf-8")
    with pytest.raises(ConfigInvalide, match="syntaxe YAML incorrecte"):
        charger_config(chemin)


def test_fichier_absent(tmp_path):
    with pytest.raises(ConfigInvalide, match="lecture impossible"):
        charger_config(tmp_path / "absent.yaml")


def test_fichier_sans_sections(tmp_path):
    chemin = tmp_path / "config.yaml"
    chemin.write_text("- a\n", encoding="utf-8")
    with pytest.raises(ConfigInvalide, match="sections"):
        charger_config(chemin)


def test_section_mal_formee(tmp_path, donnees):
    donnees["fichiers"] = "data"
    with pytest.raises(ConfigInvalide, match="fichiers : doit contenir des sous-réglages"):
        charger_config(ecrire(tmp_path, donnees))
