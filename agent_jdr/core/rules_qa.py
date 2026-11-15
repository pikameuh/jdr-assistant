"""Réponse aux questions de règles, avec sources vérifiables.

Question → recherche FTS5 (top-N passages) → un appel Claude → réponse + sources.

Traçabilité : chaque passage est envoyé comme bloc `document` texte avec les
citations natives de l'API activées. Les sources affichées sont les citations
renvoyées par l'API (texte cité exact + passage d'origine), jamais une liste
rédigée par le modèle.

Cœur sans IHM : réutilisable par la CLI comme par le futur back-end web.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import anthropic

from agent_jdr.core.config import ReglagesQuestions
from agent_jdr.core.rules_index import Passage, RulesIndex

MESSAGE_AUCUN_PASSAGE = "Aucun passage des règles ne correspond à cette question."


class IdentifiantsAbsents(RuntimeError):
    """Aucun identifiant Anthropic utilisable (clé API absente ou refusée)."""


class ReponseIncomplete(RuntimeError):
    """L'API n'a pas produit de réponse complète (refus, limite de longueur…)."""


@dataclass(frozen=True)
class Source:
    """Passage effectivement cité dans la réponse, avec les extraits exacts cités."""

    passage: Passage
    extraits: tuple[str, ...]


@dataclass(frozen=True)
class Segment:
    """Morceau de la réponse ; `sources` = numéros (1-based) des sources qui l'appuient."""

    texte: str
    sources: tuple[int, ...] = ()


@dataclass(frozen=True)
class Reponse:
    segments: tuple[Segment, ...]
    sources: tuple[Source, ...]
    passages_fournis: tuple[Passage, ...]

    @property
    def texte(self) -> str:
        return "".join(s.texte for s in self.segments)


# --- Requête ----------------------------------------------------------------------


def construire_requete(
    question: str, passages: list[Passage], reglages: ReglagesQuestions
) -> dict[str, Any]:
    """Paramètres de `client.messages.create` : un document par passage, puis la question."""
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
        **reglages.parametres_modele(),
        "system": reglages.consignes,
        "messages": [
            {"role": "user", "content": [*documents, {"type": "text", "text": question}]}
        ],
    }


# --- Lecture de la réponse --------------------------------------------------------


def lire_reponse(message: Any, passages: list[Passage]) -> Reponse:
    """Message de l'API → Reponse. Les sources sont tirées des citations, dédoublonnées par passage."""
    if message.stop_reason == "refusal":
        raise ReponseIncomplete("Le modèle a refusé de répondre à cette question.")
    if message.stop_reason == "max_tokens":
        raise ReponseIncomplete("Réponse tronquée : limite de longueur atteinte.")

    ordre: list[int] = []  # index de document, dans l'ordre de première citation
    extraits: dict[int, list[str]] = {}
    segments: list[Segment] = []
    for bloc in message.content:
        if bloc.type != "text":
            continue  # blocs de réflexion : non affichés
        numeros: list[int] = []
        for citation in bloc.citations or []:
            i = citation.document_index
            if not 0 <= i < len(passages):
                raise ValueError(f"Citation vers un document inexistant : index {i}")
            if i not in extraits:
                ordre.append(i)
                extraits[i] = []
            texte_cite = citation.cited_text.strip()
            if texte_cite and texte_cite not in extraits[i]:
                extraits[i].append(texte_cite)
            numero = ordre.index(i) + 1
            if numero not in numeros:
                numeros.append(numero)
        segments.append(Segment(bloc.text, tuple(numeros)))

    sources = tuple(Source(passages[i], tuple(extraits[i])) for i in ordre)
    return Reponse(tuple(segments), sources, tuple(passages))


# --- Orchestration ----------------------------------------------------------------


def repondre(
    question: str,
    index: RulesIndex,
    reglages: ReglagesQuestions,
    client: anthropic.Anthropic | None = None,
    limite: int | None = None,
) -> Reponse:
    """Recherche les passages pertinents puis fait rédiger la réponse par le modèle.

    Sans passage trouvé, aucun appel au modèle n'est fait. `limite` remplace
    ponctuellement `reglages.passages_envoyes`.
    """
    passages = [r.passage for r in index.rechercher(question, limite or reglages.passages_envoyes)]
    if not passages:
        return Reponse((Segment(MESSAGE_AUCUN_PASSAGE),), (), ())

    message = appeler_api(client or anthropic.Anthropic(), construire_requete(question, passages, reglages))
    return lire_reponse(message, passages)


def _identifiants_absents(e: TypeError) -> Exception:
    # Le SDK lève TypeError quand aucune méthode d'authentification n'est configurée.
    if "authentication method" not in str(e):
        return e
    return IdentifiantsAbsents(
        "Aucun identifiant Anthropic trouvé. Définir la variable ANTHROPIC_API_KEY "
        "(ou se connecter avec `ant auth login`)."
    )


def appeler_api(client: anthropic.Anthropic, params: dict[str, Any]) -> Any:
    """`client.messages.create(**params)`, erreurs d'identifiants converties en `IdentifiantsAbsents`."""
    try:
        return client.messages.create(**params)
    except anthropic.AuthenticationError as e:
        raise IdentifiantsAbsents(f"Identifiants Anthropic refusés : {e.message}") from e
    except TypeError as e:
        converti = _identifiants_absents(e)
        if converti is e:
            raise
        raise converti from e


# --- Rendu texte ------------------------------------------------------------------


def formater_reponse(reponse: Reponse) -> str:
    """Réponse avec renvois [n], puis la section « Sources » numérotée."""
    corps = "".join(
        s.texte + "".join(f" [{n}]" for n in s.sources) for s in reponse.segments
    ).strip()
    if not reponse.sources:
        return corps
    lignes = [corps, "", "Sources"]
    for n, source in enumerate(reponse.sources, 1):
        lignes.append(f"[{n}] {source.passage.reference()}")
        lignes.extend(f"    « {' '.join(e.split())} »" for e in source.extraits)
    return "\n".join(lignes)
