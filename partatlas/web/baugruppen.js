// Baugruppen: eine Stückliste mit Mengen, Fortschritt und Einkaufsliste.
// Nutzt die Hilfen aus app.js ($, esc, api, dialog, zustand …).
//
// Leitlinie: man soll sofort sehen, was fehlt, und mit einem Klick
// weiterkommen — Zähler statt Formularfelder, Vorschläge statt leerer
// Seiten, Ziehen statt Tippen.
"use strict";

zustand.baugruppe = "";
let bgDaten = null;

const dauer = (s) => {
  if (!s) return "–";
  const h = Math.floor(s / 3600), m = Math.round((s % 3600) / 60);
  return h ? `${h} h ${m} min` : `${m} min`;
};
const symbolFuer = (k) => ({ Schrauben: "🔩", Muttern: "⬡", Scheiben: "◯", Gewindeeinsätze: "🔧", Magnete: "🧲",
                            Lager: "⚙", Elektronik: "🔌", "Profil & Linear": "📏" }[k] || "📦");
// Übliche Filamentfarben — ein Klick statt Farbwähler.
const FARBEN = [["Schwarz", "#1a1a1a"], ["Weiss", "#f2f2f2"], ["Grau", "#8a8a8a"], ["Silber", "#c0c0c0"],
                ["Rot", "#c0392b"], ["Orange", "#e67e22"], ["Gelb", "#f1c40f"], ["Grün", "#27ae60"],
                ["Blau", "#2e86c1"], ["Violett", "#8e44ad"], ["Braun", "#7b4a2a"], ["Natur", "#e8dcc0"]];
const farbName = (hex) => (FARBEN.find(([, h]) => h.toLowerCase() === (hex || "").toLowerCase()) || [hex || "ohne Farbe"])[0];
const tupfer = (farbe, titel = "") => farbe
  ? `<span class="farbpunkt" style="background:${esc(farbe)}" title="${esc(titel || farbName(farbe))}"></span>`
  : `<span class="farbpunkt offen" title="Farbe offen"></span>`;

// „Brauche ich eine halbe Rolle?“ — in Worten, Rollen zu 1 kg.
function rollenText(r) {
  if (r <= 0) return "";
  if (r < 0.15) return "ein Rest";
  if (r < 0.35) return "≈ ¼ Rolle";
  if (r < 0.65) return "≈ ½ Rolle";
  if (r < 0.85) return "≈ ¾ Rolle";
  if (r < 1.2) return "≈ 1 Rolle";
  return `≈ ${zahl(Math.round(r * 2) / 2, 1)} Rollen`;
}
const prozent = (f) => (f.bedarf ? Math.round((100 * f.erledigt) / f.bedarf) : 0);
const balken = (f) => `<div class="balken ${f.bedarf && f.erledigt >= f.bedarf ? "fertig" : ""}"><i style="width:${prozent(f)}%"></i></div>`;

// ---------------------------------------------------------------- Seitenleiste

async function ladeBaugruppenLeiste() {
  const [liste, vorschlaege] = await Promise.all([api("/api/baugruppen"), api("/api/baugruppen/vorschlaege")]);
  zustand.baugruppen = liste;
  // Ein Hinweis, kein Kasten: wegklickbar, kommt erst wieder, wenn es mehr Vorschläge gibt.
  const tipp = vorschlaege.length > Number(localStorageLesen("bgtipp") || 0)
    ? `<div class="tipp" id="bg-tipp"><span>${vorschlaege.length} Ordner sehen aus wie Baugruppen</span><button class="tipp-x" id="bg-tipp-x" title="Ausblenden">×</button></div>` : "";
  abgleichen($("#baugruppen"), liste.map((b) => `
    <button class="eintrag ${zustand.baugruppe === b.id ? "aktiv" : ""}" data-baugruppe="${esc(b.id)}"><span>${esc(b.name)}</span><em title="Druckteile">${b.druck_bedarf}</em></button>`).join("")
    + (liste.length ? "" : `<button class="eintrag leer-eintrag" id="baugruppe-neu-2">＋ Neue Baugruppe</button>`) + tipp);
  zustand.bgVorschlaege = vorschlaege;
  markiereAnsicht();
}

// ---------------------------------------------------------------- Ansicht

function zeigeBaugruppeFlaeche(an) {
  document.body.classList.toggle("bg-offen", an);
  for (const s of ["#tagleiste", "#raster"]) $(s).hidden = an;
  if (an) for (const s of ["#pfad", "#filterzeile", "#stapel", "#listenkopf", "#leer"]) $(s).hidden = true;
  $("#bg-ansicht").hidden = !an;
}

async function oeffneBaugruppe(bid) {
  zustand.baugruppe = bid;
  // Eine vorher im Katalog gewählte Datei gehört nicht zur Baugruppe: rechts beginnt die Übersicht.
  zustand.gewaehlt = null;
  zeigeBaugruppeFlaeche(true);
  document.querySelectorAll("[data-ansicht], [data-ordner], [data-sammlung]").forEach((b) => b.classList.remove("aktiv"));
  document.querySelectorAll("[data-baugruppe]").forEach((b) => b.classList.toggle("aktiv", b.dataset.baugruppe === bid));
  await ladeBaugruppe();
}

function schliesseBaugruppe() {
  if (!zustand.baugruppe) return;
  zustand.baugruppe = "";
  zeigeBaugruppeFlaeche(false);
  document.querySelectorAll("[data-baugruppe]").forEach((b) => b.classList.remove("aktiv"));
  zustand.gewaehlt = null;
  $("#inspektor").innerHTML = `<p class="hinweis">Wähle ein Modell aus, um Details, Vorschau und Tags zu sehen.</p>`;
  ladeModelle();
}

async function ladeBaugruppe() {
  const bid = zustand.baugruppe;
  if (!bid) return;
  let d;
  try { d = await api(`/api/baugruppen/${bid}`); }
  catch { schliesseBaugruppe(); return; }
  if (zustand.baugruppe !== bid) return;
  bgDaten = d;
  // Eine Eingabe an Ort und Stelle (Name, Beschreibung) nicht unter den Fingern wegzeichnen.
  if (document.activeElement?.classList.contains("inline-edit")) return;
  abgleichen($("#bg-ansicht"), zeichneBaugruppe(d));
  // Rechts steht die Übersicht, solange kein einzelnes Teil gewählt ist.
  if (!zustand.gewaehlt) zeigeBgUebersicht();
}

// ---------------------------------------------------------------- Übersicht rechts
//
// Mitte: die Stückliste, sonst nichts. Rechts: was die ganze Baugruppe
// braucht — Filament, Druckzeit, Kaufteile, Ausgabe. Ein Klick auf ein Teil
// zeigt dort das Modell; „← Baugruppe“ bringt die Übersicht zurück.

