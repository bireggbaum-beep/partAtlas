"use strict";

// Werkbank: Projekte und Bausteine (Baugruppen) bearbeiten — Baum links, Inspektor rechts, in der Mitte die Übersicht (Stückliste und Fertigung
// folgen). Eigene Vollbild-Ansicht statt Seite im Katalog: wer baut, braucht Auswählen, Bearbeiten und Zurücknehmen, nicht Betrachten
// (KONZEPT §4.5a, mock/werkbank.html). Nur im Labor (Einstellungen › Ansicht › Baugruppen-Labor).
//
// Auswahl heisst eine Position an einem Ort im Baum: dasselbe Teil kann an mehreren Stellen stecken; was man ändert, ändert die Position in
// ihrer Baugruppe (und damit überall, wo diese Baugruppe verwendet wird). Alle Änderungen tragen `?im=<Kennung>` — das Projekt, das gerade
// offen ist, führt die Liste fürs Rückgängig.

const wb = { id: null, baum: null, flach: null, detail: null, sel: null, offen: new Set(), zurueck: [], index: {}, materialien: [], filter: "",
  reiter: ["stueckliste", "fertigung"].includes(localStorageLesen("wb-reiter")) ? localStorageLesen("wb-reiter") : "stueckliste",
  kat: { tab: "teile", q: "", zu: localStorageLesen("wb-kat-zu") === "1", sel: null, liste: [] }, zug: null };

const wbBasis = (id) => (id.startsWith("p_") ? "/api/projekte" : "/api/baugruppen");
const wbIst = (typ) => (wb.id || "").startsWith(typ === "projekt" ? "p_" : "b_");
const wbMit = (url) => `${url}${url.includes("?") ? "&" : "?"}im=${encodeURIComponent(wb.id)}`;
const WB_ICON = {
  projekt: '<svg class="wb-ic wb-proj" viewBox="0 0 16 16"><rect x="2.5" y="2.5" width="11" height="11" rx="1.5"/><path d="M5.5 6h5M5.5 8.5h5M5.5 11h3"/></svg>',
  baugruppe: '<svg class="wb-ic wb-baug" viewBox="0 0 16 16"><path d="M8 1.5 14 4.5v7L8 14.5 2 11.5v-7z"/><path d="M2 4.5 8 7.5l6-3M8 7.5v7"/></svg>',
  modell: '<svg class="wb-ic wb-druck" viewBox="0 0 16 16"><path d="M8 1.5 14 4.5v7L8 14.5 2 11.5v-7zM2 4.5 8 7.5l6-3M8 7.5v7"/></svg>',
  kaufteil: '<svg class="wb-ic wb-kauf" viewBox="0 0 16 16"><path d="M8 1.5 13 4.2v5.6L8 12.5 3 9.8V4.2z"/><circle cx="8" cy="7" r="1.6"/></svg>',
  eigen: '<svg class="wb-ic wb-kauf" viewBox="0 0 16 16"><circle cx="8" cy="8" r="5.5"/><path d="M5.5 8h5M8 5.5v5"/></svg>',
};
const wbArtName = { modell: "Druckteil", baugruppe: "Baugruppe", kaufteil: "Kaufteil", eigen: "Eigene Komponente" };

// ---------------------------------------------------------------- Seitenleiste: Projekte

async function ladeProjekteLeiste() {
  const ziel = $("#projekte");
  if (!ziel) return;
  let liste;
  try { liste = await api("/api/projekte"); } catch { return; }
  abgleichen(ziel, liste.map((p) => `<button class="eintrag ${wb.id === p.id ? "aktiv" : ""}" data-projekt="${esc(p.id)}" title="${esc(p.status || "")}">
      <span>${esc(p.name)}</span><em title="Positionen">${p.positionen}</em></button>`).join("")
    + (liste.length ? "" : `<button class="eintrag leer-eintrag" id="projekt-neu-2">＋ Neues Projekt</button>`));
}

async function neuesProjekt() {
  const a = await dialog(`<h2>Neues Projekt</h2>
    <p class="dim">Die Klammer um einen Bau-Auftrag: lose Teile, Baugruppen und Kaufteile für einen Zweck. Von hier verteilst du sie später auf Druckplatten.</p>
    <input type="text" id="wb-neu-name" placeholder="z. B. Halloween Deko 2026, Voron Toolhead Umbau">
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja" id="wb-neu-ok">Anlegen</button></div>`);
  if (a !== "ja") return;
  try {
    const { id } = await api("/api/projekte", { method: "POST", body: { name: $("#wb-neu-name").value } });
    await ladeProjekteLeiste();
    wbOeffne(id);
  } catch (e) { toast(e.message); }
}

// ---------------------------------------------------------------- Öffnen, Laden, Schliessen

async function wbOeffne(id, { zurueck = null } = {}) {
  if (zurueck) wb.zurueck.push(zurueck);
  Object.assign(wb, { id, sel: null, baum: null, flach: null, detail: null, offen: new Set(), filter: "" });
  if ($("#wb-suche")) $("#wb-suche").value = "";
  if (!wb.materialien.length) api("/api/materialien").then((m) => { wb.materialien = m; }).catch(() => {});
  const el = $("#werkbank");
  if (!el.dataset.gebaut) wbGeruest();
  el.hidden = false;
  document.body.classList.add("wb-an");
  await wbLaden();
  ladeProjekteLeiste();
}

function wbSchliessen() {
  if (wb.zurueck.length) { return wbOeffne(wb.zurueck.pop()); }      // aus einem Baustein zurück ins Projekt
  wb.id = null;
  $("#werkbank").hidden = true;
  document.body.classList.remove("wb-an");
  ladeProjekteLeiste();
  if (zustand.baugruppe) ladeBaugruppe();
  ladeBaugruppenLeiste();
}

