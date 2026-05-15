import os
from flask import Flask, render_template, send_from_directory

app = Flask(__name__)

LAMINAS_DIR = os.path.join(os.path.dirname(__file__), "static", "images")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def get_images():
    images = []
    for filename in sorted(os.listdir(LAMINAS_DIR)):
        ext = os.path.splitext(filename)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            images.append(filename)
    return images


@app.route("/")
def index():
    images = get_images()
    return render_template("index.html", images=images)


@app.route("/img/<path:filename>")
def serve_image(filename):
    return send_from_directory(LAMINAS_DIR, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
