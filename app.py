import os
import re
import unicodedata

import requests                                      # HTTP client (pip: requests)
import cloudinary                                    # pip: cloudinary
import cloudinary.uploader
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ── Créditos del equipo ─────────────────────────────────────
CREDIT_CONTENT_ROLE = os.environ.get("CREDIT_CONTENT_ROLE", "Content Creation")
CREDIT_CONTENT_NAME = os.environ.get("CREDIT_CONTENT_NAME", "Ivonne Casas Gago")
CREDIT_DEV_ROLE     = os.environ.get("CREDIT_DEV_ROLE",     "Web Design & Development")
CREDIT_DEV_NAME     = os.environ.get("CREDIT_DEV_NAME",     "Pablo Salgado Miranda")
PROJECT_NAME        = os.environ.get("PROJECT_NAME",        "Plena")

# ── Cloudinary ──────────────────────────────────────────────
cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    api_key    = os.environ.get("CLOUDINARY_API_KEY", ""),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", ""),
    secure     = True,
)
CLD_FOLDER = os.environ.get("CLOUDINARY_FOLDER", "plena")

# Resource type de Cloudinary por tipo de media
_CLD_RES = {
    "imagen":    "image",
    "video":     "video",
    "audio":     "video",   # Cloudinary maneja audio bajo resource_type "video"
    "documento": "raw",
}

# ── Supabase ────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


def _sb(table):
    return f"{SUPABASE_URL}/rest/v1/{table}"


def _sbh(extra=None):
    """Devuelve headers de Supabase, opcionalmente con campos extra."""
    h = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }
    if extra:
        h.update(extra)
    return h


# ── Tipos de media permitidos ───────────────────────────────
ALLOWED_MEDIA = {
    "imagen":    {"jpg", "jpeg", "png", "gif", "webp"},
    "video":     {"mp4", "webm", "ogv"},
    "audio":     {"mp3", "wav", "ogg", "m4a"},
    "documento": {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt"},
}

# ─────────────────────── SUPABASE ─────────────────────────

def load_contenido():
    try:
        r = requests.get(_sb("contenido"),
                         params={"id": "eq.1", "select": "data"},
                         headers=_sbh(), timeout=10)
        r.raise_for_status()
        rows = r.json()
        return rows[0]["data"] if rows else {}
    except Exception as e:
        app.logger.error(f"load_contenido: {e}")
        return {}


def save_contenido(data):
    r = requests.patch(_sb("contenido"),
                       params={"id": "eq.1"},
                       headers=_sbh({"Prefer": "return=minimal"}),
                       json={"data": data},
                       timeout=10)
    r.raise_for_status()


def get_images():
    """Lista de dicts {nombre, url, public_id} en el orden guardado."""
    try:
        r = requests.get(_sb("imagen_orden"),
                         params={"id": "eq.1", "select": "orden"},
                         headers=_sbh(), timeout=10)
        rows = r.json()
        return (rows[0]["orden"] or []) if rows else []
    except Exception as e:
        app.logger.error(f"get_images: {e}")
        return []


def save_orden(orden):
    requests.patch(_sb("imagen_orden"),
                   params={"id": "eq.1"},
                   headers=_sbh({"Prefer": "return=minimal"}),
                   json={"orden": orden},
                   timeout=10)


def get_documentos():
    """Lista de dicts {id, nombre, url, public_id} de tipo documento."""
    try:
        r = requests.get(_sb("media"),
                         params={"tipo":   "eq.documento",
                                 "select": "id,nombre,url,public_id",
                                 "order":  "created_at.desc"},
                         headers=_sbh(), timeout=10)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        app.logger.error(f"get_documentos: {e}")
        return []


def _add_media_record(tipo, nombre, url, public_id):
    r = requests.post(_sb("media"),
                      headers=_sbh({"Prefer": "return=representation"}),
                      json={"tipo": tipo, "nombre": nombre,
                            "url": url, "public_id": public_id},
                      timeout=10)
    r.raise_for_status()
    return r.json()[0]


def _del_media_record(public_id):
    requests.delete(_sb("media"),
                    params={"public_id": f"eq.{public_id}"},
                    headers=_sbh(), timeout=10)


# ─────────────────────── CLOUDINARY ───────────────────────

def _cld_subfolder(tipo):
    return {"imagen": "images", "video": "videos",
            "audio": "audio", "documento": "documentos"}[tipo]


def cld_upload(file_obj, tipo, nombre_base):
    """Sube a Cloudinary; retorna (secure_url, public_id)."""
    result = cloudinary.uploader.upload(
        file_obj,
        folder          = f"{CLD_FOLDER}/{_cld_subfolder(tipo)}",
        public_id       = nombre_base,
        resource_type   = _CLD_RES[tipo],
        overwrite       = False,
        unique_filename = True,
    )
    return result["secure_url"], result["public_id"]


def cld_delete(public_id, tipo):
    cloudinary.uploader.destroy(public_id, resource_type=_CLD_RES[tipo])


# ─────────────────────── UTILS ────────────────────────────

def sanitize_name(filename):
    raw = os.path.splitext(os.path.basename(filename))[0]
    raw = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9._-]", "_", raw)[:60].strip("_") or "archivo"


