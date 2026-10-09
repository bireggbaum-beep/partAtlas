// 3D-Ansicht ohne Grafikkarte: Rückfall, wenn WebGL fehlt oder abbricht
// (alte Treiber, Linux-Tester mit GeForce 9 und nouveau). Gezeichnet wird
// mit Canvas 2D: Dreiecke nach Tiefe sortiert, flach beleuchtet. Gröber als
// three.js, aber auf jedem Rechner.
//
// Rückbaubar: dieses Modul und die Weiche in app.js (siehe OFFEN.md,
// „3D-Ansicht ohne funktionierendes WebGL“). Dieselbe Schnittstelle wie
// viewer.js: zeige(), schliessen().

// Mehr Dreiecke zeichnet Canvas 2D nicht flüssig; grössere Netze werden
// vereinfacht (Ecken auf ein Raster zusammengezogen). Beim Drehen gilt die
// grobe Stufe, sobald die feine zu langsam war; in Ruhe wieder die feine.
const FEIN = 30000, GROB = 6000, ZU_LANGSAM_MS = 40;
const SICHT = 35 * Math.PI / 180;

let aktiv = null;

export function schliessen() {
  if (!aktiv) return;
  cancelAnimationFrame(aktiv.rahmen);
  clearTimeout(aktiv.ruhe);
  aktiv.beobachter.disconnect();
  aktiv.leinwand.remove();
  aktiv = null;
}

// Ecken in `zellen` Würfel je Kante zusammenziehen; Dreiecke, die dabei
// zu einer Linie oder doppelt werden, fallen weg. Ergebnis indiziert.
// `pos` ist eine Dreieckssuppe (9 Werte je Dreieck) oder, mit `index`, indiziert.
function vereinfachen(pos, zellen, kiste, index = null) {
  const [x0, y0, z0, x1, y1, z1] = kiste;
  const k = (zellen - 1) / Math.max(x1 - x0, y1 - y0, z1 - z0, 1e-9);
  const nachZelle = new Map(), summe = [], dreiecke = [], gesehen = new Set();
  const anzahl = index ? index.length : pos.length / 3;
  const ort = index ? (j) => index[j] * 3 : (j) => j * 3;
  const alsZahl = anzahl ** 3 < Number.MAX_SAFE_INTEGER;
  const ecke = (i) => {
    const s = Math.round((pos[i] - x0) * k) + zellen * (Math.round((pos[i + 1] - y0) * k) + zellen * Math.round((pos[i + 2] - z0) * k));
    let n = nachZelle.get(s);
    if (n === undefined) { n = summe.length / 4; nachZelle.set(s, n); summe.push(0, 0, 0, 0); }
    summe[n * 4] += pos[i]; summe[n * 4 + 1] += pos[i + 1]; summe[n * 4 + 2] += pos[i + 2]; summe[n * 4 + 3]++;
    return n;
  };
  for (let j = 0; j < anzahl; j += 3) {
    const a = ecke(ort(j)), b = ecke(ort(j + 1)), c = ecke(ort(j + 2));
    if (a === b || b === c || a === c) continue;
    const p = Math.min(a, b, c), r = Math.max(a, b, c), q = a + b + c - p - r;
    // Zahl statt Text als Schlüssel (schneller), solange sie eindeutig bleibt.
    const schluessel = alsZahl ? (p * anzahl + q) * anzahl + r : `${p},${q},${r}`;
    if (gesehen.has(schluessel)) continue;
    gesehen.add(schluessel);
    dreiecke.push(a, b, c);
  }
  const ecken = new Float32Array(summe.length / 4 * 3);
  for (let n = 0; n < summe.length / 4; n++)
    for (let j = 0; j < 3; j++) ecken[n * 3 + j] = summe[n * 4 + j] / summe[n * 4 + 3];
  return { ecken, dreiecke: Uint32Array.from(dreiecke) };
}

function unvereinfacht(pos) {
  const n = pos.length / 3;
  return { ecken: pos, dreiecke: Uint32Array.from({ length: n }, (_, i) => i) };
}

