from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .config import BOT_TOKEN, CURRENCY, ADMIN_IDS
from . import db

class Topup(StatesGroup):
    amount=State()
    receipt=State()

def kb_products():
    rows=[]
    for p in db.products():
        tag="⭐ " if p["featured"] else ""
        rows.append([InlineKeyboardButton(text=f"{tag}{p['name']} — {p['price']:,}", callback_data=f"buy:{p['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def main():
    if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN is missing")
    db.init()
    bot=Bot(BOT_TOKEN); dp=Dispatcher(storage=MemoryStorage())

    @dp.message(Command("start"))
    async def start(m:Message):
        db.user(m.from_user.id,m.from_user.username or "")
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 فروشگاه",callback_data="shop")],
            [InlineKeyboardButton(text="💳 موجودی",callback_data="bal"),
             InlineKeyboardButton(text="➕ شارژ دستی",callback_data="topup")],
        ])
        await m.answer("✨ به فروشگاه AZBER خوش آمدی!\n\nخرید سریع، مدیریت موجودی و کانفیگ‌های ویژه در دسترس توست.",reply_markup=kb)

    @dp.message(Command("shop"))
    async def shop(m:Message): await m.answer("🛍 محصولات فعال:",reply_markup=kb_products())

    @dp.message(Command("balance"))
    async def bal(m:Message): await m.answer(f"💰 موجودی شما: {db.balance(m.from_user.id):,} {CURRENCY}")

    @dp.callback_query(F.data=="shop")
    async def cshop(q:CallbackQuery): await q.message.edit_text("🛍 محصولات فعال:",reply_markup=kb_products()); await q.answer()

    @dp.callback_query(F.data=="bal")
    async def cbal(q:CallbackQuery): await q.answer(f"موجودی: {db.balance(q.from_user.id):,} {CURRENCY}",show_alert=True)

    @dp.callback_query(F.data=="topup")
    async def ct(q:CallbackQuery,state:FSMContext):
        await state.set_state(Topup.amount); await q.message.answer("💳 مبلغ شارژ را به تومان وارد کن:"); await q.answer()

    @dp.message(Topup.amount)
    async def ta(m:Message,state:FSMContext):
        if not m.text.isdigit() or int(m.text)<=0: return await m.answer("فقط یک مبلغ معتبر وارد کن.")
        await state.update_data(amount=int(m.text)); await state.set_state(Topup.receipt)
        await m.answer("📸 حالا عکس/رسید پرداخت را ارسال کن.")
    @dp.message(Topup.receipt)
    async def tr(m:Message,state:FSMContext):
        data=await state.get_data()
        receipt=m.photo[-1].file_id if m.photo else (m.text or "")
        db.add_topup(m.from_user.id,data["amount"],receipt)
        await state.clear(); await m.answer("✅ درخواست شارژ ثبت شد. پس از بررسی ادمین موجودی اضافه می‌شود.")
        for aid in ADMIN_IDS:
            try: await bot.send_message(aid,f"🔔 شارژ جدید\nکاربر: {m.from_user.id}\nمبلغ: {data['amount']:,} {CURRENCY}\n\nپنل ادمین را بررسی کن.")
            except: pass

    @dp.callback_query(F.data.startswith("buy:"))
    async def cbuy(q:CallbackQuery):
        pid=int(q.data.split(":")[1])
        ok,result=db.buy(q.from_user.id,pid)
        if not ok: return await q.answer(result,show_alert=True)
        p,price=result
        await q.message.answer(f"🎉 خرید با موفقیت انجام شد!\n\n📦 {p['name']}\n💰 {price:,} {CURRENCY}\n\n{p['stock']}")
        await q.answer()
    await dp.start_polling(bot)
