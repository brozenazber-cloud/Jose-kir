import asyncio

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
from config import BOT_TOKEN, ADMIN_IDS, CURRENCY


dp = Dispatcher()


class TopupState(StatesGroup):
    amount = State()
    receipt = State()


class BuyState(StatesGroup):
    discount = State()


def menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 فروشگاه",
                    callback_data="shop"
                ),
                InlineKeyboardButton(
                    text="💰 موجودی",
                    callback_data="balance"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 شارژ حساب",
                    callback_data="topup"
                )
            ]
        ]
    )


@dp.message(Command("start"))
async def start(message: Message):
    db.create_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.first_name or ""
    )

    await message.answer(
        "🌟 به فروشگاه AZBER خوش آمدید!\n\n"
        "از منوی زیر انتخاب کنید:",
        reply_markup=menu()
    )


@dp.callback_query(F.data == "shop")
async def shop(callback: CallbackQuery):
    await callback.answer()

    products = db.get_products()

    if not products:
        await callback.message.answer(
            "❌ محصولی وجود ندارد."
        )
        return

    for product in products:
        text = (
            f"✨ {product[1]}\n\n"
            f"📝 {product[2]}\n\n"
            f"💰 {product[3]:,} {CURRENCY}\n"
            f"📦 {product[4]}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛒 خرید",
                        callback_data=f"buy:{product[0]}"
                    )
                ]
            ]
        )

        await callback.message.answer(
            text,
            reply_markup=keyboard
        )


@dp.callback_query(F.data == "balance")
async def balance(callback: CallbackQuery):
    await callback.answer()

    amount = db.get_balance(
        callback.from_user.id
    )

    await callback.message.answer(
        f"💰 موجودی شما:\n\n"
        f"{amount:,} {CURRENCY}"
    )


@dp.callback_query(F.data == "topup")
async def topup(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    await state.set_state(
        TopupState.amount
    )

    await callback.message.answer(
        "💳 مبلغ شارژ را وارد کنید:\n\n"
        "مثال: 100000"
    )


@dp.message(TopupState.amount)
async def topup_amount(
    message: Message,
    state: FSMContext
):
    value = message.text.replace(",", "").strip()

    if not value.isdigit():
        await message.answer(
            "❌ فقط عدد وارد کنید."
        )
        return

    amount = int(value)

    if amount <= 0:
        await message.answer(
            "❌ مبلغ نامعتبر است."
        )
        return

    await state.update_data(
        amount=amount
    )

    await state.set_state(
        TopupState.receipt
    )

    await message.answer(
        "📸 حالا رسید پرداخت را ارسال کنید."
    )


@dp.message(TopupState.receipt)
async def topup_receipt(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    amount = data["amount"]

    receipt = message.text or ""

    if message.photo:
        receipt = message.photo[-1].file_id

    topup_id = db.create_topup(
        message.from_user.id,
        amount,
        receipt
    )

    await state.clear()

    await message.answer(
        "✅ درخواست شارژ ثبت شد.\n\n"
        f"💰 مبلغ: {amount:,} {CURRENCY}\n"
        f"🆔 درخواست: #{topup_id}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تایید",
                    callback_data=f"approve:{topup_id}"
                ),
                InlineKeyboardButton(
                    text="❌ رد",
                    callback_data=f"reject:{topup_id}"
                )
            ]
        ]
    )

    admin_text = (
        "🔔 شارژ جدید\n\n"
        f"🆔 #{topup_id}\n"
        f"👤 کاربر: {message.from_user.id}\n"
        f"💰 مبلغ: {amount:,} {CURRENCY}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                admin_text,
                reply_markup=keyboard
            )

            if message.photo:
                await message.bot.send_photo(
                    admin_id,
                    message.photo[-1].file_id
                )

        except Exception as error:
            print(
                "Admin notification error:",
                error
            )


@dp.callback_query(F.data.startswith("buy:"))
async def buy(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    product_id = int(
        callback.data.split(":")[1]
    )

    product = db.get_product(
        product_id
    )

    if not product:
        await callback.message.answer(
            "❌ محصول پیدا نشد."
        )
        return

    await state.update_data(
        product_id=product_id
    )

    await state.set_state(
        BuyState.discount
    )

    await callback.message.answer(
        f"🛒 {product[1]}\n\n"
        "اگر کد تخفیف دارید وارد کنید.\n"
        "اگر ندارید بنویسید:\n\n"
        "ندارم"
    )


@dp.message(BuyState.discount)
async def discount(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    code = message.text.strip()

    if code == "ندارم":
        code = None

    success, result = db.buy_product(
        message.from_user.id,
        data["product_id"],
        code
    )

    await state.clear()

    if not success:
        await message.answer(
            f"❌ {result}"
        )
        return

    await message.answer(
        "🎉 خرید موفق بود!\n\n"
        f"📦 {result['name']}\n"
        f"💰 {result['price']:,} {CURRENCY}\n"
        f"🏷 تخفیف: {result['discount']:,} {CURRENCY}"
    )


async def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    await dp.start_polling(
        Bot(BOT_TOKEN)
    )
