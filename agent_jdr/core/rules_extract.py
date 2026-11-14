"""Extraction des PDF de règles → passages découpés par section.

Utilisé uniquement à la construction de l'index (dépend de PyMuPDF, outil de build).
L'agent en exécution n'importe jamais ce module.

Particularités des PDF Metal Adventures 1.5 traitées ici :
- le texte de chaque page est dessiné deux fois (une passe propre puis une passe
  fragmentée superposée) → dédoublonnage des caractères par position ;
- la structure n'existe que par les polices (pas de table des matières intégrée) ;
- en-tête « Ref. » et filigrane nominatif de l'acheteur (Helvetica) → supprimés ;
- césures en fin de ligne → recollées, en gardant le trait d'union des mots composés.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from agent_jdr.core.rules_index import Passage

# Nom de fichier PDF → nom du livre tel qu'affiché dans les références.
LIVRES: dict[str, str] = {
    "MA - Manuel des joueurs 1.5.pdf": "Manuel des joueurs",
    "MA - Guide du Meneur 1.5.pdf": "Guide du Meneur",
}

# Numéro imprimé = numéro de page PDF - 1 (vérifié sur toutes les pages numérotées des deux livres).
DECALAGE_PAGE = 1

# Pages imprimées 0 à 3 : couverture, crédits, sommaire (identique dans les deux livres).
DERNIERE_PAGE_LIMINAIRE = 3

# Au-delà, un passage est coupé à la frontière de paragraphe suivante.
TAILLE_MAX_PASSAGE = 1500

# Polices hors règles : filigrane/réf. (Helvetica), citations d'illustration, ornements.
_POLICES_IGNOREES = ("Helvetica", "ViktorScript", "AdornOrnaments")

_REMPLACEMENTS = str.maketrans(
    {
        "\xa0": " ",
        " ": " ",
        "": "❑",  # case à cocher (Wingdings)
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
    }
)


# --- Classification des lignes -------------------------------------------------

TITRE = "titre"  # section (14 pt)
SOUS_TITRE = "sous_titre"  # sous-section (12 pt)
EN_TETE = "en_tete"  # titre courant de page (13,5 pt, terminé par « >> »)
NUMERO = "numero"  # numéro de page imprimé (18 pt)
CORPS = "corps"
IGNORE = "ignore"


@dataclass(frozen=True)
class Span:
    texte: str
    police: str
    taille: float


def _est_decoration(span: Span) -> bool:
    """Chevrons « >> » décoratifs devant les titres et les puces."""
    return span.police.startswith("VariexOT") and span.texte.strip() in {">", ">>"}


def classer_ligne(spans: list[Span]) -> str:
    """Rôle d'une ligne d'après la police de son span principal (le plus long)."""
    utiles = [s for s in spans if s.texte.strip() and not _est_decoration(s)]
    if not utiles:
        return IGNORE
    principal = max(utiles, key=lambda s: len(s.texte.strip()))
    police, taille = principal.police, round(principal.taille, 1)
    if police.startswith(_POLICES_IGNOREES):
        return IGNORE
    if police.startswith("MascotMVB"):  # titres des pages d'ambiance pirate
        return TITRE
    if police.startswith("BalboaPlus"):
        if taille == 18 and principal.texte.strip().isdigit():
            return NUMERO
        if taille == 13.5:
            return EN_TETE
        if taille == 14:
            return TITRE
        if taille == 12:
            return SOUS_TITRE
        # 11 pt = nouvelles d'introduction ; ≥ 15 pt = bandeaux de chapitre.
        return IGNORE
    return CORPS


def texte_ligne(spans: list[Span]) -> str:
    """Texte d'une ligne : puces « >> » converties en « • », espaces normalisés."""
    morceaux: list[str] = []
    for i, s in enumerate(spans):
        if _est_decoration(s):
            if i == 0 and s.police.startswith("VariexOT-Bold"):
                morceaux.append("• ")
            continue
        morceaux.append(s.texte)
    texte = "".join(morceaux).translate(_REMPLACEMENTS)
    texte = re.sub(r"\s+", " ", texte).strip()
    return texte.removesuffix(">>").strip()


# --- Lecture d'une page ---------------------------------------------------------


@dataclass
class Ligne:
    role: str
    texte: str
    bloc: int


