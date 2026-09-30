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
  const tipp = vorschlaege.length
    ? `<div class="tipp" id="bg-tipp"><b>💡 ${vorschlaege.length} Ordner</b> sehen aus wie Baugruppen — ansehen</div>` : "";
  $("#baugruppen").innerHTML = liste.map((b) => `
    <button class="bg-eintrag ${zustand.baugruppe === b.id ? "aktiv" : ""}" data-baugruppe="${esc(b.id)}">
      <div class="kopfzeile"><span>${esc(b.name)}</span><em title="Druckteile gedruckt">${b.druck_erledigt}/${b.druck_bedarf}</em></div>${balken(b)}</button>`).join("") + tipp;
  zustand.bgVorschlaege = vorschlaege;
}

// ---------------------------------------------------------------- Ansicht

function zeigeBaugruppeFlaeche(an) {
  for (const s of ["#tagleiste", "#raster"]) $(s).hidden = an;
  if (an) for (const s of ["#filterzeile", "#stapel", "#listenkopf", "#leer"]) $(s).hidden = true;
  $("#bg-ansicht").hidden = !an;
}

async function oeffneBaugruppe(bid) {
  zustand.baugruppe = bid;
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
  // Eingabe in einer Notiz nicht unter den Fingern wegzeichnen.
  if (document.activeElement?.classList.contains("notiz")) return;
  $("#bg-ansicht").innerHTML = zeichneBaugruppe(d);
}

