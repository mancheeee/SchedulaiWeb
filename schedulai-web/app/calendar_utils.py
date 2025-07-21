from datetime import datetime, timedelta
import pytz
from google.oauth2.credentials import Credentials
from dateutil import parser
from datetime import timedelta
from typing import Optional
from dateutil import tz
from googleapiclient.discovery import build
from difflib import get_close_matches
from pymongo import MongoClient
import os
from dotenv import load_dotenv


def ensure_aware(iso_str, local_tz):
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    return dt.astimezone(local_tz)


def find_free_slot(credentials_dict, date, start_range, end_range, duration_minutes):
    free_slots = get_all_free_slots(
        credentials_dict, date, start_range, end_range, duration_minutes
    )
    return free_slots[0] if free_slots else None


def get_all_free_slots(
    credentials_dict, date, start_range, end_range, duration_minutes
):
    creds = Credentials(**credentials_dict)
    service = build("calendar", "v3", credentials=creds)

    tz = pytz.timezone("Asia/Dubai")
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    today = datetime.now(tz).date()

    # Parse initial start and end time ranges
    start_dt = tz.localize(
        datetime.strptime(start_range, "%H:%M").replace(
            year=date_obj.year, month=date_obj.month, day=date_obj.day
        )
    )
    end_dt = tz.localize(
        datetime.strptime(end_range, "%H:%M").replace(
            year=date_obj.year, month=date_obj.month, day=date_obj.day
        )
    )

    # ⏳ Adjust start time if user asked for today's slots
    if date_obj.date() == today:
        now = datetime.now(tz)
        # Round current time to next 15-minute mark
        minute = (now.minute // 15 + 1) * 15
        if minute >= 60:
            now = now.replace(hour=now.hour + 1, minute=0, second=0, microsecond=0)
        else:
            now = now.replace(minute=minute, second=0, microsecond=0)

        # Update start_dt if it's earlier than the adjusted "now"
        if now > start_dt:
            start_dt = now

    # Prepare free/busy query
    body = {
        "timeMin": start_dt.isoformat(),
        "timeMax": end_dt.isoformat(),
        "timeZone": "Asia/Dubai",
        "items": [{"id": "primary"}],
    }

    events_result = service.freebusy().query(body=body).execute()
    busy = events_result["calendars"]["primary"].get("busy", [])

    busy_times = [
        {"start": ensure_aware(b["start"], tz), "end": ensure_aware(b["end"], tz)}
        for b in busy
    ]

    free_slots = []
    current = start_dt

    while current + timedelta(minutes=duration_minutes) <= end_dt:
        slot_start = current
        slot_end = current + timedelta(minutes=duration_minutes)

        # Check overlap with busy periods
        overlaps = any(
            slot_start < b["end"] and slot_end > b["start"] for b in busy_times
        )

        if not overlaps:
            free_slots.append(
                {"start": slot_start.isoformat(), "end": slot_end.isoformat()}
            )

        current += timedelta(minutes=duration_minutes)

    return free_slots


def create_calendar_event(credentials_dict, title, start, end, attendees):
    creds = Credentials(**credentials_dict)
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": title,
        "start": {"dateTime": start, "timeZone": ""},
        "end": {"dateTime": end, "timeZone": "Asia/Dubai"},
        "attendees": [{"email": email} for email in attendees],
        "reminders": {"useDefault": True},
    }

    created_event = service.events().insert(calendarId="primary", body=event).execute()
    return created_event


def get_events_for_day(credentials_dict, date):
    creds = Credentials(**credentials_dict)
    service = build("calendar", "v3", credentials=creds)

    tz = pytz.timezone("Asia/Dubai")
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    start_of_day = tz.localize(
        datetime(date_obj.year, date_obj.month, date_obj.day, 0, 0)
    ).isoformat()
    end_of_day = tz.localize(
        datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59)
    ).isoformat()

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])
    return [
        {
            "id": e["id"],
            "summary": e.get("summary", "Untitled"),
            "start": e["start"].get("dateTime", ""),
            "end": e["end"].get("dateTime", ""),
        }
        for e in events
    ]


