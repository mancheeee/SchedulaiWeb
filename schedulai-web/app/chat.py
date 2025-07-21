from fastapi import APIRouter, Request, Body, HTTPException
from datetime import datetime, timedelta
from pydantic import BaseModel
import httpx, os, json, re
from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dateutil import parser


from app.mongo_client import chat_collection
from app.calendar_utils import delete_event  # make sure this exists
from app.calendar_utils import (
    find_free_slot,
    get_all_free_slots,
    create_calendar_event,
    get_events_for_day,
    delete_event,
    update_event_fields,  # ✅ add this
    find_event_by_title_and_start_time,  # ✅ and this
    load_credentials_for_user,
    delete_all_events_on_date,
)
from app import calendar_utils
from app.utils import replace_natural_dates

from app.auth import user_tokens
from app.schemas import EventData, FreeSlotRequest
from pydantic import ValidationError
import traceback
from datetime import time

load_dotenv()
router = APIRouter()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")


def extract_first_json(text):
    stack = []
    start = None
    for i, char in enumerate(text):
        if char == "{":
            if start is None:
                start = i
            stack.append("{")
        elif char == "}":
            if stack:
                stack.pop()
                if not stack:
                    return text[start : i + 1]
    return None


def normalize_time_format(time_str):
    if time_str and re.fullmatch(r"\d{1,2}", time_str):
        return f"{int(time_str):02d}:00"
    return time_str


