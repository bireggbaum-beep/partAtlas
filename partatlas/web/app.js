// partAtlas — Oberfläche ohne Framework (wie pDMS). Aufbau nach dem 3MF
// Katalog: Seitenleiste, Raster, Inspektor. Das Raster ist virtuell: es
// zeichnet nur die sichtbaren Kacheln, damit 10 000 Modelle nicht den
// Browser lahmlegen (vermutete Ursache für „nicht gescheit“ bei 5 700).
"use strict";

// Phase 1: Katalog und Öffnen im Slicer/CAD. Was ein Druckmanagement voraussetzt
// (Warteschlange), ist ausgeblendet, nicht gelöscht — `data-ab-phase="2"` in der
// Seitenleiste, Filter bei den Menüs. In Phase 2 genügt PHASE = 2.
const PHASE = Number(new URLSearchParams(location.search).get("phase")) || 1;   // ?phase=2: zum Testen und Vorzeigen
document.documentElement.dataset.phase = PHASE;
const ab2 = (k) => PHASE >= 2 || !["ws", "warteschlange"].includes(k);

// Fehler in der Oberfläche kommen ins Protokoll des Servers (partatlas.log): im Browser sieht sie sonst nur, wer die Konsole offen hat.
// Höchstens ein paar je Seite, damit eine Fehlerschleife nichts füllt; schlägt das Melden selbst fehl, wird es still verworfen.
const clientFehler = { n: 0 };
function fehlerMelden(meldung, ort) {
  if (clientFehler.n++ >= 20) return;
  try {
    fetch("/api/clientfehler", { method: "POST", headers: { "Content-Type": "application/json" }, keepalive: true,
      body: JSON.stringify({ meldung: String(meldung), ort: String(ort || "") }) }).catch(() => {});
  } catch { /* nichts zu tun */ }
}
window.addEventListener("error", (e) => fehlerMelden(e.message, `${e.filename || ""}:${e.lineno || ""}:${e.colno || ""}`));
window.addEventListener("unhandledrejection", (e) => fehlerMelden(e.reason?.stack || e.reason, "Promise"));

const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const zustand = {
  modelle: [], ansicht: "alle", tags: new Set(), material: new Set(), ordner: "", format: "", suche: "", sammlung: "", sammlungen: [],
  ohneEntwuerfe: localStorageLesen("ohneEntwuerfe") === "1",
  auswahl: new Set(), layout: ["liste", "karten"].includes(localStorageLesen("layout")) ? localStorageLesen("layout") : "raster",
  sortierung: "name", gruppierung: ["ordner", "format", "material", "status", "angelegt"].includes(localStorageLesen("gruppierung")) ? localStorageLesen("gruppierung") : "keine",
  gruppen: [], eingeklappt: new Set(), wurzelNamen: new Map(), gewaehlt: null, offen: new Set(JSON.parse(localStorageLesen("offen") || "[]")),
};

// Zeichnet `html` in `ziel`, ohne unveränderte Elemente auszutauschen. Ein
// Klick besteht aus Drücken und Loslassen; wird das Element dazwischen durch
// ein gleich aussehendes ersetzt (Live-Meldung, Nachladen), geht der Klick
// verloren. Deshalb: nur anfassen, was sich geändert hat. Elemente mit
// data-id (Kacheln, Zeilen) werden über diese Kennung wiedererkannt.
function abgleichen(ziel, html) {
  if (ziel._html === html) return;
  ziel._html = html;
  const vorlage = document.createElement("template");
  vorlage.innerHTML = html;
  kinderAbgleichen(ziel, vorlage.content);
}

const schluessel = (n) => (n.nodeType === 1 ? n.getAttribute("data-id") : null);

function kinderAbgleichen(alt, neu) {
  const vorhandene = [...alt.childNodes];
  const nachKennung = new Map(vorhandene.filter(schluessel).map((n) => [schluessel(n), n]));
  const frei = vorhandene.filter((n) => !schluessel(n));
  const gebraucht = new Set();
  const passend = [];
  for (const n of neu.childNodes) {
    const k = schluessel(n);
    let a = k ? nachKennung.get(k) : null;
    if (!a && !k) {
      const i = frei.findIndex((x) => x.nodeType === n.nodeType && x.nodeName === n.nodeName && !gebraucht.has(x));
      if (i >= 0) a = frei[i];
    }
    if (a && !gebraucht.has(a) && a.nodeName === n.nodeName) { gebraucht.add(a); passend.push([a, n]); }
    else passend.push([null, n]);
  }
  for (const n of vorhandene) if (!gebraucht.has(n)) n.remove();
  let stelle = alt.firstChild;
  for (const [a, n] of passend) {
    if (!a) { alt.insertBefore(document.importNode(n, true), stelle); continue; }
    if (a !== stelle) alt.insertBefore(a, stelle); else stelle = stelle.nextSibling;
    knotenAbgleichen(a, n);
  }
}

function knotenAbgleichen(a, n) {
  if (a.nodeType !== 1) { if (a.nodeValue !== n.nodeValue) a.nodeValue = n.nodeValue; return; }
  if (a.isEqualNode(n)) return;
  for (const at of [...a.attributes]) if (!n.hasAttribute(at.name)) a.removeAttribute(at.name);
  for (const at of n.attributes) if (a.getAttribute(at.name) !== at.value) a.setAttribute(at.name, at.value);
  if (a.nodeName === "INPUT" && a.type === "checkbox") a.checked = n.hasAttribute("checked");
  kinderAbgleichen(a, n);
}

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

// `aktionen`: [[Beschriftung, Aufruf]] — Knöpfe in der Meldung („Zeigen“). `dauer` in ms.
function toast(text, { aktionen = [], dauer = 3500 } = {}) {
  const t = $("#toast");
  t.textContent = text;
  for (const [was, aufruf] of aktionen) {
    const k = document.createElement("button");
    k.textContent = was;
    k.onclick = () => { t.hidden = true; aufruf(); };
    t.append(k);
  }
  t.hidden = false;
  clearTimeout(toast.zeit);
  toast.zeit = setTimeout(() => (t.hidden = true), dauer);
}

const zahl = (x, stellen = 1) => x == null ? "–" : Number(x).toLocaleString("de-DE", { maximumFractionDigits: stellen });
const masse = (m) => m ? m.map((v) => zahl(v)).join(" × ") + " mm" : "";
const endung = { "3mf": ".3mf", stl: ".stl", obj: ".obj", step: ".step", fcstd: ".FCStd" };
// CAD-Formate ohne Netz: keine Masse, keine 3D-Ansicht; ein Bild nur, wenn die Datei eins mitbringt.
const nurCad = (m) => (m.format === "step" || m.format === "fcstd") && m.cad !== "ok";
const nurCadText = (m) => m.format === "step" && m.cad !== "fehler" && zustand.worker?.laeuft ? "Vorschau folgt (FreeCAD) …" : `${m.format === "fcstd" ? "FCStd" : "STEP"} · nur CAD`;
const istNeu = (m) => m.angelegt && (Date.now() - new Date(m.angelegt).getTime()) < 7 * 864e5;

// ---------------------------------------------------------------- Laden

// ---------------------------------------------------------------- Gruppieren
//
// Wie Sortieren, nur mit Bändern dazwischen. Die Liste wird einmal in Gruppenreihenfolge gebracht (innerhalb
// einer Gruppe bleibt die gewählte Sortierung), danach zählen alle Indizes wie bei einer flachen Liste.
// Gibt es nur eine Gruppe, steht kein Band da: es gäbe nichts zu trennen (etwa ein Ordner ohne Unterordner).

const natuerlich = (a, b) => a.localeCompare(b, "de", { numeric: true, sensitivity: "base" });
const wurzelName = (id) => zustand.wurzelNamen.get(id) || id;

// Der Ordner eines Modells hat die Form „Wurzel/Pfad“. Gruppiert wird nach der **nächsten Ebene** unter dem, was in der
// Seitenleiste gewählt ist (ohne Wahl: die Wurzeln): jede Gruppe ist ein direktes Kind und enthält alles darunter, auch
// aus tieferen Unterordnern. Dateien, die direkt im gewählten Ordner liegen, bilden eine eigene Gruppe davor.
// Ein Klick auf den Namen geht in diesen Ordner, dort gilt dieselbe Regel wieder eine Ebene tiefer.
// Die Basis, unter der gruppiert wird: der gewählte Ordner; ohne Wahl und mit genau einer Wurzel diese Wurzel (sie als einzige
// Gruppe zu zeigen trennte nichts, es sähe aus, als gruppierte nichts); mit mehreren Wurzeln die Ebene darüber, also die Wurzeln.
const gewaehlterPfad = () => (zustand.ordner ? zustand.ordner.split("/").filter(Boolean)
  : zustand.wurzelNamen.size === 1 ? [[...zustand.wurzelNamen.keys()][0]] : []);
const basisId = () => gewaehlterPfad().join("/");

function ordnerSchluessel(m) {
  const teile = (m.ordner[0] || "").split("/").filter(Boolean);
  const wahl = gewaehlterPfad();
  return teile.slice(0, wahl.length + 1).join("/");     // Wahl + eine Ebene; liegt die Datei direkt in der Wahl, ist es die Wahl selbst
}

function ordnerBeschriftung(key) {
  const teile = key.split("/").filter(Boolean);
  const name = teile.length > 1 ? teile[teile.length - 1] : wurzelName(teile[0]);
  return key === basisId() ? `Direkt in ${name}` : name;
}

function ordnerVergleich(a, b) {
  return ((b === basisId()) - (a === basisId())) || natuerlich(ordnerBeschriftung(a), ordnerBeschriftung(b));
}

const reihenfolge = (liste) => (a, b) => (liste.indexOf(a) - liste.indexOf(b)) || natuerlich(a, b);
const zeitraum = (iso) => {
  if (!iso) return "ohne";
  const tage = (Date.now() - new Date(iso).getTime()) / 86400000;
  return tage < 1 ? "heute" : tage < 7 ? "woche" : tage < 31 ? "monat" : "aelter";
};
const ZEITRAUM = { heute: "Heute", woche: "Diese Woche", monat: "Diesen Monat", aelter: "Älter", ohne: "Ohne Datum" };
const STATUS = { offen: "Noch nicht gedruckt", gedruckt: "Gedruckt", fehlt: "Datei fehlt", unlesbar: "Unlesbar" };

const GRUPPEN = {
  ordner: { schluessel: ordnerSchluessel, beschriftung: ordnerBeschriftung, vergleich: ordnerVergleich },
  format: { schluessel: (m) => m.format || "", beschriftung: (k) => (endung[k] || k).replace(".", "").toUpperCase(),
            vergleich: reihenfolge(["3mf", "stl", "obj", "step", "fcstd"]) },
  material: { schluessel: (m) => m.material || "", beschriftung: (k) => k || "Ohne Material",
              vergleich: (a, b) => (!a) - (!b) || natuerlich(a, b) },
  status: { schluessel: (m) => (m.fehlt ? "fehlt" : m.fehler ? "unlesbar" : m.drucke_n || m.gedruckt ? "gedruckt" : "offen"),
            beschriftung: (k) => STATUS[k], vergleich: reihenfolge(["offen", "gedruckt", "fehlt", "unlesbar"]) },
  angelegt: { schluessel: (m) => zeitraum(m.angelegt), beschriftung: (k) => ZEITRAUM[k],
              vergleich: reihenfolge(["heute", "woche", "monat", "aelter", "ohne"]) },
};

function gruppiere(liste) {
  const art = GRUPPEN[zustand.gruppierung];
  if (!art) return { liste, gruppen: [] };
  const je = new Map();
  for (const m of liste) {
    const k = art.schluessel(m);
    if (!je.has(k)) je.set(k, []);
    je.get(k).push(m);
  }
  const gruppen = [], aus = [];
  for (const k of [...je.keys()].sort(art.vergleich)) {
    const l = je.get(k);
    gruppen.push({ key: k, label: art.beschriftung(k), start: aus.length, n: l.length });
    aus.push(...l);
  }
  return { liste: aus, gruppen };
}

function gruppenKopf(g, y) {
  const zu = zustand.eingeklappt.has(g.key);
  const ids = zustand.modelle.slice(g.start, g.start + g.n).map((m) => m.id);
  const alle = ids.length > 0 && ids.every((id) => zustand.auswahl.has(id));
  const ordnerSprung = zustand.gruppierung === "ordner" && g.key !== basisId();
  return `<div class="gruppe ${zu ? "zu" : ""}" data-id="g:${esc(g.key)}" data-gruppe="${esc(g.key)}" style="top:${y}px" title="${zu ? "Aufklappen" : "Zuklappen"}">
    <span class="g-pfeil">${zu ? "▸" : "▾"}</span>
    <input type="checkbox" data-gruppe-wahl="${esc(g.key)}" ${alle ? "checked" : ""} title="Alle in dieser Gruppe auswählen">
    ${ordnerSprung ? `<span class="g-name g-ordner" data-gruppe-ordner="${esc(g.key)}" title="In diesen Ordner wechseln">${esc(g.label)}</span>`
      : `<span class="g-name">${esc(g.label)}</span>`}<em>${g.n}</em></div>`;
}

async function ladeModelle() {
  // Aufräumen ist keine Kachelliste, sondern eine eigene Fläche (aufraeumen.js).
  if (typeof zeigeAufraeumen === "function") {
    zeigeAufraeumen(zustand.ansicht === "aufraeumen");
    if (zustand.ansicht === "aufraeumen") return ladeAufraeumen();
  }
  const p = new URLSearchParams({ ...filterJetzt(), leiste: 1 });
  // Nur die Antwort auf die neueste Anfrage zählt. Bei 9 000 Modellen dauert eine Liste Sekunden; kam eine ältere nach einer neueren an,
  // zeigte sie einen anderen Stand (etwa die Kacheln eines anderen Ordners) als den, den die Oberfläche zu zeigen glaubte.
  const nr = ladeModelle.nr = (ladeModelle.nr || 0) + 1;
  ladeModelle.unterwegs = (ladeModelle.unterwegs || 0) + 1;
  let antwort;
  try { antwort = await api("/api/modelle?" + p); }
  finally {
    // Ein Nachladen aus einer Live-Meldung, das gewartet hat, kommt erst nach dem Zeichnen dieser Antwort dran (sonst verwürfe es sie).
    if (!--ladeModelle.unterwegs && ladeModelle.danach) { setTimeout(ladeModelle.danach, 0); ladeModelle.danach = null; }
  }
  const { modelle: liste, leiste } = antwort;
  if (nr !== ladeModelle.nr) return;
  sortiere(liste, false);
  zustand.roh = liste;
  zustand.leisteDaten = leiste;
  listeAnwenden();
}

// Was die Liste gerade zeigt — für /api/modelle und für das Nachreichen einzelner Modelle (dieselben Felder).
const filterJetzt = () => ({ q: zustand.suche, ordner: zustand.ordner, format: zustand.format, ansicht: zustand.ansicht,
                             sammlung: zustand.sammlung, tags: [...zustand.tags].join(","), material: [...zustand.material].join(",") });

// Die Sortierung, die der Server nicht macht. `nachgereicht`: neue Modelle kamen hinten dazu — dann auch nach Name wie der Server
// (ausser bei Suche und Chips: dort ordnet der Server nach Treffern, die neuen bleiben hinten).
function sortiere(liste, nachgereicht) {
  const s = (zustand.sammlung || zustand.ansicht === "warteschlange") ? "eigene" : zustand.sortierung;
  const name = (x) => (x.name || "").toLowerCase();
  if (s === "neu") liste.sort((a, b) => (b.angelegt || "").localeCompare(a.angelegt || ""));
  else if (s === "gewicht") liste.sort((a, b) => (b.gewicht_g || 0) - (a.gewicht_g || 0));
  else if (s === "groesse") liste.sort((a, b) => Math.max(...(b.masse || [0])) - Math.max(...(a.masse || [0])));
  else if (nachgereicht && s === "name" && !zustand.suche && !zustand.tags.size && !zustand.material.size)
    liste.sort((a, b) => (name(a) < name(b) ? -1 : name(a) > name(b) ? 1 : 0));
}

// zustand.roh (sortiert, mit Entwürfen) → was das Raster zeigt.
function listeAnwenden() {
  const liste = zustand.roh;
  // Entwürfe ausblenden: gemerkt; die Leiste sagt, wie viele fehlen, damit niemand ein Modell vermisst.
  zustand.entwuerfeN = liste.filter((m) => m.entwurf).length;
  const sichtbar = zustand.ohneEntwuerfe && zustand.ansicht !== "papierkorb" ? liste.filter((m) => !m.entwurf) : liste;
  const g = gruppiere(sichtbar);
  zustand.modelle = g.liste;
  zustand.gruppen = g.gruppen;
  zustand.idIndex = new Map(g.liste.map((x, i) => [x?.id, i]));
  zeichneLeiste(zustand.leisteDaten);
  zeichneFilterzeile();
  zeichneStapel();
  zeichneListenkopf();
  raster.neu();
  if (zustand.baugruppe) zeigeBaugruppeFlaeche(true);
}

async function ladeSeite() {
  const nr = ladeSeite.nr = (ladeSeite.nr || 0) + 1;     // wie bei ladeModelle: nur die neueste Antwort zählt
  const [z, ordner, tags, sammlungen, ws, entfernt] = await Promise.all([api("/api/zaehler"), api("/api/ordner"), api("/api/tags"),
                                                              api("/api/sammlungen"), api("/api/warteschlange"),
                                                              api("/api/wurzeln/entfernt").catch(() => [])]);   // ein älterer Server kennt den Endpunkt nicht: die Seite muss trotzdem aufgehen
  if (nr !== ladeSeite.nr) return;
  zustand.entfernteWurzeln = entfernt;
  // Der Willkommensschirm gehört in einen wirklich leeren Katalog. Sind alle Ordner entfernt, die Modelle aber noch da (als „Datei fehlt“),
  // wäre er falsch: er versteckt Bereinigen und lässt aussehen, als sei alles weg.
  zustand.katalogLeer = !((z.alle || 0) + (z.papierkorb || 0) + entfernt.length);
  zustand.sammlungen = sammlungen;
  abgleichen($("#sammlungen"), sammlungen.map((x) =>
    `<button class="eintrag ${zustand.sammlung === x.id ? "aktiv" : ""}" data-sammlung="${esc(x.id)}"><span>${esc(x.name)}</span><em>${x.anzahl}</em></button>`).join("")
    || `<button class="eintrag leer-eintrag" id="sammlung-neu-2">＋ Neue Sammlung</button>`);
  abgleichen($("#ws-liste"), ws.map((m, i) =>
    `<li draggable="true" data-ws="${esc(m.id)}" data-ws-waehle="${esc(m.id)}"><b>${i + 1}</b><span title="${esc(m.name)}">${esc(m.name)}${esc(endung[m.format] || "")}</span><button data-ws-weg="${esc(m.id)}" title="aus der Warteschlange">×</button></li>`).join(""));
  for (const k of ["alle", "neu", "favoriten", "duplikate", "fehlt", "unlesbar", "papierkorb", "warteschlange"]) {
    const el = $("#z-" + k);
    if (el) el.textContent = z[k] || "";
  }
  // Zählabzeichen am Besen: nur, wenn etwas zu tun ist (der Papierkorb zählt nicht).
  const zu = (z.duplikate || 0) + (z.fehlt || 0) + (z.unlesbar || 0);
  const abz = $("#abz-bereinigen");
  abz.hidden = !zu;
  abz.textContent = zu > 99 ? "99+" : zu;
  zustand.formate = z.formate;
  if (zustand.leiste) zeichneLeiste(zustand.leiste);
  // Zwei Wurzeln gleichen Namens (etwa „3D-Druck“ auf zwei Laufwerken): der übergeordnete Ordner unterscheidet sie.
  const namen = ordner.map((w) => w.name);
  zustand.doppelteWurzeln = new Set(namen.filter((n, i) => namen.indexOf(n) !== i));
  zustand.wurzelNamen = new Map(ordner.map((w) => [w.id, zustand.doppelteWurzeln.has(w.name)
    ? `${w.name} · ${(w.pfad || "").split(/[\\/]/).filter(Boolean).slice(-2, -1)[0] || ""}` : w.name]));
  zeichnePfad();
  if (zustand.gruppierung === "ordner") {      // die Wurzeln sind jetzt bekannt: die Basis kann sich geändert haben
    if (zustand.roh) listeAnwenden();
  }
  abgleichen($("#ordner"), `<div class="baum">${ordner.map((w) => zweig(w, 0)).join("")}</div>`);
  zustand.hatWurzeln = ordner.length > 0;
  zeichneLeer();
  zeichneHinweisLeiste();
  abgleichen($("#tag-liste"), tags.slice(0, 30).map((t) =>
    `<button class="eintrag ${zustand.tags.has(t.name) ? "aktiv" : ""}" data-tag="${esc(t.name)}"><span>#${esc(t.name)}</span><em>${t.anzahl}</em></button>`).join(""));
  markiereAnsicht();
}

