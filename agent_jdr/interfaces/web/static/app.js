"use strict";
// Interface web de l'assistant du meneur. Aucun texte venant du serveur ou du modèle
// n'est inséré comme HTML (sauf le manuel, produit par le serveur depuis MANUEL.md).

const $ = (sel) => document.querySelector(sel);

function el(tag, props = {}, ...enfants) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (k in n) n[k] = v;
    else n.setAttribute(k, v);
  }
  for (const e of enfants.flat()) if (e != null) n.append(e);
  return n;
}

async function api(methode, url, corps) {
  const options = { method: methode, headers: {} };
  if (corps !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(corps);
  }
  let rep;
  try {
    rep = await fetch(url, options);
  } catch {
    throw new Error("Serveur injoignable. La commande « uv run web » est-elle toujours lancée ?");
  }
  if (rep.status === 204) return null;
  const donnees = await rep.json().catch(() => ({}));
  if (!rep.ok) throw Object.assign(new Error(donnees.erreur || `Erreur ${rep.status}`), { champs: donnees.champs || {} });
  return donnees;
}

function notifier(message, erreur = false) {
  const n = el("div", { class: "notification" + (erreur ? " erreur" : ""), textContent: message });
  $("#notifications").append(n);
  setTimeout(() => n.remove(), erreur ? 9000 : 3500);
}

function confirmer(texte, libelle = "Confirmer") {
  const dlg = $("#dlg-confirmer");
  $("#confirmer-texte").textContent = texte;
  $("#confirmer-oui").textContent = libelle;
  dlg.returnValue = "";
  dlg.showModal();
  return new Promise((ok) => dlg.addEventListener("close", () => ok(dlg.returnValue === "oui"), { once: true }));
}

async function occupe(bouton, travail) {
  bouton.disabled = true;
  try { return await travail(); } finally { bouton.disabled = false; }
}

// Entrée envoie, Maj+Entrée fait une nouvelle ligne.
function envoiParEntree(textarea, formulaire) {
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      formulaire.requestSubmit();
    }
  });
}

// Texte du PNJ : les *gestes* entre astérisques en italique.
function texteAvecGestes(texte) {
  return texte.split(/(\*[^*\n]+\*)/).map((m) =>
    /^\*[^*\n]+\*$/.test(m) ? el("em", { textContent: m.slice(1, -1) }) : document.createTextNode(m));
}

