import os
import logging
import httpx
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ExploriumClient")

BASE_URL = "https://api.explorium.ai/v1"

class ExploriumClient:
    """Client for Explorium Data & Contact Enrichment API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EXPLORIUM_API_KEY", "")
        self.headers = {
            "api_key": self.api_key,
            "Content-Type": "application/json"
        }

    def search_businesses_by_country_and_niche(self, country_code: str, keywords: List[str], max_results: int = 100) -> List[Dict[str, str]]:
        """Search Explorium global database (60,000+ companies) by country code and primary niche keyword."""
        if not self.api_key:
            return []

        url = f"{BASE_URL}/businesses"
        filters = {}
        if country_code:
            filters["country_code"] = {"values": [country_code.upper()]}
        if keywords:
            primary_kw = keywords[0] if isinstance(keywords, list) else str(keywords)
            filters["website_keywords"] = {"values": [primary_kw]}

        payload = {
            "mode": "preview",
            "page_size": min(max_results, 100),
            "filters": filters
        }
        results = []
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=self.headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    for item in data:
                        domain = item.get("domain") or item.get("website", "")
                        if domain:
                            domain = domain.replace("https://", "").replace("http://", "").split("/")[0].replace("www.", "").lower()
                            company_name = item.get("name") or domain.split(".")[0].capitalize()
                            results.append({
                                "company_name": company_name,
                                "url": f"https://{domain}",
                                "domain": domain,
                                "snippet": item.get("business_description") or f"{company_name} - {country_code.upper()}",
                                "age_category": "🏛️ Established" if item.get("company_age") else "⭐ Active Business"
                            })
        except Exception as e:
            logger.warning(f"Explorium direct business search failed: {e}")
        return results

    def match_business(self, domain: str, company_name: Optional[str] = None) -> Optional[str]:
        """Matches a company domain/name to get Explorium business_id."""
        if not self.api_key:
            return None

        url = f"{BASE_URL}/businesses/match"
        payload = {
            "businesses_to_match": [{
                "domain": domain.strip().lower(),
                "name": company_name.strip() if company_name else None
            }]
        }
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, headers=self.headers, json=payload)
                if resp.status_code == 200:
                    matched = resp.json().get("matched_businesses", [])
                    if matched and matched[0].get("business_id"):
                        return matched[0]["business_id"]
        except Exception as e:
            logger.warning(f"Explorium business match failed for {domain}: {e}")
        return None

    def enrich_firmographics(self, business_id: str) -> Dict[str, Any]:
        """Enriches business firmographics (revenue, employees, NAICS, LinkedIn, logo)."""
        if not self.api_key:
            return {}

        url = f"{BASE_URL}/businesses/firmographics/enrich"
        payload = {"business_id": business_id}
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, headers=self.headers, json=payload)
                if resp.status_code == 200:
                    return resp.json().get("data", {})
        except Exception as e:
            logger.warning(f"Explorium firmographics enrich failed for {business_id}: {e}")
        return {}

    def enrich_funding(self, business_id: str) -> Dict[str, Any]:
        """Enriches company funding and acquisition details."""
        if not self.api_key:
            return {}

        url = f"{BASE_URL}/businesses/funding_and_acquisition/enrich"
        payload = {"business_id": business_id}
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, headers=self.headers, json=payload)
                if resp.status_code == 200:
                    return resp.json().get("data", {})
        except Exception as e:
            logger.warning(f"Explorium funding enrich failed for {business_id}: {e}")
        return {}

    def match_prospect(self, full_name: str, company_name: str) -> Optional[str]:
        """Matches a prospect decision-maker to get Explorium prospect_id."""
        if not self.api_key:
            return None

        url = f"{BASE_URL}/prospects/match"
        payload = {
            "prospects_to_match": [{
                "full_name": full_name.strip(),
                "company_name": company_name.strip()
            }]
        }
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, headers=self.headers, json=payload)
                if resp.status_code == 200:
                    matched = resp.json().get("matched_prospects", [])
                    if matched and matched[0].get("prospect_id"):
                        return matched[0]["prospect_id"]
        except Exception as e:
            logger.warning(f"Explorium prospect match failed for {full_name} @ {company_name}: {e}")
        return None

    def enrich_prospect_contact(self, prospect_id: str) -> Dict[str, Any]:
        """Enriches prospect verified emails, direct phone, and mobile numbers."""
        if not self.api_key:
            return {}

        url = f"{BASE_URL}/prospects/contacts_information/enrich"
        payload = {"prospect_id": prospect_id}
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, headers=self.headers, json=payload)
                if resp.status_code == 200:
                    return resp.json().get("data", {})
        except Exception as e:
            logger.warning(f"Explorium prospect contact enrich failed for {prospect_id}: {e}")
        return {}

    def enrich_full_lead(self, domain: str, company_name: str = "", decision_maker_name: str = "") -> Dict[str, Any]:
        """Runs full Explorium enrichment pipeline for a company and prospect."""
        enrichment_data = {
            "explorium_verified": False,
            "explorium_emails": [],
            "explorium_phones": [],
            "employee_count": "",
            "revenue_range": "",
            "linkedin_company": "",
            "funding_total": "",
            "investors": []
        }

        if not self.api_key:
            return enrichment_data

        # 1. Match and enrich business
        biz_id = self.match_business(domain, company_name)
        if biz_id:
            firmo = self.enrich_firmographics(biz_id)
            if firmo:
                enrichment_data["explorium_verified"] = True
                enrichment_data["employee_count"] = firmo.get("number_of_employees_range", "")
                enrichment_data["revenue_range"] = firmo.get("yearly_revenue_range", "")
                enrichment_data["linkedin_company"] = firmo.get("linkedin_profile", "")

            fund = self.enrich_funding(biz_id)
            if fund:
                total_usd = fund.get("known_funding_total_value")
                if total_usd:
                    enrichment_data["funding_total"] = f"${total_usd:,.0f}"
                enrichment_data["investors"] = fund.get("investors", [])

        # 2. Match and enrich decision maker contact if available
        if decision_maker_name and company_name:
            prospect_id = self.match_prospect(decision_maker_name, company_name)
            if prospect_id:
                contact = self.enrich_prospect_contact(prospect_id)
                if contact:
                    emails = [e["address"] for e in contact.get("emails", []) if e.get("address")]
                    phones = [p["phone_number"] for p in contact.get("phone_numbers", []) if p.get("phone_number")]
                    if contact.get("mobile_phone"):
                        phones.insert(0, contact["mobile_phone"])
                    
                    enrichment_data["explorium_emails"] = emails
                    enrichment_data["explorium_phones"] = list(set(phones))

        return enrichment_data
