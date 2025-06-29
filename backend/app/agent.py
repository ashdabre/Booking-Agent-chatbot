import dateparser
from dateparser.search import search_dates
from datetime import datetime, timedelta
from typing import TypedDict
from langgraph.graph import StateGraph, END
from .google_calendar import list_free_slots, create_event, delete_event
import os
import re

CALENDAR_ID = os.getenv("CALENDAR_ID", "primary")

class AgentState(TypedDict):
    input: str
    creds: object
    start: str
    end: str
    duration: int
    available: bool
    message: str
    confirmation: object
    awaiting_time: bool
    awaiting_date: bool
    range_start: int
    range_end: int
    deleting: bool

def extract_intent(state: AgentState) -> AgentState:
    user_input = state["input"].lower().strip()
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    # Handle delete intent
    if "delete" in user_input or "remove" in user_input:
        return {**state, "deleting": True, "message": "Which meeting would you like to delete? Please specify date and time."}

    # Range booking: "between 3-5pm next week"
    range_match = re.search(r"between\s*(\d{1,2})\s*-\s*(\d{1,2})\s*(am|pm).*next week", user_input)
    if range_match and not state.get("awaiting_date"):
        start_hr = int(range_match.group(1)) % 12 + (12 if range_match.group(3) == "pm" else 0)
        end_hr = int(range_match.group(2)) % 12 + (12 if range_match.group(3) == "pm" else 0)
        return {
            **state,
            "awaiting_date": True,
            "range_start": start_hr,
            "range_end": end_hr,
            "message": f"Sure! What day next week would you like between {range_match.group(1)}{range_match.group(3).upper()} and {range_match.group(2)}{range_match.group(3).upper()}?"
        }

    if state.get("awaiting_date", False):
        parsed_day = dateparser.parse(user_input, settings={
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': datetime.now()
        })
        if parsed_day:
            date_only = parsed_day.replace(hour=0, minute=0, second=0, microsecond=0)
            start_dt = date_only.replace(hour=state["range_start"])
            end_dt = date_only.replace(hour=state["range_end"])
            return {
                **state,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "duration": int((end_dt - start_dt).total_seconds() / 60),
                "awaiting_date": False,
                "message": ""
            }
        return {**state, "message": "❓ Could not parse the date. Please specify a day next week."}

    if state.get("awaiting_time", False):
        parsed = dateparser.parse(user_input, settings={
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': datetime.now()
        })
        if parsed:
            base_date = datetime.fromisoformat(state["start"]) if state.get("start") else datetime.now()
            start_dt = base_date.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
            end_dt = start_dt + timedelta(minutes=state.get("duration", 30))
            return {
                **state,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "awaiting_time": False,
                "message": ""
            }
        return {**state, "message": "❓ I still couldn't parse the time. Try like '3pm'."}

    # Free-time query like "any free time this Friday?"
    if re.search(r"free time", user_input) and any(day in user_input for day in weekdays):
        for day in weekdays:
            if day in user_input:
                target_day = day
                break
        parsed = dateparser.parse(f"next {target_day}")
        if parsed:
            date_only = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
            return {
                **state,
                "awaiting_time": True,
                "start": date_only.isoformat(),
                "message": f"✅ Yes, you're free on {target_day.capitalize()}! What time would you like to book?"
            }
        return {**state, "message": "❓ Could not parse the weekday for free time."}

    # Booking with weekday only (e.g. "Book a meeting on Thursday")
    if "book" in user_input and any(day in user_input for day in weekdays):
        for day in weekdays:
            if day in user_input:
                parsed = dateparser.parse(f"next {day}")
                if parsed:
                    date_only = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
                    return {
                        **state,
                        "awaiting_time": True,
                        "start": date_only.isoformat(),
                        "message": f"📅 Got it! What time on {day.capitalize()}?"
                    }

    # General case: parse range or datetime
    found = search_dates(user_input, settings={
        'PREFER_DATES_FROM': 'future',
        'RELATIVE_BASE': datetime.now()
    })
    if found and len(found) >= 2:
        start_dt, end_dt = found[0][1], found[1][1]
    else:
        parsed = dateparser.parse(user_input, settings={
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': datetime.now()
        })
        if not parsed:
            return {**state, "message": "❓ I couldn’t understand the date/time. Please specify."}
        start_dt = parsed
        end_dt = start_dt + timedelta(minutes=state.get("duration", 30))

    start_dt = start_dt.replace(second=0, microsecond=0)
    end_dt = end_dt.replace(second=0, microsecond=0)
    return {
        **state,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "duration": int((end_dt - start_dt).total_seconds() / 60),
        "available": False,
        "message": "",
        "awaiting_time": False
    }

def check_availability(state: AgentState) -> AgentState:
    if state.get("deleting", False):
        return state
    if state.get("awaiting_time", False) or state.get("awaiting_date", False):
        return state
    if not state.get("start") or not state.get("end"):
        return {**state, "message": "⛔ Could not determine a valid time."}
    start_dt = datetime.fromisoformat(state["start"])
    end_dt = datetime.fromisoformat(state["end"])
    busy = list_free_slots(state["creds"], CALENDAR_ID, start_dt, end_dt)
    available = len(busy) == 0
    msg = "✅ That time is available!" if available else "⛔ That slot is busy."
    return {**state, "available": available, "message": msg}

def confirm_booking(state: AgentState) -> AgentState:
    if state.get("deleting", False):
        start_dt = datetime.fromisoformat(state["start"])
        result = delete_event(state["creds"], CALENDAR_ID, start_dt)
        return {**state, "message": "🗑️ Meeting deleted successfully!"}
    if state.get("awaiting_time", False) or state.get("awaiting_date", False) or not state.get("available", False):
        return state
    start_dt = datetime.fromisoformat(state["start"])
    end_dt = datetime.fromisoformat(state["end"])
    event = create_event(state["creds"], CALENDAR_ID, start_dt, end_dt)
    human_start = start_dt.strftime("%A, %B %d, %Y at %I:%M %p")
    human_end = end_dt.strftime("%A, %B %d, %Y at %I:%M %p")
    formatted = {
        "summary": event.get("summary"),
        "start": human_start,
        "end": human_end,
        "organizer": event.get("organizer", {}).get("email"),
        "htmlLink": event.get("htmlLink")
    }
    return {**state, "confirmation": formatted}

def build_agent():
    builder = StateGraph(AgentState)
    builder.add_node("extract_intent", extract_intent)
    builder.add_node("check_availability", check_availability)
    builder.add_node("confirm_booking", confirm_booking)
    builder.set_entry_point("extract_intent")
    builder.add_edge("extract_intent", "check_availability")
    builder.add_edge("check_availability", "confirm_booking")
    builder.add_edge("confirm_booking", END)
    return builder.compile()