// Höchstens `grenze` Dreiecke, so fein wie möglich. Eine Oberfläche hat
// etwa zellen² Dreiecke: aus einem Probelauf die passende Zahl schätzen,
// statt das Raster in vielen Läufen schrittweise zu verkleinern.
function stufe(netz, grenze, kiste) {
  const n = netz.dreiecke.length / 3;
  if (n <= grenze) return netz;
  const lauf = (zellen) => vereinfachen(netz.ecken, zellen, kiste, netz.dreiecke);
  let zellen = 64, neu = lauf(zellen);
  for (let versuch = 0; versuch < 4; versuch++) {
    const ist = neu.dreiecke.length / 3;
    if (ist <= grenze && ist > grenze * 0.6) break;
    const naechste = Math.max(4, Math.min(1024, Math.floor(zellen * Math.sqrt(grenze / Math.max(ist, 1)) * 0.95)));
    if (naechste === zellen) break;
    zellen = naechste;
    const probe = lauf(zellen);
    if (probe.dreiecke.length / 3 <= grenze || neu.dreiecke.length / 3 > grenze) neu = probe;
  }
  return neu;
}

// Flächennormale je Dreieck, einmal beim Laden.
function normalen({ ecken, dreiecke }) {
  const n = new Float32Array(dreiecke.length);
  for (let t = 0; t < dreiecke.length; t += 3) {
    const a = dreiecke[t] * 3, b = dreiecke[t + 1] * 3, c = dreiecke[t + 2] * 3;
    const ux = ecken[b] - ecken[a], uy = ecken[b + 1] - ecken[a + 1], uz = ecken[b + 2] - ecken[a + 2];
    const vx = ecken[c] - ecken[a], vy = ecken[c + 1] - ecken[a + 1], vz = ecken[c + 2] - ecken[a + 2];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    const l = Math.hypot(nx, ny, nz) || 1;
    n[t] = nx / l; n[t + 1] = ny / l; n[t + 2] = nz / l;
  }
  return n;
}

function hexZuRgb(hex) {
  const h = hex && /^#[0-9a-f]{6}/i.test(hex) ? hex.slice(1, 7) : "e87a5c";
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
}