# ─────────────────────── RUTAS ────────────────────────────

@app.route("/")
def index():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return (
            "<h2 style='font-family:sans-serif;padding:2rem;color:#555'>"
            "Sitio en configuraci&oacute;n.<br>"
            "<small style='font-size:0.7em'>Configura las variables de entorno "
            "SUPABASE_URL y SUPABASE_KEY en Render.</small></h2>",
            503,
        )
    contenido = load_contenido()
    if not contenido:
        return (
            "<h2 style='font-family:sans-serif;padding:2rem;color:#555'>"
            "Contenido no encontrado en Supabase.<br>"
            "<small style='font-size:0.7em'>Ejecuta migrate.py o verifica que la tabla "
            "'contenido' tenga datos en Supabase.</small></h2>",
            503,
        )
    credits = {
        "content_role": CREDIT_CONTENT_ROLE,
        "content_name": CREDIT_CONTENT_NAME,
        "dev_role":     CREDIT_DEV_ROLE,
        "dev_name":     CREDIT_DEV_NAME,
        "project_name": PROJECT_NAME,
    }
    return render_template("index.html",
                           contenido=contenido,
                           images=get_images(),
                           credits=credits)


@app.route("/editar")
def editar():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return (
            "<h2 style='font-family:sans-serif;padding:2rem;color:#c00'>"
            "Variables de entorno no configuradas.<br>"
            "<small style='font-size:0.7em'>Necesitas SUPABASE_URL y SUPABASE_KEY en Render.</small></h2>",
            503,
        )
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
    data  = request.get_json(force=True)
    orden = data.get("orden", [])
    if not isinstance(orden, list):
        return jsonify({"ok": False, "error": "orden inválido"}), 400
    save_orden(orden)
    return jsonify({"ok": True})


@app.route("/subir-media", methods=["POST"])
def subir_media():
    tipo = request.form.get("tipo", "imagen")
    if tipo not in ALLOWED_MEDIA:
        return jsonify({"ok": False, "error": "tipo inválido"}), 400
    f = request.files.get("archivo")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "sin archivo"}), 400
    ext = os.path.splitext(f.filename)[1].lstrip(".").lower()
    if ext not in ALLOWED_MEDIA[tipo]:
        return jsonify({"ok": False, "error": f"extensión .{ext} no permitida"}), 400
    nombre_base = sanitize_name(f.filename)
    nombre      = nombre_base + "." + ext
    try:
        url, public_id = cld_upload(f, tipo, nombre_base)
        _add_media_record(tipo, nombre, url, public_id)
        if tipo == "imagen":
            orden = get_images()
            orden.append({"nombre": nombre, "url": url, "public_id": public_id})
            save_orden(orden)
        return jsonify({"ok": True, "url": url, "nombre": nombre, "public_id": public_id})
    except Exception as e:
        app.logger.error(f"subir-media: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/eliminar-media", methods=["POST"])
@app.route("/eliminar-imagen", methods=["POST"])   # alias para compatibilidad
def eliminar_media():
    data      = request.get_json(force=True)
    public_id = data.get("public_id", "")
    tipo      = data.get("tipo", "imagen")
    if not public_id or tipo not in _CLD_RES:
        return jsonify({"ok": False, "error": "datos inválidos"}), 400
    try:
        cld_delete(public_id, tipo)
        _del_media_record(public_id)
        if tipo == "imagen":
            orden = [img for img in get_images() if img.get("public_id") != public_id]
            save_orden(orden)
        return jsonify({"ok": True})
    except Exception as e:
        app.logger.error(f"eliminar-media: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
