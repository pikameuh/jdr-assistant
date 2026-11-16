"""Fiches PNJ : schéma validé et chargement depuis YAML.

Une fiche par fichier `<id>.yaml`, dans le dossier `fichiers.dossier_des_pnj` de la configuration. Contenu narratif uniquement :
les valeurs chiffrées du jeu restent dans les livres de règles.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

Texte = Field(min_length=1)
MOTIF_ID = r"^[a-z0-9]+(-[a-z0-9]+)*$"  # identifiant = nom du fichier


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class Parole(_Strict):
    """Manière de parler du PNJ."""

    registre: str = Texte
    tics: tuple[str, ...] = ()
    exemples: tuple[str, ...] = Field(default=(), description="Répliques types")


class Secret(_Strict):
    contenu: str = Texte
    condition_revelation: str | None = Field(
        default=None, description="Seule circonstance où le PNJ le révèle ; aucune = jamais"
    )


class Persona(_Strict):
    id: str = Field(pattern=MOTIF_ID)
    nom: str = Texte
    espece: str = Texte
    origine: str = Texte
    role: str = Texte
    personnalite: str = Texte
    parole: Parole
    objectifs: tuple[str, ...] = Field(min_length=1)
    connaissances: tuple[str, ...] = ()
    secrets: tuple[Secret, ...] = ()
    attitude_envers_pj: str = Texte


class PersonaInvalide(ValueError):
    """Fiche PNJ illisible ou non conforme au schéma."""


class PersonaInconnu(LookupError):
    """Aucune fiche PNJ avec cet identifiant."""


def charger_persona(chemin: Path) -> Persona:
    try:
        donnees = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        raise PersonaInvalide(f"{chemin.name} : lecture impossible ({e})") from e
    if not isinstance(donnees, dict):
        raise PersonaInvalide(f"{chemin.name} : la fiche doit être un dictionnaire YAML")
    try:
        persona = Persona.model_validate(donnees)
    except ValidationError as e:
        details = "; ".join(
            f"{'.'.join(map(str, err['loc'])) or '(racine)'} : {err['msg']}" for err in e.errors()
        )
        raise PersonaInvalide(f"{chemin.name} : {details}") from e
    if persona.id != chemin.stem:
        raise PersonaInvalide(
            f"{chemin.name} : l'id « {persona.id} » doit correspondre au nom du fichier"
        )
    return persona


def charger_personas(dossier: Path) -> dict[str, Persona]:
    """Toutes les fiches `*.yaml` du dossier, indexées par id."""
    return {p.stem: charger_persona(p) for p in sorted(dossier.glob("*.yaml"))}


# --- Création d'une fiche (interface web) ------------------------------------------

LIBELLES_CHAMPS = {
    "id": "Identifiant", "nom": "Nom", "espece": "Espèce", "origine": "Origine", "role": "Rôle",
    "personnalite": "Personnalité", "parole": "Parole", "registre": "Registre", "tics": "Tics",
    "exemples": "Exemples de répliques", "objectifs": "Objectifs", "connaissances": "Connaissances",
    "secrets": "Secrets", "contenu": "Contenu", "condition_revelation": "Condition de révélation",
    "attitude_envers_pj": "Attitude envers les PJ",
}


class FicheRefusee(PersonaInvalide):
    """Fiche saisie non conforme ; `erreurs` : chemin du champ (« parole.registre », « secrets.0.contenu ») → message."""

    def __init__(self, erreurs: dict[str, str]) -> None:
        self.erreurs = erreurs
        super().__init__("Fiche incomplète ou incorrecte :\n" + "\n".join(
            f"  - {_libelle(champ)} : {message}" for champ, message in erreurs.items()
        ))


def _libelle(champ: str) -> str:
    morceaux = []
    for m in champ.split("."):
        morceaux.append(f"n° {int(m) + 1}" if m.isdigit() else LIBELLES_CHAMPS.get(m, m))
    return " > ".join(morceaux)


def _message(err: dict) -> str:
    match err["type"]:
        case "missing" | "string_too_short":
            return "à remplir"
        case "too_short":
            return "au moins un élément"
        case "string_pattern_mismatch":
            return "minuscules sans accents, chiffres et tirets entre les mots (ex. capitaine-rook)"
        case "extra_forbidden":
            return "champ inconnu"
        case "string_type":
            return "doit être un texte"
    return err["msg"]


def _nettoyer(valeur):
    """Retire les textes vides et éléments vides des listes (lignes laissées blanches dans le formulaire)."""
    if isinstance(valeur, dict):
        propre = {k: _nettoyer(v) for k, v in valeur.items()}
        return {k: v for k, v in propre.items() if v not in (None, "", [])}
    if isinstance(valeur, list):
        return [v for v in (_nettoyer(x) for x in valeur) if v not in (None, "", [], {})]
    if isinstance(valeur, str):
        return valeur.strip()
    return valeur


def valider_fiche(donnees: object) -> Persona:
    """Fiche saisie (dictionnaire) → Persona, avec des messages en français par champ."""
    if not isinstance(donnees, dict):
        raise FicheRefusee({"(fiche)": "doit être un dictionnaire"})
    donnees = _nettoyer(donnees)
    donnees.setdefault("parole", {})  # erreur rattachée au registre, champ visible du formulaire
    secrets = donnees.get("secrets")
    if isinstance(secrets, list):  # un secret sans contenu (seulement une condition) est une erreur visible
        for i, s in enumerate(secrets):
            if isinstance(s, dict) and "contenu" not in s:
                raise FicheRefusee({f"secrets.{i}.contenu": "à remplir (ou supprimez ce secret)"})
    try:
        return Persona.model_validate(donnees)
    except ValidationError as e:
        erreurs: dict[str, str] = {}
        for err in e.errors():
            erreurs.setdefault(".".join(map(str, err["loc"])) or "(fiche)", _message(err))
        raise FicheRefusee(erreurs) from e


def fiche_en_yaml(persona: Persona, origine: str = "créée") -> str:
    donnees = persona.model_dump(mode="json", exclude_defaults=True)
    for secret in donnees.get("secrets", []):
        if secret.get("condition_revelation") is None:
            secret.pop("condition_revelation", None)
    corps = yaml.safe_dump(donnees, allow_unicode=True, sort_keys=False, width=10_000)
    return f"# Fiche PNJ {origine} depuis l'interface web.\n{corps}"


def creer_fiche(dossier: Path, donnees: object) -> Persona:
    """Valide puis écrit `<id>.yaml` dans `dossier`. Une fiche existante n'est jamais écrasée."""
    persona = valider_fiche(donnees)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{persona.id}.yaml"
    try:
        with chemin.open("x", encoding="utf-8") as f:  # "x" : échoue si le fichier existe
            f.write(fiche_en_yaml(persona))
    except FileExistsError as e:
        raise FicheRefusee({"id": f"un PNJ « {persona.id} » existe déjà ; choisissez un autre identifiant"}) from e
    return persona


