"""Startpunkt für das gepackte partAtlas (PyInstaller): ruft `python -m partatlas` auf, ohne dass ein Python installiert sein muss."""
import runpy

runpy.run_module("partatlas", run_name="__main__")
