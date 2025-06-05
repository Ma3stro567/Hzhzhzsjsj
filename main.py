import telebot
from telebot import types

TOKEN = '7643851453:AAGpwz8K5gvAtqetX6Y8cYzh25ZinGDv_-g'
ADMIN_ID = 5083696616
ADMIN_USERNAME = '@Ma3stro274'
ADMIN_PANEL_PASSWORD = '148852'

bot = telebot.TeleBot(TOKEN)

users = {}
offers = []
blacklist = set()
admin_state = {}
edit_offer_state = {}
deal_add_state = {}
delete_offer_state = {}

def is_blacklisted(user_id):
    return user_id in blacklist

def user_offer_limit(user_id):
    verified = users.get(user_id, {}).get('verified', False)
    return 4 if verified else 2

def user_offer_count(user_id):
    return len([o for o in offers if o['user_id'] == user_id])

def get_commission(user_id):
    verified = users.get(user_id, {}).get('verified', False)
    return 5 if verified else 10

def get_star_limit(user_id):
    verified = users.get(user_id, {}).get('verified', False)
    return 1000 if verified else 500

def get_max_price(user_id):
    verified = users.get(user_id, {}).get('verified', False)
    return 10 if verified else 10

def show_main_menu(user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('🛒 Магазин', callback_data='shop'))
    markup.add(types.InlineKeyboardButton('📤 Продать звезды', callback_data='sell'))
    markup.add(types.InlineKeyboardButton('👤 Профиль', callback_data='profile'))
    bot.send_message(user_id, '⭐ Добро пожаловать в Ma3stro shop!', reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    if is_blacklisted(message.from_user.id):
        return

    user_id = message.from_user.id
    username = message.from_user.username or f"id{user_id}"

    if user_id not in users:
        users[user_id] = {'username': username, 'verified': False, 'deal_count': 0}

    show_main_menu(user_id)

@bot.callback_query_handler(func=lambda c: c.data == 'sell')
def sell(callback):
    user_id = callback.from_user.id
    if is_blacklisted(user_id): return
    if user_offer_count(user_id) >= user_offer_limit(user_id):
        bot.answer_callback_query(callback.id, '❌ Лимит предложений достигнут!')
        return
    msg = bot.send_message(user_id, '🌟 Введите количество звёзд (до лимита):')
    bot.register_next_step_handler(msg, process_stars)

def process_stars(message):
    try:
        stars = int(message.text)
        user_id = message.from_user.id
        if stars <= 0 or stars > get_star_limit(user_id):
            raise ValueError
        msg = bot.send_message(message.chat.id, '💸 Введите цену за 1 звезду (до 10₽):')
        bot.register_next_step_handler(msg, lambda m: process_price(m, stars))
    except:
        bot.send_message(message.chat.id, f'❌ Введите корректное число от 1 до {get_star_limit(message.from_user.id)}.')

def process_price(message, stars):
    try:
        price = float(message.text)
        user_id = message.from_user.id
        max_price = get_max_price(user_id)
        if price <= 0 or price > max_price: 
            bot.send_message(message.chat.id, f'❌ Цена должна быть от 0.1 до {max_price}₽')
            return
        username = users[user_id]['username']
        offers.append({'user_id': user_id, 'username': username, 'stars': stars, 'price': price})
        bot.send_message(user_id, '✅ Ваше предложение добавлено в магазин!')
    except:
        bot.send_message(message.chat.id, '❌ Введите корректную цену.')

@bot.callback_query_handler(func=lambda c: c.data == 'shop')
def shop(callback):
    user_id = callback.from_user.id
    if is_blacklisted(user_id): return

    if not offers:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
        bot.send_message(user_id, '❌ Предложений пока нет.', reply_markup=markup)
        return

    for offer in offers:
        verified = users.get(offer['user_id'], {}).get('verified', False)
        status = '🟢' if verified else '🔘'
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('💬 Купить (через админа)', url=f"https://t.me/{ADMIN_USERNAME[1:]}"))
        bot.send_message(user_id, f"{status} @{offer['username']} | {offer['stars']} звёзд по {offer['price']}₽", reply_markup=markup)

    back_markup = types.InlineKeyboardMarkup()
    back_markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
    bot.send_message(user_id, "\u200b", reply_markup=back_markup)

@bot.callback_query_handler(func=lambda c: c.data == 'profile')
def profile(callback):
    user_id = callback.from_user.id
    user = users[user_id]
    status = '🟢 Проверенный' if user['verified'] else '🔘 Обычный'
    commission = get_commission(user_id)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('❓ Как стать проверенным?', callback_data='howto_verify'))
    user_offers = [o for o in offers if o['user_id'] == user_id]
    for i, offer in enumerate(user_offers):
        markup.add(types.InlineKeyboardButton(f'✏️ Изменить {i+1}', callback_data=f'edit_{i}'))
    markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))

    bot.send_message(user_id,
                     f"👤 @{user['username']}\n💼 Сделок: {user['deal_count']}\n💸 Комиссия: {commission}%\n🔖 Статус: {status}",
                     reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('edit_'))
def edit_offer(callback):
    user_id = callback.from_user.id
    index = int(callback.data.split('_')[1])
    user_offers = [o for o in offers if o['user_id'] == user_id]
    if index >= len(user_offers): return
    edit_offer_state[user_id] = user_offers[index]
    msg = bot.send_message(user_id, '✏️ Введите новое количество звёзд:')
    bot.register_next_step_handler(msg, save_edited_offer)

