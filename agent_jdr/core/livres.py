"""Livres de règles en PDF : état, ajout d'un PDF, reconstruction de l'index.

Le choix des livres utilisés est dans `config.yaml` (`regles.livres_utilises`, écrit
par `edition_config.choisir_livres`). La reconstruction de l'index lance la commande
`rules_index build` dans un processus séparé : le programme qui appelle ce module
n'importe jamais PyMuPDF (dépendance de construction uniquement).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from agent_jdr.core.rules_index import RulesIndex, nom_du_livre

TAILLE_MAX = 500 * 1024 * 1024  # 500 Mo ; les deux livres font environ 80 Mo chacun
DUREE_MAX_INDEXATION = 30 * 60  # secondes
# Lettres (accents compris), chiffres, espaces et ponctuation courante ; pas de « / » ni de « # ».
_NOM_PERMIS = re.compile(r"^[\w][\w .,'()+&-]*\.pdf$", re.IGNORECASE)
_verrou_indexation = threading.Lock()


class LivreRefuse(ValueError):
    """Fichier envoyé refusé (nom, format, taille, déjà présent)."""


class ErreurIndexation(RuntimeError):
    """La reconstruction de l'index a échoué (l'ancien index est conservé)."""


@dataclass(frozen=True)
class EtatLivre:
    fichier: str
    livre: str  # nom affiché dans les références
    present: bool  # le PDF est dans le dossier
    taille: int | None  # octets
    passages: int | None  # passages indexés ; None = absent de l'index
    utilise: bool  # coché dans config.yaml


def etat_livres(dossier_pdf: Path, index_db: Path, livres_utilises: tuple[str, ...]) -> list[EtatLivre]:
    """PDF du dossier, plus les livres cochés dont le PDF a disparu (pour pouvoir les décocher)."""
    presents = {p.name: p for p in dossier_pdf.glob("*") if p.suffix.lower() == ".pdf" and p.is_file()}
    comptes: dict[str, int] = {}
    if index_db.is_file():
        with RulesIndex(index_db) as idx:
            comptes = idx.passages_par_livre()
    noms = sorted(set(presents) | set(livres_utilises), key=str.casefold)
    return [
        EtatLivre(
            fichier=nom,
            livre=nom_du_livre(nom),
            present=nom in presents,
            taille=presents[nom].stat().st_size if nom in presents else None,
            passages=comptes.get(nom_du_livre(nom)),
            utilise=nom in livres_utilises,
        )
        for nom in noms
    ]


def verifier_nom(nom: str) -> str:
    nom = nom.strip()
    if Path(nom).name != nom or not _NOM_PERMIS.match(nom) or len(nom) > 150:
        raise LivreRefuse(
            f"Nom de fichier refusé : « {nom} ». Il doit finir par .pdf et ne contenir que des lettres, "
            "chiffres, espaces et la ponctuation courante (pas de / ni de #)."
        )
    return nom


def ajouter_pdf(dossier: Path, nom: str, source: BinaryIO, taille_max: int = TAILLE_MAX) -> Path:
    """Copie le PDF `source` dans `dossier` sous le nom `nom`. Un fichier existant n'est jamais remplacé."""
    nom = verifier_nom(nom)
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / nom
    if cible.exists():
        raise LivreRefuse(f"Un fichier « {nom} » existe déjà dans le dossier des livres.")
    temporaire = dossier / f".{nom}.envoi"
    try:
        with temporaire.open("wb") as f:
            debut = source.read(5)
            if debut != b"%PDF-":
                raise LivreRefuse(f"« {nom} » n'est pas un fichier PDF.")
            f.write(debut)
            shutil.copyfileobj(source, f, length=1024 * 1024)
            if f.tell() > taille_max:
                raise LivreRefuse(f"« {nom} » dépasse la taille maximale ({taille_max // (1024 * 1024)} Mo).")
        try:
            os.link(temporaire, cible)  # échoue si la cible existe : jamais d'écrasement
        except FileExistsError as e:
            raise LivreRefuse(f"Un fichier « {nom} » existe déjà dans le dossier des livres.") from e
    finally:
        temporaire.unlink(missing_ok=True)
    return cible


def reconstruire_index(chemin_config: Path) -> str:
    """Lance `rules_index build` (processus séparé) et renvoie son message de fin.

    Une seule reconstruction à la fois. En cas d'échec, l'index précédent est conservé
    (la construction remplace le fichier seulement à la fin).
    """
    if not _verrou_indexation.acquire(blocking=False):
        raise ErreurIndexation("Une reconstruction de l'index est déjà en cours. Réessayez dans un moment.")
    try:
        commande = [sys.executable, "-m", "agent_jdr.core.rules_index", "build", "--config", str(chemin_config)]
        try:
            fini = subprocess.run(
                commande, capture_output=True, text=True, timeout=DUREE_MAX_INDEXATION, check=False
            )
        except subprocess.TimeoutExpired as e:
            raise ErreurIndexation(f"Reconstruction de l'index interrompue après {DUREE_MAX_INDEXATION // 60} min.") from e
        if fini.returncode != 0:
            lignes = [l for l in fini.stderr.strip().splitlines() if l.strip()]
            detail = lignes[-1] if lignes else f"code {fini.returncode}"
            raise ErreurIndexation(f"Reconstruction de l'index impossible : {detail.removeprefix('Erreur : ')}")
        return fini.stdout.strip()
    finally:
        _verrou_indexation.release()
