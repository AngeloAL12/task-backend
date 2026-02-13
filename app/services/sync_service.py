from sqlalchemy.orm import Session
from datetime import datetime
from app.db.models import Task, CalendarSource, User
from app.services.ical_service import ICalService

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
        
        synced_count = 0
        updated_count = 0

        for event in events:
            # Check if task already exists
            existing_task = db.query(Task).filter(
                Task.external_uid == event["uid"]
            ).first()

            if existing_task:
                # Update logic
                updated = False
                if existing_task.deadline != event["start_time"]:
                    existing_task.deadline = event["start_time"]
                    updated = True
                
                if existing_task.title != event["summary"]:
                    existing_task.title = event["summary"]
                    updated = True
                
                if updated:
                    updated_count += 1
            else:
                # Create new task
                new_task = Task(
                    telegram_id=user.telegram_id,
                    title=event["summary"],
                    subject=source.name, # Use source name as subject (e.g. "Moodle")
                    deadline=event["start_time"],
                    priority="media",
                    source="ical",
                    external_uid=event["uid"],
                    calendar_source_id=source.id
                )
                db.add(new_task)
                synced_count += 1
        
        source.last_synced_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "new_tasks": synced_count,
            "updated_tasks": updated_count
        }
