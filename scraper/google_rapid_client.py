import os
import json
import logging
import httpx
import urllib.parse
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("GoogleRapidClient")

SEARCH_HOST = "google-search-master-mega.p.rapidapi.com"
MAPS_HOST = "google-maps-lead-extractor-business-search.p.rapidapi.com"
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "search_cache.json")

class GoogleRapidClient:
    """Client for RapidAPI Google Search Master & Google Maps Lead Extractor with local credit-saving cache."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY", "")
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Loads local search cache to prevent wasting RapidAPI credits."""
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

    def search_google_maps_leads(self, query: str, location: str = "United States", max_results: int = 50) -> List[Dict[str, str]]:
        """Search Google Maps via RapidAPI for direct business phone numbers, addresses, and websites."""
        if not self.api_key:
            return []

        clean_loc = location if location != "Global" else "United States"
        cache_key = f"gmaps_{query.lower()}_{clean_loc.lower()}"

        if cache_key in self.cache:
            logger.info(f"Loaded {len(self.cache[cache_key])} Google Maps leads from local cache for '{query}' in {clean_loc}")
            return self.cache[cache_key][:max_results]

        url = f"https://{MAPS_HOST}/api/v1/google-maps-lead-extractor/search"
        headers = {
            "Content-Type": "application/json",
            "x-rapidapi-host": MAPS_HOST,
            "x-rapidapi-key": self.api_key
        }
        payload = {
            "query": query,
            "location": clean_loc,
            "limit": min(max_results, 50)
        }

        results = []
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("results", [])
                    for item in items:
                        site = item.get("website") or ""
                        domain = ""
                        if site and site.startswith("http"):
                            parsed = urllib.parse.urlparse(site)
                            domain = parsed.netloc.lower().replace("www.", "")

                        company_name = item.get("name", "Local Business")
                        phone = item.get("phone", "")
                        address = item.get("address", "")
                        
                        results.append({
                            "company_name": company_name,
                            "url": site if site else f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(company_name + ' ' + clean_loc)}",
                            "domain": domain if domain else company_name.lower().replace(" ", "") + ".com",
                            "snippet": f"{company_name} - {address} (Phone: {phone})",
                            "primary_phone": phone,
                            "address": address,
                            "age_category": "⭐ Active Business"
                        })

                    if results:
                        self.cache[cache_key] = results
                        self._save_cache()
        except Exception as e:
            logger.warning(f"Google Maps Lead Extractor failed: {e}")

        return results[:max_results]

    def search_google_businesses(self, query: str, country: str = "", max_results: int = 100) -> List[Dict[str, str]]:
        """Search Google via RapidAPI for business leads with 1-request 100-item batching & caching."""
        if not self.api_key:
            return []

        clean_country = country if country != "Global" else ""
        q_str = f"{query} {clean_country}".strip()
        cache_key = f"google_{q_str.lower()}"

        if cache_key in self.cache:
            logger.info(f"Loaded {len(self.cache[cache_key])} Google search results from local cache for '{q_str}'")
            return self.cache[cache_key][:max_results]

        url = f"https://{SEARCH_HOST}/search"
        headers = {
            "x-rapidapi-host": SEARCH_HOST,
            "x-rapidapi-key": self.api_key
        }
        params = {
            "q": q_str,
            "num": str(min(max_results, 100)),
            "page": "1"
        }

        results = []
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, headers=headers, params=params)
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
                    logger.warning(f"RapidAPI Google Search error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.warning(f"RapidAPI Google Search failed: {e}")

        return results[:max_results]
