from flask import Flask, render_template
from .config import SITE_TITLE, PORT
from . import db
app=Flask(__name__,template_folder="../templates",static_folder="../static")
@app.route("/")
def home():
    db.init()
    return render_template("index.html",title=SITE_TITLE,products=db.products())
def run(): app.run(host="0.0.0.0",port=PORT)
