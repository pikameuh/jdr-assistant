"""Configuration de test, indépendante de `config.yaml` (que l'utilisateur modifie à la main)."""

from agent_jdr.core.config import Config

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
        "fichiers": {
            "index_des_regles": "/inexistant/rules.db",
            "dossier_des_pnj": "/inexistant/personas",
            "dossier_des_pdf": "/inexistant/pdf",
        },
    }
)
