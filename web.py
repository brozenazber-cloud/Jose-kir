import asyncio
import threading

from flask import Flask, render_template

import db
from config import PORT, SITE_TITLE
from bot import main as shop_bot
from admin import main as admin_bot


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)


@app.route("/")
def home():
    products = db.get_products()

    return render_template(
        "index.html",
        title=SITE_TITLE,
        products=products
    )


def run_web():
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )


async def run_bots():
    await asyncio.gather(
        shop_bot(),
        admin_bot()
    )


if __name__ == "__main__":
    db.init()

    web_thread = threading.Thread(
        target=run_web,
        daemon=True
    )

    web_thread.start()

    asyncio.run(
        run_bots()
    )
