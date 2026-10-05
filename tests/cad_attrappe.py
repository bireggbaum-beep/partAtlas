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
        f.write(f"start nice={os.nice(0)}\n")


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
        if "langsam" in name:
            time.sleep(1.5)
        if "kaputt" in name:
            raise ValueError("kaputt")
        return Form(name)


class Objekt:
    def __init__(self, name, sichtbar=True):
        self.Shape = Form(name)
        self.Visibility = sichtbar
        self.InList = []


class Dokument:
    def __init__(self, name):
        self.Name = name
        self.Objects = [Objekt(name), Objekt("verdeckt_" + name, sichtbar=False)]


class FreeCAD:
    @staticmethod
    def openDocument(pfad):
        name = os.path.basename(pfad)
        if "haengt" in name:
            time.sleep(600)
        if "kaputt" in name:
            raise ValueError("kaputt")
        return Dokument(name)

    @staticmethod
    def closeDocument(name):
        pass


Part.makeCompound = staticmethod(lambda formen: formen[0])


class MeshPart:
    @staticmethod
    def meshFromShape(Shape, LinearDeflection, AngularDeflection, Relative):
        return Netz(Shape.name)


cad_skript.lauf(job, Part, MeshPart, FreeCAD)
