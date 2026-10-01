// partAtlas — Oberfläche ohne Framework (wie pDMS). Aufbau nach dem 3MF
// Katalog: Seitenleiste, Raster, Inspektor. Das Raster ist virtuell: es
// zeichnet nur die sichtbaren Kacheln, damit 10 000 Modelle nicht den
// Browser lahmlegen (vermutete Ursache für „nicht gescheit“ bei 5 700).
"use strict";

const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const zustand = {
  modelle: [], ansicht: "alle", tags: new Set(), material: new Set(), ordner: "", format: "", suche: "", sammlung: "", sammlungen: [],
  auswahl: new Set(), layout: localStorageLesen("layout") === "liste" ? "liste" : "raster",
  sortierung: "name", gewaehlt: null, offen: new Set(JSON.parse(localStorageLesen("offen") || "[]")),
};

function localStorageLesen(k) { try { return localStorage.getItem("partatlas." + k); } catch { return null; } }
function localStorageSchreiben(k, v) { try { localStorage.setItem("partatlas." + k, v); } catch { /* egal */ } }

async function api(pfad, optionen = {}) {
  const antwort = await fetch(pfad, {
    ...optionen,
    headers: optionen.body ? { "Content-Type": "application/json" } : {},
    body: optionen.body ? JSON.stringify(optionen.body) : undefined,
  });
  const daten = await antwort.json().catch(() => ({}));
  if (!antwort.ok) throw new Error(daten.fehler || daten.detail || `Fehler ${antwort.status}`);
  return daten;
}

function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toast.zeit);
  toast.zeit = setTimeout(() => (t.hidden = true), 3500);
}

const zahl = (x, stellen = 1) => x == null ? "–" : Number(x).toLocaleString("de-DE", { maximumFractionDigits: stellen });
const masse = (m) => m ? m.map((v) => zahl(v)).join(" × ") + " mm" : "";
const endung = { "3mf": ".3mf", stl: ".stl", obj: ".obj", step: ".step" };
const istNeu = (m) => m.angelegt && (Date.now() - new Date(m.angelegt).getTime()) < 7 * 864e5;

// ---------------------------------------------------------------- Laden

async function ladeModelle() {
  const p = new URLSearchParams({ q: zustand.suche, ordner: zustand.ordner, format: zustand.format,
                                  ansicht: zustand.ansicht, sammlung: zustand.sammlung, leiste: 1,
                                  tags: [...zustand.tags].join(","), material: [...zustand.material].join(",") });
  const { modelle: liste, leiste } = await api("/api/modelle?" + p);
  zeichneLeiste(leiste);
  const s = (zustand.sammlung || zustand.ansicht === "warteschlange") ? "eigene" : zustand.sortierung;
  if (s === "neu") liste.sort((a, b) => (b.angelegt || "").localeCompare(a.angelegt || ""));
  if (s === "gewicht") liste.sort((a, b) => (b.gewicht_g || 0) - (a.gewicht_g || 0));
  if (s === "groesse") liste.sort((a, b) => Math.max(...(b.masse || [0])) - Math.max(...(a.masse || [0])));
  zustand.modelle = liste;
  $("#anzahl").textContent = `${liste.length.toLocaleString("de-DE")} Dateien`;
  zeichneFilterzeile();
  zeichneStapel();
  zeichneListenkopf();
  raster.neu();
  if (zustand.baugruppe) zeigeBaugruppeFlaeche(true);
}

async function ladeSeite() {
  const [z, ordner, tags, sammlungen, ws] = await Promise.all([api("/api/zaehler"), api("/api/ordner"), api("/api/tags"),
                                                              api("/api/sammlungen"), api("/api/warteschlange")]);
  zustand.sammlungen = sammlungen;
  $("#sammlungen").innerHTML = sammlungen.map((x) =>
    `<button class="eintrag ${zustand.sammlung === x.id ? "aktiv" : ""}" data-sammlung="${esc(x.id)}"><span>${esc(x.name)}</span><em>${x.anzahl}</em></button>`).join("");
  $("#ws-liste").innerHTML = ws.map((m, i) =>
    `<li draggable="true" data-ws="${esc(m.id)}"><b>${i + 1}</b><span data-ws-waehle="${esc(m.id)}" title="${esc(m.name)}">${esc(m.name)}${esc(endung[m.format] || "")}</span><button data-ws-weg="${esc(m.id)}" title="aus der Warteschlange">×</button></li>`).join("");
  for (const k of ["alle", "favoriten", "duplikate", "fehlt", "unlesbar", "papierkorb", "warteschlange"]) {
    const el = $("#z-" + k);
    if (el) el.textContent = z[k] || "";
  }
  $("#formate").innerHTML = Object.entries(z.formate).sort().map(([f, n]) =>
    `<button class="eintrag ${zustand.format === f ? "aktiv" : ""}" data-format="${esc(f)}"><span>${esc(endung[f] || f)}</span><em>${n}</em></button>`).join("");
  $("#ordner").innerHTML = `<div class="baum">${ordner.map((w) => zweig(w, 0)).join("")}</div>`;
  $("#tag-liste").innerHTML = tags.slice(0, 30).map((t) =>
    `<button class="eintrag ${zustand.tags.has(t.name) ? "aktiv" : ""}" data-tag="${esc(t.name)}"><span>#${esc(t.name)}</span><em>${t.anzahl}</em></button>`).join("");
  markiereAnsicht();
}

function zweig(k, tiefe) {
  const hatKinder = k.kinder.length > 0;
  const offen = zustand.offen.has(k.id);
  const aktiv = zustand.ordner === k.id ? "aktiv" : "";
  let html = `<button class="eintrag ${aktiv}" style="--tiefe:${tiefe}" data-ordner="${esc(k.id)}" title="${esc(k.pfad || k.name)}">
    <span><span class="pfeil" data-klappe="${esc(k.id)}">${hatKinder ? (offen ? "▾" : "▸") : ""}</span>${esc(k.name)}</span><em>${k.anzahl}</em></button>`;
  if (hatKinder && offen) html += k.kinder.map((c) => zweig(c, tiefe + 1)).join("");
  return html;
}

function markiereAnsicht() {
  document.querySelectorAll("[data-ansicht]").forEach((b) =>
    b.classList.toggle("aktiv", b.dataset.ansicht === zustand.ansicht && !zustand.ordner && !zustand.tags.size && !zustand.material.size && !zustand.format && !zustand.sammlung));
  document.querySelectorAll(".rail-btn[data-rail]").forEach((b) =>
    b.classList.toggle("aktiv", (b.dataset.rail === "papierkorb") === (zustand.ansicht === "papierkorb")));
}

// Die Leiste über dem Raster: Material und Tags als Chips, je mit ODER.
// Gezählt wird vor der Chip-Auswahl (Server), gewählte Chips bleiben
// sichtbar, auch wenn sie unter die ersten 14 fallen.
function zeichneLeiste(l) {
  const chip = (art, wahl, x, text) => `<button class="chip ${wahl.has(x.name) ? "aktiv" : ""}" data-${art}="${esc(x.name)}">${text}<em>${x.anzahl}</em></button>`;
  const auswahl = (liste, wahl, n) => [...liste.slice(0, n), ...liste.slice(n).filter((x) => wahl.has(x.name))];
  const mat = auswahl(l.materialien, zustand.material, 8).map((x) => chip("mat", zustand.material, x, esc(x.name))).join("");
  const tags = auswahl(l.tags, zustand.tags, 14).map((x) => chip("tag", zustand.tags, x, "#" + esc(x.name))).join("");
  const leer = !zustand.tags.size && !zustand.material.size;
  $("#tagleiste").innerHTML = `<button class="chip ${leer ? "aktiv" : ""}" data-tag="">Alle</button>`
    + (mat ? `<span class="leiste-titel">MATERIAL</span>${mat}` : "")
    + (tags ? `<span class="leiste-titel">TAGS</span>${tags}` : "");
}

function zeichneFilterzeile() {
  const teile = [];
  const sammlung = zustand.sammlungen.find((x) => x.id === zustand.sammlung);
  if (sammlung) teile.push(`Sammlung <b>${esc(sammlung.name)}</b> <button id="sammlung-umbenennen">umbenennen</button> <button id="sammlung-loeschen">löschen</button> <button id="sammlung-zu-baugruppe">🧩 als Baugruppe</button> <span class="dim">· Reihenfolge per Ziehen</span>`);
  if (zustand.ansicht === "warteschlange") teile.push(`Warteschlange <span class="dim">· Reihenfolge per Ziehen</span>`);
  if (zustand.ordner) teile.push(`Ordner ${esc(zustand.ordner.split("/").slice(1).join("/") || "(Wurzel)")}`);
  const chips = [...zustand.material, ...[...zustand.tags].map((t) => "#" + t)];
  if (chips.length) teile.push(`${chips.map(esc).join(" oder ")} <span class="dim">· wer mehr trifft, steht oben</span>`);
  if (zustand.format) teile.push(esc(endung[zustand.format] || zustand.format));
  if (zustand.suche) teile.push(`„${esc(zustand.suche)}“`);
  const z = $("#filterzeile");
  z.hidden = teile.length === 0;
  z.innerHTML = teile.join(" · ") + ` <button id="filter-weg">✕ Filter aufheben</button>`;
  const leer = $("#leer");
  leer.hidden = zustand.modelle.length > 0;
  leer.textContent = zustand.ansicht === "papierkorb" ? "Der Papierkorb ist leer."
    : (teile.length ? "Keine Treffer." : "Noch keine Modelle. Über „Importieren“ einen Ordner hinzufügen.");
}

