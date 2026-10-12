// Dateien, die auf der Platte verschwunden sind (Anwender, 12.10.2026): neue und verschobene Dateien übernimmt das Einlesen still; ganz
// am Ende kommt EIN Fenster, nur für das, was bei diesem Lauf fehlt. Es listet jedes Modell mit dem, was daran hängt — damit man weiss,
// was man gleich tut — und fragt je Zeile: ins Archiv (Vorgabe), behalten, löschen. „Für alle übernehmen“, wenn ein ganzer Ordner weg ist.
// „Später“ lässt alles, wie es ist; es steht dann unter Bereinigen › Datei fehlt und lässt sich dort wieder so entscheiden.

const FEHLT_WAHL = [["archiv", "Archiv", "Ruht mit allem, was daran hängt; kommt die Datei wieder, ist das Modell von selbst zurück"],
                    ["behalten", "Behalten", "Bleibt im Katalog, mit ruhigem Zeichen „ohne Datei“"],
                    ["loeschen", "Löschen", "In den Papierkorb von partAtlas — dort zurückholbar"]];
const fw = { liste: [], wahl: new Map(), neu: false };

function haengtText(h) {
  const t = [h.drucke && `${h.drucke} ${h.drucke === 1 ? "Druck" : "Drucke"}`, h.baugruppen && `${h.baugruppen} ${h.baugruppen === 1 ? "Baugruppe" : "Baugruppen"}`,
             h.sammlungen && `${h.sammlungen} ${h.sammlungen === 1 ? "Sammlung" : "Sammlungen"}`, h.anhaenge && `${h.anhaenge} ${h.anhaenge === 1 ? "Anhang" : "Anhänge"}`,
             h.bilder && `${h.bilder} ${h.bilder === 1 ? "eigenes Bild" : "eigene Bilder"}`, h.tags && `${h.tags} ${h.tags === 1 ? "Tag" : "Tags"}`].filter(Boolean);
  return t.length ? t.join(" · ") : "nichts weiter";
}

async function fehlendeFenster({ neu = false } = {}) {
  let liste;
  try { liste = await api(`/api/fehlende${neu ? "?neu=1" : ""}`); } catch (e) { return toast(e.message); }
  if (!liste.length) return;
  Object.assign(fw, { liste, neu, wahl: new Map(liste.map((x) => [x.id, "archiv"])) });
  let d = $("#fehlt-fenster");
  if (!d) {
    d = document.createElement("dialog");
    d.id = "fehlt-fenster";
    document.body.append(d);
  }
  fwZeichnen();
  if (!d.open) d.showModal();
}

function fwZeichnen() {
  const d = $("#fehlt-fenster"), n = fw.liste.length;
  const gruppen = new Map();
  for (const x of fw.liste) { if (!gruppen.has(x.ordner)) gruppen.set(x.ordner, []); gruppen.get(x.ordner).push(x); }
  const zaehle = (w) => [...fw.wahl.values()].filter((v) => v === w).length;
  const segment = (attr, aktiv) => `<span class="fw-seg">${FEHLT_WAHL.map(([k, t, hilfe]) =>
    `<button type="button" class="${aktiv === k ? "an" : ""} ${k === "loeschen" ? "gefahr" : ""}" ${attr}="${k}" title="${esc(hilfe)}">${t}</button>`).join("")}</span>`;
  const alleGleich = (ids) => { const w = new Set(ids.map((i) => fw.wahl.get(i))); return w.size === 1 ? [...w][0] : null; };
  const zusammen = [["archiv", "ins Archiv"], ["behalten", "behalten"], ["loeschen", "in den Papierkorb"]]
    .map(([k, t]) => zaehle(k) ? `${zaehle(k)} ${t}` : "").filter(Boolean).join(" · ");
  const titelEndung = (x) => esc(endung[x.format] || "");
  d.innerHTML = `<div class="fw">
    <div class="fw-kopf"><h2>${n === 1 ? "Eine Datei fehlt" : `${anzahl(n)} Dateien fehlen`}</h2>
      <p class="dim">${fw.neu ? "Beim Einlesen nicht mehr gefunden" : "Nicht mehr gefunden"} — im Dateimanager gelöscht oder ausserhalb der Ordner von partAtlas
        verschoben. Was soll mit den Einträgen im Katalog geschehen? Deine Dateien auf der Platte betrifft das nicht.</p></div>
    <div class="fw-alle"><span>Für alle</span>${segment("data-fw-alle", alleGleich(fw.liste.map((x) => x.id)))}</div>
    <div class="fw-liste">${[...gruppen].map(([ordner, xs]) => `
      <div class="fw-gruppe"><span class="fw-ordner" title="${esc(ordner)}">📁 ${esc(ordner || "–")} <em>${xs.length}</em></span>
        ${xs.length > 1 ? segment(`data-fw-ordner="${esc(ordner)}" data-fw-wert`, alleGleich(xs.map((x) => x.id))) : ""}</div>
      ${xs.map((x) => `<div class="fw-zeile">
        <span class="fw-name"><span><b>${esc(x.name)}</b>${titelEndung(x)}</span><small class="dim">${esc(haengtText(x.haengt))}</small></span>
        ${segment(`data-fw-id="${esc(x.id)}" data-fw-wert`, fw.wahl.get(x.id))}</div>`).join("")}`).join("")}
    </div>
    <div class="fw-fuss">
      <span class="dim">${zusammen}${zaehle("loeschen") ? " — zurückholbar unter Bereinigen" : ""}</span>
      <button type="button" class="knopf" data-fw="spaeter" title="Nichts ändern; die Modelle stehen unter Bereinigen › Datei fehlt">Später entscheiden</button>
      <button type="button" class="knopf akzent" data-fw="ok">Übernehmen</button></div></div>`;
}

document.addEventListener("click", async (e) => {
  if (!e.target.closest?.("#fehlt-fenster")) {
    if (e.target.closest?.("[data-fehlende-entscheiden]")) fehlendeFenster();
    return;
  }
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.fwAlle) { fw.liste.forEach((x) => fw.wahl.set(x.id, b.dataset.fwAlle)); return fwZeichnen(); }
  if (b.dataset.fwOrdner != null && b.dataset.fwWert) {
    fw.liste.filter((x) => x.ordner === b.dataset.fwOrdner).forEach((x) => fw.wahl.set(x.id, b.dataset.fwWert));
    return fwZeichnen();
  }
  if (b.dataset.fwId) { fw.wahl.set(b.dataset.fwId, b.dataset.fwWert); return fwZeichnen(); }
  if (b.dataset.fw === "spaeter") return $("#fehlt-fenster").close();
  if (b.dataset.fw === "ok") {
    const je = { archiv: [], behalten: [], loeschen: [] };
    for (const [id, w] of fw.wahl) je[w].push(id);
    b.disabled = true;
    b.textContent = "Wird übernommen …";
    try {
      const r = await api("/api/fehlende/entscheiden", { method: "POST", body: je });
      $("#fehlt-fenster").close();
      toast([r.archiv && `${anzahl(r.archiv)} im Archiv`, r.behalten && `${anzahl(r.behalten)} behalten`,
             r.geloescht && `${anzahl(r.geloescht)} im Papierkorb`].filter(Boolean).join(" · ") || "Erledigt.");
      neuLaden();
    } catch (err) { toast(err.message); b.disabled = false; b.textContent = "Übernehmen"; }
  }
});
