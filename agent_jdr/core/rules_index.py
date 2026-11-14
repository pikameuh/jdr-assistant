"""Index FTS5 des règles : construction et recherche.

La partie recherche n'a aucune dépendance hors bibliothèque standard ; c'est elle
que l'outil `rechercher_regle` du moteur de dialogue interrogera.

Construction : `uv run python -m agent_jdr.core.rules_index build`
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
DB_DEFAUT = RACINE / "data" / "rules.db"
DOSSIER_REGLES_DEFAUT = RACINE / "rules" / "MA - Manuel des joueurs 1.5"

VERSION_SCHEMA = 1


@dataclass(frozen=True)
class Passage:
    livre: str
    page: int  # page imprimée de début
    page_fin: int
    chapitre: str  # titre courant de page
    section: str
    sous_section: str
    texte: str

    def reference(self) -> str:
        """Ex. « Manuel des joueurs, p. 59 — L’Ingénieur > Scotty special »."""
        pages = f"p. {self.page}" if self.page == self.page_fin else f"p. {self.page}-{self.page_fin}"
        titres = " > ".join(t for t in (self.section, self.sous_section) if t)
        return f"{self.livre}, {pages}" + (f" — {titres}" if titres else "")


@dataclass(frozen=True)
class Resultat:
    passage: Passage
    score: float  # bm25 : plus petit = plus pertinent


# --- Construction ---------------------------------------------------------------

_SCHEMA = """
CREATE TABLE meta (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);
CREATE VIRTUAL TABLE passages USING fts5(
    livre UNINDEXED,
    page UNINDEXED,
    page_fin UNINDEXED,
    chapitre,
    section,
    sous_section,
    texte,
    tokenize = "unicode61 remove_diacritics 2"
);
"""


def construire_index(passages: Iterable[Passage], chemin_db: Path) -> int:
    """Écrit l'index dans `chemin_db` (remplacement atomique). Renvoie le nombre de passages."""
    chemin_db.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin_db.with_suffix(chemin_db.suffix + ".tmp")
    temporaire.unlink(missing_ok=True)
    con = sqlite3.connect(temporaire)
    try:
        con.executescript(_SCHEMA)
        con.execute("INSERT INTO meta VALUES ('version_schema', ?)", (str(VERSION_SCHEMA),))
        lignes = [
            (p.livre, p.page, p.page_fin, p.chapitre, p.section, p.sous_section, p.texte)
            for p in passages
        ]
        con.executemany("INSERT INTO passages VALUES (?, ?, ?, ?, ?, ?, ?)", lignes)
        con.execute("INSERT INTO passages(passages) VALUES ('optimize')")
        con.commit()
    finally:
        con.close()
    os.replace(temporaire, chemin_db)
    return len(lignes)


# --- Recherche ------------------------------------------------------------------

# Mots trop courants pour discriminer un passage.
_MOTS_VIDES = frozenset(
    """
    a au aux avec ce ces cet cette comment dans de des du elle en est et il ils je la le les
    leur lui ma mais me mes moi mon ne nos notre nous on ou où par pas pour qu que quel quelle
    quels quelles qui sa se ses si son sont sur ta te tes toi ton tu un une vos votre vous y
    d l j c s n m t qu est-ce faire fait peut on comment combien quand quoi
    """.split()
)

# Poids bm25 des colonnes indexées : chapitre, section, sous_section, texte
# (livre, page, page_fin sont UNINDEXED mais comptent dans la liste).
_POIDS = "0, 0, 0, 2.0, 4.0, 4.0, 1.0"


def _racine(mot: str) -> str:
    """Racinisation légère : retire le pluriel, pour une recherche par préfixe."""
    if len(mot) > 3 and mot[-1] in "sx":
        return mot[:-1]
    return mot


def requete_fts(texte: str) -> str | None:
    """Requête en langage naturel → expression FTS5 (termes en OU, par préfixe).

    Renvoie None si la requête ne contient aucun terme utile.
    """
    termes: list[str] = []
    for mot in re.findall(r"\w+", texte.lower()):
        if mot in _MOTS_VIDES or len(mot) < 2:
            continue
        terme = f'"{_racine(mot)}"*'
        if terme not in termes:
            termes.append(terme)
    return " OR ".join(termes) or None


class RulesIndex:
    """Accès en lecture seule à l'index des règles."""

    def __init__(self, chemin_db: Path = DB_DEFAUT) -> None:
        if not chemin_db.is_file():
            raise FileNotFoundError(
                f"Index des règles absent : {chemin_db}. "
                "Le construire avec : uv run python -m agent_jdr.core.rules_index build"
            )
        self._con = sqlite3.connect(f"file:{chemin_db}?mode=ro", uri=True)

    def rechercher(self, requete: str, limite: int = 5) -> list[Resultat]:
        expression = requete_fts(requete)
        if expression is None:
            return []
        lignes = self._con.execute(
            f"""
            SELECT livre, page, page_fin, chapitre, section, sous_section, texte,
                   bm25(passages, {_POIDS}) AS score
            FROM passages WHERE passages MATCH ? ORDER BY score LIMIT ?
            """,
            (expression, limite),
        ).fetchall()
        return [Resultat(Passage(*ligne[:7]), ligne[7]) for ligne in lignes]

    def nombre_passages(self) -> int:
        return self._con.execute("SELECT count(*) FROM passages").fetchone()[0]

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> RulesIndex:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


# --- Ligne de commande ----------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rules_index", description=__doc__)
    sous = parser.add_subparsers(dest="commande", required=True)
    build = sous.add_parser("build", help="Construire l'index depuis les PDF")
    build.add_argument("--regles", type=Path, default=DOSSIER_REGLES_DEFAUT)
    build.add_argument("--db", type=Path, default=DB_DEFAUT)
    cherche = sous.add_parser("search", help="Interroger l'index")
    cherche.add_argument("requete")
    cherche.add_argument("-n", type=int, default=5)
    cherche.add_argument("--db", type=Path, default=DB_DEFAUT)
    args = parser.parse_args(argv)

    if args.commande == "build":
        from agent_jdr.core.rules_extract import extraire_regles  # dépendance de build

        n = construire_index(extraire_regles(args.regles), args.db)
        print(f"{n} passages indexés dans {args.db}")
    else:
        with RulesIndex(args.db) as index:
            for r in index.rechercher(args.requete, args.n):
                print(f"[{r.score:.2f}] {r.passage.reference()}")
                print("    " + r.passage.texte[:200].replace("\n", " ") + "…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
