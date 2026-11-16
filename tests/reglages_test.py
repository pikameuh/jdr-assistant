"""Configuration de test, indépendante de `config.yaml` (que l'utilisateur modifie à la main)."""

from pathlib import Path

import yaml

from agent_jdr.core.config import CONFIG_DEFAUT, Config
from agent_jdr.core.rules_index import LIVRES_CONNUS

CONSIGNES_DIALOGUE = "Consignes de dialogue de test."
CONSIGNES_REGLES = "Consignes de règles de test."

CONFIG_TEST = Config.model_validate(
    {
        "dialogue": {
            "fournisseur": "anthropic",
            "modele": "claude-test-dialogue",
            "niveau_de_reflexion": "defaut",
            "longueur_max_reponse": 1000,
            "recherches_max_par_replique": 3,
            "passages_par_recherche": 5,
            "consignes": CONSIGNES_DIALOGUE,
        },
        "questions_de_regles": {
            "fournisseur": "anthropic",
            "modele": "claude-test-regles",
            "niveau_de_reflexion": "defaut",
            "longueur_max_reponse": 2000,
            "passages_envoyes": 8,
            "consignes": CONSIGNES_REGLES,
        },
        "regles": {"livres_utilises": ["MA - Manuel des joueurs 1.5.pdf", "MA - Guide du Meneur 1.5.pdf"]},
        "fichiers": {
            "index_des_regles": "/inexistant/rules.db",
            "dossier_des_pnj": "/inexistant/personas",
            "dossier_des_pdf": "/inexistant/pdf",
            "secrets": "/inexistant/secrets.yaml",
            "dossier_des_sessions": "/inexistant/sessions",
            "historique_des_recherches": "/inexistant/historique",
            "catalogue_des_modeles": "/inexistant/modeles.yaml",
            "modele_de_pnj": "/inexistant/modele_pnj.yaml",
        },
    }
)


def ecrire_config(dossier: Path, secrets: dict | None = None, **sections: dict) -> Path:
    """Copie de config.yaml dans `dossier`, chemins absolus vers le projet, sauf le fichier
    de secrets : `dossier/secrets.yaml`, écrit seulement si `secrets` est donné, et de
    l'historique des recherches : `dossier/historique`. Ainsi les tests des commandes ne
    lisent jamais le vrai secrets.yaml et n'écrivent jamais dans le vrai historique. `sections` : réglages modifiés."""
    donnees = yaml.safe_load(CONFIG_DEFAUT.read_text(encoding="utf-8"))
    racine = CONFIG_DEFAUT.parent
    donnees["fichiers"] = {k: str(racine / v) for k, v in donnees["fichiers"].items()}
    donnees["fichiers"]["secrets"] = str(dossier / "secrets.yaml")
    # Ce que les commandes écrivent d'elles-mêmes reste dans le dossier du test.
    donnees["fichiers"]["historique_des_recherches"] = str(dossier / "historique")
    # Les livres cochés par l'utilisateur (onglet Livres) n'influencent pas les tests.
    donnees["regles"] = {"livres_utilises": list(LIVRES_CONNUS)}
    if secrets is not None:
        (dossier / "secrets.yaml").write_text(yaml.safe_dump(secrets), encoding="utf-8")
    for nom, maj in sections.items():
        donnees[nom].update(maj)
    chemin = dossier / "config.yaml"
    chemin.write_text(yaml.safe_dump(donnees, allow_unicode=True), encoding="utf-8")
    return chemin