function zeichneBaugruppe(d) {
  const f = d.fortschritt, s = d.summen;
  const druck = d.positionen.filter((p) => p.art === "modell");
  const unter = d.positionen.filter((p) => p.art === "baugruppe");
  const kauf = d.positionen.filter((p) => p.art === "kaufteil");
  const titelbild = druck.map((p) => bildUrl(p)).find(Boolean);
  const offenTeile = f.bedarf - f.erledigt;
  const offenDruck = f.druck_bedarf - f.druck_erledigt;
  const leer = !d.positionen.length;
  // Zwei Zeilen statt einer Summe: „3 von 45“ vermischte Druck- und Kaufteile.
  const fortschrittZeilen = [
    f.druck_bedarf ? `<div class="fz"><span class="fz-name">Druckteile</span>${balken({ bedarf: f.druck_bedarf, erledigt: f.druck_erledigt })}
      <span class="fz-text"><b>${f.druck_erledigt} von ${f.druck_bedarf}</b> gedruckt${offenDruck ? ` · noch ca. ${zahl(s.offen_gewicht_g, 0)} g${s.offen_zeit_s ? ", " + dauer(s.offen_zeit_s) : ""}` : " ✓"}</span></div>` : "",
    f.kauf_bedarf ? `<div class="fz"><span class="fz-name">Kaufteile</span>${balken({ bedarf: f.kauf_bedarf, erledigt: f.kauf_erledigt })}
      <span class="fz-text"><b>${f.kauf_erledigt} von ${f.kauf_bedarf}</b> beschafft${f.kauf_erledigt >= f.kauf_bedarf ? " ✓" : ""}</span></div>` : "",
  ].join("");
  return `
  <div class="bg-kopf">
    <div class="bg-bild">${titelbild ? `<img src="${titelbild}" alt="">` : '<span style="font-size:40px">🧩</span>'}</div>
    <div style="flex:1;min-width:0">
      <h2 class="bg-titel" id="bg-name" title="Klicken zum Umbenennen">${esc(d.name)}</h2>
      <div class="bg-beschreibung" id="bg-beschreibung" title="Klicken zum Bearbeiten">${d.beschreibung ? esc(d.beschreibung) : '<span class="dim">Beschreibung hinzufügen …</span>'}</div>
      ${leer ? "" : `<div class="bg-fortschritt">${fortschrittZeilen}</div>`}
      ${!leer && offenTeile === 0 ? '<div class="feier">🎉 Alle Teile fertig — Zeit zum Zusammenbauen!</div>' : ""}
      ${d.verwendet_in.length ? `<div class="dim" style="margin-top:6px">Steckt in: ${d.verwendet_in.map((b) =>
        `<a href="#" data-baugruppe="${esc(b.id)}">${esc(b.name)}</a> (${b.menge}×)`).join(", ")}${d.exemplare > 1
        ? ` — insgesamt <b>${d.exemplare} Sätze</b>, die Zähler unten gelten für alle zusammen.` : ""}</div>` : ""}
    </div>
  </div>
  ${leer ? `
  <div class="bg-leer">
    <h3>Eine Baugruppe ist eine Stückliste</h3>
    <ol>
      <li><b>Druckteile hinzufügen</b> — hier wählen, oder im Katalog Kacheln auf „${esc(d.name)}“ links ziehen.</li>
      <li><b>Mengen einstellen</b> — 4 Arme, 8 Halter. Heisst eine Datei <code>Arm_x4</code>, steht die 4 schon da.</li>
      <li><b>Kaufteile dazu</b> — Schrauben, Muttern, Magnete, Lager aus dem Katalog.</li>
    </ol>
    <p class="dim">Dann zeigt partAtlas, was noch fehlt, wie viel Filament welcher Farbe du brauchst und was du kaufen musst.</p>
    <div class="i-knoepfe"><button class="knopf akzent" data-bg-aktion="teile">＋ Druckteile wählen</button>
      <button class="knopf" data-bg-aktion="kaufteile">＋ Kaufteile</button><button class="knopf" data-bg-aktion="unter">＋ Unterbaugruppe</button></div>
  </div>` : `
  <div class="kennzahlen">
    <div class="kennzahl"><small>DRUCKTEILE</small><b>${f.druck_erledigt} / ${f.druck_bedarf}</b><span>gedruckt · ${druck.length} verschiedene</span></div>
    <div class="kennzahl"><small>KAUFTEILE</small><b>${f.kauf_erledigt} / ${f.kauf_bedarf}</b><span>beschafft · ${s.einkauf.length} Positionen</span></div>
    <button class="kennzahl klappbar ${aufgeklappt("filament") ? "offen" : ""}" data-klapp="filament" title="Aufschlüsselung ${aufgeklappt("filament") ? "zuklappen" : "zeigen"}">
      <div class="kz-links"><small>FILAMENT ▾</small><b>${zahl(s.gewicht_g, 0)} g</b><span>${s.gewicht_geschaetzt ? "teils geschätzt" : "aus dem Slicer"}</span></div>
      <div class="kz-mini">${s.materialien.slice(0, 4).map((m) => `<div>${m.farben.slice(0, 3).map((x) => tupfer(x.farbe)).join("")}<span>${esc(m.material)}</span><em>${zahl(m.gesamt_g, 0)} g</em></div>`).join("")}</div>
    </button>
    <button class="kennzahl klappbar ${aufgeklappt("zeit") ? "offen" : ""}" data-klapp="zeit" title="Druckzeit je Teil ${aufgeklappt("zeit") ? "zuklappen" : "zeigen"}">
      <div class="kz-links"><small>DRUCKZEIT ▾</small><b>${dauer(s.zeit_s)}</b><span>${!s.zeit_s ? "keine Slicer-Daten" : s.ohne_zeit ? `${s.ohne_zeit} Teile ohne Zeit` : "aus dem Slicer"}</span></div>
      <div class="kz-mini">${s.zeiten.filter((z) => z.je_s).slice(0, 3).map((z) => `<div>${tupfer(z.farbe)}<span>${esc(z.name)}</span><em>${dauer(z.gesamt_s)}</em></div>`).join("")}</div>
    </button>
  </div>
  ${aufgeklappt("filament") ? filamentKarte(s) : ""}
  ${aufgeklappt("zeit") ? zeitKarte(s) : ""}
  <div class="bg-aktionen">
    <button class="knopf akzent" data-bg-aktion="warteschlange" ${offenTeile ? "" : "disabled"}>☰ Fehlende in die Warteschlange</button>
    <button class="knopf" data-bg-aktion="teile">＋ Druckteile</button>
    <button class="knopf" data-bg-aktion="kaufteile">＋ Kaufteile</button>
    <button class="knopf" data-bg-aktion="unter">＋ Unterbaugruppe</button>
    <button class="knopf" data-bg-aktion="csv">Stückliste als CSV</button>
    <button class="knopf" data-bg-aktion="md">… als Markdown</button>
    <button class="knopf gefahr" data-bg-aktion="loeschen">Baugruppe löschen</button>
  </div>
  ${abschnitt("DRUCKTEILE", druck, "teile", "Noch keine Druckteile.")}
  ${unter.length ? abschnitt("UNTERBAUGRUPPEN", unter, "unter", "") : ""}
  ${abschnitt("KAUFTEILE", kauf, "kaufteile", "Noch keine Kaufteile — Schrauben, Magnete, Lager …")}
  ${einkaufsliste(s)}`}`;
}

