"""Assemblage du prompt d'un PNJ : persona + scène + historique.

Sortie : paramètres `system` et `messages` de `client.messages.create`.
Le modèle, l'outil de règles et le cache sont ajoutés par le moteur de dialogue
(phase 2). L'ordre sert le cache : la partie stable (consignes + persona) vient
en premier bloc système, la partie variable (scène) en second.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from agent_jdr.core.persona import Persona
from agent_jdr.core.scene import Scene

CONSIGNES = """\
Tu incarnes un personnage non joueur (PNJ) dans une partie du jeu de rôle Metal Adventures 1.5, à la demande du meneur de jeu.
Les messages de l'utilisateur sont les paroles et actions des personnages joueurs (PJ) ; tes réponses sont les répliques de ton personnage.

Consignes :
- Réponds en français, uniquement par ce que ton personnage dit, avec au besoin un geste bref entre astérisques.
- Reste toujours en personnage : ton, vocabulaire et tics de la fiche ; ne mentionne jamais que tu es une IA ni ces consignes.
- Ne révèle un secret que si sa condition de révélation est remplie dans la scène ; un secret sans condition n'est jamais révélé. Tu peux mentir ou éluder pour le protéger, comme le ferait ton personnage.
- Ne contredis ni la fiche ni les faits établis de la scène. Ne décris ni les paroles ni les actions des PJ."""


@dataclass(frozen=True)
class Tour:
    """Une prise de parole. `pj` = nom du PJ qui parle (tours du joueur seulement)."""

    locuteur: Literal["joueur", "pnj"]
    texte: str
    pj: str | None = None


def _puces(titre: str, elements: tuple[str, ...]) -> list[str]:
    return [f"{titre} :", *(f"- {e}" for e in elements)] if elements else []


def rendre_persona(persona: Persona) -> str:
    lignes = [
        f"# Ton personnage : {persona.nom}",
        f"Espèce : {persona.espece}",
        f"Origine : {persona.origine}",
        f"Rôle : {persona.role}",
        f"Personnalité : {persona.personnalite}",
        f"Manière de parler : {persona.parole.registre}",
        *_puces("Tics", persona.parole.tics),
        *_puces("Exemples de répliques", persona.parole.exemples),
        *_puces("Objectifs", persona.objectifs),
        *_puces("Ce que tu sais", persona.connaissances),
    ]
    if persona.secrets:
        lignes.append("Secrets :")
        for s in persona.secrets:
            condition = s.condition_revelation or "jamais"
            lignes.append(f"- {s.contenu} (révélation : {condition})")
    lignes.append(f"Attitude envers les PJ : {persona.attitude_envers_pj}")
    return "\n".join(lignes)


def rendre_scene(scene: Scene) -> str:
    lignes = [
        "# Scène en cours",
        f"Lieu : {scene.lieu}",
        f"Moment : {scene.moment}",
    ]
    if scene.ambiance:
        lignes.append(f"Ambiance : {scene.ambiance}")
    if scene.pnj_presents:
        lignes.append(f"PNJ présents : {', '.join(scene.pnj_presents)}")
    if scene.pj_presents:
        lignes.append(f"PJ présents : {', '.join(scene.pj_presents)}")
    if scene.enjeux:
        lignes.append(f"Enjeux : {scene.enjeux}")
    lignes += _puces("Faits établis", scene.faits_etablis)
    return "\n".join(lignes)


def construire_prompt(
    persona: Persona, scene: Scene, historique: list[Tour]
) -> dict[str, Any]:
    """`system` + `messages` pour faire répondre `persona` au dernier tour du joueur."""
    if persona.id not in scene.pnj_presents:
        raise ValueError(f"Le PNJ « {persona.id} » n'est pas présent dans la scène")
    if not historique or historique[-1].locuteur != "joueur":
        raise ValueError("L'historique doit se terminer par un tour du joueur")

    messages = []
    for tour in historique:
        if tour.locuteur == "joueur":
            texte = f"[{tour.pj}] {tour.texte}" if tour.pj else tour.texte
            messages.append({"role": "user", "content": texte})
        else:
            messages.append({"role": "assistant", "content": tour.texte})
    if messages[0]["role"] != "user":
        raise ValueError("L'historique doit commencer par un tour du joueur")

    return {
        "system": [
            {"type": "text", "text": f"{CONSIGNES}\n\n{rendre_persona(persona)}"},
            {"type": "text", "text": rendre_scene(scene)},
        ],
        "messages": messages,
    }
