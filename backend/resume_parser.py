# resume_parser.py
"""
Resume Parser Module for HR Agent
---------------------------------
Extracts:
- Name
- Email
- Skills
- Experience
- Education
- Achievements
from resumes using:
1) Manual inline parsing
2) Manual block parsing
3) LLM (Gemini) fallback if both fail
"""

import pdfplumber
import re
import json
from typing import List, Dict, Optional, Union
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Field heading variations for detection (must be lowercase)
FIELD_HEADINGS = {
    "skills": ["skills", "technical skills", "skillset", "core competencies"],
    "experience": ["experience", "work experience", "professional experience", "employment history","work history"],
    "education": ["education", "academic qualifications", "academic", "education & qualifications"],
    "achievements": ["achievements", "awards", "honors", "accomplishments", "certifications","awards recieved"]
}

# Regex patterns
INLINE_SPLIT_RE = re.compile(r'[,\|;/]')
BULLET_START_RE = re.compile(r'^[\-\•\*\u2022]\s*', re.UNICODE)
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE)


# -------------------------------------------------------
# 1. PDF Text Extraction
# -------------------------------------------------------
def extract_text_from_pdf(file_path: str) -> str:
    """Extracts all text from a PDF resume. Returns empty string on failure."""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""
    return text.strip()


# -------------------------------------------------------
# 2. Text Preprocessing
# -------------------------------------------------------
def normalize_text(text: str) -> str:
    """Normalizes text by fixing newlines, spaces, and unicode issues."""
    if not text:
        return ""
    t = text.replace('\r\n', '\n').replace('\r', '\n')
    t = re.sub(r'\u00A0', ' ', t)  # Remove non-breaking spaces
    t = re.sub(r'\n{3,}', '\n\n', t)  # Limit blank lines
    return t.strip()


# -------------------------------------------------------
# 3. Extract Name & Email
# -------------------------------------------------------
def extract_name(text: str) -> Optional[str]:
    """
    Extracts the candidate's name.
    Uses heuristics like capitalization and position, with a fallback check using the next line for contact info.
    """
    if not text:
        return None
    lines = text.splitlines()
    title_keywords = {"engineer", "developer", "guidelines", "resume", "cv", "profile", "software"}

    for i, line in enumerate(lines[:10]):  # Check first 10 lines for flexibility
        candidate = line.strip()
        if not candidate or EMAIL_RE.search(candidate):
            continue
        
        # Check word count and capitalization
        words = candidate.split()
        if 2 <= len(words) <= 5:
            # Ensure most words are capitalized (e.g., "John Doe" not "SOFTWARE ENGINEER")
            is_capitalized = all(word[0].isupper() for word in words if word)
            if is_capitalized and not any(kw.lower() in candidate.lower() for kw in title_keywords):
                # Look ahead for contact info as a hint (email or phone number)
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if EMAIL_RE.search(next_line) or re.search(r'\+?\d{9,}', next_line):  # Phone pattern
                        return candidate
                return candidate
    
    # Fallback: if no match, return None
    return None


def extract_email(text: str) -> Optional[str]:
    """Finds the first valid email address in the resume."""
    if not text:
        return None
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


# -------------------------------------------------------
# 4. Manual Extraction
# -------------------------------------------------------
def find_inline_field(text: str, heading_variants: List[str]) -> Optional[str]:
    """Finds patterns like 'Skills: Python, Java | C++'."""
    for h in heading_variants:
        pattern = rf'(?im)\b{re.escape(h)}\s*[:\-]\s*(.+)'
        m = re.search(pattern, text)
        if m:  # Check if a match was found
            captured = m.group(1).strip().splitlines()[0].strip()
            if captured:
                return captured
    return None


def find_block_field(text: str, heading_variants: List[str]) -> Optional[str]:
    """Finds bullet-point style sections under headings."""
    heading_pattern = rf'(?im)^ *({"|".join(re.escape(h) for h in heading_variants)})\b.*'
    m = re.search(heading_pattern, text)
    if not m:
        return None

    start_pos = m.end()
    lines = text[start_pos:].strip().splitlines()
    collected = []

    # Flatten all possible heading variants to use as stop words
    all_headings = sum(FIELD_HEADINGS.values(), [])

    for line in lines:
        if not line.strip():  # Stop at the first empty line after collecting some content
            if collected:
                break
            else:
                continue

        # Stop if we hit another section's heading
        stripped_low = line.strip().lower()
        if any(stripped_low.startswith(hv) for hv in all_headings if hv not in heading_variants):
            break

        collected.append(line)
        if len(collected) >= 30:  # Safety break
            break

    return "\n".join(collected).strip() if collected else None


def parse_inline_list(raw: str) -> List[str]:
    """Splits inline text into list items."""
    return [p.strip() for p in INLINE_SPLIT_RE.split(raw) if p.strip()]


def parse_block_list(raw_block: str) -> List[str]:
    """Parses bullet-point or line-separated items."""
    result = []
    for line in raw_block.splitlines():
        ln = re.sub(BULLET_START_RE, '', line).strip()
        ln = re.sub(r'^\s*(\d+\.|[a-zA-Z]\)|[ivx]+\.)\s*', '', ln).strip()  # Remove list markers
        if not ln:
            continue
        # Handle lines that have multiple items separated by commas/etc.
        if INLINE_SPLIT_RE.search(ln):
            result.extend([s.strip() for s in INLINE_SPLIT_RE.split(ln) if s.strip()])
        else:
            result.append(ln)
    return result


