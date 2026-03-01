import requests
from icalendar import Calendar
from datetime import datetime
from typing import List, Dict, Optional

from app.core.url_safety import is_url_safe_for_fetch

# Timeout and redirect limit for SSRF defense
FETCH_TIMEOUT_SECONDS = 15
FETCH_MAX_REDIRECTS = 3


class URLNotAllowedError(ValueError):
    """Raised when a URL is rejected by SSRF validation."""


class ICalService:
    @staticmethod
    def fetch_ics(url: str) -> Optional[str]:
        if not is_url_safe_for_fetch(url):
            raise URLNotAllowedError("URL no permitida para calendario.")
        try:
            response = requests.get(
                url,
                timeout=FETCH_TIMEOUT_SECONDS,
                allow_redirects=True,
                max_redirects=FETCH_MAX_REDIRECTS,
            )
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
                
                dtend = component.get('dtend')
                categories = component.get('categories')
                
                # Normalize datetime (some are dates, some are datetimes)
                if not isinstance(dtstart, datetime):
                     dtstart = datetime.combine(dtstart, datetime.min.time())
                
                # Remove timezone info for simplicity (or handle it properly if needed)
                if dtstart.tzinfo:
                    dtstart = dtstart.replace(tzinfo=None)

                # Process dtend
                if dtend:
                    dtend = dtend.dt
                    if not isinstance(dtend, datetime):
                        dtend = datetime.combine(dtend, datetime.min.time())
                    if dtend.tzinfo:
                        dtend = dtend.replace(tzinfo=None)

                # Process categories
                category_list = []
                if categories:
                    # Categories can be a list or a single object depending on icalendar version/data
                    # But usually it's a vCategory object which behaves like a list or string
                    if hasattr(categories, "cats"):
                        for cat in categories.cats:
                            category_list.append(str(cat))
                    else:
                        # Fallback
                        category_list.append(str(categories))

                events.append({
                    "summary": str(summary),
                    "start_time": dtstart,
                    "end_time": dtend, # Added end_time
                    "uid": str(uid),
                    "description": str(description) if description else "",
                    "categories": category_list # Added categories
                })
        
        return events
