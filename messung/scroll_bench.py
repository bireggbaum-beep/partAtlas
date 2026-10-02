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
env = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "b"), "PARTATLAS_PORT": str(port), "PYTHONPATH": os.pathsep.join([WURZEL, os.environ.get("FLATGRAPH_REPO", "/home/user/flatgraphdb")])}
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
            await pg.route("**/api/vorschau/**", lambda r: r.fulfill(status=200, content_type="image/png", body=png))
            await pg.goto(f"http://127.0.0.1:{port}/?phase=2")
            await pg.wait_for_function("zustand.modelle.length >= %d" % N, timeout=60000)
            print("Modelle im Browser:", await pg.evaluate("zustand.modelle.length"))
            VAR = {
              "Ausgangslage": "",
              "contain je Kachel": ".karte,.zeile-l,.zeile-k{contain:layout paint style}",
              "contain + Bilder asynchron": ".karte,.zeile-l,.zeile-k{contain:layout paint style}",
              "ohne Bilder": ".karte img,.zeile-l img,.zeile-k img{display:none}",
              "ohne Verlauf/Rahmen": ".karte .bild{background:#222!important}.karte{border:0!important;transition:none!important}",
            }
            for lay in ["raster", "karten"]:
              await pg.click(f'[data-layout="{lay}"]'); await pg.wait_for_timeout(500)
              for name, css in VAR.items():
                await pg.evaluate("(c) => { let s = document.getElementById('v'); if (!s) { s = document.createElement('style'); s.id = 'v'; document.head.append(s); } s.textContent = c; }", css)
                if "asynchron" in name:
                    await pg.evaluate("document.querySelectorAll('img').forEach(i => i.decoding = 'async')")
                await pg.wait_for_timeout(300)
                cdp = await pg.context.new_cdp_session(pg); await cdp.send("Performance.enable")
                m0 = {x["name"]: x["value"] for x in (await cdp.send("Performance.getMetrics"))["metrics"]}
                r = await pg.evaluate("""async () => {
                  const a = document.querySelector('#raster'); a.scrollTop = 0; await new Promise(r => requestAnimationFrame(r));
                  const dt = []; let last = performance.now();
                  await new Promise(res => { let k = 0; const f = (t) => { dt.push(t - last); last = t; a.scrollTop += 60; if (++k < 300) requestAnimationFrame(f); else res(); }; requestAnimationFrame(f); });
                  dt.shift(); dt.sort((x, y) => x - y);
                  return { median: dt[dt.length >> 1], p95: dt[Math.floor(dt.length * .95)], ueber_20ms: dt.filter(x => x > 20).length };
                }""")
                m1 = {x["name"]: x["value"] for x in (await cdp.send("Performance.getMetrics"))["metrics"]}
                d = {k[:-8]: round((m1[k] - m0[k]) * 1000 / 300, 2) for k in ["ScriptDuration", "LayoutDuration", "RecalcStyleDuration", "TaskDuration"]}
                print(f"{lay:7s} {name:28s}", {k: round(v, 1) for k, v in r.items()}, "ms/Frame:", d)
            await b.close()
    asyncio.run(go())
finally:
    srv.terminate()
