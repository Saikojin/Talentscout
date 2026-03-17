import os
import io
import re
import json
import sys

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

# Common tech skills to try and extract
TECH_KEYWORDS = {
    "javascript", "python", "java", "c++", "c#", "ruby", "go", "rust", "typescript", "swift", "kotlin",
    "react", "angular", "vue", "node.js", "django", "flask", "spring", "asp.net", "express",
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible", "jenkins", "gitlab", "github actions",
    "qa", "testing", "automation", "selenium", "cypress", "playwright", "appium", "karate", "jmeter",
    "agile", "scrum", "kanban", "jira", "confluence", "git", "linux", "unix", "bash", "powershell",
    "machine learning", "ai", "data science", "nlp", "computer vision", "tensorflow", "pytorch"
}

def extract_text(file_content, filename):
    """Extracts text from various file formats."""
    ext = os.path.splitext(filename)[1].lower()
    text = ""
    
    if ext == ".pdf":
        if PdfReader is None:
            return "Error: pypdf is missing. Run 'pip install pypdf'."
        try:
            reader = PdfReader(io.BytesIO(file_content))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            text = f"Error reading PDF: {e}"
            
    elif ext == ".docx":
        if docx is None:
            return "Error: python-docx is missing. Run 'pip install python-docx'."
        try:
            doc = docx.Document(io.BytesIO(file_content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            text = f"Error reading DOCX: {e}"
            
    elif ext in [".txt", ".md", ".csv"]:
        try:
            text = file_content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_content.decode("latin-1")
            except:
                text = "Error: Could not decode text file."
    else:
        text = f"Unsupported file type: {ext}"
        
    return text

def draft_skillset(text):
    """Drafts a base_skillset.json based on common keywords found in the text."""
    lower_text = text.lower()
    found_skills = set()
    
    # Simple word boundary matching for tech keywords
    for kw in TECH_KEYWORDS:
        if re.search(rf'\b{re.escape(kw)}\b', lower_text):
            found_skills.add(kw)
            
    # Format the found skills nicely (capitalize first letter if not an acronym)
    formatted_skills = []
    for skill in found_skills:
        if len(skill) <= 3 and skill not in ["qa", "go"]:
            formatted_skills.append(skill.upper())
        else:
            formatted_skills.append(skill.title())
            
    # Sort alphabetically
    formatted_skills.sort()
    
    draft = {
        "name": "Extracted Name (Please update)",
        "experience_years": 0,
        "core_skills": formatted_skills,
        "disqualified_skills": [
            "ExampleSkillToIgnore"
        ],
        "preferred_locations": [
            "Remote",
            "City, State"
        ],
        "minimum_salary": 100000
    }
    
    return draft

# Keep original cli for backward compatibility
def extract_text_from_docx(docx_path):
    with open(docx_path, "rb") as f:
        file_content = f.read()
    return extract_text(file_content, docx_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python resume_parser.py <path_to_docx>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    text = extract_text_from_docx(file_path)
    print(text)
