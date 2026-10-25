// Filamentlager (lager.py) — die Seite „Lager“, nach dem Material Manager des 3MF Katalog Managers (Handbuch „Der Material Manager“):
// Kennzahlen, Suche, Filter „Niedrig“/„Leer“, Dashboard (Karten) oder sortierbare Liste, Formular als Seitenfenster rechts, Nachkaufen.
// Eine Spule ist kein Modell: sie lässt sich löschen (mit Rückgängig). Ein Foto der Spule ist optional (PNG, JPG, WebP bis 5 MB).

const lg = { daten: null, suche: "", filter: new Set(), ansicht: localStorageLesen("lager-ansicht") || "dashboard", sort: { spalte: "material", richtung: 1 },
             form: null, neu: new Set() };
const NIEDRIG_BIS = 0.2;                 // bis zu so viel Rest (Anteil der vollen Spule) gilt eine Spule als niedrig

const lgEuro = (x) => (x == null ? "" : Number(x).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const lgG = (x) => `${zahl(x, 1)} g`;
const lgAnteil = (s) => (s.start_g ? Math.max(0, Math.min(1, s.rest_g / s.start_g)) : 0);
const lgStatus = (s) => (s.rest_g <= 0 ? "leer" : lgAnteil(s) <= NIEDRIG_BIS ? "niedrig" : "vorraetig");
const LG_STATUS = { vorraetig: "Vorrätig", niedrig: "Niedrig", leer: "Leer" };

// Die Spule als Bild (spule.png, freigestellt) mit der Wicklung in der Farbe der Spule: über die Maske spule-wicklung.png liegt der Farbwert und wird mit dem
// Bild multipliziert (CSS). Sehr dunkle Farben werden aufgehellt, damit Rillen und Form sichtbar bleiben; ohne Farbe ein helles Grau.
function lgSpule(farbe, breite = 50) {
  const m = /^#([0-9a-f]{6})$/i.exec(farbe || "");
  const n = m ? parseInt(m[1], 16) : 0xd0d0d4;
  const r = n >> 16, g = (n >> 8) & 255, b = n & 255;
  const hell = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  const ton = hell < 0.26 ? `rgb(${Math.round(70 + r * 0.2)}, ${Math.round(70 + g * 0.2)}, ${Math.round(76 + b * 0.2)})` : `#${(n | 0x1000000).toString(16).slice(1)}`;
  return `<span class="lg-spule" style="--w:${ton};width:${breite}px" aria-hidden="true"><img src="/web/spule.png" alt=""><i></i></span>`;
}

function zeigeLager(an) {
  if (an) for (const s of ["#tagleiste", "#raster", "#listenkopf", "#stapel", "#pk-leiste", "#filterzeile", "#leer", "#pfad", "#aufraeumen", "#bg-ansicht"]) $(s).hidden = true;
  $("#lager-seite").hidden = !an;
  document.body.classList.toggle("im-lager", an);
  if (!an) lgFormZu();
}

async function ladeLager() {
  try { lg.daten = await api("/api/spulen"); } catch (e) { return toast(e.message); }
  zeichneLager();
}

function lgSichtbar() {
  const q = lg.suche.trim().toLowerCase();
  const stufen = ["niedrig", "leer"].filter((f) => lg.filter.has(f));
  return lg.daten.spulen.filter((s) => (!stufen.length || stufen.includes(lgStatus(s)))
    && (!q || [s.material, s.hersteller, s.farbname, s.ort, s.notiz].some((t) => (t || "").toLowerCase().includes(q))));
}

function lgKennzahlen() {
  const aktiv = lg.daten.spulen;
  const knapp = aktiv.filter((s) => lgStatus(s) !== "vorraetig").length;
  const orte = new Set(aktiv.map((s) => (s.ort || "").trim()).filter(Boolean)).size;
  const rest = aktiv.reduce((a, s) => a + s.rest_g, 0);
  return [["Spulen gesamt", zahl(aktiv.length, 0)], ["Restbestand gesamt", `${zahl(rest, 0)} g`], ["Belegte Lagerplätze", zahl(orte, 0)], ["Niedrig / leer", zahl(knapp, 0), knapp ? "warn" : ""]];
}

function lgKarte(s) {
  const st = lgStatus(s), name = [s.hersteller, s.farbname].filter(Boolean).join(" · ");
  return `<article class="lg-karte ${lg.neu.has(s.id) ? "neu" : ""}" data-lg-id="${esc(s.id)}">
    <div class="lg-kopf">${s.bild ? `<img class="lg-bild" src="/api/spulen/${esc(s.id)}/bild?k=${esc(s.bild.k)}" alt="">` : lgSpule(s.farbe, 50)}
      <div><b>${s.farbe ? `<span class="farbpunkt" style="background:${esc(s.farbe)}"></span>` : ""}${esc(s.material)}</b><span class="dim">${esc(name) || "&nbsp;"}</span></div></div>
    <div class="lg-reihe">${s.ort ? `<span class="lg-ort">${esc(s.ort)}</span>` : "<span></span>"}<span class="lg-marke st-${st}">${LG_STATUS[st]}</span></div>
    <div class="lg-reihe"><span class="mono">${lgG(s.rest_g)}</span><span class="dim">${Math.round(lgAnteil(s) * 100)} %</span></div>
    <div class="lg-balken st-${st}"><i style="width:${Math.round(lgAnteil(s) * 100)}%"></i></div>
    <div class="lg-reihe lg-klein dim"><span>${s.durchmesser ? `${zahl(s.durchmesser, 2)} mm` : ""}</span><span>${lgEuro(s.preis)}</span></div>
    <div class="lg-aktionen"><button type="button" class="knopf-text" data-lg-nachkaufen="${esc(s.id)}">＋ Nachkaufen</button>
      <span><button type="button" class="knopf-text" data-lg-bearbeiten="${esc(s.id)}" title="Bearbeiten" aria-label="Spule bearbeiten">✎</button>
      <button type="button" class="knopf-text" data-lg-loeschen="${esc(s.id)}" title="Löschen" aria-label="Spule löschen">✕</button></span></div>
  </article>`;
}

const LG_SPALTEN = [["material", "Material"], ["hersteller", "Hersteller"], ["farbname", "Farbe"], ["ort", "Lagerort"], ["durchmesser", "⌀"], ["rest_g", "Bestand"], ["preis", "Preis"], ["status", "Status"]];
function lgSortiert(liste) {
  const { spalte, richtung } = lg.sort;
  const wert = (s) => (spalte === "status" ? ["leer", "niedrig", "vorraetig"].indexOf(lgStatus(s)) : s[spalte]);
  return [...liste].sort((a, b) => {
    const x = wert(a), y = wert(b);
    if (x == null || x === "") return y == null || y === "" ? 0 : 1;
    if (y == null || y === "") return -1;
    return (typeof x === "number" ? x - y : String(x).localeCompare(String(y), "de")) * richtung;
  });
}
function lgTabelle(liste) {
  const kopf = LG_SPALTEN.map(([k, t]) => `<th><button type="button" data-lg-sort="${k}" aria-label="Sortieren nach ${t}">${t}${lg.sort.spalte === k ? (lg.sort.richtung > 0 ? " ▲" : " ▼") : ""}</button></th>`).join("");
  const zeilen = lgSortiert(liste).map((s) => {
    const st = lgStatus(s);
    return `<tr class="${lg.neu.has(s.id) ? "neu" : ""}" data-lg-id="${esc(s.id)}">
      <td><b>${esc(s.material)}</b></td><td>${esc(s.hersteller)}</td><td>${s.farbe ? `<span class="farbpunkt" style="background:${esc(s.farbe)}"></span> ` : ""}${esc(s.farbname)}</td>
      <td>${s.ort ? `<span class="lg-ort">${esc(s.ort)}</span>` : ""}</td><td>${s.durchmesser ? `${zahl(s.durchmesser, 2)} mm` : ""}</td>
      <td><span class="mono">${lgG(s.rest_g)}</span> <span class="dim">${Math.round(lgAnteil(s) * 100)} %</span><div class="lg-balken st-${st}"><i style="width:${Math.round(lgAnteil(s) * 100)}%"></i></div></td>
      <td class="mono">${lgEuro(s.preis)}</td><td><span class="lg-marke st-${st}">${LG_STATUS[st]}</span></td>
      <td class="lg-tab-akt"><button type="button" class="knopf-text" data-lg-nachkaufen="${esc(s.id)}" title="Nachkaufen" aria-label="Nachkaufen">＋</button>
        <button type="button" class="knopf-text" data-lg-bearbeiten="${esc(s.id)}" title="Bearbeiten" aria-label="Spule bearbeiten">✎</button>
        <button type="button" class="knopf-text" data-lg-loeschen="${esc(s.id)}" title="Löschen" aria-label="Spule löschen">✕</button></td></tr>`;
  }).join("");
  return `<table class="lg-tabelle"><thead><tr>${kopf}<th></th></tr></thead><tbody>${zeilen}</tbody></table>`;
}

function zeichneLager() {
  if (!lg.daten) return;
  const liste = lgSichtbar(), leer = !lg.daten.spulen.length;
  const merk = document.activeElement?.id === "lg-suche" ? [document.activeElement.selectionStart, document.activeElement.selectionEnd] : null;
  $("#lager-seite").innerHTML = `
    <h2 class="lg-titel">Lager</h2>
    <div class="lg-zahlen">${lgKennzahlen().map(([t, v, k]) => `<div class="lg-zahl ${k || ""}"><span>${t}</span><b>${v}</b></div>`).join("")}</div>
    <div class="lg-leiste">
      <input id="lg-suche" type="search" placeholder="Material, Hersteller, Lagerort durchsuchen …" value="${esc(lg.suche)}" aria-label="Lager durchsuchen">
      ${["niedrig", "leer"].map((f) => `<button type="button" class="knopf ${lg.filter.has(f) ? "aktiv" : ""}" data-lg-filter="${f}" aria-pressed="${lg.filter.has(f)}">${{ niedrig: "Niedrig", leer: "Leer" }[f]}</button>`).join("")}
      <span class="segment"><button type="button" data-lg-ansicht="dashboard" class="${lg.ansicht === "dashboard" ? "an" : ""}">Dashboard</button><button type="button" data-lg-ansicht="liste" class="${lg.ansicht === "liste" ? "an" : ""}">Liste</button></span>
      <span class="lg-luecke"></span>
      <button type="button" class="knopf akzent" data-lg-neu>＋ Spule anlegen</button>
    </div>
    ${leer ? `<div class="lg-leerlager">${lgSpule("", 150)}<p class="lg-leer">Noch keine Spulen. Lege deine Spulen an, dann weiss partAtlas, was du hast und was reicht.</p>
        <button type="button" class="knopf akzent" data-lg-neu>＋ Spule anlegen</button></div>`
      : !liste.length ? `<p class="lg-leer">Keine Spulen für diese Auswahl.</p>`
      : lg.ansicht === "liste" ? lgTabelle(liste) : `<div class="lg-karten">${lgSortiert(liste).map(lgKarte).join("")}</div>`}`;
  if (merk) { const f = $("#lg-suche"); f.focus(); f.setSelectionRange(...merk); }
}

// ------------------------------------------------------------------ Formular (Seitenfenster rechts)

function lgFormZu() {
  lg.form = null;
  const f = $("#lager-form");
  f.hidden = true;
  f.innerHTML = "";
}

function lgFormZeigen(spule, vorlage = null) {
  const neu = !spule, w = spule || vorlage || { durchmesser: 1.75, start_g: lg.daten.rolle_g };
  lg.form = { id: spule?.id || null, farbe: w.farbe || "", datei: null, bildWeg: false, bild: spule?.bild || (vorlage?.bild ? null : null) };
  const d = lg.daten, anzahl = (id, liste) => `<datalist id="${id}">${[...new Set(liste.filter(Boolean))].map((x) => `<option value="${esc(x)}">`).join("")}</datalist>`;
  const wert = (v) => esc(v ?? "");
  $("#lager-form").innerHTML = `
    <header><h3>${neu ? "Spule anlegen" : "Spule bearbeiten"}</h3><button type="button" class="knopf" data-lg-formzu aria-label="Schliessen">✕</button></header>
    <div class="lf-koerper">
      <div class="i-titel">BILD</div>
      <div class="lf-bild" id="lf-bild" tabindex="0" role="button" aria-label="Bild wählen oder hierher ziehen">${lgBildFeld()}</div>
      <input type="file" id="lf-bilddatei" accept="image/png,image/jpeg,image/webp" hidden>
      <p class="lf-bildhinweis" id="lf-bildhinweis" hidden></p>
      <div class="i-titel">IDENTIFIKATION</div>
      <label>Material<input id="lf-material" list="lf-material-liste" value="${wert(w.material)}" maxlength="30" placeholder="Material" autocomplete="off"></label>
      <label>Hersteller<input id="lf-hersteller" list="lf-hersteller-liste" value="${wert(w.hersteller)}" maxlength="60" placeholder="Hersteller" autocomplete="off"></label>
      <label>Farbname<input id="lf-farbname" value="${wert(w.farbname)}" maxlength="40" placeholder="Farbname"></label>
      <div class="lf-farbe"><span>Farbwert</span>
        <div class="farbfelder">${FARBEN.map(([n, h]) => `<button type="button" class="farbfeld ${h === lg.form.farbe ? "aktiv" : ""}" data-lg-farbe="${h}" title="${n}" aria-label="${n}" style="background:${h}"></button>`).join("")}</div>
        <div class="lf-hex"><input type="color" id="lf-farbwahl" value="${lg.form.farbe || "#1a1a1a"}" aria-label="Farbe wählen"><input id="lf-hex" value="${wert(lg.form.farbe)}" placeholder="#1a1a1a" maxlength="7" aria-label="Farbwert als Hex">
          <button type="button" class="knopf" data-lg-farbe="">keine</button></div></div>
      ${neu ? `<div class="lf-anzahl"><span>Anzahl Spulen</span><div><button type="button" class="knopf" data-lg-anzahl="-1" aria-label="Eine weniger">−</button><input id="lf-anzahl" type="number" min="1" max="20" value="1" aria-label="Anzahl Spulen"><button type="button" class="knopf" data-lg-anzahl="1" aria-label="Eine mehr">+</button></div>
        <p class="dim">Legt mehrere identische Spulen mit eigenem Bestand an (z. B. 3× Schwarz PLA).</p></div>` : ""}
      <div class="i-titel">LAGERUNG</div>
      <label>Lagerort<input id="lf-ort" list="lf-ort-liste" value="${wert(w.ort)}" maxlength="60" placeholder="Lagerort" autocomplete="off"></label>
      <div class="i-titel">BESTAND</div>
      <div class="lf-zwei"><label>Durchmesser (mm)<input id="lf-durchmesser" type="number" step="0.05" min="1" max="3.5" value="${wert(w.durchmesser)}"></label>
        <label>Preis (€)<input id="lf-preis" type="text" inputmode="decimal" value="${wert(w.preis)}" placeholder="optional"></label></div>
      <div class="lf-zwei"><label>Ursprungsgewicht (g)<input id="lf-start" type="number" min="1" max="20000" step="10" value="${wert(w.start_g)}"></label>
        <label>Restgewicht (g)<input id="lf-rest" type="number" min="0" max="20000" step="1" value="${wert(neu ? w.start_g : w.rest_g)}"></label></div>
      <div class="lg-balken st-vorraetig" id="lf-balken"><i></i></div><b id="lf-prozent" class="lf-prozent"></b>
      <label>Notiz<input id="lf-notiz" value="${wert(w.notiz)}" maxlength="500"></label>
      ${anzahl("lf-material-liste", [...new Set([...d.materialien, ...d.spulen.map((s) => s.material)])])}${anzahl("lf-hersteller-liste", d.spulen.map((s) => s.hersteller))}${anzahl("lf-ort-liste", d.spulen.map((s) => s.ort))}
    </div>
    <footer><button type="button" class="knopf akzent" data-lg-speichern>${neu ? "Hinzufügen" : "Speichern"}</button></footer>`;
  $("#lager-form").hidden = false;
  lgFormBalken();
  $("#lf-material").focus();
}

function lgBildFeld() {
  const f = lg.form;
  const url = f.datei ? f.vorschau : (f.bild && !f.bildWeg ? `/api/spulen/${f.id}/bild?k=${f.bild.k}` : "");
  return url ? `<img src="${esc(url)}" alt="Foto der Spule"><button type="button" class="knopf" data-lg-bildweg aria-label="Bild entfernen">✕</button>`
    : `${lgSpule(f.farbe, 64)}<span class="dim">Bild hierher ziehen oder klicken</span>`;
}

function lgBildWaehlen(datei) {
  const hinweis = $("#lf-bildhinweis");
  const fehler = !datei ? "" : !["image/png", "image/jpeg", "image/webp"].includes(datei.type) ? "Nur PNG, JPG oder WebP."
    : datei.size > 5 * 1024 * 1024 ? "Das Bild ist grösser als 5 MB." : "";
  hinweis.hidden = !fehler;
  hinweis.textContent = fehler;
  if (!datei || fehler) return;
  if (lg.form.vorschau) URL.revokeObjectURL(lg.form.vorschau);
  Object.assign(lg.form, { datei, vorschau: URL.createObjectURL(datei), bildWeg: false });
  $("#lf-bild").innerHTML = lgBildFeld();
}

// Das Bild wird mit „Speichern“ übernommen, nicht gleich beim Wählen: Escape lässt alles, wie es war.
async function lgBildSpeichern(ids) {
  const f = lg.form;
  for (const id of ids) {
    if (f.datei) {
      const r = await fetch(`/api/spulen/${id}/bild`, { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: f.datei });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).fehler || `Fehler ${r.status}`);
    } else if (f.bildWeg && f.bild) await api(`/api/spulen/${id}/bild`, { method: "DELETE" });
  }
}

