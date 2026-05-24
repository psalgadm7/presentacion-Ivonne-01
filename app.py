import os
from flask import Flask, render_template

app = Flask(__name__)

IMAGES_DIR = os.path.join(app.root_path, "static", "images")

def get_images():
    exts = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    try:
        files = sorted(
            f for f in os.listdir(IMAGES_DIR)
            if os.path.splitext(f)[1].lower() in exts
        )
    except FileNotFoundError:
        files = []
    return files

@app.route("/")
def index():
    return render_template("index.html", images=get_images())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
