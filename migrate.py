"""
migrate.py — Migración one-time: archivos locales → Cloudinary + Supabase

Ejecutar LOCALMENTE (con Python 3.x) antes del primer deploy con el nuevo código:

  pip install cloudinary requests
  python migrate.py

Requiere las siguientes variables de entorno (o editarlas directamente aquí):
  CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
  CLOUDINARY_FOLDER   (default: plena)
  SUPABASE_URL, SUPABASE_KEY

Qué hace:
  1. Sube todas las imágenes de content/images/ a Cloudinary
  2. Sube videos, audio y documentos de sus carpetas a Cloudinary
  3. Reemplaza las URLs /content/... en contenido.json por URLs de Cloudinary
  4. Sube el contenido.json actualizado a Supabase
  5. Guarda el orden de imágenes en Supabase
  6. Registra todos los archivos subidos en la tabla media de Supabase
"""

import os
import re
import json
import unicodedata

import requests
import cloudinary
import cloudinary.uploader

# ── Configuración ─────────────────────────────────────────────
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY    = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
CLD_FOLDER            = os.environ.get("CLOUDINARY_FOLDER", "plena")
SUPABASE_URL          = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY          = os.environ.get("SUPABASE_KEY", "")

cloudinary.config(
    cloud_name = CLOUDINARY_CLOUD_NAME,
    api_key    = CLOUDINARY_API_KEY,
    api_secret = CLOUDINARY_API_SECRET,
    secure     = True,
)

SB_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
}

CONTENT_DIR    = os.path.join(os.path.dirname(__file__), "content")
CONTENIDO_FILE = os.path.join(CONTENT_DIR, "contenido.json")

# Mapeo subcarpeta local → resource_type de Cloudinary
CLD_RES = {
    "images":     "image",
    "videos":     "video",
    "audio":      "video",
    "documentos": "raw",
}

TIPO_MAP = {
    "images":     "imagen",
    "videos":     "video",
    "audio":      "audio",
    "documentos": "documento",
}

IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def sanitize(filename):
    raw = os.path.splitext(os.path.basename(filename))[0]
    raw = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9._-]", "_", raw)[:60].strip("_") or "archivo"


def sb(table):
    return f"{SUPABASE_URL}/rest/v1/{table}"


def upload_to_cloudinary(local_path, subfolder):
    """Sube un archivo y retorna (secure_url, public_id)."""
    resource_type = CLD_RES[subfolder]
    nombre_base   = sanitize(local_path)
    with open(local_path, "rb") as f:
        result = cloudinary.uploader.upload(
            f,
            folder          = f"{CLD_FOLDER}/{subfolder}",
            public_id       = nombre_base,
            resource_type   = resource_type,
            overwrite       = True,
        )
    return result["secure_url"], result["public_id"]


def sb_upsert_contenido(data):
    r = requests.get(sb("contenido"), params={"id": "eq.1"}, headers=SB_HEADERS)
    if r.json():
        requests.patch(sb("contenido"),
                       params={"id": "eq.1"},
                       headers={**SB_HEADERS, "Prefer": "return=minimal"},
                       json={"data": data}, timeout=15)
    else:
        requests.post(sb("contenido"),
                      headers={**SB_HEADERS, "Prefer": "return=minimal"},
                      json={"id": 1, "data": data}, timeout=15)


def sb_upsert_orden(orden):
    r = requests.get(sb("imagen_orden"), params={"id": "eq.1"}, headers=SB_HEADERS)
    if r.json():
        requests.patch(sb("imagen_orden"),
                       params={"id": "eq.1"},
                       headers={**SB_HEADERS, "Prefer": "return=minimal"},
                       json={"orden": orden}, timeout=15)
    else:
        requests.post(sb("imagen_orden"),
                      headers={**SB_HEADERS, "Prefer": "return=minimal"},
                      json={"id": 1, "orden": orden}, timeout=15)


def sb_add_media(tipo, nombre, url, public_id):
    requests.post(sb("media"),
                  headers={**SB_HEADERS, "Prefer": "resolution=ignore-duplicates"},
                  json={"tipo": tipo, "nombre": nombre, "url": url, "public_id": public_id},
                  timeout=15)


