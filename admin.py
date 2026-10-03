from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

import db
from config import ADMIN_BOT_TOKEN, ADMIN_IDS, CURRENCY


dp = Dispatcher()


class ProductState(StatesGroup):
    name = State()
    description = State()
    price = State()


class DiscountState(StatesGroup):
    code = State()
    percent = State()


def admin(user_id):
    return user_id in ADMIN_IDS


def panel():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 محصولات",
                    callback_data="products"
                ),
                InlineKeyboardButton(
                    text="➕ محصول جدید",
                    callback_data="add_product"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏷 کد تخفیف",
                    callback_data="discount"
                ),
                InlineKeyboardButton(
                    text="💳 شارژها",
                    callback_data="topups"
                )
            ]
        ]
    )


@dp.message(Command("start"))
async def start(message: Message):
    if not admin(message.from_user.id):
        await message.answer(
            "⛔ دسترسی ندارید."
        )
        return

    await message.answer(
        "👑 پنل مدیریت AZBER",
        reply_markup=panel()
    )


@dp.message(Command("panel"))
async def panel_command(message: Message):
    if not admin(message.from_user.id):
        await message.answer(
            "⛔ دسترسی ندارید."
        )
        return

    await message.answer(
        "👑 پنل مدیریت",
        reply_markup=panel()
    )


@dp.callback_query(F.data == "products")
async def products(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True
        )
        return

    await callback.answer()

    rows = db.get_products()

    text = "📦 محصولات:\n\n"

    for row in rows:
        text += (
            f"#{row[0]} — {row[1]}\n"
            f"💰 {row[3]:,} {CURRENCY}\n"
            f"📦 {row[4]}\n\n"
        )

    await callback.message.answer(text)


@dp.callback_query(F.data == "add_product")
async def add_product(
    callback: CallbackQuery,
    state: FSMContext
):
    if not admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True
        )
        return

    await callback.answer()

    await state.set_state(
        ProductState.name
    )

    await callback.message.answer(
        "📦 نام محصول:"
    )


@dp.message(ProductState.name)
async def product_name(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        name=message.text
    )

    await state.set_state(
        ProductState.description
    )

    await message.answer(
        "📝 توضیحات محصول:"
    )


@dp.message(ProductState.description)
async def product_description(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        description=message.text
    )

    await state.set_state(
        ProductState.price
    )

    await message.answer(
        "💰 قیمت محصول:"
    )


@dp.message(ProductState.price)
async def product_price(
    message: Message,
    state: FSMContext
):
    value = message.text.replace(",", "").strip()

    if not value.isdigit():
        await message.answer(
            "❌ قیمت باید عدد باشد."
        )
        return

    data = await state.get_data()

    db.add_product(
        data["name"],
        data["description"],
        int(value)
    )

    await state.clear()

    await message.answer(
        "✅ محصول ساخته شد.",
        reply_markup=panel()
    )


@dp.callback_query(F.data == "discount")
async def discount(
    callback: CallbackQuery,
    state: FSMContext
):
    if not admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True
        )
        return

    await callback.answer()

    await state.set_state(
        DiscountState.code
    )

    await callback.message.answer(
        "🏷 کد تخفیف:"
    )


@dp.message(DiscountState.code)
async def discount_code(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        code=message.text.strip().upper()
    )

    await state.set_state(
        DiscountState.percent
    )

    await message.answer(
        "📉 درصد تخفیف:"
    )


@dp.message(DiscountState.percent)
async def discount_percent(
    message: Message,
    state: FSMContext
):
    value = message.text.strip()

    if not value.isdigit():
        await message.answer(
            "❌ فقط عدد وارد کنید."
        )
        return

    percent = int(value)

    if percent < 1 or percent > 100:
        await message.answer(
            "❌ عدد باید بین 1 تا 100 باشد."
        )
        return

    data = await state.get_data()

    db.add_discount(
        data["code"],
        percent
    )

    await state.clear()

    await message.answer(
        "✅ کد تخفیف ساخته شد.\n\n"
        f"🏷 {data['code']}\n"
        f"📉 {percent}%"
    )


@dp.callback_query(F.data == "topups")
async def topups(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True
        )
        return

    await callback.answer()

    rows = db.get_pending_topups()

    if not rows:
        await callback.message.answer(
            "✅ شارژ در انتظاری نیست."
        )
        return

    for row in rows:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ تایید",
                        callback_data=f"approve:{row[0]}"
                    ),
                    InlineKeyboardButton(
                        text="❌ رد",
                        callback_data=f"reject:{row[0]}"
                    )
                ]
            ]
        )

        await callback.message.answer(
            "💳 درخواست شارژ\n\n"
            f"🆔 #{row[0]}\n"
            f"👤 {row[1]}\n"
            f"💰 {row[2]:,} {CURRENCY}",
            reply_markup=keyboard
        )


@dp.callback_query(F.data.startswith("approve:"))
async def approve(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True
        )
        return

    topup_id = int(
        callback.data.split(":")[1]
    )

    row = db.approve_topup(
        topup_id
    )

    if not row:
        await callback.answer(
            "قبلاً بررسی شده.",
            show_alert=True
        )
        return

    await callback.answer(
        "تایید شد."
    )

    await callback.message.edit_text(
        callback.message.text +
        "\n\n✅ تایید شد."
    )


@dp.callback_query(F.data.startswith("reject:"))
async def reject(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True
        )
        return

    topup_id = int(
        callback.data.split(":")[1]
    )

    row = db.reject_topup(
        topup_id
    )

    if not row:
        await callback.answer(
            "قبلاً بررسی شده.",
            show_alert=True
        )
        return

    await callback.answer(
        "رد شد."
    )

    await callback.message.edit_text(
        callback.message.text +
        "\n\n❌ رد شد."
    )


async def main():
    if not ADMIN_BOT_TOKEN:
        raise RuntimeError(
            "ADMIN_BOT_TOKEN تنظیم نشده است."
        )

    await dp.start_polling(
        Bot(ADMIN_BOT_TOKEN)
)