function zweig(k, tiefe) {
  const hatKinder = k.kinder.length > 0;
  const offen = zustand.offen.has(k.id);
  const aktiv = zustand.ordner === k.id ? "aktiv" : "";
  const ort = tiefe === 0 && zustand.doppelteWurzeln?.has(k.name)
    ? `<small class="wz-ort">${esc((k.pfad || "").split(/[\\/]/).filter(Boolean).slice(-2, -1)[0] || (k.pfad || ""))}</small>` : "";
  let html = `<button class="eintrag ${aktiv}" style="--tiefe:${tiefe}" data-ordner="${esc(k.id)}" ${tiefe === 0 ? `data-wurzel="${esc(k.id)}" data-wurzel-name="${esc(k.name)}"` : ""} title="${esc(k.pfad || k.name)}">
    <span><span class="pfeil" data-klappe="${esc(k.id)}">${hatKinder ? (offen ? "▾" : "▸") : ""}</span>${esc(k.name)}${ort}</span><em>${k.anzahl}</em></button>`;
  if (hatKinder && offen) html += k.kinder.map((c) => zweig(c, tiefe + 1)).join("");
  return html;
}

// Die Seitenleiste wechselt als Ganzes (wie bei VS Code): Katalog oder Bereinigen.
const BEREINIGEN = ["aufraeumen", "papierkorb", "duplikate", "fehlt", "unlesbar"];

function markiereAnsicht() {
  const bereinigt = BEREINIGEN.includes(zustand.ansicht);
  $(".seite").dataset.modus = bereinigt ? "bereinigen" : "katalog";
  const hat = { ordner: !!zustand.ordner, baugruppen: !!zustand.baugruppe, sammlungen: !!zustand.sammlung, tags: zustand.tags.size > 0 };
  document.querySelectorAll(".sektion").forEach((s) => s.classList.toggle("hat-wahl", !!hat[s.dataset.sektion]));
  document.querySelectorAll("[data-ansicht]").forEach((b) =>
    b.classList.toggle("aktiv", b.dataset.ansicht === zustand.ansicht && !zustand.ordner && !zustand.tags.size && !zustand.material.size && !zustand.format && !zustand.sammlung));
  document.querySelectorAll(".rail-btn[data-rail]").forEach((b) =>
    b.classList.toggle("aktiv", (b.dataset.rail === "bereinigen") === bereinigt));
}

// Die Leiste über dem Raster: Material und Format als Chips (wenige Werte, die
// wirklich filtern). Tags stehen in der Seitenleiste und in der Suche; hier
// erscheinen nur die gewählten, zum Wegnehmen. Material mit ODER; gezählt
// wird vor der Chip-Auswahl (Server), gewählte Chips bleiben sichtbar, auch
// wenn sie unter die ersten acht fallen.
function zeichneLeiste(l) {
  zustand.leiste = l;
  const chip = (art, aktiv, name, text, n) => `<button class="chip ${aktiv ? "aktiv" : ""}" data-${art}="${esc(name)}">${text}${n != null ? `<em>${n}</em>` : ""}</button>`;
  const auswahl = (liste, wahl, n) => [...liste.slice(0, n), ...liste.slice(n).filter((x) => wahl.has(x.name))];
  const mat = auswahl(l.materialien, zustand.material, 8).map((x) => chip("mat", zustand.material.has(x.name), x.name, esc(x.name), x.anzahl)).join("");
  const fmt = Object.entries(zustand.formate || {}).sort().map(([f, n]) => chip("format", zustand.format === f, f, esc((endung[f] || f).slice(1).toUpperCase()), n)).join("");
  const tags = [...zustand.tags].map((t) => `<button class="chip aktiv" data-tag="${esc(t)}" title="Filter entfernen">#${esc(t)} ×</button>`).join("");
  const leer = !zustand.tags.size && !zustand.material.size && !zustand.format;
  const entwuerfe = zustand.entwuerfeN || zustand.ohneEntwuerfe
    ? `<button class="chip ${zustand.ohneEntwuerfe ? "aktiv" : ""}" id="entwuerfe-aus" title="Als Entwurf markierte Modelle ausblenden">${zustand.ohneEntwuerfe
      ? `${zustand.entwuerfeN || 0} ${zustand.entwuerfeN === 1 ? "Entwurf" : "Entwürfe"} ausgeblendet ×` : `Entwürfe ausblenden<em>${zustand.entwuerfeN}</em>`}</button>` : "";
  abgleichen($("#tagleiste"), `<button class="chip ${leer ? "aktiv" : ""}" data-tag="">Alle</button>`
    + (mat ? `<span class="leiste-titel">MATERIAL</span>${mat}` : "")
    + (fmt ? `<span class="leiste-titel">FORMAT</span>${fmt}` : "")
    + (tags ? `<span class="leiste-titel">TAGS</span>${tags}` : "")
    + (entwuerfe ? `<span class="leiste-luecke"></span>${entwuerfe}` : ""));
}

// Der Weg zum gewählten Ordner, dezent über der Liste: „Alle › 3D-Druck › Technik“. Jeder Teil führt dorthin zurück.
function zeichnePfad() {
  const el = $("#pfad");
  const teile = zustand.ordner ? zustand.ordner.split("/").filter(Boolean) : [];
  el.hidden = !teile.length || !!zustand.baugruppe;
  const glieder = [`<button data-pfad="">Alle</button>`, ...teile.map((t, i) => {
    const name = i === 0 ? wurzelName(t) : t;
    return i === teile.length - 1 ? `<span class="pfad-jetzt">${esc(name)}</span>`
      : `<button data-pfad="${esc(teile.slice(0, i + 1).join("/"))}">${esc(name)}</button>`;
  })];
  abgleichen(el, glieder.join('<i>›</i>'));
}

function zeichneFilterzeile() {
  const teile = [];
  const sammlung = zustand.sammlungen.find((x) => x.id === zustand.sammlung);
  if (sammlung) teile.push(`Sammlung <b>${esc(sammlung.name)}</b> <button id="sammlung-umbenennen">umbenennen</button> <button id="sammlung-loeschen">löschen</button> <button id="sammlung-zu-baugruppe">🧩 als Baugruppe</button> <span class="dim">· Reihenfolge per Ziehen</span>`);
  if (zustand.ansicht === "warteschlange") teile.push(`Warteschlange <span class="dim">· Reihenfolge per Ziehen</span>`);
  const chips = [...zustand.material, ...[...zustand.tags].map((t) => "#" + t)];
  if (chips.length) teile.push(`${chips.map(esc).join(" oder ")} <span class="dim">· wer mehr trifft, steht oben</span>`);
  if (zustand.format) teile.push(esc(endung[zustand.format] || zustand.format));
  if (zustand.suche) teile.push(`„${esc(zustand.suche)}“`);
  const z = $("#filterzeile");
  z.hidden = teile.length === 0;
  abgleichen(z, teile.join(" · ") + ` <button id="filter-weg">✕ Filter aufheben</button>`);
  zustand.filterTeile = teile.length + (zustand.ordner ? 1 : 0);
  zeichnePfad();
  zeichneLeer();
}

// Wenn nichts zu sehen ist, sagen warum — und beim ersten Start an die Hand
// nehmen: ein Ordner, ein Klick, dann sieht man das Einlesen laufen.
function zeichneLeer() {
  const leer = $("#leer");
  const erst = zustand.hatWurzeln === false && zustand.katalogLeer !== false;
  document.body.classList.toggle("erststart", erst);
  leer.hidden = zustand.modelle.length > 0 || zustand.ansicht === "aufraeumen";      // Aufräumen hat seine eigene Fläche
  if (leer.hidden) return;
  const scan = zustand.scan;
  if (erst) {
    leer.innerHTML = `<div class="willkommen">
      <h2>Willkommen bei partAtlas</h2>
      <p>Wähle den Ordner mit deinen 3D-Dateien. partAtlas liest ihn samt Unterordnern ein und
        katalogisiert die Dateien dort, wo sie liegen — nichts wird kopiert oder verschoben.</p>
      <ul>
        <li><b>Formate:</b> 3MF (inkl. Slicer-Metadaten und Thumbnail), STL, OBJ, STEP (Vorschau und Maße über FreeCAD, wenn installiert) und FCStd (Vorschau nur aus der Datei)</li>
        <li><b>Verschieben/Umbenennen</b> im Dateimanager bleibt erkannt — Tags und Verknüpfungen hängen am Inhalt, nicht am Pfad</li>
        <li><b>Weitere Ordner</b> jederzeit über Importieren → Ordner hinzufügen</li>
      </ul>
      <button class="knopf akzent gross" id="wurzel-neu-3">📁 Wurzelordner wählen …</button></div>`;
  } else if (scan && scan.laeuft && zustand.ansicht === "alle" && !zustand.filterTeile) {
    leer.innerHTML = `<div class="willkommen"><h2>Scan läuft</h2>
      <p>${scan.gefunden ? `${scan.gefunden.toLocaleString("de-DE")} Dateien gefunden · ` : ""}Phase: ${esc(scan.phase || "Start")}${scan.zu_analysieren ? ` ${scan.analysiert || 0}/${scan.zu_analysieren}` : ""}.
        Modelle erscheinen gruppenweise (je 100); Vorschauen werden anschliessend gerendert.</p>
      <div class="lauf"><i></i></div></div>`;
  } else {
    leer.textContent = zustand.ansicht === "papierkorb" ? "Der Papierkorb ist leer."
      : (zustand.filterTeile ? "Keine Treffer." : "Noch keine Modelle in diesem Ordner.");
  }
}

// Wie lange das Einlesen gedauert hat, stehen lassen: wer einen grossen Bestand prüft, will die Zahl ablesen können.
const PHASENNAME = { suchen: "Suchen", hashen: "Hashen", analysieren: "Analysieren", vorschau: "Vorschauen", cad: "STEP (FreeCAD)" };
function scanErgebnis(m) {
  if (m.phase === "fehler") return `Einlesen gescheitert: ${m.abbruch || "unbekannter Fehler"}`;
  if (m.dauer_s == null || (!m.gefunden && !m.abgebrochen && !m.nur_cad)) return "";
  const zeit = m.dauer_s < 1 ? "unter 1 s" : m.dauer_s < 60 ? `${zahl(m.dauer_s, 1)} s` : dauer(m.dauer_s);
  // Nach einem Abbruch keine „Eingelesen“-Zeile: es ist nicht alles eingelesen.
  if (m.abgebrochen) return `Abgebrochen nach ${zeit}, ${(m.bearbeitet || 0).toLocaleString("de-DE")} Dateien`;
  if (m.nur_cad) return `Im Hintergrund fertig: ${(m.bearbeitet || 0).toLocaleString("de-DE")} Dateien in ${zeit}`;
  // Phasen unter einer halben Sekunde sind Rauschen
  const phasen = Object.entries(m.phasen || {}).filter(([, s]) => s >= 0.5)
    .map(([k, s]) => `${PHASENNAME[k] || k} ${s < 60 ? zahl(s, 1) + " s" : dauer(s)}`).join(" · ");
  const weg = m.nicht_erreichbar?.length ? `; nicht erreichbar: ${m.nicht_erreichbar.join(", ")} (nichts als fehlend markiert)` : "";
  const korb = weg + (m.zurueckgeholt ? `; ${m.zurueckgeholt.toLocaleString("de-DE")} aus dem Papierkorb zurückgeholt` : "")
    + (m.im_papierkorb ? `; ${m.im_papierkorb.toLocaleString("de-DE")} im Papierkorb (aus dem Katalog entfernt) übergangen` : "");
  return `Eingelesen: ${m.gefunden.toLocaleString("de-DE")} Dateien${m.neu ? `, ${m.neu.toLocaleString("de-DE")} neu` : ""}${korb} in ${zeit}${phasen ? ` (${phasen})` : ""}`;
}

// ---------------------------------------------------------------- Virtuelles Raster und Liste
//
// Beide Ansichten zeichnen nur, was sichtbar ist. Die Liste ist dasselbe
// Raster mit einer Spalte und niedrigen Zeilen.

const raster = (() => {
  const RAND = 13;   // = --s4
  const KOPF = 34;   // = --s6, das Gruppenband
  const aussen = $("#raster"), innen = $("#raster-innen");
  let spalten = 1, geplant = false;
  let zeilen = [];   // { y, h, kopf: Gruppe } oder { y, h, von, bis } (Indizes in zustand.modelle)
  const mass = () => zustand.layout === "liste" ? { B: 0, H: 34, LUECKE: 0, RAND: 0 }
    : zustand.layout === "karten" ? { B: 0, H: 115, LUECKE: 0, RAND: 0 } : { B: 144, H: 233, LUECKE: 13, RAND };

  // Alle Zeilen mit Höhe und Lage einmal ausrechnen: Bänder und Zeilen, eingeklappte Gruppen ohne Zeilen.
  function neu() {
    const { B, H, LUECKE, RAND: R } = mass();
    spalten = zustand.layout !== "raster" ? 1 : Math.max(1, Math.floor((aussen.clientWidth - R * 2 + LUECKE) / (B + LUECKE)));
    const gruppen = zustand.gruppen.length > 1 ? zustand.gruppen : [{ start: 0, n: zustand.modelle.length, ohneKopf: true }];
    const raster_ = zustand.layout === "raster";
    zeilen = [];
    let y = R;
    for (const g of gruppen) {
      if (!g.ohneKopf) { zeilen.push({ y, h: KOPF, kopf: g }); y += KOPF + (raster_ ? 8 : 0); }
      if (!g.ohneKopf && zustand.eingeklappt.has(g.key)) { y += raster_ ? 13 : 0; continue; }
      for (let i = g.start; i < g.start + g.n; i += spalten) {
        zeilen.push({ y, h: H, von: i, bis: Math.min(i + spalten, g.start + g.n) });
        y += H + LUECKE;
      }
      if (!g.ohneKopf && raster_) y += 8;      // 13 Lücke + 8 = 21 zwischen Gruppen
    }
    innen.style.height = `${y + R}px`;
    $("#listenkopf").hidden = zustand.layout !== "liste" || !!zustand.baugruppe;
    bereich = "";
    zeichne();
  }

  // Beim Scrollen ändert sich der Zeilenbereich nur alle paar Bilder; dazwischen
  // nichts neu bauen. Alle anderen Aufrufer (Auswahl, Herz, Nachladen) zeichnen immer.
  let bereich = "";
  function zeichne(nurBeiNeuemBereich) {
    geplant = false;
    const { B, H, LUECKE, RAND: R } = mass();
    const rand = 2 * (H + LUECKE);
    const von = Math.max(0, suche(aussen.scrollTop - rand));
    let bis = von;
    const unten = aussen.scrollTop + aussen.clientHeight + rand;
    while (bis < zeilen.length && zeilen[bis].y < unten) bis++;
    if (nurBeiNeuemBereich === true && bereich === `${von}-${bis}`) return;
    bereich = `${von}-${bis}`;
    const html = [];
    for (let z = von; z < bis; z++) {
      const r = zeilen[z];
      if (r.kopf) { html.push(gruppenKopf(r.kopf, r.y)); continue; }
      for (let i = r.von; i < r.bis; i++) {
        const m = zustand.modelle[i];
        html.push(zustand.layout === "liste" ? zeileL(m, r.y) : zustand.layout === "karten" ? zeileK(m, r.y) : karte(m, R + (i - r.von) * (B + LUECKE), r.y));
      }
    }
    abgleichen(innen, html.join(""));
  }

  // Die erste Zeile, die bei Höhe `y` noch ins Bild ragt (Zeilen sind nach y geordnet).
  function suche(y) {
    let lo = 0, hi = zeilen.length;
    while (lo < hi) {
      const mitte = (lo + hi) >> 1;
      if (zeilen[mitte].y + zeilen[mitte].h < y) lo = mitte + 1; else hi = mitte;
    }
    return lo;
  }

  // Ein Sprung von mehr als einem Bildschirm je Meldung ist kein Lesen mehr, sondern Suchen.
  let letzteLage = 0, ruhe = 0;
  aussen.addEventListener("scroll", () => {
    if (Math.abs(aussen.scrollTop - letzteLage) > aussen.clientHeight) schnellScrollen = true;
    letzteLage = aussen.scrollTop;
    if (schnellScrollen) {
      clearTimeout(ruhe);
      ruhe = setTimeout(() => { schnellScrollen = false; zeichne(); }, 120);
    }
    if (!geplant) { geplant = true; requestAnimationFrame(() => zeichne(true)); }
  });
  window.addEventListener("resize", () => requestAnimationFrame(neu));

  // Ohne Argument: welches Modell gerade oben im Bild steht und wie weit unter dem oberen Rand. Mit: wieder dorthin scrollen.
  // Ganz oben gibt es keinen Anker — dort sollen neue Modelle oben sichtbar dazukommen.
  function anker(a) {
    if (a === undefined) {
      if (aussen.scrollTop <= 0) return null;
      const z = zeilen[suche(aussen.scrollTop)];
      const m = z && zustand.modelle[z.kopf ? z.kopf.start : z.von];
      return m ? { id: m.id, abstand: z.y - aussen.scrollTop } : null;
    }
    const i = a && zustand.idIndex.get(a.id);
    if (i == null) return;
    const z = zeilen.find((r) => !r.kopf && i >= r.von && i < r.bis);
    if (z) { aussen.scrollTop = z.y - a.abstand; zeichne(); }
  }
  return { neu, zeichne, anker };
})();

// Beim schnellen Ziehen an der Scrollleiste fliegen dutzende Kacheln an den Augen
// vorbei; ihre Bilder gar nicht erst anfordern. Erst wenn es ruhig wird, kommen sie.
let schnellScrollen = false;
const bildTag = (url) => (schnellScrollen ? '<img alt="">' : `<img loading="lazy" src="${url}" alt="">`);

// Kacheln und Zeilen laden die kleine Fassung (?t=1); Inspektor und Galerie das Original.
function bildUrl(m) {
  if (m.bild) return `/api/modelle/${m.id}/bild?t=1&v=${m.bild}`;
  if (m.vorschau_art && m.hash) return `/api/vorschau/${m.hash}.${m.vorschau_art}.png?t=1`;
  return m.hash && ["eingebettet", "gerendert"].includes(m.vorschau) ? `/api/vorschau/${m.hash}.png?t=1` : null;
}

function statusBadge(m) {
  // Ruhig: ein Haken, bei mehreren Drucken mit Zahl. Gewicht und Material stehen im Inspektor.
  return m.ohne_datei ? `<span class="badge ohne" title="Ohne Datei behalten">ohne Datei</span>`
    : m.fehlt ? `<span class="badge warn">⚠ Datei fehlt</span>`
    : m.fehler ? `<span class="badge warn">unlesbar</span>`
    : m.drucke_n ? `<span class="badge gedruckt" title="${m.drucke_n}× gedruckt">✓${m.drucke_n > 1 ? " " + m.drucke_n + "×" : ""}</span>` : "";
}

function karte(m, x, y) {
  const url = bildUrl(m);
  const platz = m.vorschau === "ausstehend" ? "Vorschau wird gerendert …" : (nurCad(m) ? nurCadText(m) : "keine Vorschau");
  const markiert = zustand.auswahl.has(m.id);
  return `<div class="karte ${zustand.gewaehlt === m.id ? "gewaehlt" : ""} ${markiert ? "markiert" : ""} ${zustand.auswahl.size ? "mit-auswahl" : ""} ${m.fehlt && !m.ohne_datei ? "fehlt" : ""}" draggable="true" style="left:${x}px;top:${y}px" data-id="${esc(m.id)}" data-f="${esc(m.format || "")}">
    <div class="bild">${url ? bildTag(url) : `<div class="platzhalter">${platz}</div>`}
      ${istNeu(m) ? '<span class="neu-punkt" title="Neu hinzugefügt"></span>' : ""}
      <input type="checkbox" class="wahl" data-wahl="${esc(m.id)}" ${markiert ? "checked" : ""} title="auswählen">
      ${zustand.ansicht === "papierkorb" ? "" : `<button class="herz ${m.favorit ? "an" : ""}" data-herz="${esc(m.id)}" title="Favorit">♥</button>`}
      ${m.entwurf ? `<span class="badge entwurf" title="Als Entwurf markiert">Entwurf</span>` : ""}
      ${m.fehlt && !m.ohne_datei ? `<div class="fehlt-band" title="Die Datei liegt an keinem bekannten Ort mehr. Tags, Bilder und Verknüpfungen sind noch da — legt man sie zurück, ist alles wieder verbunden.">⚠ Datei fehlt</div>` : statusBadge(m)}</div>
    <div class="text"><div class="name" title="${esc(m.name)}">${esc(m.name)}<span class="endung">${esc(endung[m.format] || "")}</span></div>
      <div class="masse">${m.masse ? m.masse.map((v) => zahl(v, v < 10 ? 1 : 0)).join(" × ") + " mm" : "&nbsp;"}</div>
      <div class="tags">${m.gewicht_g ? `${zahl(m.gewicht_g, 1)} g` : "&nbsp;"}</div></div></div>`;
}

