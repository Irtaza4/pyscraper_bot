import os
import json
import logging
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ApolloClient")

APOLLO_BASE_URL = "https://api.apollo.io/v1"
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "search_cache.json")

class ApolloClient:
    """Client for Apollo.io B2B Organization & Firmographics Enrichment API with local credit-saving cache."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("APOLLO_API_KEY", "153e-Q99n77izFwENTIHhQ")
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Loads local search cache to prevent wasting Apollo credits."""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_cache(self):
        """Saves search results to local cache."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass

    def enrich_company(self, domain: str) -> Dict[str, Any]:
        """Enriches company firmographics, employee count, LinkedIn profile, and social links using Apollo API."""
        if not self.api_key or not domain:
            return {}

        clean_dom = domain.replace("https://", "").replace("http://", "").split("/")[0].replace("www.", "").lower()
        cache_key = f"apollo_{clean_dom}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        url = f"{APOLLO_BASE_URL}/organizations/enrich"
        params = {"domain": clean_dom}

        enrich_data = {}
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, headers=self.headers, params=params)
                if resp.status_code == 200:
                    data = resp.json().get("organization", {})
                    if data:
                        enrich_data = {
                            "company_name": data.get("name") or clean_dom.split(".")[0].capitalize(),
                            "employee_count": str(data.get("estimated_num_employees", "")),
                            "industry": data.get("industry", ""),
                            "linkedin_company": data.get("linkedin_url", ""),
                            "twitter_company": data.get("twitter_url", ""),
                            "facebook_company": data.get("facebook_url", ""),
                            "keywords": data.get("keywords", [])[:5] if data.get("keywords") else []
                        }
                        self.cache[cache_key] = enrich_data
                        self._save_cache()
                else:
                    logger.warning(f"Apollo Org Enrich API error ({resp.status_code}): {resp.text[:150]}")
        except Exception as e:
            logger.warning(f"Apollo Org Enrich API failed: {e}")

        return enrich_data
