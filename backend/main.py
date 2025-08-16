# main.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from uuid import uuid4
import json

# Import our modules
from resume_parser import extract_text_from_pdf, extract_all_fields
from ranking import rank_resumes
# This import is correct
from calendar_scheduler import schedule_interview_calendar
# The email sender module is assumed to be working
from email_sender import send_interview_email

load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI"))
db = client["resumeai"]
collection = db["resumes"]

# Directory to store uploaded resumes
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model to correctly parse the incoming JSON from the frontend
class ScheduleRequest(BaseModel):
    jobDescription: str
    candidates: List[Dict[str, str]]

@app.get("/")
async def root():
    return {"message": "Resume AI Backend is running!"}

@app.get("/test")
async def test():
    return {"status": "Backend is working!"}

# ==========================
# UPLOAD & RANK RESUMES
# ==========================
@app.post("/upload")
async def upload(jobDescription: str = Form(...), resumes: List[UploadFile] = File(...)):
    try:
        parsed_resumes = []
        saved_files = []

        for resume in resumes:
            if not resume.filename or not resume.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"File {resume.filename} is not a PDF")
            
            content = await resume.read()
            if len(content) == 0:
                raise HTTPException(status_code=400, detail=f"File {resume.filename} is empty")
            
            filename = f"{uuid4()}_{resume.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            saved_files.append(resume.filename)

            resume_text = extract_text_from_pdf(file_path)
            parsed_data = extract_all_fields(resume_text)
            
            db_record = {
                "filename": filename,
                "original_name": resume.filename,
                "jobDescription": jobDescription,
                "parsed_data": parsed_data
            }
            collection.insert_one(db_record)
            parsed_resumes.append(parsed_data)

        ranked_resumes = rank_resumes(jobDescription, parsed_resumes)

        return {
            "message": f"{len(saved_files)} resumes uploaded & ranked successfully!",
            "ranklist": ranked_resumes,
            "files_processed": saved_files
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ==========================
# SCHEDULE INTERVIEWS
# ==========================
@app.post("/schedule_interviews")
async def schedule_interviews(request_body: ScheduleRequest):
    try:
        job_description = request_body.jobDescription
        candidates = request_body.candidates

        if not job_description or not candidates:
            raise HTTPException(status_code=400, detail="Job description and candidates are required.")

        interviews_scheduled = 0
        scheduling_results = []

        for candidate in candidates:
            name = candidate.get("name")
            email = candidate.get("email")

            if not name or not email:
                continue
            
            # Step 1: Schedule in Google Calendar
            calendar_status = schedule_interview_calendar(name, email, job_description)

            # Step 2: Send email confirmation (include Meet link & time if available)
            if calendar_status.get("success"):
                meet_link = calendar_status.get("meet_link", None)
                scheduled_time = calendar_status.get("start", None)
                email_status = send_interview_email(
                    name=name,
                    email=email,
                    job_description=job_description,
                    meet_link=meet_link,
                    scheduled_time=scheduled_time
                )
                if email_status:
                    interviews_scheduled += 1
                
            scheduling_results.append({
                "candidate_name": name,
                "candidate_email": email,
                "calendar_result": calendar_status
            })

        return {
            "status": "success",
            "interviews_scheduled": interviews_scheduled,
            "results": scheduling_results
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to schedule interviews: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)