async function wbLaden({ inspektor = true } = {}) {
  const id = wb.id;
  if (!id) return;
  try {
    const [baum, flach, detail] = await Promise.all([api(`${wbBasis(id)}/${id}/baum`), api(`${wbBasis(id)}/${id}/stueckliste`), api(`${wbBasis(id)}/${id}`)]);
    if (wb.id !== id) return;
    Object.assign(wb, { baum, flach, detail });
  } catch (e) {
    toast(e.message);
    wb.zurueck = [];
    return wbSchliessen();
  }
  wbIndex();
  if (wb.sel && !wb.index[wb.sel.p]) wb.sel = null;          // die Position gibt es nicht mehr
  wbZeichne(inspektor);
  wbKatListe();
}

// Jede Zeile des Baums unter ihrem Pfad merken: Auswahl und Bearbeiten finden die Position darüber wieder.
function wbIndex() {
  wb.index = {};
  const gehe = (positionen, container, pfad) => {
    for (const e of positionen) {
      const p = [...pfad, e.ref].join("|");
      wb.index[p] = { e, container, p, pfad: [...pfad, e.ref] };
      if (e.art === "baugruppe") gehe(e.positionen || [], e.id, [...pfad, e.ref]);
    }
  };
  gehe(wb.baum.positionen, wb.id, []);
}

// ---------------------------------------------------------------- Zeichnen

function wbGeruest() {
  const el = $("#werkbank");
  el.dataset.gebaut = "1";
  el.innerHTML = `
    <div class="wb-kopf" id="wb-kopf"></div>
    <div class="wb-raum" id="wb-raum" style="--wb-l:${Number(localStorageLesen("wb-l")) || 300}px;--wb-r:${Number(localStorageLesen("wb-r")) || 330}px">
      <section class="wb-spalte"><div class="wb-titel"><b>AUFBAU</b><span class="wb-luecke"></span>
        <button class="wb-kn" id="wb-auf" title="Alles aufklappen">⊞</button><button class="wb-kn" id="wb-zu" title="Alles zuklappen">⊟</button></div>
        <div class="wb-filter"><input id="wb-suche" placeholder="Im Baum suchen …" autocomplete="off"></div>
        <div class="wb-baum" id="wb-baum" tabindex="0"></div>
        <div class="wb-griff-h" id="wb-griff-h"></div>
        <div class="wb-schublade" id="wb-schublade" style="--wb-sh:${Number(localStorageLesen("wb-sh")) || 240}px"></div></section>
      <div class="wb-griff" data-g="l"></div>
      <section class="wb-spalte wb-mitte" id="wb-mitte"></section>
      <div class="wb-griff" data-g="r"></div>
      <section class="wb-spalte"><div class="wb-titel"><b>EIGENSCHAFTEN</b></div><div class="wb-insp" id="wb-insp"></div></section>
    </div>
    <div class="wb-stat" id="wb-stat"></div>`;
  const gh = $("#wb-griff-h");           // Höhe der Schublade ziehen
  gh.addEventListener("mousedown", (e) => {
    e.preventDefault();
    gh.classList.add("zieht");
    const sch = $("#wb-schublade"), start = e.clientY, h0 = sch.getBoundingClientRect().height;
    const bewegt = (m) => sch.style.setProperty("--wb-sh", Math.max(120, Math.min(innerHeight - 260, h0 - (m.clientY - start))) + "px");
    const los = () => {
      gh.classList.remove("zieht");
      removeEventListener("mousemove", bewegt);
      removeEventListener("mouseup", los);
      localStorageSchreiben("wb-sh", parseInt(getComputedStyle(sch).getPropertyValue("--wb-sh")));
    };
    addEventListener("mousemove", bewegt);
    addEventListener("mouseup", los);
  });
  wbKatGeruest();
  el.querySelectorAll(".wb-griff").forEach((g) => g.addEventListener("mousedown", (e) => {
    e.preventDefault();
    g.classList.add("zieht");
    const raum = $("#wb-raum"), start = e.clientX, was = g.dataset.g;
    const l = parseInt(getComputedStyle(raum).getPropertyValue("--wb-l")), r = parseInt(getComputedStyle(raum).getPropertyValue("--wb-r"));
    const bewegt = (m) => {
      const d = m.clientX - start;
      if (was === "l") raum.style.setProperty("--wb-l", Math.max(200, Math.min(640, l + d)) + "px");
      else raum.style.setProperty("--wb-r", Math.max(260, Math.min(600, r - d)) + "px");
    };
    const los = () => {
      g.classList.remove("zieht");
      removeEventListener("mousemove", bewegt);
      removeEventListener("mouseup", los);
      localStorageSchreiben("wb-l", parseInt(getComputedStyle(raum).getPropertyValue("--wb-l")));
      localStorageSchreiben("wb-r", parseInt(getComputedStyle(raum).getPropertyValue("--wb-r")));
    };
    addEventListener("mousemove", bewegt);
    addEventListener("mouseup", los);
  }));
}

function wbZeichne(inspektor = true) {
  wbKopf();
  wbBaum();
  wbMitte();
  wbStatus();
  if (inspektor) wbInspektor();
}