function abschnitt(titel, liste, aktion, leer) {
  return `<div class="bg-abschnitt"><h3>${titel}</h3><button data-bg-aktion="${aktion}">＋ hinzufügen</button></div>
    ${liste.length ? liste.map(position).join("") : `<div class="pos-leer">${leer}</div>`}`;
}

function position(p) {
  const r = esc(p.ref);
  const fertig = p.art !== "baugruppe" && p.erledigt >= p.bedarf;
  let vorschau, name, unterzeile, zaehlerText;
  if (p.art === "modell") {
    const url = bildUrl(p);
    vorschau = url ? `<img loading="lazy" src="${url}" alt="">` : "🧊";
    name = `<div class="name" data-bg-modell="${esc(p.id)}" title="Im Inspektor zeigen">${esc(p.name)}${esc(endung[p.format] || "")}</div>`;
    unterzeile = [p.fehlt ? "⚠ Datei fehlt" : "", p.je_gewicht_g ? `je ${zahl(p.je_gewicht_g, 1)} g${p.je_geschaetzt ? " (geschätzt)" : ""}` : "", masse(p.masse)].filter(Boolean).join(" · ");
    zaehlerText = "gedruckt";
  } else if (p.art === "kaufteil") {
    vorschau = symbolFuer(p.kategorie);
    name = `<div class="name">${esc(p.name)}</div>`;
    unterzeile = `${esc(p.kategorie || "")}${p.einheit && p.einheit !== "Stück" ? " · in " + esc(p.einheit) : ""}`;
    zaehlerText = "beschafft";
  } else {
    vorschau = "🧩";
    name = `<div class="name" data-baugruppe="${esc(p.id)}" title="Öffnen">${esc(p.name)} ›</div>`;
    unterzeile = `${p.unter_positionen} Positionen · ${p.unter_erledigt} von ${p.unter_bedarf} Teilen fertig`;
    zaehlerText = "";
  }
  const zaehler = p.art === "baugruppe"
    ? `<div class="zaehler">${balken({ bedarf: p.unter_bedarf, erledigt: p.unter_erledigt })}<span class="dim">wird in der Unterbaugruppe gezählt</span></div>`
    : `<div class="zaehler"><div class="zeile2"><span class="stepper"><button data-bg-zaehlen="-1" data-ref="${r}" title="eins weniger">−</button><span>${p.erledigt}/${p.bedarf}</span><button data-bg-zaehlen="1" data-ref="${r}" title="eins mehr ${zaehlerText}">＋</button></span>
       ${fertig ? '<span style="color:var(--good)">✓</span>' : `<button class="voll" data-bg-voll="${r}" title="alle ${zaehlerText}">alle</button>`}</div>
       <span class="dim">${zaehlerText}</span></div>`;
  const material = p.art === "modell"
    ? `<div class="material"><button class="mat-knopf ${p.material_angenommen ? "standard" : ""}" data-bg-material="${r}"
        title="${p.material_angenommen ? "Keine Angabe — Standard aus den Einstellungen. Klicken zum Festlegen." : "Material und Farbe festlegen"}">
        ${tupfer(p.farbe)}${esc(p.material)}${p.material_angenommen ? " <small>Standard</small>" : ""}</button></div>` : `<div class="material"></div>`;
  return `<div class="pos ${fertig && p.art !== "baugruppe" ? "erledigt" : ""}">
    <div class="vorschau">${vorschau}</div>
    <div style="min-width:0">${name}<div class="unter">${unterzeile}</div>
      <input class="notiz" data-bg-notiz="${r}" value="${esc(p.notiz || "")}" placeholder="Notiz …"></div>
    <div><span class="stepper"><button data-bg-menge="-1" data-ref="${r}">−</button><span>${p.menge}×</span><button data-bg-menge="1" data-ref="${r}">＋</button></span></div>
    ${zaehler}
    ${material}
    <button class="weg" data-bg-weg="${r}" title="aus der Baugruppe nehmen">×</button></div>`;
}

