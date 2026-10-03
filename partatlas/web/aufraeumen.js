// Aufräumen: Vorschläge, was Platz kostet und vermutlich weg kann — je Datei mit Grund, Grösse und dem, was daran hängt.
//
// Wie eine feingranulare Firewall (Wunsch eines Testers, 03.10.2026): jede Entscheidung einzeln und nachvollziehbar, nichts geschieht
// von selbst. partAtlas löscht hier nichts (KONZEPT §3.3). Man zeigt die Datei im Dateimanager und löscht sie dort, speichert die
// gewählten Pfade als Liste — oder sagt „Behalten“: dann schlägt partAtlas sie nicht mehr vor (eine Ausnahme, zurücknehmbar).

const aufr = { daten: null, wahl: new Set(), zu: new Set() };
const mb = (b) => (b >= 1073741824 ? `${zahl(b / 1073741824, 2)} GB` : b >= 1048576 ? `${zahl(b / 1048576, 1)} MB` : `${zahl(b / 1024, 0)} kB`);
const afSchluessel = (art, id) => `${art}:${id}`;

function zeigeAufraeumen(an) {
  if (an) for (const s of ["#tagleiste", "#raster", "#listenkopf", "#stapel", "#pk-leiste", "#filterzeile", "#leer", "#pfad"]) $(s).hidden = true;
  else for (const s of ["#tagleiste", "#raster"]) $(s).hidden = false;
  $("#aufraeumen").hidden = !an;
}

async function ladeAufraeumen() {
  try { aufr.daten = await api("/api/aufraeumen"); } catch (e) { return toast(e.message); }
  // Was nicht mehr vorgeschlagen wird, ist auch nicht mehr gewählt.
  const da = new Set(aufr.daten.gruppen.flatMap((g) => g.eintraege.map((e) => afSchluessel(g.art, e.id))));
  for (const k of [...aufr.wahl]) if (!da.has(k)) aufr.wahl.delete(k);
  zeichneAufraeumen();
}

function afEintrag(art, e) {
  const k = afSchluessel(art, e.id);
  const haengt = e.haengt.map((h) => `<span class="chip af-haengt">${esc(h)}</span>`).join("");
  const pfade = e.pfade.map((p) => `<button class="af-pfad" data-af-zeigen="${esc(e.id)}" data-pfad="${esc(p)}" title="Im Ordner zeigen">📂 ${esc(p)}</button>`).join("");
  return `<div class="af-zeile ${e.vorsicht ? "vorsicht" : ""}" data-id="${esc(k)}">
    <input type="checkbox" data-af-wahl="${esc(k)}" ${aufr.wahl.has(k) ? "checked" : ""}>
    <div class="af-was">
      <button class="af-name" data-af-modell="${esc(e.id)}">${esc(e.name)}<span class="endung">${esc(endung[e.format] || "")}</span></button>
      <div class="af-grund">${esc(e.grund)}${e.vorsicht ? " · <b>hängt noch etwas daran</b>" : ""}</div>
      ${haengt ? `<div class="af-chips">${haengt}</div>` : ""}
      <div class="af-pfade">${pfade}</div>
    </div>
    <div class="af-groesse">${mb(e.bytes)}</div>
    <div class="af-aktion">
      <button class="knopf klein" data-af-behalten="${esc(e.id)}" title="Nicht mehr vorschlagen — in den Ausnahmen zurücknehmbar">Behalten</button>
      ${e.entwurf ? `<button class="knopf klein" data-af-kein-entwurf="${esc(e.id)}" title="Doch kein Entwurf">Kein Entwurf</button>` : ""}
    </div>
  </div>`;
}

function zeichneAufraeumen() {
  const d = aufr.daten;
  if (!d) return;
  // Ein Modell kann in zwei Gruppen stehen (Kopien und gross): für die Summe zählt jedes Modell einmal, mit dem grösseren Betrag.
  const jeModell = new Map();
  for (const g of d.gruppen) for (const e of g.eintraege) jeModell.set(e.id, Math.max(jeModell.get(e.id) || 0, e.bytes));
  const gesamt = [...jeModell.values()].reduce((s, b) => s + b, 0);
  const n = jeModell.size;
  const gruppen = d.gruppen.map((g) => {
    const zu = aufr.zu.has(g.art);
    const alle = g.eintraege.length && g.eintraege.every((e) => aufr.wahl.has(afSchluessel(g.art, e.id)));
    return `<section class="af-gruppe" data-id="g-${g.art}">
      <div class="af-gkopf">
        <input type="checkbox" data-af-alle="${g.art}" ${alle ? "checked" : ""} ${g.n ? "" : "disabled"} title="Alle dieser Gruppe wählen">
        <button class="af-gtitel" data-af-zu="${g.art}">${zu ? "▸" : "▾"} ${esc(g.titel)}</button>
        <span class="af-gzahl">${g.n ? `${anzahl(g.n)} · ${mb(g.bytes)}` : "nichts"}</span>
      </div>
      <p class="dim af-erkl">${esc(g.erklaerung)}</p>
      ${zu ? "" : g.eintraege.map((e) => afEintrag(g.art, e)).join("") || `<p class="dim af-leer">Nichts zu tun.</p>`}
    </section>`;
  }).join("");
  const gewaehlt = afGewaehlt();
  abgleichen($("#aufraeumen"), `<div class="af-kopf">
      <h2>Aufräumen</h2>
      <p>${n ? `Vorschläge: <b>${mb(gesamt)}</b> in ${anzahl(n)} ${n === 1 ? "Modell" : "Modellen"}.` : "Nichts vorzuschlagen."}
        partAtlas löscht hier nichts: du entscheidest je Datei und löschst sie selbst im Dateimanager (📂). „Behalten“ heisst: nicht mehr
        vorschlagen.</p>
      <p class="dim">Danach <button class="link" data-af-neu-einlesen>neu einlesen</button>: gelöschte Entwürfe gehen dann in den Papierkorb,
        gelöschte Kopien verschwinden aus der Liste.${d.behalten ? ` · <button class="link" data-af-ausnahmen>${anzahl(d.behalten)} ${d.behalten === 1 ? "Ausnahme" : "Ausnahmen"} (Behalten)</button>` : ""}</p>
    </div>
    ${gruppen}
    <div class="af-leiste" ${gewaehlt.length ? "" : "hidden"}>
      <b>${anzahl(gewaehlt.length)} gewählt · ${mb(gewaehlt.reduce((s, x) => s + x.e.bytes, 0))}</b>
      <button class="knopf" data-af-csv title="Die Pfade als Liste speichern — zum Abarbeiten im Dateimanager">Pfade speichern (CSV)</button>
      <button class="knopf" data-af-alle-behalten>Behalten</button>
      <button class="knopf" data-af-keine>✕</button>
    </div>`);
}

