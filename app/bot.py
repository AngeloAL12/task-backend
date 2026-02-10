import io
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Task, Subject  # <--- Importamos Subject
from app.services.ai_service import analyze_intent, analyze_audio_intent


# --- 1. COMANDOS BÁSICOS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"¡Hola {user_name}! 👋\n\n"
        "Soy tu asistente personal con IA. 🧠\n"
        "Puedo organizar tus tareas por ti y detectar tus materias automáticamente según tu horario.\n\n"
        "Pruébame diciendo:\n"
        "🎤 *Mándame una nota de voz*\n"
        "📝 *'Recordar examen de redes mañana'*\n"
        "📋 Usa /listar para ver tus pendientes.",
        parse_mode="Markdown"
    )


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
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
            # Mostramos la materia detectada (subject)
            msg += f"{icon} **{t.title}**\n   └ 📚 {t.subject} | 📅 {date}\n\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
    finally:
        db.close()


async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Comando manual: /borrar 123
    user_id = update.effective_user.id
    try:
        if not context.args:
            await update.message.reply_text("❌ Uso correcto: `/borrar [ID]`")
            return
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ El ID debe ser un número.")
        return

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id, Task.telegram_id == user_id).first()
        if not task:
            await update.message.reply_text("🤷‍♂️ No encontré esa tarea.")
            return

        title = task.title
        db.delete(task)
        db.commit()
        await update.message.reply_text(f"🗑️ Tarea **{title}** eliminada.", parse_mode="Markdown")
    finally:
        db.close()


# --- COMANDO DEBUG (TEMPORAL) ---
# Para agregar horarios sin tener la Web todavía
async def debug_add_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Uso: /sethorario Compiladores | Lunes 08:00-10:00
    user_id = update.effective_user.id
    try:
        raw_text = " ".join(context.args)
        if "|" not in raw_text:
            await update.message.reply_text("❌ Formato: `/sethorario Materia | Horario`")
            return

        name, schedule = raw_text.split("|", 1)

        db = SessionLocal()
        new_subject = Subject(telegram_id=user_id, name=name.strip(), schedule_text=schedule.strip())
        db.add(new_subject)
        db.commit()
        db.close()

        await update.message.reply_text(f"✅ Materia agregada: **{name.strip()}**\n🕒 {schedule.strip()}",
                                        parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# --- 2. MANEJO DE TEXTO (INTELIGENTE) ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    db = SessionLocal()
    try:
        # A. Contexto Tareas
        tasks = db.query(Task).filter(Task.is_completed == False, Task.telegram_id == user_id).all()
        tasks_list = [f"{t.id}: {t.title}" for t in tasks]

        # B. Contexto Horario (Desde DB) 📅
        subjects = db.query(Subject).filter(Subject.telegram_id == user_id).all()
        if subjects:
            schedule_list = [f"- {s.name}: {s.schedule_text}" for s in subjects]
            user_schedule_str = "\n".join(schedule_list)
        else:
            user_schedule_str = ""

        # C. Consultar a Gemini (Pasando el horario dinámico)
        ai_decision = await asyncio.to_thread(
            analyze_intent,
            user_text,
            tasks_list,
            user_schedule_str
        )

        # D. Ejecutar Acción
        await execute_ai_action(update, db, ai_decision, user_id)

    except Exception as e:
        print(f"Error en handle_message: {e}")
        await update.message.reply_text("🔥 Ocurrió un error procesando tu mensaje.")
    finally:
        db.close()


# --- 3. MANEJO DE VOZ (INTELIGENTE) ---

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(chat_id=chat_id, action="upload_voice")

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        buffer = io.BytesIO()
        await voice_file.download_to_memory(buffer)
        audio_bytes = buffer.getvalue()

        db = SessionLocal()
        try:
            # Contexto Tareas
            tasks = db.query(Task).filter(Task.is_completed == False, Task.telegram_id == user_id).all()
            tasks_list = [f"{t.id}: {t.title}" for t in tasks]

            # Contexto Horario
            subjects = db.query(Subject).filter(Subject.telegram_id == user_id).all()
            if subjects:
                schedule_list = [f"- {s.name}: {s.schedule_text}" for s in subjects]
                user_schedule_str = "\n".join(schedule_list)
            else:
                user_schedule_str = ""

            # Consultar AI con Audio + Horario
            ai_decision = await asyncio.to_thread(
                analyze_audio_intent,
                audio_bytes,
                tasks_list,
                user_schedule_str
            )

            await execute_ai_action(update, db, ai_decision, user_id)

        finally:
            db.close()

    except Exception as e:
        print(f"Error en voz: {e}")
        await update.message.reply_text("🔥 Error procesando el audio.")


# --- 4. LÓGICA COMÚN (Ejecutor de acciones) ---

async def execute_ai_action(update: Update, db, ai_decision, user_id: int):
    # NOTA: Para completar/borrar, la IA nos devuelve el 'target_id' que identificó

    if ai_decision.action == "complete":
        task = db.query(Task).filter(Task.id == ai_decision.target_id, Task.telegram_id == user_id).first()
        if task:
            task.is_completed = True
            db.commit()
            await update.message.reply_text(f"✅ Tarea completada:\n~~{task.title}~~", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"🤔 No encontré la tarea {ai_decision.target_id}.")

    elif ai_decision.action == "delete":
        task = db.query(Task).filter(Task.id == ai_decision.target_id, Task.telegram_id == user_id).first()
        if task:
            db.delete(task)
            db.commit()
            await update.message.reply_text(f"🗑️ Tarea eliminada: **{task.title}**", parse_mode="Markdown")
        else:
            await update.message.reply_text("🤷‍♂️ No encontré esa tarea.")

    elif ai_decision.action == "chat":
        reply = ai_decision.reply_text or "Entendido."
        await update.message.reply_text(f"🗣️ {reply}")

    elif ai_decision.action == "create":
        # Aquí usamos la materia que detectó la IA (o "General" si no supo)
        subject_detected = ai_decision.subject or "General"

        new_task = Task(
            telegram_id=user_id,
            title=ai_decision.title,
            subject=subject_detected,  # <--- USAMOS LA IA
            deadline=datetime.fromisoformat(ai_decision.deadline) if ai_decision.deadline else None,
            priority=ai_decision.priority or "media",
            source="telegram"
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        date_str = new_task.deadline.strftime('%d/%m %H:%M') if new_task.deadline else "Hoy"

        msg = (f"✅ **Tarea Guardada**\n\n"
               f"📚 **{new_task.subject}**\n"  # Confirmación visual
               f"📝 {new_task.title}\n"
               f"📅 {date_str}\n"
               f"🚨 Prioridad: {new_task.priority.upper()}")

        await update.message.reply_text(msg, parse_mode="Markdown")


# --- 5. CONFIGURACIÓN DEL BOT ---

def create_bot_app():
    application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("listar", list_tasks))
    application.add_handler(CommandHandler("borrar", delete_task))

    # Comando Debug para agregar horarios sin Web
    application.add_handler(CommandHandler("sethorario", debug_add_schedule))

    # Mensajes
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(echo_handler)

    # Voz
    voice_handler = MessageHandler(filters.VOICE, handle_voice)
    application.add_handler(voice_handler)

    return application