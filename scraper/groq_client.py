import os
import logging
import httpx
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("GroqClient")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
FAST_MODEL = "llama-3.1-8b-instant"
HEAVY_MODEL = "llama-3.3-70b-versatile"

class GroqClient:
    """Client for Groq AI Ultra-Fast LLM API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate_completion(self, system_prompt: str, user_prompt: str, model: str = FAST_MODEL, temperature: float = 0.7) -> Optional[str]:
        """Generates AI completion using Groq LLM endpoint."""
        if not self.api_key:
            return None

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(GROQ_API_URL, headers=self.headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0]["message"]["content"].strip()
                else:
                    logger.warning(f"Groq API error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.warning(f"Groq API connection failed: {e}")
        return None

    def expand_niche_search_keywords(self, query: str, country: str) -> List[str]:
        """Uses Groq AI to generate localized commercial search terms for a niche & country."""
        if not self.api_key:
            return [query]

        system_prompt = "You are a B2B lead generation search engineer. Output ONLY a comma-separated list of 5 concise commercial search terms."
        user_prompt = f"Generate 5 targeted commercial search keywords for finding '{query}' businesses in {country}. Example output: keyword 1, keyword 2, keyword 3, keyword 4, keyword 5"
        
        raw_res = self.generate_completion(system_prompt, user_prompt, model=FAST_MODEL, temperature=0.5)
        if raw_res:
            terms = [t.strip().strip('"').strip("'") for t in raw_res.split(",") if t.strip()]
            return terms[:5]
        return [query]

    def generate_personalized_cold_email(self, lead: Dict[str, Any], dev_profile: Dict[str, str], pitch_strategy: str) -> Dict[str, str]:
        """Generates a hyper-personalized B2B cold outreach email using Groq AI."""
        company_name = lead.get("company_name", "your business")
        dm_name = lead.get("decision_maker_name", "Hiring Team / Founder")
        niche_domain = lead.get("domain", "")
        age = lead.get("age_category", "")
        employees = lead.get("employee_count", "")
        revenue = lead.get("revenue_range", "")

        if not self.api_key:
            return {
                "subject": f"Mobile App & Digital Upgrade for {company_name}",
                "body": f"Hi {dm_name},\n\nI came across {company_name} ({niche_domain}) and was really impressed by your operations. "
                        f"As a Flutter Mobile App Developer, I help businesses build high-performance mobile apps that drive sales and customer engagement.\n\n"
                        f"I'd love to share a quick 2-minute demo of what we can build for {company_name}. Would you be open to a brief chat this week?\n\n"
                        f"Best regards,\n{dev_profile.get('name', 'Irtaza Khalid')}\n{dev_profile.get('portfolio', 'https://irtaza.dev')}"
            }

        system_prompt = (
            "You are an elite B2B sales copywriter specializing in cold emails for mobile & software developers. "
            "Write a concise, high-converting, professional cold email (under 120 words). "
            "Return output in valid JSON format with keys 'subject' and 'body'."
        )
        user_prompt = (
            f"Draft a cold pitch to {dm_name} at {company_name} ({niche_domain}).\n"
            f"Target Details: Business Age: {age}, Employee Count: {employees}, Revenue: {revenue}\n"
            f"Developer Profile: {dev_profile.get('name', 'Irtaza Khalid')}, {dev_profile.get('role', 'Flutter Developer')}, Portfolio: {dev_profile.get('portfolio', 'https://irtaza.dev')}\n"
            f"Pitch Strategy: {pitch_strategy}\n"
            "Format: {\"subject\": \"...\", \"body\": \"...\"}"
        )

        res = self.generate_completion(system_prompt, user_prompt, model=HEAVY_MODEL, temperature=0.6)
        if res:
            try:
                import json
                clean_json = res.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                if "subject" in data and "body" in data:
                    return data
            except Exception:
                pass
        
        return {
            "subject": f"Mobile App & Digital Upgrade for {company_name}",
            "body": f"Hi {dm_name},\n\nI came across {company_name} ({niche_domain}) and was really impressed by your operations. "
                    f"As a Flutter Mobile App Developer, I help businesses build high-performance mobile apps that drive sales and customer engagement.\n\n"
                    f"I'd love to share a quick 2-minute demo of what we can build for {company_name}. Would you be open to a brief chat this week?\n\n"
                    f"Best regards,\n{dev_profile.get('name', 'Irtaza Khalid')}\n{dev_profile.get('portfolio', 'https://irtaza.dev')}"
        }