function zeigeBgUebersicht() {
  const d = bgDaten;
  if (!d || !zustand.baugruppe) return;
  zustand.angezeigt = null;
  if (typeof dreiDModul !== "undefined" && dreiDModul) dreiD().then((v) => v.schliessen());
  const s = d.summen, f = d.fortschritt;
  const leer = !d.positionen.length;
  $("#inspektor").dataset.id = "";
  $("#inspektor").innerHTML = leer ? `<p class="hinweis">Hier erscheint die Übersicht, sobald die Baugruppe Teile hat.</p>` : `
    <div class="ue-kopf"><small>BAUGRUPPE</small><b>${esc(d.name)}</b>
      <span>${f.druck_bedarf} Druckteile · ${f.kauf_bedarf} Kaufteile</span></div>
    ${uebersichtFilament(s)}
    ${uebersichtZeit(s)}
    ${uebersichtKauf(s)}
    <div class="i-titel">AUSGABE</div>
    <div class="i-knoepfe"><button class="knopf akzent" data-bg-aktion="pdf">📄 Stückliste als PDF</button>
      <button class="knopf" data-bg-aktion="csv">CSV</button><button class="knopf" data-bg-aktion="md">Markdown</button></div>`;
}

function uebersichtFilament(s) {
  if (!s.materialien.length) return "";
  const gesamt = s.materialien.reduce((a, m) => a + m.gesamt_g, 0) || 1;
  const segmente = s.materialien.flatMap((m) => m.farben.map((x) =>
    `<i style="width:${(100 * x.gesamt_g) / gesamt}%;${x.farbe ? `background:${esc(x.farbe)}` : ""}" class="${x.farbe ? "" : "offen"}"
        title="${esc(m.material)} ${esc(farbName(x.farbe))}: ${zahl(x.gesamt_g, 0)} g"></i>`)).join("");
  return `<div class="i-titel">FILAMENT · ${zahl(s.gewicht_g, 0)} g${s.gewicht_geschaetzt ? ' <span title="Ohne Slicer-Daten: 1,2 mm Hülle und 15 % Füllung">· teils geschätzt ⓘ</span>' : ""}</div>
    <div class="mischung">${segmente}</div>
    ${s.materialien.map((m) => `<div class="ue-zeile">
      <span class="ue-name"><b>${esc(m.material)}</b>${m.angenommen_g ? '<small title="ohne Angabe — Standard aus den Einstellungen">Std.</small>' : ""}</span>
      <span class="ue-farben">${m.farben.map((x) => tupfer(x.farbe, `${farbName(x.farbe)} ${zahl(x.gesamt_g, 0)} g`)).join("")}</span>
      <span class="ue-wert">${zahl(m.gesamt_g, 0)} g<small>${rollenText(m.rollen)}</small></span></div>`).join("")}`;
}

function uebersichtZeit(s) {
  const mit = s.zeiten.filter((z) => z.je_s), ohne = s.zeiten.filter((z) => !z.je_s);
  if (!mit.length && !ohne.length) return "";
  const gesamt = mit.reduce((a, z) => a + z.gesamt_s, 0) || 1;
  const segmente = mit.map((z) => `<i style="width:${(100 * z.gesamt_s) / gesamt}%;${z.farbe ? `background:${esc(z.farbe)}` : ""}"
      class="${z.farbe ? "" : "offen"} ${z.offen ? "" : "fertig"}" title="${esc(z.name)}: ${dauer(z.gesamt_s)}"></i>`).join("");
  return `<div class="i-titel">DRUCKZEIT · ${dauer(s.zeit_s)}${s.offen_zeit_s < s.zeit_s ? ` · noch ${dauer(s.offen_zeit_s)}` : ""}</div>
    ${mit.length ? `<div class="mischung">${segmente}</div>` : ""}
    ${mit.map((z) => `<div class="ue-zeile ${z.offen ? "" : "fertig"}">
      <span class="ue-name">${tupfer(z.farbe)}<span title="${esc(z.name)}">${esc(z.name)}</span>${z.stueck > 1 ? `<small>${z.stueck}×</small>` : ""}</span>
      <span class="ue-wert">${dauer(z.gesamt_s)}<small>${Math.round((100 * z.gesamt_s) / gesamt)} %</small></span></div>`).join("")}
    ${ohne.length ? `<div class="ue-zeile ohne" title="${ohne.map((z) => esc(z.name)).join(", ")}"><span class="ue-name">Ohne Slicer-Zeit</span>
      <span class="ue-wert">${ohne.length} Teile<small>kommt mit dem G-Code</small></span></div>` : ""}`;
}

function uebersichtKauf(s) {
  if (!s.einkauf.length) return "";
  return `<div class="i-titel">KAUFTEILE — EINKAUFSLISTE</div>
    ${s.einkauf.map((x) => `<div class="ue-zeile ${x.offen ? "" : "fertig"}">
      <span class="ue-name"><span title="${esc(x.name)}">${esc(x.name)}</span></span>
      <span class="ue-wert">${x.bedarf}${x.einheit === "Stück" ? "×" : " " + esc(x.einheit)}${x.offen ? "" : "<small>✓ da</small>"}</span></div>`).join("")}`;
}

// Die Ansicht einer Baugruppe: oben das Schriftfeld (wie bei einer technischen Zeichnung), darunter Reiter.
// Stückliste ist eine nummerierte Tabelle in der Reihenfolge des PDFs; Notizen und Anhänge sind als
// Aufteilung vorgesehen, aber noch nicht verdrahtet.
let bgReiter = ["stueckliste", "notizen", "anhaenge"].includes(localStorageLesen("bg-reiter")) ? localStorageLesen("bg-reiter") : "stueckliste";

function schriftfeld(d) {
  const f = d.fortschritt, s = d.summen;
  const mats = s.materialien.map((m) => m.material).join(" · ");
  const feld = (name, wert, unter) => `<div class="sf-feld"><small>${name}</small><b>${wert}</b><span>${unter || "&nbsp;"}</span></div>`;
  return `<div class="sf-felder">
    ${feld("DRUCKTEILE", f.druck_bedarf, "Stück gesamt")}
    ${feld("KAUFTEILE", f.kauf_bedarf, `${s.einkauf.length} ${s.einkauf.length === 1 ? "Sorte" : "Sorten"}`)}
    ${feld("FILAMENT", `${zahl(s.gewicht_g, 0)} g`, esc(mats) + (s.gewicht_geschaetzt ? " *" : ""))}
    ${feld("DRUCKZEIT", s.zeit_s ? dauer(s.zeit_s) : "–", s.ohne_zeit ? `${s.ohne_zeit} ohne Zeit` : "aus dem Slicer")}
    ${feld("STECKT IN", d.verwendet_in.length ? d.verwendet_in.map((b) => `<a href="#" data-baugruppe="${esc(b.id)}">${esc(b.name)}</a>`).join(", ") : "–",
           d.verwendet_in.length ? d.verwendet_in.map((b) => `${b.menge}×`).join(", ") + (d.exemplare > 1 ? ` · ${d.exemplare} Sätze` : "") : "")}
  </div>`;
}

