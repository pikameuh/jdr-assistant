import pytest

from agent_jdr.core.persona import (
    DOSSIER_PERSONAS,
    PersonaInvalide,
    charger_persona,
    charger_personas,
)

FICHE_MINIMALE = """\
id: {id}
nom: Test
espece: Humain
origine: Station
role: Barman
personnalite: Calme
parole:
  registre: Soutenu
objectifs: [Servir]
attitude_envers_pj: Neutre
"""


def ecrire(dossier, nom, contenu):
    chemin = dossier / f"{nom}.yaml"
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_toutes_les_fiches_livrees_sont_valides():
    personas = charger_personas()
    assert "orla-venn" in personas
    assert all(p.id == i for i, p in personas.items())


def test_exemple_contient_secrets_avec_et_sans_condition():
    orla = charger_persona(DOSSIER_PERSONAS / "orla-venn.yaml")
    conditions = [s.condition_revelation for s in orla.secrets]
    assert None in conditions and any(conditions)


def test_fiche_minimale(tmp_path):
    p = charger_persona(ecrire(tmp_path, "barman", FICHE_MINIMALE.format(id="barman")))
    assert p.secrets == () and p.parole.tics == ()


def test_champ_manquant(tmp_path):
    contenu = FICHE_MINIMALE.format(id="barman").replace("role: Barman\n", "")
    with pytest.raises(PersonaInvalide, match="role"):
        charger_persona(ecrire(tmp_path, "barman", contenu))


def test_champ_inconnu_refuse(tmp_path):
    contenu = FICHE_MINIMALE.format(id="barman") + "force: 12\n"
    with pytest.raises(PersonaInvalide, match="force"):
        charger_persona(ecrire(tmp_path, "barman", contenu))


def test_objectifs_obligatoires(tmp_path):
    contenu = FICHE_MINIMALE.format(id="barman").replace("[Servir]", "[]")
    with pytest.raises(PersonaInvalide, match="objectifs"):
        charger_persona(ecrire(tmp_path, "barman", contenu))


def test_texte_vide_refuse(tmp_path):
    contenu = FICHE_MINIMALE.format(id="barman").replace("Calme", '"  "')
    with pytest.raises(PersonaInvalide, match="personnalite"):
        charger_persona(ecrire(tmp_path, "barman", contenu))


def test_id_doit_correspondre_au_fichier(tmp_path):
    with pytest.raises(PersonaInvalide, match="nom du fichier"):
        charger_persona(ecrire(tmp_path, "autre", FICHE_MINIMALE.format(id="barman")))


@pytest.mark.parametrize("id_", ["Barman", "bar man", "barman-"])
def test_id_format(tmp_path, id_):
    with pytest.raises(PersonaInvalide, match=r"id : String should match pattern"):
        charger_persona(ecrire(tmp_path, id_, FICHE_MINIMALE.format(id=f'"{id_}"')))


def test_yaml_non_dictionnaire(tmp_path):
    with pytest.raises(PersonaInvalide, match="dictionnaire"):
        charger_persona(ecrire(tmp_path, "barman", "- a\n- b\n"))


def test_yaml_mal_forme(tmp_path):
    with pytest.raises(PersonaInvalide, match="lecture impossible"):
        charger_persona(ecrire(tmp_path, "barman", "nom: [ouvert\n"))
