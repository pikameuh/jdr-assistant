"""Modification de `config.yaml` et du fichier de secrets depuis une interface (web).

Les fichiers sont écrits pour être relus et modifiés à la main : les commentaires
sont conservés (remplacement ligne à ligne, jamais de réécriture complète du YAML),
et rien n'est écrit sans validation préalable du contenu complet.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from agent_jdr.core.config import (
    RACINE,
    Config,
    ConfigInvalide,
    Secrets,
    _analyser_yaml,
    _valider,
    analyser_config,
)

MODELE_SECRETS = RACINE / "secrets.exemple.yaml"
ENTREES_SECRETS = ("recherche-apikey", "personas-apikey")


def _ecrire_atomique(chemin: Path, texte: str, prive: bool = False) -> None:
    """Écrit `texte` d'un coup : un lecteur voit l'ancien fichier ou le nouveau, jamais un mélange."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_name(f".{chemin.name}.tmp")
    temporaire.write_text(texte, encoding="utf-8")
    if prive:
        os.chmod(temporaire, 0o600)
    os.replace(temporaire, chemin)


# --- config.yaml ---------------------------------------------------------------------


def enregistrer_config(chemin: Path, texte: str) -> Config:
    """Valide `texte` comme configuration complète puis l'écrit en `chemin`. Invalide → rien n'est écrit."""
    config = analyser_config(texte, chemin)
    _ecrire_atomique(chemin, texte)
    return config


def remplacer_reglage(texte: str, section: str, nom: str, valeur: str) -> str:
    """Remplace la valeur de `section > nom` dans le texte YAML, sans toucher au reste.

    Ne gère que les réglages simples sur une ligne (`  nom: valeur`), comme
    `fournisseur` et `modele`.
    """
    lignes = texte.splitlines(keepends=True)
    dans_section = False
    for i, ligne in enumerate(lignes):
        if ligne and not ligne[0].isspace() and not ligne.startswith("#") and ligne.strip():
            dans_section = ligne.split(":", 1)[0].strip() == section
            continue
        if dans_section:
            m = re.match(rf"^(\s+{re.escape(nom)}:)[^\n#]*(#.*)?(\r?\n)?$", ligne)
            if m:
                commentaire = f"  {m.group(2)}" if m.group(2) else ""
                lignes[i] = f"{m.group(1)} {valeur}{commentaire}{m.group(3) or ''}"
                return "".join(lignes)
    raise ConfigInvalide(f"réglage « {section} > {nom} » introuvable dans le fichier de configuration")


def choisir_modele(chemin: Path, section: str, fournisseur: str, modele: str) -> Config:
    """Change le fournisseur et le modèle d'un usage (`dialogue` ou `questions_de_regles`)."""
    if section not in ("dialogue", "questions_de_regles"):
        raise ConfigInvalide(f"section inconnue : {section}")
    texte = chemin.read_text(encoding="utf-8")
    texte = remplacer_reglage(texte, section, "fournisseur", fournisseur)
    texte = remplacer_reglage(texte, section, "modele", modele)
    return enregistrer_config(chemin, texte)


# --- Clés API ------------------------------------------------------------------------


def masquer_cle(cle: str | None) -> str:
    """Affichage partiel d'une clé : « sk-an***9f ». Clé courte : entièrement masquée."""
    if not cle:
        return ""
    if len(cle) < 12:
        return "***"
    return f"{cle[:5]}***{cle[-2:]}"


def _texte_initial_secrets() -> str:
    if MODELE_SECRETS.is_file():
        return MODELE_SECRETS.read_text(encoding="utf-8")
    return "".join(f'{entree}: ""\n' for entree in ENTREES_SECRETS)


def verifier_cle(entree: str, cle: str) -> str:
    """Clé nettoyée (espaces autour retirés) ; refusée si elle contient des espaces ou retours à la ligne."""
    cle = cle.strip()
    if any(c.isspace() or not c.isprintable() for c in cle):
        raise ConfigInvalide(f"« {entree} » : la clé ne doit contenir ni espace ni retour à la ligne")
    return cle


def enregistrer_cles(chemin: Path, cles: dict[str, str | None]) -> Secrets:
    """Met à jour les entrées du fichier de secrets.

    `cles` : entrée (`recherche-apikey`, `personas-apikey`) → nouvelle clé ;
    chaîne vide = effacer la clé ; entrée absente ou None = inchangée.
    Le fichier est créé (depuis `secrets.exemple.yaml`) s'il n'existe pas ;
    ses commentaires sont conservés.
    """
    texte = chemin.read_text(encoding="utf-8") if chemin.is_file() else _texte_initial_secrets()
    for entree, cle in cles.items():
        if entree not in ENTREES_SECRETS:
            raise ConfigInvalide(f"entrée de secrets inconnue : {entree}")
        if cle is None:
            continue
        cle = verifier_cle(entree, cle)
        ligne = f"{entree}: {json.dumps(cle)}"
        motif = re.compile(rf"^{re.escape(entree)}:.*$", re.MULTILINE)
        if motif.search(texte):
            texte = motif.sub(lambda _: ligne, texte, count=1)
        else:
            texte = texte + ("" if texte.endswith("\n") or not texte else "\n") + ligne + "\n"
    donnees = _analyser_yaml(texte, chemin)
    secrets = Secrets() if donnees is None else _valider(Secrets, donnees, chemin, "lignes")
    _ecrire_atomique(chemin, texte, prive=True)
    return secrets
