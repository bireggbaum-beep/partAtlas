"""Ersatz für FreeCADCmd in den Suiten: führt das echte cad_skript.py aus, nur mit Attrappen für Part und MeshPart.
Dateinamen steuern, was geschieht: „haengt“ hängt, „kaputt“ wirft eine Ausnahme, alles andere ergibt ein Netz."""
import os
import sys
import time

job = os.environ.pop("PARTATLAS_CAD_JOB")        # sonst startet das Skript beim Import selbst, mit echtem FreeCAD
import muster                                     # setzt den Suchpfad auf die Quelle (PARTATLAS_QUELLE)
from partatlas import cad_skript

if os.environ.get("CAD_ATTRAPPE_LOG"):
    with open(os.environ["CAD_ATTRAPPE_LOG"], "a") as f:
        f.write("start\n")


class Netz:
    CountFacets = 12

    def __init__(self, name):
        self.name = name

    def write(self, ziel):
        muster.stl_binaer(ziel, 10 + sum(map(ord, self.name)) % 20, 20, 30)


class Form:
    def __init__(self, name):
        self.name = name

    def isNull(self):
        return False


class Part:
    @staticmethod
    def read(pfad):
        name = os.path.basename(pfad)
        if "haengt" in name:
            time.sleep(600)
        if "kaputt" in name:
            raise ValueError("kaputt")
        return Form(name)


class MeshPart:
    @staticmethod
    def meshFromShape(Shape, LinearDeflection, AngularDeflection, Relative):
        return Netz(Shape.name)


cad_skript.lauf(job, Part, MeshPart)
