import re
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.db.models import Task, CalendarSource, User
from app.services.ical_service import ICalService

def clean_moodle_title(title: str) -> str:
    if not title: return "Evento sin título"
    # Remove common prefixes
    garbage = ["Vencimiento de ", "Cierre del ", "Entrega de ", "Está pendiente: ", "Se cierra ", "Se abre "]
    clean = title
    for g in garbage:
        clean = clean.replace(g, "")
    return clean.strip()

def extract_subject(event: dict, default_name="General") -> str:
    """Attempts to find the subject in Categories or Description"""
    # 1. Categories (Standard Moodle)
    if event.get("categories"):
        return event["categories"][0]

    # 2. Description (Course: X)
    description = event.get("description", "")
    if description:
        match = re.search(r'(?:Course|Curso):\s*(.*?)(\n|$)', description, re.IGNORECASE)
        if match:
            return match.group(1).strip()
            
    return default_name

class SyncService:
    @staticmethod
    def sync_calendar(source_id: int, db: Session):
        source = db.query(CalendarSource).filter(CalendarSource.id == source_id).first()
        if not source:
            return {"error": "Source not found"}
        
        # Get user to count associated Tasks for logging/debug
        user = db.query(User).filter(User.id == source.user_id).first()
        if not user or not user.telegram_id:
            # We need a telegram_id to create tasks currently
            return {"error": "User does not have a linked Telegram ID"}

        content = ICalService.fetch_ics(source.source_url)
        if not content:
            return {"error": "Failed to fetch ICS content"}
             
        events = ICalService.parse_ics(content)
        
        # --- ANALYSIS Phase ---
        events_map = {} 
        
        for event in events:
            raw_title = event.get("summary", "")
            clean_name = clean_moodle_title(raw_title)
            

            # Anti-Spam (Attendance)
            if "asistencia" in clean_name.lower(): 
                continue

            # Pre-calc subject to correctly group if needed, though grouping is by name (title base)
            # We will resolve subject at upsert time for now, or just extract raw here?
            # Actually, grouping is by clean_name which comes from TITLE. Subject is a property of the task.
            # So we continue as is.


            if clean_name not in events_map:
                events_map[clean_name] = {
                    "open_event": None, 
                    "close_event": None, 
                    "other_events": []
                }
            
            # Classify
            if "Se abre" in raw_title:
                events_map[clean_name]["open_event"] = event
            elif "Se cierra" in raw_title:
                events_map[clean_name]["close_event"] = event
            else:
                events_map[clean_name]["other_events"].append(event)

        # --- SAVING Phase ---
        synced_count = 0
        updated_count = 0
        found_subjects = set()
        mapping = source.subject_mapping or {}

        
        for name, data in events_map.items():
            
            # CASE 1: EXAMS (Open + Close, or just Close)
            final_event = None
            title_suffix = ""
            
            if data["close_event"]:
                final_event = data["close_event"]
                if data["open_event"]:
                    # Merge logic
                    # Store the REAL start date (from the Open event) in a new field if possible, or just for display
                    start_date = data["open_event"]["start_time"]
                    final_event["real_start_date"] = start_date # Temporary key
                    
                    title_suffix = ""
            
            elif data["other_events"]:
                for evt in data["other_events"]:
                    # Resolve Subject
                    raw_subject = extract_subject(evt, default_name=None)
                    final_subject = source.name
                    if raw_subject:
                        found_subjects.add(raw_subject)
                        final_subject = mapping.get(raw_subject, raw_subject)

                    res = SyncService._upsert_task(evt, name, final_subject, source, user, db)
                    if res == "created": synced_count += 1
                    elif res == "updated": updated_count += 1
                continue 
                
            if final_event:
                full_title = f"{name}{title_suffix}"
                
                # Resolve Subject (use final_event)
                raw_subject = extract_subject(final_event, default_name=None)
                final_subject = source.name
                if raw_subject:
                    found_subjects.add(raw_subject)
                    final_subject = mapping.get(raw_subject, raw_subject)

                res = SyncService._upsert_task(final_event, full_title, final_subject, source, user, db)
                if res == "created": synced_count += 1
                elif res == "updated": updated_count += 1

        source.last_synced_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "new_tasks": synced_count,
            "updated_tasks": updated_count,
            "found_subjects": list(found_subjects)
        }

    @staticmethod
    def _upsert_task(event, final_title, subject, source, user, db):
        # Determine deadline and start_date
        # For ICal events, start_time usually represents the 'event' time.
        # For a task/deadline, that is the deadline.
        deadline = event["start_time"]
        start_date = event.get("real_start_date") # Extracted from merge logic
        
        existing = db.query(Task).filter(Task.external_uid == event["uid"]).first()
        
        if existing:
            changed = False
            if existing.deadline != deadline:
                existing.deadline = deadline
                changed = True
            if existing.title != final_title:
                existing.title = final_title
                changed = True
            if existing.subject != subject:
                existing.subject = subject
                changed = True
            if existing.start_date != start_date:
                existing.start_date = start_date
                changed = True
                
            return "updated" if changed else "ignored"
        else:
            new_task = Task(
                telegram_id=user.telegram_id,
                title=final_title,
                subject=subject,
                deadline=deadline,
                start_date=start_date,
                priority="alta" if "Examen" in final_title else "media",
                source="ical",
                external_uid=event["uid"],
                calendar_source_id=source.id
            )
            db.add(new_task)
            return "created"
