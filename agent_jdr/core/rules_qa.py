"""Réponse aux questions de règles, avec sources vérifiables.

Question → recherche FTS5 (top-N passages) → un appel au modèle → réponse + sources.

Traçabilité : chaque source affichée est un extrait exact d'un passage envoyé,
jamais une liste rédigée librement par le modèle. Avec Anthropic, les extraits
viennent des citations natives de l'API ; avec OpenAI, d'une réponse structurée
dont chaque extrait est vérifié mot pour mot par le code (voir `fournisseurs/`).

Cœur sans IHM ni SDK : réutilisable par la CLI comme par le futur back-end web.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_jdr.core.config import ReglagesQuestions
from agent_jdr.core.fournisseurs.base import Fournisseur
from agent_jdr.core.rules_index import Passage, RulesIndex

MESSAGE_AUCUN_PASSAGE = "Aucun passage des règles ne correspond à cette question."


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
    extraits_ecartes: int = 0  # extraits cités introuvables dans leur passage (OpenAI)

    @property
    def texte(self) -> str:
        return "".join(s.texte for s in self.segments)


def assembler_reponse(
    blocs: list[tuple[str, list[tuple[int, str]]]],
    passages: list[Passage],
    extraits_ecartes: int = 0,
) -> Reponse:
    """Blocs (texte, [(index du passage, extrait cité)]) → Reponse.

    Sources dédoublonnées par passage, numérotées dans l'ordre de première citation.
    """
    ordre: list[int] = []
    extraits: dict[int, list[str]] = {}
    segments: list[Segment] = []
    for texte, citations in blocs:
        numeros: list[int] = []
        for i, cite in citations:
            if not 0 <= i < len(passages):
                raise ValueError(f"Citation vers un document inexistant : index {i}")
            if i not in extraits:
                ordre.append(i)
                extraits[i] = []
            cite = cite.strip()
            if cite and cite not in extraits[i]:
                extraits[i].append(cite)
            numero = ordre.index(i) + 1
            if numero not in numeros:
                numeros.append(numero)
        segments.append(Segment(texte, tuple(numeros)))
    sources = tuple(Source(passages[i], tuple(extraits[i])) for i in ordre)
    return Reponse(tuple(segments), sources, tuple(passages), extraits_ecartes)


def repondre(
    question: str,
    index: RulesIndex,
    reglages: ReglagesQuestions,
    fournisseur: Fournisseur,
    limite: int | None = None,
) -> Reponse:
    """Recherche les passages pertinents puis fait rédiger la réponse par le modèle.

    Sans passage trouvé, aucun appel au modèle n'est fait. `limite` remplace
    ponctuellement `reglages.passages_envoyes`.
    """
    passages = [r.passage for r in index.rechercher(question, limite or reglages.passages_envoyes)]
    if not passages:
        return Reponse((Segment(MESSAGE_AUCUN_PASSAGE),), (), ())
    return fournisseur.repondre_avec_sources(reglages.consignes, passages, question)


# --- Rendu texte ------------------------------------------------------------------


def formater_reponse(reponse: Reponse) -> str:
    """Réponse avec renvois [n], puis la section « Sources » numérotée."""
    corps = "".join(
        s.texte + "".join(f" [{n}]" for n in s.sources) for s in reponse.segments
    ).strip()
    lignes = [corps]
    if reponse.sources:
        lignes += ["", "Sources"]
        for n, source in enumerate(reponse.sources, 1):
            lignes.append(f"[{n}] {source.passage.reference()}")
            lignes.extend(f"    « {' '.join(e.split())} »" for e in source.extraits)
    if reponse.extraits_ecartes:
        lignes += [
            "",
            f"({reponse.extraits_ecartes} extrait(s) cité(s) par le modèle introuvable(s) "
            "mot pour mot dans les passages : écarté(s) des sources.)",
        ]
    return "\n".join(lignes)