// Karten: wie eine Liste, aber höher — rechts neben dem Bild ist Platz für mehr vom Modell.
function zeileK(m, y) {
  const url = bildUrl(m);
  const markiert = zustand.auswahl.has(m.id);
  const ordner = (m.ordner[0] || "").split("/").slice(1).join("/");
  const status = m.ohne_datei ? "ohne Datei" : m.fehlt ? "⚠ Datei fehlt" : m.fehler ? "unlesbar" : m.drucke_n ? `✓ ${m.drucke_n}× gedruckt` : (m.warteschlange != null && PHASE >= 2 ? "☰ Warteschlange" : "");
  const fakten = [masse(m.masse), m.gewicht_g ? zahl(m.gewicht_g, 1) + " g" : "", m.groesse ? zahl(m.groesse / 1024, 0) + " KB" : ""].filter(Boolean).join(" · ");
  const chips = [...(m.materialien || []).map((x) => `<span class="chip-k mat">${esc(x)}</span>`), ...m.tags.map((t) => `<span class="chip-k">#${esc(t)}</span>`)].join("");
  return `<div class="zeile-k ${zustand.gewaehlt === m.id || markiert ? "gewaehlt" : ""} ${m.fehlt && !m.ohne_datei ? "fehlt" : ""}" draggable="true" style="top:${y}px" data-id="${esc(m.id)}" data-f="${esc(m.format || "")}">
    <input type="checkbox" class="wahl-l" data-wahl="${esc(m.id)}" ${markiert ? "checked" : ""} title="auswählen">
    <div class="k-bild">${url ? bildTag(url) : `<div class="mini">${m.format === "step" ? "STEP" : m.format === "fcstd" ? "FCStd" : ""}</div>`}</div>
    <div class="k-text">
      <div class="k-name" title="${esc(m.name)}">${m.favorit ? "♥ " : ""}${esc(m.name)}<span class="endung">${esc(endung[m.format] || "")}</span>${m.entwurf ? ' <small class="entwurf-zeichen">Entwurf</small>' : ""}</div>
      <div class="k-fakten">${esc(fakten)}${status ? `<span class="k-status">${status}</span>` : ""}</div>
      <div class="k-chips">${chips}</div>
      <div class="k-ordner" title="${esc(ordner)}">${ordner ? "▸ " + esc(ordner) : ""}</div>
    </div>${hoverAktionen(m)}</div>`;
}

// Die Liste ist die schlanke Tabelle zum Sortieren; Tags, Ordner und Material zeigen die Karten.
const LISTENSPALTEN = [["", ""], ["", ""], ["NAME", "name"], ["FORMAT", ""], ["GRÖSSE", "groesse"], ["GEWICHT", "gewicht"],
                       ["STATUS", ""], ["", ""]];

function zeileL(m, y) {
  const url = bildUrl(m);
  const markiert = zustand.auswahl.has(m.id);
  const status = m.ohne_datei ? "ohne Datei" : m.fehlt ? "⚠ fehlt" : m.fehler ? "unlesbar" : m.drucke_n ? `✓ ${m.drucke_n}× gedruckt` : (m.warteschlange != null && PHASE >= 2 ? "☰ Warteschlange" : "");
  return `<div class="zeile-l ${zustand.gewaehlt === m.id || markiert ? "gewaehlt" : ""} ${m.fehlt && !m.ohne_datei ? "fehlt" : ""}" draggable="true" style="top:${y}px" data-id="${esc(m.id)}" data-f="${esc(m.format || "")}">
    <span>${url ? bildTag(url) : '<div class="mini"></div>'}</span>
    <span><input type="checkbox" class="wahl-l" data-wahl="${esc(m.id)}" ${markiert ? "checked" : ""}></span>
    <span title="${esc(m.name)}">${m.favorit ? "♥ " : ""}${esc(m.name)}${m.entwurf ? ' <small class="entwurf-zeichen">Entwurf</small>' : ""}</span>
    <span class="mono">${esc(endung[m.format] || "")}</span>
    <span class="mono">${esc(masse(m.masse))}</span>
    <span class="mono">${m.gewicht_g ? zahl(m.gewicht_g, 1) + " g" : ""}</span>
    <span class="mono">${status}</span>${hoverAktionen(m)}</div>`;
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
  // Dezent unten: wie viele Modelle die Liste zeigt, und wie viele davon gewählt sind.
  $("#anzahl").textContent = `${zustand.modelle.length.toLocaleString("de-DE")} Modelle${n ? ` · ${n} ausgewählt` : ""}`;
  zeichneHinweisLeiste();
  const st = $("#stapel");
  st.hidden = n === 0;
  if (!n) return;
  abgleichen(st, zustand.ansicht === "papierkorb"
    ? `<div class="st-kopf"><b>${n} ausgewählt</b>
        <button class="link" data-stapel="alle">Alle ${anzahl(zustand.modelle.length)} auswählen</button>
        <button class="st-zu" data-stapel="keine" title="Auswahl aufheben (Esc)" aria-label="Auswahl aufheben">✕</button></div>
       <div class="st-aktionen"><div class="st-gruppe"><button class="knopf" data-stapel="wiederherstellen">↩ Wiederherstellen</button></div></div>`
    : `<div class="st-kopf"><b>${n} ausgewählt</b>
        <button class="link" data-stapel="alle">Alle ${anzahl(zustand.modelle.length)} auswählen</button>
        <button class="st-zu" data-stapel="keine" title="Auswahl aufheben (Esc)" aria-label="Auswahl aufheben">✕</button></div>
      <div class="st-aktionen">
        <div class="st-gruppe" role="group" aria-label="Zuordnen">
          <button class="knopf waehl" data-stapel="tag" aria-haspopup="listbox">＃ Tag</button>
          <button class="knopf waehl" data-stapel="material" aria-haspopup="listbox">◍ Material</button>
          <button class="knopf waehl" data-stapel="sammlung" aria-haspopup="listbox">▤ Sammlung</button>
          <button class="knopf waehl" data-stapel="baugruppe" aria-haspopup="listbox">🧩 Baugruppe</button>
        </div>
        <div class="st-gruppe" role="group" aria-label="Markieren">
          <button class="knopf" data-stapel="favorit" title="Als Favorit markieren">♥ Favorit</button>
          <button class="knopf" data-stapel="entwurf" title="Als Entwurf markieren — oder, wenn sie es schon sind, nicht mehr">✎ Entwurf</button>
          <button class="knopf" data-stapel="gedruckt" title="Als gedruckt markieren">✓ Gedruckt</button>
          <button class="knopf" data-ab-phase="2" data-stapel="warteschlange">☰ Warteschlange</button>
        </div>
        <div class="st-gruppe" role="group" aria-label="Dateien">
          <button class="knopf" data-stapel="verschieben">Verschieben …</button>
          <button class="knopf gefahr" data-stapel="loeschen">Löschen …</button>
        </div>
      </div>`);
}

// Datei fehlt: drei Wege, wie bei Manyfold „delete it, or find where it went“ — und dazu „behalten“, wenn sie absichtlich weg ist.
function fehltTeil(m) {
  const zuletzt = m.zuletzt ? `<div class="dim">Lag zuletzt in <code>${esc(m.zuletzt)}</code></div>` : "";
  const suchen = `<button class="knopf" id="datei-suchen">Suchen …</button>`;
  if (m.ohne_datei) {
    return `<div class="fehlt-teil ruhig"><p><b>Ohne Datei behalten.</b> Tags, Drucke und Bilder bleiben. Kommt die Datei zurück, ist sie
      wieder verbunden.</p>${zuletzt}<div class="knoepfe-zeile">${suchen}<button class="knopf" id="ohne-datei-aus">Wieder als fehlend zeigen</button></div></div>`;
  }
  return `<div class="fehlt-teil"><p><b>⚠ Datei fehlt.</b> Sie liegt an keinem bekannten Ort mehr: gelöscht, ausserhalb der Ordner von
    partAtlas verschoben oder auf einem Laufwerk, das gerade fehlt. Tags, Drucke und Bilder sind noch da.</p>${zuletzt}
    <div class="knoepfe-zeile">${suchen}<button class="knopf" id="ohne-datei">Ohne Datei behalten</button>
      <button class="knopf gefahr" id="fehlt-entfernen">Aus dem Katalog entfernen …</button></div></div>`;
}