function filamentKarte(s) {
  if (!s.materialien.length) return "";
  const gesamt = s.materialien.reduce((a, m) => a + m.gesamt_g, 0) || 1;
  const segmente = s.materialien.flatMap((m) => m.farben.map((f) =>
    `<i style="width:${(100 * f.gesamt_g) / gesamt}%;${f.farbe ? `background:${esc(f.farbe)}` : ""}" class="${f.farbe ? "" : "offen"}"
        title="${esc(m.material || "Material offen")} ${esc(farbName(f.farbe))}: ${zahl(f.gesamt_g, 0)} g"></i>`)).join("");
  const zeilen = s.materialien.map((m) => {
    const rolle = Math.min(1, m.gesamt_g / s.rolle_g);
    return `<div class="mat-zeile">
      <div class="mat-name">${esc(m.material)}${m.angenommen_g ? `<small title="Teile ohne Angabe — Standard aus den Einstellungen">davon ${zahl(m.angenommen_g, 0)} g Standard</small>` : ""}</div>
      <div class="mat-farben">${m.farben.map((f) => `<span class="mat-farbe">${tupfer(f.farbe)}<small>${f.farbe && !farbName(f.farbe).startsWith("#") ? esc(farbName(f.farbe)) + " " : !f.farbe ? "Farbe offen " : ""}${zahl(f.gesamt_g, 0)} g</small></span>`).join("")}</div>
      <div class="mat-menge"><b>${zahl(m.gesamt_g, 0)} g</b>${m.offen_g < m.gesamt_g ? `<small>noch ${zahl(m.offen_g, 0)} g</small>` : ""}</div>
      <div class="mat-rolle"><span class="spule" title="Anteil einer Rolle zu ${s.rolle_g} g"><i style="width:${Math.round(rolle * 100)}%"></i></span><small>${rollenText(m.rollen)}</small></div>
    </div>`;
  }).join("");
  return `<div class="i-karte filament-karte">
    <div class="i-titel" style="margin-top:8px">FILAMENT NACH MATERIAL${s.gewicht_geschaetzt ? ' <span class="dim" title="Ohne Slicer-Daten: 1,2 mm Hülle und 15 % Füllung">· teils geschätzt ⓘ</span>' : ""}</div>
    <div class="mischung">${segmente}</div>
    ${zeilen}
  </div>`;
}

// Druckzeit je Teil als Balken: sieht man, was die Zeit frisst. Teile ohne
// Slicer-Zeit stehen darunter — geschätzt wird hier nichts.
function zeitKarte(s) {
  const mit = s.zeiten.filter((z) => z.je_s), ohne = s.zeiten.filter((z) => !z.je_s);
  const max = Math.max(1, ...mit.map((z) => z.gesamt_s));
  return `<div class="i-karte filament-karte">
    <div class="i-titel" style="margin-top:8px">DRUCKZEIT JE TEIL — ${dauer(s.zeit_s)} GESAMT${s.offen_zeit_s < s.zeit_s ? `, NOCH ${dauer(s.offen_zeit_s).toUpperCase()}` : ""}</div>
    ${mit.map((z) => `<div class="zeit-zeile ${z.offen ? "" : "fertig"}">
      <span class="zeit-name">${tupfer(z.farbe)}${esc(z.name)}${z.stueck > 1 ? ` <small>${z.stueck}× à ${dauer(z.je_s)}</small>` : ""}</span>
      <span class="zeit-balken"><i style="width:${(100 * z.gesamt_s) / max}%"></i><i class="rest" style="width:${(100 * z.offen_s) / max}%"></i></span>
      <span class="zeit-wert">${dauer(z.gesamt_s)}</span></div>`).join("") || '<div class="dim" style="padding:6px 0">Keine Slicer-Zeiten.</div>'}
    ${ohne.length ? `<div class="dim" style="padding:8px 0 2px">Ohne Slicer-Zeit (${ohne.length}): ${ohne.slice(0, 12).map((z) => esc(z.name)).join(", ")}${ohne.length > 12 ? " …" : ""} — Zeit kommt mit dem G-Code (Phase 2).</div>` : ""}
  </div>`;
}