def lire_page(page: pymupdf.Page) -> list[Ligne]:
    """Lignes de la page dans l'ordre du flux, sans les doublons superposés."""
    vus: set[tuple[str, int, int]] = set()
    lignes: list[Ligne] = []
    # Sans TEXT_PRESERVE_IMAGES : les images ne sont pas décodées (×10 plus rapide).
    flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    for bloc in page.get_text("rawdict", flags=flags)["blocks"]:
        if bloc["type"] != 0:
            continue
        for ligne in bloc["lines"]:
            spans: list[Span] = []
            for s in ligne["spans"]:
                gardes = []
                for c in s["chars"]:
                    cle = (c["c"], round(c["origin"][0]), round(c["origin"][1]))
                    if c["c"].strip():
                        if cle in vus:
                            continue
                        vus.add(cle)
                    gardes.append(c["c"])
                if gardes:
                    spans.append(Span("".join(gardes), s["font"], s["size"]))
            if not any(s.texte.strip() for s in spans):
                continue
            texte = texte_ligne(spans)
            role = classer_ligne(spans)
            if role == CORPS and est_residu(texte):
                continue
            if texte:
                lignes.append(Ligne(role, texte, bloc["number"]))
    return lignes


_RESIDU = re.compile(r"[a-zà-ÿ](?: [a-zà-ÿ])*")


def est_residu(texte: str) -> bool:
    """Ligne sans contenu cherchable.

    - Fragment de la passe superposée resté isolé (« t », « u d t ») ; les lignes de
      lettres isolées légitimes (« B », « L : », « 5 m ») portent une majuscule, un
      chiffre ou une ponctuation et ne sont pas concernées.
    - Ligne sans lettre ni chiffre (cases « ❑❑❑ » des fiches, « ( » isolée).
    """
    return _RESIDU.fullmatch(texte) is not None or re.search(r"\w", texte) is None


# --- Recollage des césures ------------------------------------------------------

_MOT = re.compile(r"[\w’'-]+")


def vocabulaire(paragraphes: Iterable[list[str]]) -> Counter[str]:
    """Fréquence des mots vus en milieu de ligne (donc jamais coupés par une césure)."""
    vocab: Counter[str] = Counter()
    for lignes in paragraphes:
        for ligne in lignes:
            mots = _MOT.findall(ligne.lower())
            vocab.update(mots[1:-1])
    return vocab


def joindre_lignes(lignes: list[str], vocab: Counter[str]) -> str:
    """Recolle les lignes d'un paragraphe.

    « fonction-/nement » → « fonctionnement » ; « celui-/ci » → « celui-ci » quand la
    forme avec trait d'union est la plus fréquente dans le corpus.
    """
    texte = ""
    for ligne in lignes:
        if not texte:
            texte = ligne
            continue
        m_fin = re.search(r"([\w’']+)-$", texte)
        m_debut = re.match(r"([\w’']+)", ligne)
        if m_fin and m_debut and m_debut.group(1)[0].islower():
            gauche, droite = m_fin.group(1).lower(), m_debut.group(1).lower()
            if vocab[f"{gauche}-{droite}"] > vocab[gauche + droite]:
                texte += ligne
            else:
                texte = texte[:-1] + ligne
        else:
            texte += " " + ligne
    return texte


_FIN_DE_PHRASE = re.compile(r"(?<=[.!?…»)])\s+(?=[A-ZÀ-Ý«•(])")


def decouper(texte: str, taille_max: int = TAILLE_MAX_PASSAGE) -> list[str]:
    """Coupe un texte trop long en morceaux ≤ `taille_max`, aux fins de phrase.

    Une phrase plus longue que `taille_max` reste entière dans son morceau.
    """
    if len(texte) <= taille_max:
        return [texte]
    morceaux: list[str] = []
    courant = ""
    for phrase in _FIN_DE_PHRASE.split(texte):
        if courant and len(courant) + 1 + len(phrase) > taille_max:
            morceaux.append(courant)
            courant = phrase
        else:
            courant = f"{courant} {phrase}" if courant else phrase
    if courant:
        morceaux.append(courant)
    return morceaux


# --- Découpage en passages ------------------------------------------------------


@dataclass
class _Paragraphe:
    lignes: list[str]
    page: int
    chapitre: str
    section: str
    sous_section: str
    page_fin: int = 0

    def __post_init__(self) -> None:
        self.page_fin = self.page_fin or self.page


