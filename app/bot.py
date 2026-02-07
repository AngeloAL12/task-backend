import logging
import asyncio
import sys
import os

# Add the project root to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Task
from app.services.ai_service import parse_task_with_ai

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Este es el 'Controlador' de Telegram.
    Recibe texto -> Llama a Gemini -> Guarda en DB -> Responde.
    """
    user_text = update.message.text

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        task_data = await asyncio.to_thread(parse_task_with_ai, user_text)

        db = SessionLocal()
        try:
            new_task = Task(**task_data.dict(), source="telegram")
            db.add(new_task)
            db.commit()
            db.refresh(new_task)

            response_msg = (
                f"✅ **Tarea Guardada**\n\n"
                f"📝 **{new_task.title}**\n"
                f"📅 {new_task.deadline.strftime('%d/%m %H:%M') if new_task.deadline else 'Sin fecha'}\n"
                f"🚨 Prioridad: {new_task.priority.upper()}"
            )
        except Exception as e:
            db.rollback()
            response_msg = f"❌ Error guardando en DB: {str(e)}"
        finally:
            db.close()

    except Exception as e:
        response_msg = f"🔥 Error de IA: {str(e)}"

    await update.message.reply_text(response_msg, parse_mode="Markdown")


if __name__ == '__main__':
    application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(echo_handler)

    print("🤖 Bot de Tareas iniciado... (Presiona Ctrl+C para detener)")
    application.run_polling()