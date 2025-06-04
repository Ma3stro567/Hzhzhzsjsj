import telebot
from telebot import types

TOKEN = '7839295746:AAGIaQJtwsS3qX-Cfx7Tp_MFaTDd-MgXkCQ'
ADMIN_USERNAME = '@Ma3stro274'
ADMIN_ID = 5083696616  # Замените на настоящий ID админа
ADMIN_PASSWORD = '148852'

bot = telebot.TeleBot(TOKEN)

# Хранилище данных
users = {}
offers = []
blacklist = set()
verified = set()
deal_count = {}
commission_data = {}
MAX_OFFERS = {"verified": 4, "unverified": 2}

def is_verified(user_id):
    return user_id in verified

def get_commission(user_id):
    return 5 if is_verified(user_id) else 10

def can_post_offer(user_id):
    user_offers = [o for o in offers if o["seller_id"] == user_id]
    limit = MAX_OFFERS["verified" if is_verified(user_id) else "unverified"]
    return len(user_offers) < limit

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    users[user_id] = message.from_user.username
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛒 Магазин", callback_data="shop"))
    markup.add(types.InlineKeyboardButton("➕ Продать звёзды", callback_data="sell"))
    markup.add(types.InlineKeyboardButton("👤 Профиль", callback_data="profile"))
    bot.send_message(user_id, "⭐ Добро пожаловать в бот по продаже звёзд!", reply_markup=markup)

@bot.message_handler(commands=["adminpanel"])
def admin_panel(message):
    if str(message.text).endswith(ADMIN_PASSWORD):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📬 Рассылка", callback_data="broadcast"))
        markup.add(types.InlineKeyboardButton("✅ Проверить пользователя", callback_data="verify"))
        markup.add(types.InlineKeyboardButton("⛔ ЧС", callback_data="blacklist"))
        bot.send_message(message.chat.id, "🎛 Панель администратора:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id

    if user_id in blacklist:
        bot.answer_callback_query(call.id, "Вы в черном списке.")
        return

    if call.data == "shop":
        if not offers:
            bot.send_message(user_id, "❌ Пока нет предложений.")
            return
        for offer in offers:
            username = users.get(offer["seller_id"], "неизвестно")
            verified_mark = "🟢" if offer["seller_id"] in verified else "🔘"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💬 Связаться", url=f"https://t.me/{ADMIN_USERNAME[1:]}"))
            bot.send_message(user_id, f"{verified_mark} @{username}\n"
                                      f"⭐ Кол-во: {offer['count']}\n"
                                      f"💰 Цена за звезду: {offer['price']}₽", reply_markup=markup)

    elif call.data == "sell":
        if not can_post_offer(user_id):
            bot.send_message(user_id, "⚠️ Превышен лимит предложений.")
            return
        msg = bot.send_message(user_id, "Введите количество звёзд:")
        bot.register_next_step_handler(msg, process_star_count)

    elif call.data == "profile":
        username = users.get(user_id, "неизвестно")
        verified_mark = "🟢" if user_id in verified else "🔘"
        deals = deal_count.get(user_id, 0)
        comm = get_commission(user_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❓ Как стать проверенным?", callback_data="how_verify"))
        bot.send_message(user_id, f"{verified_mark} @{username}\n"
                                  f"✅ Сделок: {deals}\n"
                                  f"💸 Комиссия: {comm}%", reply_markup=markup)

    elif call.data == "how_verify":
        bot.send_message(user_id, "Чтобы стать проверенным, нужно успешно провести 10 сделок 💼")

    elif call.data == "broadcast":
        msg = bot.send_message(user_id, "Введите текст для рассылки:")
        bot.register_next_step_handler(msg, process_broadcast)

    elif call.data == "verify":
        msg = bot.send_message(user_id, "Введите ID пользователя для проверки:")
        bot.register_next_step_handler(msg, lambda m: verify_user(m))

    elif call.data == "blacklist":
        msg = bot.send_message(user_id, "Введите ID пользователя для ЧС:")
        bot.register_next_step_handler(msg, lambda m: blacklist_user(m))

def process_star_count(message):
    user_id = message.from_user.id
    try:
        count = int(message.text)
        msg = bot.send_message(user_id, "Введите цену за одну звезду (в ₽):")
        bot.register_next_step_handler(msg, lambda m: process_price(m, count))
    except:
        bot.send_message(user_id, "❌ Ошибка ввода. Попробуйте снова.")

def process_price(message, count):
    user_id = message.from_user.id
    try:
        price = float(message.text)
        offers.append({"seller_id": user_id, "count": count, "price": price})
        bot.send_message(user_id, "✅ Ваше предложение добавлено в магазин!")
    except:
        bot.send_message(user_id, "❌ Неверный формат цены.")

def process_broadcast(message):
    text = message.text
    for uid in users:
        try:
            bot.send_message(uid, f"📢 {text}")
        except:
            continue
    bot.send_message(message.chat.id, "✅ Рассылка завершена!")

def verify_user(message):
    try:
        uid = int(message.text)
        verified.add(uid)
        bot.send_message(message.chat.id, f"✅ Пользователь {uid} теперь проверен.")
    except:
        bot.send_message(message.chat.id, "❌ Неверный ID.")

def blacklist_user(message):
    try:
        uid = int(message.text)
        blacklist.add(uid)
        bot.send_message(message.chat.id, f"⛔ Пользователь {uid} добавлен в ЧС.")
    except:
        bot.send_message(message.chat.id, "❌ Неверный ID.")

print("Бот запущен...")
bot.polling()
