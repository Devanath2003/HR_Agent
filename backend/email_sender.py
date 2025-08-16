# email_sender.py

import os
import base64
import json
from typing import Optional
from dotenv import load_dotenv

# LangChain + Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# Gmail API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText

load_dotenv()

# =======================
# ENV CONFIG
# =======================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "gmail_token.json")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set in environment.")

if not SENDER_EMAIL:
    raise ValueError("SENDER_EMAIL not set in environment.")


# =======================
# LangChain Email Generator
# =======================
def _build_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.2
    )

EMAIL_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an assistant that writes professional, concise interview invitation emails."
            " Keep tone friendly yet formal."
        ),
        (
            "human",
            """
Write a short, professional email to invite {candidate_name} for an interview.

Include:
- Appreciation for their application.
- Confirmation they have been shortlisted for the {job_description} role (extract the job from it).
- The job description {job_description} short.
- The scheduled interview date and time: {scheduled_time}.
- The Google Meet link: {meet_link} (if provided).
- Encourage them to confirm attendance.
- Yours sincerely  = Name : Abcd , Company : Xyz solutions

Do NOT include any extra formatting or markdown. Return plain text only.
"""
        )
    ]
)


def generate_email_body(candidate_name: str, job_description: str, meet_link: Optional[str], scheduled_time: str) -> str:
    """Generate email body using Gemini."""
    llm = _build_llm()
    prompt = EMAIL_PROMPT.format_messages(
        candidate_name=candidate_name,
        job_description=job_description,
        meet_link=meet_link or "Will be sent shortly via calendar invite.",
        scheduled_time=scheduled_time or "Will be shared shortly."
    )
    resp = llm.invoke(prompt)
    return resp.content.strip() # type: ignore


# =======================
# Gmail API Auth
# =======================
def authenticate_gmail_service():
    """Authenticate using OAuth and return Gmail service."""
    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GMAIL_CREDENTIALS_FILE):
                raise FileNotFoundError(f"Gmail OAuth credentials file not found: {GMAIL_CREDENTIALS_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(GMAIL_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


# =======================
# Send Email
# =======================
def send_interview_email(
    name: str,
    email: str,
    job_description: str,
    meet_link: Optional[str] = None,
    scheduled_time: Optional[str] = None
) -> bool:
    """
    Generate and send an interview email to the candidate.
    """
    try:
        # Step 1: Generate email body
        body = generate_email_body(name, job_description, meet_link, scheduled_time) # type: ignore

        # Step 2: Build MIME message
        message = MIMEText(body)
        message["to"] = email
        message["from"] = SENDER_EMAIL # type: ignore
        message["subject"] = f"Interview Invitation - {name}"

        # Step 3: Encode and send via Gmail API
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        service = authenticate_gmail_service()
        service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()

        print(f"✅ Email sent to {name} ({email})")
        return True

    except Exception as e:
        print(f"❌ Failed to send email to {name} ({email}): {e}")
        return False


if __name__ == "__main__":
    # Test sending email
    result = send_interview_email(
        name="John Doe",
        email="john.doe@example.com",
        job_description="We are hiring a Python developer with 3+ years of experience.",
        meet_link="https://meet.google.com/xyz-abcq-wef",
        scheduled_time="2025-08-20 10:00 AM IST"
    )
    print("Test result:", result)
