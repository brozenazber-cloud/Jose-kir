import asyncio
import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# =========================
# تنظیمات اولیه
# =========================

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("azber_shop")

MAIN_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN", "").strip()
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", "shop.db")

ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}

CARD_NUMBER = os.getenv("CARD_NUMBER", "").strip()
CARD_NAME = os.getenv("CARD_NAME", "").strip()
SUPPORT_USERNAME = os.getenv(
    "SUPPORT_USERNAME", "IBrOzen"
).strip().lstrip("@")

SERVER_ADDRESS = os.getenv(
    "SERVER_ADDRESS", "AzberSmp.ir"
).strip()

if not MAIN_BOT_TOKEN:
    raise RuntimeError("MAIN_BOT_TOKEN در Railway تنظیم نشده است.")

if not ADMIN_BOT_TOKEN:
    raise RuntimeError("ADMIN_BOT_TOKEN در Railway تنظیم نشده است.")

if not ADMIN_IDS:
    raise RuntimeError(
        "ADMIN_IDS باید شامل حداقل یک شناسه عددی تلگرام باشد."
    )

main_bot = Bot(
    token=MAIN_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

admin_bot = Bot(
    token=ADMIN_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

main_dp = Dispatcher(storage=MemoryStorage())
admin_dp = Dispatcher(storage=MemoryStorage())


# =========================
# دیتابیس
# =========================

DEFAULT_PRODUCTS = [
    (
        "vip",
        "rank",
        "VIP",
        100000,
        "رنک VIP و کیت دائمی دیاموند",
    ),
    (
        "legend",
        "rank",
        "LEGEND",
        150000,
        "کیت ندرایت، انچنت متوسط و دسترسی‌های "
        "/anvil، /craft و /enchantingtable",
    ),
    (
        "fly",
        "op",
        "قابلیت /fly",
        50000,
        "دسترسی به قابلیت پرواز",
    ),
    (
        "nick",
        "op",
        "قابلیت /nick",
        30000,
        "دسترسی به تغییر نام نمایشی",
    ),
    (
        "enderchest",
        "op",
        "قابلیت /enderchest",
        20000,
        "دسترسی به اندِرچست",
    ),
]


def connect_db():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect_db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_key TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                price INTEGER NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                minecraft_name TEXT NOT NULL,
                product_key TEXT NOT NULL,
                product_name TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'awaiting_receipt',
                receipt_file_id TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

        count = connection.execute(
            "SELECT COUNT(*) AS total FROM products"
        ).fetchone()["total"]

        if count == 0:
            connection.executemany(
                """
                INSERT INTO products
                (product_key, category, title, price, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                DEFAULT_PRODUCTS,
            )

        default_settings = {
            "card_number": CARD_NUMBER,
            "card_name": CARD_NAME,
            "support": SUPPORT_USERNAME,
            "server_address": SERVER_ADDRESS,
        }

        for key, value in default_settings.items():
            connection.execute(
                """
                INSERT OR IGNORE INTO settings (key, value)
                VALUES (?, ?)
                """,
                (key, value),
            )


def get_setting(key, default=""):
    with connect_db() as connection:
        row = connection.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
        ).fetchone()

    return row["value"] if row else default


def set_setting(key, value):
    with connect_db() as connection:
        connection.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, str(value)),
        )


def money(amount):
    return f"{int(amount):,}".replace(",", "٬")


def is_admin(user_id):
    return user_id in ADMIN_IDS


def safe_text(value):
    return escape(str(value or ""))


# =========================
# منوها
# =========================

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏆 رنک‌ها",
                    callback_data="category:rank",
                ),
                InlineKeyboardButton(
                    text="⚡ قابلیت‌های OP",
                    callback_data="category:op",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👤 پروفایل من",
                    callback_data="profile",
                ),
                InlineKeyboardButton(
                    text="🆘 پشتیبانی",
                    callback_data="support",
                ),
            ],
        ]
    )


def back_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ بازگشت به منو",
                    callback_data="home",
                )
            ]
        ]
    )


def products_keyboard(category):
    with connect_db() as connection:
        products = connection.execute(
            """
            SELECT product_key, title, price
            FROM products
            WHERE category = ? AND enabled = 1
            ORDER BY id
            """,
            (category,),
        ).fetchall()

    buttons = []

    for product in products:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{product['title']} — "
                        f"{money(product['price'])} تومان"
                    ),
                    callback_data=f"buy:{product['product_key']}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ بازگشت",
                callback_data="home",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =========================
# وضعیت خرید
# =========================

class Checkout(StatesGroup):
    minecraft_name = State()
    receipt = State()


# =========================
# ربات مشتری
# =========================

@main_dp.message(CommandStart())
async def customer_start(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "به فروشگاه <b>Azber SMP</b> خوش اومدی! 🎮\n\n"
        "از منو رنک یا قابلیت موردنظرت رو انتخاب کن.\n"
        "سفارش‌ها پس از بررسی پرداخت توسط ادمین تأیید می‌شن.",
        reply_markup=main_menu(),
    )


@main_dp.message(Command("cancel"))
async def customer_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "فرایند لغو شد.",
        reply_markup=main_menu(),
    )


@main_dp.callback_query(F.data == "home")
async def customer_home(
    call: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await call.message.edit_text(
        "منوی فروشگاه <b>Azber SMP</b>:",
        reply_markup=main_menu(),
    )
    await call.answer()


@main_dp.callback_query(F.data.startswith("category:"))
async def customer_category(call: CallbackQuery):
    category = call.data.split(":", 1)[1]

    if category not in ("rank", "op"):
        await call.answer("دسته‌بندی نامعتبر است.", show_alert=True)
        return

    title = "🏆 رنک‌ها" if category == "rank" else "⚡ قابلیت‌های OP"

    await call.message.edit_text(
        f"<b>{title}</b>\nمحصول موردنظرت رو انتخاب کن:",
        reply_markup=products_keyboard(category),
    )
    await call.answer()


@main_dp.callback_query(F.data == "profile")
async def customer_profile(call: CallbackQuery):
    with connect_db() as connection:
        total = connection.execute(
            "SELECT COUNT(*) AS total FROM orders WHERE user_id = ?",
            (call.from_user.id,),
        ).fetchone()["total"]

        orders = connection.execute(
            """
            SELECT id, product_name, status
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 5
            """,
            (call.from_user.id,),
        ).fetchall()

    status_names = {
        "awaiting_receipt": "منتظر رسید",
        "pending": "در انتظار بررسی",
        "approved": "تأیید شده",
        "rejected": "رد شده",
    }

    lines = [
        "👤 <b>پروفایل شما</b>",
        f"شناسه تلگرام: <code>{call.from_user.id}</code>",
        f"تعداد سفارش‌ها: {total}",
    ]

    if orders:
        lines.append("\n<b>آخرین سفارش‌ها:</b>")

        for order in orders:
            lines.append(
                f"#{order['id']} — {safe_text(order['product_name'])}"
                f" — {status_names.get(order['status'], 'نامشخص')}"
            )
    else:
        lines.append("\nهنوز سفارشی ثبت نکردی.")

    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=back_menu(),
    )
    await call.answer()


@main_dp.callback_query(F.data == "support")
async def customer_support(call: CallbackQuery):
    username = get_setting("support", SUPPORT_USERNAME).lstrip("@")

    await call.message.edit_text(
        f"🆘 برای پشتیبانی به @{safe_text(username)} پیام بده.",
        reply_markup=back_menu(),
    )
    await call.answer()


@main_dp.callback_query(F.data.startswith("buy:"))
async def customer_buy(
    call: CallbackQuery,
    state: FSMContext,
):
    product_key = call.data.split(":", 1)[1]

    with connect_db() as connection:
        product = connection.execute(
            """
            SELECT *
            FROM products
            WHERE product_key = ? AND enabled = 1
            """,
            (product_key,),
        ).fetchone()

    if not product:
        await call.answer(
            "این محصول در دسترس نیست.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.update_data(product_key=product_key)
    await state.set_state(Checkout.minecraft_name)

    await call.message.answer(
        f"محصول انتخاب‌شده: <b>{safe_text(product['title'])}</b>\n"
        f"قیمت: <b>{money(product['price'])} تومان</b>\n\n"
        "نام کاربری ماینکرفتت رو بفرست.\n"
        "نام باید ۳ تا ۱۶ کاراکتر انگلیسی، عدد یا _ داشته باشه.\n\n"
        "لغو: /cancel"
    )

    await call.answer()


@main_dp.message(Checkout.minecraft_name)
async def customer_minecraft_name(
    message: Message,
    state: FSMContext,
):
    minecraft_name = (message.text or "").strip()

    if not re.fullmatch(r"[A-Za-z0-9_]{3,16}", minecraft_name):
        await message.answer(
            "نام کاربری معتبر نیست.\n"
            "فقط حروف انگلیسی، عدد و _ با طول ۳ تا ۱۶ کاراکتر مجازه."
        )
        return

    data = await state.get_data()
    product_key = data.get("product_key")

    with connect_db() as connection:
        product = connection.execute(
            """
            SELECT *
            FROM products
            WHERE product_key = ? AND enabled = 1
            """,
            (product_key,),
        ).fetchone()

        if not product:
            await state.clear()
            await message.answer(
                "این محصول دیگر فعال نیست.",
                reply_markup=main_menu(),
            )
            return

        cursor = connection.execute(
            """
            INSERT INTO orders
            (
                user_id, username, minecraft_name,
                product_key, product_name, amount,
                status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.from_user.id,
                message.from_user.username,
                minecraft_name,
                product["product_key"],
                product["title"],
                product["price"],
                "awaiting_receipt",
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        order_id = cursor.lastrowid

    await state.update_data(
        order_id=order_id,
        minecraft_name=minecraft_name,
    )
    await state.set_state(Checkout.receipt)

    card_number = get_setting("card_number", CARD_NUMBER)
    card_name = get_setting("card_name", CARD_NAME)

    payment_details = ""

    if card_number:
        payment_details += (
            f"\nشماره کارت: <code>{safe_text(card_number)}</code>"
        )

        if card_name:
            payment_details += (
                f"\nبه نام: <b>{safe_text(card_name)}</b>"
            )
    else:
        payment_details = (
            "\nاطلاعات پرداخت هنوز تنظیم نشده است. "
            "قبل از پرداخت با پشتیبانی هماهنگ کن."
        )

    await message.answer(
        f"✅ سفارش <b>#{order_id}</b> ثبت شد.\n"
        f"محصول: {safe_text(product['title'])}\n"
        f"مبلغ: <b>{money(product['price'])} تومان</b>\n"
        f"نام ماینکرفت: <code>{safe_text(minecraft_name)}</code>"
        f"{payment_details}\n\n"
        "پس از پرداخت، تصویر رسید رو همین‌جا بفرست.\n"
        "رسید باید توسط ادمین بررسی بشه؛ ارسال عکس به‌تنهایی "
        "به معنی تأیید پرداخت نیست.\n\n"
        "لغو: /cancel"
    )


@main_dp.message(Checkout.receipt, F.photo)
async def customer_receipt(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await state.clear()
        await message.answer(
            "سفارش پیدا نشد؛ دوباره از منو شروع کن.",
            reply_markup=main_menu(),
        )
        return

    photo_id = message.photo[-1].file_id

    with connect_db() as connection:
        connection.execute(
            """
            UPDATE orders
            SET receipt_file_id = ?, status = 'pending'
            WHERE id = ? AND user_id = ?
              AND status = 'awaiting_receipt'
            """,
            (photo_id, order_id, message.from_user.id),
        )

        order = connection.execute(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()

    await state.clear()

    await message.answer(
        f"🧾 رسید سفارش #{order_id} دریافت شد.\n"
        "پس از بررسی ادمین، نتیجه رو همین‌جا دریافت می‌کنی.",
        reply_markup=main_menu(),
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید سفارش",
                    callback_data=f"order:approve:{order_id}",
                ),
                InlineKeyboardButton(
                    text="❌ رد سفارش",
                    callback_data=f"order:reject:{order_id}",
                ),
            ]
        ]
    )

    caption = (
        f"🧾 <b>رسید جدید — سفارش #{order_id}</b>\n"
        f"شناسه کاربر: <code>{order['user_id']}</code>\n"
        f"نام تلگرام: @{safe_text(order['username'] or 'ندارد')}\n"
        f"نام ماینکرفت: <code>{safe_text(order['minecraft_name'])}</code>\n"
        f"محصول: {safe_text(order['product_name'])}\n"
        f"مبلغ: {money(order['amount'])} تومان"
    )

    delivered = False

    for admin_id in ADMIN_IDS:
        try:
            await admin_bot.send_photo(
                chat_id=admin_id,
                photo=photo_id,
                caption=caption,
                reply_markup=keyboard,
            )
            delivered = True
        except Exception:
            logger.exception(
                "ارسال رسید به ادمین %s ناموفق بود",
                admin_id,
            )

    if not delivered:
        logger.error(
            "رسید سفارش %s به هیچ ادمینی تحویل نشد",
            order_id,
        )


@main_dp.message(Checkout.receipt)
async def customer_receipt_wrong_format(message: Message):
    await message.answer(
        "لطفاً تصویر رسید رو به‌صورت عکس بفرست.\n"
        "برای لغو سفارش /cancel رو بزن."
    )


# =========================
# ربات ادمین
# =========================

@admin_dp.message(CommandStart())
async def admin_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ دسترسی ندارید.")
        return

    await message.answer(
        "🛠 <b>پنل مدیریت Azber SMP</b>\n\n"
        "/orders — آخرین سفارش‌ها\n"
        "/products — فهرست محصولات\n"
        "/enable KEY — فعال‌کردن محصول\n"
        "/disable KEY — غیرفعال‌کردن محصول\n"
        "/price KEY AMOUNT — تغییر قیمت\n"
        "/card NUMBER | NAME — تنظیم کارت\n"
        "/support USERNAME — تنظیم پشتیبانی\n"
        "/addproduct KEY CATEGORY TITLE | PRICE | DESCRIPTION\n\n"
        "دسته‌بندی محصول باید rank یا op باشد."
    )


@admin_dp.message(Command("orders"))
async def admin_orders(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ دسترسی ندارید.")
        return

    with connect_db() as connection:
        orders = connection.execute(
            "SELECT * FROM orders ORDER BY id DESC LIMIT 20"
        ).fetchall()

    if not orders:
        await message.answer("هنوز سفارشی ثبت نشده.")
        return

    status_names = {
        "awaiting_receipt": "منتظر رسید",
        "pending": "در انتظار بررسی",
        "approved": "تأیید شده",
        "rejected": "رد شده",
    }

    lines = ["<b>آخرین سفارش‌ها:</b>"]

    for order in orders:
        lines.append(
            f"#{order['id']} | {safe_text(order['product_name'])} | "
            f"{money(order['amount'])} تومان | "
            f"{safe_text(order['minecraft_name'])} | "
            f"{status_names.get(order['status'], 'نامشخص')}"
        )

    await message.answer("\n".join(lines))


@admin_dp.message(Command("products"))
async def admin_products(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ دسترسی ندارید.")
        return

    with connect_db() as connection:
        products = connection.execute(
            "SELECT * FROM products ORDER BY id"
        ).fetchall()

    lines = ["<b>فهرست محصولات:</b>"]

    for product in products:
        enabled = "فعال" if product["enabled"] else "غیرفعال"

        lines.append(
            f"<code>{safe_text(product['product_key'])}</code> | "
            f"{safe_text(product['title'])} | "
            f"{money(product['price'])} تومان | {enabled}"
        )

    await message.answer("\n".join(lines))


@admin_dp.message(Command("enable"))
async def admin_enable(message: Message):
    if not is_adm
