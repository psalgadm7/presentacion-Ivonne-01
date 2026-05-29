"""
run_local.py — Inicia la app Flask localmente con las credenciales del .env

Uso:
    py run_local.py

Lee el archivo .env de IVONNE/ y configura las variables de entorno
antes de arrancar Flask, sin depender del shell.
"""
import os
import re

# ── Ruta al .env con las credenciales ────────────────────────
ENV_FILE = r"C:\Users\psalg\OneDrive\Escritorio\IVONNE\.env"

# ── Parsear el .env (formato PowerShell: $env:VAR = "valor") ─
try:
    with open(ENV_FILE, encoding="utf-8") as f:
        for line in f:
            m = re.match(r'\$env:(\w+)\s*=\s*"(.*)"', line.strip())
            if m:
                os.environ[m.group(1)] = m.group(2)
    print(f"✔  Credenciales cargadas desde {ENV_FILE}")
    print(f"   SUPABASE_URL          : {os.environ.get('SUPABASE_URL','NO SET')}")
    print(f"   CLOUDINARY_CLOUD_NAME : {os.environ.get('CLOUDINARY_CLOUD_NAME','NO SET')}")
except FileNotFoundError:
    print(f"❌  No se encontró {ENV_FILE}")
    print("    Edita la variable ENV_FILE en run_local.py")
    raise SystemExit(1)

# ── Arrancar Flask ────────────────────────────────────────────
from app import app

port = int(os.environ.get("PORT", 5000))
print(f"\n🌐  Abre http://localhost:{port}\n")
app.run(host="0.0.0.0", port=port, debug=True)
