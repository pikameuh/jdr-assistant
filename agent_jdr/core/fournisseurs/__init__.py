"""Fournisseurs de modèles. `creer_fournisseur` choisit selon `reglages.fournisseur`.

Le SDK du fournisseur n'est importé que s'il est choisi.
"""

from __future__ import annotations

from typing import Any

from agent_jdr.core.config import ReglagesModele
from agent_jdr.core.fournisseurs.base import Fournisseur


def creer_fournisseur(
    reglages: ReglagesModele, client: Any = None, cle_api: str | None = None
) -> Fournisseur:
    """`client` : client SDK à utiliser (tests) ; par défaut, créé au premier appel.

    `cle_api` : clé du fournisseur ; None = le SDK lit sa variable d'environnement.
    """
    if reglages.fournisseur == "anthropic":
        from agent_jdr.core.fournisseurs.fournisseur_anthropic import FournisseurAnthropic

        return FournisseurAnthropic(reglages, client, cle_api)
    if reglages.fournisseur == "openai":
        from agent_jdr.core.fournisseurs.fournisseur_openai import FournisseurOpenAI

        return FournisseurOpenAI(reglages, client, cle_api)
    raise ValueError(f"Fournisseur inconnu : {reglages.fournisseur}")
