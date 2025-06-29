from datetime import datetime
import os, pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from fastapi import HTTPException
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
# from google_auth_oauthlib.flow import InstalledAppFlow
import os
from google_auth_oauthlib.flow import Flow

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials.json")

SCOPES = ['https://www.googleapis.com/auth/calendar']

from dotenv import load_dotenv
load_dotenv()
def get_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES
    )

def get_credentials_from_code(code: str):
    flow = get_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    # Persist to disk/session if needed
    return creds

def list_free_slots(creds, calendar_id, start, end):
    # ✅ Convert to datetime if needed
    if isinstance(start, str):
        start = datetime.fromisoformat(start)
    if isinstance(end, str):
        end = datetime.fromisoformat(end)

    service = build('calendar', 'v3', credentials=creds)
    body = {
        "timeMin": start.isoformat() + 'Z',
        "timeMax": end.isoformat() + 'Z',
        "items": [{"id": calendar_id}],
    }
    events_result = service.freebusy().query(body=body).execute()
    return events_result["calendars"][calendar_id]["busy"]

from datetime import datetime

def create_event(creds, calendar_id, start, end, title="Meeting"):

    # ✅ Convert to datetime if not already
    if isinstance(start, str):
        try:
            start = datetime.fromisoformat(start)
        except ValueError:
            start = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")

    if isinstance(end, str):
        try:
            end = datetime.fromisoformat(end)
        except ValueError:
            end = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")

    service = build("calendar", "v3", credentials=creds)
    event = {
        "summary": title,
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Kolkata"},
    }
    return service.events().insert(calendarId=calendar_id, body=event).execute()


def build_flow():
    return Flow.from_client_secrets_file(
        os.path.join(os.path.dirname(__file__), "credentials.json"),
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI")
    )
def deserialize_credentials(creds_dict_or_str):
    if isinstance(creds_dict_or_str, str):
        creds_dict_or_str = json.loads(creds_dict_or_str)
    return Credentials.from_authorized_user_info(info=creds_dict_or_str, scopes=SCOPES)

def delete_event(creds_json, calendar_id, target_datetime):
    creds = Credentials.from_authorized_user_info(info=creds_json)
    service = build('calendar', 'v3', credentials=creds)

    # Search for events around the target time (±30 min window)
    time_min = (target_datetime - timedelta(minutes=30)).isoformat() + 'Z'
    time_max = (target_datetime + timedelta(minutes=30)).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    if not events:
        return "❌ No event found around that time."

    # Delete the first found event
    event_id = events[0]['id']
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    return "🗑️ Event deleted successfully."