// `puffer`: wie viewer.js — float32, 9 Werte je Dreieck, Z nach oben.
export function zeige(behaelter, puffer, farbe) {
  schliessen();
  const roh = new Float32Array(puffer);
  // Z oben (Druck) → Y oben, auf das Bett gestellt und mittig, wie viewer.js.
  const pos = new Float32Array(roh.length);
  for (let i = 0; i < roh.length; i += 3) { pos[i] = roh[i]; pos[i + 1] = roh[i + 2]; pos[i + 2] = -roh[i + 1]; }
  const kiste = [Infinity, Infinity, Infinity, -Infinity, -Infinity, -Infinity];
  for (let i = 0; i < pos.length; i += 3)
    for (let j = 0; j < 3; j++) { kiste[j] = Math.min(kiste[j], pos[i + j]); kiste[j + 3] = Math.max(kiste[j + 3], pos[i + j]); }
  const mx = (kiste[0] + kiste[3]) / 2, my = kiste[1], mz = (kiste[2] + kiste[5]) / 2;
  for (let i = 0; i < pos.length; i += 3) { pos[i] -= mx; pos[i + 1] -= my; pos[i + 2] -= mz; }
  const k = [kiste[0] - mx, 0, kiste[2] - mz, kiste[3] - mx, kiste[4] - my, kiste[5] - mz];
  const r = Math.max(Math.hypot(k[3] - k[0], k[4] - k[1], k[5] - k[2]) / 2, 1e-6);

  const fein = stufe(unvereinfacht(pos), FEIN, k);
  fein.normalen = normalen(fein);
  let grob = null;           // erst bauen, wenn die feine Stufe zu langsam war

  const leinwand = document.createElement("canvas");
  leinwand.className = "ohne-gpu";
  leinwand.title = "3D-Ansicht ohne Grafikkarte";
  behaelter.appendChild(leinwand);
  const ctx = leinwand.getContext("2d");
  const grund = hexZuRgb(farbe);

  // Kamera wie viewer.js: Blick auf die Mitte, Start schräg von oben.
  const startZiel = [0, (k[4] + k[1]) / 2, 0];
  const start = { winkel: Math.PI / 4, hoehe: Math.atan2(r * 1.9, Math.hypot(r * 2.6, r * 2.6)), abstand: Math.hypot(r * 2.6, r * 1.9, r * 2.6) };
  const kam = { ...start, ziel: [...startZiel], dreht: true };
  const licht = (() => { const l = Math.hypot(1, 2, 1.5); return [1 / l, 2 / l, 1.5 / l]; })();

  let zuletztMs = 0, bewegt = false;

  function zeichnen() {
    const b = leinwand.width, h = leinwand.height;
    ctx.clearRect(0, 0, b, h);
    if (!b || !h) return;
    const netz = bewegt && zuletztMs > ZU_LANGSAM_MS ? (grob ||= (() => { const g = stufe(fein, GROB, k); g.normalen = normalen(g); return g; })()) : fein;
    const t0 = performance.now();

    // Kamerabasis: vorwärts f, rechts s, oben u.
    const ch = Math.cos(kam.hoehe), sh = Math.sin(kam.hoehe);
    const auge = [kam.ziel[0] + kam.abstand * ch * Math.sin(kam.winkel), kam.ziel[1] + kam.abstand * sh, kam.ziel[2] + kam.abstand * ch * Math.cos(kam.winkel)];
    const f = [kam.ziel[0] - auge[0], kam.ziel[1] - auge[1], kam.ziel[2] - auge[2]];
    const fl = Math.hypot(...f); f[0] /= fl; f[1] /= fl; f[2] /= fl;
    const s = [-f[2], 0, f[0]]; const sl = Math.hypot(...s) || 1; s[0] /= sl; s[2] /= sl;
    const u = [s[1] * f[2] - s[2] * f[1], s[2] * f[0] - s[0] * f[2], s[0] * f[1] - s[1] * f[0]];
    const brenn = (h / 2) / Math.tan(SICHT / 2), nah = r / 100;
    const projiziere = (x, y, z, aus, o) => {
      const dx = x - auge[0], dy = y - auge[1], dz = z - auge[2];
      const tz = dx * f[0] + dy * f[1] + dz * f[2];
      aus[o] = b / 2 + (dx * s[0] + dy * s[1] + dz * s[2]) * brenn / Math.max(tz, nah);
      aus[o + 1] = h / 2 - (dx * u[0] + dy * u[1] + dz * u[2]) * brenn / Math.max(tz, nah);
      aus[o + 2] = tz;
    };

    // Raster auf dem Bett, zuerst: es liegt unter dem Modell.
    ctx.strokeStyle = "rgba(136,136,136,0.35)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    const halb = r * 1.5, a = new Float32Array(3), e = new Float32Array(3);
    for (let i = -6; i <= 6; i++) {
      const w = halb * i / 6;
      for (const [x0, z0, x1, z1] of [[w, -halb, w, halb], [-halb, w, halb, w]]) {
        projiziere(x0, 0, z0, a, 0); projiziere(x1, 0, z1, e, 0);
        if (a[2] <= nah || e[2] <= nah) continue;
        ctx.moveTo(a[0], a[1]); ctx.lineTo(e[0], e[1]);
      }
    }
    ctx.stroke();

    const { ecken, dreiecke, normalen: nrm } = netz;
    const p = new Float32Array(ecken.length);
    for (let i = 0; i < ecken.length; i += 3) projiziere(ecken[i], ecken[i + 1], ecken[i + 2], p, i);
    const anzahl = dreiecke.length / 3;
    const tiefe = new Float32Array(anzahl), folge = new Uint32Array(anzahl);
    for (let t = 0; t < anzahl; t++) {
      folge[t] = t;
      tiefe[t] = p[dreiecke[t * 3] * 3 + 2] + p[dreiecke[t * 3 + 1] * 3 + 2] + p[dreiecke[t * 3 + 2] * 3 + 2];
    }
    folge.sort((x, y) => tiefe[y] - tiefe[x]);      // hinten zuerst
    ctx.lineJoin = "round";
    for (let j = 0; j < anzahl; j++) {
      const t = folge[j], ia = dreiecke[t * 3] * 3, ib = dreiecke[t * 3 + 1] * 3, ic = dreiecke[t * 3 + 2] * 3;
      if (p[ia + 2] <= nah || p[ib + 2] <= nah || p[ic + 2] <= nah) continue;
      // Beidseitig beleuchtet wie im WebGL-Viewer (DoubleSide): STL-Normalen sind oft falsch herum.
      const hell = 0.42 + 0.58 * Math.abs(nrm[t * 3] * licht[0] + nrm[t * 3 + 1] * licht[1] + nrm[t * 3 + 2] * licht[2]);
      const farbeT = `rgb(${grund[0] * hell | 0},${grund[1] * hell | 0},${grund[2] * hell | 0})`;
      ctx.beginPath();
      ctx.moveTo(p[ia], p[ia + 1]); ctx.lineTo(p[ib], p[ib + 1]); ctx.lineTo(p[ic], p[ic + 1]);
      ctx.closePath();
      ctx.fillStyle = farbeT;
      ctx.fill();
      // Ohne Strich bleiben zwischen den Dreiecken helle Haarlinien (Kantenglättung).
      ctx.strokeStyle = farbeT;
      ctx.stroke();
    }
    if (netz === fein) zuletztMs = performance.now() - t0;
  }

  // Nur zeichnen, wenn sich etwas ändert: auf einem alten Rechner soll die
  // Ansicht nicht dauernd den Prozessor belegen.
  let vorher = 0;
  const schritt = (jetzt) => {
    if (!aktiv) return;
    aktiv.rahmen = 0;
    if (kam.dreht) {
      kam.winkel += (vorher ? jetzt - vorher : 16) / 1000 * (2 * Math.PI / 40);    // eine Umdrehung in 40 s
      vorher = jetzt;
      bewegt = true;
      zeichnen();
      aktiv.rahmen = requestAnimationFrame(schritt);
    } else {
      vorher = 0;
      zeichnen();
    }
  };
  const neuZeichnen = () => { if (aktiv && !aktiv.rahmen) aktiv.rahmen = requestAnimationFrame(schritt); };
  const inRuhe = () => {
    clearTimeout(aktiv.ruhe);
    aktiv.ruhe = setTimeout(() => { if (aktiv && !kam.dreht) { bewegt = false; neuZeichnen(); } }, 200);
  };

  // Ziehen links dreht, rechts (oder mit Umschalt) verschiebt, Rad zoomt.
  let zug = null;
  leinwand.addEventListener("contextmenu", (ev) => ev.preventDefault());
  leinwand.addEventListener("pointerdown", (ev) => {
    kam.dreht = false;           // wer selbst dreht, will nicht, dass es weiterdreht
    zug = { x: ev.clientX, y: ev.clientY, schieben: ev.button === 2 || ev.shiftKey };
    leinwand.setPointerCapture(ev.pointerId);
    leinwand.style.cursor = "grabbing";
  });
  leinwand.addEventListener("pointermove", (ev) => {
    if (!zug) return;
    const dx = ev.clientX - zug.x, dy = ev.clientY - zug.y;
    zug.x = ev.clientX; zug.y = ev.clientY;
    if (zug.schieben) {
      const m = kam.abstand * Math.tan(SICHT / 2) * 2 / Math.max(leinwand.clientHeight, 1);
      const sw = Math.cos(kam.winkel), cw = Math.sin(kam.winkel);
      kam.ziel[0] -= dx * m * sw; kam.ziel[2] += dx * m * cw;
      kam.ziel[1] += dy * m;
    } else {
      kam.winkel -= dx * 0.01;
      kam.hoehe = Math.max(-1.5, Math.min(1.5, kam.hoehe + dy * 0.01));
    }
    bewegt = true;
    neuZeichnen();
  });
  const loslassen = () => { if (!zug) return; zug = null; leinwand.style.cursor = ""; inRuhe(); };
  leinwand.addEventListener("pointerup", loslassen);
  leinwand.addEventListener("pointercancel", loslassen);
  leinwand.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    kam.abstand = Math.max(r * 0.2, Math.min(r * 50, kam.abstand * Math.exp(ev.deltaY * 0.001)));
    bewegt = true;
    neuZeichnen();
    inRuhe();
  }, { passive: false });

  // Volle Pixel nur bis Faktor 1: hochauflösend kostet das Vierfache.
  const beobachter = new ResizeObserver(() => {
    const bb = behaelter.clientWidth, hh = behaelter.clientHeight;
    if (!bb || !hh) return;
    leinwand.width = bb; leinwand.height = hh;
    neuZeichnen();
  });
  beobachter.observe(behaelter);

  aktiv = { leinwand, beobachter, rahmen: 0, ruhe: 0 };
  leinwand.width = behaelter.clientWidth; leinwand.height = behaelter.clientHeight;
  neuZeichnen();

  return {
    zuruecksetzen() {
      Object.assign(kam, start, { ziel: [...startZiel], dreht: true });
      neuZeichnen();
    },
    drehen(an) { kam.dreht = an; if (an) neuZeichnen(); else { bewegt = false; neuZeichnen(); } },
  };
}
