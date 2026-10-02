"""Findet jeden Aufruf in partatlas/, der eine Datei löscht, verschiebt oder ersetzt, oder Katalogdaten endgültig entfernt —
mit der Funktion, in der er steht. Grundlage des Wächters in test_schutz.py."""
import ast
import os

QUELLE = os.environ.get("PARTATLAS_QUELLE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GENAU = {"os.remove", "os.unlink", "os.rmdir", "os.removedirs", "shutil.rmtree", "shutil.move", "os.rename", "os.renames",
         "os.replace", "os.truncate"}
ENDUNGEN = (".unlink", ".rmdir", ".rmtree", ".verschiebe", ".run_garbage_collection", ".purge", ".hard_delete", ".delete_node",
            ".write_text", ".write_bytes", ".schreibe_atomar")
NAMEN = {"verschiebe", "run_garbage_collection", "schreibe_atomar"}


def _name(knoten):
    if isinstance(knoten, ast.Name):
        return knoten.id
    if isinstance(knoten, ast.Attribute):
        innen = _name(knoten.value)
        return f"{innen}.{knoten.attr}" if innen else f"?.{knoten.attr}"
    return None


def inventur():
    funde = set()
    ordner = os.path.join(QUELLE, "partatlas")
    for datei in sorted(os.listdir(ordner)):
        if not datei.endswith(".py"):
            continue
        baum = ast.parse(open(os.path.join(ordner, datei), encoding="utf-8").read())

        def besuch(k, stapel):
            if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                stapel = stapel + [k.name]
            if isinstance(k, ast.Call):
                n = _name(k.func) or ""
                if n in GENAU or n in NAMEN or any(n.endswith(e) for e in ENDUNGEN):
                    funde.add((datei, ".".join(stapel) or "<modul>", n))
            for kind in ast.iter_child_nodes(k):
                besuch(kind, stapel)
        besuch(baum, [])
    return funde


if __name__ == "__main__":
    for f in sorted(inventur()):
        print(f)
