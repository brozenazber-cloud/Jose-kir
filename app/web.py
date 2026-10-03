from flask import Flask, render_template
from pathlib import Path

from .config import SITE_TITLE
from . import db

BASE_DIR = Path(__file__).resolve().parent.parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)


@app.route("/")
def home():
    db.init()

    return render_template(
        "index.html",
        title=SITE_TITLE,
        products=db.products()
    )


def run():
    app.run(
        host="0.0.0.0",
        port=8080
    )
