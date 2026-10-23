// Die Hülle um partAtlas: startet den Server als Kindprozess auf einem freien Port, wartet bis er antwortet und zeigt ihn im Fenster.
// Der Server selbst bleibt unverändert (`python -m partatlas`); hier liegt nur, was ein Desktop-Programm zusätzlich braucht.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::{SocketAddr, TcpListener, TcpStream};
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent};

struct Dienst(Mutex<Option<Child>>);

fn freier_port() -> u16 {
    // Kurz binden und wieder loslassen: der Server bindet danach denselben Port.
    TcpListener::bind("127.0.0.1:0").expect("kein freier Port").local_addr().unwrap().port()
}

fn dienst_pfad(app: &tauri::AppHandle) -> std::path::PathBuf {
    if let Ok(p) = std::env::var("PARTATLAS_DIENST") {
        return p.into();
    }
    let name = if cfg!(windows) { "partatlas.exe" } else { "partatlas" };
    // Neben dem Programm (entpacktes Archiv ohne Installer) zuerst, sonst im Ressourcenordner des Installers.
    let neben = std::env::current_exe().ok().and_then(|e| e.parent().map(|p| p.join("dienst").join("partatlas").join(name)));
    match neben {
        Some(p) if p.exists() => p,
        _ => app.path().resource_dir().expect("kein Ressourcenordner").join("dienst").join("partatlas").join(name),
    }
}

fn warten_bis_bereit(port: u16, grenze: Duration) -> bool {
    let adresse: SocketAddr = ([127, 0, 0, 1], port).into();
    let start = Instant::now();
    while start.elapsed() < grenze {
        if TcpStream::connect_timeout(&adresse, Duration::from_millis(200)).is_ok() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(150));
    }
    false
}

/// Der Server soll nie ohne das Fenster weiterlaufen, auch wenn das Programm hart beendet wird (kill, Absturz): unter Linux
/// schickt der Kern ihm dann SIGKILL. Unter Windows übernimmt das später ein Job-Objekt.
fn kind_starten(pfad: std::path::PathBuf, port: u16) -> std::io::Result<Child> {
    let mut befehl = Command::new(pfad);
    befehl.env("PARTATLAS_PORT", port.to_string());
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::process::CommandExt;
        unsafe {
            befehl.pre_exec(|| {
                libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGKILL);
                Ok(())
            });
        }
    }
    befehl.spawn()
}

fn main() {
    // Die Webansicht (webkit2gtk) zeichnet sonst auf manchen Linux-Rechnern (Arch/Manjaro, alte Grafikkarten) ein schwarzes Fenster oder
    // hängt den ganzen Rechner auf. Darum zeichnet das Programm vorerst mit dem Prozessor und fasst die Grafikkarte nicht an. Wer es
    // schneller will: PARTATLAS_GRAFIK=schnell setzen. Werte, die jemand selbst gesetzt hat, bleiben.
    #[cfg(target_os = "linux")]
    if std::env::var("PARTATLAS_GRAFIK").as_deref() != Ok("schnell") {
        for (name, wert) in [
            ("WEBKIT_DISABLE_DMABUF_RENDERER", "1"),
            ("WEBKIT_DISABLE_COMPOSITING_MODE", "1"),
            ("LIBGL_ALWAYS_SOFTWARE", "1"),
        ] {
            if std::env::var_os(name).is_none() {
                std::env::set_var(name, wert);
            }
        }
    }
    let app = tauri::Builder::default()
        .setup(|app| {
            let port = freier_port();
            let kind = kind_starten(dienst_pfad(app.handle()), port);
            let fenster = app.get_webview_window("main").expect("kein Fenster");
            match kind {
                Ok(k) => {
                    app.manage(Dienst(Mutex::new(Some(k))));
                    std::thread::spawn(move || {
                        let url = format!("http://127.0.0.1:{port}/");
                        if warten_bis_bereit(port, Duration::from_secs(60)) {
                            let _ = fenster.navigate(url.parse().unwrap());
                        } else {
                            let _ = fenster.eval("document.body.innerHTML = '<p>partAtlas hat nicht gestartet.</p>'");
                        }
                    });
                }
                Err(e) => {
                    let text = format!("document.body.innerHTML = '<p>partAtlas konnte nicht gestartet werden: {}</p>'", e.to_string().replace('\'', ""));
                    let _ = fenster.eval(&text);
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Fenster konnte nicht gebaut werden");

    app.run(|handle, ereignis| {
        if let RunEvent::Exit = ereignis {
            if let Some(d) = handle.try_state::<Dienst>() {
                if let Some(mut k) = d.0.lock().unwrap().take() {
                    let _ = k.kill();
                    let _ = k.wait();
                }
            }
        }
    });
}
