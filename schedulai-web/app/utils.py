import re
from datetime import datetime, timedelta


def replace_natural_dates(text: str) -> str:
    today = datetime.now()
    tomorrow = today + timedelta(days=1)

    # Replace 'today' and 'tomorrow'
    text = re.sub(r"\btoday\b", today.strftime("%Y-%m-%d"), text, flags=re.IGNORECASE)
    text = re.sub(
        r"\btomorrow\b", tomorrow.strftime("%Y-%m-%d"), text, flags=re.IGNORECASE
    )

    # Handle "on the 12th", "on 13th"
    ordinal_match = re.search(
        r"\bon (?:the )?(\d{1,2})(st|nd|rd|th)?\b", text, flags=re.IGNORECASE
    )
    if ordinal_match:
        day = int(ordinal_match.group(1))
        month = today.month
        year = today.year

        # If day has passed, move to next month
        if day < today.day:
            month += 1
            if month > 12:
                month = 1
                year += 1

        try:
            future_date = datetime(year, month, day)
            text = re.sub(
                r"\bon (?:the )?\d{1,2}(st|nd|rd|th)?\b",
                f'on {future_date.strftime("%Y-%m-%d")}',
                text,
                flags=re.IGNORECASE,
            )
        except ValueError:
            pass  # Invalid day for the month

    # Handle weekday names like "on Monday", "next Friday"
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    for name, target_day in weekdays.items():
        # next Friday
        next_pattern = rf"\bnext {name}\b"
        if re.search(next_pattern, text, flags=re.IGNORECASE):
            days_ahead = ((target_day - today.weekday() + 7) % 7) + 7
            date_obj = today + timedelta(days=days_ahead)
            text = re.sub(
                next_pattern, date_obj.strftime("%Y-%m-%d"), text, flags=re.IGNORECASE
            )
            continue

        # on Friday
        on_pattern = rf"\bon {name}\b"
        if re.search(on_pattern, text, flags=re.IGNORECASE):
            days_ahead = (target_day - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            date_obj = today + timedelta(days=days_ahead)
            text = re.sub(
                on_pattern, date_obj.strftime("%Y-%m-%d"), text, flags=re.IGNORECASE
            )

    return text