// ---------------------------------------------------------------- Virtuelles Raster und Liste
//
// Beide Ansichten zeichnen nur, was sichtbar ist. Die Liste ist dasselbe
// Raster mit einer Spalte und niedrigen Zeilen.

const raster = (() => {
  const RAND = 14;
  const aussen = $("#raster"), innen = $("#raster-innen");
  let spalten = 1, geplant = false;
  const mass = () => zustand.layout === "liste"
    ? { B: 0, H: 36, LUECKE: 0, RAND: 0 } : { B: 164, H: 246, LUECKE: 14, RAND };

  function neu() {
    const { B, H, LUECKE, RAND: R } = mass();
    spalten = zustand.layout === "liste" ? 1 : Math.max(1, Math.floor((aussen.clientWidth - R * 2 + LUECKE) / (B + LUECKE)));
    const zeilen = Math.ceil(zustand.modelle.length / spalten);
    innen.style.height = `${R * 2 + zeilen * (H + LUECKE)}px`;
    $("#listenkopf").hidden = zustand.layout !== "liste";
    zeichne();
  }

  function zeichne() {
    geplant = false;
    const { B, H, LUECKE, RAND: R } = mass();
    const oben = aussen.scrollTop, hoehe = aussen.clientHeight;
    const von = Math.max(0, Math.floor((oben - R) / (H + LUECKE)) - 2);
    const bis = Math.ceil((oben + hoehe) / (H + LUECKE)) + 2;
    const html = [];
    for (let z = von; z < bis; z++) {
      for (let s = 0; s < spalten; s++) {
        const i = z * spalten + s;
        const m = zustand.modelle[i];
        if (!m) break;
        html.push(zustand.layout === "liste" ? zeileL(m, z * H) : karte(m, R + s * (B + LUECKE), R + z * (H + LUECKE)));
      }
    }
    innen.innerHTML = html.join("");
  }

  aussen.addEventListener("scroll", () => { if (!geplant) { geplant = true; requestAnimationFrame(zeichne); } });
  window.addEventListener("resize", () => requestAnimationFrame(neu));
  return { neu, zeichne };
})();

function bildUrl(m) {
  if (m.bild) return `/api/modelle/${m.id}/bild?v=${m.bild}`;
  return m.hash && ["eingebettet", "gerendert"].includes(m.vorschau) ? `/api/vorschau/${m.hash}.png` : null;
}

function statusBadge(m) {
  return m.fehlt ? `<span class="badge warn">⚠ Datei fehlt</span>`
    : m.fehler ? `<span class="badge warn">unlesbar</span>`
    : m.gedruckt ? `<span class="badge gedruckt">✓ Gedruckt${m.gewicht_g ? " · " + zahl(m.gewicht_g, 2) + " g" : ""}</span>` : "";
}

function karte(m, x, y) {
  const url = bildUrl(m);
  const platz = m.vorschau === "ausstehend" ? "Vorschau wird gerendert …" : (m.format === "step" ? "STEP · nur CAD" : "keine Vorschau");
  const unter = [masse(m.masse), m.gewicht_g ? `${zahl(m.gewicht_g, 1)} g${m.material ? " | " + esc(m.material) : ""}` : ""].filter(Boolean).join(" · ");
  const markiert = zustand.auswahl.has(m.id);
  return `<div class="karte ${zustand.gewaehlt === m.id ? "gewaehlt" : ""} ${markiert ? "markiert" : ""} ${m.fehlt ? "fehlt" : ""}" draggable="true" style="left:${x}px;top:${y}px" data-id="${esc(m.id)}">
    <div class="bild">${url ? `<img loading="lazy" src="${url}" alt="">` : `<div class="platzhalter">${platz}</div>`}
      ${istNeu(m) ? '<span class="badge neu">NEU</span>' : ""}
      <input type="checkbox" class="wahl" data-wahl="${esc(m.id)}" ${markiert ? "checked" : ""} title="auswählen">
      ${zustand.ansicht === "papierkorb" ? "" : `<button class="herz ${m.favorit ? "an" : ""}" data-herz="${esc(m.id)}" title="Favorit">♥</button>`}
      ${m.fehlt ? `<div class="fehlt-band" title="Die Datei liegt an keinem bekannten Ort mehr. Tags, Bilder und Verknüpfungen sind noch da — legt man sie zurück, ist alles wieder verbunden.">⚠ Datei fehlt</div>` : statusBadge(m)}</div>
    <div class="text"><div class="name" title="${esc(m.name)}">${esc(m.name)}${esc(endung[m.format] || "")}</div>
      <div class="masse">${unter || "&nbsp;"}</div>
      <div class="tags">${m.tags.slice(0, 5).map((t) => `<span>#${esc(t)}</span>`).join("")}</div></div></div>`;
}

const LISTENSPALTEN = [["", ""], ["", ""], ["NAME", "name"], ["FORMAT", ""], ["GRÖSSE", "groesse"], ["GEWICHT", "gewicht"],
                       ["STATUS", ""], ["TAGS", ""], ["ORDNER", ""]];

function zeileL(m, y) {
  const url = bildUrl(m);
  const markiert = zustand.auswahl.has(m.id);
  const ordner = (m.ordner[0] || "").split("/").slice(1).join("/");
  const status = m.fehlt ? "⚠ fehlt" : m.fehler ? "unlesbar" : m.gedruckt ? "✓ gedruckt" : (m.warteschlange != null ? "☰ Warteschlange" : "");
  return `<div class="zeile-l ${zustand.gewaehlt === m.id || markiert ? "gewaehlt" : ""} ${m.fehlt ? "fehlt" : ""}" draggable="true" style="top:${y}px" data-id="${esc(m.id)}">
    <span>${url ? `<img loading="lazy" src="${url}" alt="">` : '<div class="mini"></div>'}</span>
    <span><input type="checkbox" class="wahl-l" data-wahl="${esc(m.id)}" ${markiert ? "checked" : ""}></span>
    <span title="${esc(m.name)}">${m.favorit ? "♥ " : ""}${esc(m.name)}</span>
    <span class="mono">${esc(endung[m.format] || "")}</span>
    <span class="mono">${esc(masse(m.masse))}</span>
    <span class="mono">${m.gewicht_g ? zahl(m.gewicht_g, 1) + " g" : ""}</span>
    <span class="mono">${status}</span>
    <span class="mono">${m.tags.map((t) => "#" + esc(t)).join(" ")}</span>
    <span class="mono" title="${esc(ordner)}">${esc(ordner)}</span></div>`;
}

function zeichneListenkopf() {
  $("#listenkopf").innerHTML = LISTENSPALTEN.map(([t, k]) =>
    k ? `<button data-sortiere="${k}">${t}${zustand.sortierung === k ? " ▾" : ""}</button>` : `<span>${t}</span>`).join("");
}

// ---------------------------------------------------------------- Mehrfachauswahl
//
// Wie im 3MF Katalog: Kästchen je Kachel, Umschalt-Klick wählt einen
// Bereich, Leiste mit den Aktionen für alle Gewählten.

let letzteWahl = null;

function waehleAus(id, bereich) {
  if (bereich && letzteWahl) {
    const ids = zustand.modelle.map((m) => m.id);
    const [a, b] = [ids.indexOf(letzteWahl), ids.indexOf(id)].sort((x, y) => x - y);
    if (a >= 0 && b >= 0) ids.slice(a, b + 1).forEach((x) => zustand.auswahl.add(x));
  } else if (zustand.auswahl.has(id)) {
    zustand.auswahl.delete(id);
  } else {
    zustand.auswahl.add(id);
  }
  letzteWahl = id;
  zeichneStapel();
  raster.zeichne();
}

function zeichneStapel() {
  // Was nicht mehr in der Liste ist (gelöscht, weggefiltert), ist auch nicht gewählt.
  const sichtbar = new Set(zustand.modelle.map((m) => m.id));
  for (const id of [...zustand.auswahl]) if (!sichtbar.has(id)) zustand.auswahl.delete(id);
  const n = zustand.auswahl.size;
  const st = $("#stapel");
  st.hidden = n === 0;
  if (!n) return;
  st.innerHTML = zustand.ansicht === "papierkorb"
    ? `<b>${n} ausgewählt</b><button class="knopf" data-stapel="wiederherstellen">Wiederherstellen</button>
       <button class="knopf" data-stapel="alle">Alle auswählen</button><button class="knopf" data-stapel="keine">✕ Auswahl aufheben</button>`
    : `<b>${n} ausgewählt</b>
    <button class="knopf" data-stapel="alle">Alle auswählen (${zustand.modelle.length})</button>
    <button class="knopf" data-stapel="baugruppe">🧩 Zu Baugruppe …</button>
    <button class="knopf" data-stapel="warteschlange">☰ In Warteschlange</button>
    <select class="knopf" id="stapel-sammlung"><option value="">Zu Sammlung …</option>${zustand.sammlungen.map((x) =>
      `<option value="${esc(x.id)}">${esc(x.name)}</option>`).join("")}<option value="__neu">Neue Sammlung …</option></select>
    <button class="knopf" data-stapel="tag">＃ Tag …</button>
    <button class="knopf" data-stapel="material">Material …</button>
    <button class="knopf" data-stapel="gedruckt">✓ Gedruckt</button>
    <button class="knopf" data-stapel="favorit">♥ Favorit</button>
    <button class="knopf" data-stapel="verschieben">Verschieben …</button>
    <button class="knopf gefahr" data-stapel="loeschen">Löschen</button>
    <button class="knopf" data-stapel="keine">✕</button>`;
}