function dateCourte(iso) {
  return new Date(iso).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

// ============================ Onglets ============================

function afficherVue(nom) {
  for (const b of document.querySelectorAll(".onglet")) {
    const actif = b.dataset.vue === nom;
    b.classList.toggle("actif", actif);
    b.setAttribute("aria-selected", actif);
  }
  $("#vue-regles").classList.toggle("cache", nom !== "regles");
  $("#vue-pnj").classList.toggle("cache", nom !== "pnj");
  localStorage.setItem("vue", nom);
  if (nom === "pnj") chargerSessions();
}
for (const b of document.querySelectorAll(".onglet")) b.addEventListener("click", () => afficherVue(b.dataset.vue));

// ============================ Règles ============================

function carteChargement(question) {
  return el("article", { class: "carte reponse" },
    el("p", { class: "question", textContent: question }),
    el("p", { class: "chargement", textContent: "Recherche dans les livres et rédaction de la réponse" }));
}

function carteReponse(question, r) {
  const carte = el("article", { class: "carte reponse" }, el("p", { class: "question", textContent: question }));
  carte.append(el("div", { class: "meta", textContent: r.modele }));
  const sources = r.sources.map((s, i) => el("div", { class: "source" },
    el("div", { class: "ref", textContent: `[${i + 1}] ${s.reference}` }),
    s.extraits.map((x) => el("blockquote", { textContent: x.split(/\s+/).join(" ") })),
    el("details", {}, el("summary", { textContent: "Voir le passage complet" }), el("div", { class: "passage", textContent: s.texte }))));
  const corps = el("div", { class: "corps" });
  for (const seg of r.segments) {
    corps.append(seg.texte);
    for (const n of seg.sources) {
      corps.append(el("button", {
        class: "renvoi", textContent: `[${n}]`, title: r.sources[n - 1]?.reference || "",
        onclick: () => {
          const cible = sources[n - 1];
          cible.scrollIntoView({ behavior: "smooth", block: "center" });
          cible.classList.add("surbrillance");
          setTimeout(() => cible.classList.remove("surbrillance"), 1500);
        },
      }));
    }
  }
  carte.append(corps);
  if (sources.length) carte.append(el("section", { class: "sources" }, el("h3", { textContent: "Sources" }), sources));
  if (r.extraits_ecartes) {
    carte.append(el("p", { class: "petit", textContent:
      `${r.extraits_ecartes} extrait(s) cité(s) par le modèle introuvable(s) mot pour mot dans les passages : écarté(s) des sources.` }));
  }
  return carte;
}

function cartePassages(question, r) {
  const carte = el("article", { class: "carte reponse" },
    el("p", { class: "question", textContent: question }),
    el("div", { class: "meta", textContent: `Passages trouvés (sans appel au modèle) : ${r.passages.length}` }));
  if (!r.passages.length) carte.append(el("p", { textContent: "Aucun passage ne correspond. Essayez d'autres mots des livres." }));
  for (const p of r.passages) {
    carte.append(el("div", { class: "source" },
      el("div", { class: "ref", textContent: p.reference }),
      el("details", {}, el("summary", { textContent: p.texte.slice(0, 160).replace(/\s+/g, " ") + "…" }),
        el("div", { class: "passage", textContent: p.texte }))));
  }
  return carte;
}

async function poserQuestion(brut, bouton) {
  const question = $("#question").value.trim();
  if (!question) { $("#question").focus(); return; }
  const n = parseInt($("#nb-passages").value, 10);
  const attente = carteChargement(question);
  $("#resultats-regles").prepend(attente);
  await occupe(bouton, async () => {
    try {
      const r = await api("POST", "/api/regles", { question, brut, passages: Number.isFinite(n) ? n : null });
      attente.replaceWith(brut ? cartePassages(question, r) : carteReponse(question, r));
      $("#question").value = "";
    } catch (e) {
      attente.remove();
      notifier(e.message, true);
    }
  });
}

$("#form-regles").addEventListener("submit", (e) => { e.preventDefault(); poserQuestion(false, e.submitter || $("#form-regles .primaire")); });
$("#btn-brut").addEventListener("click", (e) => poserQuestion(true, e.currentTarget));
envoiParEntree($("#question"), $("#form-regles"));

// ============================ PNJ ============================

let sessionCourante = null;

async function chargerSessions() {
  let sessions;
  try { sessions = await api("GET", "/api/sessions"); } catch (e) { notifier(e.message, true); return; }
  const liste = $("#liste-sessions");
  liste.replaceChildren();
  if (!sessions.length) liste.append(el("li", { class: "petit", textContent: "Aucune session pour l'instant." }));
  for (const s of sessions) {
    liste.append(el("li", {
      class: s.id === sessionCourante?.id ? "actif" : "", onclick: () => ouvrirSession(s.id),
    },
      el("div", { class: "nom", textContent: `${s.persona_nom} ↔ ${s.pj}` }),
      el("div", { class: "details", textContent: `${s.lieu} · ${s.echanges} échange(s) · ${dateCourte(s.modifie_le)}` })));
  }
  if (!sessionCourante) {
    const derniere = localStorage.getItem("session");
    if (derniere && sessions.some((s) => s.id === derniere)) ouvrirSession(derniere);
  }
}

async function ouvrirSession(id) {
  try { afficherSession(await api("GET", `/api/sessions/${id}`)); }
  catch (e) { notifier(e.message, true); localStorage.removeItem("session"); }
  chargerSessions();
}

function bulle(tour, session) {
  if (tour.locuteur === "joueur") {
    return el("div", { class: "bulle joueur" }, el("span", { class: "auteur", textContent: tour.pj || session.pj }), tour.texte);
  }
  const b = el("div", { class: "bulle pnj" }, el("span", { class: "auteur", textContent: session.persona_nom }), texteAvecGestes(tour.texte));
  if (tour.regles?.length) b.append(el("div", { class: "regles", textContent: "Règles consultées : " + tour.regles.join(" ; ") }));
  return b;
}

function afficherSession(s) {
  sessionCourante = s;
  localStorage.setItem("session", s.id);
  $("#sans-session").classList.add("cache");
  $("#session").classList.remove("cache");
  $("#session-titre").textContent = `${s.persona_nom} ↔ ${s.pj}`;
  $("#session-scene").textContent = `${s.scene.lieu} · ${s.scene.moment}`;
  const details = [["Lieu", s.scene.lieu], ["Moment", s.scene.moment], ["Ambiance", s.scene.ambiance], ["Enjeux", s.scene.enjeux]];
  $("#details-scene").replaceChildren(...details.filter(([, v]) => v).flatMap(([k, v]) => [el("dt", { textContent: k }), el("dd", { textContent: v })]));
  $("#liste-faits").replaceChildren(...(s.scene.faits_etablis.length
    ? s.scene.faits_etablis.map((f) => el("li", { textContent: f }))
    : [el("li", { class: "petit", textContent: "Aucun fait pour l'instant." })]));
  const fil = $("#fil");
  fil.replaceChildren(...s.historique.map((t) => bulle(t, s)));
  if (!s.historique.length) fil.append(el("p", { class: "vide-fil", textContent: `Dites quelque chose à ${s.persona_nom}…` }));
  fil.scrollTop = fil.scrollHeight;
  $("#message").focus();
}

$("#form-message").addEventListener("submit", async (e) => {
  e.preventDefault();
  const s = sessionCourante;
  const texte = $("#message").value.trim();
  if (!s || !texte) return;
  const fil = $("#fil");
  fil.querySelector(".vide-fil")?.remove();
  const enAttente = [
    bulle({ locuteur: "joueur", texte, pj: s.pj }, s),
    el("div", { class: "bulle pnj" }, el("span", { class: "auteur", textContent: s.persona_nom }), el("span", { class: "chargement", textContent: "réfléchit" })),
  ];
  fil.append(...enAttente);
  fil.scrollTop = fil.scrollHeight;
  $("#message").value = "";
  await occupe(e.submitter || $("#form-message .primaire"), async () => {
    try {
      const maj = await api("POST", `/api/sessions/${s.id}/messages`, { texte });
      if (sessionCourante?.id === s.id) afficherSession(maj);
      chargerSessions();
    } catch (err) {
      enAttente.forEach((n) => n.remove());
      fil.append(el("div", { class: "bulle erreur", textContent: `${err.message}\n(tour non enregistré ; votre texte a été remis dans la zone de saisie)` }));
      fil.scrollTop = fil.scrollHeight;
      if (!$("#message").value) $("#message").value = texte;
    }
  });
});
envoiParEntree($("#message"), $("#form-message"));

$("#btn-scene").addEventListener("click", (e) => {
  const panneau = $("#panneau-scene");
  panneau.classList.toggle("cache");
  e.currentTarget.setAttribute("aria-expanded", !panneau.classList.contains("cache"));
});

$("#form-fait").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fait = $("#nouveau-fait").value.trim();
  if (!fait || !sessionCourante) return;
  try {
    afficherSession(await api("POST", `/api/sessions/${sessionCourante.id}/faits`, { fait }));
    $("#nouveau-fait").value = "";
    notifier("Fait ajouté à la scène.");
  } catch (err) { notifier(err.message, true); }
});

