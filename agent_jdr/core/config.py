"""Configuration : lecture et validation de `config.yaml` (racine du projet).

Toute la configuration réglable à la main vit dans ce fichier : aucune valeur
par défaut cachée dans le code. Le cœur reçoit ses réglages en paramètre ; seules
les commandes (CLI) lisent le fichier.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator

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
NomFournisseur = Literal["anthropic", "openai"]


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
            return "nom de modèle incorrect (minuscules, chiffres, points et tirets seulement)"
        case "value_error":
            return str(ctx.get("error"))
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
        case "tuple_type" | "list_type":
            return "doit être une liste, ex. [\"Livre 1.pdf\", \"Livre 2.pdf\"]"
    return err["msg"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ReglagesModele(_Strict):
    fournisseur: NomFournisseur
    modele: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]*$")
    niveau_de_reflexion: NiveauDeReflexion
    longueur_max_reponse: int = Field(ge=1, le=128000)
    consignes: str = Field(min_length=1)

    @model_validator(mode="after")
    def _modele_du_bon_fournisseur(self) -> ReglagesModele:
        est_claude = self.modele.startswith("claude-")
        if self.fournisseur == "anthropic" and not est_claude:
            raise ValueError(
                f"le modèle « {self.modele} » n'est pas un modèle Anthropic "
                "(il doit commencer par « claude- ») ; vérifiez « fournisseur » et « modele »"
            )
        if self.fournisseur == "openai" and est_claude:
            raise ValueError(
                f"le modèle « {self.modele} » est un modèle Anthropic, pas OpenAI ; "
                "vérifiez « fournisseur » et « modele »"
            )
        return self

    @property
    def effort(self) -> str | None:
        """Valeur `effort` à envoyer à l'API (None = réglage standard du modèle)."""
        return NIVEAUX_DE_REFLEXION[self.niveau_de_reflexion]


class ReglagesDialogue(ReglagesModele):
    recherches_max_par_replique: int = Field(ge=1, le=20)
    passages_par_recherche: int = Field(ge=1, le=50)


class ReglagesQuestions(ReglagesModele):
    passages_envoyes: int = Field(ge=1, le=50)


class ReglagesRegles(_Strict):
    """Livres de règles utilisés par les recherches (questions de règles et dialogue)."""

    livres_utilises: tuple[str, ...]

    @model_validator(mode="after")
    def _noms_de_pdf(self) -> ReglagesRegles:
        for nom in self.livres_utilises:
            if not nom.lower().endswith(".pdf") or "/" in nom or "\\" in nom:
                raise ValueError(
                    f"« {nom} » : indiquez le nom d'un fichier PDF du dossier des livres (ex. « Mon livre.pdf »)"
                )
        if len(set(self.livres_utilises)) != len(self.livres_utilises):
            raise ValueError("un même livre est cité deux fois")
        return self


class Fichiers(_Strict):
    index_des_regles: Path
    dossier_des_pnj: Path
    dossier_des_pdf: Path
    secrets: Path
    dossier_des_sessions: Path
    historique_des_recherches: Path
    catalogue_des_modeles: Path
    modele_de_pnj: Path


class Config(_Strict):
    dialogue: ReglagesDialogue
    questions_de_regles: ReglagesQuestions
    regles: ReglagesRegles
    fichiers: Fichiers


class Secrets(_Strict):
    """Clés API du projet, par usage. Vide = repli sur la variable d'environnement du fournisseur."""

    model_config = ConfigDict(populate_by_name=True)

    cle_recherche: SecretStr | None = Field(default=None, alias="recherche-apikey")
    cle_personas: SecretStr | None = Field(default=None, alias="personas-apikey")

    @staticmethod
    def _valeur(cle: SecretStr | None) -> str | None:
        return (cle.get_secret_value().strip() or None) if cle else None

    @property
    def recherche(self) -> str | None:
        """Clé des questions de règles (`uv run search`)."""
        return self._valeur(self.cle_recherche)

    @property
    def personas(self) -> str | None:
        """Clé du dialogue avec les PNJ (`uv run parler`)."""
        return self._valeur(self.cle_personas)


