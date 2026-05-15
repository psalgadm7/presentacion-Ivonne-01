import os
import json
from flask import Flask, render_template, send_from_directory, request, jsonify

app = Flask(__name__)

LAMINAS_DIR = os.path.join(os.path.dirname(__file__), "static", "images")
ORDEN_FILE  = os.path.join(os.path.dirname(__file__), "orden.json")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def get_images():
    all_imgs = [
        f for f in os.listdir(LAMINAS_DIR)
        if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
    ]
    if os.path.exists(ORDEN_FILE):
        with open(ORDEN_FILE) as f:
            orden = json.load(f)
        ordered = [img for img in orden if img in all_imgs]
        nuevas  = sorted([img for img in all_imgs if img not in ordered])
        return ordered + nuevas
    return sorted(all_imgs)


@app.route("/")
def index():
    images = get_images()
    return render_template("index.html", images=images)


@app.route("/img/<path:filename>")
def serve_image(filename):
    return send_from_directory(LAMINAS_DIR, filename)


@app.route("/editar")
def editar():
    images = get_images()
    return render_template("editar.html", images=images)


@app.route("/api/orden", methods=["POST"])
def guardar_orden():
    data  = request.get_json(silent=True) or {}
    orden = data.get("orden", [])
    # Validar que solo contenga nombres de archivo existentes
    validos = {
        f for f in os.listdir(LAMINAS_DIR)
        if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
    }
    orden_seguro = [img for img in orden if img in validos]
    with open(ORDEN_FILE, "w") as f:
        json.dump(orden_seguro, f)
    return jsonify({"ok": True, "total": len(orden_seguro)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