$("#btn-effacer-historique").addEventListener("click", async () => {
  const s = sessionCourante;
  if (!s || !await confirmer(`Effacer tous les échanges avec ${s.persona_nom} ? Le PNJ, le PJ, la scène et les faits sont conservés.`, "Effacer l'historique")) return;
  try {
    afficherSession(await api("DELETE", `/api/sessions/${s.id}/historique`));
    chargerSessions();
    notifier("Historique effacé.");
  } catch (err) { notifier(err.message, true); }
});

$("#btn-supprimer-session").addEventListener("click", async () => {
  const s = sessionCourante;
  if (!s || !await confirmer(`Supprimer définitivement la session « ${s.persona_nom} ↔ ${s.pj} » et tout son historique ?`, "Supprimer")) return;
  try {
    await api("DELETE", `/api/sessions/${s.id}`);
    sessionCourante = null;
    localStorage.removeItem("session");
    $("#session").classList.add("cache");
    $("#sans-session").classList.remove("cache");
    chargerSessions();
    notifier("Session supprimée.");
  } catch (err) { notifier(err.message, true); }
});

async function ouvrirNouvelleSession(preselection = null) {
  let personas;
  try { personas = await api("GET", "/api/personas"); } catch (e) { notifier(e.message, true); return; }
  if (!personas.length) { ouvrirNouveauPnj(); notifier("Aucun PNJ pour l'instant : commencez par en créer un."); return; }
  $("#ns-persona").replaceChildren(...personas.map((p) => el("option", {
    value: p.id, textContent: `${p.nom} — ${p.role}`, selected: p.id === preselection,
  })));
  $("#ns-pj").value = localStorage.getItem("pj") || "";
  $("#dlg-session").showModal();
  (preselection ? $("#ns-pj") : $("#ns-persona")).focus();
}
$("#btn-nouvelle-session").addEventListener("click", () => ouvrirNouvelleSession());
$("#btn-ns-creer-pnj").addEventListener("click", () => { $("#dlg-session").close(); ouvrirNouveauPnj(); });

