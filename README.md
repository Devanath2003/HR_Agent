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
- ### Frontend Upload Screen
  <img width="1894" height="917" alt="image" src="https://github.com/user-attachments/assets/7d28cd43-494d-46fa-afc3-d99aa519001f" />
- ### Ranked Candidates Output
  <img width="1908" height="868" alt="image" src="https://github.com/user-attachments/assets/3d9cbedc-185e-47a5-846b-8c32170e1cef" />
- ### Interview Schedule Status
  <img width="1885" height="745" alt="image" src="https://github.com/user-attachments/assets/b316061b-d864-4105-8fba-1e6182308c23" />
- ### Google Calendar Event
  <img width="1850" height="925" alt="image" src="https://github.com/user-attachments/assets/8e3ff668-0bce-4637-af64-fff98cc83ca2" />
- ### Google Meet Setup
  <img width="1704" height="801" alt="image" src="https://github.com/user-attachments/assets/70d2189a-6f83-448e-94fc-510c697d93c4" />
- ### Email Inbox
  <img width="1489" height="668" alt="image" src="https://github.com/user-attachments/assets/027b3ded-e46c-4e0f-9f00-580e5d9bf0b9" />







---

## 🎥 Demo Video

Link -: https://www.loom.com/share/de0851da43ab44e3a4de0e5e1923a533?sid=817fec63-ac75-46e1-8bb9-48da0aa8f86a

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
