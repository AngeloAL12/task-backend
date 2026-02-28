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
            
            tasks_to_check = db.query(Task).join(User).filter(
                Task.is_completed == False,
                Task.deadline > now,
                User.telegram_id.isnot(None),
                User.is_active == True
            ).all()
            
            for task in tasks_to_check:            
                time_diff = task.deadline - now
                hours_left = time_diff.total_seconds() / 3600.0
                
                user: User = task.user
                
                # Leemos preferencias (si es None, usamos el default del sistema: 24, 12, 2)
                prefs = user.reminder_preferences if user.reminder_preferences is not None else [24, 12, 2]
                
                # Leemos los que ya se mandaron (por defecto [])
                sent = task.sent_reminders or []
                
                # Buscamos todas las preferencias que ya pasaron su umbral (con tolerancia de ~1 minuto)
                # y que no han sido enviadas.
                triggered_prefs = [p for p in prefs if hours_left <= p + 0.02 and p not in sent]
                
                if triggered_prefs:
                    # La preferencia más relevante es la menor de las que se dispararon
                    target_pref = min(triggered_prefs)
                    
                    try:
                        # Formateamos el tiempo
                        time_str = f"{target_pref} horas" if target_pref != 1 else "1 hora"
                        if hours_left < 1:
                            minutes_left = max(int(hours_left * 60), 0)
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
                        
                        # Actualizamos los enviados, marcando TODOS los disparados para no mandar
                        # los avisos mayores (ej. 24h) si la tarea se creó cuando ya faltaban 2 horas
                        for p in triggered_prefs:
                            sent.append(p)
                        
                        # Hacemos flag_modified para indicar a SQLAlchemy que mutamos el JSON
                        from sqlalchemy.orm.attributes import flag_modified
                        task.sent_reminders = sent
                        flag_modified(task, "sent_reminders")
                        
                        db.commit()
                        logger.info(f"✅ Recordatorio de {target_pref}h enviado a {user.telegram_id} para tarea {task.id}")
                        
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
