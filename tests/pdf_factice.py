"""PDF minuscules générés pour les tests (PyMuPDF, dépendance de construction)."""

from pathlib import Path


def ecrire_pdf(chemin: Path, pages: list[str], sommaire: list[tuple[int, str, int]] | None = None) -> Path:
    """Un PDF avec une page par texte ; `sommaire` : (niveau, titre, page) — table des matières intégrée."""
    import pymupdf

    with pymupdf.open() as doc:
        for texte in pages:
            page = doc.new_page()
            page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), texte, fontsize=11)
        if sommaire:
            doc.set_toc(sommaire)
        doc.save(chemin)
    return chemin
