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
bot = Bot(token="8004585329:AAEe_MSDprlIqZdjyEV3AYH2iiQJDHTeCkM")
moderation_bot = Bot(token="8184681913:AAEOfeBGA2p5S7q207ZpY-4qjCdBAW5gEEg")
dp = Dispatcher()

# Initialize SQLite database
def init_db():
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
    conn.close()

# Generate unique link for user
async def generate_unique_link(user_id):
    unique_id = str(uuid.uuid4())
    conn = sqlite3.connect("valentines.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, unique_link) VALUES (?, ?)", (user_id, unique_id))
    conn.commit()
    conn.close()
    bot_info = await bot.get_me()
    return f"https://t.me/{bot_info.username}?start={unique_id}"

# Get user_id from unique link
def get_user_from_link(unique_id):
    conn = sqlite3.connect("valentines.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE unique_link = ?", (unique_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# Start command handler
@dp.message(Command("start"))
async def start_command(message: types.Message):
    args = message.text.split()
    if len(args) > 1:  # If the start command has a parameter (deep link)
        unique_id = args[1]
        receiver_id = get_user_from_link(unique_id)
        if receiver_id and receiver_id != message.from_user.id:
            # Prompt to send an anonymous message
            await message.answer("💌 Напишите анонимное валентинное сообщение:", reply_markup=types.ReplyKeyboardRemove())
            dp.data[message.from_user.id] = {"receiver_id": receiver_id}
        else:
            await message.answer("❌ Неверная или собственная ссылка! Используйте /start, чтобы получить свою ссылку.")
    else:
        # Generate and send user's unique link with share button
        user_link = await generate_unique_link(message.from_user.id)
        share_button = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться ссылкой", switch_inline_query=user_link)]
        ])
        await message.answer(
            f"Добро пожаловать в бот анонимных валентинок! 💖\n"
            f"Поделитесь этой ссылкой, чтобы получать анонимные сообщения:\n{user_link}\n\n"
            f"Когда вам отправят валентинку, вы сможете за 5 Telegram Stars узнать, кто её написал!",
            reply_markup=share_button
        )

# Support commands for Telegram Stars
@dp.message(Command("paysupport"))
async def paysupport_command(message: types.Message):
    await message.answer("Для вопросов по оплате пишите: @Borov3223")  # Замените, если другой аккаунт

@dp.message(Command("support"))
async def support_command(message: types.Message):
    await message.answer("Для общих вопросов пишите: @Borov3223")  # Замените, если другой аккаунт

@dp.message(Command("terms"))
async def terms_command(message: types.Message):
    await message.answer("Условия использования: https://telegram.org/tos")

# Handle incoming text messages (valentines)
@dp.message(F.text)
async def handle_message(message: types.Message):
    if message.from_user.id in dp.data:
        receiver_id = dp.data[message.from_user.id]["receiver_id"]
        sender_id = message.from_user.id
        message_text = message.text

        # Save message to database
        conn = sqlite3.connect("valentines.db")
        c = conn.cursor()
        c.execute("INSERT INTO messages (receiver_id, sender_id, message) VALUES (?, ?, ?)",
                  (receiver_id, sender_id, message_text))
        conn.commit()
        message_id = c.lastrowid
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
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Узнать отправителя (5 Stars)", callback_data=f"reveal_{message_id}")]
        ])
        await bot.send_message(
            receiver_id,
            f"💌 Вы получили анонимную валентинку:\n{message_text}",
            reply_markup=keyboard
        )
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
    sender_id = c.fetchone()[0]
    conn.close()

    # Create payment invoice for Telegram Stars
    prices = [LabeledPrice(label="Узнать отправителя", amount=500)]  # 5 Stars = 500 (в единицах Telegram Stars)
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Узнать отправителя",
        description="Заплатите 5 Telegram Stars, чтобы узнать профиль отправителя.",
        payload=f"reveal_{message_id}",
        provider_token="",  # Пустая строка для Telegram Stars
        currency="XTR",  # Валюта Telegram Stars
        prices=prices
    )

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
    c.execute("Узнать отправителя FROM messages WHERE id = ?", (message_id,))
    sender_id = c.fetchone()[0]
    c.execute("UPDATE messages SET is_anonymous = 0 WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()

    # Send sender's profile link
    sender_chat = await bot.get_chat(sender_id)
    sender_profile = f"https://t.me/{sender_chat.username or sender_id}"
    await message.answer(f"Отправитель раскрыт! Профиль: {sender_profile}")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())