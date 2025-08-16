# HR Agent 🤖⚙️

> An AI-powered HR automation agent that streamlines the recruitment workflow

---

## 🚀 Overview
HR Agent is an end-to-end AI system designed to assist HR teams in automating recruitment tasks.  
It leverages **AI + Google APIs** to:
- 📄 Parse resumes
- 📊 Rank candidates against a given job description
- 📅 Schedule interviews (Google Calendar + Meet links)
- 📧 Send interview confirmation emails

This reduces manual HR effort and creates a smooth, automated hiring pipeline.

---

## ✨ Features
- **Resume Parsing:** Extracts text and candidate details from uploaded PDFs.
- **Candidate Ranking:** AI-powered scoring based on job description relevance.
- **Interview Scheduling:** Uses LangChain + Gemini + Google Calendar API to propose interview slots and auto-create events with Meet links.
- **Automated Emails:** Sends interview confirmation emails to shortlisted candidates.
- **Frontend UI:** Simple web-based interface for job input and resume upload.

---

## 🛠️ Tech Stack
- **Frontend:** HTML, CSS, JavaScript
- **Backend:** FastAPI (Python)
- **AI Layer:** LangChain + Google Gemini
- **APIs:** Google Calendar API (OAuth), Gmail API
- **Database:** MongoDB (storing parsed resumes)
- **Other Tools:** dotenv, pdfplumber / PyMuPDF, smtplib

---

## ⚙️ Setup Instructions

### 1. Clone the Repo
```
git clone https://github.com/<your-username>/HR-Agent.git
cd Ilmora-HR-Agent
```

### 2. Backend Setup
```
cd backend
pip install -r requirements.txt
```

Create a `.env` file:

```
# MongoDB
MONGO_URI=mongodb://localhost:27017

# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Google OAuth Credentials
GOOGLE_CREDENTIALS_FILE=credentials.json
DEFAULT_TZ=Asia/Kolkata

# Gmail
SENDER_EMAIL=your_email@gmail.com
```

Place your **Google OAuth `credentials.json`** in the backend folder.  
On first run, you’ll authorize both Gmail and Calendar (tokens saved locally).

Run the backend:
```
uvicorn main:app --reload
```

### 3. Frontend Setup
* Open `frontend/index.html` in your browser.
* Connects automatically to the FastAPI backend.

---

## ▶️ Demo Workflow

1. Enter job description + upload resumes.
2. Backend parses resumes and ranks candidates.
3. Select candidates → auto-schedule interviews in Google Calendar (with Meet links).
4. Automated email confirmations are sent to candidates.

---

## 📸 Screenshots

(Add your screenshots here: resume ranking UI, calendar invite, email confirmation)

---

## 🎥 Demo Video

(Link to Loom/YouTube demo video here)

---

## 📂 Repository Structure
```
Ilmora-HR-Agent/
│── backend/
│   ├── main.py
│   ├── resume_parser.py
│   ├── ranking.py
│   ├── calendar_scheduler.py
│   ├── email_sender.py
│   └── requirements.txt
│
│── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
│── README.md
│── .env.example
```