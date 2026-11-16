"""Moteur de dialogue : fait répondre un PNJ, avec consultation des règles.

Un tour = réplique du joueur → appels au modèle (boucle d'outils sur
`rechercher_regle`) → réplique du PNJ. L'historique ne garde que les tours
réussis. Cœur sans IHM ni SDK : le fournisseur (Anthropic, OpenAI) est injecté.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_jdr.core.config import ReglagesDialogue
from agent_jdr.core.fournisseurs.base import (
    DefinitionOutil,
    Fournisseur,
    ReponseIncomplete,
    ResultatOutil,
)
from agent_jdr.core.persona import Persona
from agent_jdr.core.prompt_builder import Tour, construire_prompt
from agent_jdr.core.rules_index import Passage, RulesIndex
from agent_jdr.core.scene import Scene

OUTIL_REGLES = DefinitionOutil(
    nom="rechercher_regle",
    description=(
        "Recherche plein texte dans les livres de règles de Metal Adventures 1.5 "
        "(Manuel des joueurs, Guide du Meneur). Renvoie les passages les plus pertinents, "
        "chacun précédé de sa référence (livre, page, section). "
        "La recherche porte sur les mots exacts des livres, sans synonymes ni abréviations : "
        "écris les termes en toutes lettres (« points de panache » plutôt que « PP ») et, "
        "si rien ne correspond, reformule avec d'autres mots."
    ),
    schema={
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
)

AUCUN_PASSAGE = "Aucun passage trouvé. Reformule avec d'autres mots des livres."


@dataclass(frozen=True)
class Replique:
    texte: str
    regles_consultees: tuple[Passage, ...] = ()


def executer_recherche(
    index: RulesIndex, appel_id: str, entree: Any, nb_passages: int
) -> tuple[ResultatOutil, list[Passage]]:
    """Exécute un appel à `rechercher_regle` → (résultat pour le modèle, passages trouvés)."""
    requete = entree.get("requete") if isinstance(entree, dict) else None
    if not isinstance(requete, str) or not requete.strip():
        return ResultatOutil(appel_id, ("Paramètre `requete` manquant ou vide.",), erreur=True), []
    passages = [r.passage for r in index.rechercher(requete, nb_passages)]
    if not passages:
        return ResultatOutil(appel_id, (AUCUN_PASSAGE,)), []
    return ResultatOutil(appel_id, tuple(f"{p.reference()}\n{p.texte}" for p in passages)), passages


@dataclass
class MoteurDialogue:
    persona: Persona
    scene: Scene
    index: RulesIndex
    reglages: ReglagesDialogue
    fournisseur: Fournisseur
    historique: list[Tour] = field(default_factory=list)

    def repondre(self, texte: str, pj: str | None = None) -> Replique:
        """Réplique du PNJ au tour `texte` du joueur. En cas d'erreur, l'historique est inchangé."""
        texte = texte.strip()
        if not texte:
            raise ValueError("Réplique du joueur vide")
        tour_joueur = Tour("joueur", texte, pj=pj)
        # Valide persona/scène/historique avant tout appel.
        prompt = construire_prompt(
            self.persona, self.scene, [*self.historique, tour_joueur], self.reglages.consignes
        )
        session = self.fournisseur.session_outils(
            prompt.stable, prompt.scene, prompt.messages, [OUTIL_REGLES]
        )
        consultees: list[Passage] = []

        max_recherches = self.reglages.recherches_max_par_replique
        for _ in range(max_recherches + 1):
            etape = session.envoyer()
            if not etape.appels:
                break
            resultats = []
            for appel in etape.appels:
                if appel.nom == OUTIL_REGLES.nom:
                    resultat, passages = executer_recherche(
                        self.index, appel.id, appel.entree, self.reglages.passages_par_recherche
                    )
                    consultees += [p for p in passages if p not in consultees]
                else:
                    resultat = ResultatOutil(appel.id, (f"Outil inconnu : {appel.nom}",), erreur=True)
                resultats.append(resultat)
            session.ajouter_resultats(resultats)
        else:
            raise ReponseIncomplete(
                f"Trop de recherches de règles ({max_recherches}) sans réplique finale."
            )

        reponse = etape.texte.strip()
        if not reponse:
            raise ReponseIncomplete("Le modèle n'a produit aucune réplique.")
        self.historique += [tour_joueur, Tour("pnj", reponse)]
        return Replique(reponse, tuple(consultees))
