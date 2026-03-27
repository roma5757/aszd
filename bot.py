import logging
import random
import string
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.executor import start_webhook

# 🔐 НАСТРОЙКИ
API_TOKEN = "YOUR_BOT_TOKEN"
CHANNEL_ID = "@your_channel"
ADMIN_ID = 123456789

# 🌐 Railway Webhook
WEBHOOK_HOST = "https://your-app.up.railway.app"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 8000

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


# 📁 База данных
async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY
            )
        """)
        await db.commit()


async def user_exists(user_id):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()


async def add_user(user_id):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()


# 🔑 Генерация кода
def generate_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# 📢 Отправка поста в канал
@dp.message_handler(commands=["post"])
async def post(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Участвовать", callback_data="join"))

    await bot.send_message(
        CHANNEL_ID,
        "🎁 Нажми кнопку, чтобы участвовать!",
        reply_markup=keyboard
    )


# 🔘 Обработка кнопки
@dp.callback_query_handler(lambda c: c.data == "join")
async def handle_join(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    # ❌ Уже участвовал
    if await user_exists(user_id):
        await callback.answer("Ты уже участвуешь ✅", show_alert=True)
        return

    # 🔍 Проверка подписки
    member = await bot.get_chat_member(CHANNEL_ID, user_id)

    if member.status in ["left", "kicked"]:
        await callback.answer("Сначала подпишись на канал!", show_alert=True)
        return

    # ✅ Добавляем в базу
    await add_user(user_id)

    # 🔑 Код
    code = generate_code()

    username = callback.from_user.username
    if username:
        username = f"@{username}"
    else:
        username = "без username"

    # 📩 Отправка админу
    await bot.send_message(
        ADMIN_ID,
        f"Новый участник!\n\n"
        f"👤 {username}\n"
        f"🆔 {user_id}\n"
        f"🎟 Код: {code}"
    )

    await callback.answer("Ты участвуешь! 🎉", show_alert=True)


# 🚀 Запуск
async def on_startup(dp):
    await init_db()
    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown(dp):
    await bot.delete_webhook()


if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
