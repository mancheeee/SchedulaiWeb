from googleapiclient.discovery import build
from datetime import datetime
from google.oauth2.credentials import Credentials


def get_upcoming_events(credentials_dict, max_results=10):
    creds = Credentials(**credentials_dict)

    service = build("calendar", "v3", credentials=creds)

    now = datetime.utcnow().isoformat() + "Z"  # 'Z' = UTC time
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])
    return events