// Vorgesehen setzt der Anwender (entfernbar); aus der Datei kommt aus den
// Slicer-Daten der 3MF und bleibt, solange die Datei es sagt.
function materialTeil(m, alle) {
  const h = m.material_herkunft || { vorgesehen: [], aus_datei: [] };
  const frei = alle.filter((x) => !h.vorgesehen.includes(x));
  return `<div class="i-gruppe"><span class="i-label" title="Vorgesehen legst du fest; „aus 3MF“ steht in der Datei">Material</span>
    <div class="i-material">${h.vorgesehen.map((x) => `<span class="chip aktiv" title="vorgesehen">${esc(x)}<button data-material-weg="${esc(x)}" title="entfernen">×</button></span>`).join("")}
      ${h.aus_datei.map((x) => `<span class="chip" title="aus den Slicer-Daten der Datei">${esc(x)} <small>aus 3MF</small></span>`).join("")}
      <select class="knopf klein" id="material-dazu"><option value="">＋ Material …</option>${frei.map((x) => `<option>${esc(x)}</option>`).join("")}
        <option value="__neu">Neues Material …</option></select></div></div>`;
}

async function materialFrage(titel) {
  const a = await dialog(`<h2>${titel}</h2><input type="text" id="s-name" placeholder="z. B. PETG, Holz-PLA">
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Setzen</button></div>`);
  return a === "ja" ? $("#s-name").value.trim() : "";
}

async function stapel(aktion, wert) {
  const modelle = [...zustand.auswahl];
  try {
    const r = await api("/api/stapel", { method: "POST", body: { aktion, modelle, wert } });
    if (r.fehler.length) toast(`${modelle.length - r.fehler.length} erledigt, ${r.fehler.length} nicht: ${r.fehler[0].fehler}`);
    else toast(`${modelle.length} erledigt.`);
  } catch (e) { toast(e.message); }
}

async function stapelAktion(aktion) {
  const modelle = [...zustand.auswahl];
  switch (aktion) {
    case "alle": zustand.modelle.forEach((m) => zustand.auswahl.add(m.id)); zeichneStapel(); return raster.zeichne();
    case "keine": zustand.auswahl.clear(); zeichneStapel(); return raster.zeichne();
    case "warteschlange": return stapel("warteschlange");
    case "baugruppe": return zuBaugruppe(modelle);
    case "gedruckt": return stapel("gedruckt", true);
    case "favorit": return stapel("favorit", true);
    case "material": {
      const alle = await api("/api/materialien");
      const a = await dialog(`<h2>Material für ${modelle.length} Modelle</h2>
        <p class="dim">Wird als „vorgesehen“ ergänzt; vorhandene Angaben bleiben.</p>
        <div class="kategorien">${alle.map((x) => `<button type="button" class="chip" data-mat-wahl="${esc(x)}">${esc(x)}</button>`).join("")}</div>
        <input type="text" id="s-name" placeholder="oder neues Material">
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Setzen</button></div>`);
      if (a === "ja" && $("#s-name").value.trim()) return stapel("material", $("#s-name").value.trim());
      return;
    }
    case "tag": {
      const a = await dialog(`<h2>Tag für ${modelle.length} Modelle</h2><input type="text" id="s-name" placeholder="z. B. Funktional">
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Setzen</button></div>`);
      if (a === "ja") return stapel("tag", $("#s-name").value);
      return;
    }
    case "verschieben": {
      const ziel = await ordnerWahl(`${modelle.length} Modelle verschieben`, "Die Dateien werden auf der Platte verschoben. Nichts wird überschrieben.");
      if (ziel) { await stapel("verschieben", ziel); }
      return;
    }
    case "loeschen": return loeschenViele(modelle);
    case "wiederherstellen":
      for (const id of modelle) await api(`/api/modelle/${id}/wiederherstellen`, { method: "POST" }).catch((e) => toast(e.message));
      zustand.auswahl.clear();
      return;
  }
}

async function loeschenViele(modelle) {
  if (await loeschDialog(modelle, `${modelle.length} Modelle löschen?`)) { zustand.auswahl.clear(); waehle(null); }
}

// ---------------------------------------------------------------- Ordner wählen, Hochladen, Archive

async function ordnerWahl(titel, hinweis, vorwahl = "") {
  const liste = await api("/api/verzeichnisse");
  const a = await dialog(`<h2>${esc(titel)}</h2><p class="dim">${esc(hinweis)}</p>
    <select id="ordner-ziel">${liste.map((v) => `<option value="${esc(v.id)}" ${v.id === vorwahl ? "selected" : ""}>${esc(v.name)}${v.pfad ? " / " + esc(v.pfad) : ""}</option>`).join("")}</select>
    <label>Neuer Unterordner darin: <input type="text" id="ordner-neu" placeholder="optional"></label>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">OK</button></div>`);
  if (a !== "ja") return null;
  let ziel = $("#ordner-ziel").value;
  const neuName = $("#ordner-neu").value.trim();
  if (neuName) {
    try { ziel = (await api("/api/verzeichnisse", { method: "POST", body: { eltern: ziel, name: neuName } })).id; }
    catch (e) { toast(e.message); return null; }
  }
  return ziel;
}

async function hochladen(dateiliste) {
  const dateien = [...dateiliste];
  if (!dateien.length) return;
  const ziel = await ordnerWahl(`${dateien.length} Datei${dateien.length > 1 ? "en" : ""} hochladen`,
    "Archive (zip, tar) werden in einen Unterordner entpackt. Nichts wird überschrieben.", zustand.ordner);
  if (!ziel) return;
  let ok = 0;
  for (const [i, f] of dateien.entries()) {
    toast(`Hochladen ${i + 1}/${dateien.length}: ${f.name}`);
    try {
      await fetch(`/api/hochladen?ordner=${encodeURIComponent(ziel)}&name=${encodeURIComponent(f.name)}`, { method: "POST", body: f })
        .then(async (r) => { if (!r.ok) throw new Error((await r.json()).fehler); });
      ok++;
    } catch (e) { toast(`${f.name}: ${e.message}`); await new Promise((w) => setTimeout(w, 1500)); }
  }
  toast(`${ok} von ${dateien.length} hochgeladen, wird eingelesen …`);
}

async function archiveEntpacken() {
  $("#import-menu").hidden = true;
  const liste = await api("/api/archive");
  if (!liste.length) return toast("Keine Archive in den Ordnern.");
  const a = await dialog(`<h2>Archive entpacken</h2><p class="dim">Jedes in einen Unterordner daneben. Heraus kommen nur Modelle, G-Code, Bilder und Texte — nie Programme.</p>
    ${liste.map((x, i) => `<label><input type="checkbox" data-archiv="${esc(x.id)}" ${i < 50 ? "checked" : ""}> ${esc(x.id.split("/").slice(1).join("/"))} <span class="dim">${zahl(x.groesse / 1048576, 1)} MB</span></label>`).join("")}
    <label><input type="checkbox" id="archiv-weg"> Original danach in den Papierkorb von partAtlas</label>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Entpacken</button></div>`);
  if (a !== "ja") return;
  const weg = $("#archiv-weg").checked;
  const gewaehlt = [...document.querySelectorAll("[data-archiv]:checked")].map((x) => x.dataset.archiv);
  let n = 0;
  for (const id of gewaehlt) {
    try { n += (await api("/api/archive/entpacken", { method: "POST", body: { id, original_loeschen: weg } })).entpackt; }
    catch (e) { toast(`${id}: ${e.message}`); }
  }
  toast(`${n} Dateien entpackt, wird eingelesen …`);
}

// ---------------------------------------------------------------- Inspektor