def prolonge(precedente: str, suivante: str) -> bool:
    """Vrai si `suivante` continue la phrase de `precedente` malgré un changement de bloc.

    Cas typiques : suite d'un élément de liste à puce (bloc distinct dans le PDF),
    passage à la colonne ou à la page suivante au milieu d'une phrase.
    """
    if suivante.startswith("• "):
        return False
    return precedente.endswith("-") or suivante[:1].islower()


def paragraphes_du_livre(doc: pymupdf.Document) -> Iterator[_Paragraphe]:
    """Paragraphes de corps de texte avec leur contexte (chapitre/section/sous-section)."""
    chapitre = section = sous_section = ""
    courant: _Paragraphe | None = None
    bloc_courant: tuple[int, int] | None = None
    for page in doc:
        numero = page.number + 1 - DECALAGE_PAGE
        if numero <= DERNIERE_PAGE_LIMINAIRE:
            continue
        lignes = lire_page(page)
        titre_precedent: Ligne | None = None
        for ligne in lignes:
            if ligne.role == EN_TETE:
                chapitre = ligne.texte
                continue
            if ligne.role in (TITRE, SOUS_TITRE):
                # Titre sur deux lignes du même bloc → concaténation.
                suite = (
                    titre_precedent is not None
                    and titre_precedent.role == ligne.role
                    and titre_precedent.bloc == ligne.bloc
                )
                if ligne.role == TITRE:
                    section = f"{section} {ligne.texte}" if suite else ligne.texte
                    sous_section = ""
                else:
                    sous_section = f"{sous_section} {ligne.texte}" if suite else ligne.texte
                titre_precedent = ligne
                if courant:
                    yield courant
                courant, bloc_courant = None, None
                continue
            titre_precedent = None
            if ligne.role != CORPS:
                continue
            bloc = (page.number, ligne.bloc)
            nouveau = courant is None or (
                (bloc != bloc_courant or ligne.texte.startswith("• "))
                and not prolonge(courant.lignes[-1], ligne.texte)
            )
            if nouveau:
                if courant:
                    yield courant
                courant = _Paragraphe([], numero, chapitre, section, sous_section)
            bloc_courant = bloc
            assert courant is not None
            courant.lignes.append(ligne.texte)
            courant.page_fin = numero
    if courant:
        yield courant


@dataclass
class _Accumulateur:
    livre: str
    passages: list[Passage] = field(default_factory=list)
    _cle: tuple[str, str, str] | None = None
    _textes: list[str] = field(default_factory=list)
    _pages: list[int] = field(default_factory=list)

    def ajouter(self, para: _Paragraphe, texte: str) -> None:
        """Ajoute un paragraphe ; nouveau passage si la section change ou si la taille déborde."""
        cle = (para.chapitre, para.section, para.sous_section)
        for morceau in decouper(texte):
            taille = sum(len(t) + 1 for t in self._textes)
            if cle != self._cle or (self._textes and taille + len(morceau) > TAILLE_MAX_PASSAGE):
                self.vider()
                self._cle = cle
            self._textes.append(morceau)
            self._pages.extend((para.page, para.page_fin))

    def vider(self) -> None:
        if self._textes and self._cle is not None:
            chapitre, section, sous_section = self._cle
            self.passages.append(
                Passage(
                    livre=self.livre,
                    page=min(self._pages),
                    page_fin=max(self._pages),
                    chapitre=chapitre,
                    section=section,
                    sous_section=sous_section,
                    texte="\n".join(self._textes),
                )
            )
        self._textes, self._pages = [], []


def extraire_livre(pdf: Path, livre: str) -> list[Passage]:
    with pymupdf.open(pdf) as doc:
        paragraphes = list(paragraphes_du_livre(doc))
    vocab = vocabulaire(p.lignes for p in paragraphes)
    acc = _Accumulateur(livre)
    for para in paragraphes:
        acc.ajouter(para, joindre_lignes(para.lignes, vocab))
    acc.vider()
    return acc.passages


def extraire_regles(dossier: Path) -> list[Passage]:
    """Passages des deux livres de règles présents dans `dossier`."""
    passages: list[Passage] = []
    for nom_fichier, livre in LIVRES.items():
        pdf = dossier / nom_fichier
        if not pdf.is_file():
            raise FileNotFoundError(f"PDF de règles introuvable : {pdf}")
        passages.extend(extraire_livre(pdf, livre))
    return passages
