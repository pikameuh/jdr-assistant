"""Historique des questions de règles : une recherche = un fichier JSON.

Dossier : `fichiers.historique_des_recherches` de la configuration. Chaque entrée
garde la question et le résultat tel qu'affiché (réponse et sources, ou passages),
pour le rouvrir sans nouvel appel au modèle.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

_ID = re.compile(r"^[0-9a-f]{32}$")


class RechercheInconnue(LookupError):
    """Aucune recherche avec cet identifiant."""


class Recherche(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=_ID.pattern)
    date: datetime
    question: str = Field(min_length=1)
    mode: Literal["reponse", "passages"]  # réponse du modèle, ou passages seulement (sans modèle)
    resultat: dict[str, Any]

    def texte_cherchable(self) -> str:
        """Question, texte de la réponse et références des sources ou passages."""
        r = self.resultat
        morceaux = [self.question]
        morceaux += [s.get("texte", "") for s in r.get("segments", [])]
        morceaux += [s.get("reference", "") for s in (*r.get("sources", []), *r.get("passages", []))]
        return " ".join(morceaux)


def _normaliser(texte: str) -> str:
    """Minuscules sans accents, pour une recherche tolérante (« regle » trouve « Règle »)."""
    decompose = unicodedata.normalize("NFD", texte.casefold())
    return "".join(c for c in decompose if not unicodedata.combining(c))


class Historique:
    def __init__(self, dossier: Path) -> None:
        self.dossier = dossier

    def _chemin(self, id_recherche: str) -> Path:
        if not _ID.match(id_recherche):
            raise RechercheInconnue(id_recherche)
        return self.dossier / f"{id_recherche}.json"

    def ajouter(self, question: str, mode: Literal["reponse", "passages"], resultat: dict[str, Any]) -> Recherche:
        recherche = Recherche(
            id=uuid.uuid4().hex, date=datetime.now(UTC), question=question.strip(), mode=mode, resultat=resultat
        )
        self.dossier.mkdir(parents=True, exist_ok=True)
        chemin = self._chemin(recherche.id)
        temporaire = chemin.with_suffix(".tmp")
        temporaire.write_text(recherche.model_dump_json(indent=2), encoding="utf-8")
        temporaire.replace(chemin)
        return recherche

    def lister(self, filtre: str = "") -> list[Recherche]:
        """Recherches lisibles, la plus récente d'abord. `filtre` : tous les mots doivent apparaître
        (question, réponse ou références), sans tenir compte des accents ni des majuscules."""
        mots = _normaliser(filtre).split()
        resultats = []
        for chemin in self.dossier.glob("*.json"):
            try:
                r = Recherche.model_validate_json(chemin.read_text(encoding="utf-8"))
            except (OSError, ValidationError):
                continue  # fichier abîmé ou modifié à la main : ignoré
            texte = _normaliser(r.texte_cherchable())
            if all(m in texte for m in mots):
                resultats.append(r)
        return sorted(resultats, key=lambda r: r.date, reverse=True)

    def lire(self, id_recherche: str) -> Recherche:
        try:
            return Recherche.model_validate_json(self._chemin(id_recherche).read_text(encoding="utf-8"))
        except FileNotFoundError as e:
            raise RechercheInconnue(id_recherche) from e

    def supprimer(self, id_recherche: str) -> None:
        try:
            self._chemin(id_recherche).unlink()
        except FileNotFoundError as e:
            raise RechercheInconnue(id_recherche) from e

    def vider(self) -> int:
        """Supprime toutes les recherches ; renvoie leur nombre."""
        n = 0
        for chemin in self.dossier.glob("*.json"):
            if _ID.match(chemin.stem):
                chemin.unlink(missing_ok=True)
                n += 1
        return n
