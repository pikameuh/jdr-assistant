"""Couche 1 : modification de config.yaml et du fichier de secrets (fenêtre Config du web)."""

import stat

import pytest
import yaml

from agent_jdr.core.config import (
    CONFIG_DEFAUT,
    ConfigInvalide,
    charger_catalogue,
    charger_config,
    charger_secrets,
)
from agent_jdr.core.edition_config import (
    choisir_livres,
    choisir_modele,
    enregistrer_cles,
    enregistrer_config,
    masquer_cle,
    remplacer_reglage,
)
from tests.reglages_test import ecrire_config


@pytest.fixture
def config_commentee(tmp_path):
    """Copie exacte du vrai config.yaml (avec ses commentaires)."""
    chemin = tmp_path / "config.yaml"
    chemin.write_text(CONFIG_DEFAUT.read_text(encoding="utf-8"), encoding="utf-8")
    return chemin


# --- Remplacement d'un réglage -------------------------------------------------------


def test_remplacer_reglage_ne_touche_que_la_bonne_section():
    texte = "# en-tête\na:\n  modele: x  # commentaire\nb:\n  modele: x\n"
    assert remplacer_reglage(texte, "b", "modele", "y") == "# en-tête\na:\n  modele: x  # commentaire\nb:\n  modele: y\n"
    assert remplacer_reglage(texte, "a", "modele", "y") == "# en-tête\na:\n  modele: y  # commentaire\nb:\n  modele: x\n"


def test_remplacer_reglage_introuvable():
    with pytest.raises(ConfigInvalide, match="a > absent"):
        remplacer_reglage("a:\n  modele: x\n", "a", "absent", "y")


def test_choisir_modele_garde_les_commentaires(config_commentee):
    avant = config_commentee.read_text(encoding="utf-8")
    config = choisir_modele(config_commentee, "dialogue", "openai", "gpt-6.1-sol")
    assert (config.dialogue.fournisseur, config.dialogue.modele) == ("openai", "gpt-6.1-sol")
    assert config.questions_de_regles == charger_config(CONFIG_DEFAUT).questions_de_regles
    apres = config_commentee.read_text(encoding="utf-8")
    assert [l for l in avant.splitlines() if l.lstrip().startswith("#")] == [
        l for l in apres.splitlines() if l.lstrip().startswith("#")
    ]
    assert charger_config(config_commentee).dialogue.modele == "gpt-6.1-sol"


def test_choisir_modele_incoherent_n_ecrit_rien(config_commentee):
    avant = config_commentee.read_text(encoding="utf-8")
    with pytest.raises(ConfigInvalide, match="n'est pas un modèle Anthropic"):
        choisir_modele(config_commentee, "dialogue", "anthropic", "gpt-6.1-sol")
    assert config_commentee.read_text(encoding="utf-8") == avant


def test_enregistrer_config_invalide_n_ecrit_rien(config_commentee):
    avant = config_commentee.read_text(encoding="utf-8")
    with pytest.raises(ConfigInvalide, match="syntaxe YAML"):
        enregistrer_config(config_commentee, "dialogue: [")
    with pytest.raises(ConfigInvalide, match="réglage manquant"):
        enregistrer_config(config_commentee, "dialogue: {}\n")
    assert config_commentee.read_text(encoding="utf-8") == avant


def test_enregistrer_config_valide(config_commentee):
    texte = config_commentee.read_text(encoding="utf-8").replace("passages_envoyes: 8", "passages_envoyes: 12")
    assert enregistrer_config(config_commentee, texte).questions_de_regles.passages_envoyes == 12
    assert config_commentee.read_text(encoding="utf-8") == texte


# --- Clés API ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cle", "attendu"),
    [(None, ""), ("", ""), ("court", "***"), ("sk-ant-api03-abcdefXY", "sk-an***XY")],
)
def test_masquer_cle(cle, attendu):
    assert masquer_cle(cle) == attendu


def test_enregistrer_cles_cree_le_fichier_depuis_le_modele(tmp_path):
    chemin = tmp_path / "secrets.yaml"
    secrets = enregistrer_cles(chemin, {"recherche-apikey": " sk-ant-regles "})
    assert (secrets.recherche, secrets.personas) == ("sk-ant-regles", None)
    texte = chemin.read_text(encoding="utf-8")
    assert "Copiez ce fichier" in texte  # commentaires du modèle conservés
    assert stat.S_IMODE(chemin.stat().st_mode) == 0o600
    assert charger_secrets(chemin).recherche == "sk-ant-regles"


def test_enregistrer_cles_modifie_efface_et_garde_le_reste(tmp_path):
    chemin = tmp_path / "secrets.yaml"
    chemin.write_text('# mes clés\nrecherche-apikey: "a"\npersonas-apikey: "b"\n', encoding="utf-8")
    enregistrer_cles(chemin, {"personas-apikey": "sk-nouvelle", "recherche-apikey": None})
    assert chemin.read_text(encoding="utf-8") == '# mes clés\nrecherche-apikey: "a"\npersonas-apikey: "sk-nouvelle"\n'
    secrets = enregistrer_cles(chemin, {"recherche-apikey": ""})
    assert (secrets.recherche, secrets.personas) == (None, "sk-nouvelle")


