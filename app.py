import os
import re
import json
import unicodedata
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

# ── Créditos del equipo (configurables via variables de entorno) ──
CREDIT_CONTENT_ROLE = os.environ.get("CREDIT_CONTENT_ROLE", "Content Creation")
CREDIT_CONTENT_NAME = os.environ.get("CREDIT_CONTENT_NAME", "Ivonne Casas Gago")
CREDIT_DEV_ROLE     = os.environ.get("CREDIT_DEV_ROLE",     "Web Design & Development")
CREDIT_DEV_NAME     = os.environ.get("CREDIT_DEV_NAME",     "Pablo Salgado Miranda")
PROJECT_NAME        = os.environ.get("PROJECT_NAME",        "Plena")

CONTENT_DIR    = os.path.join(app.root_path, "content")
CONTENIDO_FILE = os.path.join(CONTENT_DIR, "contenido.json")
IMAGES_DIR     = os.path.join(CONTENT_DIR, "images")
ORDEN_FILE     = os.path.join(IMAGES_DIR, "orden.json")
EXTS           = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

ALLOWED_MEDIA = {
    "imagen":    ({"jpg", "jpeg", "png", "gif", "webp"},                    "images"),
    "video":     ({"mp4", "webm", "ogv"},                                    "videos"),
    "audio":     ({"mp3", "wav", "ogg", "m4a"},                             "audio"),
    "documento": ({"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt"}, "documentos"),
}


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


def get_documentos():
    """Devuelve lista de archivos en content/documentos/."""
    docs_dir = os.path.join(CONTENT_DIR, "documentos")
    try:
        return sorted(f for f in os.listdir(docs_dir) if not f.startswith("."))
    except FileNotFoundError:
        return []


# ── Servir archivos de contenido ────────────────────────────
@app.route("/content/<path:filename>")
def serve_content(filename):
    return send_from_directory(CONTENT_DIR, filename)


# ── Subir media (imagen / video / audio) ────────────────────────
@app.route("/subir-media", methods=["POST"])
def subir_media():
    tipo = request.form.get("tipo", "imagen")
    if tipo not in ALLOWED_MEDIA:
        return jsonify({"ok": False, "error": "tipo inválido"}), 400
    f = request.files.get("archivo")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "sin archivo"}), 400
    ext = os.path.splitext(f.filename)[1].lstrip(".").lower()
    exts_ok, subcarpeta = ALLOWED_MEDIA[tipo]
    if ext not in exts_ok:
        return jsonify({"ok": False, "error": f"extensión .{ext} no permitida"}), 400
    # Nombre seguro: normalizar unicode → ASCII, solo [a-zA-Z0-9._-], truncar a 60 chars
    raw = os.path.splitext(os.path.basename(f.filename))[0]
    raw = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    nombre_base = re.sub(r"[^a-zA-Z0-9._-]", "_", raw)[:60].strip("_") or "archivo"
    nombre = nombre_base + "." + ext
    dest_dir = os.path.join(CONTENT_DIR, subcarpeta)
    os.makedirs(dest_dir, exist_ok=True)   # crear carpeta si no existe
    destino = os.path.join(dest_dir, nombre)
    counter = 1
    while os.path.exists(destino):         # evitar sobreescritura
        nombre = f"{nombre_base}_{counter}.{ext}"
        destino = os.path.join(dest_dir, nombre)
        counter += 1
    f.save(destino)
    return jsonify({"ok": True, "url": f"/content/{subcarpeta}/{nombre}", "nombre": nombre})


# ── Rutas públicas ──────────────────────────────────────────
@app.route("/")
def index():
    credits = {
        "content_role": CREDIT_CONTENT_ROLE,
        "content_name": CREDIT_CONTENT_NAME,
        "dev_role":     CREDIT_DEV_ROLE,
        "dev_name":     CREDIT_DEV_NAME,
        "project_name": PROJECT_NAME,
    }
    return render_template("index.html",
                           contenido=load_contenido(),
                           images=get_images(),
                           credits=credits)


# ── Editor ──────────────────────────────────────────────────
@app.route("/editar")
def editar():
    return render_template("editar.html",
                           contenido=load_contenido(),
                           images=get_images(),
                           documentos=get_documentos())


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


@app.route("/eliminar-media", methods=["POST"])
def eliminar_media():
    """Elimina un archivo de media (imagen, video, audio) de content/."""
    data      = request.get_json(force=True)
    tipo      = data.get("tipo", "imagen")
    nombre    = os.path.basename(data.get("nombre", ""))  # prevenir path traversal
    if tipo not in ALLOWED_MEDIA or not nombre:
        return jsonify({"ok": False, "error": "datos inválidos"}), 400
    _, subcarpeta = ALLOWED_MEDIA[tipo]
    path = os.path.join(CONTENT_DIR, subcarpeta, nombre)
    if os.path.isfile(path):
        os.remove(path)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