function zeichneBaugruppe(d) {
  const titelbild = d.positionen.filter((p) => p.art === "modell").map((p) => bildUrl(p)).find(Boolean);
  const offenDruck = d.fortschritt.druck_bedarf - d.fortschritt.druck_erledigt;
  const leer = !d.positionen.length;
  const reiter = [["stueckliste", "Stückliste", d.positionen.length || ""], ["notizen", "Notizen", ""], ["anhaenge", "Anhänge", ""]];
  return `
  <div class="sf">
    <div class="sf-bild">${titelbild ? `<img src="${titelbild}" alt="">` : "🧩"}</div>
    <div class="sf-kopf">
      <small>BAUGRUPPE</small>
      <h2 class="bg-titel" id="bg-name" title="Klicken zum Umbenennen">${esc(d.name)}</h2>
      <div class="bg-beschreibung" id="bg-beschreibung" title="Klicken zum Bearbeiten">${d.beschreibung ? esc(d.beschreibung) : '<span class="dim">Beschreibung hinzufügen …</span>'}</div>
    </div>
    ${leer ? "" : schriftfeld(d)}
  </div>
  <div class="bg-reiter" role="tablist">${reiter.map(([k, t, n]) =>
    `<button role="tab" data-bg-reiter="${k}" class="${k === bgReiter ? "an" : ""}">${t}${n ? ` <span class="d-zahl">${n}</span>` : ""}${k === "stueckliste" ? "" : ' <small class="folgt">folgt</small>'}</button>`).join("")}</div>
  ${bgReiter === "notizen" ? notizenTafel() : bgReiter === "anhaenge" ? anhaengeTafel() : stuecklisteTafel(d, leer, offenDruck)}`;
}

function stuecklisteTafel(d, leer, offenDruck) {
  if (leer) return `
  <div class="bg-leer">
    <h3>Eine Baugruppe ist eine Stückliste</h3>
    <ol>
      <li><b>Druckteile hinzufügen</b> — hier wählen, oder im Katalog Kacheln auf „${esc(d.name)}“ links ziehen.</li>
      <li><b>Mengen einstellen</b> — 4 Arme, 8 Halter. Heisst eine Datei <code>Arm_x4</code>, steht die 4 schon da.</li>
      <li><b>Kaufteile dazu</b> — Schrauben, Muttern, Magnete, Lager aus dem Katalog.</li>
    </ol>
    <p class="dim">Dann zeigt partAtlas, wie viel Filament welcher Farbe du brauchst und was du kaufen musst.</p>
    <div class="i-knoepfe"><button class="knopf akzent" data-bg-aktion="teile">＋ Druckteile wählen</button>
      <button class="knopf" data-bg-aktion="kaufteile">＋ Kaufteile</button><button class="knopf" data-bg-aktion="eigene">＋ Eigene Komponente</button><button class="knopf" data-bg-aktion="unter">＋ Unterbaugruppe</button></div>
  </div>`;
  return `
  <div class="bg-werkzeug">
    <button class="knopf" data-bg-aktion="teile">＋ Druckteile</button>
    <button class="knopf" data-bg-aktion="kaufteile">＋ Kaufteile</button>
    <button class="knopf" data-bg-aktion="eigene">＋ Eigene Komponente</button>
    <button class="knopf" data-bg-aktion="unter">＋ Unterbaugruppe</button>
    <span class="bg-luecke"></span>
    <button class="knopf" data-ab-phase="2" data-bg-aktion="warteschlange" ${offenDruck ? "" : "disabled"}>☰ Fehlende in die Warteschlange</button>
    <button class="knopf gefahr" data-bg-aktion="loeschen">Baugruppe löschen</button>
  </div>
  <div class="bom">
    <div class="bom-kopf"><span>POS.</span><span></span><span>BENENNUNG</span><span>MENGE</span><span>MATERIAL</span><span class="re">GEWICHT</span><span></span></div>
    ${d.positionen.map((p, i) => position(p, i + 1)).join("")}
  </div>`;
}

// Noch nicht verdrahtet: die Aufteilung steht, damit sich die Ansicht nicht mehr umbauen muss, wenn es kommt.
function notizenTafel() {
  return `<div class="bg-tafel">
    <div class="bg-tafel-kopf"><div class="segment"><button class="an" disabled>Schreiben</button><button disabled>Vorschau</button></div>
      <span class="dim">Markdown</span></div>
    <div class="bg-platz"><b>Konstruktionsnotizen</b><span>Maße, Toleranzen, Entwürfe, Montagehinweise — in Markdown geschrieben, an dieser Baugruppe gespeichert.</span></div>
  </div>`;
}

function anhaengeTafel() {
  return `<div class="bg-tafel">
    <div class="bg-tafel-kopf"><button class="knopf" disabled title="Kommt als Nächstes">＋ Datei anhängen</button><span class="dim">z. B. Montageanleitung, Konstruktionszeichnung</span></div>
    <div class="anh-kopf"><span></span><span>TYP</span><span>NAME</span><span class="re">GRÖSSE</span><span>STAND</span></div>
    <div class="bg-platz"><b>Dateien zur Baugruppe</b><span>Montageanleitungen, Konstruktionszeichnungen (PDF, CorelDRAW, SVG, DXF …), Datenblätter — hier ablegen. Die Dateien bleiben unverändert im Bestand.</span></div>
  </div>`;
}

