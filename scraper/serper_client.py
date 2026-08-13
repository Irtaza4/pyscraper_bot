import os
import json
import logging
import httpx
import urllib.parse
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("SerperClient")

SERPER_BASE_URL = "https://google.serper.dev"
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "serper_cache.json")

class SerperClient:
    """Client for Serper.dev official Google Search & Google Places API with credit-saving local cache."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Loads local search cache to prevent wasting Serper free credits."""
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

    def search_google_organic(self, query: str, country: str = "", max_results: int = 100) -> List[Dict[str, str]]:
        """Search Google via Serper.dev for up to 100 business leads per request with local caching."""
        if not self.api_key:
            return []

        clean_country = country if country != "Global" else ""
        q_str = f"{query} {clean_country}".strip()
        cache_key = f"serper_org_{q_str.lower()}"

        if cache_key in self.cache:
            logger.info(f"Loaded {len(self.cache[cache_key])} Serper Google results from local cache for '{q_str}'")
            return self.cache[cache_key][:max_results]

        url = f"{SERPER_BASE_URL}/search"
        payload = {
            "q": q_str,
            "num": min(max_results, 100)
        }

        results = []
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=self.headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    organic = data.get("organic", [])
                    for item in organic:
                        link = item.get("link") or item.get("url", "")
                        if link and link.startswith("http"):
                            parsed = urllib.parse.urlparse(link)
                            domain = parsed.netloc.lower().replace("www.", "")
                            
                            if domain and not any(ex in domain for ex in ["google", "youtube", "wikipedia", "facebook", "instagram", "twitter", "reddit"]):
                                title = item.get("title", domain)
                                snippet = item.get("snippet", title)
                                results.append({
                                    "company_name": domain.split(".")[0].capitalize(),
                                    "url": f"{parsed.scheme}://{parsed.netloc}",
                                    "domain": domain,
                                    "snippet": title or snippet,
                                    "age_category": "⭐ Active Business"
                                })

                    if results:
                        self.cache[cache_key] = results
                        self._save_cache()
                else:
                    logger.warning(f"Serper Search API error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.warning(f"Serper Search API failed: {e}")

        return results[:max_results]

    def search_google_places(self, query: str, country: str = "", max_results: int = 20) -> List[Dict[str, str]]:
        """Search Google Places (Maps) via Serper.dev for direct local business phone numbers and websites."""
        if not self.api_key:
            return []

        clean_country = country if country != "Global" else ""
        q_str = f"{query} {clean_country}".strip()
        cache_key = f"serper_places_{q_str.lower()}"

        if cache_key in self.cache:
            logger.info(f"Loaded {len(self.cache[cache_key])} Serper Google Places leads from local cache for '{q_str}'")
            return self.cache[cache_key][:max_results]

        url = f"{SERPER_BASE_URL}/places"
        payload = {
            "q": q_str,
            "num": min(max_results, 20)
        }

        results = []
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=self.headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    places = data.get("places", [])
                    for p in places:
                        site = p.get("website") or ""
                        domain = ""
                        if site and site.startswith("http"):
                            parsed = urllib.parse.urlparse(site)
                            domain = parsed.netloc.lower().replace("www.", "")

                        company_name = p.get("title", "Local Business")
                        phone = p.get("phoneNumber", "")
                        address = p.get("address", "")

                        results.append({
                            "company_name": company_name,
                            "url": site if site else f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(company_name + ' ' + clean_country)}",
                            "domain": domain if domain else company_name.lower().replace(" ", "") + ".com",
                            "snippet": f"{company_name} - {address} (Phone: {phone})",
                            "primary_phone": phone,
                            "address": address,
                            "age_category": "⭐ Active Business"
                        })

                    if results:
                        self.cache[cache_key] = results
                        self._save_cache()
                else:
                    logger.warning(f"Serper Places API error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.warning(f"Serper Places API failed: {e}")

        return results[:max_results]