function wbKopf() {
  const b = wb.baum, v = wb.detail?.verlauf || {};
  const stack = wb.zurueck.length;
  abgleichen($("#wb-kopf"), `
    <button class="wb-kn" data-wb="schliessen" title="${stack ? "Zurück zum Projekt" : "Zurück in den Katalog"}">← ${stack ? "Zurück" : "Katalog"}</button>
    <span class="wb-trenner"></span>
    <span class="wb-name">${WB_ICON[b.art === "projekt" ? "projekt" : "baugruppe"]} ${esc(b.name)}
      <span class="wb-marke">${b.art === "projekt" ? "Projekt" : "Baustein"}</span>${b.status ? `<span class="wb-marke">${esc(b.status)}</span>` : ""}</span>
    <span class="wb-trenner"></span>
    <button class="wb-kn" data-wb="rueck" ${v.zurueck ? "" : "disabled"} title="${v.zurueck ? "Rückgängig: " + esc(v.zurueck) + " (Strg+Z)" : "Nichts zum Rückgängigmachen"}">↶</button>
    <button class="wb-kn" data-wb="wieder" ${v.vor ? "" : "disabled"} title="${v.vor ? "Wiederholen: " + esc(v.vor) + " (Strg+Umschalt+Z)" : "Nichts zu wiederholen"}">↷</button>
    <span class="wb-trenner"></span>
    <button class="wb-kn rand" data-wb="hinzu" title="Katalog-Schublade öffnen und suchen (Strg+I)">＋ Teil hinzufügen</button>
    <span class="wb-luecke"></span>
    <span class="wb-leise">${v.schritte ? `${v.schritte} ${v.schritte === 1 ? "Schritt" : "Schritte"}` : ""}</span>`);
}

function wbZeile(e, container, tief, pfad) {
  const p = [...pfad, e.ref].join("|");
  const baug = e.art === "baugruppe", auf = wb.offen.has(p);
  const unter = baug ? (e.positionen || []).length : 0;
  const tags = [e.material ? `<span class="wb-tag">${esc(e.material)}</span>` : "", e.entwurf ? '<span class="wb-tag" title="Entwurf">✎</span>' : "",
    e.fehlt ? '<span class="wb-tag warn" title="Datei fehlt">!</span>' : ""].join("");
  return `<div class="wb-z ${wb.sel?.p === p ? "sel" : ""}" data-p="${esc(p)}" style="padding-left:${8 + tief * 16}px">
    <span class="wb-pf" data-t="${esc(p)}">${baug ? (auf ? "▾" : "▸") : ""}</span>${WB_ICON[e.art] || ""}
    <span class="wb-n" title="${esc(e.name)}">${esc(e.name)}${e.art === "modell" && e.format ? `<span class="wb-endung">${esc(endung[e.format] || "")}</span>` : ""}</span>
    ${tags}${baug ? `<span class="wb-sub">${unter}</span>` : ""}<span class="wb-m">${e.menge}×</span></div>`;
}

// Suche im Baum: eine Zeile bleibt, wenn sie selbst passt oder etwas darunter; Zweige mit Treffern klappen dabei auf.
function wbTrifft(e) {
  const q = wb.filter.trim().toLowerCase();
  if (!q) return true;
  return e.name.toLowerCase().includes(q) || (e.art === "baugruppe" && (e.positionen || []).some(wbTrifft));
}

function wbZeilen(positionen, container, tief, pfad, aus) {
  for (const e of positionen) {
    if (!wbTrifft(e)) continue;
    aus.push(wbZeile(e, container, tief, pfad));
    const p = [...pfad, e.ref].join("|");
    if (e.art === "baugruppe" && (wb.offen.has(p) || wb.filter.trim())) wbZeilen(e.positionen || [], e.id, tief + 1, [...pfad, e.ref], aus);
  }
}

function wbBaum() {
  const b = wb.baum, aus = [];
  aus.push(`<div class="wb-z ${wb.sel ? "" : "sel"}" data-p="" style="padding-left:8px"><span class="wb-pf"></span>${WB_ICON[b.art === "projekt" ? "projekt" : "baugruppe"]}
    <span class="wb-n"><b>${esc(b.name)}</b></span><span class="wb-sub">${Object.keys(wb.index).length} Positionen</span></div>`);
  wbZeilen(b.positionen, wb.id, 1, [], aus);
  if (!b.positionen.length) aus.push(`<div class="wb-leer">Noch leer.<br>Mit „＋ Teil hinzufügen“ Druckteile, Kaufteile oder Baugruppen einfügen.</div>`);
  abgleichen($("#wb-baum"), aus.join(""));
}

function wbMitte() {
  const f = wb.flach || { druck: [], kauf: [], eigene: [] };
  const reiter = [["stueckliste", "Stückliste", f.druck.length + f.kauf.length + f.eigene.length || ""], ["fertigung", "Fertigung", ""]];
  abgleichen($("#wb-mitte"), `
    <div class="wb-reiter">${reiter.map(([k, t, n]) => `<button data-wr-tab="${k}" class="${wb.reiter === k ? "an" : ""}">${t}${n ? `<span class="zahl">${n}</span>` : ""}</button>`).join("")}</div>
    <div class="wb-flaeche">${wb.reiter === "fertigung" ? wbFertigung() : wbStueckliste(f)}</div>`);
}

function wbFertigung() {
  return `<div class="wb-leer">Fertigung: die Druckplatten kommen als Nächstes.</div>`;
}

