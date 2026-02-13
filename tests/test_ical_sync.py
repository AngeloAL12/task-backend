import sys
import os
from unittest.mock import MagicMock

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
UID:12345@moodle.com
DTSTART:20231010T100000Z
SUMMARY:Tarea de Prueba Moodle
DESCRIPTION:Descripcion de la tarea
END:VEVENT
BEGIN:VEVENT
UID:67890@moodle.com
DTSTART:20231011T120000Z
SUMMARY:Otra Tarea
END:VEVENT
END:VCALENDAR"""

def test_ical_parsing():
    print("Testing ICal Service Parsing...")
    events = ICalService.parse_ics(SAMPLE_ICS)
    assert len(events) == 2
    assert events[0]["uid"] == "12345@moodle.com"
    assert events[0]["summary"] == "Tarea de Prueba Moodle"
    assert isinstance(events[0]["start_time"], datetime)
    print("✅ ICal Parsing Passed")

def test_sync_logic():
    print("Testing Sync Service Logic...")
    
    # Mock DB Session
    mock_db = MagicMock()
    
    # Mock User
    mock_user = User(id=1, telegram_id=999)
    # Mock Calendar Source
    mock_source = CalendarSource(id=1, user_id=1, source_url="http://test.com/cal.ics", name="Moodle")
    
    # Setup DB Query Returns
    # First query gets source
    # Second query gets user
    # Subsequent queries check for existing tasks (simulate none exist first)
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_source, # Get Source
        mock_user,   # Get User
        None,        # Check task 1 (not found)
        None         # Check task 2 (not found)
    ]
    
    # Mock Fetch
    ICalService.fetch_ics = MagicMock(return_value=SAMPLE_ICS)
    
    # Run Sync
    result = SyncService.sync_calendar(1, mock_db)
    
    # Assertions
    print(f"Sync Result: {result}")
    assert result["status"] == "success"
    assert result["new_tasks"] == 2
    
    # Verify DB Add calls (should add 2 tasks)
    assert mock_db.add.call_count == 2
    
    print("✅ Sync Logic Passed")

if __name__ == "__main__":
    try:
        test_ical_parsing()
        test_sync_logic()
        print("🎉 All Verification Tests Passed!")
    except AssertionError as e:
        print(f"❌ Test Failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