function afGewaehlt() {
  const aus = [];
  for (const g of aufr.daten?.gruppen || []) for (const e of g.eintraege) if (aufr.wahl.has(afSchluessel(g.art, e.id))) aus.push({ g, e });
  return aus;
}

function afCsv() {
  const zeilen = [["Gruppe", "Modell", "Bytes", "Pfad", "Grund", "Hängt daran"]];
  for (const { g, e } of afGewaehlt()) for (const p of e.pfade) zeilen.push([g.titel, e.name, e.bytes, p, e.grund, e.haengt.join(", ")]);
  const text = zeilen.map((z) => z.map((x) => `"${String(x ?? "").replace(/"/g, '""')}"`).join(";")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["﻿" + text], { type: "text/csv;charset=utf-8" }));
  a.download = `partatlas-aufraeumen-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

async function afAusnahmen() {
  const liste = await api("/api/aufraeumen/behalten");
  const a = await dialog(`<h2>Ausnahmen</h2><p class="dim">Diese Modelle schlägt partAtlas beim Aufräumen nicht vor. Häkchen weg = wieder vorschlagen.</p>
    <div class="dl-liste">${liste.map((m) => `<label class="dl-zeile"><input type="checkbox" data-ausnahme="${esc(m.id)}" checked>
      <span class="dl-pfad">${esc(m.name)}${esc(endung[m.format] || "")}</span><span></span></label>`).join("")}</div>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Übernehmen</button></div>`);
  if (a !== "ja") return;
  for (const k of document.querySelectorAll("[data-ausnahme]:not(:checked)")) {
    await api(`/api/modelle/${k.dataset.ausnahme}/behalten`, { method: "POST", body: { an: false } }).catch((e) => toast(e.message));
  }
  ladeAufraeumen();
}

document.addEventListener("change", (e) => {
  if (!e.target.closest?.("#aufraeumen")) return;
  const w = e.target.dataset.afWahl, alle = e.target.dataset.afAlle;
  if (w) e.target.checked ? aufr.wahl.add(w) : aufr.wahl.delete(w);
  if (alle) {
    const g = aufr.daten.gruppen.find((x) => x.art === alle);
    for (const x of g.eintraege) e.target.checked ? aufr.wahl.add(afSchluessel(alle, x.id)) : aufr.wahl.delete(afSchluessel(alle, x.id));
  }
  zeichneAufraeumen();
});

document.addEventListener("click", async (e) => {
  const t = e.target.closest?.("#aufraeumen button");
  if (!t) return;
  const d = t.dataset;
  try {
    if (d.afZu) { aufr.zu.has(d.afZu) ? aufr.zu.delete(d.afZu) : aufr.zu.add(d.afZu); return zeichneAufraeumen(); }
    if (d.afModell) return waehle(d.afModell);
    if (d.afZeigen) return await api(`/api/modelle/${d.afZeigen}/im_ordner`, { method: "POST", body: { pfad: d.pfad } });
    if (d.afBehalten) { await api(`/api/modelle/${d.afBehalten}/behalten`, { method: "POST", body: { an: true } }); return ladeAufraeumen(); }
    if (d.afKeinEntwurf != null) { await api(`/api/modelle/${d.afKeinEntwurf}`, { method: "PATCH", body: { entwurf: false } }); return ladeAufraeumen(); }
    if ("afCsv" in d) return afCsv();
    if ("afKeine" in d) { aufr.wahl.clear(); return zeichneAufraeumen(); }
    if ("afAlleBehalten" in d) {
      const ids = [...new Set(afGewaehlt().map((x) => x.e.id))];
      for (const id of ids) await api(`/api/modelle/${id}/behalten`, { method: "POST", body: { an: true } });
      aufr.wahl.clear();
      toast(`${ids.length} als Ausnahme behalten.`);
      return ladeAufraeumen();
    }
    if ("afAusnahmen" in d) return afAusnahmen();
    if ("afNeuEinlesen" in d) { const r = await api("/api/scan", { method: "POST" }); return einlesenZeigen(r.lauf, "Neu einlesen"); }
  } catch (err) { toast(err.message); }
});