// Die Stückliste über alle Ebenen, flach: Druckteile je einmal mit Gesamtmenge, darunter die Kaufteile nach Kategorie. Eine Zeile anklicken
// wählt das erste Vorkommen im Baum.
function wbStueckliste(f) {
  const gewaehlt = wb.sel ? wb.index[wb.sel.p]?.e.ref : null;
  const s = f.summen || {};
  const druck = f.druck.map((d) => `<tr class="zl ${gewaehlt === d.ref ? "sel" : ""}" data-bz="${esc(d.ref)}">
      <td>${WB_ICON.modell}</td><td class="n">${esc(d.name)}${esc(endung[d.format] || "")}${d.entwurf ? ' <span class="wb-leise">✎</span>' : ""}${d.fehlt ? ' <span class="wb-tag warn">Datei fehlt</span>' : ""}</td>
      <td class="re">${d.menge}×</td><td>${esc(d.materialien.map((m) => m.material).join(" · "))}</td>
      <td class="re">${d.ohne_daten ? "–" : zahl(d.gewicht_g, 1) + " g" + (d.gewicht_geschaetzt ? " *" : "")}</td><td class="re">${d.zeit_s ? dauer(d.zeit_s) : "–"}</td></tr>`).join("");
  const kategorien = [...new Set(f.kauf.map((k) => k.kategorie || ""))];
  const kauf = kategorien.map((kat) => {
    const l = f.kauf.filter((k) => (k.kategorie || "") === kat);
    return `<tr class="gr"><td></td><td colspan="2">${esc(kat || "Ohne Kategorie")}</td><td class="re">${l.reduce((a, k) => a + k.menge, 0)}×</td><td></td></tr>`
      + l.map((k) => `<tr class="zl ${gewaehlt === k.ref ? "sel" : ""}" data-bz="${esc(k.ref)}"><td>${WB_ICON.kaufteil}</td><td class="n">${esc(k.name)}</td>
        <td class="wb-leise">${esc(k.norm || "")}</td><td class="re">${k.menge}×</td>
        <td>${/^https?:\/\//i.test(k.link || "") ? `<a href="${esc(k.link)}" target="_blank" rel="noopener noreferrer">${esc(new URL(k.link).hostname.replace(/^www\./, ""))} ↗</a>` : '<span class="wb-leise">–</span>'}</td></tr>`).join("");
  }).join("");
  const eigene = f.eigene.map((e) => `<tr class="zl ${gewaehlt === e.ref ? "sel" : ""}" data-bz="${esc(e.ref)}"><td>${WB_ICON.eigen}</td><td class="n">${esc(e.name)}</td><td class="wb-leise">${esc(e.art)}</td>
      <td class="re">${e.menge}×</td><td></td></tr>`).join("");
  if (!f.druck.length && !f.kauf.length && !f.eigene.length) return `<div class="wb-leer">Noch nichts in der Stückliste.<br>Mit „＋ Teil hinzufügen“ Druckteile, Kaufteile oder Baugruppen einfügen.</div>`;
  return `${f.druck.length ? `<div class="wb-ab">DRUCKTEILE · ${f.druck.length} ${f.druck.length === 1 ? "Sorte" : "Sorten"}, ${s.druckteile ?? 0} Stück</div>
    <table class="wb-tab"><thead><tr><th></th><th>Benennung</th><th class="re">Menge</th><th>Material</th><th class="re">Gewicht</th><th class="re">Zeit</th></tr></thead><tbody>${druck}
      <tr class="gr"><td></td><td>Summe</td><td class="re">${s.druckteile ?? 0}×</td><td></td><td class="re">${zahl(s.gewicht_g, 1)} g${s.gewicht_geschaetzt ? " *" : ""}</td><td class="re">${s.zeit_s ? dauer(s.zeit_s) : "–"}</td></tr></tbody></table>` : ""}
    ${f.kauf.length ? `<div class="wb-ab">ZUKAUFTEILE · ${f.kauf.length} ${f.kauf.length === 1 ? "Sorte" : "Sorten"}</div>
    <table class="wb-tab"><thead><tr><th></th><th>Benennung</th><th>Norm</th><th class="re">Menge</th><th>Bezugsquelle</th></tr></thead><tbody>${kauf}</tbody></table>` : ""}
    ${f.eigene.length ? `<div class="wb-ab">EIGENE KOMPONENTEN</div><table class="wb-tab"><thead><tr><th></th><th>Benennung</th><th>Art</th><th class="re">Menge</th><th></th></tr></thead><tbody>${eigene}</tbody></table>` : ""}
    <div class="wb-leise" style="padding-top:6px">Summen über alle Ebenen. * geschätzt (ohne Slicer-Daten). Zeile anklicken wählt das Teil im Baum.</div>`;
}

function wbStatus() {
  const s = wb.flach?.summen || {}, sel = wb.sel ? wb.index[wb.sel.p] : null;
  abgleichen($("#wb-stat"), `<span>Druckteile <b>${s.druckteile ?? "–"}</b></span><span>Zukaufteile <b>${s.kaufteile ?? "–"}</b></span>
    <span>Gewicht <b>${s.gewicht_g != null ? zahl(s.gewicht_g, 0) + " g" + (s.gewicht_geschaetzt ? " *" : "") : "–"}</b></span><span>Druckzeit <b>${s.zeit_s ? dauer(s.zeit_s) : "–"}</b></span>
    <span class="wb-luecke"></span><span>Auswahl: <b>${sel ? esc(sel.pfad.map((r, i) => wb.index[sel.pfad.slice(0, i + 1).join("|")]?.e.name || "").join(" › ")) : "–"}</b></span>`);
}

// Aus der Stückliste: das erste Vorkommen im Baum wählen und seine Äste aufklappen.
function wbWaehleRef(ref) {
  const f = Object.values(wb.index).find((x) => x.e.ref === ref);
  if (!f) return;
  for (let i = 1; i < f.pfad.length; i++) wb.offen.add(f.pfad.slice(0, i).join("|"));
  wb.sel = { p: f.p };
  wbBaum(); wbMitte(); wbStatus(); wbInspektor();
}

// ---------------------------------------------------------------- Inspektor

function wbFeld(l, inner) { return `<div class="wb-f"><label>${l}</label>${inner}</div>`; }

