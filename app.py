import os
import json
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

CONTENT_DIR    = os.path.join(app.root_path, "content")
CONTENIDO_FILE = os.path.join(CONTENT_DIR, "contenido.json")
IMAGES_DIR     = os.path.join(CONTENT_DIR, "images")
ORDEN_FILE     = os.path.join(IMAGES_DIR, "orden.json")
EXTS           = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def load_contenido():
    with open(CONTENIDO_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_contenido(data):
    with open(CONTENIDO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_images():
    try:
        all_files = {
            f for f in os.listdir(IMAGES_DIR)
            if os.path.splitext(f)[1].lower() in EXTS
        }
    except FileNotFoundError:
        return []
    try:
        with open(ORDEN_FILE, encoding="utf-8") as f:
            orden = json.load(f)
        ordered = [f for f in orden if f in all_files]
        rest    = sorted(all_files - set(ordered))
        return ordered + rest
    except (FileNotFoundError, ValueError):
        return sorted(all_files)


def save_orden(orden):
    with open(ORDEN_FILE, "w", encoding="utf-8") as f:
        json.dump(orden, f, ensure_ascii=False)


# ── Servir archivos de contenido ────────────────────────────
@app.route("/content/<path:filename>")
def serve_content(filename):
    return send_from_directory(CONTENT_DIR, filename)


# ── Rutas públicas ──────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html",
                           contenido=load_contenido(),
                           images=get_images())


# ── Editor ──────────────────────────────────────────────────
@app.route("/editar")
def editar():
    return render_template("editar.html",
                           contenido=load_contenido(),
                           images=get_images())


@app.route("/guardar-contenido", methods=["POST"])
def guardar_contenido():
    data = request.get_json(force=True)
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "datos inválidos"}), 400
    save_contenido(data)
    return jsonify({"ok": True})


@app.route("/guardar-orden-imagenes", methods=["POST"])
def guardar_orden_imagenes():
    data = request.get_json(force=True)
    orden = data.get("orden", [])
    # Validar que sean solo nombres de archivo sin rutas
    orden = [os.path.basename(f) for f in orden if isinstance(f, str)]
    save_orden(orden)
    return jsonify({"ok": True})


@app.route("/eliminar-imagen", methods=["POST"])
def eliminar_imagen():
    nombre = request.get_json(force=True).get("nombre", "")
    nombre = os.path.basename(nombre)          # prevenir path traversal
    if nombre:
        path = os.path.join(IMAGES_DIR, nombre)
        if os.path.isfile(path):
            os.remove(path)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