function lgFormBalken() {
  const start = parseFloat($("#lf-start")?.value), rest = parseFloat($("#lf-rest")?.value);
  const anteil = start > 0 && rest >= 0 ? Math.max(0, Math.min(1, rest / start)) : 0;
  $("#lf-balken i").style.width = `${Math.round(anteil * 100)}%`;
  $("#lf-balken").className = `lg-balken st-${rest <= 0 ? "leer" : anteil <= NIEDRIG_BIS ? "niedrig" : "vorraetig"}`;
  $("#lf-prozent").textContent = `${Math.round(anteil * 100)} %`;
}

function lgFormWerte() {
  const v = (id) => $(`#${id}`).value;
  return { material: v("lf-material"), hersteller: v("lf-hersteller"), farbname: v("lf-farbname"), farbe: lg.form.farbe, ort: v("lf-ort"), durchmesser: v("lf-durchmesser"),
    preis: v("lf-preis"), start_g: v("lf-start"), rest_g: v("lf-rest"), notiz: v("lf-notiz") };
}

async function lgSpeichern() {
  const werte = lgFormWerte();
  try {
    let ids = [];
    if (lg.form.id) { await api(`/api/spulen/${lg.form.id}`, { method: "PATCH", body: werte }); await lgBildSpeichern([lg.form.id]); }
    else {
      const anzahl = Number($("#lf-anzahl").value) || 1;
      ({ ids } = await api("/api/spulen", { method: "POST", body: { felder: werte, anzahl } }));
      await lgBildSpeichern(ids);
      toast(anzahl === 1 ? "Spule angelegt." : `${anzahl} Spulen angelegt.`);
    }
    lgFormZu();
    await lgNeuLaden(ids);
  } catch (e) { toast(e.message); }
}