function position(p, nr) {
  const r = esc(p.ref);
  let vorschau, name, unter;
  if (p.art === "modell") {
    const url = bildUrl(p);
    vorschau = url ? `<img loading="lazy" src="${url}" alt="">` : "🧊";
    name = `${esc(p.name)}<span class="endung">${esc(endung[p.format] || "")}</span>`;
    // Ein Entwurf in der Stückliste ist meist ein Versehen: sagen, nicht still tauschen.
    unter = [p.fehlt ? "⚠ Datei fehlt" : "", p.entwurf ? "✎ Entwurf — ist das der richtige Stand?" : "", masse(p.masse), p.je_gewicht_g ? `je ${zahl(p.je_gewicht_g, 1)} g${p.je_geschaetzt ? " *" : ""}` : ""].filter(Boolean).join(" · ");
  } else if (p.art === "kaufteil") {
    vorschau = symbolFuer(p.kategorie);
    name = esc(p.name);
    unter = `${esc(p.kategorie || "")}${p.einheit && p.einheit !== "Stück" ? " · in " + esc(p.einheit) : ""}`;
  } else if (p.art === "eigen") {
    vorschau = p.eigen_bild ? `<img loading="lazy" src="/api/eigene/${esc(p.id)}/bild?t=1" alt="">` : "🔩";
    name = esc(p.name);
    unter = ["Eigene Komponente", p.eigen_art, p.eigen_masse, p.eigen_datei].filter(Boolean).map(esc).join(" · ");
  } else {
    vorschau = "🧩";
    name = `${esc(p.name)} ›`;
    unter = `Baugruppe · ${p.unter_positionen} Positionen`;
  }
  const material = p.art === "modell"
    ? `<button class="mat-knopf ${p.material_angenommen ? "standard" : ""}" data-bg-material="${r}"
        title="${p.material_angenommen ? "Keine Angabe — Standard aus den Einstellungen. Klicken zum Festlegen." : "Material und Farbe festlegen"}">${tupfer(p.farbe)}${esc(p.material)}</button>` : "";
  const gewicht = p.art === "modell" && p.je_gewicht_g ? `${zahl(p.je_gewicht_g * p.menge, 0)} g${p.je_geschaetzt ? " *" : ""}` : "";
  const zeile = p.art === "eigen" ? `data-bg-eigen="${esc(p.id)}" title="Bearbeiten"` : p.art === "modell" ? `data-bg-modell="${esc(p.id)}" title="Im Inspektor zeigen"`
    : p.art === "baugruppe" ? `data-bg-unter="${esc(p.id)}" title="Öffnen"` : "";
  return `<div class="bz ${p.art === "modell" && zustand.gewaehlt === p.id ? "gewaehlt" : ""}" ${zeile}>
    <span class="bz-nr">${nr}</span>
    <div class="vorschau">${vorschau}</div>
    <div class="bz-name"><b>${name}</b><small>${unter}</small>${p.notiz ? `<small class="notiz-text" title="Notiz">${esc(p.notiz)}</small>` : ""}</div>
    <span class="stepper"><button data-bg-menge="-1" data-ref="${r}">−</button><span>${p.menge}×</span><button data-bg-menge="1" data-ref="${r}">＋</button></span>
    <div class="bz-mat">${material}</div>
    <span class="bz-gew mono">${gewicht}</span>
    <div class="bz-akt">${p.art === "modell" ? hoverAktionen(p) : ""}<button class="hv-btn weg" data-bg-weg="${r}" title="aus der Baugruppe nehmen">×</button></div></div>`;
}

// ---------------------------------------------------------------- Ändern

const bid = () => zustand.baugruppe;

document.addEventListener("click", (e) => {
  const r = e.target.closest?.("[data-bg-reiter]");
  if (!r || !bgDaten) return;
  bgReiter = r.dataset.bgReiter;
  localStorageSchreiben("bg-reiter", bgReiter);
  abgleichen($("#bg-ansicht"), zeichneBaugruppe(bgDaten));
});

async function positionAendern(ref, werte) {
  try { await api(`/api/baugruppen/${bid()}/positionen`, { method: "PATCH", body: { ref, ...werte } }); }
  catch (e) { toast(e.message); }
  ladeBaugruppe();
}

function positionVon(ref) { return bgDaten?.positionen.find((p) => p.ref === ref); }

async function neueBaugruppe(modelle = []) {
  const vorschlaege = zustand.bgVorschlaege || [];
  const a = await dialog(`<h2>Neue Baugruppe</h2>
    <p class="dim">Eine Stückliste: welche Teile, wie oft, welche Schrauben — und was davon schon fertig ist.</p>
    <input type="text" id="bg-neu-name" placeholder="z. B. Drohne V2, Voron Stealthburner, Werkzeugwand">
    ${modelle.length ? `<p>Mit den <b>${modelle.length} gewählten Modellen</b>. Mengen aus Dateinamen wie <code>Arm_x4</code> werden übernommen.</p>` : ""}
    ${!modelle.length && vorschlaege.length ? `<div class="i-titel">ODER AUS EINEM ORDNER</div>${vorschlaege.map((v) => `
      <div class="vorschlag"><div><b>${esc(v.name)}</b><small>${esc(v.ordner.split("/").slice(1).join("/"))} · ${v.anzahl} Modelle${v.mengen_im_namen ? ` · ${v.mengen_im_namen} mit Menge im Namen` : ""}</small></div>
        <button type="button" class="knopf" data-vorschlag="${esc(v.ordner)}">Als Baugruppe</button></div>`).join("")}` : ""}
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Anlegen</button></div>`);
  if (a !== "ja") return;
  try {
    const { id } = await api("/api/baugruppen", { method: "POST", body: { name: $("#bg-neu-name").value, modelle } });
    await ladeBaugruppenLeiste();
    oeffneBaugruppe(id);
  } catch (e) { toast(e.message); }
}

async function ausVorschlag(ordner) {
  $("#dialog").close("nein");
  try {
    const { id } = await api("/api/baugruppen", { method: "POST", body: { aus_ordner: ordner } });
    await ladeBaugruppenLeiste();
    oeffneBaugruppe(id);
    toast("Baugruppe angelegt — prüfe die Mengen.");
  } catch (e) { toast(e.message); }
}