function wbInspektor() {
  const el = $("#wb-insp");
  const sel = wb.sel ? wb.index[wb.sel.p] : null;
  if (!sel) return wbInspektorWurzel(el);
  const e = sel.e, cont = sel.container, kopfName = esc(e.name);
  const bild = e.art === "modell" ? bildUrl(e) : null;
  let h = `<div class="wb-ititel">${bild ? `<img class="wb-thumb" src="${bild}" alt="">` : ""}<div><b>${WB_ICON[e.art] || ""} ${kopfName}</b><div class="wb-leise">${wbArtName[e.art]} · in ${esc(wbName(cont))}</div></div></div>`;
  h += `<div class="wb-gruppe">POSITION</div>`;
  h += wbFeld("Menge", `<div class="wb-stepper"><button data-wm="-1">−</button><input data-wf="menge" value="${e.menge}" inputmode="numeric"><button data-wm="1">＋</button></div>`);
  h += `<div class="wb-leise" style="padding:0 10px 4px">Gesamt ab oberster Ebene: <b>${e.gesamt}×</b></div>`;
  if (e.art === "modell") {
    h += `<div class="wb-gruppe">DRUCKVORGABE</div>`;
    h += wbFeld("Material", `<input data-wf="material" list="wb-mat" value="${esc(e.material || "")}" placeholder="${esc(e.material_wirksam || "")}${e.material_angenommen ? " (Standard)" : ""}"><datalist id="wb-mat">${wb.materialien.map((m) => `<option value="${esc(m)}">`).join("")}</datalist>`);
    h += wbFeld("Farbe", `<div class="wb-farbe"><input type="color" data-wf="farbe" value="${/^#[0-9a-f]{6}$/i.test(e.farbe || "") ? e.farbe : "#888888"}"><button class="wb-kn" data-wf-leer="farbe" title="Farbe wegnehmen">×</button><span class="wb-leise">${e.farbe ? esc(e.farbe) : "keine Vorgabe"}</span></div>`);
    h += wbFeld("Füllung", `<div class="wb-einh"><input data-wf="infill" value="${e.infill ?? ""}" placeholder="–"><span>%</span></div>`);
    h += wbFeld("Wandlinien", `<div class="wb-einh"><input data-wf="waende" value="${e.waende ?? ""}" placeholder="–"><span>×</span></div>`);
    h += wbFeld("Schichthöhe", `<div class="wb-einh"><input data-wf="schicht" value="${e.schicht ?? ""}" placeholder="–"><span>mm</span></div>`);
    h += `<div class="wb-leise" style="padding:0 10px 4px">Eine Vorgabe. Gedruckt wird, was auf der Platte steht.</div>`;
  }
  if (e.art !== "baugruppe") h += wbFeld("Notiz", `<textarea data-wf="notiz" rows="2" placeholder="z. B. Stützen nur auf dem Druckbett">${esc(e.notiz || "")}</textarea>`);
  else h += wbFeld("Notiz", `<textarea data-wf="notiz" rows="2">${esc(e.notiz || "")}</textarea>`);
  if (e.art === "kaufteil") {
    const k = (wb.flach?.kauf || []).find((x) => x.id === e.id) || {};
    h += `<div class="wb-gruppe">BEZUG · gilt überall</div>`;
    h += wbFeld("Link", `<input data-wk="link" value="${esc(k.link || "")}" placeholder="https://…">`);
    if (/^https?:\/\//i.test(k.link || "")) h += wbFeld("", `<a class="wb-link" href="${esc(k.link)}" target="_blank" rel="noopener noreferrer">${esc(new URL(k.link).hostname.replace(/^www\./, ""))} ↗</a>`);
    h += wbFeld("Artikelnr.", `<input data-wk="artikelnr" value="${esc(k.artikelnr || "")}">`);
    h += wbFeld("Hinweis", `<textarea data-wk="hinweis" rows="2" placeholder="z. B. mit Schraubensicherung">${esc(k.hinweis || "")}</textarea>`);
  }
  h += `<div class="wb-aktionen">`;
  if (e.art === "baugruppe") h += `<button class="wb-kn rand" data-wb="baustein" data-id="${esc(e.id)}">Als Baustein öffnen</button>`;
  h += `<button class="wb-kn gefahr" data-wb="weg">Aus ${esc(wbName(cont))} entfernen</button></div>`;
  h += `<div class="wb-gruppe">WO VERBAUT · IM GANZEN KATALOG</div><div class="wb-verw" id="wb-verw"><span class="wb-leise">…</span></div>`;
  el.innerHTML = h;
  wbVerwendung(e.ref);
}

function wbName(id) {
  if (id === wb.id) return wb.baum.name;
  const f = Object.values(wb.index).find((x) => x.e.art === "baugruppe" && x.e.id === id);
  return f ? f.e.name : id;
}

function wbInspektorWurzel(el) {
  const b = wb.baum, d = wb.detail, projekt = b.art === "projekt";
  let h = `<div class="wb-ititel"><b>${WB_ICON[projekt ? "projekt" : "baugruppe"]} ${esc(b.name)}</b><div class="wb-leise">${projekt ? "Projekt" : "Baugruppe (wiederverwendbarer Baustein)"}</div></div>`;
  h += `<div class="wb-gruppe">${projekt ? "PROJEKT" : "BAUGRUPPE"}</div>`;
  h += wbFeld("Name", `<input data-wr="name" value="${esc(b.name)}">`);
  if (projekt) h += wbFeld("Status", `<input data-wr="status" list="wb-status" value="${esc(b.status || "")}" placeholder="frei wählbar"><datalist id="wb-status"><option value="Entwurf"><option value="In Arbeit"><option value="Fertig"></datalist>`);
  h += wbFeld(projekt ? "Notizen" : "Beschreibung", `<textarea data-wr="beschreibung" rows="4" placeholder="Wofür, welche Version, Besonderheiten …">${esc(d?.beschreibung || "")}</textarea>`);
  h += `<div class="wb-aktionen"><button class="wb-kn gefahr" data-wb="loeschen">${projekt ? "Projekt" : "Baugruppe"} löschen …</button></div>`;
  if (!projekt) h += `<div class="wb-gruppe">WO VERBAUT · IM GANZEN KATALOG</div><div class="wb-verw" id="wb-verw"><span class="wb-leise">…</span></div>`;
  el.innerHTML = h;
  if (!projekt) wbVerwendung(`ASSEMBLY/${wb.id}`);
}

// Wo verbaut: je Verwendung der Weg von oben (Projekt oder oberste Baugruppe) bis zum Teil. Ein Klick öffnet die oberste.
async function wbVerwendung(ref) {
  let wege;
  try { wege = await api(`/api/verwendung?ziel=${encodeURIComponent(ref)}`); } catch { return; }
  const ziel = $("#wb-verw");
  if (!ziel || !wege) return;
  ziel.innerHTML = wege.map((w) => `<a data-wo="${esc(w.weg[0].id)}"><span>${w.weg.map((x) => esc(x.name)).join(" › ")}</span>
    <span class="wb-m">${w.weg.map((x) => x.menge).join(" × ")} = ${w.gesamt}×</span></a>`).join("") || '<span class="wb-leise">In keiner Baugruppe und keinem Projekt.</span>';
}

// ---------------------------------------------------------------- Ändern

async function wbAendern(methode, url, body) {
  try {
    await api(wbMit(url), { method: methode, ...(body ? { body } : {}) });
  } catch (e) {
    toast(e.message);
    return wbLaden();           // der Server hat abgelehnt: die Felder wieder auf den echten Stand
  }
  return wbLaden({ inspektor: false });
}

const wbSelAktuell = () => (wb.sel ? wb.index[wb.sel.p] : null);

async function wbPosition(feld, wert) {
  const s = wbSelAktuell();
  if (!s) return;
  const body = { ref: s.e.ref, [feld]: wert };
  if (feld === "menge") body.menge = Math.max(1, Math.round(Number(wert)) || 1);
  await wbAendern("PATCH", `${wbBasis(s.container)}/${s.container}/positionen`, body);
}

async function wbEntfernen() {
  const s = wbSelAktuell();
  if (!s) return;
  wb.sel = null;
  await wbAendern("DELETE", `${wbBasis(s.container)}/${s.container}/positionen?ref=${encodeURIComponent(s.e.ref)}`);
  wbInspektor();
}

async function wbVerlauf(art) {
  try {
    const { text } = await api(`${wbBasis(wb.id)}/${wb.id}/${art}`, { method: "POST" });
    toast(`${art === "rueckgaengig" ? "Rückgängig" : "Wiederholt"}: ${text}`);
  } catch (e) { return toast(e.message); }
  await wbLaden();
}

// Wohin ein neues Teil kommt: in die gewählte Baugruppe; ist ein anderes Teil gewählt, in dessen Baugruppe; sonst in die Wurzel.
function wbZiel() {
  const s = wbSelAktuell();
  if (!s) return wb.id;
  return s.e.art === "baugruppe" ? s.e.id : s.container;
}

// ---------------------------------------------------------------- Katalog-Schublade
// Teile kommen nicht über ein Fenster hinein, sondern aus dem Katalog im Arbeitsbereich: ziehen (auf eine Baugruppe im Baum oder in die
// Wurzel), Doppelklick, ＋ oder Enter fügen in die gewählte Baugruppe ein. Dichte Zeilen, kein Raster.

function wbKatMengen() {
  const m = {};
  for (const x of Object.values(wb.index)) m[x.e.ref] = (m[x.e.ref] || 0) + x.e.gesamt;
  return m;
}

function wbKatGeruest() {
  const k = wb.kat, el = $("#wb-schublade");
  el.classList.toggle("zu", k.zu);
  el.innerHTML = `<div class="wb-titel wb-sk" data-wk="zu"><span class="wb-pf" style="width:auto">${k.zu ? "▸" : "▾"}</span><b>KATALOG</b><span class="wb-leise">ziehen oder Doppelklick</span></div>
    ${k.zu ? "" : `<div class="wb-ktabs">${[["teile", "Druckteile"], ["kaufteile", "Kaufteile"], ["unter", "Baugruppen"]].map(([t, n]) =>
        `<button data-wk-tab="${t}" class="${k.tab === t ? "an" : ""}">${n}</button>`).join("")}</div>
      <div class="wb-filter"><input id="wb-ksuche" placeholder="Suchen …" autocomplete="off" value="${esc(k.q)}"></div>
      <div class="wb-kat" id="wb-kat" tabindex="0"></div>`}`;
  if (!k.zu) wbKatLaden();
}

async function wbKatLaden() {
  const { tab, q } = wb.kat;
  let zeilen = [], mehr = false;
  try {
    if (tab === "kaufteile") {
      zeilen = (await api(`/api/kaufteile?q=${encodeURIComponent(q)}`)).map((t) => ({ ref: `PURCHASED_PART/${t.id}`, name: t.name, meta: t.norm || t.kategorie || "", symbol: symbolFuer(t.kategorie) }));
    } else if (tab === "unter") {
      zeilen = (await api("/api/baugruppen")).filter((b) => b.id !== wb.id && b.name.toLowerCase().includes(q.toLowerCase()))
        .map((b) => ({ ref: `ASSEMBLY/${b.id}`, name: b.name, meta: `${b.positionen} Pos.`, symbol: "🧩" }));
    } else {
      const alle = await api(`/api/modelle?q=${encodeURIComponent(q)}`);
      mehr = alle.length > 300;
      zeilen = alle.slice(0, 300).map((m) => ({ ref: `MODEL_ASSET/${m.id}`, name: m.name + (endung[m.format] || ""), meta: masse(m.masse), bild: bildUrl(m) }));
    }
  } catch { zeilen = []; }
  if (wb.kat.tab !== tab || wb.kat.q !== q) return;        // inzwischen etwas anderes gesucht
  wb.kat.liste = zeilen;
  wb.kat.mehr = mehr;
  wbKatListe();
}

// Nur die Markierung umschalten: die Liste neu zu zeichnen, während man doppelklickt, verlöre den zweiten Klick.
function wbKatMarkieren(ref) {
  wb.kat.sel = ref;
  document.querySelectorAll("#wb-kat .wb-k").forEach((z) => z.classList.toggle("sel", z.dataset.kref === ref));
}

function wbKatListe() {
  const el = $("#wb-kat");
  if (!el || !wb.baum) return;
  const mengen = wbKatMengen(), k = wb.kat;
  el.innerHTML = k.liste.map((z) => `<div class="wb-k ${k.sel === z.ref ? "sel" : ""}" draggable="true" data-kref="${esc(z.ref)}" title="${esc(z.name)}">
      ${z.bild ? `<img loading="lazy" src="${z.bild}" alt="">` : `<span class="wb-ksym">${z.symbol || WB_ICON.modell}</span>`}
      <span class="wb-n">${esc(z.name)}</span><span class="wb-kmeta">${esc(z.meta || "")}</span>
      <span class="wb-kn2">${mengen[z.ref] ? mengen[z.ref] + "×" : ""}</span><button class="wb-kp" data-kplus="${esc(z.ref)}" title="In ${esc(wbName(wbZiel()))} einfügen">＋</button></div>`).join("")
    + (k.mehr ? `<div class="wb-leise" style="padding:4px 10px">Mehr als 300 Treffer — Suche eingrenzen.</div>` : "")
    || `<div class="wb-leer">Nichts gefunden.</div>`;
}

function wbKatFokus() {
  wb.kat.zu = false;
  localStorageSchreiben("wb-kat-zu", "0");
  wbKatGeruest();
  $("#wb-ksuche")?.focus();
}

// Einfügen: `ziel` ist die Baugruppe oder das Projekt, in das das Teil kommt.
async function wbHinzu(ref, menge = 1, ziel = wbZiel()) {
  try {
    await api(wbMit(`${wbBasis(ziel)}/${ziel}/positionen`), { method: "POST", body: { ref, menge } });
  } catch (e) { return toast(e.message); }
  if (ziel !== wb.id) {                      // die Baugruppe, in die es kam, aufklappen
    const f = Object.values(wb.index).find((x) => x.e.art === "baugruppe" && x.e.id === ziel);
    if (f) wb.offen.add(f.p);
  }
  await wbLaden({ inspektor: false });
  wbKatListe();
}

async function wbLoeschen() {
  const projekt = wbIst("projekt");
  const a = await dialog(`<h2>„${esc(wb.baum.name)}“ löschen?</h2>
    <p>${projekt ? "Das Projekt und seine Druckplatten gehen." : "Die Baugruppe geht."} Modelle, Dateien und Kaufteile bleiben${projekt ? ", auch die Baugruppen darin" : ""}.</p>
    <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Löschen</button></div>`);
  if (a !== "ja") return;
  try { await api(`${wbBasis(wb.id)}/${wb.id}`, { method: "DELETE" }); } catch (e) { return toast(e.message); }
  wb.zurueck = [];
  wbSchliessen();
}

// ---------------------------------------------------------------- Ereignisse

document.addEventListener("click", (e) => {
  const t = e.target;
  if (t.closest("#projekt-neu, #projekt-neu-2")) return neuesProjekt();
  const pr = t.closest("[data-projekt]");
  if (pr) return wbOeffne(pr.dataset.projekt);
  if (!t.closest("#werkbank")) return;
  const aktion = t.closest("[data-wb]")?.dataset.wb;
  if (aktion === "schliessen") return wbSchliessen();
  if (aktion === "rueck") return wbVerlauf("rueckgaengig");
  if (aktion === "wieder") return wbVerlauf("wiederholen");
  if (aktion === "hinzu") return wbKatFokus();
  if (aktion === "weg") return wbEntfernen();
  if (aktion === "loeschen") return wbLoeschen();
  if (aktion === "baustein") return wbOeffne(t.closest("[data-wb]").dataset.id, { zurueck: wb.id });
  if (t.closest("#wb-auf")) { Object.keys(wb.index).forEach((p) => wb.index[p].e.art === "baugruppe" && wb.offen.add(p)); return wbBaum(); }
  if (t.closest("#wb-zu")) { wb.offen = new Set(); return wbBaum(); }
  const wo = t.closest("[data-wo]");
  if (wo) { const id = wo.dataset.wo; return id === wb.id ? null : wbOeffne(id, { zurueck: wb.id }); }
  const pf = t.closest(".wb-pf[data-t]");
  if (pf) { const p = pf.dataset.t; wb.offen.has(p) ? wb.offen.delete(p) : wb.offen.add(p); return wbBaum(); }
  const z = t.closest(".wb-z[data-p]");
  if (z) { wb.sel = z.dataset.p ? { p: z.dataset.p } : null; wbBaum(); wbMitte(); wbStatus(); return wbInspektor(); }
  if (t.closest("[data-wk=zu]")) { wb.kat.zu = !wb.kat.zu; localStorageSchreiben("wb-kat-zu", wb.kat.zu ? "1" : "0"); return wbKatGeruest(); }
  const kt = t.closest("[data-wk-tab]");
  if (kt) { wb.kat.tab = kt.dataset.wkTab; wb.kat.q = ""; wb.kat.sel = null; return wbKatGeruest(); }
  const kp = t.closest("[data-kplus]");
  if (kp) return wbHinzu(kp.dataset.kplus);
  const kz = t.closest(".wb-k[data-kref]");
  if (kz) return wbKatMarkieren(kz.dataset.kref);
  const tab = t.closest("[data-wr-tab]");
  if (tab) { wb.reiter = tab.dataset.wrTab; localStorageSchreiben("wb-reiter", wb.reiter); return wbMitte(); }
  const bz = t.closest("[data-bz]");
  if (bz) return wbWaehleRef(bz.dataset.bz);
  const m = t.closest("[data-wm]");
  if (m) { const s = wbSelAktuell(); return s && wbPosition("menge", s.e.menge + Number(m.dataset.wm)).then(() => wbInspektor()); }
  const leer = t.closest("[data-wf-leer]");
  if (leer) return wbPosition(leer.dataset.wfLeer, "").then(() => wbInspektor());
});

// Eingaben speichern beim Verlassen des Feldes (change); ein abgelehnter Wert stellt das Feld wieder auf den echten Stand.
let wbKatZeit;
document.addEventListener("input", (e) => {
  if (e.target.id === "wb-suche") { wb.filter = e.target.value; wbBaum(); }
  if (e.target.id === "wb-ksuche") { wb.kat.q = e.target.value; clearTimeout(wbKatZeit); wbKatZeit = setTimeout(wbKatLaden, 150); }
});

document.addEventListener("dblclick", (e) => {
  const kz = e.target.closest?.(".wb-k[data-kref]");
  if (kz && e.target.closest("#werkbank")) wbHinzu(kz.dataset.kref);
});

// Ziehen: aus der Schublade auf eine Baugruppe im Baum (dort hinein), auf ein anderes Teil (in dessen Baugruppe) oder in die Wurzel.
function wbZielVonZeile(zeile) {
  if (!zeile || !zeile.dataset.p) return wb.id;
  const x = wb.index[zeile.dataset.p];
  return x.e.art === "baugruppe" ? x.e.id : x.container;
}
const wbDropWeg = () => document.querySelectorAll(".wb-drop").forEach((x) => x.classList.remove("wb-drop"));
document.addEventListener("dragstart", (e) => {
  const k = e.target.closest?.(".wb-k[data-kref]");
  if (!k) return;
  wb.zug = k.dataset.kref;
  e.dataTransfer.setData("text/plain", wb.zug);
  e.dataTransfer.effectAllowed = "copy";
});
document.addEventListener("dragend", () => { wb.zug = null; wbDropWeg(); });
document.addEventListener("dragover", (e) => {
  if (!wb.zug || !e.target.closest?.("#wb-baum")) return;
  e.preventDefault();
  wbDropWeg();
  (e.target.closest(".wb-z") || $("#wb-baum .wb-z")).classList.add("wb-drop");       // ausserhalb der Zeilen: die Wurzel
});
document.addEventListener("drop", (e) => {
  if (!wb.zug || !e.target.closest?.("#wb-baum")) return;
  e.preventDefault();
  const ref = wb.zug, ziel = wbZielVonZeile(e.target.closest(".wb-z"));
  wb.zug = null;
  wbDropWeg();
  wbHinzu(ref, 1, ziel);
});

// Tastatur in der Schublade: Pfeile wählen, Enter fügt ein.
document.addEventListener("keydown", (e) => {
  if (!wb.id || $("#werkbank").hidden || document.querySelector("dialog[open]")) return;
  const inKat = e.target.closest?.("#wb-kat, #wb-ksuche");
  if ((e.ctrlKey || e.metaKey) && !e.altKey && e.key.toLowerCase() === "i") { e.preventDefault(); return wbKatFokus(); }
  if (!inKat || !["ArrowDown", "ArrowUp", "Enter"].includes(e.key)) return;
  const refs = wb.kat.liste.map((z) => z.ref);
  const i = refs.indexOf(wb.kat.sel);
  if (e.key === "Enter") { e.preventDefault(); return wb.kat.sel && wbHinzu(wb.kat.sel); }
  e.preventDefault();
  wbKatMarkieren(refs[Math.max(0, Math.min(refs.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)))] || null);
  document.querySelector(".wb-k.sel")?.scrollIntoView({ block: "nearest" });
});

