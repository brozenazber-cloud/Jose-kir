from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .config import ADMIN_BOT_TOKEN, ADMIN_IDS, CURRENCY
from . import db

class AddProduct(StatesGroup):
    name=State(); desc=State(); price=State(); stock=State()
class AddDiscount(StatesGroup):
    code=State(); value=State(); uses=State()

def panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 محصولات",callback_data="products")],
        [InlineKeyboardButton(text="➕ افزودن محصول",callback_data="addproduct")],
        [InlineKeyboardButton(text="🎟 ساخت کد تخفیف",callback_data="discount")],
        [InlineKeyboardButton(text="💳 شارژهای در انتظار",callback_data="topups")],
    ])

async def main():
    if not ADMIN_BOT_TOKEN: raise RuntimeError("ADMIN_BOT_TOKEN is missing")
    db.init(); bot=Bot(ADMIN_BOT_TOKEN); dp=Dispatcher(storage=MemoryStorage())
    def allowed(m): return m.from_user.id in ADMIN_IDS

    @dp.message(Command("start","panel"))
    async def start(m:Message):
        if allowed(m): await m.answer("🛠 پنل مدیریت AZBER SHOP\n\nهمه تنظیمات اصلی از همین‌جا قابل مدیریت است.",reply_markup=panel())
        else: await m.answer("⛔ دسترسی ندارید.")

    @dp.callback_query(F.data=="products")
    async def products(q:CallbackQuery):
        if q.from_user.id not in ADMIN_IDS: return
        ps=db.products(False)
        txt="📦 محصولات:\n\n"+"\n".join(f"#{p['id']} • {p['name']} • {p['price']:,} • {'⭐ ویژه' if p['featured'] else 'عادی'}" for p in ps)
        await q.message.edit_text(txt,reply_markup=panel()); await q.answer()

    @dp.callback_query(F.data=="addproduct")
    async def ap(q:CallbackQuery,state:FSMContext):
        await state.set_state(AddProduct.name); await q.message.answer("نام محصول:"); await q.answer()
    @dp.message(AddProduct.name)
    async def ap1(m:Message,state:FSMContext): await state.update_data(name=m.text); await state.set_state(AddProduct.desc); await m.answer("توضیحات:")
    @dp.message(AddProduct.desc)
    async def ap2(m:Message,state:FSMContext): await state.update_data(desc=m.text); await state.set_state(AddProduct.price); await m.answer("قیمت:")
    @dp.message(AddProduct.price)
    async def ap3(m:Message,state:FSMContext):
        if not m.text.isdigit(): return await m.answer("قیمت باید عدد باشد.")
        await state.update_data(price=int(m.text)); await state.set_state(AddProduct.stock); await m.answer("محتوای تحویلی/کانفیگ:")
    @dp.message(AddProduct.stock)
    async def ap4(m:Message,state:FSMContext):
        d=await state.get_data(); db.add_product(d["name"],d["desc"],d["price"],m.text)
        await state.clear(); await m.answer("✅ محصول اضافه شد.",reply_markup=panel())

    @dp.callback_query(F.data=="discount")
    async def dc(q:CallbackQuery,state:FSMContext):
        await state.set_state(AddDiscount.code); await q.message.answer("کد تخفیف را بفرست:"); await q.answer()
    @dp.message(AddDiscount.code)
    async def dc1(m:Message,state:FSMContext): await state.update_data(code=m.text); await state.set_state(AddDiscount.value); await m.answer("درصد تخفیف را وارد کن (مثلاً 20):")
    @dp.message(AddDiscount.value)
    async def dc2(m:Message,state:FSMContext):
        if not m.text.isdigit(): return await m.answer("فقط عدد.")
        await state.update_data(value=int(m.text)); await state.set_state(AddDiscount.uses); await m.answer("تعداد استفاده:")
    @dp.message(AddDiscount.uses)
    async def dc3(m:Message,state:FSMContext):
        if not m.text.isdigit(): return await m.answer("فقط عدد.")
        d=await state.get_data(); db.add_discount(d["code"],d["value"],0,int(m.text))
        await state.clear(); await m.answer("🎟 کد تخفیف ساخته شد.",reply_markup=panel())

    @dp.callback_query(F.data=="topups")
    async def tops(q:CallbackQuery):
        if q.from_user.id not in ADMIN_IDS:return
        ts=db.pending_topups()
        if not ts: return await q.answer("درخواستی نیست.",show_alert=True)
        for t in ts:
            kb=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ تأیید",callback_data=f"ok:{t['id']}"),
                 InlineKeyboardButton(text="❌ رد",callback_data=f"no:{t['id']}")]])
            await q.message.answer(f"شارژ #{t['id']}\nکاربر: {t['user_id']}\nمبلغ: {t['amount']:,} {CURRENCY}\nرسید: {t['receipt']}",reply_markup=kb)
        await q.answer()

    @dp.callback_query(F.data.startswith(("ok:","no:")))
    async def approve(q:CallbackQuery):
        ok=q.data.startswith("ok:"); tid=int(q.data.split(":")[1]); r=db.topup(tid,ok)
        await q.answer("انجام شد." if r else "قبلاً پردازش شده.",show_alert=True)
        if r:
            try: await bot.send_message(r["user_id"],f"{'✅ شارژ تأیید شد' if ok else '❌ شارژ رد شد'}\nمبلغ: {r['amount']:,} {CURRENCY}")
            except: pass
    await dp.start_polling(bot)
