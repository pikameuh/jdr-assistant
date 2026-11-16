"""Interface web : `uv run web` puis ouvrir http://127.0.0.1:8000.

Client mince, comme la CLI : toute la logique est dans `core`. La configuration est
relue à chaque requête, donc une modification (fenêtre Config ou éditeur de texte)
s'applique tout de suite, sans relancer le serveur.

Sécurité : prévu pour un usage local (127.0.0.1), sans authentification. Les clés
API ne sont jamais renvoyées au navigateur, seulement leur forme masquée.
"""

from __future__ import annotations

import argparse
import os
import re
import socket
import sys
import threading
import webbrowser
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

import markdown
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from agent_jdr.core import rules_qa
from agent_jdr.core.config import (
    CONFIG_DEFAUT,
    ENTREE_SECRETS,
    RACINE,
    Config,
    ConfigInvalide,
    Secrets,
    charger_catalogue,
    charger_config,
    charger_secrets,
)
from agent_jdr.core.edition_config import (
    choisir_modele,
    enregistrer_cles,
    enregistrer_config,
    masquer_cle,
    verifier_cle,
)
from agent_jdr.core.fournisseurs import creer_fournisseur
from agent_jdr.core.fournisseurs.base import ErreurFournisseur, IdentifiantsAbsents, ReponseIncomplete
from agent_jdr.core.persona import (
    FicheRefusee,
    Persona,
    PersonaInvalide,
    charger_modele_de_fiche,
    charger_personas,
    creer_fiche,
)
from agent_jdr.core.rules_index import RulesIndex
from agent_jdr.core.scene import Scene
from agent_jdr.core.sessions import (
    DepotSessions,
    SessionDialogue,
    SessionInconnue,
    jouer_tour,
    nouvelle_session,
)

STATIQUE = Path(__file__).parent / "static"
MANUEL = RACINE / "MANUEL.md"
VARIABLE_ENV = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
CONSEIL_CLE_WEB = "Saisissez la clé dans la fenêtre Config (bouton ⚙ en haut à droite)."
Section = Literal["questions_de_regles", "dialogue"]


