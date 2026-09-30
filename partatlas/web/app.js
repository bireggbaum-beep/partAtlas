// partAtlas — Oberfläche ohne Framework (wie pDMS). Aufbau nach dem 3MF
// Katalog: Seitenleiste, Raster, Inspektor. Das Raster ist virtuell: es
// zeichnet nur die sichtbaren Kacheln, damit 10 000 Modelle nicht den
// Browser lahmlegen (vermutete Ursache für „nicht gescheit“ bei 5 700).
"use strict";

const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const zustand = {
  modelle: [], ansicht: "alle", tag: "", ordner: "", format: "", suche: "", sammlung: "", sammlungen: [],
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
  const p = new URLSearchParams({ q: zustand.suche, tag: zustand.tag, ordner: zustand.ordner,
                                  format: zustand.format, ansicht: zustand.ansicht, sammlung: zustand.sammlung });
  const liste = await api("/api/modelle?" + p);
  const s = (zustand.sammlung || zustand.ansicht === "warteschlange") ? "eigene" : zustand.sortierung;
  if (s === "neu") liste.sort((a, b) => (b.angelegt || "").localeCompare(a.angelegt || ""));
  if (s === "gewicht") liste.sort((a, b) => (b.gewicht_g || 0) - (a.gewicht_g || 0));
  if (s === "groesse") liste.sort((a, b) => Math.max(...(b.masse || [0])) - Math.max(...(a.masse || [0])));
  zustand.modelle = liste;
  $("#anzahl").textContent = `${liste.length.toLocaleString("de-DE")} Dateien`;
  zeichneFilterzeile();
  raster.neu();
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
    `<button class="eintrag ${zustand.tag === t.name ? "aktiv" : ""}" data-tag="${esc(t.name)}"><span>#${esc(t.name)}</span><em>${t.anzahl}</em></button>`).join("");
  $("#tagleiste").innerHTML = `<button class="chip ${zustand.tag ? "" : "aktiv"}" data-tag="">#Alle</button>` +
    tags.slice(0, 14).map((t) => `<button class="chip ${zustand.tag === t.name ? "aktiv" : ""}" data-tag="${esc(t.name)}">#${esc(t.name)}</button>`).join("");
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
    b.classList.toggle("aktiv", b.dataset.ansicht === zustand.ansicht && !zustand.ordner && !zustand.tag && !zustand.format && !zustand.sammlung));
  document.querySelectorAll(".rail-btn[data-rail]").forEach((b) =>
    b.classList.toggle("aktiv", (b.dataset.rail === "papierkorb") === (zustand.ansicht === "papierkorb")));
}

