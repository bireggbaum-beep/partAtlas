// Zuordnen-Fenster: ein Muster für Tag, Material, Sammlung und Baugruppe — für viele Modelle auf einmal.
//
// Vorher vier verschiedene Wege für dieselbe Aufgabe (Textfeld, Dialog mit Chips, Dialog mit Auswahlliste, Auswahlliste in der Leiste).
// Jetzt: ein Fenster direkt am Knopf, oben ein Suchfeld, darunter was es gibt — mit dem Stand („bei 2 von 5“). Ein Klick fügt allen
// Gewählten hinzu, das Fenster bleibt offen (mehrere Tags nacheinander), der Stand der Zeile folgt sofort. Tippt man etwas, das es nicht
// gibt, bietet die erste Zeile an, es neu anzulegen. Nur Hinzufügen; Entfernen geht je Modell im Inspektor.

const ZUORDNEN_ARTEN = {
  tag:       { symbol: "＃", titel: "Tag",       suche: "Tag suchen oder neu anlegen …",       neu: "Neuer Tag",       zeile: (o) => "#" + o.name },
  material:  { symbol: "◍", titel: "Material",  suche: "Material suchen oder neu anlegen …",  neu: "Neues Material",  zeile: (o) => o.name },
  sammlung:  { symbol: "▤", titel: "Sammlung",  suche: "Sammlung suchen oder neu anlegen …",  neu: "Neue Sammlung",   zeile: (o) => o.name },
  baugruppe: { symbol: "🧩", titel: "Baugruppe", suche: "Baugruppe suchen oder neu anlegen …", neu: "Neue Baugruppe",  zeile: (o) => o.name },
};
const zw = { art: null, modelle: [], daten: null, aktiv: 0, anker: null, meldung: "", beschaeftigt: false };
const zeiger = { x: 0, y: 0 };
document.addEventListener("pointerdown", (e) => { zeiger.x = e.clientX; zeiger.y = e.clientY; }, true);

function zuordnenOffen() { return !$("#zuordnen").hidden; }

function zuordnenSchliessen(fokus = true) {
  if (!zuordnenOffen()) return;
  $("#zuordnen").hidden = true;
  const anker = zw.anker;
  Object.assign(zw, { art: null, daten: null, meldung: "", anker: null });
  if (fokus && anker instanceof Element && anker.isConnected) anker.focus();
}

// `anker`: der Knopf, an dem das Fenster hängt; ohne ihn (Rechtsklick-Menü) öffnet es dort, wo zuletzt geklickt wurde.
async function zuordnenOeffnen(art, modelle, anker) {
  if (!modelle.length) return;
  if (zuordnenOffen() && zw.art === art && anker && zw.anker === anker) return zuordnenSchliessen();
  zuordnenSchliessen(false);
  const k = ZUORDNEN_ARTEN[art];
  Object.assign(zw, { art, modelle: [...modelle], daten: null, aktiv: 0, anker: anker || null, meldung: "" });
  const el = $("#zuordnen");
  el.innerHTML = `<div class="zw-kopf"><span class="zw-titel">${k.symbol} ${k.titel} hinzufügen</span>
      <span class="zw-fuer">für ${modelle.length === 1 ? "1 Modell" : modelle.length + " Modelle"}</span></div>
    <input class="zw-suche" type="text" autocomplete="off" spellcheck="false" placeholder="${esc(k.suche)}" aria-label="${esc(k.suche)}">
    <div class="zw-liste" role="listbox"></div>
    <div class="zw-fuss"><span class="zw-status" aria-live="polite"></span><span class="zw-hinweis">↑↓ wählen · Enter · Esc</span></div>`;
  el.hidden = false;
  zuordnenPlatzieren(anker);
  $("#zuordnen .zw-suche").focus();
  await zuordnenLaden();
}

function zuordnenPlatzieren(anker) {
  const el = $("#zuordnen"), breite = el.offsetWidth;
  const r = anker instanceof Element ? anker.getBoundingClientRect() : { left: zeiger.x, right: zeiger.x, top: zeiger.y, bottom: zeiger.y };
  const links = Math.max(8, Math.min(r.left, innerWidth - breite - 8));
  // Von der Leiste aus gemessen, nicht vom Knopf: sonst läge das Fenster über ihrer Kopfzeile („4 ausgewählt“).
  const huelle = anker instanceof Element ? anker.closest("#stapel") : null;
  if (huelle) r.top = huelle.getBoundingClientRect().top;
  // Über dem Knopf, nach oben wachsend (die Leiste sitzt unten): so verdeckt das Fenster die Leiste nie, auch wenn die Liste erst
  // nachlädt und höher wird. Ist oben kein Platz, darunter.
  if (r.top > 260) Object.assign(el.style, { left: links + "px", top: "auto", bottom: innerHeight - r.top + 8 + "px", maxHeight: Math.min(440, r.top - 16) + "px" });
  else Object.assign(el.style, { left: links + "px", bottom: "auto", top: r.bottom + 8 + "px", maxHeight: Math.max(200, innerHeight - r.bottom - 16) + "px" });
}

async function zuordnenLaden() {
  const art = zw.art;
  try {
    const d = await api("/api/stapel/optionen", { method: "POST", body: { art, modelle: zw.modelle } });
    if (zw.art !== art) return;                      // inzwischen geschlossen oder gewechselt
    zw.daten = d;
  } catch (e) { toast(e.message); return zuordnenSchliessen(); }
  zuordnenZeichnen(true);
}