// Auswahllisten: bleiben offen, man kann mehrere Teile nacheinander hinzufügen.
async function waehler(art) {
  const d = $("#dialog");
  d.classList.add("breit");
  const kaufteile = art === "kaufteile";
  const kategorien = ["Schrauben", "Muttern", "Scheiben", "Gewindeeinsätze", "Magnete", "Lager", "Profil & Linear", "Elektronik", "Kleinteile", "Eigene"];
  const titel = { teile: "Druckteile hinzufügen", kaufteile: "Kaufteile hinzufügen", unter: "Unterbaugruppe hinzufügen" }[art];
  const warten = dialog(`<h2>${titel}</h2>
    <input type="text" id="w-suche" data-enter="" placeholder="${kaufteile ? "Suchen, z. B. m3x10, Magnet 6x2, 608 …" : "Modell suchen …"}" autocomplete="off">
    ${kaufteile ? `<div class="kategorien">${kategorien.map((k) => `<button type="button" class="chip" data-w-kat="${esc(k)}">${esc(k)}</button>`).join("")}</div>` : ""}
    <div class="waehler" id="w-liste"></div>
    ${kaufteile ? `<p class="dim" style="margin-top:8px">Nicht dabei? <input type="text" id="w-eigen" data-enter="#w-eigen-knopf" placeholder="Eigenes Kaufteil, z. B. Propeller 5 Zoll" style="width:60%"> <button type="button" class="knopf" id="w-eigen-knopf">Anlegen</button></p>` : ""}
    <div class="knoepfe"><button class="knopf akzent" value="fertig">Fertig</button></div>`);
  let kategorie = "";
  const laden = async () => {
    const q = $("#w-suche").value.trim();
    let zeilen = [];
    if (kaufteile) {
      const liste = await api(`/api/kaufteile?q=${encodeURIComponent(q)}&kategorie=${encodeURIComponent(kategorie)}`);
      // Ohne Suche und Kategorie alles zeigen: sortiert nach Kategorie würden 120 Zeilen nur Schrauben ergeben.
      zeilen = liste.map((t) => ({ ref: `PURCHASED_PART/${t.id}`, name: t.name, klein: [t.kategorie, t.norm].filter(Boolean).join(" · "), bild: null, symbol: symbolFuer(t.kategorie) }));
    } else if (art === "unter") {
      zeilen = (await api("/api/baugruppen")).filter((b) => b.id !== bid() && b.name.toLowerCase().includes(q.toLowerCase()))
        .map((b) => ({ ref: `ASSEMBLY/${b.id}`, name: b.name, klein: `${b.positionen} Positionen`, bild: null }));
    } else {
      const liste = await api(`/api/modelle?q=${encodeURIComponent(q)}`);
      zeilen = liste.slice(0, 120).map((m) => ({ ref: `MODEL_ASSET/${m.id}`, name: m.name + (endung[m.format] || ""),
        klein: [m.ordner[0]?.split("/").slice(1).join("/"), masse(m.masse)].filter(Boolean).join(" · "), bild: bildUrl(m) }));
    }
    const drin = new Set((bgDaten?.positionen || []).map((p) => p.ref));
    $("#w-liste").innerHTML = zeilen.map((z) => `<div class="w-zeile">
      ${z.bild ? `<img loading="lazy" src="${z.bild}" alt="">` : `<div class="mini" style="display:grid;place-items:center">${z.symbol || ""}</div>`}
      <div><b>${esc(z.name)}</b><small>${esc(z.klein || "")}</small></div>
      <input type="number" min="1" value="1" data-enter="" data-w-menge="${esc(z.ref)}">
      <button type="button" class="plus ${drin.has(z.ref) ? "ok" : ""}" data-w-plus="${esc(z.ref)}" title="${drin.has(z.ref) ? "ist drin — Klick nimmt es wieder heraus" : "hinzufügen"}"><span class="a">${drin.has(z.ref) ? "✓" : "＋"}</span><span class="b">−</span></button></div>`).join("")
      || '<div class="pos-leer">Nichts gefunden.</div>';
  };
  let zeit;
  $("#w-suche").addEventListener("input", () => { clearTimeout(zeit); zeit = setTimeout(laden, 150); });
  $("#w-liste").addEventListener("click", async (e) => {
    const plus = e.target.closest("[data-w-plus]");
    if (!plus) return;
    if (plus.disabled) return;
    const ref = plus.dataset.wPlus;
    const drin = plus.classList.contains("ok");
    const menge = Number(document.querySelector(`[data-w-menge="${CSS.escape(ref)}"]`)?.value || 1);
    plus.disabled = true;
    try {
      // Dasselbe Knöpfchen setzt und nimmt zurück: ✓ heisst „ist drin“, nochmal klicken entfernt.
      if (drin) await api(`/api/baugruppen/${bid()}/positionen?ref=${encodeURIComponent(ref)}`, { method: "DELETE" });
      else await api(`/api/baugruppen/${bid()}/positionen`, { method: "POST", body: { ref, menge } });
      plus.classList.toggle("ok", !drin);
      plus.querySelector(".a").textContent = drin ? "＋" : "✓";
      plus.title = drin ? "hinzufügen" : "ist drin — Klick nimmt es wieder heraus";
      await ladeBaugruppe();
    } catch (err) { toast(err.message); }
    plus.disabled = false;
  });
  d.querySelector(".kategorien")?.addEventListener("click", (e) => {
    const k = e.target.closest("[data-w-kat]");
    if (!k) return;
    kategorie = kategorie === k.dataset.wKat ? "" : k.dataset.wKat;
    d.querySelectorAll("[data-w-kat]").forEach((x) => x.classList.toggle("aktiv", x.dataset.wKat === kategorie));
    laden();
  });
  $("#w-eigen-knopf")?.addEventListener("click", async () => {
    const name = $("#w-eigen").value.trim();
    if (!name) return;
    try {
      const { id } = await api("/api/kaufteile", { method: "POST", body: { name } });
      await api(`/api/baugruppen/${bid()}/positionen`, { method: "POST", body: { ref: `PURCHASED_PART/${id}`, menge: 1 } });
      $("#w-eigen").value = "";
      kategorie = "Eigene";
      await ladeBaugruppe();
      laden();
    } catch (err) { toast(err.message); }
  });
  await laden();
  $("#w-suche").focus();
  await warten;
  d.classList.remove("breit");
}

async function materialWahl(titel, vorher = {}) {
  const liste = bgDaten?.materialien || ["PLA", "PETG", "ABS", "ASA", "TPU"];
  const a = await dialog(`<h2>${esc(titel)}</h2>
    <div class="i-titel">MATERIAL</div>
    <div class="kategorien">${liste.map((m) => `<button type="button" class="chip ${m === vorher.material ? "aktiv" : ""}" data-mw-mat="${esc(m)}">${esc(m)}</button>`).join("")}</div>
    <div class="i-titel">FARBE</div>
    <div class="farbfelder">${FARBEN.map(([n, h]) => `<button type="button" class="farbfeld ${h === vorher.farbe ? "aktiv" : ""}" data-mw-farbe="${h}" title="${n}" style="background:${h}"></button>`).join("")}
      <label class="dim" style="display:inline-flex;gap:6px;align-items:center">eigene <input type="color" id="mw-eigen" value="${esc(vorher.farbe || "#888888")}"></label>
      <button type="button" class="knopf" data-mw-farbe="">keine</button></div>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Übernehmen</button></div>`);
  return a === "ja" ? { material: mwWahl.material, farbe: mwWahl.farbe } : null;
}
const mwWahl = { material: null, farbe: null };
const vfWahl = { farbe: null };          // Farbe der Vorschaubilder (Einstellungen › Ansicht)
document.addEventListener("click", (e) => {
  const f = e.target.closest?.("[data-vf-farbe]");
  if (!f) return;
  vfWahl.farbe = f.dataset.vfFarbe || null;
  document.querySelectorAll("[data-vf-farbe]").forEach((x) => x.classList.toggle("aktiv", x === f));
});
document.addEventListener("click", (e) => {
  const m = e.target.closest?.("[data-mw-mat]"), f = e.target.closest?.("[data-mw-farbe]");
  if (m) { mwWahl.material = m.dataset.mwMat; document.querySelectorAll("[data-mw-mat]").forEach((x) => x.classList.toggle("aktiv", x === m)); }
  if (f) { mwWahl.farbe = f.dataset.mwFarbe || null; document.querySelectorAll("[data-mw-farbe]").forEach((x) => x.classList.toggle("aktiv", x === f)); }
});
document.addEventListener("input", (e) => {
  if (e.target.id === "mw-eigen") { mwWahl.farbe = e.target.value; document.querySelectorAll("[data-mw-farbe]").forEach((x) => x.classList.remove("aktiv")); }
});

