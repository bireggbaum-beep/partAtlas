"""
Scroll-Bench der Oberfläche (Raster, Karten): speist N künstliche Modelle
(Standard 5000) in die Seite ein und scrollt 300 Frames à 60 px. Misst je Frame
Skript-, Layout- und Stilzeit des Hauptthreads (CDP) und die Frame-Abstände.

    FLATGRAPH_REPO=/home/user/flatgraphdb N=5000 python messung/scroll_bench.py

Headless mit SwiftShader: die Frame-Abstände hängen am Malen in Software und
sagen über eine echte Grafikkarte wenig; belastbar ist der Hauptthread
(„ms/Frame“). Die Varianten zeigen, was das Malen kostet (z. B. ohne Bilder).
"""
import asyncio, os, subprocess, sys, tempfile, time, socket, json, copy, statistics, urllib.request
WURZEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(WURZEL, "tests"))
import muster
from test_ui import api, chromium
N = int(os.environ.get("N", 5000))
tmp = tempfile.mkdtemp(); sam = os.path.join(tmp, "S"); os.makedirs(sam)
muster.stl_binaer(os.path.join(sam, "A.stl"), 120, 20, 6); muster.stl_binaer(os.path.join(sam, "B.stl"), 10, 30, 40)
with socket.socket() as s:
    s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
env = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "b"), "PARTATLAS_PORT": str(port), "PYTHONPATH": os.pathsep.join([os.environ.get("PARTATLAS_QUELLE") or WURZEL, os.environ.get("FLATGRAPH_REPO", "/home/user/flatgraphdb")])}
srv = subprocess.Popen([sys.executable, "-m", "partatlas"], env=env, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(100):
        try: api(port, "/api/stand"); break
        except OSError: time.sleep(0.1)
    api(port, "/api/wurzeln", {"pfad": sam}); api(port, "/api/scan", {})
    while api(port, "/api/stand")["scan"].get("laeuft"): time.sleep(0.3)
    echt = api(port, "/api/modelle?leiste=1")
    print("API-Antwort:", type(echt).__name__, list(echt)[:6] if isinstance(echt, dict) else len(echt))
    liste = echt["modelle"] if isinstance(echt, dict) else echt
    png = urllib.request.urlopen(f"http://127.0.0.1:{port}" + (f"/api/vorschau/{liste[0]['hash']}.png")).read()
    print("Vorschau-Bytes:", len(png))
    def gross():
        out = []
        for i in range(N):
            m = copy.deepcopy(liste[i % len(liste)]); m["id"] = f"x{i}"; m["name"] = f"Modell {i:05d} Halterung lang"
            m["hash"] = f"h{i:05d}"; m["tags"] = ["alpha", "beta", "gamma"][: i % 4]
            out.append(m)
        return out
    GROSS = gross()
    async def go():
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=chromium(), args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
            pg = await b.new_page(viewport={"width": 1400, "height": 800})
            async def modelle(route):
                body = json.dumps({**echt, "modelle": GROSS} if isinstance(echt, dict) else GROSS)
                await route.fulfill(status=200, content_type="application/json", body=body)
            await pg.route("**/api/modelle?*", modelle); await pg.route("**/api/modelle", modelle)
            import io
            from PIL import Image
            import numpy as np
            foto = io.BytesIO(); Image.fromarray(np.random.default_rng(1).integers(0, 255, (1200, 1200, 3), dtype=np.uint8)).save(foto, "PNG"); foto = foto.getvalue()
            print("Foto-Bytes:", len(foto))
            klein = io.BytesIO(); yy, xx = np.mgrid[0:320, 0:320]
            Image.fromarray(np.dstack([xx * 255 // 320, yy * 255 // 320, (xx + yy) * 255 // 640]).astype(np.uint8)).save(klein, "WEBP", quality=80)
            klein = klein.getvalue(); print("Thumb-Bytes:", len(klein))
            zaehler = {"n": 0}
            async def vorschau(r):
                zaehler["n"] += 1
                if "t=1" in r.request.url: await r.fulfill(status=200, content_type="image/webp", body=klein)
                else: await r.fulfill(status=200, content_type="image/png", body=foto if os.environ.get("FOTOS", "1") == "1" else png)
            if os.environ.get("BILDER") == "404":      # ohne Interception: nur die Anfragekosten, echter Server antwortet 404
                pg.on("request", lambda q: zaehler.__setitem__("n", zaehler["n"] + 1) if "/api/vorschau/" in q.url else None)
            else:
                await pg.route("**/api/vorschau/**", vorschau)
            await pg.goto(f"http://127.0.0.1:{port}/?phase=2")
            await pg.wait_for_function("zustand.modelle.length >= %d" % N, timeout=60000)
            print("Modelle im Browser:", await pg.evaluate("zustand.modelle.length"))
            # Das Ziehen an der Scrollleiste: jeder Frame springt weit, 60 Frames, danach Ruhe bis alle Bilder da sind.
            for lay in ["raster", "karten"]:
              await pg.click(f'[data-layout="{lay}"]'); await pg.wait_for_timeout(500)
              for name in [os.environ.get("LABEL", "Stand")]:
                await pg.evaluate("document.querySelector('#raster').scrollTop = 0"); await pg.wait_for_timeout(800)
                zaehler["n"] = 0
                cdp = await pg.context.new_cdp_session(pg); await cdp.send("Performance.enable")
                m0 = {x["name"]: x["value"] for x in (await cdp.send("Performance.getMetrics"))["metrics"]}
                r = await pg.evaluate("""async () => {
                  const a = document.querySelector('#raster'); const max = a.scrollHeight - a.clientHeight;
                  const dt = []; let last = performance.now();
                  await new Promise(res => { let k = 0; const f = (t) => { dt.push(t - last); last = t; a.scrollTop = (k / 60) * max; if (++k <= 60) requestAnimationFrame(f); else res(); }; requestAnimationFrame(f); });
                  dt.shift(); dt.sort((x, y) => x - y);
                  return { median: dt[dt.length >> 1], p95: dt[Math.floor(dt.length * .95)], max: dt[dt.length - 1] };
                }""")
                m1 = {x["name"]: x["value"] for x in (await cdp.send("Performance.getMetrics"))["metrics"]}
                await pg.wait_for_timeout(1500)
                d = {k[:-8]: round((m1[k] - m0[k]) * 1000 / 60, 1) for k in ["ScriptDuration", "TaskDuration"]}
                print(f"{lay:7s} {name:14s}", {k: round(v, 1) for k, v in r.items()}, "ms/Frame:", d, "Bilder angefordert beim Ziehen:", zaehler["n"], "bis Ruhe:", zaehler["n_ruhe"] if "n_ruhe" in zaehler else "")
            await b.close()
    asyncio.run(go())
finally:
    srv.terminate()
