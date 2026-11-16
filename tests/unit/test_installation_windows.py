"""Script d'installation Windows (`installer-windows.bat`), vérifié sans Windows.

Ces tests ne lancent pas le script (cmd.exe absent ici) : ils vérifient qu'il est lisible par
cmd.exe (fins de ligne CRLF, étiquettes de saut existantes), qu'il installe par uv, qu'il ne
remplace jamais un `secrets.yaml` existant, et que la commande annoncée existe dans le projet.
"""

import re
import tomllib
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SCRIPT = RACINE / "installer-windows.bat"


def _octets() -> bytes:
    return SCRIPT.read_bytes()


def _texte() -> str:
    return _octets().decode("utf-8")


def test_fins_de_ligne_crlf_sans_bom():
    octets = _octets()
    assert not octets.startswith(b"\xef\xbb\xbf"), "un BOM UTF-8 casse la première ligne sous cmd.exe"
    assert octets.count(b"\n") == octets.count(b"\r\n"), "cmd.exe exige des fins de ligne CRLF"


def test_gitattributes_force_crlf_pour_les_bat():
    attributs = (RACINE / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert "*.bat text eol=crlf" in attributs


def test_affichage_utf8_et_dossier_du_script():
    texte = _texte()
    assert "chcp 65001" in texte
    assert 'cd /d "%~dp0"' in texte


def test_chaque_goto_vise_une_etiquette_existante():
    texte = _texte()
    etiquettes = set(re.findall(r"^:(\w+)\s*$", texte, re.M))
    sauts = set(re.findall(r"\bgoto (\w+)", texte))
    assert sauts, "aucun saut trouvé"
    assert sauts <= etiquettes, f"étiquettes manquantes : {sauts - etiquettes}"


def test_installe_uv_puis_les_dependances():
    texte = _texte()
    assert "https://astral.sh/uv/install.ps1" in texte
    assert re.search(r"^uv sync\s*$", texte, re.M)
    assert "if errorlevel 1 goto echec_sync" in texte


def test_secrets_copie_seulement_s_il_est_absent():
    lignes = [ligne.strip() for ligne in _texte().splitlines()]
    garde = lignes.index('if exist "secrets.yaml" goto secrets_present')
    copie = lignes.index('copy "secrets.exemple.yaml" "secrets.yaml" >nul')
    assert garde < copie, "la copie doit être précédée du test d'existence"
    assert (RACINE / "secrets.exemple.yaml").is_file()
    assert not re.search(r"^\s*(del|erase|move)\b", _texte(), re.M | re.I)


def test_commande_annoncee_existe_et_fenetre_reste_ouverte():
    texte = _texte()
    scripts = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
    assert "web" in scripts
    assert re.search(r"^echo\s+uv run web\s*$", texte, re.M)
    # Double-clic : sans pause, la fenêtre se fermerait avant que l'on puisse lire.
    assert texte.count("\npause") == 4  # fin normale + trois cas d'erreur


def test_sections_du_manuel_citees_existent():
    manuel = (RACINE / "MANUEL.md").read_text(encoding="utf-8")
    for numero in re.findall(r"MANUEL\.md, section (\d+)", _texte()):
        assert re.search(rf"^## {numero}\. ", manuel, re.M), f"section {numero} absente du manuel"
