"""Fournisseur Anthropic (API Messages).

- Dialogue : réflexion adaptative, outil en mode strict, cache sur la partie
  stable (`system[0]`) et cache automatique en fin de conversation.
- Questions de règles : un bloc `document` par passage, citations natives.
"""

from __future__ import annotations

from typing import Any

import anthropic

from agent_jdr.core.config import ReglagesModele
from agent_jdr.core.fournisseurs.base import (
    MESSAGE_REFUS,
    MESSAGE_TRONQUE,
    AppelOutil,
    DefinitionOutil,
    ErreurFournisseur,
    Etape,
    IdentifiantsAbsents,
    ReponseIncomplete,
    ResultatOutil,
)
from agent_jdr.core.rules_index import Passage
from agent_jdr.core.rules_qa import Reponse, assembler_reponse

CACHE = {"type": "ephemeral"}


class FournisseurAnthropic:
    def __init__(
        self,
        reglages: ReglagesModele,
        client: anthropic.Anthropic | None = None,
        cle_api: str | None = None,
    ) -> None:
        self.reglages = reglages
        self._client = client
        self._cle_api = cle_api

    # --- Appel ------------------------------------------------------------------

    def parametres(self) -> dict[str, Any]:
        """Paramètres communs : modèle, longueur, réflexion."""
        params: dict[str, Any] = {
            "model": self.reglages.modele,
            "max_tokens": self.reglages.longueur_max_reponse,
            "thinking": {"type": "adaptive"},
        }
        if self.reglages.effort:
            params["output_config"] = {"effort": self.reglages.effort}
        return params

    def appeler(self, params: dict[str, Any]) -> Any:
        """`messages.create`, erreurs converties en erreurs communes, réponse vérifiée."""
        if self._client is None:
            self._client = (
                anthropic.Anthropic(api_key=self._cle_api) if self._cle_api else anthropic.Anthropic()
            )
        client = self._client
        try:
            message = client.messages.create(**params)
        except anthropic.AuthenticationError as e:
            raise IdentifiantsAbsents(f"Identifiants Anthropic refusés : {e.message}") from e
        except anthropic.APIError as e:
            raise ErreurFournisseur(f"API Anthropic : {e.message}") from e
        except TypeError as e:
            # Le SDK lève TypeError quand aucune méthode d'authentification n'est configurée.
            if "authentication method" not in str(e):
                raise
            raise IdentifiantsAbsents(
                "Aucun identifiant Anthropic trouvé : clé absente du fichier de secrets "
                "et variable ANTHROPIC_API_KEY non définie."
            ) from e
        if message.stop_reason == "refusal":
            raise ReponseIncomplete(MESSAGE_REFUS)
        if message.stop_reason == "max_tokens":
            raise ReponseIncomplete(MESSAGE_TRONQUE)
        return message

    # --- Dialogue avec outils ------------------------------------------------------

    def session_outils(
        self,
        stable: str,
        variable: str,
        messages: list[dict[str, str]],
        outils: list[DefinitionOutil],
    ) -> _SessionAnthropic:
        fixes = {
            **self.parametres(),
            "cache_control": CACHE,
            "tools": [
                {"name": o.nom, "description": o.description, "input_schema": o.schema, "strict": True}
                for o in outils
            ],
            "system": [
                {"type": "text", "text": stable, "cache_control": CACHE},
                {"type": "text", "text": variable},
            ],
        }
        return _SessionAnthropic(self, fixes, list(messages))

    # --- Questions de règles ---------------------------------------------------------

    def repondre_avec_sources(self, consignes: str, passages: list[Passage], question: str) -> Reponse:
        message = self.appeler(construire_requete(self.parametres(), consignes, passages, question))
        return lire_reponse(message, passages)


class _SessionAnthropic:
    def __init__(self, fournisseur: FournisseurAnthropic, fixes: dict[str, Any], messages: list[Any]) -> None:
        self._fournisseur = fournisseur
        self._fixes = fixes
        self._messages = messages
        self._dernier: Any = None

    def envoyer(self) -> Etape:
        message = self._fournisseur.appeler({**self._fixes, "messages": self._messages})
        self._dernier = message
        texte = "".join(b.text for b in message.content if b.type == "text")
        if message.stop_reason != "tool_use":
            return Etape(texte)
        appels = tuple(
            AppelOutil(b.id, b.name, b.input if isinstance(b.input, dict) else None)
            for b in message.content
            if b.type == "tool_use"
        )
        return Etape(texte, appels)

    def ajouter_resultats(self, resultats: list[ResultatOutil]) -> None:
        blocs = []
        for r in resultats:
            bloc: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": r.id,
                "content": [{"type": "text", "text": t} for t in r.contenu],
            }
            if r.erreur:
                bloc["is_error"] = True
            blocs.append(bloc)
        # Contenu renvoyé tel quel (blocs de réflexion compris), puis tous les résultats.
        self._messages = [
            *self._messages,
            {"role": "assistant", "content": self._dernier.content},
            {"role": "user", "content": blocs},
        ]


def construire_requete(
    parametres: dict[str, Any], consignes: str, passages: list[Passage], question: str
) -> dict[str, Any]:
    """Paramètres de `messages.create` : un document par passage, puis la question."""
    documents = [
        {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": p.texte},
            "title": p.reference(),
            "citations": {"enabled": True},
        }
        for p in passages
    ]
    return {
        **parametres,
        "system": consignes,
        "messages": [{"role": "user", "content": [*documents, {"type": "text", "text": question}]}],
    }


def lire_reponse(message: Any, passages: list[Passage]) -> Reponse:
    """Message de l'API → Reponse, à partir des citations natives."""
    blocs = [
        (bloc.text, [(c.document_index, c.cited_text) for c in bloc.citations or []])
        for bloc in message.content
        if bloc.type == "text"  # blocs de réflexion : non affichés
    ]
    return assembler_reponse(blocs, passages)
