// G-Code ohne Modell (Bereinigen): was das Einlesen nicht eindeutig zuordnen konnte (gcode_ordner.py). Je G-Code: Grund in Worten, passende
// Modelle zum Anklicken, „Modell wählen …“ mit Suche, „Nicht zuordnen“ (ausblenden, zurücknehmbar). Die Datei im Ordner fasst partAtlas nicht an.

const gco = { daten: null };

function zeigeGcode(an) {
  if (an) for (const s of ["#tagleiste", "#raster", "#listenkopf", "#stapel", "#pk-leiste", "#filterzeile", "#leer", "#pfad"]) $(s).hidden = true;
  $("#gcode-offen").hidden = !an;
}

async function ladeGcode() {
  try { gco.daten = await api("/api/gcode_offen"); } catch (e) { return toast(e.message); }
  zeichneGcode();
}

function gcGrund(e) {
  const nennt = e.namen.map((n) => `„${n}“`).join(", ");
  if (e.art === "unklar") return `nennt ${nennt} — ${e.kandidaten.length} Modelle heissen so. Welches war es?`;
  if (!e.namen.length) return "nennt kein Modell, und der Dateiname passt zu keinem";
  return `nennt ${nennt} — kein Modell heisst so (umbenannt, gelöscht oder noch nicht eingelesen?)`;
}

function gcZeile(e) {
  const kand = e.kandidaten.map((m) => `<button class="knopf klein" data-gc-zu="${esc(e.id)}" data-modell="${esc(m.id)}" title="Diesem Modell zuordnen">
      → ${esc(m.name)}${esc(endung[m.format] || "")}<span class="dim"> · ${esc(m.ordner || "")}</span></button>`).join("");
  return `<div class="af-zeile gc-zeile" data-id="${esc(e.id)}">
    <div class="af-was">
      <b class="af-name">${esc(e.name)}</b>
      <div class="af-grund">${esc(gcGrund(e))}</div>
      <div class="af-pfade"><button class="af-pfad" data-gc-zeigen="${esc(e.id)}" title="Im Ordner zeigen">📂 ${esc(e.ordner)}</button></div>
      ${kand ? `<div class="af-chips gc-kandidaten">${kand}</div>` : ""}
    </div>
    <div class="af-aktion">
      <button class="knopf klein" data-gc-waehlen="${esc(e.id)}" data-name="${esc(e.name)}">Modell wählen …</button>
      <button class="knopf klein" data-gc-weg="${esc(e.id)}" title="Nicht mehr zeigen — zurücknehmbar">Nicht zuordnen</button>
    </div>
  </div>`;
}

function zeichneGcode() {
  const d = gco.daten;
  if (!d) return;
  const n = d.eintraege.length;
  abgleichen($("#gcode-offen"), `<div class="af-kopf">
      <h2>G-Code ohne Modell</h2>
      <p>${n ? `${anzahl(n)} ${n === 1 ? "G-Code" : "G-Codes"} aus deinen Ordnern konnte partAtlas keinem Modell sicher zuordnen.` : "Alle G-Codes aus deinen Ordnern sind zugeordnet."}
        Ordnest du einen zu, hängt er am Modell wie ein hochgeladener — als Druck „Noch nicht gedruckt“. Die Datei bleibt im Ordner.</p>
      ${d.ausgeblendet ? `<p class="dim"><button class="link" data-gc-ausgeblendet>${anzahl(d.ausgeblendet)} nicht zugeordnet (ausgeblendet)</button></p>` : ""}
    </div>
    <section class="af-gruppe">${d.eintraege.map(gcZeile).join("") || `<p class="dim af-leer">Nichts zu tun.</p>`}</section>`);
}

async function gcZuordnen(id, modelle) {
  await api("/api/gcode_offen/zuordnen", { method: "POST", body: { id, modelle } });
  toast("Zugeordnet — der G-Code steht jetzt beim Modell unter „Drucke“.");
  await ladeGcode();
  neuLaden();
}

// Modell wählen: Suche über den Katalog, Klick ordnet zu.
async function gcWaehlen(id, name) {
  const d = $("#dialog");
  d.classList.add("breit");
  const warten = dialog(`<h2>Modell für ${esc(name)}</h2>
    <input type="text" id="gc-suche" placeholder="Modell suchen …" autocomplete="off">
    <div class="waehler" id="gc-liste"></div>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button></div>`);
  const laden = async () => {
    const q = $("#gc-suche").value.trim();
    const liste = await api(`/api/modelle?q=${encodeURIComponent(q)}`);
    $("#gc-liste").innerHTML = liste.slice(0, 120).map((m) => `<div class="w-zeile">
      ${bildUrl(m) ? `<img loading="lazy" src="${bildUrl(m)}" alt="">` : `<div class="mini"></div>`}
      <div><b>${esc(m.name + (endung[m.format] || ""))}</b><small>${esc(m.ordner[0]?.split("/").slice(1).join("/") || "")}</small></div>
      <button type="button" class="knopf klein" data-gc-nimm="${esc(m.id)}">Zuordnen</button></div>`).join("") || '<div class="pos-leer">Nichts gefunden.</div>';
  };
  let zeit;
  $("#gc-suche").addEventListener("input", () => { clearTimeout(zeit); zeit = setTimeout(laden, 150); });
  $("#gc-liste").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-gc-nimm]");
    if (!b) return;
    d.close("ok");
    try { await gcZuordnen(id, [b.dataset.gcNimm]); } catch (err) { toast(err.message); }
  });
  $("#gc-suche").value = name.replace(/\.gcode$/i, "").replace(/^\d{4}-\d{4}-/, "").replace(/_plate\d+.*$/i, "");
  laden();
  $("#gc-suche").focus();
  await warten;
  d.classList.remove("breit");
}

async function gcAusgeblendete() {
  const liste = await api("/api/gcode_offen/ausgeblendet");
  const a = await dialog(`<h2>Nicht zugeordnet</h2><p class="dim">Diese G-Codes zeigt partAtlas nicht mehr. Häkchen weg = wieder zeigen.</p>
    <div class="dl-liste">${liste.map((x) => `<label class="dl-zeile"><input type="checkbox" data-gc-aus="${esc(x.id)}" checked>
      <span class="dl-pfad">${esc(x.name)}</span><span></span></label>`).join("")}</div>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Übernehmen</button></div>`);
  if (a !== "ja") return;
  for (const k of document.querySelectorAll("[data-gc-aus]:not(:checked)")) {
    await api("/api/gcode_offen/ausblenden", { method: "POST", body: { id: k.dataset.gcAus, an: false } }).catch((e) => toast(e.message));
  }
  await ladeGcode();
  neuLaden();
}

document.addEventListener("click", async (e) => {
  const t = e.target.closest?.("#gcode-offen button");
  if (!t) return;
  const d = t.dataset;
  try {
    if (d.gcZu) return await gcZuordnen(d.gcZu, [d.modell]);
    if (d.gcWaehlen) return await gcWaehlen(d.gcWaehlen, d.name);
    if (d.gcZeigen) return await api("/api/gcode_offen/im_ordner", { method: "POST", body: { id: d.gcZeigen } });
    if (d.gcWeg) {
      await api("/api/gcode_offen/ausblenden", { method: "POST", body: { id: d.gcWeg, an: true } });
      toast("Ausgeblendet — oben unter „nicht zugeordnet“ zurückholbar.");
      await ladeGcode();
      return neuLaden();
    }
    if ("gcAusgeblendet" in d) return await gcAusgeblendete();
  } catch (err) { toast(err.message); }
});
