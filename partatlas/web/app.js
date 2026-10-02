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

const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const zustand = {
  modelle: [], ansicht: "alle", tags: new Set(), material: new Set(), ordner: "", format: "", suche: "", sammlung: "", sammlungen: [],
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

function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toast.zeit);
  toast.zeit = setTimeout(() => (t.hidden = true), 3500);
}

const zahl = (x, stellen = 1) => x == null ? "–" : Number(x).toLocaleString("de-DE", { maximumFractionDigits: stellen });
const masse = (m) => m ? m.map((v) => zahl(v)).join(" × ") + " mm" : "";
const endung = { "3mf": ".3mf", stl: ".stl", obj: ".obj", step: ".step", fcstd: ".FCStd" };
// CAD-Formate ohne Netz: keine Masse, keine 3D-Ansicht; ein Bild nur, wenn die Datei eins mitbringt.
const nurCad = (m) => (m.format === "step" || m.format === "fcstd") && m.cad !== "ok";
const nurCadText = (m) => m.format === "step" && m.cad !== "fehler" && zustand.scan?.laeuft ? "Vorschau folgt (FreeCAD) …" : `${m.format === "fcstd" ? "FCStd" : "STEP"} · nur CAD`;
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
  const p = new URLSearchParams({ q: zustand.suche, ordner: zustand.ordner, format: zustand.format,
                                  ansicht: zustand.ansicht, sammlung: zustand.sammlung, leiste: 1,
                                  tags: [...zustand.tags].join(","), material: [...zustand.material].join(",") });
  const { modelle: liste, leiste } = await api("/api/modelle?" + p);
  zeichneLeiste(leiste);
  const s = (zustand.sammlung || zustand.ansicht === "warteschlange") ? "eigene" : zustand.sortierung;
  if (s === "neu") liste.sort((a, b) => (b.angelegt || "").localeCompare(a.angelegt || ""));
  if (s === "gewicht") liste.sort((a, b) => (b.gewicht_g || 0) - (a.gewicht_g || 0));
  if (s === "groesse") liste.sort((a, b) => Math.max(...(b.masse || [0])) - Math.max(...(a.masse || [0])));
  const g = gruppiere(liste);
  zustand.modelle = g.liste;
  zustand.gruppen = g.gruppen;
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
    const g = gruppiere(zustand.modelle);
    zustand.modelle = g.liste;
    zustand.gruppen = g.gruppen;
    raster.neu();
  }
  abgleichen($("#ordner"), `<div class="baum">${ordner.map((w) => zweig(w, 0)).join("")}</div>`);
  zustand.hatWurzeln = ordner.length > 0;
  zeichneLeer();
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
const BEREINIGEN = ["papierkorb", "duplikate", "fehlt", "unlesbar"];

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
  abgleichen($("#tagleiste"), `<button class="chip ${leer ? "aktiv" : ""}" data-tag="">Alle</button>`
    + (mat ? `<span class="leiste-titel">MATERIAL</span>${mat}` : "")
    + (fmt ? `<span class="leiste-titel">FORMAT</span>${fmt}` : "")
    + (tags ? `<span class="leiste-titel">TAGS</span>${tags}` : ""));
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
  const erst = zustand.hatWurzeln === false;
  document.body.classList.toggle("erststart", erst);
  leer.hidden = zustand.modelle.length > 0;
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
  if (m.dauer_s == null || (!m.gefunden && !m.abgebrochen)) return "";
  const zeit = m.dauer_s < 1 ? "unter 1 s" : m.dauer_s < 60 ? `${zahl(m.dauer_s, 1)} s` : dauer(m.dauer_s);
  // Nach einem Abbruch keine „Eingelesen“-Zeile: es ist nicht alles eingelesen.
  if (m.abgebrochen) return `Abgebrochen nach ${zeit}, ${(m.bearbeitet || 0).toLocaleString("de-DE")} Dateien`;
  // Phasen unter einer halben Sekunde sind Rauschen
  const phasen = Object.entries(m.phasen || {}).filter(([, s]) => s >= 0.5)
    .map(([k, s]) => `${PHASENNAME[k] || k} ${s < 60 ? zahl(s, 1) + " s" : dauer(s)}`).join(" · ");
  return `Eingelesen: ${m.gefunden.toLocaleString("de-DE")} Dateien${m.neu ? `, ${m.neu.toLocaleString("de-DE")} neu` : ""} in ${zeit}${phasen ? ` (${phasen})` : ""}`;
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
  return { neu, zeichne };
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
  return m.fehlt ? `<span class="badge warn">⚠ Datei fehlt</span>`
    : m.fehler ? `<span class="badge warn">unlesbar</span>`
    : m.drucke_n ? `<span class="badge gedruckt" title="${m.drucke_n}× gedruckt">✓${m.drucke_n > 1 ? " " + m.drucke_n + "×" : ""}</span>` : "";
}

