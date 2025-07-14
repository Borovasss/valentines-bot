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
logging.basicConfig(level=logging.INFO)

# Initialize main bot and moderation bot
main_bot = Bot(token="8004585329:AAEe_MSDprlIqZdjyEV3AYH2iiQJDHTeCkM")
moderation_bot = Bot(token="8184681913:AAEOfeBGA2p5S7q207ZpY-4qjCdBAW5gEEg")
dp_main = Dispatcher()
dp_moderation = Dispatcher()

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
        bot_info = await main_bot.get_me()
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

# Main bot: Start command handler
@dp_main.message(Command("start"))
async def start_command(message: types.Message):
    args = message.text.split()
    logging.info(f"Получена команда /start от user_id {message.from_user.id} с аргументами: {args}")
    if len(args) > 1:  # If the start command has a parameter (deep link)
        unique_id = args[1]
        receiver_id = get_user_from_link(unique_id)
        if receiver_id and receiver_id != message.from_user.id:
            await message.answer("💌 Напишите анонимное валентинное сообщение:", reply_markup=types.ReplyKeyboardRemove())
            dp_main.data[message.from_user.id] = {"receiver_id": receiver_id}
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

# Main bot: Support commands
@dp_main.message(Command("paysupport"))
async def paysupport_command(message: types.Message):
    await message.answer("Для вопросов по оплате пишите: @Borov3223")  # Замените, если другой аккаунт

@dp_main.message(Command("support"))
async def support_command(message: types.Message):
    await message.answer("Для общих вопросов пишите: @Borov3223")  # Замените, если другой аккаунт

@dp_main.message(Command("terms"))
async def terms_command(message: types.Message):
    await message.answer("Условия использования: https://telegram.org/tos")

# Main bot: Handle incoming text messages
@dp_main.message(F.text)
async def handle_message(message: types.Message):
    logging.info(f"Получено текстовое сообщение от user_id {message.from_user.id}: {message.text}")
    if message.from_user.id in dp_main.data:
        receiver_id = dp_main.data[message.from_user.id]["receiver_id"]
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

        # Send message to moderation bot
        mod_message = (
            f"Новое сообщение:\n"
            f"Отправитель ID: {sender_id}\n"
            f"Получатель ID: {receiver_id}\n"
            f"Текст: {message_text}"
        )
        try:
            await moderation_bot.send_message(
                chat_id=5397929249,  # Ваш Telegram ID
                text=mod_message
            )
            logging.info(f"Сообщение успешно отправлено модерационному боту: {mod_message}")
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения модерационному боту: {e}")

        # Notify receiver
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Узнать отправителя (5 Stars)", callback_data=f"reveal_{message_id}")]
            ])
            await main_bot.send_message(
                receiver_id,
                f"💌 Вы получили анонимную валентинку:\n{message_text}",
                reply_markup=keyboard
            )
            logging.info(f"Уведомление отправлено получателю receiver_id {receiver_id}")
        except Exception as e:
            logging.error(f"Ошибка отправки уведомления получателю receiver_id {receiver_id}: {e}")
        await message.answer("Ваше валентинное сообщение отправлено! 💖")
        del dp_main.data[message.from_user.id]
    else:
        await message.answer(
            "Пожалуйста, используйте свою уникальную ссылку, чтобы отправить сообщение, или /start, чтобы получить свою ссылку."
        )

# Main bot: Handle reveal sender button
@dp_main.callback_query(F.data.startswith("reveal_"))
async def reveal_sender(callback: types.CallbackQuery):
    message_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect("valentines.db")
    c = conn.cursor()
    c.execute("SELECT sender_id FROM messages WHERE id = ?", (message_id,))
    result = c.fetchone()
    sender_id = result[0] if result else None
    conn.close()

    if sender_id:
        prices = [LabeledPrice(label="Узнать отправителя", amount=500)]  # 5 Stars = 500
        await main_bot.send_invoice(
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

# Main bot: Handle pre-checkout query
@dp_main.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await main_bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Main bot: Handle successful payment
@dp_main.message(F.successful_payment)
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
        sender_chat = await main_bot.get_chat(sender_id)
        sender_profile = f"https://t.me/{sender_chat.username or sender_id}"
        await message.answer(f"Отправитель раскрыт! Профиль: {sender_profile}")
    else:
        await message.answer("❌ Ошибка: отправитель не найден.")
        logging.error(f"Отправитель для message_id {message_id} не найден")

# Moderation bot: Start command
@dp_moderation.message(Command("start"))
async def moderation_start_command(message: types.Message):
    if message.from_user.id == 5397929249:  # Ваш Telegram ID
        await moderation_bot.send_message(
            chat_id=5397929249,
            text="Сервер запущен! Модерационный бот готов принимать сообщения."
        )
        logging.info("Модерационный бот: Сервер запущен")
    else:
        await message.answer("Доступ только для администратора.")

async def main():
    init_db()
    try:
        await asyncio.gather(
            dp_main.start_polling(main_bot),
            dp_moderation.start_polling(moderation_bot)
        )
    except Exception as e:
        logging.error(f"Ошибка при запуске опроса: {e}")

if __name__ == "__main__":
    asyncio.run(main())