$("#form-session").addEventListener("submit", async (e) => {
  e.preventDefault();
  const corps = {
    persona: $("#ns-persona").value, pj: $("#ns-pj").value.trim(), lieu: $("#ns-lieu").value.trim(),
    moment: $("#ns-moment").value.trim(), ambiance: $("#ns-ambiance").value.trim(), enjeux: $("#ns-enjeux").value.trim(),
  };
  try {
    const s = await api("POST", "/api/sessions", corps);
    localStorage.setItem("pj", corps.pj);
    $("#dlg-session").close();
    $("#form-session").reset();
    afficherSession(s);
    chargerSessions();
  } catch (err) { notifier(err.message, true); }
});

// ============================ Fenêtres : fermeture ============================

for (const b of document.querySelectorAll("dialog .fermer")) b.addEventListener("click", () => b.closest("dialog").close());
for (const d of document.querySelectorAll("dialog.fenetre")) {
  d.addEventListener("click", (e) => { if (e.target === d) d.close(); }); // clic sur le fond
}

// ============================ Aide ============================

let manuelCharge = false;
$("#btn-aide").addEventListener("click", async () => {
  $("#dlg-aide").showModal();
  if (manuelCharge) return;
  try {
    const { html } = await api("GET", "/api/manuel");
    const article = $("#contenu-manuel");
    article.innerHTML = html; // produit par le serveur depuis MANUEL.md (fichier du projet)
    for (const a of article.querySelectorAll('a[href^="#"]')) {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)))?.scrollIntoView({ behavior: "smooth" });
      });
    }
    manuelCharge = true;
  } catch (e) { $("#contenu-manuel").textContent = e.message; }
});

// ============================ Configuration ============================

const USAGES = {
  questions_de_regles: { titre: "Questions de règles", detail: "Onglet Règles · clé « recherche-apikey »" },
  dialogue: { titre: "Dialogue avec les PNJ", detail: "Onglet PNJ · clé « personas-apikey »" },
};
const FOURNISSEURS = { anthropic: "Anthropic (Claude)", openai: "OpenAI (GPT)" };
const PREFIXE_CLE = { anthropic: "sk-ant-", openai: "sk-" };