// Die Zeilen für den aktuellen Suchtext: Treffer, davor ggf. „neu anlegen“.
function zuordnenZeilen() {
  const q = $("#zuordnen .zw-suche").value.trim(), ql = q.toLowerCase();
  const alle = zw.daten ? zw.daten.optionen : [];
  const treffer = alle.filter((o) => !ql || o.name.toLowerCase().includes(ql))
    .sort((a, b) => (b.name.toLowerCase().startsWith(ql) - a.name.toLowerCase().startsWith(ql)));
  const zeilen = treffer.map((o) => ({ typ: "opt", o }));
  // „Neu anlegen“ steht hinter den Treffern: wer „kue“ tippt und Enter drückt, soll „#kuehlung“ bekommen, keinen neuen Tag „kue“.
  if (q && !alle.some((o) => o.name.toLowerCase() === ql)) zeilen.push({ typ: "neu", q });
  return zeilen;
}

const zuordnenFertig = (z) => z.typ === "opt" && zw.daten && z.o.bei >= zw.daten.n;

function zuordnenZeichnen(neuBestimmen = false) {
  if (!zuordnenOffen() || !zw.daten) return;
  const zeilen = zuordnenZeilen();
  if (neuBestimmen || zw.aktiv >= zeilen.length) {
    // Vorausgewählt wird der erste Treffer, der noch etwas bewirkt. „Neu anlegen“ nur, wenn es gar keinen Treffer gibt — wer „stap“ tippt und
    // Enter drückt, soll keinen Tag „stap“ anlegen, auch wenn „#stapel“ schon bei allen steht.
    const offen = zeilen.findIndex((z) => z.typ === "opt" && !zuordnenFertig(z));
    zw.aktiv = offen >= 0 ? offen : zeilen.some((z) => z.typ === "opt") ? -1 : zeilen.length ? 0 : -1;
  }
  const n = zw.daten.n, k = ZUORDNEN_ARTEN[zw.art];
  const stand = (o) => (o.bei >= n ? `<span class="zw-stand voll" title="Schon bei ${n === 1 ? "diesem Modell" : "allen " + n}">✓${n > 1 ? " alle" : ""}</span>`
    : o.bei ? `<span class="zw-stand teil" title="Schon bei ${o.bei} von ${n}">${o.bei} von ${n}</span>` : "");
  $("#zuordnen .zw-liste").innerHTML = zeilen.map((z, i) => z.typ === "neu"
    ? `<button type="button" class="zw-zeile neu ${i === zw.aktiv ? "aktiv" : ""}" role="option" data-zw-neu="1" data-zw-i="${i}">
        <span class="zw-plus">＋</span><span class="zw-name">${k.neu} „${esc(z.q)}“ anlegen</span></button>`
    : `<button type="button" class="zw-zeile ${i === zw.aktiv ? "aktiv" : ""} ${zuordnenFertig(z) ? "fertig" : ""}" role="option"
        aria-disabled="${zuordnenFertig(z)}" data-zw-id="${esc(z.o.id)}" data-zw-i="${i}">
        <span class="zw-name">${esc(k.zeile(z.o))}</span>${stand(z.o)}</button>`).join("")
    || `<div class="zw-leer">${zw.daten.optionen.length ? "Nichts gefunden." : "Noch nichts vorhanden — tippe einen Namen, um das erste anzulegen."}</div>`;
  $("#zuordnen .zw-status").textContent = zw.meldung;
  $("#zuordnen .zw-liste .aktiv")?.scrollIntoView({ block: "nearest" });
}

async function zuordnenAnwenden(zeile) {
  if (zw.beschaeftigt || !zeile || zuordnenFertig(zeile)) return;
  zw.beschaeftigt = true;
  const body = { art: zw.art, modelle: zw.modelle };
  if (zeile.typ === "neu") body.neu = zeile.q; else body.ziel = zeile.o.id;
  try {
    const r = await api("/api/stapel/zuordnen", { method: "POST", body });
    const teile = [];
    if (r.neu || zeile.typ === "neu") teile.push(`„${r.name}“ angelegt`);
    teile.push(`${r.hinzugefuegt} hinzugefügt`);
    if (r.schon) teile.push(`${r.schon} schon dabei`);
    zw.meldung = teile.join(" · ");
    $("#zuordnen .zw-suche").value = "";
    await zuordnenLaden();
    $("#zuordnen .zw-suche").focus();
  } catch (e) { zw.meldung = e.message; zuordnenZeichnen(); }
  finally { zw.beschaeftigt = false; }
}

document.addEventListener("input", (e) => {
  if (!e.target.classList?.contains("zw-suche")) return;
  zw.meldung = "";
  zuordnenZeichnen(true);
});

document.addEventListener("keydown", (e) => {
  if (!zuordnenOffen() || !e.target.classList?.contains("zw-suche")) return;
  const zeilen = zuordnenZeilen();
  if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); return zuordnenSchliessen(); }
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    if (zeilen.length) zw.aktiv = zw.aktiv < 0 ? (e.key === "ArrowDown" ? 0 : zeilen.length - 1)
      : (zw.aktiv + (e.key === "ArrowDown" ? 1 : -1) + zeilen.length) % zeilen.length;
    return zuordnenZeichnen();
  }
  if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); return zuordnenAnwenden(zeilen[zw.aktiv]); }
}, true);

document.addEventListener("click", (e) => {
  const z = e.target.closest?.("#zuordnen .zw-zeile");
  if (!z) return;
  zuordnenAnwenden(zuordnenZeilen()[+z.dataset.zwI]);
});

// Ausserhalb geklickt: zu. (Der Knopf, der es geöffnet hat, schaltet selbst um.)
document.addEventListener("pointerdown", (e) => {
  if (!zuordnenOffen() || e.target.closest?.("#zuordnen") || (zw.anker && zw.anker.contains?.(e.target))) return;
  zuordnenSchliessen(false);
}, true);
window.addEventListener("resize", () => zuordnenSchliessen(false));
