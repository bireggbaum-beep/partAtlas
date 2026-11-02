// Das Feld „＋ Tag“ im Inspektor mit Vorschlägen aus den vorhandenen Tags (Anwender 2.11.2026: „nativ, wie eine Premium-App“).
// Zweck: kein Tippfehler-Duplikat („halterung“ neben „halter“), und mehrere Tags hintereinander ohne Maus. Enter nimmt den markierten Vorschlag;
// vorbelegt ist ein genauer Treffer oder einer, der so anfängt — sonst „neu anlegen“, damit ein neuer Tag nie aus Versehen ein anderer wird.

const tf = { tags: null, liste: [], markiert: -1, offen: false };

const tfNorm = (s) => s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/^#/, "").trim();

function tfFeld() { return document.getElementById("tag-neu"); }

function tfBox() {
  let b = document.getElementById("tag-vorschlaege");
  if (!b) {
    b = document.createElement("ul");
    b.id = "tag-vorschlaege";
    b.className = "tag-vorschlaege";
    b.setAttribute("role", "listbox");
    b.hidden = true;
    document.body.append(b);
    // mousedown statt click: das Feld behält den Fokus, die Liste schliesst nicht vorher
    b.addEventListener("mousedown", (e) => {
      const li = e.target.closest("li[data-i]");
      if (!li) return;
      e.preventDefault();
      tfNehmen(Number(li.dataset.i));
    });
  }
  return b;
}

async function tfTagsLaden() {
  try { tf.tags = await api("/api/tags"); } catch { tf.tags = []; }
}

function tfBerechnen() {
  const feld = tfFeld();
  const roh = feld.value.trim().replace(/^#/, "");
  const q = tfNorm(roh);
  const schon = new Set([...document.querySelectorAll(".i-tags [data-tag-weg]")].map((b) => b.dataset.tagWeg));
  if (!q || !tf.tags) return { liste: [], markiert: -1 };
  const rang = (t) => { const n = tfNorm(t.name); return n === q ? 0 : n.startsWith(q) ? 1 : n.split(/[\s_-]+/).some((w) => w.startsWith(q)) ? 2 : n.includes(q) ? 3 : 9; };
  const treffer = tf.tags.filter((t) => !schon.has(t.name)).map((t) => [rang(t), t]).filter(([r]) => r < 9)
    .sort((a, b) => a[0] - b[0] || (b[1].eigen > 0) - (a[1].eigen > 0) || b[1].anzahl - a[1].anzahl || a[1].name.localeCompare(b[1].name, "de"))
    .slice(0, 8).map(([r, t]) => ({ ...t, rang: r }));
  const genau = treffer.some((t) => t.rang === 0) || schon.has(q);
  const liste = genau ? treffer : [...treffer, { neu: true, name: roh }];
  // Vorbelegt: genau oder Anfang — sonst „neu anlegen“ (die letzte Zeile).
  const markiert = treffer.length && treffer[0].rang <= 1 ? 0 : liste.length - 1;
  return { liste, markiert };
}

function tfZeichnen() {
  const feld = tfFeld(), box = tfBox();
  if (!feld || !tf.offen || !tf.liste.length) {
    box.hidden = true;
    feld?.setAttribute("aria-expanded", "false");
    feld?.removeAttribute("aria-activedescendant");
    return;
  }
  box.innerHTML = tf.liste.map((t, i) => `<li role="option" id="tv-${i}" data-i="${i}" aria-selected="${i === tf.markiert}"
      class="${i === tf.markiert ? "markiert" : ""} ${t.neu ? "neu" : ""} ${!t.neu && !t.eigen ? "auto" : ""}">
      ${t.neu ? `<span>„${esc(t.name)}“ neu anlegen</span><kbd>Enter</kbd>` : `<span>#${esc(t.name)}</span><em>${t.anzahl}</em>`}</li>`).join("");
  const r = feld.getBoundingClientRect();
  box.style.left = `${Math.round(Math.min(r.left, innerWidth - 220))}px`;
  box.style.minWidth = `${Math.max(200, Math.round(r.width))}px`;
  box.style.maxHeight = "";
  box.hidden = false;
  // Unter das Feld, wenn dort Platz ist; sonst darüber — wie ein Auswahlmenü des Systems am unteren Fensterrand.
  const unten = innerHeight - r.bottom - 12, oben = r.top - 12, h = box.offsetHeight;
  const nachOben = h > unten && oben > unten;
  box.style.maxHeight = `${Math.max(120, Math.min(260, nachOben ? oben : unten))}px`;
  box.style.top = `${Math.round(nachOben ? r.top - 4 - box.offsetHeight : r.bottom + 4)}px`;
  feld.setAttribute("aria-expanded", "true");
  feld.setAttribute("aria-activedescendant", `tv-${tf.markiert}`);
  box.querySelector(".markiert")?.scrollIntoView({ block: "nearest" });
}

function tfAktualisieren() {
  const { liste, markiert } = tfBerechnen();
  tf.liste = liste; tf.markiert = markiert; tf.offen = liste.length > 0;
  tfZeichnen();
}

function tfSchliessen() { tf.offen = false; tfZeichnen(); }

async function tfNehmen(i) {
  const feld = tfFeld();
  const t = tf.liste[i];
  const name = t ? t.name : feld.value.trim();
  if (!name) return;
  tfSchliessen();
  const id = $("#inspektor").dataset.id;
  try { await api(`/api/modelle/${id}/tags`, { method: "POST", body: { tag: name } }); }
  catch (err) { return toast(err.message); }
  tf.tags = null;                        // die Anzahlen haben sich geändert
  await waehle(id);
  // Weiter im Feld: mehrere Tags hintereinander, ohne neu hineinzuklicken.
  const neu = tfFeld();
  if (neu) { neu.focus(); tfTagsLaden(); }
}

document.addEventListener("focusin", (e) => { if (e.target.id === "tag-neu" && !tf.tags) tfTagsLaden(); });
document.addEventListener("focusout", (e) => { if (e.target.id === "tag-neu") tfSchliessen(); });
document.addEventListener("input", async (e) => {
  if (e.target.id !== "tag-neu") return;
  if (!tf.tags) await tfTagsLaden();
  tfAktualisieren();
});
document.addEventListener("keydown", (e) => {
  if (e.target.id !== "tag-neu" || e.isComposing) return;
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    if (!tf.offen) { tfAktualisieren(); e.preventDefault(); return; }
    const n = tf.liste.length;
    tf.markiert = (tf.markiert + (e.key === "ArrowDown" ? 1 : -1) + n) % n;
    tfZeichnen();
    e.preventDefault();
  } else if (e.key === "Enter") {
    e.preventDefault();
    if (e.target.value.trim()) tfNehmen(tf.offen ? tf.markiert : -1);
  } else if (e.key === "Escape") {
    // Erst die Liste zu, dann (zweites Esc) raus aus dem Feld — wie bei jeder Auswahlliste.
    e.preventDefault();
    e.stopImmediatePropagation();
    if (tf.offen) tfSchliessen();
    else { e.target.value = ""; e.target.blur(); }
  }
}, true);
window.addEventListener("resize", () => tf.offen && tfZeichnen());
document.addEventListener("scroll", () => tf.offen && tfZeichnen(), true);