def clean_and_normalize_list(items: List[str]) -> List[str]:
    """Removes duplicates, trims spaces, and normalizes formatting."""
    seen, out = set(), []
    for it in items:
        # Normalize whitespace and remove trailing punctuation
        token_norm = re.sub(r'\s+', ' ', it.strip()).strip(".;,:")
        if token_norm and token_norm.lower() not in seen:
            seen.add(token_norm.lower())
            out.append(token_norm)
    return out


# -------------------------------------------------------
# 5. LLM Fallback (Gemini)
# -------------------------------------------------------
def call_llm_extract_field(resume_text: str, field: str) -> List[str]:
    """Calls Gemini API to extract a specific field."""
    if not resume_text:
        return []
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ Gemini API key not found in .env file. LLM fallback skipped.")
        return []

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    # Adjust prompt based on field type
    if field == "name":
        prompt = f"""
From the resume text below, extract the candidate's "{field}" and return the result ONLY as a JSON array of strings containing the full name.
Do not include any explanations or introductory text. If no name is found, return an empty array [].

Resume Text:
---
{resume_text[:4000]}
---

Example for "name": ["John Doe"]
Example for other fields (e.g., "Skills"): ["Python", "Data Analysis"]

JSON Array Output:
"""
    else:
        prompt = f"""
From the resume text below, extract the "{field}" and return the result ONLY as a JSON array of strings.
Do not include any explanations or introductory text. If nothing is found, return an empty array [].

Resume Text:
---
{resume_text[:4000]}
---

Example for "Skills": ["Python", "Data Analysis", "Project Management"]
Example for "Experience": ["Software Engineer at Google (2020-Present)", "Intern at Microsoft (Summer 2019)"]

JSON Array Output:
"""

    try:
        print(f"[LLM Fallback] Calling Gemini for '{field}'...")
        response = model.generate_content(prompt)
        # Clean up potential markdown code blocks from the response
        json_string = re.sub(r'^\s*```json\s*|\s*```\s*$', '', response.text.strip(), flags=re.MULTILINE)

        parsed_list = json.loads(json_string)
        if isinstance(parsed_list, list) and all(isinstance(item, str) for item in parsed_list):
            print(f"parsed - {field}")
            return parsed_list
        else:
            print(f"⚠️ Unexpected API format for '{field}'.")
            return []
    except Exception as e:
        print(f"❌ Gemini API error for '{field}': {e}")
        return []


# -------------------------------------------------------
# 6. Hybrid Extraction Logic
# -------------------------------------------------------
def extract_field_hybrid(resume_text: str, field: str) -> List[str]:
    """Tries inline -> block -> LLM fallback."""
    if not resume_text:
        return []
    assert field in FIELD_HEADINGS, f"Unknown field: {field}"
    
    heading_variants = FIELD_HEADINGS[field]

    # 1. Try inline parsing
    inline_raw = find_inline_field(resume_text, heading_variants)
    if inline_raw:
        parsed = clean_and_normalize_list(parse_inline_list(inline_raw))
        if parsed:
            print(f"✅ Parsed '{field}' using inline method.")
            return parsed

    # 2. Try block parsing
    block_raw = find_block_field(resume_text, heading_variants)
    if block_raw:
        parsed = clean_and_normalize_list(parse_block_list(block_raw))
        if parsed:
            print(f"✅ Parsed '{field}' using block method.")
            return parsed

    # 3. Fallback to LLM
    print(f"ℹ️ Could not parse '{field}' manually, falling back to LLM.")
    return clean_and_normalize_list(call_llm_extract_field(resume_text, field))


def extract_all_fields(resume_text: str, fields: Optional[List[str]] = None) -> Dict[str, Union[str, List[str]]]:
    """
    Extracts all relevant fields (plus name & email) from resume text.
    Returns a dictionary ready for MongoDB storage and JSON response.
    """
    if not resume_text:
        return {
            "name": "Not Found",
            "email": "Not Found",
            "skills": [],
            "experience": [],
            "education": [],
            "achievements": []
        }
    
    normalized_text = normalize_text(resume_text)
    
    if fields is None:
        fields = ["skills", "experience", "education", "achievements"]

    data: Dict[str, Union[str, List[str]]] = {}
    for f in fields:
        try:
            data[f] = extract_field_hybrid(normalized_text, f)
        except Exception as e:
            print(f"Error parsing field '{f}': {e}")
            data[f] = []  # Return empty list for failed fields
    data["name"] = extract_name(normalized_text) or "Not Found"
    data["email"] = extract_email(normalized_text) or "Not Found"
    return data


# -------------------------------------------------------
# 7. Main Execution (Test)
# -------------------------------------------------------
if __name__ == "__main__":
    # NOTE: Ensure 'sample_resume.pdf' exists in the same directory.
    # NOTE: Ensure a .env file with your GEMINI_API_KEY is present for the LLM fallback.
    resume_file = "sample_resume.pdf"
    
    if os.path.exists(resume_file):
        print(f"Parsing '{resume_file}'...")
        resume_text_content = extract_text_from_pdf(resume_file)
        parsed_data = extract_all_fields(resume_text_content)
        print("\n--- PARSED RESUME DATA ---")
        print(json.dumps(parsed_data, indent=2))
    else:
        print(f"Error: The file '{resume_file}' was not found.")
        print("Please add a PDF resume to the directory and rename it to 'sample_resume.pdf' to run this test.")