// Einen Ordner zeigen; partAtlas prüft, ob fehlende Dateien darin liegen (gleicher Inhalt), auch die anderer Modelle.
async function dateiSuchen() {
  let w;
  try { w = await api("/api/wurzeln/waehlen", { method: "POST" }); } catch (e) { return toast(e.message); }
  if (w.abgebrochen) return;
  const pfad = w.keinDialog ? await ordnerWaehler() : w.pfad;
  if (!pfad) return;
  let r;
  try { r = await api("/api/fehlende/suchen", { method: "POST", body: { pfad } }); } catch (e) { return toast(e.message); }
  const n = r.treffer.length;
  if (!n) {
    return dialog(`<h2>Nicht gefunden</h2><p>In <code>${esc(r.pfad)}</code> liegt keine der fehlenden Dateien.</p>
      <p class="dim">Erkannt wird nur dieselbe Datei. Eine geänderte Fassung erkennt partAtlas nicht von selbst — sie kommt beim Einlesen als
      neues Modell.${r.vollstaendig ? "" : " Der Ordner ist sehr gross; durchsucht wurde nur ein Teil."}</p>
      <div class="knoepfe"><button class="knopf akzent" value="ok">OK</button></div>`);
  }
  const liste = `<ul>${r.treffer.slice(0, 8).map((t) => `<li>${esc(t.name)} <span class="dim">· ${esc(t.pfad)}</span></li>`).join("")}${n > 8 ? `<li>… und ${n - 8} weitere</li>` : ""}</ul>`;
  if (r.wurzel) return toast(`${n} ${n === 1 ? "Datei" : "Dateien"} gefunden — wird verbunden.`);
  const a = await dialog(`<h2>${n} ${n === 1 ? "fehlende Datei" : "fehlende Dateien"} gefunden</h2>${liste}
    <p>Der Ordner gehört noch nicht zum Katalog. Fügst du ihn hinzu, sind sie wieder verbunden, mit Tags, Drucken und Bildern.</p>
    <p class="dim">Alle anderen Modelle in diesem Ordner kommen dabei ebenfalls in den Katalog.</p>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Ordner hinzufügen</button></div>`);
  if (a !== "ja") return;
  try { einlesenGestartet((await api("/api/wurzeln", { method: "POST", body: { pfad: r.pfad } })).lauf); }
  catch (e) { toast(e.message); }
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

async function stapel(aktion, wert, modelle = [...zustand.auswahl]) {
  try {
    const r = await api("/api/stapel", { method: "POST", body: { aktion, modelle, wert } });
    if (r.fehler.length) toast(`${modelle.length - r.fehler.length} erledigt, ${r.fehler.length} nicht: ${r.fehler[0].fehler}`);
    else toast(`${modelle.length} erledigt.`);
  } catch (e) { toast(e.message); }
}

async function stapelAktion(aktion, modelle = [...zustand.auswahl], anker = null) {
  switch (aktion) {
    case "tag": case "material": case "sammlung": case "baugruppe": return zuordnenOeffnen(aktion, modelle, anker);
    case "alle": zustand.modelle.forEach((m) => zustand.auswahl.add(m.id)); zeichneStapel(); return raster.zeichne();
    case "keine": zustand.auswahl.clear(); zeichneStapel(); return raster.zeichne();
    case "warteschlange": return stapel("warteschlange", null, modelle);
    case "gedruckt": return stapel("gedruckt", true, modelle);
    case "favorit": return stapel("favorit", true, modelle);
    // Sind schon alle Entwurf, nimmt derselbe Knopf es zurück.
    case "entwurf": return stapel("entwurf", !modelle.every((x) => zustand.modelle.find((m) => m.id === x)?.entwurf), modelle);
    case "verschieben": {
      const ziel = await ordnerWahl(`${modelle.length} Modelle verschieben`, "Die Dateien werden auf der Platte verschoben. Nichts wird überschrieben.");
      if (ziel) { await stapel("verschieben", ziel, modelle); }
      return;
    }
    case "loeschen": return loeschenViele(modelle);
    case "wiederherstellen":
      for (const id of modelle) await api(`/api/modelle/${id}/wiederherstellen`, { method: "POST" }).catch((e) => toast(e.message));
      zustand.auswahl.clear();
      return;
  }
}

// Die Leiste über der Liste. Im Papierkorb: was drin liegt und die entfernten Ordner mit „Wieder hinzufügen“. Ohne eingetragenen Ordner, aber
// mit Modellen im Katalog: was los ist und wie es zurückgeht. Einen „Papierkorb leeren“ gibt es bewusst nicht: er räumte per Müllsammler alles
// Gelöschte auf einmal ab (auch entfernte Ordner, Baugruppen, Drucke) und liesse sich nicht rückgängig machen. Endgültig entfernt wird nur
// einzeln (endgueltigEntfernen).
function zeichneHinweisLeiste() {
  const entf = zustand.entfernteWurzeln || [];
  const zeilen = [];
  if (zustand.ansicht === "papierkorb") {
    const n = zustand.modelle.length;
    zeilen.push(`<div class="pk-zeile"><span>🗑 ${n ? `${n.toLocaleString("de-DE")} ${n === 1 ? "Modell" : "Modelle"}` : "Keine Modelle"} im Papierkorb. Er wird nie von selbst geleert; „Wiederherstellen“ holt ein Modell zurück, „Endgültig entfernen“ nimmt eines für immer heraus.</span></div>`);
    for (const w of entf) {
      zeilen.push(`<div class="pk-zeile"><span>📁 Entfernter Ordner <b>${esc(w.name || "")}</b> <code>${esc(w.pfad || "")}</code>${w.modelle ? ` · ${w.modelle.toLocaleString("de-DE")} Modelle` : ""}${w.vorhanden ? "" : " · liegt dort nicht mehr"}</span>
        ${w.vorhanden ? `<button class="knopf klein" data-wurzel-zurueck="${esc(w.id)}">Wieder hinzufügen</button>` : ""}</div>`);
    }
  } else if (zustand.hatWurzeln === false && zustand.katalogLeer === false) {
    zeilen.push(`<div class="pk-zeile"><span>Es ist kein Ordner mehr eingetragen. Die Modelle bleiben im Katalog, samt Tags und Drucken, und warten auf ihre Dateien.${entf.length ? " Entfernte Ordner holst du unter Bereinigen › Papierkorb zurück." : ""}</span>
      <button class="knopf klein" id="wurzel-neu-4">Ordner hinzufügen …</button></div>`);
  }
  $("#pk-leiste").hidden = !zeilen.length;
  $("#pk-leiste").innerHTML = zeilen.join("");
}
document.addEventListener("click", async (e) => {
  const zurueck = e.target.closest("[data-wurzel-zurueck]");
  if (zurueck) {
    try {
      const r = await api(`/api/wurzeln/${encodeURIComponent(zurueck.dataset.wurzelZurueck)}/wiederherstellen`, { method: "POST" });
      einlesenGestartet(r.lauf);
      await ladeSeite();
      neuLaden();
    } catch (err) { toast(err.message); }
  }
  if (e.target.closest("#wurzel-neu-4")) wurzelNeu();
});


async function loeschenViele(modelle) {
  if (await loeschDialog(modelle, `${modelle.length} Modelle aus dem Katalog entfernen?`)) { zustand.auswahl.clear(); waehle(null); }
}

// ---------------------------------------------------------------- Ordner wählen, Archive

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

async function archiveEntpacken() {
  $("#import-menu").hidden = true;
  const liste = await api("/api/archive");
  if (!liste.length) return toast("Keine Archive in den Ordnern.");
  const a = await dialog(`<h2>Archive entpacken</h2><p class="dim">Jedes in einen Unterordner daneben. Heraus kommen nur Modelle, G-Code, Bilder und Texte — nie Programme.</p>
    ${liste.map((x, i) => `<label><input type="checkbox" data-archiv="${esc(x.id)}" ${i < 50 ? "checked" : ""}> ${esc(x.id.split("/").slice(1).join("/"))} <span class="dim">${zahl(x.groesse / 1048576, 1)} MB</span></label>`).join("")}
    <p class="dim">Das Archiv selbst bleibt unverändert liegen.</p>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Entpacken</button></div>`);
  if (a !== "ja") return;
  const gewaehlt = [...document.querySelectorAll("[data-archiv]:checked")].map((x) => x.dataset.archiv);
  let n = 0, lauf = null;
  for (const id of gewaehlt) {
    try { const r = await api("/api/archive/entpacken", { method: "POST", body: { id } }); n += r.entpackt; lauf = r.lauf; }
    catch (e) { toast(`${id}: ${e.message}`); }
  }
  einlesenGestartet(lauf);
}

// ---------------------------------------------------------------- Inspektor

// `live`: aus einer Live-Meldung, nicht vom Anwender. Dann wird nicht neu
// gezeichnet, solange er im Inspektor tippt — sonst ersetzte das neue Feld
// seine halbe Eingabe. Beim Verlassen des Feldes wird es nachgeholt.
async function waehle(id, live = false) {
  zustand.gewaehlt = id;
  raster.zeichne();
  if (!id && zustand.baugruppe && typeof zeigeBgUebersicht === "function") return zeigeBgUebersicht();
  if (!id) { zustand.angezeigt = null; if (dreiDModul) (await dreiD()).schliessen(); $("#inspektor").innerHTML = `<p class="hinweis">Wähle ein Modell aus, um Details, Vorschau und Tags zu sehen.</p>`; return; }
  const [m, prog, materialien] = await Promise.all([api(`/api/modelle/${id}`), ladeProgramme(), api("/api/materialien")]);
  if (zustand.gewaehlt !== id) return;
  if (live && zustand.angezeigt === id && imInspektorAmTippen()) { zustand.nachholen = true; return; }
  const papierkorb = m.papierkorb;
  const zeile = ([a, b]) => `<div class="zeile"><span>${a}</span><span>${b}</span></div>`;
  // Gewicht, Zeit, Filament: vom Referenzdruck, sonst aus der Datei (KONZEPT §4.6).
  const rw = m.ref_werte;
  const zeit = rw?.dauer_s || m.platten.reduce((t, p) => t + (p.zeit_s || 0), 0);
  const zeitQuelle = rw?.dauer_s ? "Referenzdruck" : "Slicer";
  const drucken = [
    ["Grösse", esc(masse(m.masse) || "–")],
    ["Gewicht", m.gewicht_g ? esc(zahl(m.gewicht_g, 1)) + ` g <small class="dim">${m.gewicht_herkunft === "druck" ? "Referenzdruck" : "aus Slicer"}</small>` : "–"],
    ...(zeit ? [["Druckzeit", esc(dauer(zeit)) + ` <small class="dim">${zeitQuelle}</small>`]] : []),
    ...(m.platten.length > 1 ? [["Druckplatten", m.platten.length]] : []),
  ];
  const filamentZeile = (name, liste) => `<div class="zeile"><span>${name}</span><span>${liste.map((f) =>
    `<span class="farbpunkt" style="background:${esc(f.farbe || "transparent")}"></span>${esc(f.typ || "?")} ${zahl(f.g, 1)} g`).join("<br>")}</span></div>`;
  const platten = rw?.filament?.length ? filamentZeile("Filament", rw.filament)
    : m.platten.map((p) => filamentZeile(m.platten.length > 1 ? `Platte ${p.nr}` : "Filament", p.filamente)).join("");
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
  // Eine Live-Meldung zeichnet den Inspektor neu; ein offenes Menü bleibt offen.
  const menuOffen = zustand.angezeigt === id && $("#mehr-menu") && !$("#mehr-menu").hidden;
  const reiter = papierkorb ? "datei" : ["uebersicht", "verwendet", "drucke", "datei"].includes(localStorageLesen("reiter")) ? localStorageLesen("reiter") : "uebersicht";
  const reiterKopf = papierkorb ? "" : `<div class="i-reiter" role="tablist">
      <button role="tab" data-reiter="uebersicht">Übersicht</button>
      <button role="tab" data-reiter="verwendet">Verwendet${(m.baugruppen || []).length + m.sammlungen.length ? ` <span class="d-zahl">${(m.baugruppen || []).length + m.sammlungen.length}</span>` : ""}</button>
      <button role="tab" data-reiter="drucke">Drucke${m.drucke_n ? ` <span class="d-zahl">${m.drucke_n}</span>` : ""}</button>
      <button role="tab" data-reiter="datei">Datei</button></div>`;
  $("#inspektor").innerHTML = `
    <div class="i-fix">
      ${zustand.baugruppe ? `<button class="zurueck" id="bg-zurueck">← Baugruppe</button>` : ""}
      <div class="galerie" id="i-galerie" data-sig="${esc(sig)}"></div>
      <div class="i-griff" title="Höhe der Vorschau ziehen (Doppelklick: zurücksetzen)"></div>
      <div class="i-name">${esc(m.name)}<span class="dim">${esc(endung[m.format] || "")}</span></div>
      ${papierkorb ? `<div class="i-haupt"><button class="knopf akzent" id="wiederherstellen">Wiederherstellen</button>
        <button class="knopf gefahr" id="endgueltig">Endgültig entfernen …</button></div>`
        : `<div class="i-haupt">${oeffnenKnoepfe(m, prog)}
        <div class="mehr"><button class="schalter" id="mehr-knopf" title="Weitere Aktionen">⋯</button>
          <div class="menu" id="mehr-menu" hidden>
            <button id="umbenennen">Umbenennen …</button>
            <button id="verschieben">In anderen Ordner verschieben …</button>
            <button id="gal-plus-menu">Bild hinzufügen …</button>
            <hr><button id="loeschen" class="gefahr">Löschen …</button>
          </div></div>
      </div>`}
      ${reiterKopf}
    </div>
    ${m.fehler_text ? `<p class="fehler">Unlesbar: ${esc(m.fehler_text)}</p>` : ""}
    ${m.fehlt ? fehltTeil(m) : ""}

    <div class="i-tafel" data-reiter="uebersicht">
    ${papierkorb ? "" : `<div class="i-schalter">
        <button class="schalter ${m.warteschlange != null ? "an" : ""}" data-ab-phase="2" id="ws-knopf" title="${m.warteschlange != null ? "Aus der Warteschlange nehmen" : "Zum Drucken vormerken"}">☰ ${m.warteschlange != null ? `Warteschlange · Platz ${m.warteschlange + 1}` : "In Warteschlange"}</button>
        <button class="schalter ${m.gedruckt ? "an" : ""}" id="gedruckt" title="${m.drucke_n ? "Zu den Drucken" : "Als gedruckt markieren"}">${m.drucke_n ? `✓ ${m.drucke_n}× gedruckt` : "○ Noch nicht gedruckt"}</button>
        <button class="schalter ${m.favorit ? "an" : ""}" id="favorit" title="Favorit">♥</button>
        <button class="schalter ${m.entwurf ? "an" : ""}" id="entwurf" title="${m.entwurf ? "Kein Entwurf mehr" : "Als Entwurf markieren — ausblendbar, nicht in neuen Baugruppen"}">✎ Entwurf</button>
      </div>`}
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
    </div>

    ${papierkorb ? "" : `<div class="i-tafel" data-reiter="verwendet">${verwendetTafel(m)}</div>`}
    ${papierkorb ? "" : `<div class="i-tafel" data-reiter="drucke">${druckeTafel(m)}</div>`}

    <div class="i-tafel" data-reiter="datei">
      <div class="i-titel">MODELLDATEN</div>
      <div class="i-karte">${details.map(zeile).join("")}${quelle}</div>
      ${papierkorb ? "" : cadZeile(m)}
      <div class="i-label">${papierkorb ? "Lag zuletzt in" : "Ort" + (m.orte.length > 1 ? `e (${m.orte.length})` : "")}</div>
      ${orte}
    </div>`;
  $("#inspektor").dataset.reiter = reiter;
  $("#inspektor").dataset.id = id;
  if (menuOffen) $("#mehr-menu").hidden = false;
  if (alteGalerie) { $("#i-galerie").replaceWith(alteGalerie); return; }
  zustand.angezeigt = id;
  zeigeGalerie(m);
}

// ---------------------------------------------------------------- Drucke
//
// Ein Druck ist ein einzelnes Mal, dass das Modell auf dem Drucker lag: mit
// Gewicht, Dauer, Filament, Foto, Ergebnis, Notiz. „Gedruckt“ und der
// Zähler folgen daraus (KONZEPT §4.6). Ein Druck kann an mehreren Modellen
// hängen — eine Platte mit drei Teilen —, dann steht „zusammen mit …“ dabei.

const ERGEBNIS = { gut: ["✓ Gut", "gut"], fehler: ["⚠ Mit Fehlern", "fehler"], abgebrochen: ["✕ Abgebrochen", "abbruch"] };
const datumDe = (d) => d ? new Date(d + "T00:00").toLocaleDateString("de-DE") : "Datum unbekannt";

function druckeTafel(m) {
  const liste = m.drucke || [];
  const kopf = `<div class="d-oben"><button class="knopf akzent" data-druck-neu>＋ Druck</button>
    <span class="dim">${m.drucke_n ? `${m.drucke_n}× gedruckt` : "Noch nicht gedruckt"}</span></div>`;
  if (!liste.length) return kopf + `<p class="d-leer">Hier stehen die Drucke dieses Modells — mit Einstellungen, Foto und Ergebnis.
    Wenn einer gut wurde, markierst du ihn als Referenz und weisst beim nächsten Mal, wie es ging.</p>`;
  return kopf + liste.map((d) => {
    const [text, art] = ERGEBNIS[d.ergebnis] || ERGEBNIS.gut;
    const werte = [d.gewicht_g != null ? `${zahl(d.gewicht_g, 1)} g` : "", d.dauer_s ? dauer(d.dauer_s) : ""].filter(Boolean).join(" · ");
    const fil = d.filament.map((f) => `<span class="chip"><span class="farbpunkt" style="background:${esc(f.farbe || "transparent")}"></span>${esc(f.typ || "?")}${f.g != null ? " " + zahl(f.g, 1) + " g" : ""}</span>`).join("");
    return `<div class="druck ${d.referenz ? "ref" : ""}" data-druck="${esc(d.id)}">
      <div class="d-kopf"><span class="d-erg ${art}">${text}</span><b>${esc(datumDe(d.datum))}</b>
        ${d.referenz ? `<span class="d-refmarke" title="So war es gut — Referenz für dieses Modell">★ Referenz</span>` : ""}</div>
      ${werte || fil ? `<div class="d-werte">${werte ? `<span class="mono">${esc(werte)}</span>` : ""}${fil}</div>` : ""}
      ${d.notiz ? `<p class="d-notiz">${esc(d.notiz)}</p>` : ""}
      ${d.zusammen_mit.length ? `<div class="d-zusammen">zusammen mit ${d.zusammen_mit.map((x) => `<button class="link" data-gefaehrte="${esc(x.id)}">${esc(x.name)}</button>`).join(", ")}</div>` : ""}
      <div class="d-fotos">${d.bilder.map((b) => `<span class="d-foto"><a href="${esc(b.url)}" target="_blank" rel="noopener"><img src="${esc(b.url)}" alt="" loading="lazy"></a>
        <button data-druck-bild-weg="${esc(d.id)}|${esc(b.k)}" title="Foto entfernen">×</button></span>`).join("")}
        <button class="d-fotoplus" data-druck-foto="${esc(d.id)}" title="Foto zum Druck hinzufügen">＋ Foto</button></div>
      <div class="d-aktionen"><button class="link" data-druck-ref="${esc(d.id)}" data-an="${d.referenz ? "0" : "1"}">${d.referenz ? "★ Keine Referenz mehr" : "☆ Als Referenz"}</button>
        <button class="link" data-druck-aendern="${esc(d.id)}">Bearbeiten …</button>
        <button class="link gefahr" data-druck-weg="${esc(d.id)}">Entfernen …</button></div>
    </div>`;
  }).join("");
}

// Ein Formular für „neu“ und „bearbeiten“. Gibt die Felder zurück oder null.
async function druckDialog({ titel, namen, druck }) {
  const mats = await api("/api/materialien");
  const d = druck || {};
  const f0 = (d.filament && d.filament[0]) || {};
  const std = d.dauer_s ? [Math.floor(d.dauer_s / 3600), Math.round((d.dauer_s % 3600) / 60)] : ["", ""];
  const heute = new Date().toISOString().slice(0, 10);
  const a = await dialog(`<h2>${esc(titel)}</h2>
    ${namen.length > 1 ? `<p class="dim">Gilt für: ${namen.map(esc).join(", ")}</p>` : ""}
    <div class="d-form">
      <div class="d-ergebnis">${Object.entries(ERGEBNIS).map(([k, [t]]) =>
        `<label><input type="radio" name="df-erg" value="${k}" ${(d.ergebnis || "gut") === k ? "checked" : ""}><span>${t}</span></label>`).join("")}</div>
      <label>Datum <input type="date" id="df-datum" value="${esc(druck ? (d.datum || "") : heute)}"></label>
      <div class="d-zweier">
        <label>Gewicht (g) <input type="number" id="df-g" min="0" step="0.1" value="${d.gewicht_g ?? ""}"></label>
        <label>Dauer <span class="d-dauer"><input type="number" id="df-h" min="0" value="${std[0]}"> h <input type="number" id="df-min" min="0" max="59" value="${std[1]}"> min</span></label>
      </div>
      <div class="d-filament">
        <label>Material <select id="df-typ"><option value="">–</option>${mats.map((x) => `<option ${f0.typ === x ? "selected" : ""}>${esc(x)}</option>`).join("")}</select></label>
        <label>Farbe <input type="color" id="df-farbe" value="${esc(f0.farbe || "#cccccc")}" data-gesetzt="${f0.farbe ? "1" : ""}"></label>
        <label>Verbrauch (g) <input type="number" id="df-fg" min="0" step="0.1" value="${f0.g ?? ""}"></label>
      </div>
      <label>Notiz <textarea id="df-notiz" rows="3" placeholder="z. B. Düse 215 °C, Lüfter 60 %, Brim an">${esc(d.notiz || "")}</textarea></label>
    </div>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" id="df-ok" value="ja">Speichern</button></div>`);
  if (a !== "ja") return null;
  const zahlOderNull = (id) => { const v = $(id).value; return v === "" ? null : Number(v); };
  const h = zahlOderNull("#df-h"), mi = zahlOderNull("#df-min");
  const typ = $("#df-typ").value, farbe = $("#df-farbe").dataset.gesetzt ? $("#df-farbe").value : null, fg = zahlOderNull("#df-fg");
  // Weitere Filamente (aus einer G-Code-Datei, später) bleiben unberührt.
  const rest = (d.filament || []).slice(1);
  const erstes = typ || farbe || fg != null ? [{ typ: typ || null, farbe, g: fg }] : [];
  return {
    ergebnis: document.querySelector('input[name="df-erg"]:checked').value,
    datum: $("#df-datum").value || null,
    gewicht_g: zahlOderNull("#df-g"),
    dauer_s: h == null && mi == null ? null : (h || 0) * 3600 + (mi || 0) * 60,
    filament: [...erstes, ...rest],
    notiz: $("#df-notiz").value,
  };
}
document.addEventListener("input", (e) => { if (e.target.id === "df-farbe") e.target.dataset.gesetzt = "1"; });

async function druckAnlegen(modelle) {
  const namen = modelle.map((id) => zustand.modelle.find((x) => x.id === id)?.name || id);
  const felder = await druckDialog({ titel: modelle.length > 1 ? "Zusammen gedruckt" : "Neuer Druck", namen });
  if (!felder) return;
  try {
    await api("/api/drucke", { method: "POST", body: { modelle, felder } });
    toast("Druck angelegt.");
  } catch (e) { toast(e.message); return; }
  localStorageSchreiben("reiter", "drucke");
  if (zustand.gewaehlt && modelle.includes(zustand.gewaehlt)) waehle(zustand.gewaehlt);
}

// „Wo kommt dieses Modell vor?“ — jede Zeile führt dorthin. Die Angaben stehen schon im Modell; flatgraph liefert sie als Nachbarschaft des Knotens.
function verwendetTafel(m) {
  const zeile = (attr, inhalt, rechts) => `<button class="v-zeile" ${attr}><span>${inhalt}</span>${rechts ? `<em>${rechts}</em>` : ""}</button>`;
  const gruppe = (titel, zeilen) => (zeilen.length ? `<div class="i-titel">${titel}</div><div class="v-liste">${zeilen.join("")}</div>` : "");
  const bg = (m.baugruppen || []).map((b) => zeile(`data-baugruppe="${esc(b.id)}"`, `🧩 ${esc(b.name)}`, `${b.menge}×`));
  const sa = m.sammlungen.map((x) => zeile(`data-springe="sammlung" data-id="${esc(x.id)}"`, esc(x.name), "Sammlung"));
  const tg = m.tags.map((t) => zeile(`data-springe="tag" data-id="${esc(t)}"`, `#${esc(t)}`));
  const dr = m.drucke_n ? [zeile('data-gehe-reiter="drucke"', `🖨 ${m.drucke_n} ${m.drucke_n === 1 ? "Druck" : "Drucke"}`, "ansehen")] : [];
  // Anzeige wie in der Seitenleiste: der Name der Wurzel statt ihrer Kennung („demo/Drohne“ statt „w_001/Drohne“)
  const ortName = (o) => { const [wurzel, ...rest] = o.split("/").filter(Boolean); return [wurzelName(wurzel), ...rest].join("/"); };
  const or = [...new Set(m.ordner || [])].map((o) => zeile(`data-springe="ordner" data-id="${esc(o)}"`, `📁 ${esc(ortName(o))}`));
  const leer = !bg.length && !sa.length && !tg.length && !dr.length
    ? `<p class="dim v-leer">Noch in keiner Baugruppe oder Sammlung, ohne Tags und ohne Druck.</p>` : "";
  return leer + gruppe("BAUGRUPPEN", bg) + gruppe("SAMMLUNGEN", sa) + gruppe("TAGS", tg) + gruppe("DRUCKE", dr) + gruppe("ORDNER", or);
}

// Vor und zurück zwischen den Ansichten, die man angesprungen hat (Verlauf des Browsers: Alt+← / Alt+→ und die Maustasten gehen von selbst).
// Eine Momentaufnahme hält fest, was man sah: Ordner, Sammlung, Filter, Baugruppe, gewähltes Modell.
const nav = { nr: 0, hoechste: 0 };
const momentaufnahme = () => ({ nr: nav.nr, ordner: zustand.ordner, sammlung: zustand.sammlung, ansicht: zustand.ansicht, format: zustand.format,
  suche: zustand.suche, tags: [...zustand.tags], material: [...zustand.material], baugruppe: zustand.baugruppe || "", gewaehlt: zustand.gewaehlt });
function navKnoepfe() {
  if ($("#nav-zurueck")) $("#nav-zurueck").disabled = nav.nr <= 0;
  if ($("#nav-vor")) $("#nav-vor").disabled = nav.nr >= nav.hoechste;
}
function navigiere(aendern) {
  try { history.replaceState(momentaufnahme(), ""); } catch { /* ohne Verlauf bleibt es bei der Ansicht */ }
  const r = aendern();
  nav.nr += 1; nav.hoechste = nav.nr;
  try { history.pushState(momentaufnahme(), ""); } catch { /* s. o. */ }
  navKnoepfe();
  return r;
}
async function ansichtWiederherstellen(st) {
  const warBaugruppe = zustand.baugruppe;
  nav.nr = st.nr ?? 0;
  Object.assign(zustand, { ordner: st.ordner, sammlung: st.sammlung, ansicht: st.ansicht, format: st.format, suche: st.suche || "",
    tags: new Set(st.tags), material: new Set(st.material) });
  if ($("#suche")) $("#suche").value = zustand.suche;
  navKnoepfe();
  if (st.baugruppe) return oeffneBaugruppe(st.baugruppe);
  if (warBaugruppe) {
    zustand.baugruppe = "";
    zeigeBaugruppeFlaeche(false);
    document.querySelectorAll("[data-baugruppe]").forEach((b) => b.classList.remove("aktiv"));
  }
  zustand.gewaehlt = null;
  neuLaden();
  if (st.gewaehlt) waehle(st.gewaehlt);
}
window.addEventListener("popstate", (e) => { if (e.state) ansichtWiederherstellen(e.state); });
function springeZu(art, id) {
  const leeren = { tags: new Set(), material: new Set(), format: "" };
  return navigiere(() => {
    if (zustand.baugruppe) { zustand.baugruppe = ""; zeigeBaugruppeFlaeche(false); document.querySelectorAll("[data-baugruppe]").forEach((b) => b.classList.remove("aktiv")); }
    if (art === "sammlung") Object.assign(zustand, { ...leeren, sammlung: id, ansicht: "alle", ordner: "" });
    else if (art === "ordner") Object.assign(zustand, { ...leeren, ordner: id, ansicht: "alle", sammlung: "" });
    else if (art === "tag") Object.assign(zustand, { ...leeren, tags: new Set([id]), ansicht: "alle", ordner: "", sammlung: "" });
    neuLaden();
  });
}

function reiterWaehlen(r) {
  localStorageSchreiben("reiter", r);
  $("#inspektor").dataset.reiter = r;
}

let druckFotoZiel = null;
document.addEventListener("click", async (e) => {
  const t = e.target;
  if (!t.closest?.("#inspektor")) return;
  const id = zustand.gewaehlt;
  const tab = t.closest(".i-reiter [data-reiter]");
  if (tab) return reiterWaehlen(tab.dataset.reiter);
  if (t.closest("[data-druck-neu]")) return druckAnlegen([id]);
  const gef = t.closest("[data-gefaehrte]");
  if (gef) return waehle(gef.dataset.gefaehrte);
  const bearb = t.closest("[data-druck-aendern]");
  if (bearb) {
    const m = await api(`/api/modelle/${id}`);
    const d = m.drucke.find((x) => x.id === bearb.dataset.druckAendern);
    if (!d) return;
    const felder = await druckDialog({ titel: "Druck bearbeiten", namen: [m.name, ...d.zusammen_mit.map((x) => x.name)], druck: d });
    if (!felder) return;
    try { await api(`/api/drucke/${d.id}`, { method: "PATCH", body: felder }); } catch (err) { toast(err.message); }
    return waehle(id);
  }
  const rf = t.closest("[data-druck-ref]");
  if (rf) {
    try { await api(`/api/drucke/${rf.dataset.druckRef}/referenz`, { method: "POST", body: { modell: id, an: rf.dataset.an === "1" } }); }
    catch (err) { toast(err.message); }
    return waehle(id);
  }
  const weg = t.closest("[data-druck-weg]");
  if (weg) {
    const a = await dialog(`<h2>Druck entfernen?</h2><p class="dim">Der Eintrag und seine Fotos verschwinden aus partAtlas; die Fotos bleiben im Archiv des Bestands (<code>vault_archive</code>). Hängt der Druck an mehreren Modellen, verschwindet er bei allen.</p>
      <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr" value="ja">Entfernen</button></div>`);
    if (a !== "ja") return;
    try { await api(`/api/drucke/${weg.dataset.druckWeg}`, { method: "DELETE" }); } catch (err) { toast(err.message); }
    return waehle(id);
  }
  const foto = t.closest("[data-druck-foto]");
  if (foto) { druckFotoZiel = foto.dataset.druckFoto; return $("#druck-bild-wahl").click(); }
  const fw = t.closest("[data-druck-bild-weg]");
  if (fw) {
    const [did, k] = fw.dataset.druckBildWeg.split("|");
    try { await api(`/api/drucke/${did}/bilder/${k}`, { method: "DELETE" }); } catch (err) { toast(err.message); }
    return waehle(id);
  }
});
// Fotos auf einen Druck gezogen; ohne Druck (leerer Teil des Reiters) entsteht ein neuer mit diesen Fotos.
async function druckBilderAblegen(did, dateien) {
  const id = zustand.gewaehlt;
  const bilder = [...dateien].filter((f) => /^image\/(png|jpeg|webp)$/.test(f.type));
  if (!id || !bilder.length) return toast("Nur PNG, JPG oder WebP.");
  try {
    if (!did) did = (await api("/api/drucke", { method: "POST", body: { modelle: [id], felder: {} } })).id;
    for (const f of bilder) {
      const r = await fetch(`/api/drucke/${did}/bilder`, { method: "POST", body: f });
      if (!r.ok) toast((await r.json().catch(() => ({}))).fehler || "Foto nicht gespeichert.");
    }
  } catch (err) { return toast(err.message); }
  toast(bilder.length > 1 ? `${bilder.length} Fotos hinzugefügt.` : "Foto hinzugefügt.");
  if (zustand.gewaehlt === id) waehle(id);
}
$("#druck-bild-wahl").addEventListener("change", async (e) => {
  const did = druckFotoZiel;
  const bilder = [...e.target.files];
  e.target.value = "";
  if (!did) return;
  for (const f of bilder) {
    const r = await fetch(`/api/drucke/${did}/bilder`, { method: "POST", body: f });
    if (!r.ok) toast((await r.json().catch(() => ({}))).fehler || "Foto nicht gespeichert.");
  }
  if (zustand.gewaehlt) waehle(zustand.gewaehlt);
});

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
  const hatNetz = !m.papierkorb && !m.fehlt && !m.fehler_text && !nurCad(m);
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
  umschalten();
}

const hauptHtml = (m, f, darf) => !f
  ? `<div class="gal-leer"><span>${nurCad(m) ? nurCadText(m) : "Keine Vorschau"}</span>
      ${darf ? `<button class="knopf" data-gal-plus>＋ Eigenes Bild hinzufügen</button>` : ""}</div>`
  : f.art === "3d" ? `<span class="laden">3D wird geladen …</span><button class="bild-knopf" id="ansicht-zurueck" title="Ansicht zurücksetzen">⟲</button>`
  : `<img src="${esc(f.url)}" alt="${esc(f.titel)}" draggable="false">`;

const aktionenHtml = (f, darf) => f && f.art === "eigen" && darf
  ? `${f.ist_vorschaubild ? "" : `<button data-gal-titel="eigen:${esc(f.k)}" title="Dieses Bild auf der Kachel zeigen">★ Als Vorschaubild</button>`}
    <button data-gal-weg="${esc(f.k)}" title="Bild entfernen">Entfernen</button>`
  : f && f.art !== "3d" && darf && !f.ist_vorschaubild
    ? `<button data-gal-titel="${esc(f.art)}" title="Dieses Bild auf der Kachel zeigen">★ Als Vorschaubild</button>` : "";

const etikettText = (f, i, n) => `${f.titel}${n > 1 ? ` · ${i + 1} / ${n}` : ""}`;