def modifier_fiche(dossier: Path, id_persona: str, donnees: object) -> Persona:
    """Valide puis remplace la fiche `<id_persona>.yaml`, qui doit exister.

    L'identifiant ne change pas (c'est le nom du fichier, et les sessions y font
    référence). Le fichier est réécrit à partir des champs : les commentaires d'une
    fiche écrite à la main ne sont pas conservés.
    """
    chemin = dossier / f"{id_persona}.yaml"
    if not re.fullmatch(MOTIF_ID, id_persona) or not chemin.is_file():
        raise PersonaInconnu(id_persona)
    if isinstance(donnees, dict):
        donnees = {**donnees}
        if donnees.get("id", id_persona) not in ("", id_persona):
            raise FicheRefusee({"id": "l'identifiant d'un PNJ existant ne peut pas changer (les sessions y font référence)"})
        donnees["id"] = id_persona
    persona = valider_fiche(donnees)
    temporaire = chemin.with_name(f".{chemin.name}.tmp")
    temporaire.write_text(fiche_en_yaml(persona, "modifiée"), encoding="utf-8")
    os.replace(temporaire, chemin)
    return persona


def charger_modele_de_fiche(chemin: Path) -> dict:
    """Modèle pré-rempli proposé à la création d'un PNJ (pas validé : c'est un point de départ)."""
    try:
        donnees = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        raise PersonaInvalide(f"Modèle de fiche PNJ illisible ({chemin.name}) : {e}") from e
    if not isinstance(donnees, dict):
        raise PersonaInvalide(f"Modèle de fiche PNJ ({chemin.name}) : doit être un dictionnaire YAML")
    return donnees
