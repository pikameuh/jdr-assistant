"""Fiches PNJ : schéma validé et chargement depuis YAML.

Une fiche par fichier `<id>.yaml`, dans le dossier `fichiers.dossier_des_pnj` de la configuration. Contenu narratif uniquement :
les valeurs chiffrées du jeu restent dans les livres de règles.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

Texte = Field(min_length=1)


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
    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
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
