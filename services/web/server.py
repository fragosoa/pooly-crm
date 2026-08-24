"""
Minimal static file server for the Pooly CRM frontend.

No build step (the app is a single self-contained index.html, same as the
original prototype). This just serves that file, injecting the API/auth
URLs from environment variables at startup so the same index.html works
unchanged across local dev, staging and production.
"""
import os
from flask import Flask, Response

app = Flask(__name__)

_INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


def _render_index():
    with open(_INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__CRM_API_URL__", os.getenv("CRM_API_URL", "http://localhost:8081"))
    html = html.replace("__POOLY_CORE_URL__", os.getenv("POOLY_CORE_URL", "http://localhost:8080"))
    return html


# Rendered once at startup — envs don't change at runtime on Railway.
_RENDERED_HTML = _render_index()


@app.route("/")
@app.route("/<path:_unused>")  # single-page app: any path serves the same shell
def index(_unused=None):
    return Response(_RENDERED_HTML, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8082)), debug=True)