@router.post("/chat")
async def chat_with_gpt(request: Request):
    body = await request.json()
    user_prompt = body.get("message")
    credentials_dict = user_tokens.get("demo_user")

    if not credentials_dict:
        return {"error": "❌ No credentials found. Please log in first."}

    user_prompt = replace_natural_dates(user_prompt)

    system_prompt = f"""
    You are a smart calendar assistant named Schedulai. Always return only valid, compact JSON. 

    Never return placeholder values like "Meeting title (unknown)". If unsure, just omit the title field.

    ---

    ✅ When **scheduling** an event, return:
    {{
    "action": "create",
    "title": "Meeting title",
    "date": "YYYY-MM-DD",
    "start_range": "HH:MM",
    "end_range": "HH:MM",
    "duration": optional number of minutes,
    "participants": ["email1", "email2"]
    }}

    ---

    ✅ When **checking availability**, return:
    {{
    "action": "check" or "check_free_time",
    "date": "YYYY-MM-DD",
    "start_range": "HH:MM",       // optional
    "end_range": "HH:MM",         // optional
    "duration": optional number of minutes
    }}

    ---

    ✅ When **deleting** an event, users may provide only a date + time, or a title + date.
    Return:
    {{
    "action": "delete",
    "title": "Meeting title (optional)",
    "start_time": "YYYY-MM-DDTHH:MM:SS"
    }}

    ---

    ✅ When deleting **all events for a specific day**, return:
    {{
    "action": "delete_all",
    "date": "YYYY-MM-DD"
    }}

    ---

    ✅ When **updating** an event, users might only say:
    - "rename the 3pm call on July 15"
    - "move meeting to 6pm"
    - "change title of event on Friday"

    You must extract what you can, and return:
    {{
    "action": "update",
    "original_event": {{
        "title": "original title if known",
        "start_time": "YYYY-MM-DDTHH:MM:SS"
    }},
    "updated_fields": {{
        "title": "New title (optional)",
        "start_time": "YYYY-MM-DDTHH:MM:SS (optional)",
        "end_time": "YYYY-MM-DDTHH:MM:SS (optional)",
        "participants": ["email1", "email2"]  // optional
    }}
    }}

    ---

    Only return JSON — no markdown, no explanation, no apologies. Just raw valid JSON in the expected schema.

    ⚠️ TODAY'S DATE IS {datetime.now().strftime('%Y-%m-%d')}

    🛑 Never return past dates.
    Only use today's date or a future date (>= today's date).
    """
    few_shot_examples = [
        {
            "role": "user",
            "content": "rename my 3pm meeting on July 20 to 'Client Review'",
        },
        {
            "role": "assistant",
            "content": """
{
  "action": "update",
  "original_event": {
    "start_time": "2025-07-20T15:00:00+05:00"
  },
  "updated_fields": {
    "title": "Client Review"
  }
}
""",
        },
        {
            "role": "user",
            "content": "cancel the event titled 'Strategy Call' on July 15 at 7pm",
        },
        {
            "role": "assistant",
            "content": """
{
  "action": "delete",
  "title": "Strategy Call",
  "start_time": "2025-07-15T19:00:00+05:00"
}
""",
        },
        {
            "role": "user",
            "content": "move the 3pm call on July 16 to 6pm",
        },
        {
            "role": "assistant",
            "content": """
{
  "action": "update",
  "original_event": {
    "start_time": "2025-07-16T15:00:00+05:00"
  },
  "updated_fields": {
    "start_time": "2025-07-16T18:00:00+05:00",
    "end_time": "2025-07-16T19:00:00+05:00"
  }
}
""",
        },
        {
            "role": "user",
            "content": "delete all meetings on July 19",
        },
        {
            "role": "assistant",
            "content": """
{
  "action": "delete_all",
  "date": "2025-07-19"
}
""",
        },
        {
            "role": "user",
            "content": "Move the 3pm meeting on July 17 to Saturday at 5pm",
        }, 
        {
            "role": "assistant",
            "content": """
{
  "action": "update",
  "original_event": {
    "start_time": "2025-07-17T15:00:00+05:00"
  },
  "updated_fields": {
    "start_time": "2025-07-20T17:00:00+05:00",
    "end_time": "2025-07-20T18:00:00+05:00"
  }
}
""",
        },
        {
            "role": "user",
            "content": "Reschedule the 3pm PDFCall tomorrow to July 22 at 6pm",
        },
        {
            "role": "assistant",
            "content": """
{
  "action": "update",
  "original_event": {
    "title": "PDFCall",
    "start_time": "2025-07-17T15:00:00+05:00"
  },
  "updated_fields": {
    "start_time": "2025-07-22T18:00:00+05:00",
    "end_time": "2025-07-22T19:00:00+05:00"
  }
}
""",
        },
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        *few_shot_examples,
        {"role": "user", "content": user_prompt},
    ]

    payload = {
        "model": LLM_MODEL,
        "messages": messages,  # ✅ Now using system + few-shot + user input
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            content = res.json()
            print("📦 Full OpenRouter API Response:", content)
    except Exception as e:
        traceback.print_exc()
        return {"error": f"❌ Failed to fetch from LLM API: {str(e)}"}

    try:
        if "choices" not in content or not content["choices"]:
            return {
                "error": "❌ LLM response missing 'choices'",
                "raw_response": content,
            }
        raw_message = content["choices"][0]["message"]["content"]
        print("🧠 LLM Raw Response:\n", raw_message)

        chat_collection.insert_one(
            {
                "user_message": user_prompt,
                "bot_response": raw_message,
                "timestamp": datetime.utcnow(),
            }
        )

        try:
            parsed_data = json.loads(raw_message)
        except json.JSONDecodeError:
            first_json = extract_first_json(raw_message)
            if not first_json:
                return {"error": "❌ No valid JSON object in GPT response"}
            try:
                parsed_data = json.loads(first_json)
            except json.JSONDecodeError as e:
                return {
                    "error": f"❌ Failed to parse JSON: {str(e)}",
                    "raw": first_json,
                }

        parsed_data.setdefault("title", "Meeting")
        parsed_data.setdefault("participants", [])
        parsed_data.setdefault("action", "schedule")

        # Normalize time
        parsed_data["start_range"] = normalize_time_format(
            parsed_data.get("start_range") or "08:00"
        )
        parsed_data["end_range"] = normalize_time_format(
            parsed_data.get("end_range") or "20:00"
        )

        action = parsed_data.get("action", "").lower()

        # 🔥 DELETE
        if action == "delete":
            start_dt = parsed_data.get("start_time")
            title = parsed_data.get("title")

            if not start_dt:
                return {"error": "❌ 'start_time' is required for deleting an event."}

            try:
                dt = datetime.fromisoformat(start_dt)
                date = dt.strftime("%Y-%m-%d")
                start_range = dt.strftime("%H:%M")
                end_range = (dt + timedelta(hours=1)).strftime("%H:%M")
            except Exception as e:
                return {"error": f"❌ Failed to parse 'start_time': {str(e)}"}

            delete_result = await run_in_threadpool(
                delete_event,
                credentials_dict,
                date,
                start_range,
                end_range,
                title,
            )

            return {
                "event_deleted": True,
                "message": delete_result,
                "event_data": {
                    "date": date,
                    "start_range": start_range,
                    "end_range": end_range,
                    "title": title,
                    "start_time": start_dt,
                },
            }

        # 🧹 DELETE ALL EVENTS ON A DAY
        elif action == "delete_all":
            date = parsed_data.get("date")
            if not date:
                return {"error": "❌ Date is required to delete all events on a day."}

            result = await run_in_threadpool(
                delete_all_events_on_date, credentials_dict, date
            )

            return {
                "message": f"🧹 Deleted {result['total_deleted']} events on {date}.",
                "details": result,
            }

        # 📅 SCHEDULE
        elif action in ("create", "schedule"):
            if (
                not parsed_data.get("duration")
                and parsed_data.get("start_range")
                and parsed_data.get("end_range")
            ):
                fmt = "%H:%M"
                start = datetime.strptime(parsed_data["start_range"], fmt)
                end = datetime.strptime(parsed_data["end_range"], fmt)
                parsed_data["duration"] = int((end - start).total_seconds() // 60)

            validated = EventData(**parsed_data)
            event_data = validated.dict()

            if not event_data["title"] or event_data["title"].lower() == "event":
                event_data["title"] = (
                    f"Meeting with {', '.join(event_data['participants'])}"
                    if event_data["participants"]
                    else "Scheduled Meeting"
                )

            free_slot = await run_in_threadpool(
                find_free_slot,
                credentials_dict,
                event_data["date"],
                event_data["start_range"],
                event_data["end_range"],
                event_data["duration"],
            )

            if free_slot:
                created = await run_in_threadpool(
                    create_calendar_event,
                    credentials_dict,
                    event_data["title"],
                    free_slot["start"],
                    free_slot["end"],
                    event_data["participants"],
                )
                return {
                    "event_created": True,
                    "details": created,
                    "event_data": event_data,
                }
            else:
                return {"message": "❌ No available time slot found."}

        # ✨ UPDATE
        elif action == "update":
            original = parsed_data.get("original_event")
            updates = parsed_data.get("updated_fields")

            print("🛠 Parsed Action:", action)
            print("🧾 Original Event:", original)
            print("✏️ Updates:", updates)

            if not original or not updates:
                return {
                    "response": "⚠️ To update a meeting, I need both the original event and the updated fields."
                }

            start_time_str = original.get("start_time", "")
            if not start_time_str or "T" not in start_time_str:
                return {"response": f"❌ Invalid start_time format: '{start_time_str}'"}

            try:
                event_to_update = await run_in_threadpool(
                    find_event_by_title_and_start_time,
                    credentials_dict,
                    original.get("title"),
                    original.get("start_time"),
                )
            except Exception as e:
                return {"response": f"❌ Error finding event: {str(e)}"}

            if not event_to_update:
                return {"response": "❌ No matching event found to update."}

            try:
                updated_event = await run_in_threadpool(
                    update_event_fields,
                    credentials_dict,
                    event_to_update,
                    updates,
                )
                return {
                    "event_updated": True,
                    "message": f"✅ Event updated: {updated_event['summary']} now starts at {updated_event['start']['dateTime']}",
                    "updated_event": updated_event,
                }
            except Exception as e:
                return {"response": f"❌ Failed to update: {str(e)}"}

        # ⏱️ FREE SLOT
        elif action in ("check", "check_free_time"):
            validated = FreeSlotRequest(**parsed_data)
            slot_req = validated.dict()
            requested_date = datetime.strptime(slot_req["date"], "%Y-%m-%d").date()
            now = datetime.now()

            if requested_date == now.date():
                current_time = now.time()
                slot_start_time = datetime.strptime(
                    slot_req["start_range"], "%H:%M"
                ).time()
                if current_time > slot_start_time:
                    new_start = (
                        (now + timedelta(hours=1))
                        .replace(minute=0, second=0, microsecond=0)
                        .strftime("%H:%M")
                    )
                    slot_req["start_range"] = new_start
                    parsed_data["start_range"] = new_start

            free_slots = await run_in_threadpool(
                get_all_free_slots,
                credentials_dict,
                slot_req["date"],
                slot_req["start_range"],
                slot_req["end_range"],
                slot_req["duration"],
            )

            return {
                "event_created": False,
                "message": f"🕒 Found {len(free_slots)} free slots:",
                "free_slots": free_slots,
            }

        # ❌ Unexpected Action
        else:
            return {"error": f"⚠️ Unexpected action: {action}", "raw_data": parsed_data}

    except Exception as e:
        traceback.print_exc()


@router.get("/calendar/day-schedule")
async def get_schedule_for_day(date: str, request: Request):
    credentials_dict = user_tokens.get("demo_user")
    if not credentials_dict:
        return {"error": "No credentials found."}

    events = await run_in_threadpool(get_events_for_day, credentials_dict, date)
    return {"events": events}


@router.get("/calendar/booked")
async def get_booked_events(date: str, request: Request):
    credentials_dict = user_tokens.get("demo_user")
    if not credentials_dict:
        return {"error": "No credentials found."}

    events = await run_in_threadpool(get_events_for_day, credentials_dict, date)
    return {"booked": events}


from fastapi import Body, HTTPException
from googleapiclient.discovery import build


class CredentialsPayload(BaseModel):
    token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list


@router.delete("/calendar/event/{event_id}")
async def delete_event_by_id(event_id: str, credentials: CredentialsPayload):
    try:
        creds = Credentials(**credentials.dict())
        service = build("calendar", "v3", credentials=creds)
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return {"status": "deleted"}
    except Exception as e:
        print(f"Error deleting event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/history/clear")
async def clear_chat_logs():
    result = chat_collection.delete_many({})
    return {"message": f"Deleted {result.deleted_count} chat logs."}


@router.get("/user_calendar_events")
def get_calendar_events(user_id: str):
    try:
        from app.calendar_utils import load_credentials_for_user
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from datetime import datetime

        credentials_dict = load_credentials_for_user(user_id)
        creds = Credentials(**credentials_dict)
        service = build("calendar", "v3", credentials=creds)

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=datetime.utcnow().isoformat() + "Z",
                maxResults=20,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        return {"events": events_result.get("items", [])}
    except Exception as e:
        print("❌ Backend error while fetching events:", str(e))
        raise HTTPException(status_code=500, detail=f"Calendar fetch failed: {str(e)}")
