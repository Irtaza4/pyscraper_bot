import logging
from typing import List, Dict, Any, Callable, Optional
from urllib.parse import urlparse

from .fetcher import HTTPFetcher
from .contact_extractor import ContactExtractor
from .lead_scorer import LeadScorer

logger = logging.getLogger("LeadCrawler")

BAD_TITLE_KEYWORDS = ["checking your browser", "just a moment", "attention required", "cloudflare", "403 forbidden", "access denied", "security check"]

class LeadCrawler:
    """Multi-domain crawler that deeply scans websites for lead contact details."""

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

        return {
            "domain": domain,
            "company_name": company_name,
            "url": url,
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

    def crawl_batch(self, urls: List[str], progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[Dict[str, Any]]:
        results = []
        total = len(urls)
        for i, u in enumerate(urls, 1):
            if not u.strip():
                continue
            if progress_callback:
                progress_callback(i, total, u)
            lead = self.crawl_domain(u.strip())
            results.append(lead)
        return results