async function waehle(id) {
  zustand.gewaehlt = id;
  raster.zeichne();
  if (!id && zustand.baugruppe && typeof zeigeBgUebersicht === "function") return zeigeBgUebersicht();
  if (!id) { zustand.angezeigt = null; if (dreiDModul) (await dreiD()).schliessen(); $("#inspektor").innerHTML = `<p class="hinweis">Wähle ein Modell aus, um Details, Vorschau und Tags zu sehen.</p>`; return; }
  const [m, prog, materialien] = await Promise.all([api(`/api/modelle/${id}`), ladeProgramme(), api("/api/materialien")]);
  if (zustand.gewaehlt !== id) return;
  const papierkorb = m.papierkorb;
  const zeile = ([a, b]) => `<div class="zeile"><span>${a}</span><span>${b}</span></div>`;
  const zeit = m.platten.reduce((t, p) => t + (p.zeit_s || 0), 0);
  // Zum Drucken: was man vor dem Slicen wissen will. Datei-Details: was man
  // nur manchmal braucht — zugeklappt, der Zustand bleibt gemerkt.
  const drucken = [
    ["Grösse", esc(masse(m.masse) || "–")],
    ["Gewicht", m.gewicht_g ? esc(zahl(m.gewicht_g, 1)) + " g <small class=\"dim\">aus Slicer</small>" : "–"],
    ...(zeit ? [["Druckzeit", esc(dauer(zeit))]] : []),
    ...(m.platten.length > 1 ? [["Druckplatten", m.platten.length]] : []),
  ];
  const platten = m.platten.map((p) => `<div class="zeile"><span>${m.platten.length > 1 ? `Platte ${p.nr}` : "Filament"}</span><span>${p.filamente.map((f) =>
    `<span class="farbpunkt" style="background:${esc(f.farbe || "transparent")}"></span>${esc(f.typ || "?")} ${zahl(f.g, 1)} g`).join("<br>")}</span></div>`).join("");
  const details = [
    ["Volumen", m.volumen_cm3 != null ? esc(zahl(m.volumen_cm3)) + " cm³" : "–"],
    ["Objekte", m.objekte ?? "–"],
    ["Dreiecke", m.dreiecke != null ? esc(zahl(m.dreiecke, 0)) : "–"],
    ["Ersteller", esc(m.designer || "–")],
    ["Dateigrösse", m.groesse ? esc(zahl(m.groesse / 1024, 0)) + " KB" : "–"],
    ["Eingelesen", m.eingelesen ? new Date(m.eingelesen).toLocaleDateString("de-DE") : "–"],
  ];
  const orte = (papierkorb ? m.papierkorb_ablage : m.orte).map((o) => `<div class="ort">${esc(o.absolut || o.pfad)}</div>`).join("") || '<div class="dim">–</div>';
  const quelle = `<div class="zeile quelle"><span>Quelle</span><span>${m.quelle_url
    ? `<a href="${esc(m.quelle_url)}" target="_blank" rel="noopener noreferrer">${esc(m.quelle_url.replace(/^https?:\/\//, "").slice(0, 32))}…</a>` : "–"}
    ${papierkorb ? "" : `<button class="knopf" id="quelle-aendern" title="Quelle ändern">✎</button>`}</span></div>`;
  // Dasselbe Modell neu gezeichnet (Tag dazu, Live-Meldung): die Galerie
  // bleibt stehen, samt 3D-Ansicht — ausser es kam ein Bild dazu oder weg.
  const sig = JSON.stringify([m.papierkorb, m.ansichten.map((a) => a.url)]);
  const alteGalerie = zustand.angezeigt === id && $("#i-galerie")?.dataset.sig === sig ? $("#i-galerie") : null;
  const detailsOffen = localStorageLesen("details") === "1";
  // Eine Live-Meldung zeichnet den Inspektor neu; ein offenes Menü bleibt offen.
  const menuOffen = zustand.angezeigt === id && $("#mehr-menu") && !$("#mehr-menu").hidden;
  $("#inspektor").innerHTML = `
    ${zustand.baugruppe ? `<button class="zurueck" id="bg-zurueck">← Baugruppe</button>` : ""}
    <div class="galerie" id="i-galerie" data-sig="${esc(sig)}"></div>
    <div class="i-kopf">
      <div class="i-name">${esc(m.name)}<span class="dim">${esc(endung[m.format] || "")}</span></div>
      ${papierkorb ? `<div class="i-haupt"><button class="knopf akzent" id="wiederherstellen">Wiederherstellen</button></div>`
        : `<div class="i-haupt">${oeffnenKnoepfe(m, prog)}
        <div class="mehr"><button class="schalter" id="mehr-knopf" title="Weitere Aktionen">⋯</button>
          <div class="menu" id="mehr-menu" hidden>
            <button id="umbenennen">Umbenennen …</button>
            <button id="verschieben">In anderen Ordner verschieben …</button>
            <button id="gal-plus-menu">Bild hinzufügen …</button>
            <hr><button id="loeschen" class="gefahr">Löschen …</button>
          </div></div>
      </div>
      <div class="i-schalter">
        <button class="schalter ${m.warteschlange != null ? "an" : ""}" id="ws-knopf" title="${m.warteschlange != null ? "Aus der Warteschlange nehmen" : "Zum Drucken vormerken"}">☰ ${m.warteschlange != null ? `Warteschlange · Platz ${m.warteschlange + 1}` : "In Warteschlange"}</button>
        <button class="schalter ${m.gedruckt ? "an" : ""}" id="gedruckt" title="Als gedruckt markieren">${m.gedruckt ? "✓ Gedruckt" : "○ Nicht gedruckt"}</button>
        <button class="schalter ${m.favorit ? "an" : ""}" id="favorit" title="Favorit">♥</button>
      </div>`}
    </div>
    ${m.fehler_text ? `<p class="fehler">Unlesbar: ${esc(m.fehler_text)}</p>` : ""}
    ${m.fehlt ? `<p class="fehler"><b>⚠ Datei fehlt.</b> Sie liegt an keinem bekannten Ort mehr — gelöscht, umbenannt ausserhalb der Ordner von partAtlas oder auf einem Laufwerk, das gerade fehlt. Tags, Bilder und Verknüpfungen sind noch da: legt man die Datei zurück, ist beim nächsten Einlesen alles wieder verbunden. Braucht man das Modell nicht mehr: „Löschen“.</p>` : ""}

    <div class="i-titel">ZUM DRUCKEN</div>
    <div class="i-karte">${drucken.map(zeile).join("")}${platten}</div>
    ${papierkorb ? "" : materialTeil(m, materialien)}

    ${papierkorb ? "" : `<div class="i-titel">ORDNEN</div>
    <div class="i-gruppe"><span class="i-label">Tags</span>
      <div class="i-tags">${m.tags.map((t) => `<span class="chip">#${esc(t)}<button data-tag-weg="${esc(t)}" title="entfernen">×</button></span>`).join("")}
        <input id="tag-neu" placeholder="＋ Tag" autocomplete="off"></div></div>
    <div class="i-gruppe"><span class="i-label">Baugruppen</span>
      <div class="i-sammlungen">${(m.baugruppen || []).map((b) => `<button class="chip" data-baugruppe="${esc(b.id)}">🧩 ${esc(b.name)} · ${b.menge}×</button>`).join("")}
        <button class="knopf klein" id="zu-baugruppe">＋ Baugruppe …</button></div></div>
    <div class="i-gruppe"><span class="i-label">Sammlungen</span>
      <div class="i-sammlungen">${m.sammlungen.map((x) => `<span class="chip">${esc(x.name)}<button data-sammlung-weg="${esc(x.id)}" title="aus der Sammlung">×</button></span>`).join("")}
        <select class="knopf klein" id="sammlung-dazu"><option value="">＋ Sammlung …</option>${zustand.sammlungen
          .filter((x) => !m.sammlungen.some((y) => y.id === x.id)).map((x) => `<option value="${esc(x.id)}">${esc(x.name)}</option>`).join("")}
          <option value="__neu">Neue Sammlung …</option></select></div></div>`}

    <details class="i-details" id="i-details" ${detailsOffen ? "open" : ""}>
      <summary>DATEI-DETAILS</summary>
      <div class="i-karte">${details.map(zeile).join("")}${quelle}</div>
      <div class="i-label">${papierkorb ? "Lag zuletzt in" : "Ort" + (m.orte.length > 1 ? `e (${m.orte.length})` : "")}</div>
      ${orte}
    </details>`;
  $("#inspektor").dataset.id = id;
  if (menuOffen) $("#mehr-menu").hidden = false;
  if (alteGalerie) { $("#i-galerie").replaceWith(alteGalerie); return; }
  zustand.angezeigt = id;
  zeigeGalerie(m);
}

// ---------------------------------------------------------------- Galerie
//
// Alles, was es zu einem Modell zu sehen gibt, zum Durchblättern: die
// eigenen Bilder (das erste ist das Titelbild), die 3D-Ansicht, das Bild aus
// der Datei, die berechnete Vorschau. Blättern mit Pfeilen, Kacheln,
// Pfeiltasten oder Wischen; eigene Bilder per ＋, Hineinziehen oder Strg+V.
// Ohne WebGL fehlt nur die 3D-Ansicht.

let viewer = null, dreiDModul = null;
const galerie = { m: null, folien: [], i: 0, ziel: null };
async function dreiD() {
  if (!dreiDModul) dreiDModul = import("/web/viewer.js");
  return dreiDModul;
}

async function zeigeGalerie(m) {
  const hatNetz = !m.papierkorb && !m.fehlt && !m.fehler_text && m.format !== "step";
  const v = await dreiD().catch(() => null);
  if (zustand.gewaehlt !== m.id) return;
  const kann3d = hatNetz && v && v.webglMoeglich();
  const eigene = m.ansichten.filter((a) => a.art === "eigen");
  const folien = [...eigene, ...(kann3d ? [{ art: "3d", titel: "3D-Ansicht" }] : []),
                  ...m.ansichten.filter((a) => a.art !== "eigen")];
  // Start: das Titelbild, wenn es eins gibt; sonst was man zuletzt wollte.
  let i = 0;
  if (galerie.ziel) i = Math.max(0, folien.findIndex((f) => f.k === galerie.ziel));
  else if (!eigene.length && kann3d && localStorageLesen("ansicht") === "bild") i = Math.min(folien.length - 1, 1);
  galerie.ziel = null;
  Object.assign(galerie, { m, folien, i });
  zeichneGalerie();
}

function galerieBlaettern(schritt) {
  const n = galerie.folien.length;
  if (n < 2) return;
  galerieZeigen((galerie.i + schritt + n) % n);
}

function galerieZeigen(i) {
  if (i === galerie.i) return;
  galerie.i = i;
  const f = galerie.folien[i];
  if (f.art === "3d") localStorageSchreiben("ansicht", "3d");
  else if (f.art !== "eigen") localStorageSchreiben("ansicht", "bild");
  zeichneGalerie();
}

async function zeichneGalerie() {
  const { m, folien, i } = galerie;
  const feld = $("#i-galerie");
  if (!feld || !m) return;
  const f = folien[i];
  const n = folien.length;
  const darf = !m.papierkorb;
  if (dreiDModul) (await dreiD()).schliessen();
  viewer = null;
  const pfeile = n > 1 ? `<button class="gal-pfeil links" data-gal="-1" title="Vorheriges (←)">‹</button>
    <button class="gal-pfeil rechts" data-gal="1" title="Nächstes (→)">›</button>` : "";
  const ersteEigene = folien.findIndex((x) => x.art === "eigen");
  const aktionen = f && f.art === "eigen" && darf ? `<div class="gal-aktionen">
    ${i !== ersteEigene ? `<button data-gal-titel="${esc(f.k)}" title="Dieses Bild auf der Kachel zeigen">★ Als Titelbild</button>` : ""}
    <button data-gal-weg="${esc(f.k)}" title="Bild entfernen">Entfernen</button></div>` : "";
  const leer = `<div class="gal-leer"><span>${m.format === "step" ? "STEP · nur CAD" : "Keine Vorschau"}</span>
    ${darf ? `<button class="knopf" data-gal-plus>＋ Eigenes Bild hinzufügen</button>` : ""}</div>`;
  const haupt = !f ? leer
    : f.art === "3d" ? `<span class="laden">3D wird geladen …</span><button class="bild-knopf" id="ansicht-zurueck" title="Ansicht zurücksetzen">⟲</button>`
    : `<img src="${esc(f.url)}" alt="${esc(f.titel)}" draggable="false">`;
  const minis = folien.map((x, j) => `<button class="gal-mini ${j === i ? "an" : ""}" data-gal-i="${j}" data-art="${x.art}" title="${esc(x.titel)}">
      ${x.art === "3d" ? "<span>3D</span>" : `<img src="${esc(x.url)}" alt="" loading="lazy">`}</button>`).join("");
  feld.innerHTML = `<div class="i-bild" id="i-bild">${haupt}${pfeile}
      ${f ? `<span class="gal-etikett">${esc(f.titel)}${n > 1 ? ` · ${i + 1} / ${n}` : ""}</span>` : ""}${aktionen}
      <div class="gal-abwurf">Als Bild zu „${esc(m.name)}“ hinzufügen</div></div>
    ${f && (n > 1 || darf) ? `<div class="gal-leiste">${minis}${darf ? `<button class="gal-mini plus" data-gal-plus title="Eigene Bilder hinzufügen (oder hineinziehen, Strg+V)">＋</button>` : ""}</div>` : ""}`;
  if (f && f.art === "3d") lade3d(m);
}

async function lade3d(m) {
  const feld = $("#i-bild");
  try {
    const v = await dreiD();
    const antwort = await fetch(`/api/modelle/${m.id}/netz`);
    if (!antwort.ok) throw new Error((await antwort.json().catch(() => ({}))).detail || "Netz nicht lesbar");
    const puffer = await antwort.arrayBuffer();
    if (zustand.gewaehlt !== m.id || galerie.folien[galerie.i]?.art !== "3d" || !feld.isConnected) return;
    feld.querySelector(".laden")?.remove();
    const farbe = m.platten.flatMap((p) => p.filamente).map((f) => f.farbe).find(Boolean) || null;
    viewer = v.zeige(feld, puffer, farbe);
  } catch (e) {
    const laden = feld.querySelector(".laden");
    if (laden) laden.textContent = e.message;
  }
}

async function bilderHochladen(dateien) {
  const id = galerie.m?.id;
  const bilder = [...dateien].filter((f) => /^image\/(png|jpeg|webp)$/.test(f.type));
  if (!id || galerie.m.papierkorb) return;
  if (!bilder.length) return toast("Nur PNG, JPG oder WebP.");
  let letztes = null;
  for (const f of bilder) {
    const r = await fetch(`/api/modelle/${id}/bilder`, { method: "POST", body: f });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) { toast(d.fehler || "Bild nicht gespeichert."); continue; }
    letztes = d.k;
  }
  if (!letztes) return;
  toast(bilder.length > 1 ? `${bilder.length} Bilder hinzugefügt.` : "Bild hinzugefügt.");
  galerie.ziel = letztes;
  zustand.angezeigt = null;
  if (zustand.gewaehlt === id) waehle(id);
}

document.addEventListener("click", async (e) => {
  const t = e.target;
  if (!t.closest?.("#i-galerie")) return;
  const m = galerie.m;
  const schritt = t.closest("[data-gal]");
  if (schritt) return galerieBlaettern(Number(schritt.dataset.gal));
  const mini = t.closest("[data-gal-i]");
  if (mini) return galerieZeigen(Number(mini.dataset.galI));
  if (t.closest("[data-gal-plus]")) return $("#bild-wahl").click();
  const titel = t.closest("[data-gal-titel]");
  if (titel) {
    await api(`/api/modelle/${m.id}/bilder/${titel.dataset.galTitel}/titel`, { method: "POST" });
    toast("Titelbild gesetzt.");
    galerie.ziel = titel.dataset.galTitel;
    zustand.angezeigt = null;
    return waehle(m.id);
  }
  const weg = t.closest("[data-gal-weg]");
  if (weg) {
    const a = await dialog(`<h2>Bild entfernen?</h2><p class="dim">Es verschwindet aus partAtlas. Die Datei bleibt im Archiv des Bestands (<code>vault_archive</code>).</p>
      <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr" value="ja">Entfernen</button></div>`);
    if (a !== "ja") return;
    await api(`/api/modelle/${m.id}/bilder/${weg.dataset.galWeg}`, { method: "DELETE" });
    zustand.angezeigt = null;
    return waehle(m.id);
  }
});

// Wischen auf dem Bild (Tablet, Touchpad-Klick-Ziehen) — nicht auf der 3D-Ansicht, die dreht.
let wischStart = null;
document.addEventListener("pointerdown", (e) => { wischStart = e.target.closest?.("#i-bild img") ? e.clientX : null; });
document.addEventListener("pointerup", (e) => {
  if (wischStart == null) return;
  const dx = e.clientX - wischStart;
  wischStart = null;
  if (Math.abs(dx) > 40) galerieBlaettern(dx < 0 ? 1 : -1);
});

// Bild aus der Zwischenablage: Bildschirmfoto, Bild aus dem Browser kopiert.
document.addEventListener("paste", (e) => {
  const tippt = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "");
  const bilder = [...(e.clipboardData?.files || [])].filter((f) => f.type.startsWith("image/"));
  if (tippt || !bilder.length || !zustand.gewaehlt || !$("#i-galerie")) return;
  e.preventDefault();
  bilderHochladen(bilder);
});

let programmCache = null;
function ladeProgramme() {
  if (!programmCache) programmCache = api("/api/programme").catch(() => ({ programme: [], standard: {}, arten: {} }));
  return programmCache;
}

// Hauptknopf mit dem Standardprogramm des Formats, daneben die übrigen,
// die das Format können, und immer „mit dem System“ — so bleibt keine
// Datei ohne Weg nach draussen, auch wenn nichts erkannt wurde.
function oeffnenKnoepfe(m, prog) {
  const std = prog.programme.find((p) => p.pfad === prog.standard[m.format]);
  const passend = prog.programme.filter((p) => p.formate.includes(m.format) && p !== std);
  const haupt = std
    ? `<button class="knopf akzent" id="oeffnen" data-pfad="${esc(std.pfad)}" title="${esc(std.pfad)}">↗ In ${esc(std.name)} öffnen</button>`
    : `<button class="knopf" id="oeffnen" data-system="1">↗ Mit dem System öffnen</button>`;
  const gruppen = Object.entries(prog.arten).map(([art, titel]) => {
    const g = passend.filter((p) => p.art === art);
    return g.length ? `<optgroup label="${esc(titel)}">${g.map((p) => `<option value="${esc(p.pfad)}">${esc(p.name)}</option>`).join("")}</optgroup>` : "";
  }).join("");
  const menue = std || passend.length
    ? `<select class="knopf" id="oeffnen-mit" title="Öffnen mit …"><option value="">Öffnen mit …</option>${gruppen}
        ${std ? '<option value="__system">Mit dem System öffnen</option>' : ""}<option value="__einstellungen">Programme einstellen …</option></select>`
    : "";
  return haupt + menue;
}

async function modellOeffnen(body) {
  const id = $("#inspektor").dataset.id;
  try {
    const r = await api(`/api/modelle/${id}/oeffnen`, { method: "POST", body });
    toast(r.programm ? `${r.programm} wird geöffnet …` : "Wird geöffnet …");
  } catch (err) { toast(err.message); }
}

async function aendern(id, werte) {
  try { await api(`/api/modelle/${id}`, { method: "PATCH", body: werte }); }
  catch (e) { toast(e.message); }
}

// ---------------------------------------------------------------- Dialoge

// Was an einem Modell hängt, in Worten statt Kantennamen; der Name der
// Kante steht dahinter, damit man sieht, dass es flatgraph ist, der zählt.
function dialog(html) {
  const d = $("#dialog");
  $("#dialog-inhalt").innerHTML = html;
  d.showModal();
  return new Promise((ok) => d.addEventListener("close", () => ok(d.returnValue), { once: true }));
}

async function loeschen(id) {
  const m = zustand.modelle.find((x) => x.id === id) || await api(`/api/modelle/${id}`);
  if (await loeschDialog([id], `„${esc(m.name)}${esc(endung[m.format] || "")}“ löschen?`)) waehle(null);
}

// Was am Modell hängt, aus der Nachbarschaft im Graphen — damit man weiss,
// was man tut. Ankreuzen lässt sich nur, was wirklich eine Wahl ist: Tags
// und Sammlungen, an denen sonst nichts mehr hängt. Alles andere geht mit in
// den Papierkorb und kommt beim Wiederherstellen zurück.
async function loeschDialog(modelle, titel) {
  const v = await api("/api/stapel/loeschvorschau", { method: "POST", body: { modelle } });
  const viele = modelle.length > 1;
  const nurT = v.tags.filter((t) => !t.sonst), andereT = v.tags.filter((t) => t.sonst);
  const nurS = v.sammlungen.filter((x) => !x.sonst), andereS = v.sammlungen.filter((x) => x.sonst);
  const zeile = (symbol, html) => `<div class="lz"><span class="lz-s">${symbol}</span><div>${html}</div></div>`;
  const dateien = v.dateien.length
    ? zeile("📄", `${v.dateien.length === 1 ? "<b>Die Datei</b> verschwindet aus ihrem Ordner" : `<b>${v.dateien.length} Dateien</b> verschwinden aus ihren Ordnern`}:
        <ul>${v.dateien.slice(0, 6).map((d) => `<li>${esc(d)}</li>`).join("")}${v.dateien.length > 6 ? `<li>… und ${v.dateien.length - 6} weitere</li>` : ""}</ul>`)
    : zeile("📄", "Keine Datei auf der Platte (fehlt schon).");
  const bilder = v.bilder ? zeile("🖼", `<b>${v.bilder} eigene${v.bilder === 1 ? "s Bild" : " Bilder"}</b> gehen mit.`) : "";
  const baugruppen = v.baugruppen.length ? zeile("⚠", `<b>Steckt in ${v.baugruppen.length === 1 ? "einer Baugruppe" : `${v.baugruppen.length} Baugruppen`}</b> — fehlt dort in der Stückliste, bis es zurückkommt:
      <ul>${v.baugruppen.map((b) => `<li>🧩 ${esc(b.name)} · ${b.menge}×${viele ? ` (${b.teile.map(esc).join(", ")})` : ""}</li>`).join("")}</ul>`) : "";
  const schlange = v.warteschlange ? zeile("☰", `${viele ? `${v.warteschlange} davon stehen` : "Steht"} in der Warteschlange und ${viele ? "fallen" : "fällt"} heraus.`) : "";
  const sammlungen = v.sammlungen.length ? zeile("▤", `${viele ? "In" : "Steht in"} ${v.sammlungen.length === 1 ? "einer Sammlung" : `${v.sammlungen.length} Sammlungen`}:
      <ul>${andereS.map((x) => `<li>${esc(x.name)} <span class="dim">· ${x.sonst} weitere Modelle bleiben</span></li>`).join("")}
        ${nurS.map((x) => `<li><label><input type="checkbox" data-mit-sammlung="${esc(x.id)}"> ${esc(x.name)} <span class="dim">· danach leer — Sammlung auch löschen</span></label></li>`).join("")}</ul>`) : "";
  const tags = v.tags.length ? zeile("#", `Tags: ${andereT.map((t) => `<span class="chip">#${esc(t.name)} <span class="dim">${t.sonst}</span></span>`).join(" ")}
      ${nurT.length ? `<div class="lz-wahl"><label><input type="checkbox" id="mit-tags"> Tags, die nur ${viele ? "diese Modelle haben" : "dieses Modell hat"}, ganz löschen:
        ${nurT.map((t) => `<span class="chip">#${esc(t.name)}</span>`).join(" ")}</label>
        <p class="lz-warn" hidden>Kommen beim Wiederherstellen nicht mit zurück.</p></div>` : ""}`) : "";
  const a = await dialog(`<h2>${titel}</h2>
    <p class="dim">Alles kommt in den Papierkorb von partAtlas. „Wiederherstellen“ legt es an seinen Ort zurück; endgültig weg ist es erst, wenn der Papierkorb geleert wird.</p>
    <div class="loesch-liste">${dateien}${bilder}${baugruppen}${schlange}${sammlungen}${tags}</div>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr" value="ja">In den Papierkorb</button></div>`);
  if (a !== "ja") return false;
  const wahl = {
    tags: $("#mit-tags")?.checked ? nurT.map((t) => t.name) : [],
    sammlungen: [...document.querySelectorAll("[data-mit-sammlung]:checked")].map((x) => x.dataset.mitSammlung),
  };
  try {
    const r = await api("/api/stapel", { method: "POST", body: { aktion: "loeschen", modelle, wert: wahl } });
    if (r.fehler.length) toast(`${modelle.length - r.fehler.length} gelöscht, ${r.fehler.length} nicht: ${r.fehler[0].fehler}`);
    else toast(viele ? `${modelle.length} Modelle im Papierkorb.` : "In den Papierkorb gelegt.");
    return true;
  } catch (e) { toast(e.message); return false; }
}

async function umbenennen(id) {
  const m = await api(`/api/modelle/${id}`);
  const antwort = await dialog(`<h2>Umbenennen</h2><p class="dim">Die Datei wird auf der Platte umbenannt, die Endung bleibt.</p>
    <input type="text" id="neuer-name" value="${esc(m.name)}">
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Umbenennen</button></div>`);
  if (antwort !== "ja") return;
  const name = $("#neuer-name").value;
  await aendern(id, { name });
  waehle(id);
}

async function wurzelNeu() {
  $("#import-menu").hidden = true;
  const antwort = await dialog(`<h2>Ordner hinzufügen</h2>
    <p class="dim">Pfad auf diesem Rechner, z. B. <code>~/3D-Druck</code>. Die Struktur bleibt, wie sie ist.</p>
    <input type="text" id="wurzel-pfad" placeholder="/home/…/3D-Druck">
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Hinzufügen und einlesen</button></div>`);
  if (antwort !== "ja") return;
  try { await api("/api/wurzeln", { method: "POST", body: { pfad: $("#wurzel-pfad").value } }); toast("Ordner wird eingelesen …"); }
  catch (e) { toast(e.message); }
}

// ---------------------------------------------------------------- Ereignisse

document.addEventListener("click", async (e) => {
  const t = e.target;
  const wahl = t.closest("[data-wahl]");
  if (wahl) { e.stopPropagation(); return waehleAus(wahl.dataset.wahl, e.shiftKey); }
  const st = t.closest("[data-stapel]");
  if (st) return stapelAktion(st.dataset.stapel);
  const lay = t.closest("[data-layout]");
  if (lay) {
    zustand.layout = lay.dataset.layout;
    localStorageSchreiben("layout", zustand.layout);
    document.querySelectorAll("[data-layout]").forEach((b) => b.classList.toggle("an", b.dataset.layout === zustand.layout));
    $("#raster").scrollTop = 0;
    return raster.neu();
  }
  const sort = t.closest("[data-sortiere]");
  if (sort) { zustand.sortierung = sort.dataset.sortiere; $("#sortierung").value = zustand.sortierung; return ladeModelle(); }
  const zeileListe = t.closest(".zeile-l");
  if (zeileListe && (e.ctrlKey || e.metaKey || e.shiftKey)) return waehleAus(zeileListe.dataset.id, e.shiftKey);
  if (zeileListe) return waehle(zeileListe.dataset.id);
  const herz = t.closest("[data-herz]");
  if (herz) {
    e.stopPropagation();
    const m = zustand.modelle.find((x) => x.id === herz.dataset.herz);
    if (m) { m.favorit = !m.favorit; raster.zeichne(); await aendern(m.id, { favorit: m.favorit }); }
    return;
  }
  const klappe = t.closest("[data-klappe]");
  if (klappe && klappe.textContent) {
    const id = klappe.dataset.klappe;
    zustand.offen.has(id) ? zustand.offen.delete(id) : zustand.offen.add(id);
    localStorageSchreiben("offen", JSON.stringify([...zustand.offen]));
    ladeSeite();
    return;
  }
  const k = t.closest(".karte");
  if (k && (e.ctrlKey || e.metaKey || e.shiftKey)) return waehleAus(k.dataset.id, e.shiftKey);
  if (k) return waehle(k.dataset.id);
  const ansicht = t.closest("[data-ansicht]");
  if (ansicht) { Object.assign(zustand, { ansicht: ansicht.dataset.ansicht, ordner: "", tags: new Set(), material: new Set(), format: "", sammlung: "" }); return neuLaden(); }
  const rail = t.closest("[data-rail]");
  if (rail) { Object.assign(zustand, { ansicht: rail.dataset.rail === "papierkorb" ? "papierkorb" : "alle", ordner: "", tags: new Set(), material: new Set(), format: "", sammlung: "" }); return neuLaden(); }
  const ordner = t.closest("[data-ordner]");
  if (ordner) { Object.assign(zustand, { ordner: ordner.dataset.ordner, ansicht: "alle", sammlung: "" }); return neuLaden(); }
  const sammlung = t.closest("[data-sammlung]");
  if (sammlung) { Object.assign(zustand, { sammlung: sammlung.dataset.sammlung, ansicht: "alle", ordner: "", tags: new Set(), material: new Set(), format: "" }); return neuLaden(); }
  const wsWeg = t.closest("[data-ws-weg]");
  if (wsWeg) { await api(`/api/warteschlange/${wsWeg.dataset.wsWeg}`, { method: "DELETE" }); return; }
  const wsWaehle = t.closest("[data-ws-waehle]");
  if (wsWaehle) return waehle(wsWaehle.dataset.wsWaehle);
  const sammlungWeg = t.closest("[data-sammlung-weg]");
  if (sammlungWeg) {
    await api(`/api/sammlungen/${sammlungWeg.dataset.sammlungWeg}/modelle/${$("#inspektor").dataset.id}`, { method: "DELETE" });
    return;
  }
  const tag = t.closest("[data-tag]");
  const mat = t.closest("[data-mat]");
  if (tag || mat) {
    const [wahl, wert] = tag ? [zustand.tags, tag.dataset.tag] : [zustand.material, mat.dataset.mat];
    if (!wert) { zustand.tags.clear(); zustand.material.clear(); }
    else if (wahl.has(wert)) wahl.delete(wert);
    else wahl.add(wert);
    if (zustand.ansicht === "papierkorb") zustand.ansicht = "alle";
    return neuLaden();
  }
  const fmt = t.closest("[data-format]");
  if (fmt) { zustand.format = zustand.format === fmt.dataset.format ? "" : fmt.dataset.format; return neuLaden(); }
  const matWahl = t.closest("[data-mat-wahl]");
  if (matWahl) { $("#s-name").value = matWahl.dataset.matWahl; return; }
  const matWeg = t.closest("[data-material-weg]");
  if (matWeg) {
    const id = $("#inspektor").dataset.id;
    await api(`/api/modelle/${id}/material/${encodeURIComponent(matWeg.dataset.materialWeg)}`, { method: "DELETE" });
    return waehle(id);
  }
  const tagWeg = t.closest("[data-tag-weg]");
  if (tagWeg) {
    const id = $("#inspektor").dataset.id;
    await api(`/api/modelle/${id}/tags/${encodeURIComponent(tagWeg.dataset.tagWeg)}`, { method: "DELETE" });
    return waehle(id);
  }
  const id = $("#inspektor").dataset.id;
  switch (t.id) {
    case "filter-weg": Object.assign(zustand, { ordner: "", tags: new Set(), material: new Set(), format: "", suche: "", sammlung: "", ansicht: "alle" }); $("#suche").value = ""; return neuLaden();
    case "sammlung-neu": return sammlungNeu([]);
    case "sammlung-zu-baugruppe": {
      try {
        const neu = await api("/api/baugruppen", { method: "POST", body: { aus_sammlung: zustand.sammlung } });
        await ladeBaugruppenLeiste();
        oeffneBaugruppe(neu.id);
        toast("Baugruppe angelegt — jetzt Mengen und Kaufteile ergänzen.");
      } catch (e2) { toast(e2.message); }
      return;
    }
    case "zu-baugruppe": return zuBaugruppe([id]);
    case "sammlung-umbenennen": {
      const alt = zustand.sammlungen.find((x) => x.id === zustand.sammlung);
      const a = await dialog(`<h2>Sammlung umbenennen</h2><input type="text" id="s-name" value="${esc(alt?.name)}">
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Umbenennen</button></div>`);
      if (a === "ja") await api(`/api/sammlungen/${zustand.sammlung}`, { method: "PATCH", body: { name: $("#s-name").value } }).catch((e2) => toast(e2.message));
      return;
    }
    case "sammlung-loeschen": {
      const alt = zustand.sammlungen.find((x) => x.id === zustand.sammlung);
      const a = await dialog(`<h2>Sammlung „${esc(alt?.name)}“ löschen?</h2><p>Die Modelle bleiben im Katalog, nur die Sammlung geht.</p>
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Löschen</button></div>`);
      if (a === "ja") { await api(`/api/sammlungen/${zustand.sammlung}`, { method: "DELETE" }); zustand.sammlung = ""; neuLaden(); }
      return;
    }
    case "ansicht-zurueck": viewer?.zuruecksetzen(); return;
    case "ws-knopf": {
      const m = await api(`/api/modelle/${id}`);
      if (m.warteschlange != null) await api(`/api/warteschlange/${id}`, { method: "DELETE" });
      else await api("/api/warteschlange", { method: "POST", body: { modelle: [id] } });
      return;
    }
    case "import-knopf": $("#import-menu").hidden = !$("#import-menu").hidden; return;
    case "wurzel-neu": case "wurzel-neu-2": return wurzelNeu();
    case "hochladen-knopf": $("#import-menu").hidden = true; return $("#datei-wahl").click();
    case "archive-knopf": return archiveEntpacken();
    case "verschieben": {
      const ziel = await ordnerWahl("Verschieben", "Die Datei wird auf der Platte verschoben. Nichts wird überschrieben.");
      if (ziel) await api(`/api/modelle/${id}/verschieben`, { method: "POST", body: { ordner: ziel } }).then(() => toast("Verschoben.")).catch((e2) => toast(e2.message));
      return;
    }
    case "quelle-aendern": {
      const m = await api(`/api/modelle/${id}`);
      const a = await dialog(`<h2>Quelle</h2><p class="dim">Woher das Modell stammt, z. B. Printables oder MakerWorld.</p>
        <input type="text" id="quelle-url" value="${esc(m.quelle_url || "")}" placeholder="https://…">
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Speichern</button></div>`);
      if (a === "ja") await aendern(id, { quelle_url: $("#quelle-url").value });
      return;
    }
    case "neu-einlesen": $("#import-menu").hidden = true; await api("/api/scan", { method: "POST" }); return toast("Wird neu eingelesen …");
    case "gedruckt": { const m = zustand.modelle.find((x) => x.id === id); await aendern(id, { gedruckt: !(m && m.gedruckt) }); return waehle(id); }
    case "favorit": { const m = zustand.modelle.find((x) => x.id === id); await aendern(id, { favorit: !(m && m.favorit) }); return waehle(id); }
    case "oeffnen": { const k = $("#oeffnen"); return modellOeffnen(k.dataset.system ? { system: true } : { pfad: k.dataset.pfad }); }
    case "mehr-knopf": $("#mehr-menu").hidden = !$("#mehr-menu").hidden; return;
    case "gal-plus-menu": $("#mehr-menu").hidden = true; return $("#bild-wahl").click();
    case "umbenennen": return umbenennen(id);
    case "loeschen": return loeschen(id);
    case "wiederherstellen":
      try { await api(`/api/modelle/${id}/wiederherstellen`, { method: "POST" }); toast("Wiederhergestellt."); waehle(null); }
      catch (e2) { toast(e2.message); }
      return;
    case "thema": {
      const neu = document.documentElement.dataset.app === "dark" ? "light" : "dark";
      document.documentElement.dataset.app = neu;
      localStorageSchreiben("thema", neu);
      return;
    }
  }
  if (!t.closest(".import")) $("#import-menu").hidden = true;
  if (!t.closest(".mehr") && $("#mehr-menu")) $("#mehr-menu").hidden = true;
});

document.addEventListener("change", async (e) => {
  if (e.target.id === "mit-tags") { $(".lz-warn").hidden = !e.target.checked; return; }
  if (e.target.id === "material-dazu" && e.target.value) {
    const id = $("#inspektor").dataset.id;
    let wert = e.target.value;
    e.target.value = "";
    if (wert === "__neu") wert = await materialFrage("Neues Material");
    if (!wert) return;
    try { await api(`/api/modelle/${id}/material`, { method: "POST", body: { material: wert } }); } catch (err) { toast(err.message); }
    return waehle(id);
  }
  if (e.target.id === "oeffnen-mit" && e.target.value) {
    const w = e.target.value;
    e.target.value = "";
    if (w === "__einstellungen") return einstellungen();
    return modellOeffnen(w === "__system" ? { system: true } : { pfad: w });
  }
  if (e.target.id === "sammlung-dazu" && e.target.value) {
    const id = $("#inspektor").dataset.id, sid = e.target.value;
    e.target.value = "";
    if (sid === "__neu") return sammlungNeu([id]);
    await api(`/api/sammlungen/${sid}/modelle`, { method: "POST", body: { modelle: [id] } }).catch((err) => toast(err.message));
  }
  if (e.target.id === "stapel-sammlung" && e.target.value) {
    const sid = e.target.value;
    e.target.value = "";
    if (sid === "__neu") return sammlungNeu([...zustand.auswahl]);
    return stapel("sammlung", sid);
  }
  if (e.target.id === "datei-wahl") { const f = e.target.files; await hochladen(f); e.target.value = ""; return; }
  if (e.target.id === "bild-wahl" && e.target.files.length) {
    const dateien = [...e.target.files];
    e.target.value = "";
    return bilderHochladen(dateien);
  }
  if (e.target.id === "sortierung") { zustand.sortierung = e.target.value; ladeModelle(); }
});

document.addEventListener("keydown", async (e) => {
  if (e.target.id === "tag-neu" && e.key === "Enter" && e.target.value.trim()) {
    const id = $("#inspektor").dataset.id;
    try { await api(`/api/modelle/${id}/tags`, { method: "POST", body: { tag: e.target.value } }); }
    catch (err) { toast(err.message); }
    waehle(id);
  }
  const tippt = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName) || $("#dialog").open;
  if (e.key === "/" && !tippt) { e.preventDefault(); $("#suche").focus(); }
  if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && !tippt && !$("#dialog").open && $("#i-galerie")?.matches(":hover")) {
    e.preventDefault();
    galerieBlaettern(e.key === "ArrowRight" ? 1 : -1);
  }
  // Escape hebt die Auswahl auch aus dem Suchfeld heraus auf — nur ein
  // offener Dialog schliesst zuerst sich selbst.
  if (e.key === "Escape" && zustand.auswahl.size && !$("#dialog").open) stapelAktion("keine");
  if ((e.key === "Delete" || e.key === "Backspace") && zustand.auswahl.size && !tippt && zustand.ansicht !== "papierkorb") {
    e.preventDefault();
    loeschenViele([...zustand.auswahl]);
  }
});

let suchZeit;
$("#suche").addEventListener("input", (e) => {
  clearTimeout(suchZeit);
  suchZeit = setTimeout(() => { zustand.suche = e.target.value.trim(); ladeModelle(); }, 150);
});

function neuLaden() {
  ladeModelle();
  ladeSeite();
  if (typeof ladeBaugruppenLeiste === "function") ladeBaugruppenLeiste();
  if (zustand.baugruppe) ladeBaugruppe();
}

async function sammlungNeu(modelle) {
  const a = await dialog(`<h2>Neue Sammlung</h2><p class="dim">Mehrere Modelle zu einem Projekt zusammenfassen.</p>
    <input type="text" id="s-name" placeholder="z. B. Drohne V2">
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Anlegen</button></div>`);
  if (a !== "ja") return;
  try { await api("/api/sammlungen", { method: "POST", body: { name: $("#s-name").value, modelle } }); }
  catch (e) { toast(e.message); }
}

// ---------------------------------------------------------------- Ziehen und Ablegen
//
// Kachel → Sammlung oder Warteschlange: hinzufügen. Innerhalb einer
// Sammlung, der Warteschlange im Raster oder der Liste links: umsortieren.

let gezogen = null;          // {art: "modell"|"ws", id}

document.addEventListener("dragstart", (e) => {
  const k = e.target.closest?.(".karte, .zeile-l"), w = e.target.closest?.("[data-ws]");
  if (k) { gezogen = { art: "modell", id: k.dataset.id }; k.classList.add("ziehen"); }
  else if (w) gezogen = { art: "ws", id: w.dataset.ws };
  else return;
  e.dataTransfer.effectAllowed = "copyMove";
  e.dataTransfer.setData("text/plain", gezogen.id);
});
document.addEventListener("dragend", () => {
  gezogen = null;
  document.querySelectorAll(".ziehen, .ziehziel").forEach((x) => x.classList.remove("ziehen", "ziehziel"));
});

// Zieht man eine gewählte Kachel, gelten alle Gewählten.
const gezogene = () => (zustand.auswahl.has(gezogen.id) ? [...zustand.auswahl] : [gezogen.id]);

function ablageZiel(el) {
  if (!gezogen || !el?.closest) return null;
  const bg = el.closest("#baugruppen [data-baugruppe]");
  if (bg && gezogen.art === "modell") return bg;
  const o = el.closest("[data-ordner]");
  if (o && gezogen.art === "modell" && zustand.ansicht !== "papierkorb") return o;
  const s = el.closest("[data-sammlung]");
  if (s && gezogen.art === "modell") return s;
  const ws = el.closest('[data-ansicht="warteschlange"], [data-ws]');
  if (ws) return ws;
  const k = el.closest(".karte");
  if (k && k.dataset.id !== gezogen.id && (zustand.sammlung || zustand.ansicht === "warteschlange")) return k;
  return null;
}
document.addEventListener("dragover", (e) => {
  const z = ablageZiel(e.target);
  if (!z) return;
  e.preventDefault();
  document.querySelectorAll(".ziehziel").forEach((x) => x !== z && x.classList.remove("ziehziel"));
  z.classList.add("ziehziel");
});
document.addEventListener("drop", async (e) => {
  const z = ablageZiel(e.target);
  if (!z) return;
  e.preventDefault();
  const g = gezogen;
  try {
    if (z.dataset.baugruppe) {
      await api(`/api/baugruppen/${z.dataset.baugruppe}/positionen`, { method: "POST", body: { refs: gezogene().map((x) => `MODEL_ASSET/${x}`) } });
      toast("Zur Baugruppe hinzugefügt.");
    } else if (z.dataset.ordner) {
      const r = await api("/api/stapel", { method: "POST", body: { aktion: "verschieben", modelle: gezogene(), wert: z.dataset.ordner } });
      toast(r.fehler.length ? r.fehler[0].fehler : "Verschoben.");
    } else if (z.dataset.sammlung) {
      await api(`/api/sammlungen/${z.dataset.sammlung}/modelle`, { method: "POST", body: { modelle: gezogene() } });
      toast("Zur Sammlung hinzugefügt.");
    } else if (z.dataset.ws || z.dataset.ansicht === "warteschlange") {
      const reihe = [...document.querySelectorAll("[data-ws]")].map((x) => x.dataset.ws);
      if (!reihe.includes(g.id)) await api("/api/warteschlange", { method: "POST", body: { modelle: [g.id] } });
      if (z.dataset.ws) await api("/api/warteschlange", { method: "PUT", body: { modelle: vorSetzen(reihe.includes(g.id) ? reihe : [...reihe, g.id], g.id, z.dataset.ws) } });
    } else if (z.classList.contains("karte")) {
      const neu = vorSetzen(zustand.modelle.map((m) => m.id), g.id, z.dataset.id);
      if (zustand.sammlung) await api(`/api/sammlungen/${zustand.sammlung}/reihenfolge`, { method: "PUT", body: { modelle: neu } });
      else await api("/api/warteschlange", { method: "PUT", body: { modelle: neu } });
    }
  } catch (err) { toast(err.message); }
});

// `wer` vor `vor` einsortieren.
function vorSetzen(liste, wer, vor) {
  const ohne = liste.filter((x) => x !== wer);
  const i = ohne.indexOf(vor);
  ohne.splice(i < 0 ? ohne.length : i, 0, wer);
  return ohne;
}

// ---------------------------------------------------------------- Live (flatgraph bei_aenderung → SSE)

let liveZeit, liveBetrifft = false;
function live() {
  const q = new EventSource("/api/live");
  q.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.art === "scan") {
      $("#scan-status").textContent = m.laeuft
        ? `Einlesen: ${m.phase}${m.analysiert != null && m.zu_analysieren ? ` ${m.analysiert}/${m.zu_analysieren}` : ""}`
        : (m.vorschauen_offen ? "" : "");
      if (m.phase === "vorschau" && m.vorschauen_offen) $("#scan-status").textContent = `Vorschauen: noch ${m.vorschauen_offen}`;
      if (m.phase === "fertig") { $("#scan-status").textContent = ""; neuLaden(); }
      return;
    }
    // Viele Änderungen hintereinander (Scan) sammeln, dann einmal laden.
    const meins = zustand.gewaehlt && [m.ref, m.quelle, m.ziel].includes(`MODEL_ASSET/${zustand.gewaehlt}`);
    if (meins) liveBetrifft = true;
    clearTimeout(liveZeit);
    liveZeit = setTimeout(() => {
      neuLaden();
      if (liveBetrifft && zustand.gewaehlt && document.activeElement?.id !== "tag-neu") waehle(zustand.gewaehlt);
      liveBetrifft = false;
    }, 300);
  };
}

