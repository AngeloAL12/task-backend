import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.db.database import SessionLocal
from app.db.models import Task, User

logger = logging.getLogger(__name__)

async def check_and_send_reminders(bot_app):
    """
    Background worker that runs indefinitely, checking for tasks that are nearing their deadline
    and sending a Telegram notification based on the user's `reminder_preferences`.
    """
    logger.info("🤖 Starting background reminder worker...")
    
    while True:
        try:
            db: Session = SessionLocal()
            now = datetime.now()
            
            # Buscamos tareas no completadas con deadline en el futuro y que el usuario tenga Telegram
            tasks_to_check = db.query(Task).join(User).filter(
                Task.is_completed == False,
                Task.deadline > now,
                User.telegram_id.isnot(None),
                User.is_active == True
            ).all()
            
            for task in tasks_to_check:
                # Calculamos horas restantes (con decimales para precisión)
                time_diff = task.deadline - now
                hours_left = time_diff.total_seconds() / 3600.0
                
                user: User = task.user
                
                # Leemos preferencias (por defecto en models es [24, 12, 2])
                prefs = user.reminder_preferences or []
                
                # Leemos los que ya se mandaron (por defecto [])
                sent = task.sent_reminders or []
                
                for pref_hour in sorted(prefs, reverse=True):
                    # Si faltan igual o menos horas que la preferencia, y NO la hemos enviado ya
                    if hours_left <= pref_hour and pref_hour not in sent:
                        try:
                            # Formateamos el tiempo
                            time_str = f"{pref_hour} horas" if pref_hour != 1 else "1 hora"
                            if hours_left < 1:
                                minutes_left = int(hours_left * 60)
                                time_str = f"{minutes_left} minutos"
                            
                            date_str = task.deadline.strftime("%d/%m %H:%M")
                            msg = (
                                f"⏳ **¡Recordatorio de Tarea!**\n\n"
                                f"Tu tarea **{task.title}** vence pronto.\n"
                                f"📚 **Materia:** {task.subject}\n"
                                f"📅 **Vence el:** {date_str}\n"
                                f"⏰ **Faltan menos de:** {time_str}"
                            )
                            
                            await bot_app.bot.send_message(
                                chat_id=user.telegram_id,
                                text=msg,
                                parse_mode="Markdown"
                            )
                            
                            # Actualizamos los enviados
                            sent.append(pref_hour)
                            
                            # Hacemos flag_modified para indicar a SQLAlchemy que mutamos el JSON
                            from sqlalchemy.orm.attributes import flag_modified
                            task.sent_reminders = sent
                            flag_modified(task, "sent_reminders")
                            
                            db.commit()
                            logger.info(f"✅ Recordatorio de {pref_hour}h enviado a {user.telegram_id} para tarea {task.id}")
                            
                        except Exception as e:
                            logger.error(f"❌ Error enviando recordatorio a {user.telegram_id}: {e}")
            
            db.close()
            
            # Dormir 60 segundos antes de volver a checar
            await asyncio.sleep(60)
            
        except asyncio.CancelledError:
            logger.info("🛑 Background reminder worker stopped.")
            break
        except Exception as e:
            logger.error(f"❌ Error en el worker de recordatorios: {e}")
            await asyncio.sleep(60) # Reintento
