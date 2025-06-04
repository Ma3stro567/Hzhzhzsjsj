import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackContext, 
    CallbackQueryHandler, MessageHandler, Filters
)
import sqlite3
import re

# Настройка базы данных
conn = sqlite3.connect('star_market.db', check_same_thread=False)
cursor = conn.cursor()

# Создаем таблицы
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    is_verified BOOLEAN DEFAULT 0,
    deals_completed INTEGER DEFAULT 0,
    commission_rate REAL DEFAULT 10.0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS offers (
    offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    stars INTEGER,
    price REAL,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS blacklist (
    user_id INTEGER PRIMARY KEY,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
''')

conn.commit()

# Конфигурация бота
BOT_TOKEN = "7839295746:AAGIaQJtwsS3qX-Cfx7Tp_MFaTDd-MgXkCQ"
ADMIN_USERNAME = "@Ma3stro274"
ADMIN_PASSWORD = "148852"
COMMISSION_REGULAR = 10.0
COMMISSION_VERIFIED = 5.0

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
def get_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def create_user(user_id, username):
    if not get_user(user_id):
        cursor.execute(
            'INSERT INTO users (user_id, username) VALUES (?, ?)',
            (user_id, username)
        )
        conn.commit()

def get_offers_count(user_id):
    cursor.execute(
        'SELECT COUNT(*) FROM offers WHERE user_id = ? AND is_active = 1',
        (user_id,)
    )
    return cursor.fetchone()[0]

def get_offer_limit(user_id):
    user = get_user(user_id)
    return 4 if user and user[2] else 2  # 2 для обычных, 4 для проверенных

# ===================== ОСНОВНЫЕ КОМАНДЫ =====================
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    create_user(user.id, user.username)
    
    text = (
        f"🌟✨ *Добро пожаловать на Космический рынок звезд\!* ✨🌟\n\n"
        f"Здесь вы можете покупать и продавать звезды\! 💫\n\n"
        "🔹 *Продавайте звёзды* \- устанавливайте свою цену\n"
        "🔹 *Покупайте звёзды* \- находите лучшие предложения\n"
        "🔹 *Станьте проверенным продавцом* \- снизьте комиссию до 5\% ✅\n\n"
        "👇 *Используйте команды:*\n"
        "/addoffer \- добавить предложение\n"
        "/market \- посмотреть магазин\n"
        "/profile \- ваш профиль"
    )
    
    update.message.reply_text(text, parse_mode='MarkdownV2')

def add_offer(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Проверка черного списка
    cursor.execute('SELECT 1 FROM blacklist WHERE user_id = ?', (user_id,))
    if cursor.fetchone():
        update.message.reply_text("⛔ *Вы в черном списке!* ⛔", parse_mode='MarkdownV2')
        return
    
    # Проверка лимита предложений
    current_offers = get_offers_count(user_id)
    offer_limit = get_offer_limit(user_id)
    
    if current_offers >= offer_limit:
        update.message.reply_text(
            f"🚫 *Достигнут лимит предложений!*\n"
            f"Ваш лимит: *{offer_limit}* {'⭐' if offer_limit == 2 else '⭐⭐⭐⭐'}\n"
            f"Удалите одно из текущих предложений",
            parse_mode='MarkdownV2'
        )
        return
    
    # Запрос данных
    context.user_data['creating_offer'] = True
    update.message.reply_text(
        "✨ *Создаем новое предложение!* ✨\n\n"
        "Введите данные в формате:\n"
        "`<количество звезд> <цена за 1 звезду в рублях>`\n\n"
        "*Пример:* `5 1000`\n"
        "\(5 звезд по 1000 руб\. каждая\)",
        parse_mode='MarkdownV2'
    )

def handle_offer_input(update: Update, context: CallbackContext) -> None:
    if not context.user_data.get('creating_offer'):
        return
    
    user_id = update.effective_user.id
    try:
        stars, price = map(float, update.message.text.split())
        stars = int(stars)
        
        if stars <= 0 or price <= 0:
            raise ValueError("Отрицательные значения")
            
        # Проверка лимита
        current_offers = get_offers_count(user_id)
        offer_limit = get_offer_limit(user_id)
        
        if current_offers >= offer_limit:
            update.message.reply_text("❗ Лимит предложений изменился в процессе ввода!")
            return
        
        # Добавление в БД
        cursor.execute(
            'INSERT INTO offers (user_id, stars, price) VALUES (?, ?, ?)',
            (user_id, stars, price)
        )
        conn.commit()
        
        # Расчет с комиссией
        user = get_user(user_id)
        commission = COMMISSION_VERIFIED if user[2] else COMMISSION_REGULAR
        total = stars * price
        after_commission = total * (1 - commission/100)
        
        update.message.reply_text(
            f"✅ *Предложение добавлено!* ✅\n\n"
            f"⭐ *Звезд:* {stars}\n"
            f"💰 *Цена за звезду:* {price} руб\n"
            f"💎 *Итого:* {total:.2f} руб\n"
            f"📉 *Комиссия ({commission}%):* {total * commission/100:.2f} руб\n"
            f"💳 *Вы получите:* {after_commission:.2f} руб\n\n"
            f"Ваше предложение теперь видно в /market",
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания предложения: {e}")
        update.message.reply_text(
            "❌ *Некорректный формат!*\n"
            "Используйте: `<количество> <цена>`\n"
            "*Пример:* `3 1500`",
            parse_mode='MarkdownV2'
        )
    
    context.user_data['creating_offer'] = False

def market(update: Update, context: CallbackContext) -> None:
    cursor.execute('''
        SELECT o.offer_id, o.stars, o.price, u.username, u.is_verified 
        FROM offers o
        JOIN users u ON o.user_id = u.user_id
        WHERE o.is_active = 1
    ''')
    offers = cursor.fetchall()
    
    if not offers:
        update.message.reply_text("😔 *В магазине пока нет предложений!*", parse_mode='MarkdownV2')
        return
    
    text = "🛒 *Космический рынок звезд* 🪐\n\n"
    for offer in offers:
        status = "✅" if offer[4] else "❌"
        text += (
            f"{status} *Продавец:* @{offer[3]}\n"
            f"⭐ *Звезд:* {offer[1]}\n"
            f"💰 *Цена за штуку:* {offer[2]} руб\n"
            f"💎 *Сумма:* {offer[1] * offer[2]} руб\n"
            f"[Купить](https://t.me/{ADMIN_USERNAME[1:]}) | ID: `{offer[0]}`\n"
            "――――――――――――――――――――\n"
        )
    
    # Создаем инлайн-кнопки
    keyboard = [
        [InlineKeyboardButton("🔍 Обновить", callback_data='refresh_market')],
        [InlineKeyboardButton("👤 Мой профиль", callback_data='my_profile')]
    ]
    
    update.message.reply_text(
        text, 
        parse_mode='MarkdownV2',
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

def profile(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    db_user = get_user(user.id)
    
    if not db_user:
        create_user(user.id, user.username)
        db_user = get_user(user.id)
    
    is_verified = db_user[2]
    deals = db_user[3]
    commission = db_user[4]
    offer_count = get_offers_count(user.id)
    offer_limit = get_offer_limit(user.id)
    
    status = "✅ Проверенный" if is_verified else "❌ Непроверенный"
    status_emoji = "🟢" if is_verified else "🔴"
    
    text = (
        f"{status_emoji} *Ваш профиль*\n\n"
        f"👤 *Юзернейм:* @{user.username}\n"
        f"📛 *Статус:* {status}\n"
        f"📊 *Завершенные сделки:* {deals}\n"
        f"📉 *Комиссия:* {commission}%\n"
        f"📦 *Активные предложения:* {offer_count}/{offer_limit}\n\n"
    )
    
    # Кнопка "Как стать проверенным?"
    keyboard = [[
        InlineKeyboardButton("❓ Как стать проверенным?", callback_data='how_to_verify')
    ]]
    
    update.message.reply_text(
        text, 
        parse_mode='MarkdownV2',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===================== АДМИН-ПАНЕЛЬ =====================
def admin_panel(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    text = "🔐 *Введите пароль для доступа к админ-панели:*"
    context.user_data['awaiting_password'] = True
    update.message.reply_text(text, parse_mode='MarkdownV2')

def handle_admin_password(update: Update, context: CallbackContext) -> None:
    if not context.user_data.get('awaiting_password'):
        return
        
    if update.message.text == ADMIN_PASSWORD:
        # Показать админ-меню
        keyboard = [
            [InlineKeyboardButton("📢 Сделать рассылку", callback_data='admin_broadcast')],
            [InlineKeyboardButton("⛔ Добавить в ЧС", callback_data='admin_ban')],
            [InlineKeyboardButton("✅ Верифицировать пользователя", callback_data='admin_verify')],
            [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')]
        ]
        
        update.message.reply_text(
            "👑 *Админ-панель активирована!* 👑\n"
            "Выберите действие:",
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        update.message.reply_text("❌ *Неверный пароль!*", parse_mode='MarkdownV2')
        
    context.user_data['awaiting_password'] = False

# ===================== CALLBACK HANDLERS =====================
def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    # Обновление магазина
    if query.data == 'refresh_market':
        cursor.execute('''
            SELECT o.offer_id, o.stars, o.price, u.username, u.is_verified 
            FROM offers o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.is_active = 1
        ''')
        offers = cursor.fetchall()
        
        if not offers:
            query.edit_message_text("😔 *В магазине пока нет предложений!*", parse_mode='MarkdownV2')
            return
        
        text = "🛒 *Космический рынок звезд* 🪐\n\n"
        for offer in offers:
            status = "✅" if offer[4] else "❌"
            text += (
                f"{status} *Продавец:* @{offer[3]}\n"
                f"⭐ *Звезд:* {offer[1]}\n"
                f"💰 *Цена за штуку:* {offer[2]} руб\n"
                f"💎 *Сумма:* {offer[1] * offer[2]} руб\n"
                f"[Купить](https://t.me/{ADMIN_USERNAME[1:]}) | ID: `{offer[0]}`\n"
                "――――――――――――――――――――\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("🔍 Обновить", callback_data='refresh_market')],
            [InlineKeyboardButton("👤 Мой профиль", callback_data='my_profile')]
        ]
        
        query.edit_message_text(
            text, 
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard)),
            disable_web_page_preview=True
        )
    
    # Профиль пользователя
    elif query.data == 'my_profile':
        user = query.from_user
        db_user = get_user(user.id)
        is_verified = db_user[2]
        deals = db_user[3]
        commission = db_user[4]
        offer_count = get_offers_count(user.id)
        offer_limit = get_offer_limit(user.id)
        
        status = "✅ Проверенный" if is_verified else "❌ Непроверенный"
        status_emoji = "🟢" if is_verified else "🔴"
        
        text = (
            f"{status_emoji} *Ваш профиль*\n\n"
            f"👤 *Юзернейм:* @{user.username}\n"
            f"📛 *Статус:* {status}\n"
            f"📊 *Завершенные сделки:* {deals}\n"
            f"📉 *Комиссия:* {commission}%\n"
            f"📦 *Активные предложения:* {offer_count}/{offer_limit}\n\n"
        )
        
        keyboard = [[
            InlineKeyboardButton("❓ Как стать проверенным?", callback_data='how_to_verify')
        ]]
        
        query.edit_message_text(
            text, 
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Как стать проверенным
    elif query.data == 'how_to_verify':
        text = (
            "🌟 *Как стать проверенным продавцом?* 🌟\n\n"
            "1\. Пройдите *10 успешных сделок*\n"
            "2\. Обратитесь к администратору @Ma3stro274\n"
            "3\. После проверки получите статус ✅\n\n"
            "*Преимущества:*\n"
            f"✅ Сниженная комиссия *{COMMISSION_VERIFIED}%* вместо {COMMISSION_REGULAR}%\n"
            f"✅ Лимит предложений *4⭐* вместо 2⭐\n"
            "✅ Зеленая отметка в магазине\n\n"
            "🔄 После 10 сделок администратор добавит вас вручную"
        )
        keyboard = [[
            InlineKeyboardButton("👤 Назад в профиль", callback_data='my_profile'),
            InlineKeyboardButton("🛒 В магазин", callback_data='refresh_market')
        ]]
        query.edit_message_text(
            text, 
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Админ: Рассылка
    elif query.data == 'admin_broadcast':
        context.user_data['admin_action'] = 'broadcast'
        query.message.reply_text("📢 *Введите текст рассылки:*", parse_mode='MarkdownV2')
    
    # Админ: Бан пользователя
    elif query.data == 'admin_ban':
        context.user_data['admin_action'] = 'ban_user'
        query.message.reply_text(
            "⛔ *Введите ID пользователя для добавления в ЧС:*\n"
            "\(можно узнать через /profile пользователя\)",
            parse_mode='MarkdownV2'
        )
    
    # Админ: Верификация
    elif query.data == 'admin_verify':
        context.user_data['admin_action'] = 'verify_user'
        query.message.reply_text(
            "✅ *Введите ID пользователя для верификации:*\n"
            "\(можно узнать через /profile пользователя\)",
            parse_mode='MarkdownV2'
        )
    
    # Админ: Статистика
    elif query.data == 'admin_stats':
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM offers WHERE is_active = 1")
        active_offers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM blacklist")
        banned_users = cursor.fetchone()[0]
        
        text = (
            "📊 *Статистика бота*\n\n"
            f"👥 Пользователи: *{total_users}*\n"
            f"🛒 Активные предложения: *{active_offers}*\n"
            f"⛔ Заблокированные: *{banned_users}*"
        )
        query.message.reply_text(text, parse_mode='MarkdownV2')

# ===================== АДМИН-ДЕЙСТВИЯ =====================
def handle_admin_action(update: Update, context: CallbackContext) -> None:
    action = context.user_data.get('admin_action')
    if not action:
        return
    
    try:
        # Рассылка
        if action == 'broadcast':
            text = update.message.text
            
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            
            for user in users:
                try:
                    context.bot.send_message(
                        chat_id=user[0],
                        text=text,
                        parse_mode='MarkdownV2'
                    )
                except Exception as e:
                    logger.error(f"Ошибка рассылки: {e}")
            
            update.message.reply_text(f"✅ *Рассылка отправлена {len(users)} пользователям!*", parse_mode='MarkdownV2')
        
        # Бан пользователя
        elif action == 'ban_user':
            user_id = int(update.message.text)
            
            # Проверка существования
            if not get_user(user_id):
                update.message.reply_text("❌ Пользователь не найден!")
                return
            
            # Добавление в ЧС
            cursor.execute("INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)", (user_id,))
            
            # Деактивация предложений
            cursor.execute("UPDATE offers SET is_active = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
            
            update.message.reply_text(f"⛔ *Пользователь {user_id} добавлен в ЧС!*", parse_mode='MarkdownV2')
        
        # Верификация
        elif action == 'verify_user':
            user_id = int(update.message.text)
            
            user = get_user(user_id)
            if not user:
                update.message.reply_text("❌ Пользователь не найден!")
                return
                
            # Обновление статуса и комиссии
            cursor.execute(
                "UPDATE users SET is_verified = 1, commission_rate = ? WHERE user_id = ?",
                (COMMISSION_VERIFIED, user_id)
            )
            conn.commit()
            
            update.message.reply_text(f"✅ *Пользователь {user_id} теперь проверенный!*", parse_mode='MarkdownV2')
    
    except Exception as e:
        logger.error(f"Ошибка админ-действия: {e}")
        update.message.reply_text("❌ Ошибка выполнения команды!")
    
    context.user_data['admin_action'] = None

# ===================== ЗАПУСК БОТА =====================
def main() -> None:
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    # Основные команды
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("addoffer", add_offer))
    dp.add_handler(CommandHandler("market", market))
    dp.add_handler(CommandHandler("profile", profile))
    dp.add_handler(CommandHandler("adminpanel", admin_panel))
    
    # Обработчики сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_offer_input))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_admin_password))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_admin_action))
    
    # Обработчики кнопок
    dp.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
