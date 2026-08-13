import os
import json
from typing import Dict, Any, Optional
from pypdf import PdfReader

DEFAULT_PROFILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "profile.json")

class CVParser:
    """Parses CV text/PDF files and manages developer profile data."""

    @staticmethod
    def load_default_profile() -> Dict[str, Any]:
        if os.path.exists(DEFAULT_PROFILE_PATH):
            with open(DEFAULT_PROFILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("developer", {})
        return {}

    @staticmethod
    def parse_pdf(pdf_path: str) -> str:
        text = ""
        try:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            text = f"Error reading PDF: {e}"
        return text