def test_enregistrer_cles_ajoute_une_entree_absente(tmp_path):
    chemin = tmp_path / "secrets.yaml"
    chemin.write_text('recherche-apikey: "a"', encoding="utf-8")
    assert enregistrer_cles(chemin, {"personas-apikey": "b"}).personas == "b"


@pytest.mark.parametrize("cle", ["sk ant", "sk\nrecherche-apikey: pirate"])
def test_enregistrer_cles_refuse_espaces_et_retours(tmp_path, cle):
    chemin = tmp_path / "secrets.yaml"
    with pytest.raises(ConfigInvalide, match="ni espace"):
        enregistrer_cles(chemin, {"personas-apikey": cle})
    assert not chemin.exists()


def test_enregistrer_cles_entree_inconnue(tmp_path):
    with pytest.raises(ConfigInvalide, match="inconnue"):
        enregistrer_cles(tmp_path / "secrets.yaml", {"autre": "x"})


def test_cle_avec_guillemets_relue_telle_quelle(tmp_path):
    chemin = tmp_path / "secrets.yaml"
    assert enregistrer_cles(chemin, {"personas-apikey": 'a"b\\c'}).personas == 'a"b\\c'
    assert charger_secrets(chemin).personas == 'a"b\\c'


# --- Catalogue des modèles -------------------------------------------------------------


def test_catalogue_du_projet_valide():
    catalogue = charger_catalogue(charger_config().fichiers.catalogue_des_modeles)
    assert "claude-sonnet-5-5" in [m.nom for m in catalogue.anthropic]
    assert all(not m.nom.startswith("claude-") for m in catalogue.openai)
    # Les modèles légers portent un avertissement affiché par la fenêtre Config.
    legers = {m.nom for f in ("anthropic", "openai") for m in catalogue.modeles(f) if m.avertissement}
    assert legers == {"claude-haiku-5-5", "gpt-6-luna"}


def test_modeles_par_defaut_presents_dans_le_catalogue():
    config = charger_config()
    catalogue = charger_catalogue(config.fichiers.catalogue_des_modeles)
    for section in (config.dialogue, config.questions_de_regles):
        assert section.modele in [m.nom for m in catalogue.modeles(section.fournisseur)]


def test_catalogue_modele_sous_le_mauvais_fournisseur(tmp_path):
    chemin = tmp_path / "modeles.yaml"
    chemin.write_text(yaml.safe_dump({"anthropic": [{"nom": "gpt-6-luna"}], "openai": [{"nom": "gpt-6-luna"}]}))
    with pytest.raises(ConfigInvalide, match="pas le bon fournisseur"):
        charger_catalogue(chemin)


def test_catalogue_champ_inconnu(tmp_path):
    chemin = tmp_path / "modeles.yaml"
    chemin.write_text(yaml.safe_dump({"anthropic": [{"nom": "claude-x", "cout": 1}], "openai": [{"nom": "gpt"}]}))
    with pytest.raises(ConfigInvalide, match="réglage inconnu"):
        charger_catalogue(chemin)


def test_ecrire_config_de_test_inclut_les_nouveaux_fichiers(tmp_path):
    config = charger_config(ecrire_config(tmp_path))
    assert config.fichiers.dossier_des_sessions.name == "sessions"
    assert config.fichiers.catalogue_des_modeles.name == "modeles.yaml"


# --- Livres utilisés -------------------------------------------------------------------


def test_choisir_livres_garde_les_commentaires(config_commentee):
    avant = config_commentee.read_text(encoding="utf-8")
    config = choisir_livres(config_commentee, ["Écran du meneur.pdf"])
    assert config.regles.livres_utilises == ("Écran du meneur.pdf",)
    apres = config_commentee.read_text(encoding="utf-8")
    assert 'livres_utilises: ["Écran du meneur.pdf"]' in apres
    lignes_changees = [a for a, b in zip(avant.splitlines(), apres.splitlines(), strict=True) if a != b]
    assert len(lignes_changees) == 1  # seule la ligne du réglage change


def test_choisir_aucun_livre(config_commentee):
    assert choisir_livres(config_commentee, []).regles.livres_utilises == ()


@pytest.mark.parametrize("nom", ["Livre #2.pdf", "Livre.txt"])
def test_choisir_livres_nom_refuse_n_ecrit_rien(config_commentee, nom):
    avant = config_commentee.read_text(encoding="utf-8")
    with pytest.raises(ConfigInvalide):
        choisir_livres(config_commentee, [nom])
    assert config_commentee.read_text(encoding="utf-8") == avant


def test_remplacer_une_liste_ecrite_en_colonne():
    texte = "regles:\n  livres_utilises:  # choix\n  - A.pdf\n  -   B.pdf\n# suite\nfichiers:\n  x: 1\n"
    assert remplacer_reglage(texte, "regles", "livres_utilises", '["C.pdf"]') == (
        'regles:\n  livres_utilises: ["C.pdf"]  # choix\n# suite\nfichiers:\n  x: 1\n'
    )
    texte = "regles:\n  livres_utilises:\n    - A.pdf\n  autre: 2\n"
    assert remplacer_reglage(texte, "regles", "livres_utilises", "[]") == "regles:\n  livres_utilises: []\n  autre: 2\n"
