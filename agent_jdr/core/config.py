"""Configuration : lecture et validation de `config.yaml` (racine du projet).

Toute la configuration réglable à la main vit dans ce fichier : aucune valeur
par défaut cachée dans le code. Le cœur reçoit ses réglages en paramètre ; seules
les commandes (CLI) lisent le fichier.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

RACINE = Path(__file__).resolve().parents[2]
CONFIG_DEFAUT = RACINE / "config.yaml"

# Nom affiché dans config.yaml → valeur `effort` de l'API (None = non envoyé).
NIVEAUX_DE_REFLEXION: dict[str, str | None] = {
    "defaut": None,
    "bas": "low",
    "moyen": "medium",
    "eleve": "high",
    "tres_eleve": "xhigh",
    "maximum": "max",
}
NiveauDeReflexion = Literal["defaut", "bas", "moyen", "eleve", "tres_eleve", "maximum"]


class ConfigInvalide(ValueError):
    """Fichier de configuration illisible ou non conforme."""


def _message_en_francais(err: dict[str, Any]) -> str:
    """Erreur de validation pydantic → phrase compréhensible sans connaître Python."""
    ctx = err.get("ctx", {})
    match err["type"]:
        case "missing":
            return "réglage manquant"
        case "extra_forbidden":
            return "réglage inconnu (faute de frappe ?)"
        case "literal_error":
            return f"valeur non permise ; choix possibles : {str(ctx.get('expected')).replace(' or ', ' ou ')}"
        case "string_pattern_mismatch":
            return "nom de modèle incorrect (il doit commencer par « claude- »)"
        case "greater_than_equal":
            return f"doit être au moins {ctx.get('ge')}"
        case "less_than_equal":
            return f"doit être au plus {ctx.get('le')}"
        case "int_parsing" | "int_type" | "int_from_float":
            return "doit être un nombre entier"
        case "string_too_short":
            return "ne doit pas être vide"
        case "string_type" | "path_type":
            return "doit être un texte"
        case "model_type" | "dict_type":
            return "doit contenir des sous-réglages « nom: valeur »"
    return err["msg"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ReglagesModele(_Strict):
    modele: str = Field(pattern=r"^claude-[a-z0-9.-]+$")
    niveau_de_reflexion: NiveauDeReflexion
    longueur_max_reponse: int = Field(ge=1, le=128000)
    consignes: str = Field(min_length=1)

    def parametres_modele(self) -> dict[str, Any]:
        """Paramètres communs de `messages.create` : modèle, longueur, réflexion."""
        params: dict[str, Any] = {
            "model": self.modele,
            "max_tokens": self.longueur_max_reponse,
            "thinking": {"type": "adaptive"},
        }
        effort = NIVEAUX_DE_REFLEXION[self.niveau_de_reflexion]
        if effort:
            params["output_config"] = {"effort": effort}
        return params


class ReglagesDialogue(ReglagesModele):
    recherches_max_par_replique: int = Field(ge=1, le=20)
    passages_par_recherche: int = Field(ge=1, le=50)


class ReglagesQuestions(ReglagesModele):
    passages_envoyes: int = Field(ge=1, le=50)


class Fichiers(_Strict):
    index_des_regles: Path
    dossier_des_pnj: Path
    dossier_des_pdf: Path


class Config(_Strict):
    dialogue: ReglagesDialogue
    questions_de_regles: ReglagesQuestions
    fichiers: Fichiers


def charger_config(chemin: Path = CONFIG_DEFAUT) -> Config:
    """Lit et valide la configuration. Chemins relatifs = relatifs au dossier du fichier."""
    try:
        donnees = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    except OSError as e:
        raise ConfigInvalide(f"{chemin} : lecture impossible ({e.strerror})") from e
    except yaml.YAMLError as e:
        raise ConfigInvalide(f"{chemin.name} : syntaxe YAML incorrecte\n{e}") from e
    if not isinstance(donnees, dict):
        raise ConfigInvalide(f"{chemin.name} : le fichier doit contenir des sections « nom: valeur »")
    try:
        config = Config.model_validate(donnees)
    except ValidationError as e:
        details = "\n".join(
            f"  - {' > '.join(map(str, err['loc'])) or '(racine)'} : {_message_en_francais(err)}"
            for err in e.errors()
        )
        raise ConfigInvalide(f"{chemin.name} : réglages incorrects\n{details}") from e

    base = chemin.resolve().parent
    fichiers = config.fichiers.model_copy(
        update={nom: base / valeur for nom, valeur in config.fichiers if not valeur.is_absolute()}
    )
    return config.model_copy(update={"fichiers": fichiers})