function afficherPanneauConfig(nom) {
  for (const b of document.querySelectorAll(".onglet-config")) b.classList.toggle("actif", b.dataset.panneau === nom);
  $("#panneau-simple").classList.toggle("cache", nom !== "simple");
  $("#panneau-avance").classList.toggle("cache", nom !== "avance");
}
for (const b of document.querySelectorAll(".onglet-config")) b.addEventListener("click", () => afficherPanneauConfig(b.dataset.panneau));

function etatCle(u) {
  if (u.cle_source === "fichier") return [el("code", { textContent: u.cle_masquee }), el("span", { class: "pastille ok", textContent: "fichier de secrets" })];
  if (u.cle_source === "environnement") return [el("code", { textContent: u.cle_masquee }), el("span", { class: "pastille ok", textContent: u.variable_env })];
  return [el("span", { class: "pastille absente", textContent: "aucune clé" })];
}

function carteUsage(section, u, catalogue) {
  const choixFournisseur = el("select", {}, Object.entries(FOURNISSEURS).map(([v, t]) => el("option", { value: v, textContent: t, selected: v === u.fournisseur })));
  const choixModele = el("select");
  const description = el("div", { class: "description-modele" });
  const cle = el("input", { type: "password", autocomplete: "off", placeholder: "Nouvelle clé (laisser vide pour garder l'actuelle)" });
  const indication = el("div", { class: "petit" });
  let effacer = false;

  function remplirModeles() {
    const f = choixFournisseur.value;
    const modeles = [...(catalogue?.[f] || [])];
    if (f === u.fournisseur && !modeles.some((m) => m.nom === u.modele)) modeles.unshift({ nom: u.modele, description: "modèle actuel, absent du catalogue", prix: "" });
    choixModele.replaceChildren(...modeles.map((m) => el("option", { value: m.nom, textContent: m.nom, selected: f === u.fournisseur && m.nom === u.modele })));
    choixModele._modeles = modeles;
    decrire();
    indication.textContent = `Clé ${FOURNISSEURS[f]} : commence par « ${PREFIXE_CLE[f]} ».` +
      (f !== u.fournisseur ? " Changement de fournisseur : pensez à saisir la clé correspondante." : "");
  }
  function decrire() {
    const m = choixModele._modeles?.find((x) => x.nom === choixModele.value);
    description.textContent = m ? [m.description, m.prix && `${m.prix} par million de jetons (entrée / sortie)`].filter(Boolean).join(" · ") : "";
  }
  choixFournisseur.addEventListener("change", remplirModeles);
  choixModele.addEventListener("change", decrire);
  remplirModeles();

  const boutonEffacer = el("button", {
    type: "button", class: "secondaire", textContent: "Effacer la clé",
    disabled: u.cle_source !== "fichier",
    title: "Retire la clé du fichier de secrets",
    onclick: async () => {
      if (!await confirmer(`Retirer la clé de « ${USAGES[section].titre} » du fichier de secrets ?`, "Effacer la clé")) return;
      effacer = true;
      enregistrer.click();
    },
  });
  const enregistrer = el("button", {
    type: "button", class: "primaire", textContent: "Enregistrer",
    onclick: (e) => occupe(e.currentTarget, async () => {
      const corps = { section, fournisseur: choixFournisseur.value, modele: choixModele.value, cle: effacer ? "" : (cle.value.trim() || null) };
      effacer = false;
      try {
        afficherConfig(await api("PUT", "/api/config/usage", corps));
        notifier(`${USAGES[section].titre} : réglages enregistrés.`);
      } catch (err) { notifier(err.message, true); }
    }),
  });

  return el("section", { class: "carte usage" },
    el("h3", { textContent: USAGES[section].titre }),
    el("div", { class: "petit", textContent: USAGES[section].detail }),
    el("div", { class: "champs" },
      el("label", {}, "Fournisseur", choixFournisseur),
      el("label", {}, "Modèle", choixModele, description),
      el("div", {}, el("div", { class: "petit", textContent: "Clé API actuelle" }), el("div", { class: "cle-actuelle" }, etatCle(u))),
      el("label", {}, "Nouvelle clé API", cle, indication)),
    el("div", { class: "ligne-actions" }, boutonEffacer, el("span", { class: "espace" }), enregistrer));
}