document.documentElement.dataset.app = localStorageLesen("thema") || "dark";
neuLaden();
live();

// Dateien aus dem Dateimanager ins Fenster ziehen: hochladen.
let abwurfZaehler = 0;
const vonAussen = (e) => !gezogen && [...(e.dataTransfer?.types || [])].includes("Files");
window.addEventListener("dragenter", (e) => { if (vonAussen(e)) { abwurfZaehler++; $("#abwurf").hidden = false; } });
window.addEventListener("dragleave", (e) => {
  if (vonAussen(e) && --abwurfZaehler <= 0) { abwurfZaehler = 0; $("#abwurf").hidden = true; $("#i-galerie")?.classList.remove("abwurf-ziel"); }
});
window.addEventListener("dragover", (e) => {
  if (!vonAussen(e)) return;
  e.preventDefault();
  const aufGalerie = !!(e.target.closest?.("#i-galerie") && galerie.m && !galerie.m.papierkorb);
  $("#i-galerie")?.classList.toggle("abwurf-ziel", aufGalerie);
  $("#abwurf").hidden = aufGalerie;
});
window.addEventListener("drop", (e) => {
  if (!vonAussen(e)) return;
  e.preventDefault();
  abwurfZaehler = 0;
  $("#abwurf").hidden = true;
  $("#i-galerie")?.classList.remove("abwurf-ziel");
  // Auf die Galerie gezogen: Bilder zum Modell, keine neuen Modelldateien.
  if (e.target.closest?.("#i-galerie") && galerie.m && !galerie.m.papierkorb) return bilderHochladen(e.dataTransfer.files);
  hochladen(e.dataTransfer.files);
});
document.querySelectorAll("[data-layout]").forEach((b) => b.classList.toggle("an", b.dataset.layout === zustand.layout));

// Datei-Details auf- oder zugeklappt lassen, wie man es zuletzt wollte.
document.addEventListener("toggle", (e) => {
  if (e.target.id === "i-details") localStorageSchreiben("details", e.target.open ? "1" : "0");
}, true);
