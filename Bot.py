import asyncio
import logging
import random
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
BOT_TOKEN = "8520271990:AAGHQGPdr01j3Tfn6iWU0JyuH12uHAGR3tw"
CHANNEL_ID = -1001920136785
CHANNEL_NAME = "HenPicture"
# ====================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

user_states = {}
used_links = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = {"step": "captcha"}

    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operation = random.choice(["+", "-", "*"])

    if operation == "+":
        answer = num1 + num2
    elif operation == "-":
        answer = num1 - num2
    else:
        answer = num1 * num2

    user_states[user_id].update({
        "num1": num1, 
        "num2": num2, 
        "operation": operation, 
        "answer": answer
    })

    # ✅ ИСПРАВЛЕНО: все символы экранированы правильно
    captcha_text = "🔐 Для доступа реши простую капчу:

"
    captcha_text += f"*{num1} {operation} {num2} = ?*

"
    captcha_text += "Отправь только число ответом."
    
    await update.message.reply_text(captcha_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    if user_id not in user_states:
        await message.reply_text("👋 Нажми /start, чтобы начать и пройти капчу.")
        return

    state = user_states[user_id]

    if state.get("step") == "captcha":
        try:
            user_answer = int(message.text.strip())
        except ValueError:
            await message.reply_text("❌ Введи только число!")
            return

        if user_answer == state["answer"]:
            await generate_invite_link(update, context)
        else:
            wrong_text = f"❌ Неправильно! Было: *{state['answer']}*

Попробуй еще раз: /start"
            await message.reply_text(wrong_text, parse_mode="Markdown")
            user_states.pop(user_id, None)
    else:
        await message.reply_text("Нажми /start для новой ссылки.")

async def generate_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    try:
        invite_link_obj = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            expire_date=int((datetime.now() + timedelta(hours=24)).timestamp()),
            member_limit=1,
            creates_join_request=False,
            name=f"Invite_{user_id}"
        )

        invite_link = invite_link_obj.invite_link
        used_links.add(invite_link)
        expires_at = datetime.fromtimestamp(invite_link_obj.expire_date)

        success_text = "✅ Капча пройдена!

"
        success_text += f"🔗 Ссылка в **{CHANNEL_NAME}**:
"
        success_text += f"`{invite_link}`

"
        success_text += f"⏰ До: `{expires_at.strftime('%d.%m.%Y %H:%M')}`
"
        success_text += "⚠️ Только 1 вступление!"

        await message.reply_text(success_text, parse_mode="Markdown")

        user_states[user_id]["step"] = "completed"
        user_states[user_id]["link"] = invite_link
        
        logger.info(f"Ссылка выдана {user_id}: {invite_link}")

    except Exception as e:
        logger.error(f"Ошибка ссылки: {e}")
        error_text = "❌ Ошибка создания ссылки!

"
        error_text += "🔧 Бот должен быть АДМИНОМ канала с правом:
"
        error_text += "• 'Приглашать пользователей'

"
        error_text += "Добавь бота как админа и попробуй /start"
        await message.reply_text(error_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "🤖 *HenPicture Invite Bot*

"
    help_text += "🔹 /start — пройти капчу и получить ссылку
"
    help_text += "🔹 /help — это сообщение

"
    help_text += "*Как работает:*
"
    help_text += "1. /start
"
    help_text += "2. Реши пример (1-10)
"
    help_text += "3. Получи уникальную ссылку

"
    help_text += "⚡ Ссылка: 1 человек, 24 часа"
    await update.message.reply_text(help_text, parse_mode="Markdown")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Бот HenPicture запущен!")
    print(f"📢 Канал: {CHANNEL_ID}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
