"""CLI de dialogue avec un PNJ : `uv run parler <persona> --lieu … --moment … --pj …`.

Client mince : toute la logique est dans `core`. Commandes en cours de partie :
`/fait <texte>` ajoute un fait établi à la scène, `/quitter` termine.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_jdr.core.config import (
    CONFIG_DEFAUT,
    ConfigInvalide,
    charger_config,
    charger_secrets,
    conseil_cle,
)
from agent_jdr.core.dialogue_engine import MoteurDialogue
from agent_jdr.core.fournisseurs import creer_fournisseur
from agent_jdr.core.fournisseurs.base import (
    ErreurFournisseur,
    IdentifiantsAbsents,
    ReponseIncomplete,
)
from agent_jdr.core.persona import PersonaInvalide, charger_personas
from agent_jdr.core.rules_index import RulesIndex, livres_choisis
from agent_jdr.core.scene import Scene


def _erreur(message: str) -> None:
    print(f"Erreur : {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="parler", description=__doc__)
    parser.add_argument("persona", help="id de la fiche PNJ (nom du fichier sans .yaml)")
    parser.add_argument("--lieu", required=True)
    parser.add_argument("--moment", required=True)
    parser.add_argument("--pj", required=True, help="nom du personnage joueur qui parle")
    parser.add_argument("--ambiance", default="")
    parser.add_argument("--enjeux", default="")
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAUT, help="fichier de configuration")
    parser.add_argument("--personas", type=Path, help="remplace fichiers.dossier_des_pnj")
    parser.add_argument("--db", type=Path, help="remplace fichiers.index_des_regles")
    args = parser.parse_args(argv)

    try:
        config = charger_config(args.config)
        secrets = charger_secrets(config.fichiers.secrets)
    except ConfigInvalide as e:
        _erreur(f"configuration : {e}")
        return 1
    try:
        personas = charger_personas(args.personas or config.fichiers.dossier_des_pnj)
    except PersonaInvalide as e:
        _erreur(str(e))
        return 1
    if args.persona not in personas:
        _erreur(f"PNJ inconnu « {args.persona} ». Disponibles : {', '.join(personas) or 'aucun'}")
        return 1
    persona = personas[args.persona]
    scene = Scene(
        lieu=args.lieu,
        moment=args.moment,
        ambiance=args.ambiance,
        pnj_presents=(persona.id,),
        pj_presents=(args.pj,),
        enjeux=args.enjeux,
    )
    try:
        index = RulesIndex(args.db or config.fichiers.index_des_regles, livres_choisis(config))
    except FileNotFoundError as e:
        _erreur(str(e))
        return 1

    try:
        import readline  # noqa: F401  (édition de ligne et historique au clavier)
    except ImportError:
        pass

    with index:
        reglages = config.dialogue
        moteur = MoteurDialogue(persona, scene, index, reglages, creer_fournisseur(reglages, cle_api=secrets.personas))
        print(f"Vous parlez à {persona.nom} ({reglages.fournisseur}, modèle : {reglages.modele}).")
        print("/fait <texte> : ajouter un fait à la scène ; /quitter : sortir.")
        while True:
            try:
                ligne = input(f"{args.pj} > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if not ligne:
                continue
            if ligne == "/quitter":
                return 0
            if ligne.startswith("/fait"):
                fait = ligne.removeprefix("/fait").strip()
                if not fait:
                    print("Usage : /fait <texte>")
                    continue
                moteur.scene = moteur.scene.avec_fait(fait)
                print(f"(fait ajouté : {fait})")
                continue
            try:
                replique = moteur.repondre(ligne, pj=args.pj)
            except IdentifiantsAbsents as e:
                _erreur(f"{e}\n{conseil_cle('dialogue', config.fichiers.secrets)}")
                return 1
            except ReponseIncomplete as e:
                _erreur(f"{e} (tour non enregistré, vous pouvez reformuler)")
                continue
            except ErreurFournisseur as e:
                _erreur(f"{e} (tour non enregistré)")
                continue
            print(f"{persona.nom} > {replique.texte}")
            if replique.regles_consultees:
                refs = "; ".join(p.reference() for p in replique.regles_consultees)
                print(f"    (règles consultées : {refs})")


if __name__ == "__main__":
    sys.exit(main())