// Neue Einträge sind kurz hervorgehoben (3MF Katalog: grün umrandet).
async function lgNeuLaden(neueIds = []) {
  lg.neu = new Set(neueIds);
  await ladeLager();
  if (neueIds.length) setTimeout(() => { lg.neu = new Set(); zeichneLager(); }, 2500);
}

// ------------------------------------------------------------------ Nachkaufen

async function lgNachkaufen(sid) {
  const s = lg.daten.spulen.find((x) => x.id === sid);
  const a = await dialog(`<h2>Nachkaufen</h2>
    <p class="dim">${esc(s.material)}${s.hersteller || s.farbname ? ` · ${esc([s.hersteller, s.farbname].filter(Boolean).join(" "))}` : ""} — neue, volle Spulen mit denselben Angaben.</p>
    <div class="lg-nachkauf">
      <label>Anzahl (1 bis 20)<input id="nk-anzahl" type="number" min="1" max="20" value="1"></label>
      <label>Menge je Spule (g)<input id="nk-menge" type="number" min="1" max="20000" value="${esc(s.start_g)}"></label>
      <label>Preis je Spule (€)<input id="nk-preis" type="text" inputmode="decimal" value="${esc(s.preis ?? "")}"></label>
      <label>Lagerort<input id="nk-ort" value="${esc(s.ort || "")}" maxlength="60"></label>
    </div>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Nachkaufen</button></div>`);
  if (a !== "ja") return;
  try {
    const { ids } = await api(`/api/spulen/${sid}/nachkaufen`, { method: "POST",
      body: { anzahl: Number($("#nk-anzahl").value) || 1, felder: { start_g: $("#nk-menge").value, preis: $("#nk-preis").value, ort: $("#nk-ort").value } } });
    toast(ids.length === 1 ? "Spule nachgekauft." : `${ids.length} Spulen nachgekauft.`);
    await lgNeuLaden(ids);
  } catch (e) { toast(e.message); }
}