class ErreurApi(Exception):
    def __init__(self, statut: int, message: str, champs: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.statut = statut
        self.message = message
        self.champs = champs or {}


# --- Corps des requêtes ----------------------------------------------------------------


class QuestionRegles(BaseModel):
    question: str = Field(min_length=1)
    passages: int | None = Field(default=None, ge=1, le=50)
    brut: bool = False


class TexteConfig(BaseModel):
    texte: str


class ReglagesUsage(BaseModel):
    section: Section
    fournisseur: Literal["anthropic", "openai"]
    modele: str
    cle: str | None = None  # None = inchangée ; "" = effacer


class NouvelleSession(BaseModel):
    persona: str
    pj: str = Field(min_length=1)
    lieu: str = Field(min_length=1)
    moment: str = Field(min_length=1)
    ambiance: str = ""
    enjeux: str = ""


class Message(BaseModel):
    texte: str = Field(min_length=1)


class NouvelleFiche(BaseModel):
    fiche: dict[str, Any]


class Fait(BaseModel):
    fait: str = Field(min_length=1)


# --- Application -----------------------------------------------------------------------


def creer_app(
    chemin_config: Path = CONFIG_DEFAUT,
    fabrique_fournisseur: Callable[..., Any] = creer_fournisseur,
    hotes_autorises: tuple[str, ...] = ("127.0.0.1", "localhost"),
) -> FastAPI:
    """`fabrique_fournisseur` : remplacé par les tests ; `hotes_autorises` : protège
    contre le « DNS rebinding » (une page web malveillante visant 127.0.0.1)."""
    app = FastAPI(title="Assistant du meneur — Metal Adventures 1.5", docs_url=None, redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(hotes_autorises))
    app.mount("/static", StaticFiles(directory=STATIQUE), name="static")
    depots: dict[Path, DepotSessions] = {}
    verrou_config = threading.Lock()

    @app.exception_handler(ErreurApi)
    async def _erreur_api(_: Request, exc: ErreurApi) -> JSONResponse:
        return JSONResponse({"erreur": exc.message, "champs": exc.champs}, status_code=exc.statut)

    @app.exception_handler(RequestValidationError)
    async def _requete_invalide(_: Request, exc: RequestValidationError) -> JSONResponse:
        champs = ", ".join(str(e["loc"][-1]) for e in exc.errors())
        return JSONResponse({"erreur": f"Champ manquant ou incorrect : {champs}"}, status_code=422)

    def config() -> Config:
        try:
            return charger_config(chemin_config)
        except ConfigInvalide as e:
            raise ErreurApi(409, f"Configuration invalide (corrigez-la dans la fenêtre Config) :\n{e}") from e

    def secrets(cfg: Config) -> Secrets:
        try:
            return charger_secrets(cfg.fichiers.secrets)
        except ConfigInvalide as e:
            raise ErreurApi(409, f"Fichier de secrets invalide : {e}") from e

    def depot(cfg: Config) -> DepotSessions:
        dossier = cfg.fichiers.dossier_des_sessions
        return depots.setdefault(dossier, DepotSessions(dossier))

    def personas(cfg: Config) -> dict[str, Persona]:
        try:
            return charger_personas(cfg.fichiers.dossier_des_pnj)
        except PersonaInvalide as e:
            raise ErreurApi(409, str(e)) from e

    @contextmanager
    def index(cfg: Config) -> Iterator[RulesIndex]:
        try:
            idx = RulesIndex(cfg.fichiers.index_des_regles)
        except FileNotFoundError as e:
            raise ErreurApi(409, str(e)) from e
        with idx:
            yield idx

    @contextmanager
    def appel_modele() -> Iterator[None]:
        """Erreurs du fournisseur → message lisible."""
        try:
            yield
        except IdentifiantsAbsents as e:
            raise ErreurApi(401, f"{e}\n{CONSEIL_CLE_WEB}") from e
        except ReponseIncomplete as e:
            raise ErreurApi(502, f"{e} Vous pouvez reformuler.") from e
        except ErreurFournisseur as e:
            raise ErreurApi(502, str(e)) from e

    # --- Pages -----------------------------------------------------------------------

    @app.get("/", include_in_schema=False)
    def accueil() -> FileResponse:
        return FileResponse(STATIQUE / "index.html")

    @app.get("/api/manuel")
    def manuel() -> dict[str, str]:
        texte = MANUEL.read_text(encoding="utf-8")
        html = markdown.markdown(
            texte,
            extensions=["tables", "fenced_code", "toc", "sane_lists"],
            extension_configs={"toc": {"slugify": _ancre_github}},
        )
        return {"html": html}

    # --- Configuration ---------------------------------------------------------------

    def etat_config() -> dict[str, Any]:
        texte = chemin_config.read_text(encoding="utf-8")
        etat: dict[str, Any] = {
            "chemin": str(chemin_config), "texte": texte, "erreur": None, "usages": None, "catalogue": None,
        }
        try:
            cfg = charger_config(chemin_config)
            cles = charger_secrets(cfg.fichiers.secrets)
        except ConfigInvalide as e:
            etat["erreur"] = str(e)
            return etat
        etat["usages"] = {
            section: _usage(getattr(cfg, section), getattr(cles, attribut), cfg.fichiers.secrets)
            for section, attribut in (("questions_de_regles", "recherche"), ("dialogue", "personas"))
        }
        try:
            catalogue = charger_catalogue(cfg.fichiers.catalogue_des_modeles)
            etat["catalogue"] = catalogue.model_dump()
        except ConfigInvalide as e:
            etat["erreur"] = f"Catalogue des modèles : {e}"
        return etat

    @app.get("/api/config")
    def lire_config() -> dict[str, Any]:
        return etat_config()

    @app.put("/api/config")
    def ecrire_config(corps: TexteConfig) -> dict[str, Any]:
        with verrou_config:
            try:
                enregistrer_config(chemin_config, corps.texte)
            except ConfigInvalide as e:
                raise ErreurApi(422, f"Rien n'a été enregistré : {e}") from e
        return etat_config()

    @app.put("/api/config/usage")
    def regler_usage(corps: ReglagesUsage) -> dict[str, Any]:
        cfg = config()
        try:
            catalogue = charger_catalogue(cfg.fichiers.catalogue_des_modeles)
        except ConfigInvalide as e:
            raise ErreurApi(409, f"Catalogue des modèles : {e}") from e
        noms = [m.nom for m in catalogue.modeles(corps.fournisseur)]
        actuel = getattr(cfg, corps.section)
        hors_catalogue_actuel = corps.fournisseur == actuel.fournisseur and corps.modele == actuel.modele
        if corps.modele not in noms and not hors_catalogue_actuel:
            raise ErreurApi(422, f"Modèle « {corps.modele} » absent du catalogue pour {corps.fournisseur}.")
        with verrou_config:
            try:
                entree = ENTREE_SECRETS[corps.section]
                if corps.cle is not None:  # vérifiée avant de toucher à config.yaml
                    verifier_cle(entree, corps.cle)
                choisir_modele(chemin_config, corps.section, corps.fournisseur, corps.modele)
                if corps.cle is not None:
                    enregistrer_cles(cfg.fichiers.secrets, {entree: corps.cle})
            except ConfigInvalide as e:
                raise ErreurApi(422, f"Rien n'a été enregistré : {e}") from e
        return etat_config()

    # --- Questions de règles ---------------------------------------------------------

    @app.post("/api/regles")
    def question_regles(corps: QuestionRegles) -> dict[str, Any]:
        cfg = config()
        reglages = cfg.questions_de_regles
        limite = corps.passages or reglages.passages_envoyes
        with index(cfg) as idx:
            if corps.brut:
                return {"passages": [
                    {"reference": r.passage.reference(), "texte": r.passage.texte, "score": round(r.score, 2)}
                    for r in idx.rechercher(corps.question, limite)
                ]}
            fournisseur = fabrique_fournisseur(reglages, cle_api=secrets(cfg).recherche)
            with appel_modele():
                reponse = rules_qa.repondre(corps.question, idx, reglages, fournisseur, limite=limite)
        return {
            "segments": [{"texte": s.texte, "sources": list(s.sources)} for s in reponse.segments],
            "sources": [
                {"reference": s.passage.reference(), "extraits": list(s.extraits), "texte": s.passage.texte}
                for s in reponse.sources
            ],
            "extraits_ecartes": reponse.extraits_ecartes,
            "modele": f"{reglages.fournisseur} · {reglages.modele}",
        }

    # --- PNJ et sessions -------------------------------------------------------------

    @app.get("/api/personas")
    def lister_personas() -> list[dict[str, str]]:
        return [
            {"id": p.id, "nom": p.nom, "role": p.role, "espece": p.espece}
            for p in personas(config()).values()
        ]

    @app.get("/api/personas/modele")
    def modele_de_fiche() -> dict[str, Any]:
        cfg = config()
        try:
            return charger_modele_de_fiche(cfg.fichiers.modele_de_pnj)
        except PersonaInvalide as e:
            raise ErreurApi(409, str(e)) from e

    @app.get("/api/personas/{id_persona}")
    def fiche_persona(id_persona: str) -> dict[str, Any]:
        persona = personas(config()).get(id_persona)
        if persona is None:
            raise ErreurApi(404, f"PNJ inconnu « {id_persona} ».")
        return persona.model_dump(mode="json")

    @app.post("/api/personas", status_code=201)
    def creer_persona(corps: NouvelleFiche) -> dict[str, str]:
        cfg = config()
        personas(cfg)  # une fiche existante cassée est signalée avant d'en ajouter une
        try:
            persona = creer_fiche(cfg.fichiers.dossier_des_pnj, corps.fiche)
        except FicheRefusee as e:
            statut = 409 if "existe déjà" in e.erreurs.get("id", "") else 422
            raise ErreurApi(statut, str(e), e.erreurs) from e
        return {"id": persona.id, "nom": persona.nom, "role": persona.role, "espece": persona.espece}

    def vue_session(session: SessionDialogue, noms: dict[str, Persona]) -> dict[str, Any]:
        vue = session.model_dump(mode="json")
        persona = noms.get(session.persona)
        vue["persona_nom"] = persona.nom if persona else f"{session.persona} (fiche introuvable)"
        return vue

    def lire_session(cfg: Config, id_session: str) -> SessionDialogue:
        try:
            return depot(cfg).lire(id_session)
        except SessionInconnue as e:
            raise ErreurApi(404, "Session introuvable (supprimée ?).") from e

    @app.get("/api/sessions")
    def lister_sessions() -> list[dict[str, Any]]:
        cfg = config()
        noms = personas(cfg)
        return [
            {
                "id": s.id, "persona": s.persona, "pj": s.pj, "lieu": s.scene.lieu,
                "persona_nom": vue_session(s, noms)["persona_nom"],
                "echanges": sum(t.locuteur == "pnj" for t in s.historique),
                "modifie_le": s.modifie_le.isoformat(),
            }
            for s in depot(cfg).lister()
        ]

    @app.post("/api/sessions", status_code=201)
    def creer_session(corps: NouvelleSession) -> dict[str, Any]:
        cfg = config()
        noms = personas(cfg)
        if corps.persona not in noms:
            raise ErreurApi(404, f"PNJ inconnu « {corps.persona} ».")
        scene = Scene(
            lieu=corps.lieu, moment=corps.moment, ambiance=corps.ambiance, enjeux=corps.enjeux,
            pnj_presents=(corps.persona,), pj_presents=(corps.pj.strip(),),
        )
        session = nouvelle_session(noms[corps.persona], corps.pj, scene)
        depot(cfg).enregistrer(session)
        return vue_session(session, noms)

    @app.get("/api/sessions/{id_session}")
    def detail_session(id_session: str) -> dict[str, Any]:
        cfg = config()
        return vue_session(lire_session(cfg, id_session), personas(cfg))

    @app.delete("/api/sessions/{id_session}", status_code=204)
    def supprimer_session(id_session: str) -> None:
        cfg = config()
        with depot(cfg).verrou(id_session):
            try:
                depot(cfg).supprimer(id_session)
            except SessionInconnue as e:
                raise ErreurApi(404, "Session introuvable (déjà supprimée ?).") from e

    @app.delete("/api/sessions/{id_session}/historique")
    def effacer_historique(id_session: str) -> dict[str, Any]:
        cfg = config()
        with depot(cfg).verrou(id_session):
            session = lire_session(cfg, id_session).sans_historique()
            depot(cfg).enregistrer(session)
        return vue_session(session, personas(cfg))

    @app.post("/api/sessions/{id_session}/faits")
    def ajouter_fait(id_session: str, corps: Fait) -> dict[str, Any]:
        cfg = config()
        with depot(cfg).verrou(id_session):
            try:
                session = lire_session(cfg, id_session).avec_fait(corps.fait)
            except ValueError as e:
                raise ErreurApi(422, str(e)) from e
            depot(cfg).enregistrer(session)
        return vue_session(session, personas(cfg))

    @app.post("/api/sessions/{id_session}/messages")
    def parler(id_session: str, corps: Message) -> dict[str, Any]:
        cfg = config()
        noms = personas(cfg)
        reglages = cfg.dialogue
        with depot(cfg).verrou(id_session):
            session = lire_session(cfg, id_session)
            if session.persona not in noms:
                raise ErreurApi(409, f"Fiche PNJ « {session.persona} » introuvable.")
            fournisseur = fabrique_fournisseur(reglages, cle_api=secrets(cfg).personas)
            with index(cfg) as idx, appel_modele():
                try:
                    session, _ = jouer_tour(session, noms[session.persona], idx, reglages, fournisseur, corps.texte)
                except ValueError as e:
                    raise ErreurApi(422, str(e)) from e
            depot(cfg).enregistrer(session)
        return vue_session(session, noms)

    return app


def _ancre_github(titre: str, separateur: str) -> str:
    """Ancre d'un titre comme sur GitHub (liens du sommaire de MANUEL.md) : « Régler l'assistant : »
    → « régler-lassistant- »."""
    return re.sub(r"[^\w\- ]", "", titre.strip().lower()).replace(" ", separateur)


def _usage(reglages: Any, cle: str | None, fichier_secrets: Path) -> dict[str, Any]:
    """Fournisseur, modèle et état de la clé d'un usage (clé toujours masquée)."""
    if cle:
        source, affichee = "fichier", masquer_cle(cle)
    elif cle_env := os.environ.get(VARIABLE_ENV[reglages.fournisseur], "").strip():
        source, affichee = "environnement", masquer_cle(cle_env)
    else:
        source, affichee = "absente", ""
    return {
        "fournisseur": reglages.fournisseur,
        "modele": reglages.modele,
        "cle_masquee": affichee,
        "cle_source": source,
        "variable_env": VARIABLE_ENV[reglages.fournisseur],
        "fichier_secrets": str(fichier_secrets),
    }


def _port_libre(hote: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((hote, port))
        except OSError:
            return False
    return True


def main(argv: list[str] | None = None) -> int:
    import uvicorn

    parser = argparse.ArgumentParser(prog="web", description="Interface web de l'assistant du meneur.")
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAUT, help="fichier de configuration")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--hote", default="127.0.0.1", help="adresse d'écoute (défaut : cette machine seulement)")
    parser.add_argument("--sans-navigateur", action="store_true", help="ne pas ouvrir le navigateur")
    args = parser.parse_args(argv)

    if not args.config.is_file():
        print(f"Erreur : fichier de configuration introuvable : {args.config}", file=sys.stderr)
        return 1
    local = args.hote in ("127.0.0.1", "localhost")
    if not local:
        print(
            "Attention : l'interface est accessible depuis le réseau, sans mot de passe. "
            "Toute personne qui y accède peut modifier la configuration et utiliser vos clés API.",
            file=sys.stderr,
        )
    if not _port_libre(args.hote, args.port):
        print(
            f"Erreur : le port {args.port} est déjà utilisé (l'interface est peut-être déjà lancée "
            f"dans un autre terminal). Choisissez-en un autre, par exemple : uv run web --port {args.port + 1}",
            file=sys.stderr,
        )
        return 1
    app = creer_app(args.config.resolve(), hotes_autorises=("127.0.0.1", "localhost") if local else ("*",))
    adresse = f"http://{'127.0.0.1' if local else args.hote}:{args.port}"
    print(f"Interface web : {adresse}  (Ctrl+C pour arrêter)")
    if not args.sans_navigateur:
        threading.Timer(1.0, webbrowser.open, args=(adresse,)).start()
    uvicorn.run(app, host=args.hote, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
