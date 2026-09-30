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
      <div class="kopfzeile"><span>${esc(b.name)}</span><em>${b.erledigt}/${b.bedarf}</em></div>${balken(b)}</button>`).join("") + tipp;
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
  const text = !f.bedarf ? "Noch leer."
    : offenTeile === 0 ? `<b>Alles da.</b> ${f.bedarf} von ${f.bedarf} Teilen gedruckt und beschafft.`
    : `<b>${f.erledigt} von ${f.bedarf}</b> Teilen fertig · noch ca. <b>${zahl(s.offen_gewicht_g, 0)} g</b> Filament`
      + (s.offen_zeit_s ? ` · <b>${dauer(s.offen_zeit_s)}</b> Druckzeit` : "");
  const leer = !d.positionen.length;
  return `
  <div class="bg-kopf">
    <div class="bg-bild">${titelbild ? `<img src="${titelbild}" alt="">` : '<span style="font-size:40px">🧩</span>'}</div>
    <div style="flex:1;min-width:0">
      <h2 class="bg-titel" id="bg-name" title="Klicken zum Umbenennen">${esc(d.name)}</h2>
      <div class="bg-beschreibung" id="bg-beschreibung" title="Klicken zum Bearbeiten">${d.beschreibung ? esc(d.beschreibung) : '<span class="dim">Beschreibung hinzufügen …</span>'}</div>
      ${leer ? "" : `<div class="bg-fortschritt">${balken(f)}<div class="text">${text}</div></div>`}
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
    <div class="kennzahl"><small>DRUCKTEILE</small><b>${s.druckteile}</b><span>${druck.length} verschiedene</span></div>
    <div class="kennzahl"><small>KAUFTEILE</small><b>${s.kaufteile}</b><span>${s.einkauf.length} Positionen</span></div>
    <div class="kennzahl"><small>FILAMENT</small><b>${zahl(s.gewicht_g, 0)} g</b><span title="Ohne Slicer-Daten geschätzt: 1,2 mm Hülle und 15 % Füllung">${s.gewicht_geschaetzt ? "teils geschätzt ⓘ" : "aus dem Slicer"}${s.ohne_daten ? ` · ${s.ohne_daten} ohne Daten` : ""}</span></div>
    <div class="kennzahl"><small>DRUCKZEIT</small><b>${dauer(s.zeit_s)}</b><span>${!s.zeit_s ? "keine Slicer-Daten" : s.ohne_zeit ? `${s.ohne_zeit} Teile ohne Slicer-Zeit` : "aus dem Slicer"}</span></div>
  </div>
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
    ? `<div class="material dim">${p.farbe ? `<span class="farbpunkt" style="background:${esc(p.farbe)}"></span>` : ""}${esc(p.material || "")}</div>` : `<div class="material"></div>`;
  return `<div class="pos ${fertig && p.art !== "baugruppe" ? "erledigt" : ""}">
    <div class="vorschau">${vorschau}</div>
    <div style="min-width:0">${name}<div class="unter">${unterzeile}</div>
      <input class="notiz" data-bg-notiz="${r}" value="${esc(p.notiz || "")}" placeholder="Notiz …"></div>
    <div><span class="stepper"><button data-bg-menge="-1" data-ref="${r}">−</button><span>${p.menge}×</span><button data-bg-menge="1" data-ref="${r}">＋</button></span></div>
    ${zaehler}
    ${material}
    <button class="weg" data-bg-weg="${r}" title="aus der Baugruppe nehmen">×</button></div>`;
}

function einkaufsliste(s) {
  if (!s.filament.length && !s.einkauf.length) return "";
  return `<div class="bg-abschnitt"><h3>EINKAUFSLISTE — ÜBER ALLE EBENEN</h3></div>
  <div class="einkauf">
    <div class="i-karte"><div class="i-titel" style="margin-top:8px">FILAMENT</div>
      ${s.filament.map((x) => `<div class="zeile"><span>${x.farbe ? `<span class="farbpunkt" style="background:${esc(x.farbe)}"></span>` : ""}${esc(x.material)}${x.farbe ? "" : ' <span class="dim">(Farbe offen)</span>'}</span>
        <span>${x.offen_g ? `noch ${zahl(x.offen_g, 0)} g` : "✓"} · ${zahl(x.gesamt_g, 0)} g gesamt</span></div>`).join("") || '<div class="zeile"><span class="dim">–</span></div>'}</div>
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