function zeichneFilterzeile() {
  const teile = [];
  const sammlung = zustand.sammlungen.find((x) => x.id === zustand.sammlung);
  if (sammlung) teile.push(`Sammlung <b>${esc(sammlung.name)}</b> <button id="sammlung-umbenennen">umbenennen</button> <button id="sammlung-loeschen">löschen</button> <span class="dim">· Reihenfolge per Ziehen</span>`);
  if (zustand.ansicht === "warteschlange") teile.push(`Warteschlange <span class="dim">· Reihenfolge per Ziehen</span>`);
  if (zustand.ordner) teile.push(`Ordner ${esc(zustand.ordner.split("/").slice(1).join("/") || "(Wurzel)")}`);
  if (zustand.tag) teile.push(`#${esc(zustand.tag)}`);
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

// ---------------------------------------------------------------- Virtuelles Raster

const raster = (() => {
  const B = 164, H = 246, LUECKE = 14, RAND = 14;
  const aussen = $("#raster"), innen = $("#raster-innen");
  let spalten = 1, geplant = false;

  function neu() {
    spalten = Math.max(1, Math.floor((aussen.clientWidth - RAND * 2 + LUECKE) / (B + LUECKE)));
    const zeilen = Math.ceil(zustand.modelle.length / spalten);
    innen.style.height = `${RAND * 2 + zeilen * (H + LUECKE)}px`;
    zeichne();
  }

  function zeichne() {
    geplant = false;
    const oben = aussen.scrollTop, hoehe = aussen.clientHeight;
    const von = Math.max(0, Math.floor((oben - RAND) / (H + LUECKE)) - 2);
    const bis = Math.ceil((oben + hoehe) / (H + LUECKE)) + 2;
    const html = [];
    for (let z = von; z < bis; z++) {
      for (let s = 0; s < spalten; s++) {
        const i = z * spalten + s;
        const m = zustand.modelle[i];
        if (!m) break;
        html.push(karte(m, RAND + s * (B + LUECKE), RAND + z * (H + LUECKE)));
      }
    }
    innen.innerHTML = html.join("");
  }

  aussen.addEventListener("scroll", () => { if (!geplant) { geplant = true; requestAnimationFrame(zeichne); } });
  window.addEventListener("resize", () => requestAnimationFrame(neu));
  return { neu, zeichne };
})();

function bildUrl(m) {
  return m.hash && ["eingebettet", "gerendert"].includes(m.vorschau) ? `/api/vorschau/${m.hash}.png` : null;
}

function karte(m, x, y) {
  const url = bildUrl(m);
  const platz = m.vorschau === "ausstehend" ? "Vorschau wird gerendert …" : (m.format === "step" ? "STEP · nur CAD" : "keine Vorschau");
  const status = m.fehlt ? `<span class="badge warn">⚠ Datei fehlt</span>`
    : m.fehler ? `<span class="badge warn">unlesbar</span>`
    : m.gedruckt ? `<span class="badge gedruckt">✓ Gedruckt${m.gewicht_g ? " · " + zahl(m.gewicht_g, 2) + " g" : ""}</span>` : "";
  const unter = [masse(m.masse), m.gewicht_g ? `${zahl(m.gewicht_g, 1)} g${m.material ? " | " + esc(m.material) : ""}` : ""].filter(Boolean).join(" · ");
  return `<div class="karte ${zustand.gewaehlt === m.id ? "gewaehlt" : ""}" draggable="true" style="left:${x}px;top:${y}px" data-id="${esc(m.id)}">
    <div class="bild">${url ? `<img loading="lazy" src="${url}" alt="">` : `<div class="platzhalter">${platz}</div>`}
      ${istNeu(m) ? '<span class="badge neu">NEU</span>' : ""}
      <span class="badge format">${esc(endung[m.format] || m.format || "?")}</span>
      ${zustand.ansicht === "papierkorb" ? "" : `<button class="herz ${m.favorit ? "an" : ""}" data-herz="${esc(m.id)}" title="Favorit">♥</button>`}
      ${status}</div>
    <div class="text"><div class="name" title="${esc(m.name)}">${esc(m.name)}${esc(endung[m.format] || "")}</div>
      <div class="masse">${unter || "&nbsp;"}</div>
      <div class="tags">${m.tags.slice(0, 5).map((t) => `<span>#${esc(t)}</span>`).join("")}</div></div></div>`;
}

// ---------------------------------------------------------------- Inspektor

async function waehle(id) {
  zustand.gewaehlt = id;
  raster.zeichne();
  if (!id) { zustand.angezeigt = null; if (dreiDModul) (await dreiD()).schliessen(); $("#inspektor").innerHTML = `<p class="hinweis">Wähle ein Modell aus, um Details, Vorschau und Tags zu sehen.</p>`; return; }
  const [m, slicer] = await Promise.all([api(`/api/modelle/${id}`), ladeSlicer()]);
  if (zustand.gewaehlt !== id) return;
  const url = bildUrl(m);
  const zeilen = [
    ["Grösse", masse(m.masse) || "–"],
    ["Volumen", m.volumen_cm3 != null ? zahl(m.volumen_cm3) + " cm³" : "–"],
    ["Gewicht (aus Slicer)", m.gewicht_g ? zahl(m.gewicht_g, 2) + " g" : "–"],
    ["Objekte", m.objekte ?? "–"],
    ["Druckplatten", m.platten.length || "–"],
    ["Dreiecke", m.dreiecke != null ? zahl(m.dreiecke, 0) : "–"],
    ["Ersteller", m.designer || "–"],
    ["Eingelesen", m.eingelesen ? new Date(m.eingelesen).toLocaleDateString("de-DE") : "–"],
  ];
  const platten = m.platten.map((p) => `<div class="zeile"><span>Platte ${p.nr}</span><span>${p.filamente.map((f) =>
    `<span class="farbpunkt" style="background:${esc(f.farbe || "transparent")}"></span>${esc(f.typ || "?")} ${zahl(f.g, 2)} g`).join("<br>")}</span></div>`).join("");
  const papierkorb = m.papierkorb;
  // Dasselbe Modell neu gezeichnet (Tag dazu, Live-Meldung): die 3D-Ansicht
  // bleibt stehen, statt das Netz neu zu laden.
  const altesBild = zustand.angezeigt === id ? $("#i-bild") : null;
  $("#inspektor").innerHTML = `
    <div class="i-bild" id="i-bild"></div>
    <div class="i-name">${esc(m.name)}${esc(endung[m.format] || "")}</div>
    ${m.fehler_text ? `<p class="fehler">Unlesbar: ${esc(m.fehler_text)}</p>` : ""}
    ${m.fehlt ? `<p class="fehler">Die Datei ist an keinem bekannten Ort mehr. Tags und Historie bleiben erhalten.</p>` : ""}
    <div class="i-karte">${zeilen.map(([a, b]) => `<div class="zeile"><span>${a}</span><span>${esc(b)}</span></div>`).join("")}</div>
    ${platten ? `<div class="i-titel">FILAMENTVERBRAUCH (AUS SLICER)</div><div class="i-karte">${platten}</div>` : ""}
    ${papierkorb ? "" : `<div class="i-titel">HASHTAGS</div>
    <div class="i-tags">${m.tags.map((t) => `<span class="chip">#${esc(t)}<button data-tag-weg="${esc(t)}" title="entfernen">×</button></span>`).join("")}
      <input id="tag-neu" placeholder="Tag hinzufügen" autocomplete="off"></div>`}
    ${papierkorb ? "" : `<div class="i-titel">SAMMLUNGEN</div>
    <div class="i-sammlungen">${m.sammlungen.map((x) => `<span class="chip">${esc(x.name)}<button data-sammlung-weg="${esc(x.id)}" title="aus der Sammlung">×</button></span>`).join("")}
      <select class="knopf" id="sammlung-dazu"><option value="">＋ Zu Sammlung …</option>${zustand.sammlungen
        .filter((x) => !m.sammlungen.some((y) => y.id === x.id)).map((x) => `<option value="${esc(x.id)}">${esc(x.name)}</option>`).join("")}
        <option value="__neu">Neue Sammlung …</option></select></div>`}
    <div class="i-titel">${papierkorb ? "LAG ZULETZT IN" : "ORT" + (m.orte.length > 1 ? "E (" + m.orte.length + ")" : "")}</div>
    ${(papierkorb ? m.papierkorb_ablage : m.orte).map((o) => `<div class="ort">${esc(o.absolut || o.pfad)}</div>`).join("") || '<div class="dim">–</div>'}
    <div class="i-knoepfe">${papierkorb
      ? `<button class="knopf akzent" id="wiederherstellen">Wiederherstellen</button>`
      : `<button class="knopf ${m.gedruckt ? "akzent" : ""}" id="gedruckt">${m.gedruckt ? "✓ Gedruckt" : "Nicht gedruckt"}</button>
         <button class="knopf ${m.favorit ? "akzent" : ""}" id="favorit">♥</button>
         <button class="knopf" id="ws-knopf">${m.warteschlange != null ? "Aus Warteschlange entfernen" : "☰ In Warteschlange"}</button>
         ${slicer.length ? `<select class="knopf" id="slicer"><option value="">↗ Im Slicer öffnen …</option>${slicer.map((s) =>
            `<option value="${esc(s.pfad)}">${esc(s.name)}</option>`).join("")}</select>` : `<span class="dim">Kein Slicer gefunden</span>`}
         <button class="knopf" id="umbenennen">Umbenennen</button>
         <button class="knopf gefahr" id="loeschen">Löschen</button>`}</div>`;
  $("#inspektor").dataset.id = id;
  if (altesBild) { $("#i-bild").replaceWith(altesBild); return; }
  zustand.angezeigt = id;
  zeigeBild(m, url);
}

// ---------------------------------------------------------------- 3D oder Bild
//
// Wie im 3MF Katalog umschaltbar; die Wahl bleibt gespeichert. Ohne WebGL
// (alte Hardware) gibt es nur das Bild — das rendert der Server.

let viewer = null, dreiDModul = null;
async function dreiD() {
  if (!dreiDModul) dreiDModul = import("/web/viewer.js");
  return dreiDModul;
}

async function zeigeBild(m, url) {
  const feld = $("#i-bild");
  if (!feld) return;
  const hatNetz = !m.papierkorb && !m.fehlt && !m.fehler_text && m.format !== "step";
  const v = await dreiD().catch(() => null);
  const kann3d = hatNetz && v && v.webglMoeglich();
  const will3d = kann3d && localStorageLesen("ansicht") !== "bild";
  if (v) v.schliessen();
  viewer = null;
  const umschalter = kann3d ? `<div class="umschalter"><button data-ansicht3d="3d" class="${will3d ? "an" : ""}">3D-Ansicht</button><button data-ansicht3d="bild" class="${will3d ? "" : "an"}">Bild</button></div>` : "";
  if (!will3d) {
    feld.innerHTML = umschalter + (url ? `<img src="${url}" alt="">` : `<span class="dim">${m.format === "step" ? "STEP · nur CAD" : "keine Vorschau"}</span>`);
    return;
  }
  feld.innerHTML = umschalter + `<span class="laden">3D wird geladen …</span><button class="bild-knopf" id="ansicht-zurueck" title="Ansicht zurücksetzen">⟲</button>`;
  try {
    const antwort = await fetch(`/api/modelle/${m.id}/netz`);
    if (!antwort.ok) throw new Error((await antwort.json().catch(() => ({}))).detail || "Netz nicht lesbar");
    const puffer = await antwort.arrayBuffer();
    if (zustand.gewaehlt !== m.id || !$("#i-bild")) return;
    feld.querySelector(".laden")?.remove();
    const farbe = m.platten.flatMap((p) => p.filamente).map((f) => f.farbe).find(Boolean) || null;
    viewer = v.zeige(feld, puffer, farbe);
  } catch (e) {
    feld.innerHTML = umschalter + (url ? `<img src="${url}" alt="">` : "") + `<span class="dim">${esc(e.message)}</span>`;
  }
}

let slicerCache = null;
async function ladeSlicer() {
  if (!slicerCache) slicerCache = api("/api/slicer").catch(() => []);
  return slicerCache;
}

async function aendern(id, werte) {
  try { await api(`/api/modelle/${id}`, { method: "PATCH", body: werte }); }
  catch (e) { toast(e.message); }
}

// ---------------------------------------------------------------- Dialoge

function dialog(html) {
  const d = $("#dialog");
  $("#dialog-inhalt").innerHTML = html;
  d.showModal();
  return new Promise((ok) => d.addEventListener("close", () => ok(d.returnValue), { once: true }));
}

async function loeschen(id) {
  const [m, v] = await Promise.all([api(`/api/modelle/${id}`), api(`/api/modelle/${id}/loeschen`)]);
  const kanten = Object.entries(v.kanten).map(([art, n]) => `${n} × ${esc(art)}`).join(", ");
  const antwort = await dialog(`<h2>„${esc(m.name)}“ löschen?</h2>
    <p>Diese Dateien kommen in den Papierkorb von partAtlas und verschwinden aus ihrem Ordner:</p>
    <ul>${v.dateien.map((d) => `<li>${esc(d)}</li>`).join("") || "<li>keine (Datei fehlt schon)</li>"}</ul>
    <p class="dim">Mit in den Papierkorb (flatgraph <code>loeschfolgen</code>): ${v.knoten.length} Datei-Knoten${kanten ? "; Verknüpfungen: " + kanten : ""}.
    Wiederherstellen legt alles zurück an seinen Ort.</p>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">In den Papierkorb</button></div>`);
  if (antwort !== "ja") return;
  try { await api(`/api/modelle/${id}/loeschen`, { method: "POST" }); waehle(null); toast("In den Papierkorb gelegt."); }
  catch (e) { toast(e.message); }
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
  if (k) return waehle(k.dataset.id);
  const ansicht = t.closest("[data-ansicht]");
  if (ansicht) { Object.assign(zustand, { ansicht: ansicht.dataset.ansicht, ordner: "", tag: "", format: "", sammlung: "" }); return neuLaden(); }
  const rail = t.closest("[data-rail]");
  if (rail) { Object.assign(zustand, { ansicht: rail.dataset.rail === "papierkorb" ? "papierkorb" : "alle", ordner: "", tag: "", format: "", sammlung: "" }); return neuLaden(); }
  const ordner = t.closest("[data-ordner]");
  if (ordner) { Object.assign(zustand, { ordner: ordner.dataset.ordner, ansicht: "alle", sammlung: "" }); return neuLaden(); }
  const sammlung = t.closest("[data-sammlung]");
  if (sammlung) { Object.assign(zustand, { sammlung: sammlung.dataset.sammlung, ansicht: "alle", ordner: "", tag: "", format: "" }); return neuLaden(); }
  const d3 = t.closest("[data-ansicht3d]");
  if (d3) { localStorageSchreiben("ansicht", d3.dataset.ansicht3d); zustand.angezeigt = null; return waehle(zustand.gewaehlt); }
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
  if (tag) { zustand.tag = tag.dataset.tag; if (zustand.ansicht === "papierkorb") zustand.ansicht = "alle"; return neuLaden(); }
  const fmt = t.closest("[data-format]");
  if (fmt) { zustand.format = zustand.format === fmt.dataset.format ? "" : fmt.dataset.format; return neuLaden(); }
  const tagWeg = t.closest("[data-tag-weg]");
  if (tagWeg) {
    const id = $("#inspektor").dataset.id;
    await api(`/api/modelle/${id}/tags/${encodeURIComponent(tagWeg.dataset.tagWeg)}`, { method: "DELETE" });
    return waehle(id);
  }
  const id = $("#inspektor").dataset.id;
  switch (t.id) {
    case "filter-weg": Object.assign(zustand, { ordner: "", tag: "", format: "", suche: "", sammlung: "", ansicht: "alle" }); $("#suche").value = ""; return neuLaden();
    case "sammlung-neu": return sammlungNeu([]);
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
    case "neu-einlesen": $("#import-menu").hidden = true; await api("/api/scan", { method: "POST" }); return toast("Wird neu eingelesen …");
    case "gedruckt": { const m = zustand.modelle.find((x) => x.id === id); await aendern(id, { gedruckt: !(m && m.gedruckt) }); return waehle(id); }
    case "favorit": { const m = zustand.modelle.find((x) => x.id === id); await aendern(id, { favorit: !(m && m.favorit) }); return waehle(id); }
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
});

document.addEventListener("change", async (e) => {
  if (e.target.id === "slicer" && e.target.value) {
    const id = $("#inspektor").dataset.id;
    try { await api(`/api/modelle/${id}/slicer`, { method: "POST", body: { pfad: e.target.value } }); toast("Slicer wird geöffnet …"); }
    catch (err) { toast(err.message); }
    e.target.value = "";
  }
  if (e.target.id === "sammlung-dazu" && e.target.value) {
    const id = $("#inspektor").dataset.id, sid = e.target.value;
    e.target.value = "";
    if (sid === "__neu") return sammlungNeu([id]);
    await api(`/api/sammlungen/${sid}/modelle`, { method: "POST", body: { modelle: [id] } }).catch((err) => toast(err.message));
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
  if (e.key === "/" && !["INPUT", "SELECT"].includes(document.activeElement.tagName)) { e.preventDefault(); $("#suche").focus(); }
});

let suchZeit;
$("#suche").addEventListener("input", (e) => {
  clearTimeout(suchZeit);
  suchZeit = setTimeout(() => { zustand.suche = e.target.value.trim(); ladeModelle(); }, 150);
});

function neuLaden() { ladeModelle(); ladeSeite(); }

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
  const k = e.target.closest?.(".karte"), w = e.target.closest?.("[data-ws]");
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

function ablageZiel(el) {
  if (!gezogen || !el?.closest) return null;
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
    if (z.dataset.sammlung) {
      await api(`/api/sammlungen/${z.dataset.sammlung}/modelle`, { method: "POST", body: { modelle: [g.id] } });
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