async function bgAktion(aktion) {
  const d = bgDaten;
  switch (aktion) {
    case "teile": case "kaufteile": case "unter": return waehler(aktion);
    case "eigene": return eigeneWaehlen();      // siehe eigene.js

    case "warteschlange": {
      const { eingereiht } = await api(`/api/baugruppen/${bid()}/warteschlange`, { method: "POST" });
      return toast(`${eingereiht} fehlende Druckteile in der Warteschlange.`);
    }
    case "csv": case "md": return (window.location.href = `/api/baugruppen/${bid()}/export?format=${aktion}`);
    case "pdf": return window.open(`/api/baugruppen/${bid()}/export?format=pdf`, "_blank", "noopener");
    case "loeschen": {
      const a = await dialog(`<h2>„${esc(d.name)}“ löschen?</h2><p>Nur die Stückliste geht. Modelle, Dateien und Kaufteile bleiben.</p>
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Löschen</button></div>`);
      if (a !== "ja") return;
      await api(`/api/baugruppen/${bid()}`, { method: "DELETE" });
      schliesseBaugruppe();
      return ladeBaugruppenLeiste();
    }
  }
}

// ---------------------------------------------------------------- Ereignisse

// Navigation weg von der Baugruppe: jeder andere Eintrag links schliesst sie.
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-ansicht], [data-ordner], [data-sammlung], [data-tag], [data-format], [data-rail], #filter-weg")) schliesseBaugruppe();
}, true);

document.addEventListener("click", async (e) => {
  const t = e.target;
  if (t.closest("#bg-tipp-x")) { localStorageSchreiben("bgtipp", String((zustand.bgVorschlaege || []).length)); return ladeBaugruppenLeiste(); }
  if (t.closest("#bg-tipp") || t.id === "baugruppe-neu" || t.id === "baugruppe-neu-2") return neueBaugruppe();
  const vor = t.closest("[data-vorschlag]");
  if (vor) return ausVorschlag(vor.dataset.vorschlag);
  const b = t.closest("[data-baugruppe]");
  if (b) { e.preventDefault(); return navigiere(() => oeffneBaugruppe(b.dataset.baugruppe)); }
  if (t.closest("#bg-zurueck")) { zustand.gewaehlt = null; return zeigeBgUebersicht(); }
  const aktRechts = t.closest("#inspektor [data-bg-aktion]");
  if (aktRechts) return bgAktion(aktRechts.dataset.bgAktion);
  if (!t.closest("#bg-ansicht")) return;
  const akt = t.closest("[data-bg-aktion]");
  if (akt) return bgAktion(akt.dataset.bgAktion);
  const m = t.closest("[data-bg-menge]");
  if (m) { const p = positionVon(m.dataset.ref); return positionAendern(p.ref, { menge: Math.max(1, p.menge + Number(m.dataset.bgMenge)) }); }
  const z = t.closest("[data-bg-zaehlen]");
  if (z) { const p = positionVon(z.dataset.ref); return positionAendern(p.ref, { erledigt: Math.max(0, Math.min(p.bedarf, p.erledigt + Number(z.dataset.bgZaehlen))) }); }
  const v = t.closest("[data-bg-voll]");
  if (v) { const p = positionVon(v.dataset.bgVoll); return positionAendern(p.ref, { erledigt: p.bedarf }); }
  const w = t.closest("[data-bg-weg]");
  if (w) {
    await api(`/api/baugruppen/${bid()}/positionen?ref=${encodeURIComponent(w.dataset.bgWeg)}`, { method: "DELETE" });
    return ladeBaugruppe();
  }
  const mat = t.closest("[data-bg-material]");
  if (mat) {
    const p = positionVon(mat.dataset.bgMaterial);
    Object.assign(mwWahl, { material: p.material || null, farbe: p.farbe || null });
    const w = await materialWahl(`Material und Farbe: ${p.name}`, p);
    if (w) return positionAendern(p.ref, { material: w.material || "", farbe: w.farbe || "" });
    return;
  }
  const mod = t.closest("[data-bg-modell]");
  if (mod) {
    document.querySelectorAll(".bz[data-bg-modell]").forEach((r) => r.classList.toggle("gewaehlt", r === mod));
    return waehle(mod.dataset.bgModell);
  }
  const unter = t.closest("[data-bg-unter]");
  if (unter) return navigiere(() => oeffneBaugruppe(unter.dataset.bgUnter));
  if (t.closest("#bg-name")) {
    return inlineBearbeiten(t.closest("#bg-name"), { wert: bgDaten.name, speichern: (name) => name.trim() && api(`/api/baugruppen/${bid()}`, { method: "PATCH", body: { name } }) });
  }
  if (t.closest("#bg-beschreibung")) {
    return inlineBearbeiten(t.closest("#bg-beschreibung"), { wert: bgDaten.beschreibung || "", mehrzeilig: true, platzhalter: "Beschreibung hinzufügen …",
      speichern: (beschreibung) => api(`/api/baugruppen/${bid()}`, { method: "PATCH", body: { beschreibung } }) });
  }
});

// Name und Beschreibung werden dort bearbeitet, wo sie stehen: ein Klick
// macht aus dem Text ein Feld, Verlassen speichert, Esc verwirft. Die
// Beschreibung ist mehrzeilig (Enter = neue Zeile, Strg+Enter = fertig).
function inlineBearbeiten(el, { wert, platzhalter = "", mehrzeilig = false, speichern }) {
  const feld = document.createElement(mehrzeilig ? "textarea" : "input");
  feld.className = `inline-edit ${el.className}`.replace("bg-beschreibung", "bg-beschreibung-feld");
  feld.value = wert;
  feld.placeholder = platzhalter;
  const anpassen = () => { if (mehrzeilig) { feld.style.height = "auto"; feld.style.height = feld.scrollHeight + "px"; } };
  el.replaceWith(feld);
  anpassen();
  feld.focus();
  feld.setSelectionRange(feld.value.length, feld.value.length);
  let fertig = false;
  const abschluss = async (sichern) => {
    if (fertig) return;
    fertig = true;
    feld.blur();
    try { if (sichern && feld.value !== wert) await speichern(feld.value); }
    catch (err) { toast(err.message); }
    $("#bg-ansicht")._html = null;      // das Feld steht nicht im gemerkten HTML
    ladeBaugruppe();
  };
  feld.addEventListener("input", anpassen);
  feld.addEventListener("blur", () => abschluss(true));
  feld.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { e.preventDefault(); abschluss(false); }
    else if (e.key === "Enter" && (!mehrzeilig || e.ctrlKey || e.metaKey)) { e.preventDefault(); abschluss(true); }
  });
}

