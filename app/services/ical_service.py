import requests
from icalendar import Calendar
from datetime import datetime
from typing import List, Dict, Optional

class ICalService:
    @staticmethod
    def fetch_ics(url: str) -> Optional[str]:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching ICS: {e}")
            return None

    @staticmethod
    def parse_ics(content: str) -> List[Dict]:
        calendar = Calendar.from_ical(content)
        events = []

        for component in calendar.walk():
            if component.name == "VEVENT":
                summary = component.get('summary')
                dtstart = component.get('dtstart').dt
                uid = component.get('uid')
                description = component.get('description')
                
                # Normalize datetime (some are dates, some are datetimes)
                if not isinstance(dtstart, datetime):
                     dtstart = datetime.combine(dtstart, datetime.min.time())
                
                # Remove timezone info for simplicity (or handle it properly if needed)
                if dtstart.tzinfo:
                    dtstart = dtstart.replace(tzinfo=None)

                events.append({
                    "summary": str(summary),
                    "start_time": dtstart,
                    "uid": str(uid),
                    "description": str(description) if description else ""
                })
        
        return events