document.addEventListener("change", (e) => {
  if (e.target.id === "ein-labor") return ladeProjekteLeiste();
  if (!e.target.closest?.("#werkbank")) return;
  const i = e.target;
  if (i.dataset.wf) return wbPosition(i.dataset.wf, i.value);
  if (i.dataset.wr) {
    // Ein neuer Name steht auch in der Überschrift des Inspektors; bei den anderen Feldern bleibt der Fokus, wo er ist.
    const name = i.dataset.wr === "name";
    return wbAendern("PATCH", `${wbBasis(wb.id)}/${wb.id}`, { [i.dataset.wr]: i.value }).then(() => { if (name) wbInspektor(); });
  }
  if (i.dataset.wk) {
    const s = wbSelAktuell();
    if (s) wbAendern("PATCH", `/api/kaufteile/${encodeURIComponent(s.e.id)}`, { [i.dataset.wk]: i.value });
  }
});

document.addEventListener("keydown", (e) => {
  if (!wb.id || $("#werkbank").hidden || document.querySelector("dialog[open]")) return;
  const tippt = e.target.closest?.("input, textarea, select");
  if ((e.ctrlKey || e.metaKey) && !e.altKey && e.key.toLowerCase() === "z" && !tippt) { e.preventDefault(); return wbVerlauf(e.shiftKey ? "wiederholen" : "rueckgaengig"); }
  if (tippt) return;
  if (e.key === "Escape") return wbSchliessen();
  if ((e.key === "Delete" || e.key === "Backspace") && wb.sel && !e.target.closest?.("#wb-kat")) { e.preventDefault(); return wbEntfernen(); }
  if (["ArrowDown", "ArrowUp", "ArrowRight", "ArrowLeft"].includes(e.key)) {
    const zeilen = [...document.querySelectorAll("#wb-baum .wb-z")];
    const i = zeilen.findIndex((z) => z.classList.contains("sel"));
    const s = wbSelAktuell();
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      const n = zeilen[i + (e.key === "ArrowDown" ? 1 : -1)];
      if (n) { wb.sel = n.dataset.p ? { p: n.dataset.p } : null; wbBaum(); wbMitte(); wbStatus(); wbInspektor(); }
    } else if (s && s.e.art === "baugruppe") {
      if (e.key === "ArrowRight") { wb.offen.add(s.p); wbBaum(); }
      else if (wb.offen.has(s.p)) { wb.offen.delete(s.p); wbBaum(); }
    }
    e.preventDefault();
  }
});

ladeProjekteLeiste().catch(() => {});