# Nom de l'entrée du fichier de secrets pour chaque usage (affiché dans les messages).
ENTREE_SECRETS = {"questions_de_regles": "recherche-apikey", "dialogue": "personas-apikey"}


def conseil_cle(section: str, fichier: Path) -> str:
    """Où renseigner la clé d'un usage (affiché quand elle manque ou est refusée)."""
    return f"Renseignez la clé « {ENTREE_SECRETS[section]} » dans {fichier} (voir MANUEL.md, section 4)."


def _lire_texte(chemin: Path) -> str:
    try:
        return chemin.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigInvalide(f"{chemin} : lecture impossible ({e.strerror})") from e


def _analyser_yaml(texte: str, chemin: Path) -> Any:
    try:
        return yaml.safe_load(texte)
    except yaml.YAMLError as e:
        raise ConfigInvalide(f"{chemin.name} : syntaxe YAML incorrecte\n{e}") from e


def _lire_yaml(chemin: Path) -> Any:
    return _analyser_yaml(_lire_texte(chemin), chemin)


def _valider(modele: type[BaseModel], donnees: Any, chemin: Path, forme: str) -> Any:
    if not isinstance(donnees, dict):
        raise ConfigInvalide(f"{chemin.name} : le fichier doit contenir des {forme} « nom: valeur »")
    try:
        return modele.model_validate(donnees)
    except ValidationError as e:
        details = "\n".join(
            f"  - {' > '.join(map(str, err['loc'])) or '(racine)'} : {_message_en_francais(err)}"
            for err in e.errors()
        )
        raise ConfigInvalide(f"{chemin.name} : réglages incorrects\n{details}") from e


def charger_secrets(chemin: Path) -> Secrets:
    """Lit le fichier de secrets. Fichier absent ou vide = aucune clé (repli sur l'environnement)."""
    if not chemin.is_file():
        return Secrets()
    donnees = _lire_yaml(chemin)
    if donnees is None:
        return Secrets()
    return _valider(Secrets, donnees, chemin, "lignes")


def charger_config(chemin: Path = CONFIG_DEFAUT) -> Config:
    """Lit et valide la configuration. Chemins relatifs = relatifs au dossier du fichier."""
    return analyser_config(_lire_texte(chemin), chemin)


def analyser_config(texte: str, chemin: Path = CONFIG_DEFAUT) -> Config:
    """Valide le contenu `texte` d'un fichier de configuration situé (ou à écrire) en `chemin`."""
    config = _valider(Config, _analyser_yaml(texte, chemin), chemin, "sections")

    base = chemin.resolve().parent
    fichiers = config.fichiers.model_copy(
        update={nom: base / valeur for nom, valeur in config.fichiers if not valeur.is_absolute()}
    )
    return config.model_copy(update={"fichiers": fichiers})


# --- Catalogue des modèles (choix proposés par l'interface web) ---------------------


class ModeleCatalogue(_Strict):
    nom: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]*$")
    description: str = ""
    prix: str = ""


class Catalogue(_Strict):
    anthropic: tuple[ModeleCatalogue, ...] = Field(min_length=1)
    openai: tuple[ModeleCatalogue, ...] = Field(min_length=1)

    def modeles(self, fournisseur: str) -> tuple[ModeleCatalogue, ...]:
        return getattr(self, fournisseur)


def charger_catalogue(chemin: Path) -> Catalogue:
    """Liste des modèles proposés, par fournisseur (fichier `modeles.yaml`)."""
    catalogue = _valider(Catalogue, _lire_yaml(chemin), chemin, "sections")
    for fournisseur in ("anthropic", "openai"):
        for m in catalogue.modeles(fournisseur):
            if m.nom.startswith("claude-") != (fournisseur == "anthropic"):
                raise ConfigInvalide(
                    f"{chemin.name} : le modèle « {m.nom} » est rangé sous « {fournisseur} », "
                    "ce n'est pas le bon fournisseur"
                )
    return catalogue
