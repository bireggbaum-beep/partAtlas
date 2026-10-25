// Filamentlager (lager.py): die Spulen des Anwenders in einem Fenster, wie der „Material Manager“ des 3MF Katalog Managers.
// Liste mit Rest und Wert, dazu ein Formular zum Anlegen und Ändern. Leere Spulen werden archiviert, nicht gelöscht.

const lager = { daten: null, leere: false, form: null, offen: false };

const lgEuro = (x) => `${Number(x).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;
const lgAnteil = (s) => (s.start_g ? Math.max(0, Math.min(1, s.rest_g / s.start_g)) : 0);
const lgStand = (s) => (s.rest_g <= 0 ? "leer" : lgAnteil(s) <= 0.1 ? "knapp" : "voll");

function lgSumme(spulen) {
  const aktiv = spulen.filter((s) => !s.archiviert);
  const kg = aktiv.reduce((a, s) => a + s.rest_g, 0) / 1000;
  const wert = aktiv.reduce((a, s) => a + (s.preis != null && s.start_g ? s.preis * (s.rest_g / s.start_g) : 0), 0);
  return { n: aktiv.length, kg, wert, ohnePreis: aktiv.some((s) => s.preis == null) };
}

function lgZeile(s) {
  const stand = lgStand(s);
  const name = [s.hersteller, s.farbname].filter(Boolean).join(" ");
  return `<div class="lg-zeile ${s.archiviert ? "archiv" : ""}" data-lg-id="${esc(s.id)}">
    ${tupfer(s.farbe, s.farbname || "")}
    <div class="lg-name"><b>${esc(s.material)}</b>${name ? ` · ${esc(name)}` : ""}
      <span class="dim">${[s.durchmesser ? `${zahl(s.durchmesser, 2)} mm` : "", s.ort].filter(Boolean).map(esc).join(" · ")}</span></div>
    <div class="lg-rest ${stand}" title="${zahl(s.rest_g, 1)} von ${zahl(s.start_g, 0)} g"><i style="width:${Math.round(lgAnteil(s) * 100)}%"></i></div>
    <span class="lg-g mono">${zahl(s.rest_g, 0)} g</span>
    <span class="lg-preis dim">${s.preis != null ? lgEuro(s.preis) : ""}</span>
    <button type="button" class="knopf-text" data-lg-bearbeiten="${esc(s.id)}" title="Bearbeiten">✎</button>
    <button type="button" class="knopf-text" data-lg-archiv="${esc(s.id)}" title="${s.archiviert ? "Wieder aktivieren" : "Als leer ablegen"}">${s.archiviert ? "↺" : "▣"}</button>
  </div>`;
}

function lgListe() {
  const d = lager.daten, summe = lgSumme(d.spulen);
  const sichtbar = d.spulen.filter((s) => lager.leere || !s.archiviert);
  const archiviert = d.spulen.length - summe.n;
  return `<div class="lg">
    <h2>Filamentlager</h2>
    <p class="dim">${summe.n ? `${summe.n} ${summe.n === 1 ? "Spule" : "Spulen"} · ${zahl(summe.kg, 2)} kg Rest · Wert ${lgEuro(summe.wert)}${summe.ohnePreis ? " (ohne Spulen ohne Preis)" : ""}` : "Noch keine Spulen. Lege deine Spulen an, dann weiss partAtlas, was du hast."}</p>
    <div class="lg-leiste">
      <button type="button" class="knopf akzent" data-lg-neu>＋ Spule</button>
      ${archiviert ? `<label><input type="checkbox" data-lg-leere ${lager.leere ? "checked" : ""}> Abgelegte zeigen (${archiviert})</label>` : ""}
    </div>
    <div class="lg-liste">${sichtbar.length ? sichtbar.map(lgZeile).join("") : `<p class="dim">${summe.n ? "Keine abgelegten Spulen." : ""}</p>`}</div>
    <div class="knoepfe"><button class="knopf" value="ok">Schliessen</button></div>
  </div>`;
}

function lgForm() {
  const f = lager.form, d = lager.daten, neu = !f.id;
  const wert = (k, v = "") => esc(f.werte[k] ?? v);
  const optionen = (liste, aktuell) => liste.map((m) => `<option value="${esc(m)}" ${m === aktuell ? "selected" : ""}>${esc(m)}</option>`).join("");
  const mats = [...new Set([...d.materialien, ...(f.werte.material ? [f.werte.material] : [])])];
  const hersteller = [...new Set(d.spulen.map((s) => s.hersteller).filter(Boolean))], orte = [...new Set(d.spulen.map((s) => s.ort).filter(Boolean))];
  return `<div class="lg">
    <h2>${neu ? "Neue Spule" : "Spule bearbeiten"}</h2>
    <div class="lg-form">
      <label>Material <select id="lg-material">${optionen(mats, f.werte.material || mats[0])}</select></label>
      <label>Hersteller <input id="lg-hersteller" list="lg-hersteller-liste" value="${wert("hersteller")}" maxlength="60"></label>
      <label>Farbname <input id="lg-farbname" value="${wert("farbname")}" maxlength="40" placeholder="z. B. Galaxy Black"></label>
      <div class="lg-farbe"><span>Farbe</span>
        <div class="farbfelder">${FARBEN.map(([n, h]) => `<button type="button" class="farbfeld ${h === f.werte.farbe ? "aktiv" : ""}" data-lg-farbe="${h}" title="${n}" style="background:${h}"></button>`).join("")}
          <button type="button" class="knopf ${f.werte.farbe ? "" : "aktiv"}" data-lg-farbe="">keine</button></div></div>
      <label>Durchmesser <select id="lg-durchmesser">${optionen(["1.75", "2.85"], String(f.werte.durchmesser ?? 1.75))}</select> mm</label>
      <label>Gewicht der vollen Spule <input id="lg-start" type="number" min="1" max="20000" step="10" value="${wert("start_g", d.rolle_g)}"> g</label>
      ${neu ? "" : `<label>Rest <input id="lg-rest" type="number" min="0" max="20000" step="1" value="${wert("rest_g")}"> g</label>`}
      <label>Preis der vollen Spule <input id="lg-preis" type="text" inputmode="decimal" value="${wert("preis")}" placeholder="optional"> €</label>
      <label>Lagerort <input id="lg-ort" list="lg-ort-liste" value="${wert("ort")}" maxlength="60"></label>
      <label>Notiz <input id="lg-notiz" value="${wert("notiz")}" maxlength="500"></label>
      ${neu ? `<label>Anzahl <input id="lg-anzahl" type="number" min="1" max="20" value="1"> gleiche Spulen, alle voll</label>` : ""}
      <datalist id="lg-hersteller-liste">${hersteller.map((h) => `<option value="${esc(h)}">`).join("")}</datalist>
      <datalist id="lg-ort-liste">${orte.map((o) => `<option value="${esc(o)}">`).join("")}</datalist>
    </div>
    <div class="knoepfe"><button type="button" class="knopf" data-lg-zurueck>Abbrechen</button><button type="button" class="knopf akzent" data-lg-speichern>${neu ? "Anlegen" : "Speichern"}</button></div>
  </div>`;
}

function lgZeichnen() {
  $("#dialog-inhalt").innerHTML = lager.form ? lgForm() : lgListe();
}

async function lgLaden() {
  lager.daten = await api("/api/spulen");
}

function lgFormLesen() {
  const v = (id) => $(`#${id}`)?.value ?? "";
  const werte = {
    material: v("lg-material"), hersteller: v("lg-hersteller"), farbname: v("lg-farbname"), farbe: lager.form.werte.farbe || "",
    durchmesser: v("lg-durchmesser"), start_g: v("lg-start"), preis: v("lg-preis"), ort: v("lg-ort"), notiz: v("lg-notiz"),
  };
  if (lager.form.id) werte.rest_g = v("lg-rest");
  return werte;
}

