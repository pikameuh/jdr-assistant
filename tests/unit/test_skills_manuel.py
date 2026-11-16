"""Le manuel (section « Se faire aider par Claude Code », affichée aussi par le bouton ? du web)
liste exactement les skills qui réagissent à une phrase de l'utilisateur, avec ces phrases.

Un skill « réagit à une phrase » quand son SKILL.md contient la section `## Phrases de l'utilisateur`
(une phrase par ligne : `- « … »`). Ajouter, retirer ou modifier une telle phrase sans mettre le
manuel à jour fait échouer ces tests.
"""

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SKILLS = RACINE / ".claude" / "skills"
MANUEL = RACINE / "MANUEL.md"
TITRE_SKILL = "## Phrases de l'utilisateur"
TITRE_MANUEL = "Se faire aider par Claude Code"


def _section(texte: str, motif_titre: str) -> str | None:
    """Corps d'une section de niveau 2, jusqu'au titre de niveau 2 suivant."""
    m = re.search(rf"^{motif_titre}\n(.*?)(?=^## |\Z)", texte, re.M | re.S)
    return m.group(1) if m else None


def phrases_des_skills() -> dict[str, list[str]]:
    resultat = {}
    for fichier in sorted(SKILLS.glob("*/SKILL.md")):
        texte = fichier.read_text(encoding="utf-8")
        nom = re.search(r"^name:\s*(\S+)\s*$", texte, re.M)
        assert nom and nom.group(1) == fichier.parent.name, f"{fichier} : `name` ≠ nom du dossier"
        section = _section(texte, re.escape(TITRE_SKILL))
        if section is not None:
            phrases = re.findall(r"^- « (.+?) »", section, re.M)
            assert phrases, f"{fichier} : « {TITRE_SKILL} » ne contient aucune phrase `- « … »`"
            resultat[nom.group(1)] = phrases
    return resultat


def lignes_du_manuel() -> dict[str, str]:
    """Ligne du tableau du manuel pour chaque skill nommé dans sa dernière colonne."""
    section = _section(MANUEL.read_text(encoding="utf-8"), rf"## \d+\. {re.escape(TITRE_MANUEL)}")
    assert section is not None, f"Section « {TITRE_MANUEL} » absente de MANUEL.md"
    lignes = {}
    for ligne in section.splitlines():
        m = re.fullmatch(r"\|.*\|\s*`([a-z0-9-]+)`\s*\|", ligne.strip())
        if m:
            assert m.group(1) not in lignes, f"Skill `{m.group(1)}` listé deux fois dans le manuel"
            lignes[m.group(1)] = ligne
    return lignes


def test_au_moins_un_skill_a_des_phrases():
    assert phrases_des_skills()


def test_le_manuel_liste_exactement_les_skills_a_phrases():
    skills, manuel = set(phrases_des_skills()), set(lignes_du_manuel())
    assert not skills - manuel, f"Skills absents de MANUEL.md (section « {TITRE_MANUEL} ») : {sorted(skills - manuel)}"
    assert not manuel - skills, f"Skills du manuel sans section « {TITRE_SKILL} » (ou supprimés) : {sorted(manuel - skills)}"


def test_le_manuel_reprend_chaque_phrase_mot_pour_mot():
    lignes = lignes_du_manuel()
    manquantes = [
        f"{nom} : « {phrase} »"
        for nom, phrases in phrases_des_skills().items()
        for phrase in phrases
        if nom in lignes and f"« {phrase} »" not in lignes[nom]
    ]
    assert not manquantes, f"Phrases absentes de leur ligne dans MANUEL.md : {manquantes}"


def test_le_manuel_ne_cite_pas_de_phrase_retiree_du_skill():
    phrases = phrases_des_skills()
    en_trop = [
        f"{nom} : « {cite} »"
        for nom, ligne in lignes_du_manuel().items()
        for cite in re.findall(r"« (.+?) »", ligne)
        if cite not in phrases.get(nom, [])
    ]
    assert not en_trop, f"Phrases du manuel absentes du skill : {en_trop}"