function aufgeklappt(k) { return localStorageLesen(`klapp.${k}`) === "1"; }

function einkaufsliste(s) {
  if (!s.einkauf.length) return "";
  return `<div class="bg-abschnitt"><h3>EINKAUFSLISTE KAUFTEILE — ÜBER ALLE EBENEN</h3></div>
  <div class="einkauf">
    <div class="i-karte"><div class="i-titel" style="margin-top:8px">KAUFTEILE</div>
      ${s.einkauf.map((x) => `<div class="zeile"><span>${esc(x.name)}</span><span>${x.offen ? `fehlen <b>${x.offen}</b> von ${x.bedarf}` : "✓ alle " + x.bedarf} ${esc(x.einheit === "Stück" ? "" : x.einheit)}</span></div>`).join("") || '<div class="zeile"><span class="dim">–</span></div>'}</div>
  </div>`;
}

// ---------------------------------------------------------------- Ändern

const bid = () => zustand.baugruppe;

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
    <input type="text" id="w-suche" placeholder="${kaufteile ? "Suchen, z. B. m3x10, Magnet 6x2, 608 …" : "Modell suchen …"}" autocomplete="off">
    ${kaufteile ? `<div class="kategorien">${kategorien.map((k) => `<button type="button" class="chip" data-w-kat="${esc(k)}">${esc(k)}</button>`).join("")}</div>` : ""}
    <div class="waehler" id="w-liste"></div>
    ${kaufteile ? `<p class="dim" style="margin-top:8px">Nicht dabei? <input type="text" id="w-eigen" placeholder="Eigenes Kaufteil, z. B. Propeller 5 Zoll" style="width:60%"> <button type="button" class="knopf" id="w-eigen-knopf">Anlegen</button></p>` : ""}
    <div class="knoepfe"><button class="knopf akzent" value="fertig">Fertig</button></div>`);
  let kategorie = "";
  const laden = async () => {
    const q = $("#w-suche").value.trim();
    let zeilen = [];
    if (kaufteile) {
      const liste = await api(`/api/kaufteile?q=${encodeURIComponent(q)}&kategorie=${encodeURIComponent(kategorie)}`);
      zeilen = liste.slice(0, 120).map((t) => ({ ref: `PURCHASED_PART/${t.id}`, name: t.name, klein: [t.kategorie, t.norm].filter(Boolean).join(" · "), bild: null, symbol: symbolFuer(t.kategorie) }));
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
      <input type="number" min="1" value="1" data-w-menge="${esc(z.ref)}">
      <button type="button" class="plus ${drin.has(z.ref) ? "ok" : ""}" data-w-plus="${esc(z.ref)}" title="${drin.has(z.ref) ? "schon drin — nochmal erhöht die Menge" : "hinzufügen"}">${drin.has(z.ref) ? "✓" : "＋"}</button></div>`).join("")
      || '<div class="pos-leer">Nichts gefunden.</div>';
  };
  let zeit;
  $("#w-suche").addEventListener("input", () => { clearTimeout(zeit); zeit = setTimeout(laden, 150); });
  $("#w-liste").addEventListener("click", async (e) => {
    const plus = e.target.closest("[data-w-plus]");
    if (!plus) return;
    const ref = plus.dataset.wPlus;
    const menge = Number(document.querySelector(`[data-w-menge="${CSS.escape(ref)}"]`)?.value || 1);
    try {
      await api(`/api/baugruppen/${bid()}/positionen`, { method: "POST", body: { ref, menge } });
      plus.classList.add("ok"); plus.textContent = "✓";
      await ladeBaugruppe();
    } catch (err) { toast(err.message); }
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

    case "warteschlange": {
      const { eingereiht } = await api(`/api/baugruppen/${bid()}/warteschlange`, { method: "POST" });
      return toast(`${eingereiht} fehlende Druckteile in der Warteschlange.`);
    }
    case "csv": case "md": return (window.location.href = `/api/baugruppen/${bid()}/export?format=${aktion}`);
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
  if (t.closest("#bg-tipp") || t.id === "baugruppe-neu") return neueBaugruppe();
  const vor = t.closest("[data-vorschlag]");
  if (vor) return ausVorschlag(vor.dataset.vorschlag);
  const b = t.closest("[data-baugruppe]");
  if (b) { e.preventDefault(); return oeffneBaugruppe(b.dataset.baugruppe); }
  if (!t.closest("#bg-ansicht")) return;
  const klapp = t.closest("[data-klapp]");
  if (klapp) {
    localStorageSchreiben(`klapp.${klapp.dataset.klapp}`, aufgeklappt(klapp.dataset.klapp) ? "0" : "1");
    $("#bg-ansicht").innerHTML = zeichneBaugruppe(bgDaten);
    return;
  }
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
  if (mod) return waehle(mod.dataset.bgModell);
  if (t.closest("#bg-name")) {
    const a = await dialog(`<h2>Baugruppe umbenennen</h2><input type="text" id="s-name" value="${esc(bgDaten.name)}">
      <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Umbenennen</button></div>`);
    if (a === "ja") await api(`/api/baugruppen/${bid()}`, { method: "PATCH", body: { name: $("#s-name").value } }).catch((e2) => toast(e2.message));
    return;
  }
  if (t.closest("#bg-beschreibung")) {
    const a = await dialog(`<h2>Beschreibung</h2><textarea id="s-text" rows="5" style="width:100%">${esc(bgDaten.beschreibung || "")}</textarea>
      <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Speichern</button></div>`);
    if (a === "ja") await api(`/api/baugruppen/${bid()}`, { method: "PATCH", body: { beschreibung: $("#s-text").value } });
  }
});

