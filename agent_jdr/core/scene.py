"""État de scène : le contexte dans lequel les PNJ s'expriment.

Immuable et sérialisable en JSON (réutilisable tel quel par le back-end web).
Toute modification renvoie une nouvelle scène.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    lieu: str = Field(min_length=1)
    moment: str = Field(min_length=1)
    ambiance: str = ""
    pnj_presents: tuple[str, ...] = Field(default=(), description="Ids des fiches PNJ")
    pj_presents: tuple[str, ...] = ()
    enjeux: str = ""
    faits_etablis: tuple[str, ...] = Field(default=(), description="Ordre chronologique")

    def avec_fait(self, fait: str) -> Scene:
        """Nouvelle scène où `fait` s'ajoute aux faits établis."""
        fait = fait.strip()
        if not fait:
            raise ValueError("Un fait établi ne peut pas être vide")
        return self.model_copy(update={"faits_etablis": (*self.faits_etablis, fait)})

    def vers_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def depuis_json(cls, texte: str) -> Scene:
        return cls.model_validate_json(texte)