function karte(m, x, y) {
  const url = bildUrl(m);
  const platz = m.vorschau === "ausstehend" ? "Vorschau wird gerendert …" : (nurCad(m) ? nurCadText(m) : "keine Vorschau");
  const markiert = zustand.auswahl.has(m.id);
  return `<div class="karte ${zustand.gewaehlt === m.id ? "gewaehlt" : ""} ${markiert ? "markiert" : ""} ${zustand.auswahl.size ? "mit-auswahl" : ""} ${m.fehlt ? "fehlt" : ""}" draggable="true" style="left:${x}px;top:${y}px" data-id="${esc(m.id)}">
    <div class="bild">${url ? bildTag(url) : `<div class="platzhalter">${platz}</div>`}
      ${istNeu(m) ? '<span class="neu-punkt" title="Neu hinzugefügt"></span>' : ""}
      <input type="checkbox" class="wahl" data-wahl="${esc(m.id)}" ${markiert ? "checked" : ""} title="auswählen">
      ${zustand.ansicht === "papierkorb" ? "" : `<button class="herz ${m.favorit ? "an" : ""}" data-herz="${esc(m.id)}" title="Favorit">♥</button>`}
      ${m.fehlt ? `<div class="fehlt-band" title="Die Datei liegt an keinem bekannten Ort mehr. Tags, Bilder und Verknüpfungen sind noch da — legt man sie zurück, ist alles wieder verbunden.">⚠ Datei fehlt</div>` : statusBadge(m)}</div>
    <div class="text"><div class="name" title="${esc(m.name)}">${esc(m.name)}<span class="endung">${esc(endung[m.format] || "")}</span></div>
      <div class="masse">${m.masse ? m.masse.map((v) => zahl(v, v < 10 ? 1 : 0)).join(" × ") + " mm" : "&nbsp;"}</div>
      <div class="tags">${m.gewicht_g ? `${zahl(m.gewicht_g, 1)} g` : "&nbsp;"}</div></div></div>`;
}

