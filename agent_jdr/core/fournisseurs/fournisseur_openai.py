"""Fournisseur OpenAI (API Responses).

- Dialogue : consignes + persona puis scène dans `instructions` (le cache d'OpenAI
  est automatique et porte sur le début de la requête) ; outil en mode strict ;
  les éléments renvoyés (raisonnement compris) sont repassés tels quels avec les
  résultats d'outils, comme l'exige la documentation.
- Questions de règles : OpenAI n'a pas de citations natives. Le modèle renvoie une
  réponse structurée (JSON) qui cite, pour chaque segment, des extraits des
  passages ; le code vérifie chaque extrait mot pour mot et écarte les autres.
"""

from __future__ import annotations

import json
import re
from typing import Any

import openai
from pydantic import BaseModel, ValidationError

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

CONSIGNE_FORMAT = """\
Format de réponse (imposé par le programme) : découpe ta réponse en segments, dans l'ordre de lecture.
Pour chaque segment, `citations` liste les passages qui l'appuient : `passage` est le numéro du passage, `extrait` un morceau de ce passage copié mot pour mot, sans aucune modification.
Un segment qui n'affirme aucune règle a une liste de citations vide."""

SCHEMA_REPONSE = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "texte": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "passage": {"type": "integer"},
                                "extrait": {"type": "string"},
                            },
                            "required": ["passage", "extrait"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["texte", "citations"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["segments"],
    "additionalProperties": False,
}


class _Citation(BaseModel):
    passage: int
    extrait: str


class _SegmentJson(BaseModel):
    texte: str
    citations: list[_Citation]


class _ReponseJson(BaseModel):
    segments: list[_SegmentJson]


def _normaliser(texte: str) -> str:
    return " ".join(texte.split())


class FournisseurOpenAI:
    def __init__(
        self,
        reglages: ReglagesModele,
        client: openai.OpenAI | None = None,
        cle_api: str | None = None,
    ) -> None:
        self.reglages = reglages
        self._client = client
        self._cle_api = cle_api

    # --- Appel ------------------------------------------------------------------

    def parametres(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.reglages.modele,
            "max_output_tokens": self.reglages.longueur_max_reponse,
        }
        if self.reglages.effort:
            params["reasoning"] = {"effort": self.reglages.effort}
        return params

    def _client_ou_defaut(self) -> openai.OpenAI:
        if self._client is None:
            try:
                self._client = (
                    openai.OpenAI(api_key=self._cle_api) if self._cle_api else openai.OpenAI()
                )
            except openai.OpenAIError as e:  # levée à la création quand la clé manque
                raise IdentifiantsAbsents(
                    "Aucune clé OpenAI trouvée : clé absente du fichier de secrets "
                    "et variable OPENAI_API_KEY non définie."
                ) from e
        return self._client

    def appeler(self, params: dict[str, Any]) -> Any:
        """`responses.create`, erreurs converties en erreurs communes, réponse vérifiée."""
        client = self._client_ou_defaut()
        try:
            reponse = client.responses.create(**params)
        except openai.AuthenticationError as e:
            raise IdentifiantsAbsents(f"Clé OpenAI refusée : {e.message}") from e
        except openai.APIError as e:
            raise ErreurFournisseur(f"API OpenAI : {e.message}") from e

        if reponse.status == "incomplete":
            raison = reponse.incomplete_details.reason if reponse.incomplete_details else None
            if raison == "max_output_tokens":
                raise ReponseIncomplete(MESSAGE_TRONQUE)
            if raison == "content_filter":
                raise ReponseIncomplete(MESSAGE_REFUS)
            raise ReponseIncomplete(f"Réponse incomplète ({raison or 'raison inconnue'}).")
        if reponse.status == "failed":
            detail = reponse.error.message if reponse.error else "raison inconnue"
            raise ErreurFournisseur(f"API OpenAI : échec de la réponse ({detail})")
        for element in reponse.output:
            if element.type == "message" and any(c.type == "refusal" for c in element.content):
                raise ReponseIncomplete(MESSAGE_REFUS)
        return reponse

    # --- Dialogue avec outils ------------------------------------------------------

    def session_outils(
        self,
        stable: str,
        variable: str,
        messages: list[dict[str, str]],
        outils: list[DefinitionOutil],
    ) -> _SessionOpenAI:
        fixes = {
            **self.parametres(),
            "instructions": f"{stable}\n\n{variable}",
            "tools": [
                {
                    "type": "function",
                    "name": o.nom,
                    "description": o.description,
                    "parameters": o.schema,
                    "strict": True,
                }
                for o in outils
            ],
        }
        entree = [{"role": m["role"], "content": m["content"]} for m in messages]
        return _SessionOpenAI(self, fixes, entree)

    # --- Questions de règles ---------------------------------------------------------

    def repondre_avec_sources(self, consignes: str, passages: list[Passage], question: str) -> Reponse:
        reponse = self.appeler(construire_requete(self.parametres(), consignes, passages, question))
        return lire_reponse(reponse.output_text, passages)


class _SessionOpenAI:
    def __init__(self, fournisseur: FournisseurOpenAI, fixes: dict[str, Any], entree: list[Any]) -> None:
        self._fournisseur = fournisseur
        self._fixes = fixes
        self._entree = entree
        self._dernier: Any = None

    def envoyer(self) -> Etape:
        reponse = self._fournisseur.appeler({**self._fixes, "input": self._entree})
        self._dernier = reponse
        appels = tuple(
            AppelOutil(e.call_id, e.name, _decoder(e.arguments))
            for e in reponse.output
            if e.type == "function_call"
        )
        return Etape(reponse.output_text, appels)

    def ajouter_resultats(self, resultats: list[ResultatOutil]) -> None:
        sorties = [
            {
                "type": "function_call_output",
                "call_id": r.id,
                "output": ("Erreur : " if r.erreur else "") + "\n\n".join(r.contenu),
            }
            for r in resultats
        ]
        # Tous les éléments renvoyés (raisonnement compris), puis les résultats.
        self._entree = [*self._entree, *self._dernier.output, *sorties]


def _decoder(arguments: str) -> Any:
    try:
        return json.loads(arguments)
    except (json.JSONDecodeError, TypeError):
        return None


def construire_requete(
    parametres: dict[str, Any], consignes: str, passages: list[Passage], question: str
) -> dict[str, Any]:
    """Passages numérotés à partir de 1, puis la question ; réponse JSON imposée."""
    documents = "\n\n".join(
        f"[Passage {n}] {p.reference()}\n{p.texte}" for n, p in enumerate(passages, 1)
    )
    return {
        **parametres,
        "instructions": f"{consignes}\n\n{CONSIGNE_FORMAT}",
        "input": [{"role": "user", "content": f"{documents}\n\nQuestion : {question}"}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "reponse_sourcee",
                "schema": SCHEMA_REPONSE,
                "strict": True,
            }
        },
    }


