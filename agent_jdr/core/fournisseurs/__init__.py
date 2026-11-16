"""Fournisseurs de modèles. `creer_fournisseur` choisit selon `reglages.fournisseur`.

Le SDK du fournisseur n'est importé que s'il est choisi.
"""

from __future__ import annotations

from typing import Any

from agent_jdr.core.config import ReglagesModele
from agent_jdr.core.fournisseurs.base import Fournisseur


def creer_fournisseur(reglages: ReglagesModele, client: Any = None) -> Fournisseur:
    """`client` : client SDK à utiliser (tests) ; par défaut, créé au premier appel."""
    if reglages.fournisseur == "anthropic":
        from agent_jdr.core.fournisseurs.fournisseur_anthropic import FournisseurAnthropic

        return FournisseurAnthropic(reglages, client)
    if reglages.fournisseur == "openai":
        from agent_jdr.core.fournisseurs.fournisseur_openai import FournisseurOpenAI

        return FournisseurOpenAI(reglages, client)
    raise ValueError(f"Fournisseur inconnu : {reglages.fournisseur}")