document.addEventListener("change", (e) => {
  const n = e.target.closest?.("[data-bg-notiz]");
  if (n) positionAendern(n.dataset.bgNotiz, { notiz: n.value });
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.target.closest?.("[data-bg-notiz]")) e.target.blur();
});

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
  Object.assign(mwWahl, { material: e.gilt.material, farbe: e.gilt.farbe });
  const a = await dialog(`<h2>Einstellungen</h2>
    <p class="dim">Was partAtlas annimmt, wenn ein Druckteil keine Angabe hat (kein Slicer-Wert, nichts festgelegt).</p>
    <div class="i-titel">STANDARDMATERIAL</div>
    <div class="kategorien">${e.materialien.map((m) => `<button type="button" class="chip ${m === e.gilt.material ? "aktiv" : ""}" data-mw-mat="${esc(m)}">${esc(m)}</button>`).join("")}</div>
    <div class="i-titel">STANDARDFARBE</div>
    <div class="farbfelder">${FARBEN.map(([n, h]) => `<button type="button" class="farbfeld ${h === e.gilt.farbe ? "aktiv" : ""}" data-mw-farbe="${h}" title="${n}" style="background:${h}"></button>`).join("")}
      <button type="button" class="knopf ${e.gilt.farbe ? "" : "aktiv"}" data-mw-farbe="">keine</button></div>
    <div class="i-titel">ROLLENGRÖSSE</div>
    <label>Gramm je Rolle <input type="number" id="ein-rolle" min="100" max="10000" step="50" value="${e.gilt.rolle_g}" style="width:90px"></label>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Speichern</button></div>`);
  if (a !== "ja") return;
  try {
    await api("/api/einstellungen", { method: "PUT", body: { standard_material: mwWahl.material, standard_farbe: mwWahl.farbe,
                                                          rolle_g: Number($("#ein-rolle").value) } });
    toast("Gespeichert.");
    ladeBaugruppe();
  } catch (err) { toast(err.message); }
}
document.addEventListener("click", (e) => { if (e.target.closest?.("#einstellungen")) einstellungen(); });
