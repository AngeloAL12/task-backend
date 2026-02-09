import io
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Task
from app.services.ai_service import analyze_intent, analyze_audio_intent

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"¡Hola {user_name}! 👋\n\n"
        "Soy tu asistente personal con IA. 🧠\n"
        "Puedo organizar tus tareas por ti.\n\n"
        "Pruébame diciendo:\n"
        "🎤 *Mándame una nota de voz*\n"
        "📝 *'Recordar pagar la luz mañana'*\n"
        "📋 Usa /listar para ver tus pendientes.",
        parse_mode="Markdown"
    )

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    db = SessionLocal()
    try:
        # 🔥 FILTRAMOS: Solo tareas de este usuario
        tasks = db.query(Task).filter(
            Task.is_completed == False,
            Task.telegram_id == user_id
        ).order_by(Task.deadline).all()

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
    user_id = update.effective_user.id  # 🔥 ID DEL USUARIO
    try:
        task_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Uso correcto: `/borrar [ID]`")
        return

    db = SessionLocal()
    try:
        # 🔥 SEGURIDAD: Solo borramos si el ID coincide Y el dueño es el usuario
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.telegram_id == user_id
        ).first()

        if not task:
            await update.message.reply_text("🤷‍♂️ No encontré esa tarea (o no es tuya).")
            return

        title = task.title
        db.delete(task)
        db.commit()
        await update.message.reply_text(f"🗑️ Tarea **{title}** eliminada.", parse_mode="Markdown")
    finally:
        db.close()


# --- 2. MANEJO DE TEXTO (INTELIGENTE) ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # 🔥 ID DEL USUARIO
    user_text = update.message.text
    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    db = SessionLocal()
    try:
        # A. Contexto: Solo pasamos a la IA las tareas DE ESTE USUARIO
        tasks = db.query(Task).filter(
            Task.is_completed == False,
            Task.telegram_id == user_id
        ).all()
        tasks_list = [f"{t.id}: {t.title}" for t in tasks]

        # B. Consultar a Gemini
        ai_decision = await asyncio.to_thread(analyze_intent, user_text, tasks_list)

        # C. Ejecutar Acción (Pasamos user_id)
        await execute_ai_action(update, db, ai_decision, user_id)

    except Exception as e:
        await update.message.reply_text(f"🔥 Error: {str(e)}")
    finally:
        db.close()


# --- 3. MANEJO DE VOZ (INTELIGENTE) ---

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # 🔥 ID DEL USUARIO
    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(chat_id=chat_id, action="upload_voice")

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        buffer = io.BytesIO()
        await voice_file.download_to_memory(buffer)
        audio_bytes = buffer.getvalue()

        db = SessionLocal()
        try:
            # Contexto filtrado por usuario
            tasks = db.query(Task).filter(
                Task.is_completed == False,
                Task.telegram_id == user_id
            ).all()
            tasks_list = [f"{t.id}: {t.title}" for t in tasks]

            ai_decision = await asyncio.to_thread(analyze_audio_intent, audio_bytes, tasks_list)

            # Ejecutar con user_id
            await execute_ai_action(update, db, ai_decision, user_id)

        finally:
            db.close()

    except Exception as e:
        await update.message.reply_text(f"🔥 Error procesando audio: {str(e)}")


# --- 4. LÓGICA COMÚN (Ejecutor de acciones) ---

async def execute_ai_action(update: Update, db, ai_decision, user_id: int):
    """
    Función auxiliar que recibe el user_id para asegurar
    que nadie toque las tareas de otro.
    """

    if ai_decision.action == "complete":
        # 🔥 Filtramos por ID de tarea Y ID de usuario
        task = db.query(Task).filter(
            Task.id == ai_decision.target_id,
            Task.telegram_id == user_id
        ).first()

        if task:
            task.is_completed = True
            db.commit()
            await update.message.reply_text(f"✅ Tarea completada:\n~~{task.title}~~", parse_mode="Markdown")
        else:
            await update.message.reply_text(
                f"🤔 La IA quiso completar la tarea {ai_decision.target_id}, pero no la encontré en tu lista.")

    elif ai_decision.action == "delete":
        # 🔥 Filtramos por ID de tarea Y ID de usuario
        task = db.query(Task).filter(
            Task.id == ai_decision.target_id,
            Task.telegram_id == user_id
        ).first()

        if task:
            db.delete(task)
            db.commit()
            await update.message.reply_text(f"🗑️ Tarea eliminada: **{task.title}**", parse_mode="Markdown")
        else:
            await update.message.reply_text("🤷‍♂️ No encontré esa tarea para borrar.")

    elif ai_decision.action == "chat":
        await update.message.reply_text(f"🗣️ {ai_decision.reply_text}")

    elif ai_decision.action == "create":
        # 🔥 Al crear, le pegamos la etiqueta del dueño (telegram_id)
        new_task = Task(
            telegram_id=user_id,  # <--- ¡ESTO ES LO MÁS IMPORTANTE!
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
        msg = (f"✅ **Tarea Guardada**\n\n"
               f"📝 **{new_task.title}**\n"
               f"📅 {date_str}\n"
               f"🚨 Prioridad: {new_task.priority.upper()}")

        await update.message.reply_text(msg, parse_mode="Markdown")


# --- 5. CONFIGURACIÓN DEL BOT (Igual que antes) ---

def create_bot_app():
    application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("listar", list_tasks))
    application.add_handler(CommandHandler("borrar", delete_task))
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(echo_handler)
    voice_handler = MessageHandler(filters.VOICE, handle_voice)
    application.add_handler(voice_handler)
    application.add_handler(CommandHandler("start", start))
    return application