def delete_event(credentials_dict, date, start_range, end_range, title=None):
    creds = Credentials(**credentials_dict)
    service = build("calendar", "v3", credentials=creds)
    local_tz = pytz.timezone("Asia/")

    try:
        start_datetime_str = f"{date}T{start_range}:00"
        end_datetime_str = f"{date}T{end_range}:00"

        start_dt = local_tz.localize(
            datetime.strptime(start_datetime_str, "%Y-%m-%dT%H:%M:%S")
        )
        end_dt = local_tz.localize(
            datetime.strptime(end_datetime_str, "%Y-%m-%dT%H:%M:%S")
        )

        print("🔍 Deleting event titled:", title)
        print("🔎 From:", start_dt)
        print("🔎 To  :", end_dt)

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        items = events_result.get("items", [])
        print(f"📅 Found {len(items)} events in time range.")

        for event in items:
            event_title = event.get("summary", "")
            event_start = event.get("start", {}).get("dateTime", "")
            if not event_start:
                continue

            event_dt = ensure_aware(event_start, local_tz)
            delta = abs((event_dt - start_dt).total_seconds())

            # ✅ Flexible match: either time is very close or title matches
            if (
                title and title.strip().lower() in event_title.strip().lower()
            ) or delta <= 300:
                service.events().delete(
                    calendarId="primary", eventId=event["id"]
                ).execute()
                print("🗑️ Deleted event:", event_title)
                return f"✅ Deleted event: {event_title} on {date} at {start_range}"

        return "❌ No matching event found with that title or time."

    except Exception as e:
        print("❌ Error in delete_event:", e)
        raise


def delete_event_by_id(credentials_dict, event_id):
    creds = Credentials(**credentials_dict)
    service = build("calendar", "v3", credentials=creds)

    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        print("🗑️ Deleted event with ID:", event_id)
        return True
    except Exception as e:
        print("❌ Error deleting event:", e)
        raise


def find_event_by_title_and_start_time(
    credentials_dict, title: str = None, start_time_iso: str = None
):
    creds = Credentials(**credentials_dict)
    service = build("calendar", "v3", credentials=creds)

    try:
        local_tz = pytz.timezone("Asia/Dubai")

        if start_time_iso:
            start_dt = parser.isoparse(start_time_iso)
            end_dt = start_dt + timedelta(hours=3)
        else:
            # If no time provided, use whole day
            start_dt = datetime.now(tz=local_tz).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_dt = start_dt + timedelta(days=1)

        print("🔍 Searching for event...")
        print("🔎 Time Range:", start_dt.isoformat(), "to", end_dt.isoformat())

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        for event in events_result.get("items", []):
            event_title = event.get("summary", "")
            event_start = event.get("start", {}).get("dateTime", "")
            if not event_start:
                continue

            event_dt = ensure_aware(event_start, local_tz)

            # Match by time if provided
            if start_time_iso:
                target_dt = parser.isoparse(start_time_iso)
                delta = abs((event_dt - target_dt).total_seconds())
                if delta <= 300:  # within 5 minutes
                    if (
                        not title
                        or title.strip().lower() in event_title.strip().lower()
                    ):
                        print("✅ Match by time ±5min:", event_title)
                        return event
            # Match by title if only title provided
            elif title and title.strip().lower() in event_title.strip().lower():
                print("✅ Match by title only:", event_title)
                return event

        print("❌ No matching event found.")
        return None

    except Exception as e:
        print("❌ Error in find_event_by_title_and_start_time:", e)
        raise


def update_event_fields(credentials_dict, event, updates):
    creds = Credentials(**credentials_dict)
    service = build("calendar", "v3", credentials=creds)
    event_id = event["id"]

    if "title" in updates:
        event["summary"] = updates["title"]
    if "start_time" in updates:
        event["start"]["dateTime"] = updates["start_time"]
    if "end_time" in updates:
        event["end"]["dateTime"] = updates["end_time"]
    if "participants" in updates:
        event["attendees"] = [{"email": email} for email in updates["participants"]]

    updated_event = (
        service.events()
        .update(calendarId="primary", eventId=event_id, body=event)
        .execute()
    )

    return updated_event


def load_credentials_for_user(user_id: str):
    client = MongoClient(os.getenv("MONGODB_URI"))
    load_dotenv()
    db = client["schedulai_db"]
    user = db["users"].find_one({"user_id": user_id})

    if not user or "credentials" not in user:
        raise Exception("No credentials found for user.")

    return user["credentials"]


def delete_all_events_on_date(credentials_dict, date_str):
    creds = Credentials(**credentials_dict)
    service = build("calendar", "v3", credentials=creds)

    local_tz = pytz.timezone("Asia/Dubai")
    date = datetime.strptime(date_str, "%Y-%m-%d").date()

    start_dt = local_tz.localize(datetime.combine(date, datetime.min.time()))
    end_dt = local_tz.localize(
        datetime.combine(date + timedelta(days=1), datetime.min.time())
    )

    print(f"🔍 Fetching events on {date_str} between {start_dt} and {end_dt}...")

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])
    deleted_titles = []

    for event in events:
        event_id = event["id"]
        title = event.get("summary", "Untitled Event")
        try:
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            deleted_titles.append(title)
            print(f"✅ Deleted: {title}")
        except Exception as e:
            print(f"❌ Failed to delete {title}: {e}")

    return {
        "date": date_str,
        "deleted_events": deleted_titles,
        "total_deleted": len(deleted_titles),
    }
