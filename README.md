# AZBER SHOP — Railway Telegram Shop

A clean two-bot Telegram shop with an admin bot, manual wallet charging,
discount codes, featured configs, SQLite storage, and a modern web landing page.

## Railway

Create one Railway service from this repository.

Required variables:
- `BOT_TOKEN` — sales bot token
- `ADMIN_BOT_TOKEN` — admin bot token
- `ADMIN_IDS` — Telegram numeric IDs separated by commas

Optional:
- `SITE_TITLE`
- `CURRENCY`
- `PORT` (Railway normally provides PORT automatically)

The web service starts with `gunicorn web:app`.

## Important

Never put Telegram bot tokens directly in the repository.
All shop data is stored in `data/shop.db` at runtime.

## Commands

Sales bot:
- /start
- /shop
- /balance
- /help

Admin bot:
- /start
- /panel

From the admin panel you can add products, change prices, create discount
codes, create featured configs, review users and approve manual top-ups.

## Persistence

SQLite is intentionally simple for a starter Railway deployment. For a
multi-instance production setup, switch the DB layer to PostgreSQL.