// Aus Auswahl, Sammlung, Inspektor — aufgerufen aus app.js.
async function zuBaugruppe(modelle) {
  const liste = zustand.baugruppen || [];
  const a = await dialog(`<h2>${modelle.length > 1 ? modelle.length + " Modelle" : "Modell"} zu einer Baugruppe</h2>
    <select id="bg-ziel">${liste.map((b) => `<option value="${esc(b.id)}">${esc(b.name)}</option>`).join("")}<option value="__neu">Neue Baugruppe …</option></select>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Hinzufügen</button></div>`);
  if (a !== "ja") return;
  const ziel = $("#bg-ziel").value;
  if (ziel === "__neu") return neueBaugruppe(modelle);
  await api(`/api/baugruppen/${ziel}/positionen`, { method: "POST", body: { refs: modelle.map((m) => `MODEL_ASSET/${m}`) } })
    .then(() => toast("Zur Baugruppe hinzugefügt.")).catch((e) => toast(e.message));
}

ladeBaugruppenLeiste();

// ---------------------------------------------------------------- Einstellungen
//
// Was gilt, wo nichts angegeben ist. Wer nur PLA+ druckt, stellt das
// einmal ein und muss nie wieder ein Teil anfassen.

async function einstellungen() {
  const e = await api("/api/einstellungen");
  Object.assign(progWahl, { ...e.programm, geaendert: {} });
  Object.assign(mwWahl, { material: e.gilt.material, farbe: e.gilt.farbe });
  vfWahl.farbe = e.vorschau_farbe || null;
  $("#dialog").classList.add("einst");
  // Alle Abschnitte stehen im Dialog, nur einer ist sichtbar: so gilt beim Speichern,
  // was in jedem eingestellt wurde, auch wenn man zwischendurch gewechselt hat.
  const abschnitte = [
    ["vorgaben", "Vorgaben", `
      <p class="dim">Was partAtlas annimmt, wenn ein Druckteil keine Angabe hat (kein Slicer-Wert, nichts festgelegt).</p>
      <div class="i-titel">STANDARDMATERIAL</div>
      <div class="kategorien">${e.materialien.map((m) => `<button type="button" class="chip ${m === e.gilt.material ? "aktiv" : ""}" data-mw-mat="${esc(m)}">${esc(m)}</button>`).join("")}</div>
      <div class="i-titel">STANDARDFARBE</div>
      <div class="farbfelder">${FARBEN.map(([n, h]) => `<button type="button" class="farbfeld ${h === e.gilt.farbe ? "aktiv" : ""}" data-mw-farbe="${h}" title="${n}" style="background:${h}"></button>`).join("")}
        <button type="button" class="knopf ${e.gilt.farbe ? "" : "aktiv"}" data-mw-farbe="">keine</button></div>
      <div class="i-titel">ROLLENGRÖSSE</div>
      <label>Gramm je Rolle <input type="number" id="ein-rolle" min="100" max="10000" step="50" value="${e.gilt.rolle_g}" style="width:90px"></label>`],
    ["ansicht", "Ansicht", `
      <div class="i-titel">KACHELN</div>
      <label><input type="checkbox" id="ein-format-etikett" ${zustand.formatEtikett ? "checked" : ""}> Dateiformat auf dem Vorschaubild zeigen</label>
      <p class="dim">Unten links auf jeder Kachel, etwa STL, 3MF, STEP — in der Farbe des Formats.</p>
      <div class="i-titel">UNTER DEM NAMEN</div>
      ${Object.entries(KACHEL_ZEILEN).map(([k, z]) => `<label><input type="checkbox" data-kachel-zeile="${k}" ${zustand.kachelZeilen.includes(k) ? "checked" : ""}> ${z.titel}</label>`).join("")}
      <p class="dim">Mehr Zeilen machen die Kachel etwas höher. Gilt für diesen Browser und wirkt sofort.</p>
      <div class="i-titel">FARBE DER VORSCHAUBILDER</div>
      <div class="farbfelder">${FARBEN.map(([n, h]) => `<button type="button" class="farbfeld ${h === e.vorschau_farbe ? "aktiv" : ""}" data-vf-farbe="${h}" title="${n}" style="background:${h}"></button>`).join("")}
        <button type="button" class="knopf ${e.vorschau_farbe ? "" : "aktiv"}" data-vf-farbe="">Vorgabe</button></div>
      <p class="dim">Für Modelle, deren Datei keine eigene Farbe mitbringt — Farben aus der Datei gehen immer vor.
        Vorgesehen für eine spätere Fassung: die gewählte Farbe wird gespeichert, die Bilder ändern sich noch nicht.</p>`],
    ["einlesen", "Einlesen", `
      <div class="i-titel">TAGS</div>
      <label><input type="checkbox" id="ein-autotags" ${e.auto_tags ? "checked" : ""}> Tags aus dem Dateinamen vorschlagen (wie im 3MF Katalog)</label>
      <p class="dim">Gilt für neu eingelesene Dateien. Vorhandene Tags bleiben.</p>
      <div class="i-titel">EINLESEN</div>
      <label><input type="checkbox" id="ein-start" ${e.scan_beim_start ? "checked" : ""}> Beim Start einlesen</label>
      <p class="dim">Aus (Vorgabe): partAtlas liest nur ein, wenn du es auslöst — mit ⟳ neben „Bibliothek“. Bei einer grossen Bibliothek auf einer langsamen
        Platte bleibt der Start ruhig. Dateien, die du ausserhalb verschoben oder gelöscht hast, erscheinen dann erst nach dem nächsten Einlesen.</p>
      <div class="i-titel">FREECAD-DOKUMENTE (FCSTD)</div>
      <label>Über FreeCAD einlesen für Maße, Gewicht und 3D-Ansicht
        <select id="ein-fcstd"><option value="" ${!e.fcstd_freecad ? "selected" : ""}>Fragen</option>
          <option value="ja" ${e.fcstd_freecad === "ja" ? "selected" : ""}>Ja, immer</option>
          <option value="nein" ${e.fcstd_freecad === "nein" ? "selected" : ""}>Nein, nie</option></select></label>
      <p class="dim">Ein FreeCAD-Dokument kann Programmcode enthalten, der beim Laden ausgeführt wird — als würdest du es in FreeCAD öffnen.
        Nur für Dateien aus Quellen, denen du vertraust.</p>
      <div class="i-titel">PROTOKOLL</div>
      <p class="dim">Was partAtlas beim Einlesen und bei Fehlern meldet, steht auch in der Datei <code>partatlas.log</code> im Bestand.
        Bei einem Fehler: diese Datei schicken.</p>
      <button type="button" class="knopf" id="ein-protokoll">Protokoll im Dateimanager zeigen</button>
      <div class="i-titel">SICHERUNGEN</div>
      <p class="dim">partAtlas sichert die Datenbank (Modelle, Tags, Drucke, Baugruppen, Ordner) beim Start und vor jeder Massenaktion,
        etwa bevor ein Ordner entfernt wird. Es löscht nie Dateien in deinen Ordnern. Zurückholen bei beendetem partAtlas:
        <code>python -m partatlas.sicherung --zurueck NAME</code>.</p>
      <div id="ein-sicherungen" class="dim">…</div>
      <div class="knoepfe" style="justify-content:flex-start"><button type="button" class="knopf" id="ein-sichern">Jetzt sichern</button>
        <button type="button" class="knopf" id="ein-sicherungen-zeigen">Ordner zeigen</button></div>`],
    ["pdf", "PDF-Export", `
      <p class="dim">Was die Stückliste einer Baugruppe als PDF enthält („Stückliste als PDF“ in der Baugruppe).</p>
      <div class="i-titel">ABSCHNITTE</div>
      ${PDF_FELDER.slice(0, 5).map(([k, t]) => pdfSchalter(k, t, e.pdf)).join("")}
      <div class="i-titel">DARSTELLUNG</div>
      ${PDF_FELDER.slice(5).map(([k, t]) => pdfSchalter(k, t, e.pdf)).join("")}`],
    ["programme", "Programme", `
      <p class="dim">Mit diesen beiden Programmen öffnet partAtlas ein Modell: STEP- und FCStd-Dateien im CAD, alles andere im Slicer.
        Was auf diesem Rechner installiert ist, steht schon da.</p>
      <div id="prog-teil">${progTeil()}</div>`],
  ];
  const gemerkt = localStorageLesen("einstellungen-abschnitt");
  const zeige = abschnitte.some(([k]) => k === gemerkt) ? gemerkt : abschnitte[0][0];
  const a = await dialog(`<div class="ein">
    <nav class="ein-nav">${abschnitte.map(([k, t]) => `<button type="button" data-ein="${k}" class="${k === zeige ? "aktiv" : ""}">${t}</button>`).join("")}</nav>
    <div class="ein-haupt">
      <h2 id="ein-titel">${abschnitte.find(([k]) => k === zeige)[1]}</h2>
      <div class="ein-inhalt">${abschnitte.map(([k, , h]) => `<section data-ein-teil="${k}" ${k === zeige ? "" : "hidden"}>${h}</section>`).join("")}</div>
      <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Speichern</button></div>
    </div></div>`);
  $("#dialog").classList.remove("einst");
  if (a !== "ja") return;
  try {
    await api("/api/einstellungen", { method: "PUT", body: { standard_material: mwWahl.material, standard_farbe: mwWahl.farbe, vorschau_farbe: vfWahl.farbe,
                                                          rolle_g: Number($("#ein-rolle").value), auto_tags: $("#ein-autotags").checked, scan_beim_start: $("#ein-start").checked,
                                                          fcstd_freecad: $("#ein-fcstd").value || null,
                                                          programm: progWahl.geaendert,
                                                          pdf: Object.fromEntries([...document.querySelectorAll("[data-pdf]")].map((c) => [c.dataset.pdf, c.checked])) } });
    toast("Gespeichert.");
    programmeAktualisieren();
    ladeBaugruppe();
    if ($("#inspektor").dataset.id) waehle($("#inspektor").dataset.id);
  } catch (err) { toast(err.message); }
}

