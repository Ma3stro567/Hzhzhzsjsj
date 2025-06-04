import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# === НАСТРОЙКИ ===
API_TOKEN = '7839295746:AAGIaQJtwsS3qX-Cfx7Tp_MFaTDd-MgXkCQ'
ADMIN_USERNAME = '@Ma3stro274'
ADMIN_ID = 5083696616 # Заменить на настоящий user_id админа
ADMIN_PASSWORD = '148852'

# === FSM ===
class AddOffer(StatesGroup):
    waiting_amount = State()
    waiting_price = State()

# === ИНИЦИАЛИЗАЦИЯ ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

conn = sqlite3.connect("stars_bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    verified INTEGER DEFAULT 0,
    deals INTEGER DEFAULT 0,
    blacklist INTEGER DEFAULT 0
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    price_per_star INTEGER
)""")
conn.commit()

# === УТИЛИТЫ ===
def is_verified(user_id):
    cursor.execute("SELECT verified FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row and row[0] == 1

def get_commission(user_id):
    return 5 if is_verified(user_id) else 10

def get_offer_limit(user_id):
    return 4 if is_verified(user_id) else 2

# === КНОПКИ ===
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🛍 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="➕ Добавить предложение", callback_data="add_offer")],
        [InlineKeyboardButton(text="🗑 Мои предложения", callback_data="my_offers")],
        [InlineKeyboardButton(text="🛠 Админ панель", callback_data="admin_panel")]
    ])

# === СТАРТ ===
@dp.message(CommandStart())
async def start(message: types.Message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (message.from_user.id, message.from_user.username))
    conn.commit()
    await message.answer("🌟 Добро пожаловать в маркетплейс звёзд!", reply_markup=main_menu())

# === КНОПКИ ===
@dp.callback_query(F.data == "profile")
async def show_profile(call: types.CallbackQuery):
    user_id = call.from_user.id
    cursor.execute("SELECT verified, deals FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    verified = "🟢" if row[0] else "❌"
    deals = row[1]
    commission = get_commission(user_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Как стать проверенным?", callback_data="how_to_verify")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])
    await call.message.edit_text(f"👤 Профиль\n\nЮзер: @{call.from_user.username}\nПроверенный: {verified}\nСделок: {deals}\nКомиссия: {commission}%", reply_markup=kb)

@dp.callback_query(F.data == "how_to_verify")
async def how_to_verify(call: types.CallbackQuery):
    await call.message.edit_text("🟢 Чтобы стать проверенным, нужно провести 10 успешных сделок через администратора.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]]))

@dp.callback_query(F.data == "shop")
async def show_shop(call: types.CallbackQuery):
    cursor.execute("""
        SELECT offers.id, users.username, offers.amount, offers.price_per_star, users.verified 
        FROM offers JOIN users ON offers.user_id = users.user_id
    """)
    offers = cursor.fetchall()
    if not offers:
        return await call.message.edit_text("🛍 Магазин пуст.", reply_markup=main_menu())

    buttons = []
    for offer_id, username, amount, price, verified in offers:
        label = f"{'🟢 ' if verified else ''}@{username}: {amount}⭐ по {price}₽"
        buttons.append([InlineKeyboardButton(text=label, url=f"https://t.me/{ADMIN_USERNAME[1:]}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    await call.message.edit_text("🛍 Все предложения:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "add_offer")
async def start_add_offer(call: types.CallbackQuery, state: FSMContext):
    cursor.execute("SELECT COUNT(*) FROM offers WHERE user_id=?", (call.from_user.id,))
    count = cursor.fetchone()[0]
    if count >= get_offer_limit(call.from_user.id):
        return await call.message.answer("⚠️ Превышен лимит предложений.")
    await call.message.answer("✍️ Введите количество звёзд:")
    await state.set_state(AddOffer.waiting_amount)

@dp.message(AddOffer.waiting_amount)
async def offer_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ Введите число.")
    await state.update_data(amount=int(message.text))
    await message.answer("💸 Введите цену за 1 звезду (₽):")
    await state.set_state(AddOffer.waiting_price)

@dp.message(AddOffer.waiting_price)
async def offer_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ Введите число.")
    data = await state.get_data()
    cursor.execute("INSERT INTO offers (user_id, amount, price_per_star) VALUES (?, ?, ?)",
                   (message.from_user.id, data['amount'], int(message.text)))
    conn.commit()
    await message.answer("✅ Предложение добавлено!", reply_markup=main_menu())
    await state.clear()

@dp.callback_query(F.data == "my_offers")
async def my_offers(call: types.CallbackQuery):
    cursor.execute("SELECT id, amount, price_per_star FROM offers WHERE user_id=?", (call.from_user.id,))
    offers = cursor.fetchall()
    if not offers:
        return await call.message.edit_text("У вас нет предложений.", reply_markup=main_menu())
    kb = []
    for offer_id, amount, price in offers:
        kb.append([InlineKeyboardButton(text=f"❌ Удалить {amount}⭐ по {price}₽", callback_data=f"del_{offer_id}")])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    await call.message.edit_text("Ваши предложения:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("del_"))
async def delete_offer(call: types.CallbackQuery):
    offer_id = int(call.data.split("_")[1])
    cursor.execute("DELETE FROM offers WHERE id=? AND user_id=?", (offer_id, call.from_user.id))
    conn.commit()
    await call.message.answer("✅ Удалено.", reply_markup=main_menu())

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.message.answer("⛔ Нет доступа.")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast")],
        [InlineKeyboardButton(text="✅ Сделать проверенным", callback_data="verify")],
        [InlineKeyboardButton(text="➕ Добавить сделку", callback_data="add_deal")],
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data="ban")]
    ])
    await call.message.edit_text("🛠 Админ панель:", reply_markup=kb)

@dp.callback_query(F.data == "verify")
async def verify_user(call: types.CallbackQuery):
    await call.message.answer("Введите user_id пользователя для проверки:")

    @dp.message()
    async def set_verified(msg: types.Message):
        cursor.execute("UPDATE users SET verified=1 WHERE user_id=?", (int(msg.text),))
        conn.commit()
        await msg.answer("✅ Сделан проверенным.")

@dp.callback_query(F.data == "add_deal")
async def add_deal(call: types.CallbackQuery):
    await call.message.answer("Введите user_id для добавления сделки:")

    @dp.message()
    async def add_one_deal(msg: types.Message):
        cursor.execute("UPDATE users SET deals = deals + 1 WHERE user_id=?", (int(msg.text),))
        conn.commit()
        await msg.answer("✅ Сделка добавлена.")

@dp.callback_query(F.data == "ban")
async def ban_user(call: types.CallbackQuery):
    await call.message.answer("Введите user_id для бана:")

    @dp.message()
    async def ban(msg: types.Message):
        cursor.execute("UPDATE users SET blacklist=1 WHERE user_id=?", (int(msg.text),))
        conn.commit()
        await msg.answer("🚫 Пользователь заблокирован.")

@dp.callback_query(F.data == "back")
async def go_back(call: types.CallbackQuery):
    await call.message.edit_text("🌟 Главное меню:", reply_markup=main_menu())

# === ЗАПУСК ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                       
