"""Sessions de dialogue persistantes : un PNJ, un PJ, une scène et l'historique des échanges.

Une session = un fichier JSON dans le dossier `fichiers.dossier_des_sessions`.
Le cœur ne sait rien de l'IHM : la CLI comme le web peuvent s'en servir.
"""

from __future__ import annotations

import re
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agent_jdr.core.config import ReglagesDialogue
from agent_jdr.core.dialogue_engine import MoteurDialogue, Replique
from agent_jdr.core.fournisseurs.base import Fournisseur
from agent_jdr.core.persona import Persona
from agent_jdr.core.prompt_builder import Tour
from agent_jdr.core.rules_index import RulesIndex
from agent_jdr.core.scene import Scene

_ID = re.compile(r"^[0-9a-f]{32}$")


class SessionInconnue(LookupError):
    """Aucune session avec cet identifiant."""


class TourEnregistre(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    locuteur: Literal["joueur", "pnj"]
    texte: str
    pj: str | None = None
    regles: tuple[str, ...] = Field(default=(), description="Références des règles consultées (PNJ)")


class SessionDialogue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=_ID.pattern)
    persona: str
    pj: str = Field(min_length=1)
    scene: Scene
    historique: tuple[TourEnregistre, ...] = ()
    cree_le: datetime
    modifie_le: datetime

    def tours(self) -> list[Tour]:
        return [Tour(t.locuteur, t.texte, pj=t.pj) for t in self.historique]

    def _modifiee(self, **champs: object) -> SessionDialogue:
        return self.model_copy(update={**champs, "modifie_le": _maintenant()})

    def avec_fait(self, fait: str) -> SessionDialogue:
        return self._modifiee(scene=self.scene.avec_fait(fait))

    def sans_historique(self) -> SessionDialogue:
        """Même session (PNJ, PJ, scène et faits), historique des échanges effacé."""
        return self._modifiee(historique=())


def _maintenant() -> datetime:
    return datetime.now(UTC)


def nouvelle_session(persona: Persona, pj: str, scene: Scene) -> SessionDialogue:
    maintenant = _maintenant()
    return SessionDialogue(
        id=uuid.uuid4().hex, persona=persona.id, pj=pj.strip(), scene=scene,
        cree_le=maintenant, modifie_le=maintenant,
    )


def jouer_tour(
    session: SessionDialogue,
    persona: Persona,
    index: RulesIndex,
    reglages: ReglagesDialogue,
    fournisseur: Fournisseur,
    texte: str,
) -> tuple[SessionDialogue, Replique]:
    """Fait répondre le PNJ au joueur. En cas d'erreur, rien n'est ajouté à la session."""
    if persona.id != session.persona:
        raise ValueError(f"La session concerne « {session.persona} », pas « {persona.id} »")
    moteur = MoteurDialogue(persona, session.scene, index, reglages, fournisseur, session.tours())
    replique = moteur.repondre(texte, pj=session.pj)
    ajout = (
        TourEnregistre(locuteur="joueur", texte=texte.strip(), pj=session.pj),
        TourEnregistre(
            locuteur="pnj",
            texte=replique.texte,
            regles=tuple(p.reference() for p in replique.regles_consultees),
        ),
    )
    return session._modifiee(historique=(*session.historique, *ajout)), replique


class DepotSessions:
    """Sessions enregistrées dans un dossier, un fichier JSON par session."""

    def __init__(self, dossier: Path) -> None:
        self.dossier = dossier
        self._verrous: dict[str, threading.Lock] = {}
        self._verrou_global = threading.Lock()

    def _chemin(self, id_session: str) -> Path:
        if not _ID.match(id_session):
            raise SessionInconnue(id_session)
        return self.dossier / f"{id_session}.json"

    @contextmanager
    def verrou(self, id_session: str) -> Iterator[None]:
        """Empêche deux modifications simultanées d'une même session (lecture → écriture)."""
        with self._verrou_global:
            verrou = self._verrous.setdefault(id_session, threading.Lock())
        with verrou:
            yield

    def lister(self) -> list[SessionDialogue]:
        """Sessions lisibles, la plus récemment modifiée d'abord (fichiers illisibles ignorés)."""
        sessions = []
        for chemin in self.dossier.glob("*.json"):
            try:
                sessions.append(SessionDialogue.model_validate_json(chemin.read_text(encoding="utf-8")))
            except (OSError, ValidationError):
                continue
        return sorted(sessions, key=lambda s: s.modifie_le, reverse=True)

    def lire(self, id_session: str) -> SessionDialogue:
        chemin = self._chemin(id_session)
        try:
            texte = chemin.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise SessionInconnue(id_session) from e
        return SessionDialogue.model_validate_json(texte)

    def enregistrer(self, session: SessionDialogue) -> None:
        chemin = self._chemin(session.id)
        self.dossier.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_suffix(".tmp")
        temporaire.write_text(session.model_dump_json(indent=2), encoding="utf-8")
        temporaire.replace(chemin)

    def supprimer(self, id_session: str) -> None:
        try:
            self._chemin(id_session).unlink()
        except FileNotFoundError as e:
            raise SessionInconnue(id_session) from e