const PDF_FELDER = [["struktur", "Strukturstückliste (jede Ebene mit Positionsnummer)"], ["mengen", "Mengenübersicht der Druckteile"],
  ["einkauf", "Einkaufsliste der Kaufteile"], ["filament", "Filament je Material und Farbe"], ["kennzahlen", "Kennzahlen oben (Teile, Filament, Druckzeit)"],
  ["bilder", "Vorschaubilder"], ["kaestchen", "Abhakkästchen zum Ausdrucken"], ["pfade", "Dateipfade unter den Namen"]];
const pdfSchalter = (k, t, wert) => `<label><input type="checkbox" data-pdf="${k}" ${wert[k] ? "checked" : ""}> ${t}</label>`;

// Zwei Plätze, keine Liste: ein Slicer und ein CAD. Der Pfad kommt aus dem Dateidialog des
// Rechners, nie aus einem Textfeld. `geaendert` merkt, was erst mit „Speichern“ gilt
// (Pfad, oder "" für „wieder automatisch“).
const progWahl = { slicer: null, cad: null, geaendert: {} };
const PROG_ARTEN = [["slicer", "Slicer", "zum Aufbereiten und Drucken, z. B. PrusaSlicer, Bambu Studio, OrcaSlicer"],
                    ["cad", "CAD", "zum Konstruieren und Ändern, z. B. FreeCAD"]];

function progTeil() {
  return PROG_ARTEN.map(([art, name, hilfe]) => {
    const p = progWahl[art];
    return `<div class="prog-feld">
      <div class="prog-art"><b>${name}</b><small>${hilfe}</small></div>
      <div class="prog-wahl">${p ? `<div><b>${esc(p.name)}</b>${p.automatisch ? '<span class="prog-gefunden">gefunden</span>' : ""}</div><code title="${esc(p.pfad)}">${esc(p.pfad)}</code>`
                                : progWahl.geaendert[art] === "" ? '<span class="dim">Automatisch — wird beim Speichern gewählt.</span>'
                                : '<span class="dim">Nichts gefunden — bitte ein Programm auswählen.</span>'}</div>
      <div class="prog-aktion"><button type="button" class="knopf" data-prog-aendern="${art}">${p ? "Ändern …" : "Auswählen …"}</button>
        ${p && !p.automatisch ? `<button type="button" class="knopf-text" data-prog-auto="${art}">Automatisch</button>` : ""}</div>
    </div>`;
  }).join("");
}

document.addEventListener("click", async (e) => {
  const aendern = e.target.closest?.("[data-prog-aendern]"), auto = e.target.closest?.("[data-prog-auto]");
  if (!aendern && !auto) return;
  if (auto) {
    const art = auto.dataset.progAuto;
    progWahl.geaendert[art] = "";
    // Wie es automatisch wäre, weiss der Server; die Anzeige zeigt es nach dem Speichern.
    progWahl[art] = null;
    $("#prog-teil").innerHTML = progTeil();
    return;
  }
  const art = aendern.dataset.progAendern;
  aendern.disabled = true;
  aendern.textContent = "Dialog geöffnet …";
  try {
    const p = await api("/api/programme/waehlen", { method: "POST", body: { art } });
    if (!p.abgebrochen) { progWahl[art] = p; progWahl.geaendert[art] = p.pfad; }
  } catch (err) { toast(err.message); }
  $("#prog-teil").innerHTML = progTeil();
});
document.addEventListener("click", (e) => {
  if (e.target.closest?.("#einstellungen")) return einstellungen();
  const wahl = e.target.closest?.("[data-ein]");
  if (!wahl) return;
  document.querySelectorAll("[data-ein]").forEach((b) => b.classList.toggle("aktiv", b === wahl));
  document.querySelectorAll("[data-ein-teil]").forEach((s) => { s.hidden = s.dataset.einTeil !== wahl.dataset.ein; });
  $("#ein-titel").textContent = wahl.textContent;
  localStorageSchreiben("einstellungen-abschnitt", wahl.dataset.ein);
});
