import logging
from typing import List, Dict, Any, Callable, Optional
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from .fetcher import HTTPFetcher
from .contact_extractor import ContactExtractor
from .lead_scorer import LeadScorer

logger = logging.getLogger("LeadCrawler")

BAD_TITLE_KEYWORDS = ["checking your browser", "just a moment", "attention required", "cloudflare", "403 forbidden", "access denied", "security check"]

class LeadCrawler:
    """Multi-domain crawler that deeply scans websites concurrently using multi-threading."""

    def __init__(self, fetcher: Optional[HTTPFetcher] = None):
        self.fetcher = fetcher or HTTPFetcher()

    def clean_company_name(self, domain: str, title: str) -> str:
        clean_domain = domain.replace("www.", "").split(".")[0].capitalize()
        if not title:
            return clean_domain

        title_lower = title.lower()
        if any(bad in title_lower for bad in BAD_TITLE_KEYWORDS):
            return clean_domain

        title_parts = title.split("|")[0].split("-")[0].split(":")[0].strip()
        if len(title_parts) >= 2 and len(title_parts) < 35:
            return title_parts

        return clean_domain

    def crawl_domain(self, url: str, max_subpages: int = 3) -> Dict[str, Any]:
        """Deeply crawl a domain homepage and contact subpages for lead data."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        domain = urlparse(url).netloc or url

        # 1. Fetch Homepage
        html = self.fetcher.fetch(url)
        if not html:
            clean_name = domain.replace("www.", "").split(".")[0].capitalize()
            return {
                "domain": domain,
                "company_name": clean_name,
                "url": url,
                "status": "Failed to fetch homepage",
                "emails": [],
                "phones": [],
                "socials": {},
                "score": 0,
                "category": "Unreachable"
            }

        base_data = ContactExtractor.extract_from_html(html, url)
        all_emails = set(base_data.get("emails", []))
        all_phones = set(base_data.get("phones", []))
        socials = base_data.get("socials", {})
        subpages = base_data.get("contact_subpages", [])
        dm_name = base_data.get("decision_maker_name", "")
        dm_role = base_data.get("decision_maker_role", "Founder & CEO")

        # 2. Deep scan subpages if emails are missing or sparse
        scanned_subpages = []
        if len(all_emails) == 0 and subpages:
            for sub_url in subpages[:max_subpages]:
                sub_html = self.fetcher.fetch(sub_url)
                if sub_html:
                    scanned_subpages.append(sub_url)
                    sub_data = ContactExtractor.extract_from_html(sub_html, sub_url)
                    all_emails.update(sub_data.get("emails", []))
                    all_phones.update(sub_data.get("phones", []))
                    if not dm_name and sub_data.get("decision_maker_name"):
                        dm_name = sub_data["decision_maker_name"]
                        dm_role = sub_data["decision_maker_role"]
                    for plat, link in sub_data.get("socials", {}).items():
                        if plat not in socials:
                            socials[plat] = link

        # Consolidated record
        consolidated = {
            "url": url,
            "title": base_data.get("title", ""),
            "meta_description": base_data.get("meta_description", ""),
            "emails": list(all_emails),
            "phones": list(all_phones),
            "socials": socials,
            "has_app_store": base_data.get("has_app_store", False)
        }

        # 3. Score Lead
        score_info = LeadScorer.calculate_score(consolidated)

        # Clean Company Name
        company_name = self.clean_company_name(domain, base_data.get("title", ""))

        primary_email = list(all_emails)[0] if all_emails else ""
        primary_phone = list(all_phones)[0] if all_phones else ""

        # Detect Business Age Category
        from .lead_finder import LeadFinder
        full_text = f"{base_data.get('title', '')} {base_data.get('meta_description', '')}"
        age_category = LeadFinder.detect_business_age(full_text)

        # Enrich via Explorium Data & Contact Enrichment API
        from .explorium_client import ExploriumClient
        explorium = ExploriumClient()
        exp_data = explorium.enrich_full_lead(domain, company_name=company_name, decision_maker_name=dm_name)

        if exp_data.get("explorium_emails"):
            all_emails.update(exp_data["explorium_emails"])
        if exp_data.get("explorium_phones"):
            all_phones.update(exp_data["explorium_phones"])
        if exp_data.get("linkedin_company") and not socials.get("LinkedIn"):
            socials["LinkedIn"] = exp_data["linkedin_company"]

        # Enrich via Apollo.io Organization API (Firmographics & Socials)
        from .apollo_client import ApolloClient
        apollo = ApolloClient()
        apollo_data = apollo.enrich_company(domain)
        if apollo_data:
            if apollo_data.get("linkedin_company") and not socials.get("LinkedIn"):
                socials["LinkedIn"] = apollo_data["linkedin_company"]
            if apollo_data.get("twitter_company") and not socials.get("Twitter"):
                socials["Twitter"] = apollo_data["twitter_company"]
            if apollo_data.get("facebook_company") and not socials.get("Facebook"):
                socials["Facebook"] = apollo_data["facebook_company"]
            if not exp_data.get("employee_count") and apollo_data.get("employee_count"):
                exp_data["employee_count"] = f"{apollo_data['employee_count']} Employees"

        primary_email = list(all_emails)[0] if all_emails else ""
        primary_phone = list(all_phones)[0] if all_phones else ""

        return {
            "domain": domain,
            "company_name": company_name,
            "url": url,
            "age_category": age_category,
            "explorium_verified": exp_data.get("explorium_verified", False),
            "employee_count": exp_data.get("employee_count", ""),
            "revenue_range": exp_data.get("revenue_range", ""),
            "funding_total": exp_data.get("funding_total", ""),
            "decision_maker_name": dm_name,
            "decision_maker_role": dm_role,
            "primary_email": primary_email,
            "all_emails": ", ".join(all_emails),
            "primary_phone": primary_phone,
            "linkedin": socials.get("LinkedIn", ""),
            "twitter": socials.get("Twitter/X", socials.get("Twitter", "")),
            "facebook": socials.get("Facebook", ""),
            "instagram": socials.get("Instagram", ""),
            "title": base_data.get("title", ""),
            "meta_description": base_data.get("meta_description", ""),
            "scanned_subpages": len(scanned_subpages),
            "has_app": consolidated["has_app_store"],
            "score": score_info["score"],
            "category": score_info["category"],
            "reasons": " | ".join(score_info["reasons"]),
            "status": "Success" if primary_email else "No email found"
        }

    def crawl_batch(self, urls: List[str], max_workers: int = 8, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[Dict[str, Any]]:
        """Crawl batch URLs concurrently with 8 parallel worker threads."""
        results = []
        total = len(urls)
        completed_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.crawl_domain, u.strip()): u.strip() for u in urls if u.strip()}
            for future in as_completed(future_to_url):
                completed_count += 1
                u = future_to_url[future]
                if progress_callback:
                    progress_callback(completed_count, total, u)
                try:
                    lead = future.result()
                    results.append(lead)
                except Exception:
                    pass

        return results