// Beim Blättern bleiben Pfeile, Leiste und Aktionen stehen — nur das Bild
// wechselt. Wer sie neu zeichnet, nimmt der Maus das Ziel zwischen Drücken
// und Loslassen: der Klick geht verloren, das Bild flackert.
async function umschalten() {
  const { m, folien, i } = galerie;
  const bild = $("#i-bild");
  if (!bild || !m) return;
  const f = folien[i];
  if (dreiDModul) (await dreiD()).schliessen();
  viewer = null;
  if (galerie.i !== i || $("#i-bild") !== bild) return;
  const haupt = bild.querySelector(".gal-haupt");
  const img = haupt.firstElementChild;
  if (f && f.art !== "3d" && img?.tagName === "IMG") { img.src = f.url; img.alt = f.titel; }
  else haupt.innerHTML = hauptHtml(m, f, !m.papierkorb);
  const et = bild.querySelector(".gal-etikett");
  if (et && f) et.textContent = etikettText(f, i, folien.length);
  bild.querySelector(".gal-aktionen").innerHTML = aktionenHtml(f, !m.papierkorb);
  document.querySelectorAll("#i-galerie .gal-mini[data-gal-i]").forEach((x) => x.classList.toggle("an", Number(x.dataset.galI) === i));
  if (f && f.art === "3d") lade3d(m);
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
  const minis = folien.map((x, j) => `<button class="gal-mini ${j === i ? "an" : ""}" data-gal-i="${j}" data-art="${x.art}" title="${esc(x.titel)}">
      ${x.art === "3d" ? "<span>3D</span>" : `<img src="${esc(x.url)}" alt="" loading="lazy" draggable="false">`}</button>`).join("");
  feld.innerHTML = `<div class="i-bild" id="i-bild"><div class="gal-haupt">${hauptHtml(m, f, darf)}</div>${pfeile}
      <span class="gal-etikett">${f ? esc(etikettText(f, i, n)) : ""}</span><div class="gal-aktionen">${aktionenHtml(f, darf)}</div>
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
  if (titel) return vorschauSetzen(titel.dataset.galTitel);
  const weg = t.closest("[data-gal-weg]");
  if (weg) return bildEntfernen(weg.dataset.galWeg);
});

// „eigen:<k>“ = eigenes Bild, sonst die Art (extrahiert, berechnet).
async function vorschauSetzen(wahl) {
  const m = galerie.m;
  const eigen = wahl.startsWith("eigen:");
  await api(eigen ? `/api/modelle/${m.id}/bilder/${wahl.slice(6)}/titel` : `/api/modelle/${m.id}/vorschau/${wahl}/titel`, { method: "POST" });
  toast("Vorschaubild gesetzt.");
  galerie.ziel = eigen ? wahl.slice(6) : null;
  zustand.angezeigt = null;
  waehle(m.id);
}

async function bildEntfernen(k) {
  const m = galerie.m;
  {
    const a = await dialog(`<h2>Bild entfernen?</h2><p class="dim">Es verschwindet aus partAtlas. Die Datei bleibt im Archiv des Bestands (<code>vault_archive</code>).</p>
      <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr" value="ja">Entfernen</button></div>`);
    if (a !== "ja") return;
    await api(`/api/modelle/${m.id}/bilder/${k}`, { method: "DELETE" });
    zustand.angezeigt = null;
    return waehle(m.id);
  }
}

