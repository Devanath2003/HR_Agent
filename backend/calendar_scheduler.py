# calendar_scheduler.py
"""
Agentic Calendar Scheduler (OAuth version)
--------------------------
1) Uses LangChain + Gemini to propose interview event details
2) Creates the event in Google Calendar (with Meet link)
3) Returns a dict with event details
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import re

from dotenv import load_dotenv

# --- LLM (LangChain + Gemini) ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# --- Google Calendar API (OAuth) ---
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# --- Timezone ---
from zoneinfo import ZoneInfo

load_dotenv()

# =============================
# ENV CONFIG
# =============================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # required
# Google OAuth credentials and token
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = "token.json"
DEFAULT_TZ = os.getenv("DEFAULT_TZ", "Asia/Kolkata")

# Google Calendar API scope for full access + Meet links
SCOPES = ['https://www.googleapis.com/auth/calendar']

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set.")

# =============================
# LLM: Propose meeting details
# =============================
# This is the same LLM logic from your original code
def _build_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GEMINI_API_KEY, temperature=0.2)

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an assistant that creates concise interview calendar events."
            " Follow constraints strictly and return STRICT JSON only."
        ),
        (
            "human",
            """
Today is {now_str} (timezone: {tz}).
You will receive:
- Candidate name and email
- Job description

Constraints:
- Suggest a 30-minute interview between 10:00 and 17:00 local time on the next 1-5 business days.
- Avoid weekends.
- Keep title concise: "Interview: <Role> — <CandidateName>"
- Provide a short description (2-4 lines) referencing the role and next steps.
- Location should be "Google Meet".
- Timezone must be {tz}.
- Return STRICT JSON (no code fences, no extra text) with keys:
  {{
    "title": "...",
    "description": "...",
    "start_time_iso": "YYYY-MM-DDTHH:MM:SS±HH:MM",
    "end_time_iso": "YYYY-MM-DDTHH:MM:SS±HH:MM",
    "timezone": "{tz}",
    "location": "Google Meet"
  }}

Candidate:
- name: {candidate_name}
- email: {candidate_email}

Job Description:
{job_description}
""",
        ),
    ]
)

def propose_meeting_details(
    job_description: str,
    candidate_name: str,
    candidate_email: str,
    tz: str = DEFAULT_TZ,
) -> Dict:
    """Use Gemini to propose the meeting title, description, and time window."""
    llm = _build_llm()
    now = datetime.now(ZoneInfo(tz))
    now_str = now.strftime("%Y-%m-%d %H:%M:%S %Z%z")

    prompt = PROMPT.format_messages(
        now_str=now_str,
        tz=tz,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        job_description=job_description,
    )

    resp = llm.invoke(prompt)

    # Ensure we always get a clean string for JSON parsing
    if isinstance(resp.content, str):
        raw = resp.content.strip()
    else:
        raw = str(resp.content).strip()

    print("RAW GEMINI OUTPUT:", raw)

    # Remove markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
        req_keys = {"title", "description", "start_time_iso", "end_time_iso", "timezone", "location"}
        if not req_keys.issubset(data.keys()):
            raise ValueError("Missing keys in LLM output.")
        return data
    except Exception as e:
        print("❌ JSON parsing failed:", e)
        # Fallback: next business day 10:00–10:30
        start = _next_business_day_at_time(now, hour=10, minute=0)
        end = start + timedelta(minutes=30)
        return {
            "title": f"Interview: Candidate — {candidate_name}",
            "description": "Interview for the role.",
            "start_time_iso": start.isoformat(),
            "end_time_iso": end.isoformat(),
            "timezone": tz,
            "location": "Google Meet",
        }

def _next_business_day_at_time(now_dt: datetime, hour: int = 10, minute: int = 0) -> datetime:
    """Compute next business day at specific local time."""
    candidate = now_dt
    for _ in range(7):
        candidate = candidate + timedelta(days=1)
        if candidate.weekday() < 5:  # Mon-Fri
            return candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return (now_dt + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)

# =============================
# Google Calendar Service (OAuth)
# =============================
def authenticate_google_calendar():
    """Authenticate the user using OAuth 2.0 and return a Calendar API service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Google OAuth credentials file not found: {CREDENTIALS_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

# =============================
# Public API used by main.py
# =============================
def schedule_interview_calendar(
    name: str,
    email: str,
    job_description: str
) -> Dict:
    """
    1) Ask LLM to propose details
    2) Create event in Google Calendar (Meet link)
    3) Return details (truthy dict)
    """
    try:
        # 1) LLM proposes details
        proposed = propose_meeting_details(job_description, name, email, tz=DEFAULT_TZ)

        # Normalize times to RFC3339 / Calendar API accepted format
        start_iso = proposed["start_time_iso"]
        end_iso = proposed["end_time_iso"]
        tz = proposed.get("timezone", DEFAULT_TZ)
        title = proposed["title"]
        description = proposed["description"]

        service = authenticate_google_calendar()

        # 2) Build Calendar event
        event_body = {
            "summary": title,
            "description": description,
            "location": proposed.get("location", "Google Meet"),
            "start": {"dateTime": start_iso, "timeZone": tz},
            "end": {"dateTime": end_iso, "timeZone": tz},
            "attendees": [{"email": email, "displayName": name}],
            "conferenceData": {
                "createRequest": {
                    "requestId": f"meet-{uuid.uuid4()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        created = (
            service.events()
            .insert(
                calendarId='primary',
                body=event_body,
                conferenceDataVersion=1,
                sendUpdates="all",  # emails invite automatically
            )
            .execute()
        )

        event_id = created.get("id")
        html_link = created.get("htmlLink")
        meet_link: Optional[str] = None
        conf = created.get("conferenceData", {})
        entry_points = conf.get("entryPoints", [])
        for ep in entry_points:
            if ep.get("entryPointType") == "video":
                meet_link = ep.get("uri")
                break

        return {
            "success": True,
            "event_id": event_id,
            "event_link": html_link,
            "meet_link": meet_link,
            "start": start_iso,
            "end": end_iso,
        }

    except Exception as e:
        print(f"❌ Calendar scheduling error for {name} <{email}>: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Example usage for testing
    result = schedule_interview_calendar(
        name="John Doe",
        email="john.doe@example.com",
        job_description="Seeking a talented Python developer with 3+ years of experience..."
    )
    print(result)