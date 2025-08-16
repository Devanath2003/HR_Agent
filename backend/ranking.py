# ranking.py
"""
Ranking Module
--------------
Takes parsed resume data and a job description,
uses LLM (Gemini) to score and rank resumes.
"""

import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from typing import List, Dict

# Load env variables
load_dotenv()

# Configure Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-2.0-flash-lite')


def rank_resumes(job_description: str, parsed_resumes: List[Dict]) -> List[Dict]:
    """
    Rank resumes based on job description.
    Args:
        job_description (str): The job description text.
        parsed_resumes (list): List of dicts with parsed resume data.
    Returns:
        List[dict]: Sorted resumes with name, email, score, and top matches.
    """
    ranked_list = []

    for resume in parsed_resumes:
        # Ensure name/email exist
        name = resume.get("name", "Unknown")
        email = resume.get("email", "Not Found")

        # Send to LLM for scoring
        prompt = f"""
You are an AI assistant helping an HR team rank resumes.
You will be given:
1. A job description
2. Parsed resume data (structured JSON)

Your task:
- Compare the candidate's details with the job description
- Give a match score (0 to 100) based on relevance to the job
- Identify the top matching skills/experiences from the resume

Job Description:
-----
{job_description}
-----

Parsed Resume Data:
-----
{json.dumps(resume, indent=2)}
-----

Return ONLY a JSON object in this format:
{{
  "score": <integer between 0 and 100>,
  "top_matches": ["skill1", "skill2", ...]
}}
"""

        try:
            response = model.generate_content(prompt)
            result_str = response.text.strip()

            if result_str.startswith("```json"):
                result_str = result_str.strip("```json").strip("`").strip()

            result_json = json.loads(result_str)

            ranked_list.append({
                "name": name,
                "email": email,
                "score": result_json.get("score", 0),
                "top_matches": result_json.get("top_matches", [])
            })

        except Exception as e:
            print(f"❌ Error ranking resume for {name}: {e}")
            ranked_list.append({
                "name": name,
                "email": email,
                "score": 0,
                "top_matches": []
            })

    # Sort by score descending
    ranked_list.sort(key=lambda x: x["score"], reverse=True)
    return ranked_list


# Debug/Test
if __name__ == "__main__":
    # Example test data
    job_desc = "We are hiring a Python backend developer with Django and REST API experience."
    resumes_data = [
        {
            "name": "Alice",
            "email": "alice@example.com",
            "skills": ["Python", "Django", "REST APIs", "AWS"],
            "experience": ["Backend Developer at XYZ", "3 years Python experience"],
            "education": ["B.Tech Computer Science"],
            "achievements": ["AWS Certified Developer"]
        },
        {
            "name": "Bob",
            "email": "bob@example.com",
            "skills": ["Java", "Spring Boot", "SQL"],
            "experience": ["Backend Developer at ABC", "2 years Java experience"],
            "education": ["B.Tech Information Technology"],
            "achievements": []
        }
    ]

    ranked = rank_resumes(job_desc, resumes_data)
    print(json.dumps(ranked, indent=2))