def save_edited_offer(message):
    user_id = message.from_user.id
    try:
        new_stars = int(message.text)
        if new_stars <= 0 or new_stars > get_star_limit(user_id):
            raise ValueError
        for offer in offers:
            if offer == edit_offer_state.get(user_id):
                offer['stars'] = new_stars
                bot.send_message(user_id, '✅ Обновлено!')
    except:
        bot.send_message(user_id, f'❌ Ошибка. Введите число от 1 до {get_star_limit(user_id)}.')

@bot.callback_query_handler(func=lambda c: c.data == 'howto_verify')
def howto_verify(callback):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
    bot.send_message(callback.from_user.id, '✅ Проведите 10 успешных сделок и вы станете проверенным!', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == 'back_to_main')
def back_to_main(callback):
    show_main_menu(callback.from_user.id)

@bot.message_handler(commands=['adminpanel'])
def admin_panel(message):
    if str(message.text).endswith(ADMIN_PANEL_PASSWORD):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('📊 Статистика', callback_data='stats'))
        markup.add(types.InlineKeyboardButton('📬 Рассылка', callback_data='broadcast'))
        markup.add(types.InlineKeyboardButton('✅ Проверить пользователя', callback_data='verify'))
        markup.add(types.InlineKeyboardButton('⛔ ЧС', callback_data='blacklist'))
        markup.add(types.InlineKeyboardButton('➕ Сделка', callback_data='deal_add'))
        markup.add(types.InlineKeyboardButton('🗑 Удалить предложение', callback_data='del_offer'))
        markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
        bot.send_message(message.chat.id, '🔐 Админ панель:', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == 'stats')
def show_stats(callback):
    total_users = len(users)
    verified_users = len([u for u in users.values() if u['verified']])
    total_deals = sum(u['deal_count'] for u in users.values())
    total_offers = len(offers)
    blacklisted_users = len(blacklist)
    
    stats_text = f"""📊 **Статистика бота**

👥 **Пользователи:**
├ 🔢 Всего: {total_users}
├ 🟢 Проверенных: {verified_users}
├ 🔘 Обычных: {total_users - verified_users}
└ 🚫 В ЧС: {blacklisted_users}

💼 **Сделки:**
└ 📈 Всего проведено: {total_deals}

🛒 **Предложения:**
└ 📦 Активных: {total_offers}

⭐ **Лимиты:**
├ 🔢 Звёзд (обычные): 500
├ 🔢 Звёзд (проверенные): 1000
└ 💰 Максимальная цена: 10₽"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
    bot.send_message(callback.from_user.id, stats_text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data == 'broadcast')
def broadcast(callback):
    msg = bot.send_message(callback.from_user.id, '📨 Введите текст рассылки:')
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    for uid in users:
        try:
            bot.send_message(uid, message.text)
        except:
            continue

@bot.callback_query_handler(func=lambda c: c.data == 'verify')
def ask_verify(callback):
    msg = bot.send_message(callback.from_user.id, '🆔 Введите ID пользователя для проверки:')
    bot.register_next_step_handler(msg, verify_user)

def verify_user(message):
    try:
        uid = int(message.text)
        if uid in users:
            users[uid]['verified'] = True
            bot.send_message(uid, '🎉 Вы стали проверенным пользователем!')
            bot.send_message(message.chat.id, '✅ Успешно.')
    except:
        bot.send_message(message.chat.id, '❌ Ошибка.')

@bot.callback_query_handler(func=lambda c: c.data == 'blacklist')
def ask_blacklist(callback):
    msg = bot.send_message(callback.from_user.id, '🆔 Введите ID пользователя для ЧС:')
    bot.register_next_step_handler(msg, add_to_blacklist)

def add_to_blacklist(message):
    try:
        uid = int(message.text)
        blacklist.add(uid)
        bot.send_message(uid, '🚫 Вы занесены в ЧС.')
        bot.send_message(message.chat.id, '✅ Добавлен в ЧС.')
    except:
        bot.send_message(message.chat.id, '❌ Ошибка.')

@bot.callback_query_handler(func=lambda c: c.data == 'deal_add')
def ask_deal_add(callback):
    msg = bot.send_message(callback.from_user.id, '🆔 Введите ID пользователя кому добавить сделку:')
    bot.register_next_step_handler(msg, add_deal)

def add_deal(message):
    try:
        uid = int(message.text)
        users[uid]['deal_count'] += 1
        if users[uid]['deal_count'] >= 10 and not users[uid]['verified']:
            users[uid]['verified'] = True
            bot.send_message(uid, '🎉 Вы стали проверенным пользователем!')
        bot.send_message(message.chat.id, '✅ Сделка добавлена.')
    except:
        bot.send_message(message.chat.id, '❌ Ошибка.')

@bot.callback_query_handler(func=lambda c: c.data == 'del_offer')
def delete_offer(callback):
    for i, offer in enumerate(offers):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('🗑 Удалить', callback_data=f'del_{i}'))
        bot.send_message(callback.from_user.id, f"@{offer['username']} | {offer['stars']} ⭐ по {offer['price']}₽", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('del_'))
def do_delete_offer(callback):
    index = int(callback.data.split('_')[1])
    if 0 <= index < len(offers):
        offers.pop(index)
        bot.send_message(callback.from_user.id, '✅ Удалено.')

print("✅ Бот запущен")
bot.polling(none_stop=True)
bot.remove_webhook()
