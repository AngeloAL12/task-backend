import sys
import os
from unittest.mock import MagicMock, call

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.ical_service import ICalService
from app.services.sync_service import SyncService
from app.db.models import Task, User, CalendarSource
from datetime import datetime

# Mock ICal Content
SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Moodle//NONSGML//EN
BEGIN:VEVENT
UID:101@moodle.com
DTSTART:20231010T100000Z
SUMMARY:Vencimiento de Tarea 1
DESCRIPTION:Course: Moodle Course A
END:VEVENT
BEGIN:VEVENT
UID:102@moodle.com
DTSTART:20231011T120000Z
SUMMARY:Cierre del Examen
DESCRIPTION:Course: Moodle Course B
END:VEVENT
END:VCALENDAR"""

def test_mapping_logic():
    print("Testing Subject Mapping Logic...")
    
    # Mock DB Session
    mock_db = MagicMock()
    
    # Mock User
    mock_user = User(id=1, telegram_id=999)
    
    # Mock Calendar Source with Mapping
    mock_source = CalendarSource(
        id=1, 
        user_id=1, 
        source_url="http://test.com/cal.ics", 
        name="Moodle",
        subject_mapping={
            "Moodle Course A": "Matemáticas",
             # Moodle Course B is NOT mapped
        }
    )
    
    # Setup DB Query Returns
    # 1. Get Source
    # 2. Get User
    # 3. Check Task 1 (not found)
    # 4. Check Task 2 (not found)
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_source, 
        mock_user,   
        None,        
        None         
    ]
    
    # Mock Fetch
    ICalService.fetch_ics = MagicMock(return_value=SAMPLE_ICS)
    ICalService.parse_ics = MagicMock(return_value=[
        {
            "uid": "101@moodle.com",
            "summary": "Vencimiento de Tarea 1",
            "start_time": datetime(2023, 10, 10, 10, 0),
            "description": "Course: Moodle Course A",
            "categories": [],
        },
        {
            "uid": "102@moodle.com",
            "summary": "Cierre del Examen",
            "start_time": datetime(2023, 10, 11, 12, 0),
            "description": "Course: Moodle Course B",
            "categories": [],
        }
    ])
    
    # Run Sync
    result = SyncService.sync_calendar(1, mock_db)
    
    # Assertions
    print(f"Sync Result: {result}")
    
    found_subjects = result.get("found_subjects", [])
    print(f"Found Subjects: {found_subjects}")
    
    assert "Moodle Course A" in found_subjects
    assert "Moodle Course B" in found_subjects
    
    # Verify created tasks
    # We expect 2 tasks to be added
    assert mock_db.add.call_count == 2
    
    # Inspect the Task objects passed to add
    # Call args list: [call(Task(...)), call(Task(...))]
    tasks_created = [call_args[0][0] for call_args in mock_db.add.call_args_list]
    
    task_a = next(t for t in tasks_created if t.external_uid == "101@moodle.com")
    task_b = next(t for t in tasks_created if t.external_uid == "102@moodle.com")
    
    print(f"Task A Subject: {task_a.subject}")
    print(f"Task B Subject: {task_b.subject}")
    
    # Check Mapping Application
    assert task_a.subject == "Matemáticas", f"Expected 'Matemáticas', got '{task_a.subject}'"
    
    # Check Default Behavior (No Mapping)
    # If mapping not found, it should use the raw subject (Moodle Course B) OR Source Name depending on logic?
    # Logic: final_subject = mapping.get(raw, raw) -> So it should be raw subject "Moodle Course B"
    assert task_b.subject == "Moodle Course B", f"Expected 'Moodle Course B', got '{task_b.subject}'"

    print("✅ Mapping Logic Passed")

if __name__ == "__main__":
    try:
        test_mapping_logic()
        print("🎉 Verification Successful!")
    except AssertionError as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
