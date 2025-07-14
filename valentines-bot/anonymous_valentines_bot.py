import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F
from aiogram.types import LabeledPrice
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize bot
bot = Bot(token="7953383202:AAGDM20U_YXOj_t_PfNvScytpFl55pRc_lE")  # Бот для пользователей
dp = Dispatcher()

# Admin settings
ADMIN_ID = 5397929249  # Ваш Telegram ID
ADMIN_PASSWORD = "Borov329700"  # Пароль для админ-доступа

# Initialize SQLite database
def init_db():
    try:
        conn = sqlite3.connect("valentines.db")
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            unique_link TEXT UNIQUE
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receiver_id INTEGER,
            sender_id INTEGER,
            message TEXT,
            is_anonymous INTEGER DEFAULT 1
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY
        )''')
        conn.commit()
        logging.info("База данных успешно инициализирована")
    except Exception as e:
        logging.error(f"Ошибка инициализации базы данных: {e}")
    finally:
        conn.close()

# Check if user is banned
def is_user_banned(user_id):
    try:
        conn = sqlite3.connect("valentines.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM banned_users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logging.error(f"Ошибка проверки статуса бана для user_id {user_id}: {e}")
        return False

# Generate unique link for user
async def generate_unique_link(user_id):
    try:
        unique_id = str(uuid.uuid4())
        conn = sqlite3.connect("valentines.db")
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (user_id, unique_link) VALUES (?, ?)", (user_id, unique_id))
        conn.commit()
        logging.info(f"Сохранён user_id {user_id} с unique_id {unique_id} в БД")
        bot_info = await bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={unique_id}"
        logging.info(f"Сгенерирована ссылка для user_id {user_id}: {link}")
        return link
    except Exception as e:
        logging.error(f"Ошибка генерации ссылки для user_id {user_id}: {e}")
        return None
    finally:
        conn.close()

# Get user_id from unique link
def get_user_from_link(unique_id):
    try:
        conn = sqlite3.connect("valentines.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE unique_link = ?", (unique_id,))
        result = c.fetchone()
        logging.info(f"Поиск user_id для unique_id {unique_id}: {result}")
        return result[0] if result else None
    except Exception as e:
        logging.error(f"Ошибка поиска user_id для unique_id {unique_id}: {e}")
        return None
    finally:
        conn.close()

# Start command handler with menu
@dp.message(CommandStart())
async def start_command(message: types.Message):
    args = message.text.split()
    logging.info(f"Получена команда /start от user_id {message.from_user.id} с аргументами: {args}")
    
    # Check if user is banned
    if is_user_banned(message.from_user.id):
        await message.answer("🚫 Вы забанены и не можете использовать бот.")
        logging.warning(f"Забаненный user_id {message.from_user.id} пытался использовать /start")
        return
    
    # Handle link-based start
    if len(args) > 1:
        unique_id = args[1]
        receiver_id = get_user_from_link(unique_id)
        if receiver_id and receiver_id != message.from_user.id:
            await message.answer(
                "💌 Напишите анонимное валентинное сообщение:",
                reply_markup=types.ReplyKeyboardRemove()
            )
            dp.data[message.from_user.id] = {"receiver_id": receiver_id}
            logging.info(f"Успешно обработана ссылка для user_id {message.from_user.id}, receiver_id: {receiver_id}")
        else:
            user_link = await generate_unique_link(message.from_user.id)
            if user_link:
                menu = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📤 Поделиться ссылкой", switch_inline_query=user_link)],
                    [InlineKeyboardButton(text="🔧 Админ-панель", callback_data="admin_panel")]
                ])
                await message.answer(
                    "❌ Неверная или собственная ссылка!\n\n"
                    "💖 Добро пожаловать в бот анонимных валентинок! 💖\n\n"
                    "Отправляйте и получайте анонимные сообщения, полные любви и тепла! 💌\n"
                    f"Ваша уникальная ссылка: {user_link}\n"
                    "Поделитесь ею с друзьями, чтобы получать валентинки!\n\n"
                    "За 5 Telegram Stars 🌟 вы сможете узнать, кто отправил вам сообщение!\n\n"
                    "Выберите действие:",
                    reply_markup=menu
                )
                logging.info(f"Ссылка отправлена user_id {message.from_user.id}: {user_link}")
            else:
                await message.answer("❌ Ошибка при генерации ссылки. Попробуйте ещё раз.")
                logging.error(f"Не удалось сгенерировать ссылку для user_id {message.from_user.id}")
    else:
        user_link = await generate_unique_link(message.from_user.id)
        if user_link:
            menu = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Поделиться ссылкой", switch_inline_query=user_link)],
                [InlineKeyboardButton(text="🔧 Админ-панель", callback_data="admin_panel")]
            ])
            await message.answer(
                "💖 Добро пожаловать в бот анонимных валентинок! 💖\n\n"
                "Отправляйте и получайте анонимные сообщения, полные любви и тепла! 💌\n"
                f"Ваша уникальная ссылка: {user_link}\n"
                "Поделитесь ею с друзьями, чтобы получать валентинки!\n\n"
                "За 5 Telegram Stars 🌟 вы сможете узнать, кто отправил вам сообщение!\n\n"
                "Выберите действие:",
                reply_markup=menu
            )
            logging.info(f"Ссылка отправлена user_id {message.from_user.id}: {user_link}")
        else:
            await message.answer("❌ Ошибка при генерации ссылки. Попробуйте ещё раз.")
            logging.error(f"Не удалось сгенерировать ссылку для user_id {message.from_user.id}")

# Admin panel callback
@dp.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("❌ Доступ только для администратора.")
        logging.warning(f"Неавторизованный доступ к админ-панели от user_id {callback.from_user.id}")
        await callback.answer()
        return
    
    if dp.data.get(callback.from_user.id, {}).get("admin_authorized", False):
        await show_admin_panel(callback.message)
    else:
        await callback.message.answer("🔐 Введите пароль для доступа к админ-панели:")
        dp.data[callback.from_user.id] = dp.data.get(callback.from_user.id, {})
        dp.data[callback.from_user.id]["awaiting_password"] = True
    await callback.answer()

# Handle password input
@dp.message(F.text & F.func(lambda message: dp.data.get(message.from_user.id, {}).get("awaiting_password", False)))
async def handle_password(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ только для администратора.")
        return
    
    if message.text == ADMIN_PASSWORD:
        dp.data[message.from_user.id]["admin_authorized"] = True
        dp.data[message.from_user.id]["awaiting_password"] = False
        await show_admin_panel(message)
        logging.info(f"Админ user_id {message.from_user.id} успешно авторизовался")
    else:
        await message.answer("❌ Неверный пароль. Попробуйте снова:")
        logging.warning(f"Неверный пароль от user_id {message.from_user.id}")

# Show admin panel
async def show_admin_panel(message: types.Message):
    admin_menu = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Просмотреть сообщения", callback_data="admin_messages")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🗑 Очистить базу данных", callback_data="admin_clear_db")],
        [InlineKeyboardButton(text="🚫 Забанить пользователя", callback_data="admin_ban")],
        [InlineKeyboardButton(text="✅ Разбанить пользователя", callback_data="admin_unban")],
        [InlineKeyboardButton(text="🔒 Заблокировать админ-панель", callback_data="admin_lock")]
    ])
    await message.answer(
        "🔧 Админ-панель\n\nВыберите действие:",
        reply_markup=admin_menu
    )

# Admin callback handler
@dp.callback_query(F.data.startswith("admin_"))
async def admin_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID or not dp.data.get(callback.from_user.id, {}).get("admin_authorized", False):
        await callback.message.answer("❌ Доступ только для администратора.")
        logging.warning(f"Неавторизованный доступ к админ-действию от user_id {callback.from_user.id}")
        await callback.answer()
        return
    
    action = callback.data.split("_")[1]
    
    if action == "messages":
        try:
            conn = sqlite3.connect("valentines.db")
            c = conn.cursor()
            c.execute("SELECT id, receiver_id, sender_id, message, is_anonymous FROM messages ORDER BY id DESC LIMIT 10")
            messages = c.fetchall()
            conn.close()

            if not messages:
                await callback.message.answer("Нет сообщений в базе данных.")
                logging.info("Команда /messages: База данных пуста")
                return

            response = "Последние сообщения:\n\n"
            for msg in messages:
                msg_id, receiver_id, sender_id, text, is_anonymous = msg
                response += (
                    f"ID: {msg_id}\n"
                    f"Отправитель ID: {sender_id}\n"
                    f"Получатель ID: {receiver_id}\n"
                    f"Текст: {text}\n"
                    f"Анонимно: {'Да' if is_anonymous else 'Нет'}\n\n"
                )
            await callback.message.answer(response)
            logging.info(f"Команда /messages выполнена для user_id {callback.from_user.id}")
        except Exception as e:
            await callback.message.answer("❌ Ошибка при получении сообщений.")
            logging.error(f"Ошибка команды /messages: {e}")
    
    elif action == "stats":
        try:
            conn = sqlite3.connect("valentines.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            user_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM messages")
            message_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM banned_users")
            banned_count = c.fetchone()[0]
            conn.close()
            await callback.message.answer(
                f"📊 Статистика бота:\n"
                f"Пользователей: {user_count}\n"
                f"Сообщений: {message_count}\n"
                f"Забаненных пользователей: {banned_count}"
            )
            logging.info(f"Команда /stats выполнена для user_id {callback.from_user.id}")
        except Exception as e:
            await callback.message.answer("❌ Ошибка при получении статистики.")
            logging.error(f"Ошибка команды /stats: {e}")
    
    elif action == "clear_db":
        await callback.message.answer("🗑 Подтвердите очистку базы данных (введите: ПОДТВЕРДИТЬ):")
        dp.data[callback.from_user.id]["awaiting_clear_db"] = True
    
    elif action == "ban":
        await callback.message.answer("🚫 Введите ID пользователя для бана:")
        dp.data[callback.from_user.id]["awaiting_ban"] = True
    
    elif action == "unban":
        await callback.message.answer("✅ Введите ID пользователя для разбана:")
        dp.data[callback.from_user.id]["awaiting_unban"] = True
    
    elif action == "lock":
        dp.data[callback.from_user.id]["admin_authorized"] = False
        user_link = await generate_unique_link(callback.from_user.id)
        if user_link:
            menu = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Поделиться ссылкой", switch_inline_query=user_link)],
                [InlineKeyboardButton(text="🔧 Админ-панель", callback_data="admin_panel")]
            ])
            await callback.message.answer(
                "🔒 Админ-панель заблокирована.\n\n"
                "💖 Добро пожаловать в бот анонимных валентинок! 💖\n\n"
                "Отправляйте и получайте анонимные сообщения, полные любви и тепла! 💌\n"
                f"Ваша уникальная ссылка: {user_link}\n"
                "Поделитесь ею с друзьями, чтобы получать валентинки!\n\n"
                "За 5 Telegram Stars 🌟 вы сможете узнать, кто отправил вам сообщение!\n\n"
                "Выберите действие:",
                reply_markup=menu
            )
            logging.info(f"Админ-панель заблокирована для user_id {callback.from_user.id}")
        else:
            await callback.message.answer("❌ Ошибка при генерации ссылки. Попробуйте ещё раз.")
            logging.error(f"Не удалось сгенерировать ссылку при блокировке админ-панели для user_id {callback.from_user.id}")
    
    await callback.answer()

# Handle clear_db confirmation
@dp.message(F.text & F.func(lambda message: dp.data.get(message.from_user.id, {}).get("awaiting_clear_db", False)))
async def handle_clear_db(message: types.Message):
    if message.from_user.id != ADMIN_ID or not dp.data.get(message.from_user.id, {}).get("admin_authorized", False):
        await message.answer("❌ Доступ только для администратора.")
        return
    
    if message.text == "ПОДТВЕРДИТЬ":
        try:
            conn = sqlite3.connect("valentines.db")
            c = conn.cursor()
            c.execute("DELETE FROM users")
            c.execute("DELETE FROM messages")
            c.execute("DELETE FROM banned_users")
            conn.commit()
            conn.close()
            await message.answer("🗑 База данных успешно очищена.")
            logging.info(f"База данных очищена user_id {message.from_user.id}")
        except Exception as e:
            await message.answer("❌ Ошибка при очистке базы данных.")
            logging.error(f"Ошибка очистки базы данных: {e}")
        finally:
            dp.data[message.from_user.id]["awaiting_clear_db"] = False
    else:
        await message.answer("❌ Очистка отменена. Введите ПОДТВЕРДИТЬ для подтверждения.")
        dp.data[message.from_user.id]["awaiting_clear_db"] = False

# Handle ban user
@dp.message(F.text & F.func(lambda message: dp.data.get(message.from_user.id, {}).get("awaiting_ban", False)))
async def handle_ban_user(message: types.Message):
    if message.from_user.id != ADMIN_ID or not dp.data.get(message.from_user.id, {}).get("admin_authorized", False):
        await message.answer("❌ Доступ только для администратора.")
        return
    
    try:
        user_id = int(message.text)
        if user_id == ADMIN_ID:
            await message.answer("❌ Нельзя забанить администратора.")
            return
        conn = sqlite3.connect("valentines.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
        await message.answer(f"🚫 Пользователь {user_id} забанен.")
        logging.info(f"Пользователь {user_id} забанен админом {message.from_user.id}")
    except ValueError:
        await message.answer("❌ Введите корректный ID пользователя (число).")
    except Exception as e:
        await message.answer("❌ Ошибка при бане пользователя.")
        logging.error(f"Ошибка бана пользователя: {e}")
    finally:
        dp.data[message.from_user.id]["awaiting_ban"] = False

# Handle unban user
@dp.message(F.text & F.func(lambda message: dp.data.get(message.from_user.id, {}).get("awaiting_unban", False)))
async def handle_unban_user(message: types.Message):
    if message.from_user.id != ADMIN_ID or not dp.data.get(message.from_user.id, {}).get("admin_authorized", False):
        await message.answer("❌ Доступ только для администратора.")
        return
    
    try:
        user_id = int(message.text)
        conn = sqlite3.connect("valentines.db")
        c = conn.cursor()
        c.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Пользователь {user_id} разбанен.")
        logging.info(f"Пользователь {user_id} разбанен админом {message.from_user.id}")
    except ValueError:
        await message.answer("❌ Введите корректный ID пользователя (число).")
    except Exception as e:
        await message.answer("❌ Ошибка при разбане пользователя.")
        logging.error(f"Ошибка разбана пользователя: {e}")
    finally:
        dp.data[message.from_user.id]["awaiting_unban"] = False

# Support and terms commands
@dp.message(Command("paysupport"))
async def paysupport_command(message: types.Message):
    await message.answer("📞 Для вопросов по оплате пишите: @Borov3223")  # Замените, если другой аккаунт

@dp.message(Command("support"))
async def support_command(message: types.Message):
    await message.answer("📞 Для общих вопросов пишите: @Borov3223")  # Замените, если другой аккаунт

@dp.message(Command("terms"))
async def terms_command(message: types.Message):
    await message.answer("📜 Условия использования: https://telegram.org/tos")

# Handle incoming text messages
@dp.message(F.text)
async def handle_message(message: types.Message):
    logging.info(f"Получено текстовое сообщение от user_id {message.from_user.id}: {message.text}")
    
    # Skip if user is banned
    if is_user_banned(message.from_user.id):
        await message.answer("🚫 Вы забанены и не можете отправлять сообщения.")
        logging.warning(f"Забаненный user_id {message.from_user.id} пытался отправить сообщение")
        return
    
    if message.from_user.id in dp.data and "receiver_id" in dp.data[message.from_user.id]:
        receiver_id = dp.data[message.from_user.id]["receiver_id"]
        sender_id = message.from_user.id
        message_text = message.text
        logging.info(f"Обработка сообщения: sender_id {sender_id}, receiver_id {receiver_id}, текст: {message_text}")

        # Save message to database
        try:
            conn = sqlite3.connect("valentines.db")
            c = conn.cursor()
            c.execute("INSERT INTO messages (receiver_id, sender_id, message) VALUES (?, ?, ?)",
                      (receiver_id, sender_id, message_text))
            conn.commit()
            message_id = c.lastrowid
            logging.info(f"Сообщение сохранено в БД: message_id {message_id}, receiver_id {receiver_id}, sender_id {sender_id}")
        except Exception as e:
            logging.error(f"Ошибка сохранения сообщения в БД: {e}")
            await message.answer("❌ Ошибка при сохранении сообщения. Попробуйте ещё раз.")
            return
        finally:
            conn.close()

        # Send message to moderator
        mod_message = (
            f"Новое сообщение:\n"
            f"Отправитель ID: {sender_id}\n"
            f"Получатель ID: {receiver_id}\n"
            f"Текст: {message_text}"
        )
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,  # Ваш Telegram ID
                text=mod_message
            )
            logging.info(f"Сообщение отправлено модератору: {mod_message}")
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения модератору: {e}")

        # Notify receiver
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Узнать отправителя (5 Stars)", callback_data=f"reveal_{message_id}")]
            ])
            await bot.send_message(
                receiver_id,
                f"💌 Вы получили анонимную валентинку:\n{message_text}",
                reply_markup=keyboard
            )
            logging.info(f"Уведомление отправлено получателю receiver_id {receiver_id}")
        except Exception as e:
            logging.error(f"Ошибка отправки уведомления получателю receiver_id {receiver_id}: {e}")
        await message.answer("Ваше валентинное сообщение отправлено! 💖")
        del dp.data[message.from_user.id]
    else:
        await message.answer(
            "Пожалуйста, используйте свою уникальную ссылку, чтобы отправить сообщение, или /start, чтобы получить свою ссылку."
        )

# Handle reveal sender button
@dp.callback_query(F.data.startswith("reveal_"))
async def reveal_sender(callback: types.CallbackQuery):
    message_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect("valentines.db")
    c = conn.cursor()
    c.execute("SELECT sender_id FROM messages WHERE id = ?", (message_id,))
    result = c.fetchone()
    sender_id = result[0] if result else None
    conn.close()

    if sender_id:
        prices = [LabeledPrice(label="Узнать отправителя", amount=500)]
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Узнать отправителя",
            description="Заплатите 5 Telegram Stars, чтобы узнать профиль отправителя.",
            payload=f"reveal_{message_id}",
            provider_token="",
            currency="XTR",
            prices=prices
        )
    else:
        await callback.message.answer("❌ Ошибка: сообщение не найдено.")
        logging.error(f"Сообщение с ID {message_id} не найдено для reveal")
    await callback.answer()

# Handle pre-checkout query
@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Handle successful payment
@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    message_id = int(payload.split("_")[1])
    conn = sqlite3.connect("valentines.db")
    c = conn.cursor()
    c.execute("SELECT sender_id FROM messages WHERE id = ?", (message_id,))
    result = c.fetchone()
    sender_id = result[0] if result else None
    c.execute("UPDATE messages SET is_anonymous = 0 WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()

    if sender_id:
        sender_chat = await bot.get_chat(sender_id)
        sender_profile = f"https://t.me/{sender_chat.username or sender_id}"
        await message.answer(f"Отправитель раскрыт! Профиль: {sender_profile}")
    else:
        await message.answer("❌ Ошибка: отправитель не найден.")
        logging.error(f"Отправитель для message_id {message_id} не найден")

async def main():
    init_db()
    try:
        await dp.start_polling(bot)
        logging.info("Опрос успешно запущен")
    except Exception as e:
        logging.error(f"Ошибка при запуске опроса: {e}")
        raise  # Повторно выбросить исключение для отображения в логах Render

if __name__ == "__main__":
    asyncio.run(main())
