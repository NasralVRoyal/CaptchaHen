import asyncio
import logging
import random
import string
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== НАСТРОЙКИ БОТА ==================

# Токен бота (ТВОЙ)
BOT_TOKEN = "8520271990:AAGHQGPdr01j3Tfn6iWU0JyuH12uHAGR3tw"

# ID канала (ТВОЙ приватный канал)
CHANNEL_ID = -1001920136785

# Имя канала (для вывода в тексте, не обязательно совпадает с @username)
CHANNEL_NAME = "HenPicture"

# ====================================================

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Состояния пользователей и выданные ссылки (в памяти)
user_states = {}
used_links = set()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start — выдать капчу."""
    user_id = update.effective_user.id
    user_states[user_id] = {"step": "captcha"}

    # Генерируем простой пример
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operation = random.choice(["+", "-", "*"])

    if operation == "+":
        answer = num1 + num2
    elif operation == "-":
        answer = num1 - num2
    else:
        answer = num1 * num2

    user_states[user_id].update(
        {"num1": num1, "num2": num2, "operation": operation, "answer": answer}
    )

    text = (
        "🔐 Для доступа реши простую капчу:

"
        f"*{num1} {operation} {num2} = ?*

"
        "Отправь только число ответом на это сообщение."
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех текстовых сообщений (проверка капчи)."""
    user_id = update.effective_user.id
    message = update.message

    # Если пользователь еще не начинал (/start не жали)
    if user_id not in user_states:
        await message.reply_text("👋 Нажми /start, чтобы начать и пройти капчу.")
        return

    state = user_states[user_id]

    # Этап капчи
    if state.get("step") == "captcha":
        try:
            user_answer = int(message.text.strip())
        except ValueError:
            await message.reply_text("❌ Введи, пожалуйста, только число.")
            return

        if user_answer == state["answer"]:
            # Капча пройдена — генерируем ссылку
            await generate_invite_link(update, context)
        else:
            await message.reply_text(
                f"❌ Неправильный ответ!
"
                f"Правильно было: *{state['answer']}*

"
                "Попробуй еще раз: /start",
                parse_mode="Markdown",
            )
            # Сбрасываем состояние
            user_states.pop(user_id, None)

    else:
        await message.reply_text("Нажми /start, чтобы получить новую ссылку.")


async def generate_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание одноразовой приглашалки на канал через Bot API."""
    user_id = update.effective_user.id
    message = update.message

    try:
        # Генерируем однократную инвайт-ссылку через Telegram API
        # (требует, чтобы бот был админом в канале с правом Invite users)
        invite_link_obj = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            expire_date=int((datetime.now() + timedelta(hours=24)).timestamp()),
            member_limit=1,  # одно вступление
            creates_join_request=False,
            name=f"Invite for {user_id}",
        )

        invite_link = invite_link_obj.invite_link
        used_links.add(invite_link)

        expires_at = datetime.fromtimestamp(invite_link_obj.expire_date)

        text = (
            "✅ *Капча пройдена успешно!*

"
            f"🔗 *Твоя уникальная пригласительная ссылка в канал* **{CHANNEL_NAME}**:
"
            f"`{invite_link}`

"
            f"⏰ Действительна до: `{expires_at.strftime('%d.%m.%Y %H:%M')}`
"
            "⚠️ Ссылка одноразовая и сработает только один раз."
        )

        await message.reply_text(text, parse_mode="Markdown")

        user_states[user_id]["step"] = "completed"
        user_states[user_id]["link"] = invite_link
        user_states[user_id]["expires"] = expires_at

        logger.info(f"Выдана ссылка пользователю {user_id}: {invite_link}")

    except Exception as e:
        logger.error(f"Ошибка при генерации ссылки: {e}")
        await message.reply_text(
            "❌ Произошла ошибка при создании ссылки.
"
            "Убедись, что бот является админом канала с правом приглашать пользователей.
"
            "Попробуй еще раз: /start"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help."""
    text = (
        "🤖 *Бот выдачи инвайта в канал HenPicture*

"
        "/start — пройти капчу и получить одноразовую ссылку
"
        "/help — показать это сообщение

"
        "Алгоритм работы:
"
        "1) Нажимаешь /start
"
        "2) Решешь простой пример
"
        "3) Получаешь уникальную ссылку (1 вступление, 24 часа)"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def main():
    """Точка входа — запуск бота."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Все текстовые сообщения
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("🚀 Бот запущен...")
    print(f"📢 Канал ID: {CHANNEL_ID} ({CHANNEL_NAME})")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
