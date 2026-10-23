"""Startpunkt für das gepackte partAtlas (PyInstaller): ruft `python -m partatlas` auf, ohne dass ein Python installiert sein muss.

freeze_support: Die Hilfsprozesse für die Vorschaubilder starten im gepackten Programm sonst das ganze Programm noch einmal (zweiter
Server, „Adresse belegt“), und es entstünden keine Vorschaubilder.
Starter-Betrieb ist hier der Standard: Browser öffnen, am Ende von selbst beenden. Das Tauri-Fenster setzt PARTATLAS_STARTER=0."""
import multiprocessing
import os
import runpy

if __name__ == "__main__":
    multiprocessing.freeze_support()
    os.environ.setdefault("PARTATLAS_STARTER", "1")
    runpy.run_module("partatlas", run_name="__main__")