async function lgLoeschen(sid) {
  try {
    await api(`/api/spulen/${sid}`, { method: "DELETE" });
    await ladeLager();
    toast("Spule gelöscht.", { aktionen: [["Rückgängig", async () => { await api(`/api/spulen/${sid}/zurueck`, { method: "POST" }); await ladeLager(); }]] });
  } catch (e) { toast(e.message); }
}

// ------------------------------------------------------------------ Bedienung

document.addEventListener("click", (e) => {
  const t = e.target;
  if (!t.closest) return;
  if (t.closest("#lager-seite") || t.closest("#lager-form")) {
    const hol = (a) => t.closest(`[${a}]`);
    let b;
    if (hol("data-lg-neu")) return lgFormZeigen(null);
    if ((b = hol("data-lg-bearbeiten"))) return lgFormZeigen(lg.daten.spulen.find((s) => s.id === b.dataset.lgBearbeiten));
    if ((b = hol("data-lg-nachkaufen"))) return lgNachkaufen(b.dataset.lgNachkaufen);
    if ((b = hol("data-lg-loeschen"))) return lgLoeschen(b.dataset.lgLoeschen);
    if ((b = hol("data-lg-filter"))) { lg.filter.has(b.dataset.lgFilter) ? lg.filter.delete(b.dataset.lgFilter) : lg.filter.add(b.dataset.lgFilter); return zeichneLager(); }
    if ((b = hol("data-lg-ansicht"))) { lg.ansicht = b.dataset.lgAnsicht; localStorageSchreiben("lager-ansicht", lg.ansicht); return zeichneLager(); }
    if ((b = hol("data-lg-sort"))) {
      lg.sort = { spalte: b.dataset.lgSort, richtung: lg.sort.spalte === b.dataset.lgSort ? -lg.sort.richtung : 1 };
      return zeichneLager();
    }
    if (hol("data-lg-bildweg")) { Object.assign(lg.form, { datei: null, bildWeg: true }); $("#lf-bild").innerHTML = lgBildFeld(); return; }
    if (t.closest("#lf-bild")) return $("#lf-bilddatei").click();
    if (hol("data-lg-formzu")) return lgFormZu();
    if (hol("data-lg-speichern")) return lgSpeichern();
    if ((b = hol("data-lg-anzahl"))) { const f = $("#lf-anzahl"); f.value = Math.max(1, Math.min(20, (Number(f.value) || 1) + Number(b.dataset.lgAnzahl))); return; }
    if ((b = hol("data-lg-farbe"))) {
      lg.form.farbe = b.dataset.lgFarbe;
      $("#lf-hex").value = lg.form.farbe;
      if (lg.form.farbe) $("#lf-farbwahl").value = lg.form.farbe;
      document.querySelectorAll("#lager-form [data-lg-farbe]").forEach((x) => x.classList.toggle("aktiv", x.dataset.lgFarbe === lg.form.farbe));
    }
  }
});
document.addEventListener("dblclick", (e) => {
  const z = e.target.closest?.("#lager-seite [data-lg-id]");
  if (z && !e.target.closest("button")) lgFormZeigen(lg.daten.spulen.find((s) => s.id === z.dataset.lgId));
});
document.addEventListener("input", (e) => {
  const t = e.target;
  if (t.id === "lg-suche") { lg.suche = t.value; return zeichneLager(); }
  if (!t.closest?.("#lager-form")) return;
  if (t.id === "lf-start" || t.id === "lf-rest") lgFormBalken();
  if (t.id === "lf-farbwahl") { lg.form.farbe = t.value; $("#lf-hex").value = t.value; }
  if (t.id === "lf-hex" && /^#[0-9a-fA-F]{6}$/.test(t.value)) { lg.form.farbe = t.value.toLowerCase(); $("#lf-farbwahl").value = lg.form.farbe; }
  if (t.id === "lf-hex" && !t.value) lg.form.farbe = "";
  if (t.id === "lf-farbwahl" || t.id === "lf-hex") document.querySelectorAll("#lager-form [data-lg-farbe]").forEach((x) => x.classList.toggle("aktiv", x.dataset.lgFarbe === lg.form.farbe));
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && lg.form && !$("#dialog").open) { e.preventDefault(); lgFormZu(); }
  if (e.key === "Enter" && lg.form && e.target.closest?.("#lager-form") && e.target.matches("input:not([type=color])")) { e.preventDefault(); lgSpeichern(); }
});

document.addEventListener("change", (e) => { if (e.target.id === "lf-bilddatei") { lgBildWaehlen(e.target.files[0]); e.target.value = ""; } });
document.addEventListener("dragover", (e) => { if (e.target.closest?.("#lf-bild")) { e.preventDefault(); e.stopPropagation(); } });
document.addEventListener("drop", (e) => {
  if (!e.target.closest?.("#lf-bild")) return;
  e.preventDefault(); e.stopPropagation();
  lgBildWaehlen(e.dataTransfer.files[0]);
}, true);
document.addEventListener("keydown", (e) => { if ((e.key === "Enter" || e.key === " ") && e.target.id === "lf-bild") { e.preventDefault(); e.stopPropagation(); $("#lf-bilddatei").click(); } }, true);