let texteConfigCharge = "";
function afficherConfig(etat) {
  const alerte = $("#config-erreur");
  alerte.textContent = etat.erreur || "";
  alerte.classList.toggle("cache", !etat.erreur);
  $("#chemin-config").textContent = `Fichier : ${etat.chemin}`;
  texteConfigCharge = etat.texte;
  $("#texte-config").value = etat.texte;
  const usages = $("#usages");
  if (!etat.usages) {
    usages.replaceChildren(el("p", { textContent: "Corrigez d'abord le fichier config.yaml (onglet « Fichier config.yaml »)." }));
    afficherPanneauConfig("avance");
    return;
  }
  usages.replaceChildren(...Object.entries(etat.usages).map(([section, u]) => carteUsage(section, u, etat.catalogue)));
}

$("#btn-config").addEventListener("click", async () => {
  try {
    afficherConfig(await api("GET", "/api/config"));
    $("#dlg-config").showModal();
  } catch (e) { notifier(e.message, true); }
});

$("#btn-enregistrer-config").addEventListener("click", (e) => occupe(e.currentTarget, async () => {
  try {
    afficherConfig(await api("PUT", "/api/config", { texte: $("#texte-config").value }));
    notifier("config.yaml enregistré.");
  } catch (err) {
    const alerte = $("#config-erreur");
    alerte.textContent = err.message;
    alerte.classList.remove("cache");
  }
}));

$("#btn-recharger-config").addEventListener("click", () => {
  $("#texte-config").value = texteConfigCharge;
  $("#config-erreur").classList.add("cache");
});

$("#texte-config").addEventListener("keydown", (e) => {
  if (e.key === "Tab") { // indentation par espaces (YAML refuse les tabulations)
    e.preventDefault();
    const t = e.currentTarget;
    t.setRangeText("  ", t.selectionStart, t.selectionEnd, "end");
  }
});

$("#dlg-config").addEventListener("close", () => {
  if ($("#texte-config").value !== texteConfigCharge) notifier("Modifications de config.yaml non enregistrées : abandonnées.", true);
});

// ============================ Nouveau PNJ ============================
// Formulaire pré-rempli (modèle guidé ou copie d'un PNJ). Chaque champ garde sa valeur de
// départ (data-depart) : un champ encore identique est surligné, et signalé avant l'envoi.

const LISTES_PNJ = ["parole.tics", "parole.exemples", "objectifs", "connaissances"];
let idSaisiALaMain = false;

