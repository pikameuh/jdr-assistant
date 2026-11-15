"""Moteur de dialogue : fait répondre un PNJ, avec consultation des règles.

Un tour = réplique du joueur → appels Claude (boucle tool use sur
`rechercher_regle`) → réplique du PNJ. L'historique ne garde que les tours
réussis. Cœur sans IHM : réutilisé par la CLI et le futur back-end web.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import anthropic

from agent_jdr.core.config import ReglagesDialogue
from agent_jdr.core.persona import Persona
from agent_jdr.core.prompt_builder import Tour, construire_prompt
from agent_jdr.core.rules_index import Passage, RulesIndex
from agent_jdr.core.rules_qa import ReponseIncomplete, appeler_api
from agent_jdr.core.scene import Scene

OUTIL_REGLES = {
    "name": "rechercher_regle",
    "description": (
        "Recherche plein texte dans les livres de règles de Metal Adventures 1.5 "
        "(Manuel des joueurs, Guide du Meneur). Renvoie les passages les plus pertinents, "
        "chacun précédé de sa référence (livre, page, section). "
        "La recherche porte sur les mots exacts des livres, sans synonymes ni abréviations : "
        "écris les termes en toutes lettres (« points de panache » plutôt que « PP ») et, "
        "si rien ne correspond, reformule avec d'autres mots."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "requete": {
                "type": "string",
                "description": "Mots-clés en français, ex. « prix pile énergétique ».",
            }
        },
        "required": ["requete"],
        "additionalProperties": False,
    },
    "strict": True,
}

AUCUN_PASSAGE = "Aucun passage trouvé. Reformule avec d'autres mots des livres."


@dataclass(frozen=True)
class Replique:
    texte: str
    regles_consultees: tuple[Passage, ...] = ()


def construire_appel(
    system: list[dict[str, Any]], messages: list[dict[str, Any]], reglages: ReglagesDialogue
) -> dict[str, Any]:
    """Paramètres complets de `messages.create`, à partir de la sortie de `construire_prompt`.

    Cache : marqueur sur `system[0]` (consignes + persona, identique d'une scène à
    l'autre) et cache automatique en fin de conversation (historique qui s'allonge).
    """
    system = [dict(bloc) for bloc in system]
    system[0]["cache_control"] = {"type": "ephemeral"}
    return {
        **reglages.parametres_modele(),
        "cache_control": {"type": "ephemeral"},
        "tools": [OUTIL_REGLES],
        "system": system,
        "messages": messages,
    }


def executer_recherche(
    index: RulesIndex, entree: Any, nb_passages: int
) -> tuple[dict[str, Any], list[Passage]]:
    """Exécute un appel à `rechercher_regle` → (bloc tool_result sans id, passages)."""
    requete = entree.get("requete") if isinstance(entree, dict) else None
    if not isinstance(requete, str) or not requete.strip():
        return {"content": "Paramètre `requete` manquant ou vide.", "is_error": True}, []
    passages = [r.passage for r in index.rechercher(requete, nb_passages)]
    if not passages:
        return {"content": AUCUN_PASSAGE}, []
    contenu = [{"type": "text", "text": f"{p.reference()}\n{p.texte}"} for p in passages]
    return {"content": contenu}, passages


@dataclass
class MoteurDialogue:
    persona: Persona
    scene: Scene
    index: RulesIndex
    reglages: ReglagesDialogue
    client: anthropic.Anthropic | None = None
    historique: list[Tour] = field(default_factory=list)

    def repondre(self, texte: str, pj: str | None = None) -> Replique:
        """Réplique du PNJ au tour `texte` du joueur. En cas d'erreur, l'historique est inchangé."""
        texte = texte.strip()
        if not texte:
            raise ValueError("Réplique du joueur vide")
        client = self.client or anthropic.Anthropic()
        tour_joueur = Tour("joueur", texte, pj=pj)
        # Valide persona/scène/historique ; system + messages initiaux.
        prompt = construire_prompt(
            self.persona, self.scene, [*self.historique, tour_joueur], self.reglages.consignes
        )
        messages = prompt["messages"]
        consultees: list[Passage] = []

        max_recherches = self.reglages.recherches_max_par_replique
        for _ in range(max_recherches + 1):
            message = appeler_api(client, construire_appel(prompt["system"], messages, self.reglages))
            if message.stop_reason == "refusal":
                raise ReponseIncomplete("Le modèle a refusé de produire cette réplique.")
            if message.stop_reason == "max_tokens":
                raise ReponseIncomplete("Réplique tronquée : limite de longueur atteinte.")
            if message.stop_reason != "tool_use":
                break
            resultats = []
            for bloc in message.content:
                if bloc.type != "tool_use":
                    continue
                if bloc.name == OUTIL_REGLES["name"]:
                    resultat, passages = executer_recherche(
                        self.index, bloc.input, self.reglages.passages_par_recherche
                    )
                    consultees += [p for p in passages if p not in consultees]
                else:
                    resultat = {"content": f"Outil inconnu : {bloc.name}", "is_error": True}
                resultats.append({"type": "tool_result", "tool_use_id": bloc.id, **resultat})
            # Contenu renvoyé tel quel (blocs de réflexion compris), puis tous les résultats.
            messages = [
                *messages,
                {"role": "assistant", "content": message.content},
                {"role": "user", "content": resultats},
            ]
        else:
            raise ReponseIncomplete(
                f"Trop de recherches de règles ({max_recherches}) sans réplique finale."
            )

        reponse = "".join(b.text for b in message.content if b.type == "text").strip()
        if not reponse:
            raise ReponseIncomplete("Le modèle n'a produit aucune réplique.")
        self.historique += [tour_joueur, Tour("pnj", reponse)]
        return Replique(reponse, tuple(consultees))