def lire_reponse(texte_json: str, passages: list[Passage]) -> Reponse:
    """JSON du modèle → Reponse. Seuls les extraits présents mot pour mot (espaces
    normalisés) dans le passage cité sont gardés ; les autres sont comptés comme écartés."""
    try:
        donnees = _ReponseJson.model_validate(json.loads(texte_json))
    except (json.JSONDecodeError, ValidationError) as e:
        raise ReponseIncomplete("Réponse du modèle mal formée (JSON attendu).") from e

    textes_passages = [_normaliser(p.texte) for p in passages]
    ecartes = 0
    blocs: list[tuple[str, list[tuple[int, str]]]] = []
    for segment in donnees.segments:
        citations = []
        for c in segment.citations:
            i = c.passage - 1
            extrait = _normaliser(c.extrait)
            if 0 <= i < len(passages) and extrait and extrait in textes_passages[i]:
                citations.append((i, extrait))
            else:
                ecartes += 1
        texte = segment.texte
        # Les segments se suivent : garantir une séparation lisible entre deux segments.
        if blocs and texte and not texte[0].isspace() and not re.match(r"[,.;:!?)»]", texte):
            precedent = blocs[-1][0]
            if precedent and not precedent[-1].isspace():
                texte = " " + texte
        blocs.append((texte, citations))
    return assembler_reponse(blocs, passages, ecartes)