// Rechtsklick auf das Bild: dasselbe wie die Knöpfe, an der Stelle der Maus.
document.addEventListener("contextmenu", (e) => {
  const eintrag = e.target.closest?.(".eintrag[data-ordner]");
  if (eintrag) {
    e.preventDefault();
    const menu = $("#kontext");
    const istWurzel = eintrag.dataset.wurzel !== undefined;
    // Wie in VS Code: „Im Dateimanager zeigen“ für jeden Ordner. Löschen nur für Unterordner; die Wurzel wird nur entfernt.
    menu.innerHTML = `<button type="button" data-km="ordner-zeigen">Im Dateimanager zeigen</button>`
      + (istWurzel ? `<button type="button" data-km="wurzel-weg" class="gefahr">Aus partAtlas entfernen …</button>`
                   : `<button type="button" data-km="ordner-weg" class="gefahr">Ordner aus dem Katalog entfernen …</button>`);
    kontextMenu.ziel = { ordner: { id: eintrag.dataset.ordner, name: eintrag.dataset.wurzelName || eintrag.dataset.ordner.split("/").pop() },
                         wurzel: istWurzel ? { id: eintrag.dataset.wurzel, name: eintrag.dataset.wurzelName, pfad: eintrag.title, anzahl: Number(eintrag.querySelector("em")?.textContent) || 0 } : null };
    menu.hidden = false;
    const b = menu.getBoundingClientRect();
    menu.style.left = Math.min(e.clientX, innerWidth - b.width - 6) + "px";
    menu.style.top = Math.min(e.clientY, innerHeight - b.height - 6) + "px";
    return;
  }
  if (!e.target.closest?.("#i-bild") || !galerie.m || galerie.m.papierkorb) return;
  const f = galerie.folien[galerie.i];
  if (!f || f.art === "3d") return;
  e.preventDefault();
  const eintraege = [];
  if (!f.ist_vorschaubild) eintraege.push(["gal-titel", "★ Als Vorschaubild festlegen"]);
  if (f.art === "eigen") eintraege.push(["gal-weg", "Bild entfernen …", "gefahr"]);
  eintraege.push(["gal-plus", "Eigenes Bild hinzufügen …"]);
  const menu = $("#kontext");
  menu.innerHTML = eintraege.map(([k, t, kl]) => `<button type="button" data-km="${k}" class="${kl || ""}">${t}</button>`).join("");
  kontextMenu.ziel = { galerie: f };
  menu.hidden = false;
  const b = menu.getBoundingClientRect();
  menu.style.left = Math.min(e.clientX, innerWidth - b.width - 6) + "px";
  menu.style.top = Math.min(e.clientY, innerHeight - b.height - 6) + "px";
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

// Die Programme für die Hover-Knöpfe in Liste und Karten: synchron zur Hand, weil die Zeilen
// als Text gebaut werden. Nach dem Laden und nach geänderten Einstellungen neu zeichnen.
let programmDaten = null;
function programmeAktualisieren() {
  programmCache = null;
  return ladeProgramme().then((p) => { programmDaten = p; raster.zeichne(); });
}

// Zeichensprache wie die Ansichtsleiste links: Linie, flach, einfarbig (16 × 16, 1,4 px).
const HV_ICONS = {
  slicer: '<svg viewBox="0 0 16 16"><path d="M8 2 14 5 8 8 2 5z"/><path d="M2 8l6 3 6-3"/><path d="M2 11l6 3 6-3"/></svg>',
  cad: '<svg viewBox="0 0 16 16"><path d="M8 1.5 14 4.7v6.6L8 14.5 2 11.3V4.7z"/><path d="M2 4.7 8 8l6-3.3M8 8v6.5"/></svg>',
};

// Beim Überfahren: im Slicer / im CAD öffnen. Nur, wo es geht (Datei da, Programm für das Format da).
function hoverAktionen(m) {
  if (!programmDaten || m.fehlt || m.fehler || zustand.ansicht === "papierkorb") return "";
  const { je } = programmeFuer(m, programmDaten);
  const knoepfe = ["slicer", "cad"].map((a) => {
    if (je[a]?.length) {
      const p = je[a][0];
      return `<button type="button" class="hv-btn" data-hv="${esc(p.pfad)}" data-hv-id="${esc(m.id)}" title="In ${esc(p.name)} öffnen" aria-label="In ${esc(p.name)} öffnen">${HV_ICONS[a]}</button>`;
    }
    // Gar kein Programm dieser Art eingerichtet: der Knopf bleibt da, gedämpft, und führt in die Einstellungen —
    // sonst findet niemand heraus, warum er fehlt. (Kann nur das Format nicht, bleibt er weg.)
    if (programmDaten.programme.some((p) => p.art === a)) return "";
    const name = programmDaten.arten?.[a] || a;
    return `<button type="button" class="hv-btn leer" data-hv-einrichten="1" title="Noch kein ${esc(name)} eingerichtet — in den Einstellungen wählen" aria-label="${esc(name)} einrichten">${HV_ICONS[a]}</button>`;
  }).join("");
  return knoepfe ? `<div class="hv">${knoepfe}</div>` : "";
}

let programmCache = null;
function ladeProgramme() {
  if (!programmCache) programmCache = api("/api/programme").catch(() => ({ programme: [], standard: {}, arten: {} }));
  return programmCache;
}

// Hauptknopf mit dem Standardprogramm des Formats, daneben die übrigen,
// die das Format können, und immer „mit dem System“ — so bleibt keine
// Datei ohne Weg nach draussen, auch wenn nichts erkannt wurde.
// Je Art (Slicer, CAD) die Programme, die das Format öffnen, das
// Standardprogramm der Art vorn. Slicen und Bearbeiten sind verschiedene
// Absichten — deshalb zwei Wege statt eines „Öffnen“.
const ART_SYMBOL = { slicer: "🖨", cad: "📐" };
function programmeFuer(m, prog) {
  const std = prog.programme.find((p) => p.pfad === prog.standard[m.format]);
  const je = {};
  for (const art of Object.keys(prog.arten)) {
    const liste = prog.programme.filter((p) => p.art === art && p.formate.includes(m.format));
    je[art] = std && std.art === art ? [std, ...liste.filter((p) => p !== std)] : liste;
  }
  return { je, hauptArt: std ? std.art : null };
}

function oeffnenKnoepfe(m, prog) {
  const { je, hauptArt } = programmeFuer(m, prog);
  const arten = Object.keys(prog.arten).filter((a) => je[a].length).sort((x, y) => (y === hauptArt) - (x === hauptArt));
  if (!arten.length) return `<button class="knopf" id="oeffnen" data-system="1" title="Mit dem Standardprogramm des Systems öffnen">↗ Öffnen</button>`;
  const knoepfe = arten.map((art, i) => {
    const p = je[art][0];
    return `<button class="knopf ${i === 0 ? "akzent" : ""}" ${i === 0 ? 'id="oeffnen"' : ""} data-oeffne-pfad="${esc(p.pfad)}"
      title="In ${esc(p.name)} öffnen (${esc(prog.arten[art])})">${ART_SYMBOL[art] || "↗"} ${esc(p.name)}</button>`;
  }).join("");
  const weitere = Object.entries(prog.arten).map(([art, titel]) => {
    const g = je[art].slice(1);
    return g.length ? `<optgroup label="${esc(titel)}">${g.map((p) => `<option value="${esc(p.pfad)}">${esc(p.name)}</option>`).join("")}</optgroup>` : "";
  }).join("");
  return knoepfe + `<select class="knopf schmal" id="oeffnen-mit" title="Öffnen mit … (weitere Programme)"><option value="">▾</option>${weitere}
      <option value="__system">Mit dem System öffnen</option><option value="__einstellungen">Programme einstellen …</option></select>`;
}

async function modellOeffnen(body, id = $("#inspektor").dataset.id) {
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

// Enter in einem Feld löst die Hauptaktion des Dialogs aus (wie ein Klick auf
// den farbigen Knopf), nie „Abbrechen“. Das Absenden des Formulars würde den
// ersten Knopf nehmen — und der ist Abbrechen. Felder mit data-enter nennen
// ihren eigenen Knopf; data-enter="" heisst: Enter tut dort nichts.
$("#dialog-inhalt").addEventListener("keydown", (e) => {
  const f = e.target;
  if (e.key !== "Enter" || e.isComposing || !f.matches?.("input:not([type=checkbox]):not([type=radio]):not([type=color]), select")) return;
  e.preventDefault();
  const ziel = f.dataset.enter != null ? f.dataset.enter : ".knoepfe .akzent";
  if (ziel) $("#dialog-inhalt").querySelector(ziel)?.click();
});

async function loeschen(id) {
  const m = zustand.modelle.find((x) => x.id === id) || await api(`/api/modelle/${id}`);
  if (await loeschDialog([id], `„${esc(m.name)}${esc(endung[m.format] || "")}“ aus dem Katalog entfernen?`)) waehle(null);
}

// Was am Modell hängt, aus der Nachbarschaft im Graphen — damit man weiss,
// was man tut. Ankreuzen lässt sich nur, was wirklich eine Wahl ist: Tags
// und Sammlungen, an denen sonst nichts mehr hängt. Alles andere geht mit in
// den Papierkorb und kommt beim Wiederherstellen zurück.
async function loeschDialog(modelle, titel, ordner = null) {
  const v = await api("/api/stapel/loeschvorschau", { method: "POST", body: { modelle } });
  const viele = modelle.length > 1;
  const nurT = v.tags.filter((t) => !t.sonst), andereT = v.tags.filter((t) => t.sonst);
  const nurS = v.sammlungen.filter((x) => !x.sonst), andereS = v.sammlungen.filter((x) => x.sonst);
  const zeile = (symbol, html) => `<div class="lz"><span class="lz-s">${symbol}</span><div>${html}</div></div>`;
  const dateien = v.dateien.length
    ? zeile("📄", `${v.dateien.length === 1 ? "<b>Die Datei</b> bleibt in ihrem Ordner liegen" : `<b>${v.dateien.length} Dateien</b> bleiben in ihren Ordnern liegen`}:
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
  const o = ordner?.inhalt;
  const ordnerZeile = !o ? "" : zeile("📁", `<b>Der Ordner bleibt mit allem, was darin liegt, auf der Platte.</b>${o.andere_n ? ` Darin liegen auch ${o.andere_n} ${o.andere_n === 1 ? "andere Datei" : "andere Dateien"}, die keine Modelle sind.` : ""}${o.mehrfach.length ? `<br>${o.mehrfach.length} ${o.mehrfach.length === 1 ? "Modell hat" : "Modelle haben"} eine Kopie ausserhalb und bleiben im Katalog.` : ""}`);
  const a = await dialog(`<h2>${titel}</h2>
    <p class="dim">Das Modell kommt in den Papierkorb von partAtlas und ist damit aus dem Katalog. <b>Die Dateien bleiben unverändert in ihren
      Ordnern</b> — partAtlas löscht und verschiebt nichts. „Wiederherstellen“ nimmt das Modell wieder auf.</p>
    <div class="loesch-liste">${ordnerZeile}${dateien}${bilder}${baugruppen}${schlange}${sammlungen}${tags}</div>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr" value="ja">Aus dem Katalog entfernen</button></div>`);
  if (a !== "ja") return false;
  const wahl = {
    tags: $("#mit-tags")?.checked ? nurT.map((t) => t.name) : [],
    sammlungen: [...document.querySelectorAll("[data-mit-sammlung]:checked")].map((x) => x.dataset.mitSammlung),
  };
  if (ordner) {
    try { return await api("/api/ordner/loeschen", { method: "POST", body: { id: ordner.id, ...wahl } }); }
    catch (e) { toast(e.message); return false; }
  }
  try {
    const r = await api("/api/stapel", { method: "POST", body: { aktion: "loeschen", modelle, wert: wahl } });
    if (r.fehler.length) toast(`${modelle.length - r.fehler.length} gelöscht, ${r.fehler.length} nicht: ${r.fehler[0].fehler}`);
    else toast(viele ? `${modelle.length} Modelle aus dem Katalog entfernt, die Dateien bleiben.` : "Aus dem Katalog entfernt, die Datei bleibt.");
    return true;
  } catch (e) { toast(e.message); return false; }
}

// Ein Modell aus dem Papierkorb endgültig aus dem Katalog nehmen. Einzeln und mit eingetipptem Wort, weil es nicht zurückkommt; vorher
// legt der Server eine Sicherung an. Liegt die Datei noch im Ordner, sagt der Dialog, dass sie beim nächsten Einlesen wiederkommt.
async function endgueltigEntfernen(id) {
  let v;
  try { v = await api(`/api/modelle/${id}/endgueltig`); } catch (e) { return toast(e.message); }
  const datei = v.im_ordner.length
    ? `<p><b>Die Datei bleibt in ihrem Ordner</b> — partAtlas löscht sie nicht. Beim nächsten Einlesen erscheint sie deshalb wieder, als neues
        Modell ohne Tags, Drucke und Bilder:</p><ul>${v.im_ordner.map((d) => `<li>${esc(d)}</li>`).join("")}</ul>
       <p class="dim">Soll sie nicht mehr im Katalog auftauchen, lass das Modell besser im Papierkorb.</p>`
    : `<p class="dim">Die Datei liegt nicht mehr in einem eingetragenen Ordner.</p>`;
  const a = await dialog(`<h2>„${esc(v.name)}“ endgültig entfernen?</h2>
    <p>Das Modell verschwindet aus dem Papierkorb und lässt sich dort nicht mehr wiederherstellen — mit seinen Tags, Drucken und
      Verknüpfungen. Vorher legt partAtlas eine Sicherung der Datenbank an.</p>
    ${datei}
    ${v.bilder ? `<p class="dim">${v.bilder === 1 ? "Das eigene Bild kommt" : `Die ${v.bilder} eigenen Bilder kommen`} ins Archiv des Bestands (vault_archive), nicht weg.</p>` : ""}
    <p>Zum Bestätigen <b>entfernen</b> eintippen:</p>
    <input type="text" id="endgueltig-wort" autocomplete="off" data-enter="#endgueltig-ja">
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr" id="endgueltig-ja" value="ja" disabled>Endgültig entfernen</button></div>`);
  if (a !== "ja") return;
  try {
    await api(`/api/modelle/${id}/endgueltig`, { method: "POST", body: { bestaetigung: $("#endgueltig-wort").value } });
    toast("Endgültig entfernt.");
    waehle(null);
  } catch (e) { toast(e.message); }
}

$("#dialog-inhalt").addEventListener("input", (e) => {
  if (e.target.id === "endgueltig-wort") $("#endgueltig-ja").disabled = e.target.value.trim().toLowerCase() !== "entfernen";
});

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
  let w;
  try { w = await api("/api/wurzeln/waehlen", { method: "POST" }); } catch (e) { return toast(e.message); }
  if (w.abgebrochen) return;
  // Ohne Dateidialog auf dem Rechner (kein zenity, kdialog, Tk) bleibt der eigene Ordnerbaum.
  const pfad = w.keinDialog ? await ordnerWaehler() : w.pfad;
  if (!pfad) return;
  // Erst zeigen, was kommt (wie pDMS), dann einlesen.
  let u;
  try { u = await api("/api/wurzeln/uebersicht", { method: "POST", body: { pfad } }); } catch (e) { return toast(e.message); }
  const frage = await dialog(u.modelle
    ? `<h2>Ordner einlesen?</h2><p><code>${esc(u.pfad)}</code></p>
      <p><b>${u.vollstaendig ? "" : "Über "}${anzahl(u.modelle)} ${u.modelle === 1 ? "Modelldatei" : "Modelldateien"}</b>: ${formatListe(u.je_format)}</p>
      <p class="dim">Die Dateien bleiben, wo sie sind. Während des Einlesens siehst du, wie weit es ist.</p>
      <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Einlesen</button></div>`
    : `<h2>Ordner ohne Modelle</h2><p>In diesem Ordner liegen keine Modelldateien (3MF, STL, OBJ, STEP, FCStd).</p>
      <p class="dim">${esc(u.pfad)}</p>
      <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf" value="ja">Trotzdem hinzufügen</button></div>`);
  if (frage !== "ja") return;
  try {
    const r = await api("/api/wurzeln", { method: "POST", body: { pfad } });
    zustand.hatWurzeln = true;
    zeichneLeer();
    ladeSeite();
    einlesenGestartet(r.lauf);
  } catch (e) { toast(e.message); }
}

// Rückfall, wenn der Rechner keinen Ordnerdialog hat: Sprungziele links, Unterordner
// zum Hineinklicken, unten wie viele Modelldateien darin liegen.
const ow = { pfad: null };
async function ordnerWaehler() {
  const fertig = dialog(`<h2>Wurzelordner hinzufügen</h2>
    <p class="dim">Wird rekursiv gescannt; versteckte Ordner (.name) bleiben aussen vor.</p>
    <div id="ow" class="ow"><div class="dim">Lade …</div></div>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja" id="ow-ok" disabled>Diesen Ordner hinzufügen</button></div>`);
  $("#dialog").classList.add("breit");
  owLaden(null);
  const a = await fertig;
  $("#dialog").classList.remove("breit");
  return a === "ja" ? ow.pfad : null;
}

async function owLaden(pfad) {
  let d;
  try { d = await api("/api/durchsuchen" + (pfad ? "?pfad=" + encodeURIComponent(pfad) : "")); }
  catch (e) { return toast(e.message); }
  ow.pfad = d.pfad;
  const anzahl = d.modelle === null ? `<span class="dim">Wähle den Ordner, in dem deine Modelle liegen.</span>`
    : d.modelle ? `<b>${d.vollstaendig ? "" : "mehr als "}${d.modelle.toLocaleString("de-DE")} Modelldateien</b> in diesem Ordner und seinen Unterordnern`
    : `<span class="dim">Keine Modelldateien in diesem Ordner.</span>`;
  $("#ow").innerHTML = `<div class="ow-grid">
      <div class="ow-ziele">${d.sprungziele.map((z) => `<button type="button" class="${z.pfad === d.pfad ? "an" : ""}" data-ow-pfad="${esc(z.pfad)}">
        ${z.art === "home" ? "🏠" : z.art === "laufwerk" ? "💽" : "📁"} ${esc(z.name)}</button>`).join("")}</div>
      <div class="ow-liste">
        <div class="ow-pfad">${d.eltern ? `<button type="button" class="knopf klein" data-ow-pfad="${esc(d.eltern)}" title="Übergeordneter Ordner">⬆</button>` : ""}<code>${esc(d.pfad)}</code></div>
        <div class="ow-ordner">${d.ordner.map((o) => `<button type="button" data-ow-pfad="${esc(o.pfad)}">📁 ${esc(o.name)}</button>`).join("") || '<div class="dim">Keine Unterordner.</div>'}</div>
      </div></div>
    <div class="ow-fuss">${anzahl}</div>`;
  $("#ow-ok").disabled = d.modelle === null;     // Wurzelverzeichnis und Systemordner lassen sich nicht hinzufügen
}

document.addEventListener("click", (e) => {
  const z = e.target.closest?.("[data-ow-pfad]");
  if (z) return owLaden(z.dataset.owPfad);
});

// ---------------------------------------------------------------- Ereignisse

document.addEventListener("click", async (e) => {
  const t = e.target;
  const wahl = t.closest("[data-wahl]");
  if (wahl) { e.stopPropagation(); return waehleAus(wahl.dataset.wahl, e.shiftKey); }
  const gw = t.closest("[data-gruppe-wahl]");
  if (gw) {
    e.stopPropagation();
    const g = zustand.gruppen.find((x) => x.key === gw.dataset.gruppeWahl);
    if (g) {
      const ids = zustand.modelle.slice(g.start, g.start + g.n).map((m) => m.id);
      const alle = ids.every((id) => zustand.auswahl.has(id));
      ids.forEach((id) => (alle ? zustand.auswahl.delete(id) : zustand.auswahl.add(id)));
      zeichneStapel();
      raster.zeichne();
    }
    return;
  }
  const pf = t.closest("[data-pfad]");
  if (pf) { Object.assign(zustand, { ordner: pf.dataset.pfad, ansicht: "alle", sammlung: "", eingeklappt: new Set() }); return neuLaden(); }
  const go = t.closest("[data-gruppe-ordner]");
  if (go) {
    const id = go.dataset.gruppeOrdner;
    // Die Seitenleiste zeigt den Weg dorthin offen.
    const teile = id.split("/");
    for (let i = 1; i < teile.length; i++) zustand.offen.add(teile.slice(0, i).join("/"));
    localStorageSchreiben("offen", JSON.stringify([...zustand.offen]));
    Object.assign(zustand, { ordner: id, ansicht: "alle", sammlung: "", eingeklappt: new Set() });
    return neuLaden();
  }
  const gk = t.closest("[data-gruppe]");
  if (gk) {
    const key = gk.dataset.gruppe;
    if (zustand.eingeklappt.has(key)) zustand.eingeklappt.delete(key); else zustand.eingeklappt.add(key);
    return raster.neu();
  }
  if (t.closest("[data-hv-einrichten]")) {
    e.stopImmediatePropagation();
    localStorageSchreiben("einstellungen-abschnitt", "programme");
    return einstellungen();
  }
  const hv = t.closest("[data-hv]");
  if (hv) { e.stopImmediatePropagation(); return modellOeffnen({ pfad: hv.dataset.hv }, hv.dataset.hvId); }
  const st = t.closest("[data-stapel]");
  if (st) return stapelAktion(st.dataset.stapel, undefined, st);
  const lay = t.closest("[data-layout]");
  if (lay) {
    zustand.layout = lay.dataset.layout;
    localStorageSchreiben("layout", zustand.layout);
    document.querySelectorAll("[data-layout]").forEach((b) => b.classList.toggle("an", b.dataset.layout === zustand.layout));
$("#gruppierung").value = zustand.gruppierung;
    $("#raster").scrollTop = 0;
    return raster.neu();
  }
  const sort = t.closest("[data-sortiere]");
  if (sort) { zustand.sortierung = sort.dataset.sortiere; $("#sortierung").value = zustand.sortierung; return ladeModelle(); }
  const zeileListe = t.closest(".zeile-l, .zeile-k");
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
  if (ansicht) return navigiere(() => { Object.assign(zustand, { ansicht: ansicht.dataset.ansicht, ordner: "", tags: new Set(), material: new Set(), format: "", sammlung: "" }); return neuLaden(); });
  const rail = t.closest("[data-rail]");
  if (rail) return navigiere(() => { Object.assign(zustand, { ansicht: rail.dataset.rail === "bereinigen" ? "papierkorb" : "alle", ordner: "", tags: new Set(), material: new Set(), format: "", sammlung: "" }); return neuLaden(); });
  const ordner = t.closest("[data-ordner]");
  if (ordner) return navigiere(() => { Object.assign(zustand, { ordner: ordner.dataset.ordner, ansicht: "alle", sammlung: "" }); return neuLaden(); });
  const sammlung = t.closest("[data-sammlung]");
  if (sammlung) return navigiere(() => { Object.assign(zustand, { sammlung: sammlung.dataset.sammlung, ansicht: "alle", ordner: "", tags: new Set(), material: new Set(), format: "" }); return neuLaden(); });
  const springe = t.closest("[data-springe]");
  if (springe) return springeZu(springe.dataset.springe, springe.dataset.id);
  const geheReiter = t.closest("[data-gehe-reiter]");
  if (geheReiter) return reiterWaehlen(geheReiter.dataset.geheReiter);
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
    if (!wert) { zustand.tags.clear(); zustand.material.clear(); zustand.format = ""; }
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
    case "entwuerfe-aus":
      zustand.ohneEntwuerfe = !zustand.ohneEntwuerfe;
      localStorageSchreiben("ohneEntwuerfe", zustand.ohneEntwuerfe ? "1" : "0");
      return ladeModelle();
    case "filter-weg": Object.assign(zustand, { ordner: "", tags: new Set(), material: new Set(), format: "", suche: "", sammlung: "", ansicht: "alle" }); $("#suche").value = ""; $("#suche-x").hidden = true; return neuLaden();
    case "sammlung-neu": case "sammlung-neu-2": return sammlungNeu([]);
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
    case "wurzel-neu": case "wurzel-neu-2": case "wurzel-neu-3": return wurzelNeu();
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
    case "neu-einlesen-2": {
      $("#import-menu").hidden = true;
      const r = await api("/api/scan", { method: "POST" });
      return einlesenGestartet(r.lauf);
    }
    case "gedruckt": {
      // Mit Drucken führt der Knopf zu ihnen; ohne legt er einen leeren an.
      const m = zustand.modelle.find((x) => x.id === id);
      if (m && m.drucke_n) return reiterWaehlen("drucke");
      await aendern(id, { gedruckt: true });
      return waehle(id);
    }
    case "favorit": { const m = zustand.modelle.find((x) => x.id === id); await aendern(id, { favorit: !(m && m.favorit) }); return waehle(id); }
    case "entwurf": { const m = await api(`/api/modelle/${id}`); await aendern(id, { entwurf: !m.entwurf }); return waehle(id); }
    case "oeffnen": { const k = $("#oeffnen"); return modellOeffnen(k.dataset.system ? { system: true } : { pfad: k.dataset.oeffnePfad }); }
    case "mehr-knopf": $("#mehr-menu").hidden = !$("#mehr-menu").hidden; return;
    case "gal-plus-menu": $("#mehr-menu").hidden = true; return $("#bild-wahl").click();
    case "umbenennen": return umbenennen(id);
    case "loeschen": return loeschen(id);
    case "wiederherstellen":
      try { await api(`/api/modelle/${id}/wiederherstellen`, { method: "POST" }); toast("Wiederhergestellt."); waehle(null); }
      catch (e2) { toast(e2.message); }
      return;
    case "endgueltig": return endgueltigEntfernen(id);
    case "datei-suchen": return dateiSuchen();
    case "fehlt-entfernen": return loeschen(id);
    case "ohne-datei": case "ohne-datei-aus":
      // Die Markierung steht am Datei-Knoten; die Live-Meldung zeichnet nur die Liste neu, der Inspektor folgt hier.
      try { await api(`/api/modelle/${id}/ohne_datei`, { method: "POST", body: { an: t.id === "ohne-datei" } }); waehle(id); }
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
  if (e.target.id === "bild-wahl" && e.target.files.length) {
    const dateien = [...e.target.files];
    e.target.value = "";
    return bilderHochladen(dateien);
  }
  if (e.target.id === "sortierung") { zustand.sortierung = e.target.value; ladeModelle(); }
  if (e.target.id === "gruppierung") {
    zustand.gruppierung = e.target.value;
    zustand.eingeklappt.clear();
    localStorageSchreiben("gruppierung", zustand.gruppierung);
    ladeModelle();
  }
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
  $("#suche-x").hidden = !e.target.value;
  clearTimeout(suchZeit);
  suchZeit = setTimeout(() => { zustand.suche = e.target.value.trim(); ladeModelle(); }, 150);
});

function sucheLeeren() {
  const s = $("#suche");
  s.value = "";
  s.dispatchEvent(new Event("input"));
  s.focus();
}
$("#suche-x").addEventListener("click", sucheLeeren);
$("#suche").addEventListener("keydown", (e) => { if (e.key === "Escape" && e.target.value) { e.preventDefault(); sucheLeeren(); } });

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
  const k = e.target.closest?.(".karte, .zeile-l, .zeile-k"), w = e.target.closest?.("[data-ws]");
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

// ---------------------------------------------------------------- Einlesen: der Knopf ⟳ bei „Bibliothek“ (KONZEPT §3.4)
//
// Kein Fenster: der Knopf dreht sich, neben „Bibliothek“ steht „liest ein …“, den Fortschritt zeigt die kleine Anzeige unten links.
// Am Ende eine kurze Meldung („3 neue Modelle“, mit „Zeigen“); das Ergebnis bleibt neben „Bibliothek“ stehen. Vorher wartete ein Fenster
// über allem auf das Ende genau eines Laufs — blieb diese Meldung aus (Fehler, Verbindungslücke), stand die ganze Oberfläche.

const FORMATNAME = { stl: "STL", "3mf": "3MF", obj: "OBJ", step: "STEP", fcstd: "FCStd" };
const anzahl = (n) => Number(n || 0).toLocaleString("de-DE");
const formatListe = (je) => Object.entries(je || {}).sort((a, b) => b[1] - a[1])
  .map(([f, n]) => `${anzahl(n)} ${FORMATNAME[f] || f.toUpperCase()}`).join(" · ");
const sekunden = (s) => (s == null ? "" : s < 1 ? "unter 1 s" : s < 60 ? `${zahl(s, 1)} s` : `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`);
// stopp: Hochladen abbrechen. erwartet/seit: der Lauf, den ein Klick eben angestossen hat. gemeldet: der letzte Lauf, dessen Ende schon
// gemeldet ist (null = noch unbekannt, beim ersten Stand vom Server gesetzt). ergebnis/titel: was neben „Bibliothek“ stehen bleibt.
const einlesen = { erwartet: 0, seit: 0, gemeldet: null, ergebnis: "", titel: "" };

// Das Einlesen eines Laufs ist vorbei, sobald `einlesen_s` steht — danach rechnet derselbe Lauf nur noch Vorschaubilder und FreeCAD.
const einlesenVorbei = (m) => !m.nur_cad && (m.einlesen_s != null || m.phase === "fehler" || !!m.abgebrochen || (!m.laeuft && m.phase === "fertig"));
const liestEin = (m) => !!(m.laeuft && !m.nur_cad && m.einlesen_s == null);
// Gleich nach dem Klick drehen, nicht erst mit der ersten Meldung des Servers — aber höchstens kurz ohne Bestätigung von ihm.
const einlesenAngestossen = (m) => einlesen.erwartet > (m.lauf || 0) && Date.now() - einlesen.seit < 3000;

function einlesenGestartet(lauf) {
  if (!lauf) return;
  einlesen.erwartet = Math.max(einlesen.erwartet, lauf);
  einlesen.seit = Date.now();
  einlesenZeichnen(zustand.scan || {});
  setTimeout(() => einlesenZeichnen(zustand.scan || {}), 3100);
}

function einlesenZeichnen(m) {
  const dreht = liestEin(m) || einlesenAngestossen(m);
  const knopf = $("#neu-einlesen-2");
  knopf.classList.toggle("dreht", dreht);
  knopf.title = dreht ? "Liest ein …" : "Alle Ordner neu einlesen";
  const lauf = m.lauf || 0;
  if (einlesen.gemeldet == null) einlesen.gemeldet = einlesenVorbei(m) ? lauf : lauf - 1;      // ein Ergebnis von vor dem Laden nicht melden
  if (einlesenVorbei(m)) {
    einlesen.ergebnis = m.phase === "fehler" ? "gescheitert" : m.abgebrochen ? "abgebrochen"
      : m.neu ? `${anzahl(m.neu)} neu` : m.geaendert ? `${anzahl(m.geaendert)} geändert` : "nichts Neues";
    einlesen.titel = scanErgebnis(m);
    if (lauf > einlesen.gemeldet) {
      einlesen.gemeldet = lauf;
      einlesenMelden(m);
      if (scanHatVeraendert(m)) neuLaden();       // die neuen Kacheln jetzt, nicht erst nach Vorschaubildern und FreeCAD
    }
  }
  zuletztZeigen();
}

// Eine Meldung, die von selbst verschwindet. Was zu tun bleibt, hat einen Knopf dorthin.
function einlesenMelden(m) {
  if (m.phase === "fehler") return toast(`Einlesen gescheitert: ${m.abbruch || "unbekannter Fehler"}. Was schon eingelesen war, bleibt im Katalog.`, { dauer: 10000 });
  if (m.abgebrochen) return toast("Einlesen abgebrochen. Was schon eingelesen war, bleibt im Katalog.");
  const modelle = (n) => `${anzahl(n)} ${n === 1 ? "Modell" : "Modelle"}`;
  const teile = [m.neu ? `${anzahl(m.neu)} ${m.neu === 1 ? "neues Modell" : "neue Modelle"}`
    : m.geaendert ? `${modelle(m.geaendert)} geändert` : `Nichts Neues – ${anzahl(m.gefunden)} Dateien geprüft`];
  const ziele = [];
  if (m.neu) ziele.push(["Zeigen", "neu"]);
  if (m.neu && m.geaendert) teile.push(`${anzahl(m.geaendert)} geändert`);
  if (m.verschoben) teile.push(`${anzahl(m.verschoben)} an neuem Ort`);
  if (m.zurueckgeholt) teile.push(`${anzahl(m.zurueckgeholt)} aus dem Papierkorb zurück`);
  if (m.aufgeraeumt) teile.push(`${anzahl(m.aufgeraeumt)} ${m.aufgeraeumt === 1 ? "Entwurf" : "Entwürfe"} aufgeräumt (Datei gelöscht)`);
  const weg = (m.entfernt || 0) - (m.aufgeraeumt || 0);
  if (weg > 0) { teile.push(`${anzahl(weg)} nicht mehr da`); ziele.push(["Datei fehlt", "fehlt"]); }
  if (m.unlesbar) { teile.push(`${anzahl(m.unlesbar)} unlesbar`); ziele.push(["Unlesbar", "unlesbar"]); }
  if (m.kopien) { teile.push(`${anzahl(m.kopien)} ${m.kopien === 1 ? "Kopie" : "Kopien"} mit gleichem Inhalt`); ziele.push(["Duplikate", "duplikate"]); }
  if (m.nicht_erreichbar?.length) teile.push(`nicht erreichbar: ${m.nicht_erreichbar.join(", ")} (nichts als fehlend markiert)`);
  toast(teile.join(" · "), { dauer: teile.length > 1 || ziele.length > 1 ? 9000 : 4500,
                aktionen: ziele.map(([was, ansicht]) => [was, () => document.querySelector(`[data-ansicht="${ansicht}"]`)?.click()]) });
}

// Klein beim Zahnrad: ein Balken, darüber in Worten, was gerade passiert. Keine Schritte (Einlesen und Hintergrund zählten getrennt:
// „1 von 2“, dann „1 von 3“ — verwirrend). Weg, sobald nichts mehr läuft.
// Restzeit aus dem bisherigen Tempo dieser Phase. Erst nach einer Weile und ein paar Dateien: vorher wäre es geraten.
function restzeit(fertig, gesamt, sek) {
  if (!(fertig >= 10 && sek >= 20 && gesamt > fertig)) return "";
  const rest = (gesamt - fertig) * sek / fertig;
  if (rest < 60) return "noch unter 1 min";
  if (rest < 3600) return `noch etwa ${Math.round(rest / 60)} min`;
  const h = Math.floor(rest / 3600), min = Math.round((rest % 3600) / 300) * 5;
  return min >= 60 ? `noch etwa ${h + 1} h` : `noch etwa ${h} h${min ? ` ${min} min` : ""}`;
}

function hintergrundZeichnen() {
  const h = $("#hintergrund");
  // Das Einlesen geht vor (kurz, der Anwender wartet darauf); läuft es nicht, die Hintergrundarbeit.
  const art = zustand.scan?.laeuft ? "scan" : zustand.worker?.laeuft ? "worker" : null;
  const m = art ? zustand[art] : {};
  if (!art) { h.hidden = true; return; }
  let text, fertig = null, gesamt = null;
  if (m.abbricht) text = "Wird abgebrochen …";
  else if (m.phase === "suchen") text = "Ordner durchsuchen";
  else if (m.phase === "hashen") { text = "Datenbank aufbauen"; [fertig, gesamt] = [m.geprueft, m.zu_pruefen]; }
  else if (m.phase === "auslesen") { text = "Daten auslesen"; [fertig, gesamt] = [m.ausgelesen, m.zu_auslesen]; }
  else if (m.phase === "vorschau") { text = "Vorschaubilder erzeugen"; [fertig, gesamt] = [(m.vorschauen_gesamt || 0) - (m.vorschauen_offen || 0), m.vorschauen_gesamt]; }
  else if (m.phase === "thumbs") { text = "Kleine Bilder erzeugen"; [fertig, gesamt] = [m.thumbs_fertig, m.thumbs_gesamt]; }
  else if (m.phase === "cad") { text = "FreeCAD-Dateien umwandeln"; [fertig, gesamt] = [(m.cad_gesamt || 0) - (m.cad_offen || 0), m.cad_gesamt]; }
  else text = "Läuft …";
  const anteil = gesamt ? fertig / gesamt : null;
  const rest = m.abbricht ? "" : restzeit(fertig, gesamt, m.phase_s || 0);
  h.hidden = false;
  abgleichen(h, `<div class="hg-kopf"><span>${text}</span>${gesamt ? `<span class="hg-zahl">${anzahl(fertig)} / ${anzahl(gesamt)}</span>` : ""}</div>
    <div class="balken klein ${anteil == null ? "unbestimmt" : ""}"><i style="width:${Math.round((anteil ?? 0.3) * 100)}%"></i></div>
    ${rest ? `<div class="hg-zeile dim">${rest}</div>` : ""}`);
}

// ---------------------------------------------------------------- Live (flatgraph bei_aenderung → SSE)

// „Zuletzt eingelesen: vor 3 Std.“ neben „Bibliothek“. Der Zeitpunkt kommt vom Server (/api/stand und die Meldung am Ende eines Einlesens).
function vorZeit(iso, jetzt = Date.now()) {
  const s = Math.max(0, Math.round((jetzt - new Date(iso).getTime()) / 1000));
  if (s < 60) return "gerade eben";
  if (s < 3600) return `vor ${Math.floor(s / 60)} Min.`;
  if (s < 86400) return `vor ${Math.floor(s / 3600)} Std.`;
  const t = Math.floor(s / 86400);
  return `vor ${t} ${t === 1 ? "Tag" : "Tagen"}`;
}
let zuletztEingelesen = null;
function zuletztZeigen(iso) {
  if (iso) zuletztEingelesen = iso;
  const el = $("#zuletzt-eingelesen");
  if (!el) return;
  const m = zustand.scan || {};
  if (liestEin(m) || einlesenAngestossen(m)) { el.textContent = "liest ein …"; el.title = ""; return; }
  if (!zuletztEingelesen) { el.textContent = einlesen.ergebnis === "gescheitert" ? "gescheitert" : ""; el.title = einlesen.titel; return; }
  el.textContent = vorZeit(zuletztEingelesen) + (einlesen.ergebnis ? ` · ${einlesen.ergebnis}` : "");
  el.title = [`Zuletzt eingelesen: ${new Date(zuletztEingelesen).toLocaleString("de-DE")}`, einlesen.titel].filter(Boolean).join("\n");
}
setInterval(zuletztZeigen, 60000);

let liveZeit = null, liveBetrifft = false;
let LIVE_SCAN_MS = 5000, letztesLiveLaden = 0;       // während eines Einlesens höchstens so oft die Liste neu holen

// Hat das Einlesen etwas verändert, das in der Liste steht? Sonst ist das Neuladen am Ende überflüssig: ein Einlesen ohne Funde schreibt
// nichts (gemessen: 0 Änderungsmeldungen), und die Liste ist schon aktuell. Bei 9 000 Modellen auf einem älteren Rechner sind das Sekunden.
const scanHatVeraendert = (m) => !!(m.neu || m.geaendert || m.verschoben || m.entfernt || m.zurueckgeholt || m.aufgeraeumt
  || m.abgebrochen || !zustand.modelle.length);
// Läuft gerade etwas — Einlesen oder Hintergrundarbeit? Dann kommen viele Änderungen kurz hintereinander.
const etwasLaeuft = () => !!(zustand.scan?.laeuft || zustand.worker?.laeuft);
function abbrechenZeigen() {
  const s = zustand.scan || {}, w = zustand.worker || {};
  $("#scan-abbrechen").hidden = !((s.laeuft && !s.abbricht) || (w.laeuft && !w.abbricht));
}

function liveScan(m) {
  const vorher = zustand.scan || {};
  zustand.scan = m;
  if (m.zuletzt_eingelesen) zuletztEingelesen = m.zuletzt_eingelesen;
  einlesenZeichnen(m);
  hintergrundZeichnen();
  if (!zustand.modelle.length) zeichneLeer();
  abbrechenZeigen();
  if (m.fcstd_frage && !zustand.fcstdGefragt) { zustand.fcstdGefragt = true; fcstdFrage(m.fcstd_frage); }
}

// Der Worker (Vorschaubilder, kleine Bilder, FreeCAD) meldet sich getrennt vom Einlesen und läuft neben ihm.
function liveWorker(m) {
  const vorher = zustand.worker || {};
  zustand.worker = m;
  hintergrundZeichnen();
  abbrechenZeigen();
  if (m.fcstd_frage && !zustand.fcstdGefragt) { zustand.fcstdGefragt = true; fcstdFrage(m.fcstd_frage); }
  // Am Ende der Runde einmal alles neu, was sich dabei nur Kachel für Kachel geändert hat (etwa die Sortierung nach Grösse).
  if (vorher.laeuft && !m.laeuft && (m.vorschauen_gesamt || m.cad_gesamt)) neuLaden();
}

// Während etwas läuft, ändern sich laufend einzelne Modelle: neue kommen dazu, Vorschaubilder und Werte werden fertig. Dafür nie die
// ganze Liste holen (bei 9 000 Modellen Sekunden, auf dem Server wie im Browser, und jedes Mal überholt), sondern die Verweise aus den
// Live-Meldungen sammeln und jede halbe Sekunde nur diese Modelle nachreichen: fertige Kacheln werden an Ort und Stelle ausgetauscht,
// neue eingefügt — in jeder Ansicht, ohne dass man sie wechseln muss (KONZEPT §3.4). Ansichten mit eigener Reihenfolge oder Auswahl
// (Neu, Warteschlange, Sammlung, Papierkorb, Baugruppe) laden weiter ganz, sie sind klein.
const nach = { refs: new Set(), zeit: null, unterwegs: false, seite: 0 };
const nachreichbar = () => !zustand.sammlung && !zustand.baugruppe && !["neu", "warteschlange", "papierkorb", "aufraeumen"].includes(zustand.ansicht);
// Was eine Kachel an eine andere Stelle bringt oder in eine andere Gruppe: dann Liste neu ordnen, sonst nur austauschen.
const lage = (x) => JSON.stringify([x.name, x.gewicht_g, x.masse, x.angelegt, x.entwurf, x.format, x.material, x.ordner, x.fehlt, x.fehler, x.drucke_n, x.gedruckt]);

function nachreichenPlanen(m) {
  for (const r of [m.ref, m.quelle, m.ziel]) if (r && /^(MODEL_ASSET|PART_GEOMETRY)\//.test(r)) nach.refs.add(r);
  if (nach.refs.size && !nach.zeit && !nach.unterwegs) nach.zeit = setTimeout(nachreichen, 500);
}

async function nachreichen() {
  nach.zeit = null;
  if (!nach.refs.size) return;
  // Eine ganze Liste ist unterwegs: danach. Sie zeigt den Stand von ihrem Beginn; was seitdem kam, reichen wir dann nach.
  if (ladeModelle.unterwegs) { nach.zeit = setTimeout(nachreichen, 500); return; }
  const refs = [...nach.refs];
  nach.refs.clear();
  nach.unterwegs = true;
  const nr = ladeModelle.nr;
  let r = null;
  try { r = await api("/api/modelle/aenderungen", { method: "POST", body: { refs, filter: filterJetzt() } }); }
  catch { refs.forEach((x) => nach.refs.add(x)); }           // später noch einmal
  finally {
    nach.unterwegs = false;
    if (nach.refs.size && !nach.zeit) nach.zeit = setTimeout(nachreichen, r ? 500 : 3000);
  }
  if (!r || nr !== ladeModelle.nr || !zustand.roh) return;   // inzwischen eine andere Ansicht gewählt: ihre Liste ist frischer
  const pos = new Map(zustand.roh.map((x, i) => [x.id, i]));
  const weg = new Set(r.weg);
  let ordnen = false;
  const getauscht = [];
  for (const k of r.modelle) {
    const i = pos.get(k.id);
    if (i == null) { zustand.roh.push(k); ordnen = true; continue; }
    if (lage(zustand.roh[i]) !== lage(k)) ordnen = true;
    zustand.roh[i] = k;
    getauscht.push(k);
  }
  if ([...weg].some((id) => pos.has(id))) { zustand.roh = zustand.roh.filter((x) => !weg.has(x.id)); ordnen = true; }
  if (ordnen) {
    // Die Kachel oben im Bild bleibt, wo sie ist: neue Modelle weiter oben schieben die Ansicht nicht weg.
    const anker = raster.anker();
    sortiere(zustand.roh, true);
    listeAnwenden();
    raster.anker(anker);
    seiteNachladen();
  } else {
    for (const k of getauscht) { const i = zustand.idIndex.get(k.id); if (i != null) zustand.modelle[i] = k; }
    raster.zeichne();
  }
  const ids = new Set(r.modelle.map((x) => x.id));
  if (zustand.gewaehlt && ids.has(zustand.gewaehlt)) waehle(zustand.gewaehlt, true);
}

// Ordnerbaum und Zähler links: während des Einlesens höchstens alle 5 s, nie zwei gleichzeitig.
function seiteNachladen() {
  if (nach.seite) return;
  nach.seite = setTimeout(async () => { try { await ladeSeite(); } finally { nach.seite = 0; } }, 5000);
}

function liveAenderung(m) {
  if (etwasLaeuft() && nachreichbar() && zustand.roh) return nachreichenPlanen(m);
  const meins = zustand.gewaehlt && [m.ref, m.quelle, m.ziel].includes(`MODEL_ASSET/${zustand.gewaehlt}`);
  if (meins) liveBetrifft = true;
  const feuern = () => {
    liveZeit = null;
    // Ist noch eine Liste unterwegs, wartet das Nachladen auf sie. Sonst überholte bei grossen Katalogen (Liste dauert länger als
    // LIVE_SCAN_MS) jedes Nachladen das vorige: alle Antworten verworfen, die Liste blieb stehen, und Klicks auf Filter gingen mit unter.
    if (ladeModelle.unterwegs) { ladeModelle.danach = feuern; return; }
    letztesLiveLaden = Date.now();
    neuLaden();
    if (liveBetrifft && zustand.gewaehlt) waehle(zustand.gewaehlt, true);
    liveBetrifft = false;
  };
  if (etwasLaeuft()) {
    // Beim Einlesen kommt fast jede Sekunde eine Änderung (FreeCAD, Vorschauen). Jedes Mal die ganze Liste holen und zeichnen hielte den
    // Rechner dauernd beschäftigt, auch den Server (er baut die Kacheln nach jeder Änderung neu). Stattdessen höchstens alle LIVE_SCAN_MS einmal.
    // Die erste Änderung nach einer Ruhepause lädt sofort (ein kleiner Import zeigt seine Modelle gleich); danach höchstens alle LIVE_SCAN_MS.
    if (liveZeit === null) liveZeit = setTimeout(feuern, Math.max(0, LIVE_SCAN_MS - (Date.now() - letztesLiveLaden)));
    return;
  }
  // Sonst: viele Änderungen hintereinander sammeln, dann einmal laden.
  clearTimeout(liveZeit);
  liveZeit = setTimeout(feuern, 300);
}

function live() {
  const q = new EventSource("/api/live");
  let verbunden = 0;
  q.onopen = () => {
    // Der Server schickt zuerst den ganzen Stand. Was in der Lücke geschah (oder ob der Server neu gestartet ist), steht darin — ein Ende,
    // das in die Lücke fiel, wird nicht nachgemeldet, steht aber neben „Bibliothek“.
    einlesen.gemeldet = null;
    if (verbunden++) neuLaden();
  };
  q.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.art === "scan") return liveScan(m);
    if (m.art === "worker") return liveWorker(m);
    if (m.art === "neu_laden") { nach.refs.clear(); return neuLaden(); }    // zu viele Meldungen verpasst: alles neu
    liveAenderung(m);
  };
}

document.documentElement.dataset.app = localStorageLesen("thema") || "dark";
neuLaden();
programmeAktualisieren();
$("#scan-abbrechen").onclick = async () => {
  $("#scan-abbrechen").hidden = true;
  try { await api("/api/scan/abbrechen", { method: "POST" }); } catch (err) { toast(err.message); }
};
api("/api/stand").then((s) => { $("#version").textContent = s.version || ""; zuletztZeigen(s.zuletzt_eingelesen); if (s.version) document.title = `partAtlas ${s.version}`; if (s.scan) zustand.scan = { ...s.scan, ...(zustand.scan || {}) }; if (s.worker) zustand.worker = { ...s.worker, ...(zustand.worker || {}) }; hintergrundZeichnen(); abbrechenZeigen(); if (s.scan?.fcstd_frage && !zustand.fcstdGefragt) { zustand.fcstdGefragt = true; fcstdFrage(s.scan.fcstd_frage); } if (s.scan) einlesenZeichnen(zustand.scan); }).catch(() => {});
live();
try { nav.nr = history.state?.nr ?? 0; nav.hoechste = nav.nr; history.replaceState(momentaufnahme(), ""); } catch { /* s. o. */ }
$("#nav-zurueck")?.addEventListener("click", () => history.back());
$("#nav-vor")?.addEventListener("click", () => history.forward());
navKnoepfe();

// Aus dem Dateimanager ins Fenster gezogen: nur Bilder auf Vorschau oder Druck. Modelle und Ordner kommen allein über
// Importieren › Ordner hinzufügen (KONZEPT §3.4) — anderswo abgelegt geschieht nichts, auch kein Öffnen der Datei im Browser.
// Ein Bild aus der eigenen Leiste hat Dateityp „Files“, kommt aber nicht von
// aussen — sonst entstünde vom Original eine Kopie als eigenes Bild.
let vonGalerie = false;
document.addEventListener("dragstart", (e) => { vonGalerie = !!e.target.closest?.("#i-galerie"); }, true);
document.addEventListener("dragend", () => { vonGalerie = false; }, true);
const vonAussen = (e) => !gezogen && !vonGalerie && [...(e.dataTransfer?.types || [])].includes("Files");
// Bilder auf einen Druck (Foto dazu) oder auf den leeren Teil des Reiters „Drucke“ (neuer Druck mit Foto).
const druckZiel = (e) => (!galerie.m || galerie.m.papierkorb ? null : e.target.closest?.(".druck, .i-tafel[data-reiter='drucke']"));
const aufGalerie = (e) => !!(e.target.closest?.("#i-galerie") && galerie.m && !galerie.m.papierkorb);
const abwurfAufraeumen = () => document.querySelectorAll(".abwurf-ziel, .druck-ziel").forEach((x) => x.classList.remove("abwurf-ziel", "druck-ziel"));
window.addEventListener("dragleave", (e) => { if (vonAussen(e)) abwurfAufraeumen(); });
window.addEventListener("dragover", (e) => {
  if (!vonAussen(e)) return;
  e.preventDefault();
  const gal = aufGalerie(e), dz = gal ? null : druckZiel(e);
  abwurfAufraeumen();
  if (gal) $("#i-galerie")?.classList.add("abwurf-ziel");
  if (dz) dz.classList.add("druck-ziel");
  e.dataTransfer.dropEffect = gal || dz ? "copy" : "none";
});
window.addEventListener("drop", (e) => {
  if (!vonAussen(e)) return;
  e.preventDefault();
  const dz = druckZiel(e);
  abwurfAufraeumen();
  if (aufGalerie(e)) return bilderHochladen(e.dataTransfer.files);
  if (dz) return druckBilderAblegen(dz.closest(".druck")?.dataset.druck || null, e.dataTransfer.files);
});
document.querySelectorAll("[data-layout]").forEach((b) => b.classList.toggle("an", b.dataset.layout === zustand.layout));

// Datei-Details auf- oder zugeklappt lassen, wie man es zuletzt wollte.
document.addEventListener("toggle", (e) => {
}, true);

function imInspektorAmTippen() {
  const a = document.activeElement;
  return !!(a && a.closest?.("#inspektor") && /^(INPUT|SELECT|TEXTAREA)$/.test(a.tagName));
}
document.addEventListener("focusout", (e) => {
  if (!e.target.closest?.("#inspektor") || !zustand.nachholen) return;
  // Erst nach dem Wechsel des Fokus prüfen: springt er ins nächste Feld, weiter warten.
  setTimeout(() => {
    if (zustand.nachholen && !imInspektorAmTippen() && zustand.gewaehlt) { zustand.nachholen = false; waehle(zustand.gewaehlt, true); }
  }, 0);
});

// ---------------------------------------------------------------- Abschnitte der Seitenleiste
//
// Einklappbar wie in VS Code; der Zustand bleibt je Abschnitt gemerkt. Beim
// Ziehen einer Kachel klappt ein zugeklappter Abschnitt auf, wenn man kurz
// über seiner Überschrift verweilt — so bleibt er Ablageziel.

function sektionSetzen(sek, zu) {
  sek.dataset.zu = zu ? "1" : "";
  localStorageSchreiben("sektion." + sek.dataset.sektion, zu ? "1" : "0");
}
document.querySelectorAll(".sektion").forEach((sek) => {
  if (sek.dataset.sektion === "ordner") return;     // die Bibliothek ist immer offen; zu klappen sind nur ihre Ordner
  const gemerkt = localStorageLesen("sektion." + sek.dataset.sektion);
  if (gemerkt != null) sek.dataset.zu = gemerkt === "1" ? "1" : "";
});
document.addEventListener("click", (e) => {
  const kopf = e.target.closest?.(".sk-kopf");
  if (kopf) { const sek = kopf.closest(".sektion"); sektionSetzen(sek, !sek.dataset.zu); }
});
let sekZiehZeit = null;
document.addEventListener("dragover", (e) => {
  const kopf = e.target.closest?.(".sektion[data-zu='1'] h3");
  if (!kopf) { clearTimeout(sekZiehZeit); sekZiehZeit = null; return; }
  if (!sekZiehZeit) sekZiehZeit = setTimeout(() => { sektionSetzen(kopf.closest(".sektion"), false); sekZiehZeit = null; }, 600);
});

// ---------------------------------------------------------------- Rechtsklick-Menü
//
// Wie im Dateimanager: Rechtsklick auf eine Kachel wählt sie (oder lässt
// die Auswahl stehen, wenn sie dazugehört) und zeigt, was man damit tun kann.
// Für mehrere gilt, was für mehrere Sinn ergibt.

async function kontextMenu(e, id) {
  e.preventDefault();
  const mehrere = zustand.auswahl.size > 1 && zustand.auswahl.has(id);
  const modelle = mehrere ? [...zustand.auswahl] : [id];
  if (!mehrere && zustand.gewaehlt !== id) waehle(id);
  const m = zustand.modelle.find((x) => x.id === id) || {};
  const papierkorb = zustand.ansicht === "papierkorb";
  let eintraege;
  if (papierkorb) {
    // Endgültig nur je Modell, nie für eine Auswahl: ein „alles leeren“ gibt es bewusst nicht.
    eintraege = [["wiederherstellen", `↩ Wiederherstellen${mehrere ? ` (${modelle.length})` : ""}`],
      ...(mehrere ? [] : [["-"], ["endgueltig", "Endgültig entfernen …", "gefahr"]])];
  } else if (mehrere) {
    eintraege = [
      ["kopf", `${modelle.length} Modelle`],
      ["warteschlange", "☰ In die Warteschlange"], ["druck", "🖨 Zusammen gedruckt …"], ["gedruckt", "✓ Als gedruckt markieren"], ["favorit", "♥ Favorit"], ["entwurf", "✎ Entwurf ein/aus"],
      ["-"], ["tag", "＃ Tag …"], ["material", "Material …"], ["baugruppe", "🧩 Zu Baugruppe …"], ["sammlung", "▤ Zu Sammlung …"],
      ["-"], ["verschieben", "In anderen Ordner verschieben …"], ["-"], ["loeschen", "Löschen …", "gefahr"]];
  } else {
    const prog = await ladeProgramme();
    const { je } = programmeFuer(m, prog);
    const da = !m.fehlt;
    const kein = { slicer: "Kein Slicer für dieses Format", cad: "Kein CAD-Programm für dieses Format" };
    const oeffnen = Object.keys(prog.arten).map((art) => {
      const liste = je[art];
      if (!liste.length) return ["einrichten", `${ART_SYMBOL[art] || "↗"} ${kein[art] || "Kein Programm"} — einrichten …`, "aus"];
      if (liste.length === 1) return ["oeffnen", `${ART_SYMBOL[art] || "↗"} In ${esc(liste[0].name)} öffnen`, "", liste[0].pfad];
      return ["unter", `${ART_SYMBOL[art] || "↗"} ${art === "slicer" ? "Im Slicer" : "Im CAD"} öffnen`, "",
        liste.map((p, i) => `<button data-km="oeffnen" data-pfad="${esc(p.pfad)}">${esc(p.name)}${i === 0 ? ' <small class="dim">Standard</small>' : ""}</button>`).join("")];
    });
    eintraege = [
      ...(da ? [...oeffnen, ["system", "↗ Mit dem System öffnen"], ["ordner", "📂 Im Ordner zeigen"], ["-"]] : []),
      ["ws", m.warteschlange != null ? "☰ Aus der Warteschlange" : "☰ In die Warteschlange"],
      ["druck1", "🖨 Druck anlegen …"],
      ["gedruckt1", m.gedruckt ? "○ Als nicht gedruckt markieren" : "✓ Als gedruckt markieren"],
      ["favorit1", m.favorit ? "♡ Kein Favorit mehr" : "♥ Favorit"],
      ["entwurf1", m.entwurf ? "✎ Kein Entwurf mehr" : "✎ Als Entwurf markieren"],
      ["-"], ["baugruppe", "🧩 Zu Baugruppe …"], ["sammlung", "▤ Zu Sammlung …"],
      ["-"], ["umbenennen", "Umbenennen …"], ["verschieben", "In anderen Ordner verschieben …"],
      ["-"], ["loeschen", "Löschen …", "gefahr"]];
  }
  eintraege = eintraege.filter(([k]) => ab2(k));
  const menu = $("#kontext");
  menu.innerHTML = eintraege.map(([k, t, kl, extra]) => k === "-" ? "<hr>" : k === "kopf" ? `<div class="km-kopf">${esc(t)}</div>`
    : k === "unter" ? `<div class="km-unter"><button type="button">${t}<span class="km-pfeil">▸</span></button><div class="menu km-flyout">${extra}</div></div>`
    : `<button data-km="${k}" class="${kl || ""}" ${extra ? `data-pfad="${esc(extra)}"` : ""}>${t}</button>`).join("");
  kontextMenu.ziel = { id, modelle, m };
  menu.hidden = false;
  // Im Fenster halten: am Rand nach links bzw. oben aufklappen.
  const b = menu.getBoundingClientRect();
  menu.style.left = Math.min(e.clientX, innerWidth - b.width - 6) + "px";
  menu.style.top = Math.min(e.clientY, innerHeight - b.height - 6) + "px";
  menu.classList.toggle("flyout-links", menu.getBoundingClientRect().right + 220 > innerWidth);
}

// FCStd über FreeCAD: ein Dokument kann Programmcode enthalten, der beim Laden läuft — deshalb nie ohne Zusage. Einmal je Sitzung
// gefragt; „Nicht jetzt“ fragt beim nächsten Start wieder, „Nie“ merkt sich die Antwort (Einstellungen › Einlesen).
async function fcstdFrage(n) {
  const a = await dialog(`<h2>FreeCAD-Dateien über FreeCAD einlesen?</h2>
    <p>${n} ${n === 1 ? "FreeCAD-Datei hat" : "FreeCAD-Dateien haben"} noch keine Maße, kein Gewicht und keine 3D-Ansicht. partAtlas kann
      sie dafür im Hintergrund in FreeCAD laden, ohne Fenster.</p>
    <p class="dim">Das Vorschaubild, das du vielleicht schon siehst, steckt in der Datei selbst (FreeCAD legt es beim Speichern hinein).
      partAtlas liest es nur aus — FreeCAD wurde dafür nicht gestartet.</p>
    <p><b>Wichtig:</b> Ein FreeCAD-Dokument kann Programmcode enthalten, der beim Laden ausgeführt wird. Das ist dasselbe, als würdest du die
      Datei in FreeCAD öffnen. Mach das nur für Dateien aus Quellen, denen du vertraust; bei heruntergeladenen Archiven aus dem Netz ist das
      Risiko höher als bei eigenen Konstruktionen.</p>
    <div class="knoepfe"><button class="knopf" value="nie">Nie</button><button class="knopf" value="nein">Nicht jetzt</button><button class="knopf akzent" value="ja">Ja, einlesen</button></div>`);
  if (a !== "ja" && a !== "nie") return;
  try {
    await api("/api/einstellungen", { method: "PUT", body: { fcstd_freecad: a === "ja" ? "ja" : "nein" } });
    if (a === "ja") { await api("/api/cad/starten", { method: "POST" }); toast("FCStd-Dateien werden über FreeCAD umgewandelt …"); }
  } catch (e) { toast(e.message); }
}

// Was mit der Umwandlung über FreeCAD ist — sonst sieht man bei einem CAD-Modell ohne Vorschau nie, woran es liegt.
function cadZeile(m) {
  if (m.format !== "step" && m.format !== "fcstd") return "";
  const sc = zustand.scan || {};
  let text, knopf = "";
  // Ein Bild aus der Datei ist eine Vorschau; was FreeCAD zusätzlich bringt, sind Maße, Gewicht und die 3D-Ansicht.
  const bild = m.ansichten?.some((a) => a.art === "extrahiert") ? "Die Vorschau ist das Bild, das in der Datei gespeichert ist. " : "";
  const zusatz = bild ? "Maße, Gewicht und 3D-Ansicht kommen mit FreeCAD" : "Vorschau, Maße und 3D-Ansicht kommen mit FreeCAD";
  if (m.cad === "ok") text = "Netz, Maße und Vorschau stammen aus FreeCAD.";
  else if (m.cad === "fehler") {
    text = `Die Umwandlung über FreeCAD ist gescheitert: <code>${esc(m.cad_fehler || "ohne Meldung")}</code>`;
    knopf = `<button class="knopf klein" data-cad-erneut>Alle gescheiterten erneut versuchen</button>`;
  } else if (sc.laeuft) text = "Wird gerade eingelesen …";
  else if (sc.cad_ohne_freecad) text = `${zusatz}, aber partAtlas hat beim letzten Einlesen keinen Aufruf von FreeCAD ermittelt${sc.cad_programm ? ` (erkannt: <code>${esc(sc.cad_programm)}</code>)` : " (kein CAD-Programm erkannt)"}. Einstellungen › Programme: CAD wählen.`;
  else if (m.format === "fcstd" && sc.fcstd_frage) text = `${zusatz}. partAtlas hat gefragt, ob FCStd-Dateien über FreeCAD eingelesen werden dürfen — noch keine Zusage (Einstellungen › Einlesen).`;
  else if (m.format === "fcstd") text = `${zusatz}, sobald du es erlaubst: FCStd-Dateien liest partAtlas nur nach deiner Zusage über FreeCAD (Einstellungen › Einlesen).`;
  else text = `${zusatz}; das geschieht beim nächsten Einlesen.`;
  return `<div class="i-titel">FREECAD</div><div class="i-karte"><div class="dim" style="padding:4px 0">${bild}${text}</div>${knopf}</div>`;
}
document.addEventListener("click", async (e) => {
  if (e.target.closest("[data-cad-erneut]")) {
    try { const r = await api("/api/cad/erneut", { method: "POST" }); toast(`${r.zurueckgesetzt} Datei${r.zurueckgesetzt === 1 ? "" : "en"} werden erneut versucht …`); }
    catch (err) { toast(err.message); }
  }
  if (e.target.closest("#ein-sichern")) {
    try { const r = await api("/api/sicherungen", { method: "POST" }); toast(`Gesichert: ${r.name}`); sicherungenZeigen(); } catch (err) { toast(err.message); }
  }
  if (e.target.closest("#ein-sicherungen-zeigen")) {
    try { await api("/api/sicherungen/zeigen", { method: "POST" }); } catch (err) { toast(err.message); }
  }
  if (e.target.closest("#ein-protokoll")) {
    try { await api("/api/protokoll/zeigen", { method: "POST" }); } catch (err) { toast(err.message); }
  }
});

// Die letzten Sicherungen in den Einstellungen: sehen, dass es sie gibt, ist schon die halbe Beruhigung.
async function sicherungenZeigen() {
  const el = document.getElementById("ein-sicherungen");
  if (!el) return;
  try {
    const l = await api("/api/sicherungen");
    el.innerHTML = l.length ? `${l.length} Sicherungen, neueste: ${l.slice(0, 3).map((s) => `${esc(s.zeit)} (${esc(s.grund)})`).join(" · ")}` : "Noch keine Sicherung.";
  } catch { el.textContent = "Sicherungen nicht lesbar."; }
}
new MutationObserver(() => { if (document.getElementById("ein-sicherungen")?.textContent === "…") sicherungenZeigen(); })
  .observe(document.getElementById("dialog"), { childList: true, subtree: true });

async function ordnerZeigen(id) {
  try { await api("/api/ordner/im_ordner", { method: "POST", body: { id } }); } catch (e) { toast(e.message); }
}

// Ordner aus dem Katalog entfernen: die Modelle darin gehen in den Papierkorb von partAtlas. Der Ordner und alles darin bleibt auf der
// Platte — partAtlas löscht in den Ordnern des Anwenders nichts; wer ihn auch loswerden will, tut das im Dateimanager, dorthin führt
// der Knopf. (Der Ordnerbaum zeigt nur Ordner mit Modellen: nach dem Entfernen verschwindet er aus der Seitenleiste.)
async function ordnerLoeschen(id, name) {
  let i;
  try { i = await api(`/api/ordner/inhalt?id=${encodeURIComponent(id)}`); } catch (e) { return toast(e.message); }
  if (!i.modelle.length) {
    const a = await dialog(`<h2>Ordner „${esc(name)}“</h2>
      <p>Es liegen keine Modelle des Katalogs darin${i.andere_n ? `, aber ${i.andere_n} ${i.andere_n === 1 ? "andere Datei" : "andere Dateien"}` : ""}. Es gibt nichts aus dem Katalog zu entfernen,
        und partAtlas löscht in deinen Ordnern nichts.</p>
      <div class="knoepfe"><button class="knopf" value="nein">Schließen</button><button class="knopf akzent" value="zeigen">Im Dateimanager zeigen</button></div>`);
    if (a === "zeigen") ordnerZeigen(id);
    return;
  }
  const r = await loeschDialog(i.modelle, `Ordner „${esc(name)}“ aus dem Katalog entfernen?`, { id, inhalt: i });
  if (!r) return;
  if (r.fehler?.length) toast(`${r.fehler.length} Modelle ließen sich nicht entfernen: ${r.fehler[0].fehler}`);
  if (zustand.ordner === id || zustand.ordner.startsWith(id + "/")) zustand.ordner = id.slice(0, id.lastIndexOf("/"));
  await ladeSeite();
  neuLaden();
  const a = await dialog(`<h2>Aus dem Katalog entfernt</h2>
    <p>${r.modelle} ${r.modelle === 1 ? "Modell liegt" : "Modelle liegen"} im Papierkorb von partAtlas. <b>Der Ordner und seine Dateien liegen unverändert auf der Platte:</b></p>
    <p class="dim">${esc(r.pfad)}</p>
    <p>Willst du ihn auch von der Platte löschen, geht das im Dateimanager.</p>
    <div class="knoepfe"><button class="knopf" value="nein">Schließen</button><button class="knopf akzent" value="zeigen">Im Dateimanager zeigen</button></div>`);
  if (a === "zeigen") ordnerZeigen(id);
}

async function wurzelEntfernen({ id, name, pfad, anzahl }) {
  const a = await dialog(`<h2>Ordner aus partAtlas entfernen?</h2>
    <p><b>${esc(name)}</b>${anzahl ? ` — ${anzahl} ${anzahl === 1 ? "Modell" : "Modelle"}` : ""}<br><code>${esc(pfad)}</code></p>
    <p class="dim">Die Dateien auf der Platte bleiben unberührt. Tags, Bilder und Verknüpfungen der Modelle bleiben erhalten;
      die Modelle gelten als „Datei fehlt“, bis der Ordner wieder hinzugefügt wird. Du findest ihn unter Bereinigen › Papierkorb und holst ihn
      dort mit einem Klick zurück.</p>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr" value="ja">Entfernen</button></div>`);
  if (a !== "ja") return;
  try {
    await api(`/api/wurzeln/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (zustand.ordner === id || zustand.ordner.startsWith(id + "/")) zustand.ordner = "";
    toast("Ordner entfernt.");
    await ladeSeite();
    neuLaden();
  } catch (e) { toast(e.message); }
}

async function kontextAktion(k, knopf) {
  $("#kontext").hidden = true;
  if (kontextMenu.ziel.ordner) {
    const o = kontextMenu.ziel.ordner;
    if (k === "wurzel-weg") return wurzelEntfernen(kontextMenu.ziel.wurzel);
    if (k === "ordner-zeigen") return ordnerZeigen(o.id);
    if (k === "ordner-weg") return ordnerLoeschen(o.id, o.name);
    return;
  }
  const f = kontextMenu.ziel.galerie;
  if (f) {
    if (k === "gal-titel") return vorschauSetzen(f.art === "eigen" ? `eigen:${f.k}` : f.art);
    if (k === "gal-weg") return bildEntfernen(f.k);
    if (k === "gal-plus") return $("#bild-wahl").click();
    return;
  }
  const { id, modelle, m } = kontextMenu.ziel;
  switch (k) {
    case "oeffnen": return modellOeffnen({ pfad: knopf.dataset.pfad }, id);
    case "system": return modellOeffnen({ system: true }, id);
    case "einrichten": return einstellungen();
    case "ordner":
      try { await api(`/api/modelle/${id}/im_ordner`, { method: "POST" }); } catch (err) { toast(err.message); }
      return;
    case "ws":
      if (m.warteschlange != null) await api(`/api/warteschlange/${id}`, { method: "DELETE" });
      else await api("/api/warteschlange", { method: "POST", body: { modelle: [id] } });
      return;
    case "druck1": return druckAnlegen([id]);
    case "gedruckt1": return aendern(id, { gedruckt: !m.gedruckt });
    case "favorit1": return aendern(id, { favorit: !m.favorit });
    case "entwurf1": return aendern(id, { entwurf: !m.entwurf });
    case "umbenennen": return umbenennen(id);
    case "loeschen": return modelle.length > 1 ? loeschenViele(modelle) : loeschen(id);
    case "wiederherstellen":
      for (const x of modelle) await api(`/api/modelle/${x}/wiederherstellen`, { method: "POST" }).catch((err) => toast(err.message));
      return;
    case "endgueltig": return endgueltigEntfernen(id);
    case "druck": return druckAnlegen(modelle);
    default: return stapelAktion(k, modelle);
  }
}

document.addEventListener("click", (e) => {
  const b = e.target.closest?.("#inspektor [data-oeffne-pfad]:not(#oeffnen)");
  if (b) modellOeffnen({ pfad: b.dataset.oeffnePfad });
});
document.addEventListener("contextmenu", (e) => {
  const k = e.target.closest?.(".karte, .zeile-l, .zeile-k");
  if (k) kontextMenu(e, k.dataset.id);
});
document.addEventListener("click", (e) => {
  const b = e.target.closest?.("[data-km]");
  if (b) return kontextAktion(b.dataset.km, b);
  if (!e.target.closest?.("#kontext")) $("#kontext").hidden = true;
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("#kontext").hidden = true; });
window.addEventListener("blur", () => { $("#kontext").hidden = true; });
document.addEventListener("scroll", () => { $("#kontext").hidden = true; }, true);

// ---------------------------------------------------------------- Breite der Seitenleisten
//
// Inspektor (rechte Seitenleiste) aus- und einblenden, wie in pDMS: ein Klick, die Wahl überlebt den Neustart. Der Griff am
// rechten Rand bleibt, solange er weg ist — ohne ihn fände ihn niemand wieder.
function inspektorSichtbar(an) {
  $(".app").classList.toggle("insp-versteckt", !an);
  $("#insp-auf").hidden = an;
  const knopf = $("#insp-umschalten");
  knopf.textContent = an ? "⇥" : "⇤";
  knopf.title = an ? "Details ausblenden — die Liste bekommt die ganze Breite" : "Details wieder einblenden";
  knopf.setAttribute("aria-pressed", String(an));
  localStorageSchreiben("inspektor", an ? "auf" : "zu");
  requestAnimationFrame(() => raster.neu());          // die Liste gewinnt oder verliert Breite: Spalten und Kacheln neu legen
}
inspektorSichtbar(localStorageLesen("inspektor") !== "zu");
$("#insp-umschalten").addEventListener("click", () => inspektorSichtbar($(".app").classList.contains("insp-versteckt")));
$("#insp-auf").addEventListener("click", () => inspektorSichtbar(true));

// Die Griffe sitzen auf den Rändern; Ziehen ändert die Spaltenbreite, die
// Zahl bleibt gemerkt, ein Doppelklick stellt die Vorgabe wieder her.

const BREITE = { seite: { vorgabe: 233, min: 160, max: 480, var: "--seite-b", von: "links" },
                 inspektor: { vorgabe: 377, min: 260, max: 700, var: "--insp-b", von: "rechts" } };
function breiteSetzen(name, px, merken = true) {
  const b = BREITE[name];
  px = Math.round(Math.max(b.min, Math.min(b.max, px)));
  document.documentElement.style.setProperty(b.var, px + "px");
  if (merken) localStorageSchreiben("breite." + name, px);
  return px;
}
for (const name of Object.keys(BREITE)) {
  const gemerkt = Number(localStorageLesen("breite." + name));
  if (gemerkt) breiteSetzen(name, gemerkt, false);
}
document.querySelectorAll("[data-griff]").forEach((g) => {
  const name = g.dataset.griff, b = BREITE[name];
  g.addEventListener("dblclick", () => { breiteSetzen(name, b.vorgabe); raster.neu(); });
  g.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    g.setPointerCapture(e.pointerId);
    g.classList.add("zieht");
    const rand = $(".app").getBoundingClientRect();
    const bewegen = (ev) => {
      breiteSetzen(name, b.von === "links" ? ev.clientX - rand.left - 50 : rand.right - ev.clientX, false);
      requestAnimationFrame(() => raster.neu());
    };
    const ende = () => {
      g.classList.remove("zieht");
      g.removeEventListener("pointermove", bewegen);
      g.removeEventListener("pointerup", ende);
      g.removeEventListener("pointercancel", ende);
      localStorageSchreiben("breite." + name, parseInt(document.documentElement.style.getPropertyValue(b.var)));
    };
    g.addEventListener("pointermove", bewegen);
    g.addEventListener("pointerup", ende);
    g.addEventListener("pointercancel", ende);
  });
});


// ---------------------------------------------------------------- Felder der Seitenleiste (Split View)
//
// Wie in VS Code: jedes Feld hat dieselbe Mindesthöhe, ein eingeklapptes nur die Kopfzeile. Das erste
// offene Feld (der Explorer, solange er offen ist) nimmt auf, was frei wird, und gibt her, was fehlt —
// zuerst es selbst, dann von unten nach oben. Ein Griff an der Oberkante eines Feldes verschiebt die
// Grenze zu dem darüber: das eine wächst, die auf der anderen Seite schrumpfen der Reihe nach bis zu
// ihrer Mindesthöhe. Alle Höhen rechnet seitenLayout(); das CSS setzt sie nur.
const KOPF = 25, FELD_MIN = 125, FELD_START = 150;
const feldRaum = $(".panes");
const felder = [...feldRaum.children].filter((x) => x.classList.contains("sektion"));
let gemerkteHoehen = {};
try { gemerkteHoehen = JSON.parse(localStorageLesen("felder") || "{}") || {}; } catch { gemerkteHoehen = {}; }
const feldSichtbar = () => felder.filter((f) => !f.hidden && getComputedStyle(f).display !== "none");
const feldOffen = (f) => !f.dataset.zu;
// Gleiche Mindesthöhe für alle offenen Felder; wird das Fenster so niedrig, dass sie nicht reicht, schrumpft sie gemeinsam.
function feldMin() {
  const liste = feldSichtbar(), offene = liste.filter(feldOffen).length;
  if (!offene) return FELD_MIN;
  return Math.max(KOPF + 36, Math.min(FELD_MIN, Math.floor((feldRaum.clientHeight - (liste.length - offene) * KOPF) / offene)));
}
const setzeHoehen = (karte) => karte.forEach((h, f) => { f.style.height = h + "px"; });

function seitenLayout() {
  const T = feldRaum.clientHeight;
  const liste = feldSichtbar();
  if (T <= 0 || !liste.length) return;
  const min = feldMin();
  const g = new Map(liste.map((f) => [f, feldOffen(f) ? Math.max(min, gemerkteHoehen[f.dataset.sektion] || FELD_START) : KOPF]));
  const offene = liste.filter(feldOffen);
  let delta = T - [...g.values()].reduce((a, b) => a + b, 0);
  if (offene.length) {
    const biegsam = offene[0];
    if (delta > 0) g.set(biegsam, g.get(biegsam) + delta);
    else for (const f of [biegsam, ...offene.slice(1).reverse()]) {
      const nimm = Math.min(g.get(f) - min, -delta);
      g.set(f, g.get(f) - nimm);
      delta += nimm;
      if (delta >= 0) break;
    }
  }
  setzeHoehen(g);
  // Ein Griff nur dort, wo oberhalb und unterhalb je ein offenes Feld liegt.
  liste.forEach((f, i) => {
    const griff = f.querySelector(":scope > .sash");
    const weg = !(liste.slice(0, i).some(feldOffen) && liste.slice(i).some(feldOffen));
    if (griff && griff.hidden !== weg) griff.hidden = weg;     // nur bei Änderung: sonst weckt es den Beobachter wieder auf
  });
}

felder.slice(1).forEach((f) => {
  const griff = document.createElement("div");
  griff.className = "sash";
  griff.title = "Höhe ziehen";
  f.prepend(griff);
  griff.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    const liste = feldSichtbar();
    const i = liste.indexOf(f);
    const min = feldMin();
    const start = new Map(liste.map((x) => [x, x.offsetHeight]));
    const ueber = liste.slice(0, i).filter(feldOffen).reverse();   // das nächste zuerst
    const unter = liste.slice(i).filter(feldOffen);
    if (!ueber.length || !unter.length) return;
    griff.setPointerCapture(e.pointerId);
    griff.classList.add("zieht");
    const y0 = e.clientY;
    // `waechst` wächst um d, die `gibt` schrumpfen der Reihe nach um zusammen d (jedes höchstens bis FELD_MIN).
    const verschiebe = (waechst, gibt, d) => {
      const g = new Map(start);
      d = Math.max(0, Math.min(d, gibt.reduce((s, x) => s + start.get(x) - min, 0)));
      g.set(waechst, start.get(waechst) + d);
      let rest = d;
      for (const x of gibt) { const nimm = Math.min(start.get(x) - min, rest); g.set(x, start.get(x) - nimm); rest -= nimm; }
      setzeHoehen(g);
    };
    const bewegt = (m) => {
      const d = m.clientY - y0;
      if (d >= 0) verschiebe(ueber[0], unter, d); else verschiebe(unter[0], ueber, -d);
    };
    const fertig = () => {
      griff.classList.remove("zieht");
      griff.removeEventListener("pointermove", bewegt);
      griff.removeEventListener("pointerup", fertig);
      griff.removeEventListener("pointercancel", fertig);
      for (const x of feldSichtbar().filter(feldOffen)) gemerkteHoehen[x.dataset.sektion] = x.offsetHeight;
      localStorageSchreiben("felder", JSON.stringify(gemerkteHoehen));
    };
    griff.addEventListener("pointermove", bewegt);
    griff.addEventListener("pointerup", fertig);
    griff.addEventListener("pointercancel", fertig);
  });
});
new ResizeObserver(seitenLayout).observe(feldRaum);
new MutationObserver(seitenLayout).observe(feldRaum, { attributes: true, subtree: true, attributeFilter: ["data-zu", "hidden"] });
new MutationObserver(seitenLayout).observe($(".seite"), { attributes: true, attributeFilter: ["data-modus"] });   // Katalog ↔ Bereinigen
requestAnimationFrame(seitenLayout);


// ---------------------------------------------------------------- Höhe der Vorschau im Inspektor
//
// Das Bild braucht man nach dem ersten Hinsehen nicht mehr gross: der Griff unter der Vorschau zieht
// die Höhe, die Leiste mit den kleinen Bildern entfällt, wenn nur noch wenig bleibt. Gemerkt.
const BILD_MIN = 48, BILD_KLEIN = 120;
function setzeBildHoehe(px) {
  const root = document.documentElement;
  if (px == null) root.style.removeProperty("--bild-h");
  else root.style.setProperty("--bild-h", px + "px");
  root.classList.toggle("bild-klein", px != null && px < BILD_KLEIN);
}
{
  const gemerkt = Number(localStorageLesen("bildhoehe"));
  if (gemerkt) setzeBildHoehe(gemerkt);
}
document.addEventListener("pointerdown", (e) => {
  const griff = e.target.closest?.(".i-griff");
  if (!griff) return;
  e.preventDefault();
  griff.setPointerCapture(e.pointerId);
  griff.classList.add("zieht");
  const y0 = e.clientY, h0 = $("#i-bild")?.offsetHeight || 220;
  const hoechst = Math.round(innerHeight * 0.6);
  const bewegt = (m) => setzeBildHoehe(Math.round(Math.min(hoechst, Math.max(BILD_MIN, h0 + m.clientY - y0))));
  const fertig = () => {
    griff.classList.remove("zieht");
    griff.removeEventListener("pointermove", bewegt);
    griff.removeEventListener("pointerup", fertig);
    griff.removeEventListener("pointercancel", fertig);
    localStorageSchreiben("bildhoehe", String($("#i-bild")?.offsetHeight || ""));
  };
  griff.addEventListener("pointermove", bewegt);
  griff.addEventListener("pointerup", fertig);
  griff.addEventListener("pointercancel", fertig);
});
document.addEventListener("dblclick", (e) => {
  if (!e.target.closest?.(".i-griff")) return;
  setzeBildHoehe(null);
  localStorageSchreiben("bildhoehe", "");
});