def migrate():
    print("=" * 55)
    print("  MIGRACIÓN: Archivos locales → Cloudinary + Supabase")
    print("=" * 55)

    if not CLOUDINARY_CLOUD_NAME or not SUPABASE_URL:
        print("\n❌  ERROR: Faltan variables de entorno.")
        print("     Configura CLOUDINARY_* y SUPABASE_* antes de ejecutar.")
        return

    # ── Cargar contenido.json local ───────────────────────────
    with open(CONTENIDO_FILE, encoding="utf-8") as f:
        contenido = json.load(f)
    contenido_str = json.dumps(contenido)   # para reemplazos de URL

    # ── 1. Subir imágenes y construir orden ───────────────────
    images_dir = os.path.join(CONTENT_DIR, "images")
    orden_file = os.path.join(images_dir, "orden.json")
    orden_local = []
    if os.path.exists(orden_file):
        with open(orden_file, encoding="utf-8") as f:
            orden_local = json.load(f)

    try:
        all_imgs = {fi for fi in os.listdir(images_dir)
                    if os.path.splitext(fi)[1].lower() in IMG_EXTS}
    except FileNotFoundError:
        all_imgs = set()

    ordered = [fi for fi in orden_local if fi in all_imgs]
    rest    = sorted(all_imgs - set(ordered))
    all_imgs_ordered = ordered + rest

    new_orden  = []
    url_map    = {}   # /content/... → cloudinary_url

    print(f"\n📸  Imágenes ({len(all_imgs_ordered)}):")
    for nombre in all_imgs_ordered:
        local_path = os.path.join(images_dir, nombre)
        url, public_id = upload_to_cloudinary(local_path, "images")
        new_orden.append({"nombre": nombre, "url": url, "public_id": public_id})
        url_map[f"/content/images/{nombre}"] = url
        sb_add_media("imagen", nombre, url, public_id)
        print(f"  ✔ {nombre}")

    # ── 2. Subir video, audio, documentos ─────────────────────
    for subfolder in ("videos", "audio", "documentos"):
        folder_path = os.path.join(CONTENT_DIR, subfolder)
        if not os.path.exists(folder_path):
            continue
        files = [fi for fi in os.listdir(folder_path) if not fi.startswith(".")]
        tipo  = TIPO_MAP[subfolder]
        print(f"\n📁  {subfolder} ({len(files)}):")
        for nombre in files:
            local_path = os.path.join(folder_path, nombre)
            url, public_id = upload_to_cloudinary(local_path, subfolder)
            url_map[f"/content/{subfolder}/{nombre}"] = url
            sb_add_media(tipo, nombre, url, public_id)
            print(f"  ✔ {nombre}")

    # ── 3. Actualizar URLs en contenido.json ──────────────────
    print(f"\n🔄  Reemplazando {len(url_map)} URLs en contenido.json…")
    for old, new in url_map.items():
        contenido_str = contenido_str.replace(old, new)
    contenido_updated = json.loads(contenido_str)

    # ── 4. Guardar en Supabase ────────────────────────────────
    print("\n☁️   Guardando contenido en Supabase…")
    sb_upsert_contenido(contenido_updated)
    print("  ✔ contenido → Supabase")

    print("☁️   Guardando orden de imágenes en Supabase…")
    sb_upsert_orden(new_orden)
    print("  ✔ orden de imágenes → Supabase")

    print("\n" + "=" * 55)
    print("  ✅  MIGRACIÓN COMPLETADA")
    print("=" * 55)
    print(f"\n  Imágenes subidas  : {len(new_orden)}")
    print(f"  URLs reemplazadas : {len(url_map)}")
    print("\nPróximos pasos:")
    print("  1. Configura las 6 variables de entorno en Render.com")
    print("  2. git add -A && git commit -m 'feat: migrate to cloudinary+supabase' && git push")
    print("  3. Render redeploya automáticamente — ¡listo!")


if __name__ == "__main__":
    migrate()