async function lgSpeichern() {
  const werte = lgFormLesen();
  try {
    if (lager.form.id) await api(`/api/spulen/${lager.form.id}`, { method: "PATCH", body: werte });
    else {
      const anzahl = Number($("#lg-anzahl")?.value) || 1;
      await api("/api/spulen", { method: "POST", body: { felder: werte, anzahl } });
      toast(anzahl === 1 ? "Spule angelegt." : `${anzahl} Spulen angelegt.`);
    }
    await lgLaden();
    lager.form = null;
    lgZeichnen();
  } catch (e) { toast(e.message); }
}

async function oeffneLager() {
  try { await lgLaden(); } catch (e) { return toast(e.message); }
  Object.assign(lager, { form: null, offen: true });
  const zu = dialog(lgListe());
  await zu;
  lager.offen = false;
}

$("#dialog-inhalt").addEventListener("click", async (e) => {
  if (!lager.offen) return;
  const t = e.target;
  const hol = (a) => t.closest?.(`[${a}]`);
  if (hol("data-lg-neu")) { lager.form = { id: null, werte: { durchmesser: 1.75, start_g: lager.daten.rolle_g } }; return lgZeichnen(); }
  const bearb = hol("data-lg-bearbeiten");
  if (bearb) { lager.form = { id: bearb.dataset.lgBearbeiten, werte: { ...lager.daten.spulen.find((s) => s.id === bearb.dataset.lgBearbeiten) } }; return lgZeichnen(); }
  if (hol("data-lg-zurueck")) { lager.form = null; return lgZeichnen(); }
  if (hol("data-lg-speichern")) return lgSpeichern();
  const farbe = hol("data-lg-farbe");
  if (farbe) { lager.form.werte = { ...lgFormLesen(), farbe: farbe.dataset.lgFarbe }; return lgZeichnen(); }
  const archiv = hol("data-lg-archiv");
  if (archiv) {
    const s = lager.daten.spulen.find((x) => x.id === archiv.dataset.lgArchiv);
    try { await api(`/api/spulen/${s.id}`, { method: "PATCH", body: { archiviert: !s.archiviert } }); await lgLaden(); lgZeichnen(); }
    catch (er) { toast(er.message); }
  }
});
$("#dialog-inhalt").addEventListener("change", (e) => {
  if (lager.offen && e.target.matches?.("[data-lg-leere]")) { lager.leere = e.target.checked; lgZeichnen(); }
});
document.addEventListener("click", (e) => { if (e.target.closest?.("#lager")) oeffneLager(); });