function identifiantDepuisNom(nom) {
  return nom.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

const valeurChemin = (obj, chemin) => chemin.split(".").reduce((o, k) => o?.[k], obj);

function champTexte(valeur, props = {}) {
  const champ = el("input", { value: valeur ?? "", ...props });
  champ.dataset.depart = valeur ?? "";
  champ.addEventListener("input", marquerInchanges);
  return champ;
}

function ligneListe(conteneur, valeur) {
  const ligne = el("div", { class: "ligne-liste" }, champTexte(valeur),
    el("button", { type: "button", class: "bouton-retirer", title: "Retirer", textContent: "✕",
      onclick: () => { ligne.remove(); marquerInchanges(); } }));
  conteneur.querySelector(".lignes").append(ligne);
  return ligne;
}

function remplirListe(conteneur, valeurs) {
  conteneur.replaceChildren(
    el("div", { class: "titre-champ" }, conteneur.dataset.libelle, " ", el("span", { class: "petit", textContent: `(${conteneur.dataset.aide})` })),
    el("div", { class: "lignes" }),
    el("button", { type: "button", class: "secondaire petit-bouton", textContent: "+ Ajouter",
      onclick: () => ligneListe(conteneur, "").querySelector("input").focus() }));
  const elements = valeurs?.length ? valeurs : [""];
  for (const v of elements) ligneListe(conteneur, v);
}

function blocSecret(secret = {}) {
  const bloc = el("div", { class: "secret" },
    el("div", { class: "champs-secret" },
      el("label", {}, "Le secret", champTexte(secret.contenu, { class: "secret-contenu" })),
      el("label", {}, "Seule circonstance où il le révèle (vide = jamais)", champTexte(secret.condition_revelation, { class: "secret-condition" }))),
    el("button", { type: "button", class: "bouton-retirer", title: "Retirer ce secret", textContent: "✕",
      onclick: () => { bloc.remove(); marquerInchanges(); } }));
  $("#pnj-secrets").append(bloc);
  return bloc;
}

function remplirFiche(fiche) {
  const form = $("#form-pnj");
  for (const champ of form.querySelectorAll("[data-champ]:not(.ligne-liste *, .secret *)")) {
    const v = valeurChemin(fiche, champ.dataset.champ) ?? "";
    champ.value = v;
    champ.dataset.depart = v;
    champ.oninput = marquerInchanges;
  }
  for (const c of form.querySelectorAll("[data-liste]")) remplirListe(c, valeurChemin(fiche, c.dataset.liste));
  $("#pnj-secrets").replaceChildren();
  for (const s of fiche.secrets || []) blocSecret(s);
  const id = form.querySelector('[data-champ="id"]');
  id.value = id.dataset.depart = fiche.id || identifiantDepuisNom(fiche.nom || "");
  idSaisiALaMain = false;
  effacerErreursPnj();
  marquerInchanges();
}

function champsSaisis() {
  return [...$("#form-pnj .corps-pnj").querySelectorAll("input, textarea")];
}

function marquerInchanges() {
  for (const c of champsSaisis()) c.classList.toggle("inchange", c.value.trim() !== "" && c.value === c.dataset.depart);
}

function lireFiche() {
  const form = $("#form-pnj");
  const fiche = { parole: {} };
  const poser = (chemin, v) => {
    const cles = chemin.split(".");
    const cible = cles.slice(0, -1).reduce((o, k) => (o[k] ??= {}), fiche);
    cible[cles.at(-1)] = v;
  };
  for (const champ of form.querySelectorAll("[data-champ]:not(.ligne-liste *, .secret *)")) poser(champ.dataset.champ, champ.value.trim());
  for (const c of form.querySelectorAll("[data-liste]")) {
    const valeurs = [];
    for (const input of c.querySelectorAll(".ligne-liste input")) {
      delete input.dataset.champ;
      const v = input.value.trim();
      if (v) { input.dataset.champ = `${c.dataset.liste}.${valeurs.length}`; valeurs.push(v); }
    }
    poser(c.dataset.liste, valeurs);
  }
  fiche.secrets = [];
  for (const bloc of $("#pnj-secrets").children) {
    const contenu = bloc.querySelector(".secret-contenu"), condition = bloc.querySelector(".secret-condition");
    delete contenu.dataset.champ; delete condition.dataset.champ;
    if (!contenu.value.trim() && !condition.value.trim()) continue;
    const i = fiche.secrets.length;
    contenu.dataset.champ = `secrets.${i}.contenu`;
    condition.dataset.champ = `secrets.${i}.condition_revelation`;
    fiche.secrets.push({ contenu: contenu.value.trim(), condition_revelation: condition.value.trim() || null });
  }
  return fiche;
}

function effacerErreursPnj() {
  $("#pnj-erreur").classList.add("cache");
  for (const n of document.querySelectorAll("#form-pnj .message-champ")) n.remove();
  for (const n of document.querySelectorAll("#form-pnj .champ-erreur")) n.classList.remove("champ-erreur");
}

function afficherErreursPnj(message, champs = {}) {
  effacerErreursPnj();
  const alerte = $("#pnj-erreur");
  alerte.textContent = message;
  alerte.classList.remove("cache");
  let premier = null;
  for (const [chemin, texte] of Object.entries(champs)) {
    const cible = document.querySelector(`#form-pnj [data-champ="${chemin}"]`)
      || document.querySelector(`#form-pnj [data-liste="${chemin}"] input`)
      || (chemin === "secrets" ? $("#btn-ajouter-secret") : null);
    if (!cible) continue;
    cible.classList.add("champ-erreur");
    cible.closest("label, .ligne-liste, .liste-champ")?.after(el("div", { class: "message-champ", textContent: texte }));
    premier ??= cible;
  }
  (premier || alerte).scrollIntoView({ behavior: "smooth", block: "center" });
  premier?.focus?.();
}

let personasConnus = [];
async function chargerDepart(valeur) {
  if (valeur === "__vierge") return remplirFiche({});
  if (valeur === "__modele") return remplirFiche(await api("GET", "/api/personas/modele"));
  const fiche = await api("GET", `/api/personas/${valeur}`);
  remplirFiche({ ...fiche, id: "", nom: "" }); // une copie doit porter un autre nom
  $('#form-pnj [data-champ="nom"]').focus();
}

async function ouvrirNouveauPnj() {
  try {
    personasConnus = await api("GET", "/api/personas");
    $("#pnj-depart").replaceChildren(
      el("option", { value: "__modele", textContent: "Modèle guidé (exemple à adapter)" }),
      el("option", { value: "__vierge", textContent: "Fiche vierge" }),
      ...personasConnus.map((p) => el("option", { value: p.id, textContent: `Copie de : ${p.nom}` })));
    await chargerDepart("__modele");
    $("#dlg-pnj").showModal();
    $("#form-pnj .corps-pnj").scrollTop = 0;
    $('#form-pnj [data-champ="nom"]').select();
  } catch (e) { notifier(e.message, true); }
}

$("#btn-nouveau-pnj").addEventListener("click", ouvrirNouveauPnj);
$("#btn-ajouter-secret").addEventListener("click", () => blocSecret().querySelector("input").focus());

let departPrecedent = "__modele";
$("#pnj-depart").addEventListener("focus", (e) => { departPrecedent = e.currentTarget.value; });
$("#pnj-depart").addEventListener("change", async (e) => {
  const select = e.currentTarget;
  const saisie = champsSaisis().some((c) => c.value !== c.dataset.depart);
  if (saisie && !await confirmer("Remplacer votre saisie par ce point de départ ? Ce que vous avez écrit sera perdu.", "Remplacer")) {
    select.value = departPrecedent;
    return;
  }
  departPrecedent = select.value;
  try { await chargerDepart(select.value); } catch (err) { notifier(err.message, true); }
});

$('#form-pnj [data-champ="nom"]').addEventListener("input", (e) => {
  if (!idSaisiALaMain) $('#form-pnj [data-champ="id"]').value = identifiantDepuisNom(e.currentTarget.value);
});
$('#form-pnj [data-champ="id"]').addEventListener("input", (e) => { idSaisiALaMain = e.currentTarget.value !== ""; });

$("#form-pnj").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fiche = lireFiche();
  const inchanges = champsSaisis().filter((c) => c.classList.contains("inchange") && c.dataset.champ !== "id");
  if (inchanges.length && !await confirmer(
    `${inchanges.length} champ(s) n'ont pas été modifiés depuis le point de départ (surlignés). Créer le PNJ quand même ?`, "Créer quand même")) {
    inchanges[0].scrollIntoView({ behavior: "smooth", block: "center" });
    inchanges[0].focus();
    return;
  }
  await occupe(e.submitter || $("#form-pnj .primaire"), async () => {
    try {
      const p = await api("POST", "/api/personas", { fiche });
      $("#dlg-pnj").close();
      notifier(`PNJ « ${p.nom} » créé.`);
      ouvrirNouvelleSession(p.id);
    } catch (err) { afficherErreursPnj(err.message, err.champs); }
  });
});

// ============================ Démarrage ============================

afficherVue(localStorage.getItem("vue") === "pnj" ? "pnj" : "regles");
