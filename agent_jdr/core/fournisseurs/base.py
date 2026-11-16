"""Interface commune aux fournisseurs de modèles (Anthropic, OpenAI).

Le cœur (moteur de dialogue, questions de règles) ne parle qu'à cette interface ;
seuls les modules `fournisseur_*.py` importent un SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from agent_jdr.core.rules_index import Passage
    from agent_jdr.core.rules_qa import Reponse

MESSAGE_REFUS = "Le modèle a refusé de répondre."
MESSAGE_TRONQUE = "Réponse tronquée : limite de longueur atteinte."


class IdentifiantsAbsents(RuntimeError):
    """Aucune clé API utilisable (absente ou refusée)."""


class ReponseIncomplete(RuntimeError):
    """Le modèle n'a pas produit de réponse complète (refus, limite de longueur…)."""


class ErreurFournisseur(RuntimeError):
    """Erreur renvoyée par l'API du fournisseur (réseau, crédit, modèle inconnu…)."""


@dataclass(frozen=True)
class DefinitionOutil:
    nom: str
    description: str
    schema: dict[str, Any]  # schéma JSON des paramètres (mode strict)


@dataclass(frozen=True)
class AppelOutil:
    id: str
    nom: str
    entree: Any  # paramètres décodés ; None si le modèle a envoyé un JSON illisible


@dataclass(frozen=True)
class ResultatOutil:
    id: str
    contenu: tuple[str, ...]
    erreur: bool = False


@dataclass(frozen=True)
class Etape:
    """Réponse du modèle à un appel : du texte, et éventuellement des appels d'outils."""

    texte: str
    appels: tuple[AppelOutil, ...] = ()


class SessionOutils(Protocol):
    """Conversation en cours avec outils. Garde l'historique brut propre au fournisseur
    (blocs de réflexion, éléments de raisonnement) entre deux appels."""

    def envoyer(self) -> Etape: ...

    def ajouter_resultats(self, resultats: list[ResultatOutil]) -> None: ...


class Fournisseur(Protocol):
    def session_outils(
        self,
        stable: str,
        variable: str,
        messages: list[dict[str, str]],
        outils: list[DefinitionOutil],
    ) -> SessionOutils:
        """`stable` : consignes + persona (identique d'une scène à l'autre, mis en cache) ;
        `variable` : la scène ; `messages` : historique `{"role", "content"}`."""
        ...

    def repondre_avec_sources(
        self, consignes: str, passages: list[Passage], question: str
    ) -> Reponse: ...
