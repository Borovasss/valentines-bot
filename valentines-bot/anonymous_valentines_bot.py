import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F
from aiogram.types import LabeledPrice
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize bot
bot = Bot(token="7953383202:AAGDM20U_YXOj_t_PfNvScytpFl55pRc_lE")  # Бот для пользователей
dp = Dispatcher()

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
        conn.commit()
        logging.info("База данных успешно инициализирована")
    except Exception as e:
        logging.error(f"Ошибка инициализации базы данных: {e}")
    finally:
        conn.close()

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

# Start command handler
@dp.message(Command("start"))
async def start_command(message: types.Message):
    args = message.text.split()
    logging.info(f"Получена команда /start от user_id {message.from_user.id} с аргументами: {args}")
    
    # Moderator start command
    if message.from_user.id == 5397929249:  # Ваш Telegram ID
        await message.answer("Сервер запущен! Бот готов принимать сообщения.")
        logging.info("Бот: Сервер запущен")
        return
    
    # Regular user start command
    if len(args) > 1:
        unique_id = args[1]
        receiver_id = get_user_from_link(unique_id)
        if receiver_id and receiver_id != message.from_user.id:
            await message.answer("💌 Напишите анонимное валентинное сообщение:", reply_markup=types.ReplyKeyboardRemove())
            dp.data[message.from_user.id] = {"receiver_id": receiver_id}
            logging.info(f"Успешно обработана ссылка для user_id {message.from_user.id}, receiver_id: {receiver_id}")
        else:
            await message.answer("❌ Неверная или собственная ссылка! Используйте /start, чтобы получить свою ссылку.")
            logging.warning(f"Неверная или собственная ссылка для user_id {message.from_user.id}, unique_id: {unique_id}")
    else:
        user_link = await generate_unique_link(message.from_user.id)
        if user_link:
            share_button = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Поделиться ссылкой", switch_inline_query=user_link)]
            ])
            await message.answer(
                f"Добро пожаловать в бот анонимных валентинок! 💖\n"
                f"Поделитесь этой ссылкой, чтобы получать анонимные сообщения:\n{user_link}\n\n"
                f"Когда вам отправят валентинку, вы сможете за 5 Telegram Stars узнать, кто её написал!",
                reply_markup=share_button
            )
            logging.info(f"Ссылка отправлена user_id {message.from_user.id}: {user_link}")
        else:
            await message.answer("❌ Ошибка при генерации ссылки. Попробуйте ещё раз.")
            logging.error(f"Не удалось сгенерировать ссылку для user_id {message.from_user.id}")

# Messages command handler (for moderator)
@dp.message(Command("messages"))
async def messages_command(message: types.Message):
    if message.from_user.id != 5397929249:  # Только для модератора
        await message.answer("❌ Доступ только для администратора.")
        logging.warning(f"Неавторизованный доступ к /messages от user_id {message.from_user.id}")
        return
    
    try:
        conn = sqlite3.connect("valentines.db")
        c = conn.cursor()
        c.execute("SELECT id, receiver_id, sender_id, message, is_anonymous FROM messages ORDER BY id DESC LIMIT 10")
        messages = c.fetchall()
        conn.close()

        if not messages:
            await message.answer("Нет сообщений в базе данных.")
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
        await message.answer(response)
        logging.info(f"Команда /messages выполнена для user_id {message.from_user.id}")
    except Exception as e:
        await message.answer("❌ Ошибка при получении сообщений.")
        logging.error(f"Ошибка команды /messages: {e}")

# Support commands
@dp.message(Command("paysupport"))
async def paysupport_command(message: types.Message):
    await message.answer("Для вопросов по оплате пишите: @Borov3223")  # Замените, если другой аккаунт

@dp.message(Command("support"))
async def support_command(message: types.Message):
    await message.answer("Для общих вопросов пишите: @Borov3223")  # Замените, если другой аккаунт

@dp.message(Command("terms"))
async def terms_command(message: types.Message):
    await message.answer("Условия использования: https://telegram.org/tos")

# Handle incoming text messages
@dp.message(F.text)
async def handle_message(message: types.Message):
    logging.info(f"Получено текстовое сообщение от user_id {message.from_user.id}: {message.text}")
    if message.from_user.id in dp.data:
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
                chat_id=5397929249,  # Ваш Telegram ID
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