// Karten: wie eine Liste, aber höher — rechts neben dem Bild ist Platz für mehr vom Modell.
function zeileK(m, y) {
  const url = bildUrl(m);
  const markiert = zustand.auswahl.has(m.id);
  const ordner = (m.ordner[0] || "").split("/").slice(1).join("/");
  const status = m.fehlt ? "⚠ Datei fehlt" : m.fehler ? "unlesbar" : m.drucke_n ? `✓ ${m.drucke_n}× gedruckt` : (m.warteschlange != null && PHASE >= 2 ? "☰ Warteschlange" : "");
  const fakten = [masse(m.masse), m.gewicht_g ? zahl(m.gewicht_g, 1) + " g" : "", m.groesse ? zahl(m.groesse / 1024, 0) + " KB" : ""].filter(Boolean).join(" · ");
  const chips = [...(m.materialien || []).map((x) => `<span class="chip-k mat">${esc(x)}</span>`), ...m.tags.map((t) => `<span class="chip-k">#${esc(t)}</span>`)].join("");
  return `<div class="zeile-k ${zustand.gewaehlt === m.id || markiert ? "gewaehlt" : ""} ${m.fehlt ? "fehlt" : ""}" draggable="true" style="top:${y}px" data-id="${esc(m.id)}">
    <input type="checkbox" class="wahl-l" data-wahl="${esc(m.id)}" ${markiert ? "checked" : ""} title="auswählen">
    <div class="k-bild">${url ? bildTag(url) : `<div class="mini">${m.format === "step" ? "STEP" : m.format === "fcstd" ? "FCStd" : ""}</div>`}</div>
    <div class="k-text">
      <div class="k-name" title="${esc(m.name)}">${m.favorit ? "♥ " : ""}${esc(m.name)}<span class="endung">${esc(endung[m.format] || "")}</span></div>
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
  const status = m.fehlt ? "⚠ fehlt" : m.fehler ? "unlesbar" : m.drucke_n ? `✓ ${m.drucke_n}× gedruckt` : (m.warteschlange != null && PHASE >= 2 ? "☰ Warteschlange" : "");
  return `<div class="zeile-l ${zustand.gewaehlt === m.id || markiert ? "gewaehlt" : ""} ${m.fehlt ? "fehlt" : ""}" draggable="true" style="top:${y}px" data-id="${esc(m.id)}">
    <span>${url ? bildTag(url) : '<div class="mini"></div>'}</span>
    <span><input type="checkbox" class="wahl-l" data-wahl="${esc(m.id)}" ${markiert ? "checked" : ""}></span>
    <span title="${esc(m.name)}">${m.favorit ? "♥ " : ""}${esc(m.name)}</span>
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
  // Papierkorb: der Knopf zum endgültigen Leeren (der Server konnte das, die Oberfläche bot es nirgends an).
  const pk = zustand.ansicht === "papierkorb" && zustand.modelle.length > 0;
  $("#pk-leiste").hidden = !pk;
  if (pk) $("#pk-text").textContent = `🗑 ${zustand.modelle.length.toLocaleString("de-DE")} ${zustand.modelle.length === 1 ? "Modell" : "Modelle"} im Papierkorb`;
  const st = $("#stapel");
  st.hidden = n === 0;
  if (!n) return;
  abgleichen(st, zustand.ansicht === "papierkorb"
    ? `<b>${n} ausgewählt</b><button class="knopf" data-stapel="wiederherstellen">Wiederherstellen</button>
       <button class="knopf" data-stapel="alle">Alle auswählen</button><button class="knopf" data-stapel="keine">✕ Auswahl aufheben</button>`
    : `<b>${n} ausgewählt</b>
    <button class="knopf" data-stapel="alle">Alle auswählen (${zustand.modelle.length})</button>
    <button class="knopf" data-stapel="baugruppe">🧩 Zu Baugruppe …</button>
    <button class="knopf" data-ab-phase="2" data-stapel="warteschlange">☰ In Warteschlange</button>
    <select class="knopf" id="stapel-sammlung"><option value="">Zu Sammlung …</option>${zustand.sammlungen.map((x) =>
      `<option value="${esc(x.id)}">${esc(x.name)}</option>`).join("")}<option value="__neu">Neue Sammlung …</option></select>
    <button class="knopf" data-stapel="tag">＃ Tag …</button>
    <button class="knopf" data-stapel="material">Material …</button>
    <button class="knopf" data-stapel="gedruckt">✓ Gedruckt</button>
    <button class="knopf" data-stapel="favorit">♥ Favorit</button>
    <button class="knopf" data-stapel="verschieben">Verschieben …</button>
    <button class="knopf gefahr" data-stapel="loeschen">Löschen</button>
    <button class="knopf" data-stapel="keine">✕</button>`);
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

async function stapelAktion(aktion, modelle = [...zustand.auswahl]) {
  switch (aktion) {
    case "alle": zustand.modelle.forEach((m) => zustand.auswahl.add(m.id)); zeichneStapel(); return raster.zeichne();
    case "keine": zustand.auswahl.clear(); zeichneStapel(); return raster.zeichne();
    case "warteschlange": return stapel("warteschlange", null, modelle);
    case "baugruppe": return zuBaugruppe(modelle);
    case "gedruckt": return stapel("gedruckt", true, modelle);
    case "favorit": return stapel("favorit", true, modelle);
    case "material": {
      const alle = await api("/api/materialien");
      const a = await dialog(`<h2>Material für ${modelle.length} Modelle</h2>
        <p class="dim">Wird als „vorgesehen“ ergänzt; vorhandene Angaben bleiben.</p>
        <div class="kategorien">${alle.map((x) => `<button type="button" class="chip" data-mat-wahl="${esc(x)}">${esc(x)}</button>`).join("")}</div>
        <input type="text" id="s-name" placeholder="oder neues Material">
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Setzen</button></div>`);
      if (a === "ja" && $("#s-name").value.trim()) return stapel("material", $("#s-name").value.trim(), modelle);
      return;
    }
    case "tag": {
      const a = await dialog(`<h2>Tag für ${modelle.length} Modelle</h2><input type="text" id="s-name" placeholder="z. B. Funktional">
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Setzen</button></div>`);
      if (a === "ja") return stapel("tag", $("#s-name").value, modelle);
      return;
    }
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

// Papierkorb endgültig leeren: die Dateien gehen von der Platte, danach ist nichts mehr wiederherzustellen. Eigene Bilder werden
// archiviert und gehen nicht verloren.
async function papierkorbLeeren() {
  const n = zustand.modelle.length;
  const a = await dialog(`<h2>Papierkorb endgültig leeren?</h2>
    <p>${n.toLocaleString("de-DE")} ${n === 1 ? "Modell wird" : "Modelle werden"} samt ${n === 1 ? "seiner Datei" : "ihren Dateien"} von der Platte gelöscht. Danach lässt sich nichts davon wiederherstellen.</p>
    <p class="dim">Eigene Bilder, die du hinzugefügt hattest, werden archiviert und gehen nicht verloren.</p>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr" value="ja">Endgültig löschen</button></div>`);
  if (a !== "ja") return;
  try {
    const r = await api("/api/papierkorb/leeren", { method: "POST" });
    toast(`${r.geloescht} ${r.geloescht === 1 ? "Modell" : "Modelle"} endgültig gelöscht.`);
    waehle(null);
    await ladeSeite();
    neuLaden();
  } catch (e) { toast(e.message); }
}
$("#pk-leeren").addEventListener("click", papierkorbLeeren);

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
  const reiter = papierkorb ? "datei" : ["uebersicht", "drucke", "datei"].includes(localStorageLesen("reiter")) ? localStorageLesen("reiter") : "uebersicht";
  const reiterKopf = papierkorb ? "" : `<div class="i-reiter" role="tablist">
      <button role="tab" data-reiter="uebersicht">Übersicht</button>
      <button role="tab" data-reiter="drucke">Drucke${m.drucke_n ? ` <span class="d-zahl">${m.drucke_n}</span>` : ""}</button>
      <button role="tab" data-reiter="datei">Datei</button></div>`;
  $("#inspektor").innerHTML = `
    <div class="i-fix">
      ${zustand.baugruppe ? `<button class="zurueck" id="bg-zurueck">← Baugruppe</button>` : ""}
      <div class="galerie" id="i-galerie" data-sig="${esc(sig)}"></div>
      <div class="i-griff" title="Höhe der Vorschau ziehen (Doppelklick: zurücksetzen)"></div>
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
      </div>`}
      ${reiterKopf}
    </div>
    ${m.fehler_text ? `<p class="fehler">Unlesbar: ${esc(m.fehler_text)}</p>` : ""}
    ${m.fehlt ? `<p class="fehler"><b>⚠ Datei fehlt.</b> Sie liegt an keinem bekannten Ort mehr — gelöscht, umbenannt ausserhalb der Ordner von partAtlas oder auf einem Laufwerk, das gerade fehlt. Tags, Bilder und Verknüpfungen sind noch da: legt man die Datei zurück, ist beim nächsten Einlesen alles wieder verbunden. Braucht man das Modell nicht mehr: „Löschen“.</p>` : ""}

    <div class="i-tafel" data-reiter="uebersicht">
    ${papierkorb ? "" : `<div class="i-schalter">
        <button class="schalter ${m.warteschlange != null ? "an" : ""}" data-ab-phase="2" id="ws-knopf" title="${m.warteschlange != null ? "Aus der Warteschlange nehmen" : "Zum Drucken vormerken"}">☰ ${m.warteschlange != null ? `Warteschlange · Platz ${m.warteschlange + 1}` : "In Warteschlange"}</button>
        <button class="schalter ${m.gedruckt ? "an" : ""}" id="gedruckt" title="${m.drucke_n ? "Zu den Drucken" : "Als gedruckt markieren"}">${m.drucke_n ? `✓ ${m.drucke_n}× gedruckt` : "○ Noch nicht gedruckt"}</button>
        <button class="schalter ${m.favorit ? "an" : ""}" id="favorit" title="Favorit">♥</button>
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

    ${papierkorb ? "" : `<div class="i-tafel" data-reiter="drucke">${druckeTafel(m)}</div>`}

    <div class="i-tafel" data-reiter="datei">
      <div class="i-titel">MODELLDATEN</div>
      <div class="i-karte">${details.map(zeile).join("")}${quelle}</div>
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
                   : `<button type="button" data-km="ordner-weg" class="gefahr">Ordner löschen …</button>`);
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
  if (await loeschDialog([id], `„${esc(m.name)}${esc(endung[m.format] || "")}“ löschen?`)) waehle(null);
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
  const o = ordner?.inhalt;
  const ordnerZeile = !o ? "" : o.andere_n || o.mehrfach.length
    ? zeile("📁", `<b>Der Ordner bleibt stehen</b>, weil noch etwas darin liegt, das partAtlas nicht löscht:
        <ul>${o.andere.slice(0, 6).map((d) => `<li>${esc(d)}</li>`).join("")}${o.andere_n > 6 ? `<li>… und ${o.andere_n - 6} weitere</li>` : ""}
          ${o.mehrfach.length ? `<li>${o.mehrfach.length} ${o.mehrfach.length === 1 ? "Modell hat" : "Modelle haben"} eine Kopie ausserhalb und bleiben</li>` : ""}</ul>
        Den Rest löschst du danach im Dateimanager; der Knopf dort hin kommt gleich.`)
    : zeile("📁", "Der Ordner wird danach entfernt: er ist dann leer.");
  const a = await dialog(`<h2>${titel}</h2>
    <p class="dim">Alles kommt in den Papierkorb von partAtlas. „Wiederherstellen“ legt es an seinen Ort zurück; endgültig weg ist es erst, wenn der Papierkorb geleert wird.</p>
    <div class="loesch-liste">${ordnerZeile}${dateien}${bilder}${baugruppen}${schlange}${sammlungen}${tags}</div>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr" value="ja">In den Papierkorb</button></div>`);
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
  let w;
  try { w = await api("/api/wurzeln/waehlen", { method: "POST" }); } catch (e) { return toast(e.message); }
  if (w.abgebrochen) return;
  // Ohne Dateidialog auf dem Rechner (kein zenity, kdialog, Tk) bleibt der eigene Ordnerbaum.
  const pfad = w.keinDialog ? await ordnerWaehler() : w.pfad;
  if (!pfad) return;
  if (!w.keinDialog && !w.modelle) {
    const frage = await dialog(`<h2>Ordner ohne Modelle</h2><p>In diesem Ordner liegen keine Modelldateien (3MF, STL, OBJ, STEP, FCStd).</p>
      <p class="dim">${esc(pfad)}</p>
      <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf" value="ja">Trotzdem hinzufügen</button></div>`);
    if (frage !== "ja") return;
  }
  try {
    await api("/api/wurzeln", { method: "POST", body: { pfad } });
    zustand.hatWurzeln = true;
    zustand.scan = { laeuft: true };
    zeichneLeer();
    toast(w.modelle ? `${w.vollstaendig ? "" : "Über "}${w.modelle.toLocaleString("de-DE")} ${w.modelle === 1 ? "Modelldatei wird" : "Modelldateien werden"} eingelesen …` : "Ordner wird eingelesen …");
    ladeSeite();
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
  if (st) return stapelAktion(st.dataset.stapel);
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
  if (ansicht) { Object.assign(zustand, { ansicht: ansicht.dataset.ansicht, ordner: "", tags: new Set(), material: new Set(), format: "", sammlung: "" }); return neuLaden(); }
  const rail = t.closest("[data-rail]");
  if (rail) { Object.assign(zustand, { ansicht: rail.dataset.rail === "bereinigen" ? "papierkorb" : "alle", ordner: "", tags: new Set(), material: new Set(), format: "", sammlung: "" }); return neuLaden(); }
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
    case "neu-einlesen": case "neu-einlesen-2": $("#import-menu").hidden = true; await api("/api/scan", { method: "POST" }); return toast("Wird neu eingelesen …");
    case "gedruckt": {
      // Mit Drucken führt der Knopf zu ihnen; ohne legt er einen leeren an.
      const m = zustand.modelle.find((x) => x.id === id);
      if (m && m.drucke_n) return reiterWaehlen("drucke");
      await aendern(id, { gedruckt: true });
      return waehle(id);
    }
    case "favorit": { const m = zustand.modelle.find((x) => x.id === id); await aendern(id, { favorit: !(m && m.favorit) }); return waehle(id); }
    case "oeffnen": { const k = $("#oeffnen"); return modellOeffnen(k.dataset.system ? { system: true } : { pfad: k.dataset.oeffnePfad }); }
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

// ---------------------------------------------------------------- Live (flatgraph bei_aenderung → SSE)

let liveZeit, liveBetrifft = false;
function live() {
  const q = new EventSource("/api/live");
  q.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.art === "scan") {
      zustand.scan = m;
      if (!zustand.modelle.length) zeichneLeer();
      $("#scan-abbrechen").hidden = !m.laeuft || !!m.abbricht;
      $("#scan-status").textContent = m.laeuft && m.abbricht ? "Wird abgebrochen …" : m.laeuft
        ? `Einlesen: ${m.phase}${m.analysiert != null && m.zu_analysieren ? ` ${m.analysiert}/${m.zu_analysieren}` : ""}`
        : (m.vorschauen_offen ? "" : "");
      if (m.phase === "vorschau" && m.vorschauen_offen && !m.abbricht) $("#scan-status").textContent = `Vorschauen: noch ${m.vorschauen_offen}`;
      if (m.phase === "cad" && m.laeuft && !m.abbricht) $("#scan-status").textContent = `STEP umwandeln (FreeCAD): noch ${m.cad_offen}`;
      if (m.fcstd_frage && !m.laeuft && !zustand.fcstdGefragt) { zustand.fcstdGefragt = true; fcstdFrage(m.fcstd_frage); }
      if (m.phase === "fertig" || m.abgebrochen) {
        $("#scan-status").textContent = $("#scan-status").title = scanErgebnis(m);
        if (m.dauer_s != null && m.gefunden) toast(scanErgebnis(m));
        neuLaden();
      }
      return;
    }
    // Viele Änderungen hintereinander (Scan) sammeln, dann einmal laden.
    const meins = zustand.gewaehlt && [m.ref, m.quelle, m.ziel].includes(`MODEL_ASSET/${zustand.gewaehlt}`);
    if (meins) liveBetrifft = true;
    clearTimeout(liveZeit);
    liveZeit = setTimeout(() => {
      neuLaden();
      if (liveBetrifft && zustand.gewaehlt) waehle(zustand.gewaehlt, true);
      liveBetrifft = false;
    }, 300);
  };
}

document.documentElement.dataset.app = localStorageLesen("thema") || "dark";
neuLaden();
programmeAktualisieren();
$("#scan-abbrechen").onclick = async () => {
  $("#scan-abbrechen").hidden = true;
  try { await api("/api/scan/abbrechen", { method: "POST" }); } catch (err) { toast(err.message); }
};
api("/api/stand").then((s) => { $("#version").textContent = s.version || ""; if (s.scan?.fcstd_frage && !s.scan.laeuft && !zustand.fcstdGefragt) { zustand.fcstdGefragt = true; fcstdFrage(s.scan.fcstd_frage); } $("#scan-abbrechen").hidden = !(s.scan && s.scan.laeuft && !s.scan.abbricht); if (s.scan && !s.scan.laeuft) $("#scan-status").textContent = $("#scan-status").title = scanErgebnis(s.scan); }).catch(() => {});
live();

// Dateien aus dem Dateimanager ins Fenster ziehen: hochladen.
let abwurfZaehler = 0;
// Ein Bild aus der eigenen Leiste hat Dateityp „Files“, kommt aber nicht von
// aussen — sonst entstünde vom Original eine Kopie als eigenes Bild.
let vonGalerie = false;
document.addEventListener("dragstart", (e) => { vonGalerie = !!e.target.closest?.("#i-galerie"); }, true);
document.addEventListener("dragend", () => { vonGalerie = false; }, true);
const vonAussen = (e) => !gezogen && !vonGalerie && [...(e.dataTransfer?.types || [])].includes("Files");
window.addEventListener("dragenter", (e) => { if (vonAussen(e)) { abwurfZaehler++; $("#abwurf").hidden = false; } });
// Bilder auf einen Druck (Foto dazu) oder auf den leeren Teil des Reiters „Drucke“ (neuer Druck mit Foto).
const druckZiel = (e) => (!galerie.m || galerie.m.papierkorb ? null : e.target.closest?.(".druck, .i-tafel[data-reiter='drucke']"));
const abwurfAufraeumen = () => document.querySelectorAll(".abwurf-ziel, .druck-ziel").forEach((x) => x.classList.remove("abwurf-ziel", "druck-ziel"));
window.addEventListener("dragleave", (e) => {
  if (vonAussen(e) && --abwurfZaehler <= 0) { abwurfZaehler = 0; $("#abwurf").hidden = true; abwurfAufraeumen(); }
});
window.addEventListener("dragover", (e) => {
  if (!vonAussen(e)) return;
  e.preventDefault();
  const aufGalerie = !!(e.target.closest?.("#i-galerie") && galerie.m && !galerie.m.papierkorb);
  const dz = aufGalerie ? null : druckZiel(e);
  abwurfAufraeumen();
  if (aufGalerie) $("#i-galerie")?.classList.add("abwurf-ziel");
  if (dz) dz.classList.add("druck-ziel");
  $("#abwurf").hidden = aufGalerie || !!dz;
});
window.addEventListener("drop", (e) => {
  if (!vonAussen(e)) return;
  e.preventDefault();
  abwurfZaehler = 0;
  $("#abwurf").hidden = true;
  const dz = druckZiel(e);
  abwurfAufraeumen();
  // Auf die Galerie gezogen: Bilder zum Modell, keine neuen Modelldateien.
  if (e.target.closest?.("#i-galerie") && galerie.m && !galerie.m.papierkorb) return bilderHochladen(e.dataTransfer.files);
  if (dz) return druckBilderAblegen(dz.closest(".druck")?.dataset.druck || null, e.dataTransfer.files);
  // Nur Bilder, aber nirgends, wo sie hingehören: nicht als Modelldatei einlesen wollen.
  const dateien = [...e.dataTransfer.files];
  if (dateien.length && dateien.every((f) => f.type.startsWith("image/"))) return toast("Bilder gehören auf die Vorschau oder auf einen Druck.");
  hochladen(e.dataTransfer.files);
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
    eintraege = [["wiederherstellen", `↩ Wiederherstellen${mehrere ? ` (${modelle.length})` : ""}`]];
  } else if (mehrere) {
    eintraege = [
      ["kopf", `${modelle.length} Modelle`],
      ["warteschlange", "☰ In die Warteschlange"], ["druck", "🖨 Zusammen gedruckt …"], ["gedruckt", "✓ Als gedruckt markieren"], ["favorit", "♥ Favorit"],
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
      ${n === 1 ? "sie" : "sie"} dafür im Hintergrund in FreeCAD laden, ohne Fenster.</p>
    <p><b>Wichtig:</b> Ein FreeCAD-Dokument kann Programmcode enthalten, der beim Laden ausgeführt wird. Das ist dasselbe, als würdest du die
      Datei in FreeCAD öffnen. Mach das nur für Dateien aus Quellen, denen du vertraust; bei heruntergeladenen Archiven aus dem Netz ist das
      Risiko höher als bei eigenen Konstruktionen.</p>
    <div class="knoepfe"><button class="knopf" value="nie">Nie</button><button class="knopf" value="nein">Nicht jetzt</button><button class="knopf akzent" value="ja">Ja, einlesen</button></div>`);
  if (a !== "ja" && a !== "nie") return;
  try {
    await api("/api/einstellungen", { method: "PUT", body: { fcstd_freecad: a === "ja" ? "ja" : "nein" } });
    if (a === "ja") { await api("/api/scan", { method: "POST" }); toast("FCStd-Dateien werden über FreeCAD eingelesen …"); }
  } catch (e) { toast(e.message); }
}

async function ordnerZeigen(id) {
  try { await api("/api/ordner/im_ordner", { method: "POST", body: { id } }); } catch (e) { toast(e.message); }
}

// Ordner löschen: die Modelle darin gehen in den Papierkorb, leere Verzeichnisse werden entfernt. Was keine Modelldatei ist
// (Bilder, PDFs aus einem entpackten Archiv), rührt partAtlas nicht an — dann bleibt der Ordner, und der Anwender räumt den Rest
// im Dateimanager selbst ab; dorthin führt der Knopf.
async function ordnerLoeschen(id, name) {
  let i;
  try { i = await api(`/api/ordner/inhalt?id=${encodeURIComponent(id)}`); } catch (e) { return toast(e.message); }
  const rest = i.andere_n || i.mehrfach.length;
  let r;
  if (i.modelle.length) {
    r = await loeschDialog(i.modelle, `Ordner „${esc(name)}“ löschen?`, { id, inhalt: i });
    if (!r) return;
    if (r.fehler?.length) toast(`${r.fehler.length} Modelle ließen sich nicht löschen: ${r.fehler[0].fehler}`);
  } else if (rest) {
    const a = await dialog(`<h2>Ordner „${esc(name)}“ lässt sich hier nicht löschen</h2>
      <p>Es liegen keine Modelle des Katalogs darin, aber ${i.andere_n} ${i.andere_n === 1 ? "andere Datei" : "andere Dateien"}, die partAtlas nicht anrührt:</p>
      <ul>${i.andere.slice(0, 8).map((d) => `<li>${esc(d)}</li>`).join("")}${i.andere_n > 8 ? `<li>… und ${i.andere_n - 8} weitere</li>` : ""}</ul>
      <div class="knoepfe"><button class="knopf" value="nein">Schließen</button><button class="knopf akzent" value="zeigen">Im Dateimanager zeigen</button></div>`);
    if (a === "zeigen") ordnerZeigen(id);
    return;
  } else {
    if (await dialog(`<h2>Leeren Ordner löschen?</h2><p><b>${esc(name)}</b> ist leer.</p>
      <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr" value="ja">Löschen</button></div>`) !== "ja") return;
    try { r = await api("/api/ordner/loeschen", { method: "POST", body: { id } }); } catch (e) { return toast(e.message); }
  }
  if (zustand.ordner === id || zustand.ordner.startsWith(id + "/")) zustand.ordner = id.slice(0, id.lastIndexOf("/"));
  await ladeSeite();
  neuLaden();
  if (r.entfernt) return toast("Ordner gelöscht.");
  const g = r.geblieben;
  const a = await dialog(`<h2>Der Ordner bleibt stehen</h2>
    <p>${r.modelle ? `${r.modelle} ${r.modelle === 1 ? "Modell liegt" : "Modelle liegen"} im Papierkorb. ` : ""}Der Ordner enthält noch
      ${g.andere ? `${g.andere} ${g.andere === 1 ? "andere Datei" : "andere Dateien"}` : ""}${g.andere && g.modelle ? " und " : ""}${g.modelle ? `${g.modelle} ${g.modelle === 1 ? "Modell" : "Modelle"}` : ""},
      die partAtlas nicht löscht.</p>
    <p class="dim">${esc(r.pfad)}</p>
    <div class="knoepfe"><button class="knopf" value="nein">Schließen</button><button class="knopf akzent" value="zeigen">Im Dateimanager zeigen</button></div>`);
  if (a === "zeigen") ordnerZeigen(id);
}

async function wurzelEntfernen({ id, name, pfad, anzahl }) {
  const a = await dialog(`<h2>Ordner aus partAtlas entfernen?</h2>
    <p><b>${esc(name)}</b>${anzahl ? ` — ${anzahl} ${anzahl === 1 ? "Modell" : "Modelle"}` : ""}<br><code>${esc(pfad)}</code></p>
    <p class="dim">Die Dateien auf der Platte bleiben unberührt. Tags, Bilder und Verknüpfungen der Modelle bleiben erhalten;
      die Modelle gelten als „Datei fehlt“, bis der Ordner wieder hinzugefügt wird.</p>
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
    case "umbenennen": return umbenennen(id);
    case "loeschen": return modelle.length > 1 ? loeschenViele(modelle) : loeschen(id);
    case "wiederherstellen":
      for (const x of modelle) await api(`/api/modelle/${x}/wiederherstellen`, { method: "POST" }).catch((err) => toast(err.message));
      return;
    case "sammlung": return sammlungWahl(modelle);
    case "druck": return druckAnlegen(modelle);
    default: return stapelAktion(k, modelle);
  }
}

async function sammlungWahl(modelle) {
  const a = await dialog(`<h2>Zu Sammlung${modelle.length > 1 ? ` (${modelle.length} Modelle)` : ""}</h2>
    <select id="s-wahl">${zustand.sammlungen.map((x) => `<option value="${esc(x.id)}">${esc(x.name)}</option>`).join("")}
      <option value="__neu">Neue Sammlung …</option></select>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Hinzufügen</button></div>`);
  if (a !== "ja") return;
  const sid = $("#s-wahl").value;
  if (sid === "__neu") return sammlungNeu(modelle);
  await api(`/api/sammlungen/${sid}/modelle`, { method: "POST", body: { modelle } }).catch((err) => toast(err.message));
  toast("Zur Sammlung hinzugefügt.");
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
