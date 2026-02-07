import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from sqlalchemy import or_

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Task
# IMPORTANTE: Importamos la nueva función inteligente
from app.services.ai_service import analyze_intent


# --- 1. COMANDOS CLÁSICOS (Listar y Borrar) ---
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(Task.is_completed == False).order_by(Task.deadline).all()
        if not tasks:
            await update.message.reply_text("🎉 ¡Eres libre! No tienes tareas pendientes.")
            return

        msg = "📋 **Tus Tareas Pendientes:**\n\n"
        for t in tasks:
            icon = "🔥" if t.priority == "alta" else "🔹"
            date = t.deadline.strftime('%d/%m %H:%M') if t.deadline else "Sin fecha"
            msg += f"{icon} **{t.title}**\n   └ 📅 {date} (ID: {t.id})\n\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
    finally:
        db.close()


async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        task_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Uso: `/borrar [ID]`")
        return

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            await update.message.reply_text("🤷‍♂️ No encontré esa tarea.")
            return

        title = task.title
        db.delete(task)
        db.commit()
        await update.message.reply_text(f"🗑️ Tarea **{title}** eliminada.")
    finally:
        db.close()


# --- 2. CEREBRO INTELIGENTE (El Router) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id

    # Feedback visual ("Escribiendo...")
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    db = SessionLocal()
    try:
        # A. OBTENER CONTEXTO: Leemos las tareas pendientes de la DB
        tasks = db.query(Task).filter(Task.is_completed == False).all()
        # Creamos una lista simplificada para la IA: "ID: Título"
        tasks_list = [f"{t.id}: {t.title}" for t in tasks]

        # B. CONSULTAR A LA IA: Le pasamos el texto Y la lista de tareas
        ai_decision = await asyncio.to_thread(analyze_intent, user_text, tasks_list)

        # C. EJECUTAR LA ACCIÓN DECIDIDA
        if ai_decision.action == "complete":
            # Caso 1: Completar tarea
            task = db.query(Task).filter(Task.id == ai_decision.target_id).first()
            if task:
                task.is_completed = True
                db.commit()
                await update.message.reply_text(f"✅ ¡Excelente! Tarea completada:\n~~{task.title}~~",
                                                parse_mode="Markdown")
            else:
                await update.message.reply_text("🤔 La IA quiso completar una tarea que no encontré.")

        elif ai_decision.action == "delete":
            # Caso 2: Borrar tarea
            task = db.query(Task).filter(Task.id == ai_decision.target_id).first()
            if task:
                db.delete(task)
                db.commit()
                await update.message.reply_text(f"🗑️ Tarea eliminada: **{task.title}**", parse_mode="Markdown")
            else:
                await update.message.reply_text("🤷‍♂️ No encontré esa tarea para borrar.")

        elif ai_decision.action == "chat":
            # Caso 3: Charla casual
            await update.message.reply_text(ai_decision.reply_text or "¡Hola!")

        else:  # action == "create"
            # Caso 4: Crear nueva tarea
            new_task = Task(
                title=ai_decision.title,
                subject="Telegram",
                deadline=datetime.fromisoformat(ai_decision.deadline) if ai_decision.deadline else None,
                priority=ai_decision.priority or "media",
                source="telegram"
            )
            db.add(new_task)
            db.commit()
            db.refresh(new_task)

            date_str = new_task.deadline.strftime('%d/%m %H:%M') if new_task.deadline else "Hoy"
            msg = (f"✅ **Tarea Guardada**\n"
                   f"📝 {new_task.title}\n"
                   f"📅 {date_str} | 🚨 {new_task.priority.upper()}")
            await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"🔥 Error: {str(e)}")
    finally:
        db.close()


# --- 3. CONFIGURACIÓN ---
def create_bot_app():
    application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("listar", list_tasks))
    application.add_handler(CommandHandler("borrar", delete_task))

    # Manejamos todo el texto con la nueva función inteligente
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(echo_handler)

    return application