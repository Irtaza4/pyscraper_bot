import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Dict, List, Set, Any, Optional

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
PHONE_REGEX = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}'

IGNORED_EMAIL_DOMAINS = {
    'example.com', 'domain.com', 'email.com', 'sentry.io', 'wixpress.com',
    'schema.org', 'w3.org', 'bootstrap.com', 'googleapis.com'
}

IGNORED_EMAIL_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js'
}

SOCIAL_DOMAINS = {
    'linkedin.com': 'LinkedIn',
    'twitter.com': 'Twitter',
    'x.com': 'Twitter/X',
    'facebook.com': 'Facebook',
    'instagram.com': 'Instagram',
    'github.com': 'GitHub',
    'youtube.com': 'YouTube',
}

CONTACT_PAGE_KEYWORDS = ['contact', 'about', 'team', 'leadership', 'founders', 'connect', 'reach', 'get-in-touch']
DECISION_MAKER_KEYWORDS = [r'CEO', r'Founder', r'Co-Founder', r'Owner', r'Managing Director', r'President', r'Chief Executive']

class ContactExtractor:
    """Extracts contact info, decision makers, social profiles, metadata, and subpages from HTML."""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        email_lower = email.lower().strip()
        if any(email_lower.endswith(ext) for ext in IGNORED_EMAIL_EXTENSIONS):
            return False
        domain = email_lower.split('@')[-1] if '@' in email_lower else ''
        if domain in IGNORED_EMAIL_DOMAINS:
            return False
        if len(email) < 5 or len(email) > 80:
            return False
        return True

    @classmethod
    def extract_decision_maker(cls, soup: BeautifulSoup) -> Dict[str, str]:
        """Extracts decision-maker name & role from team/about sections."""
        role_found = "Founder & CEO"
        name_found = ""

        # Search for headings or paragraphs mentioning CEO / Founder
        for pattern in DECISION_MAKER_KEYWORDS:
            tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'div', 'span'], text=re.compile(pattern, re.IGNORECASE))
            for tag in tags:
                text = tag.get_text().strip()
                if len(text) < 100:
                    # Look for names in text or sibling tags
                    words = text.split()
                    for i, w in enumerate(words):
                        if any(re.search(pattern, w, re.IGNORECASE) for pattern in DECISION_MAKER_KEYWORDS):
                            role_found = w
                            # Check neighboring words for name
                            possible_name = " ".join([w for w in words if w[0].isupper() and len(w) > 2][:2])
                            if possible_name and possible_name.lower() not in ["ceo", "founder", "about", "our"]:
                                name_found = possible_name
                                break
                if name_found:
                    break
            if name_found:
                break

        return {"name": name_found, "role": role_found}

    @classmethod
    def extract_from_html(cls, html_content: str, base_url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, 'lxml' if 'lxml' in html_content else 'html.parser')

        # 1. Page Title & Meta Description
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_desc = ""
        meta_desc_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc_tag and meta_desc_tag.get('content'):
            meta_desc = meta_desc_tag['content'].strip()

        # 2. Extract Emails
        emails: Set[str] = set()

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            if href.lower().startswith('mailto:'):
                raw_email = href.split('mailto:')[-1].split('?')[0].strip()
                if cls.is_valid_email(raw_email):
                    emails.add(raw_email)

        raw_text = soup.get_text(separator=' ')
        found_emails = re.findall(EMAIL_REGEX, raw_text)
        for em in found_emails:
            if cls.is_valid_email(em):
                emails.add(em)

        # 3. Extract Phone Numbers
        phones: Set[str] = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            if href.lower().startswith('tel:'):
                phone_num = href.split('tel:')[-1].split('?')[0].strip()
                if len(phone_num) >= 7:
                    phones.add(phone_num)

        phone_matches = re.findall(PHONE_REGEX, raw_text)
        for ph in phone_matches:
            cleaned_ph = ph.strip()
            if len(re.sub(r'\D', '', cleaned_ph)) >= 8:
                phones.add(cleaned_ph)

        # 4. Extract Social Links & Subpages
        socials: Dict[str, str] = {}
        contact_subpages: Set[str] = set()
        parsed_base = urlparse(base_url)

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            full_url = urljoin(base_url, href)
            href_lower = href.lower()

            for domain, platform_name in SOCIAL_DOMAINS.items():
                if domain in href_lower:
                    socials[platform_name] = full_url

            if urlparse(full_url).netloc == parsed_base.netloc:
                path = urlparse(full_url).path.lower()
                if any(kw in path for kw in CONTACT_PAGE_KEYWORDS):
                    contact_subpages.add(full_url)

        # 5. Extract Decision Maker Info
        dm_info = cls.extract_decision_maker(soup)

        # 6. Extract Tech & App Store Indicators
        has_app_store = bool(soup.find(href=re.compile(r'apps\.apple\.com|play\.google\.com')))
        has_mobile_meta = bool(soup.find('meta', attrs={'name': 'viewport'}))

        return {
            "url": base_url,
            "title": title,
            "meta_description": meta_desc,
            "emails": list(emails),
            "phones": list(phones)[:3],
            "socials": socials,
            "contact_subpages": list(contact_subpages)[:5],
            "decision_maker_name": dm_info["name"],
            "decision_maker_role": dm_info["role"],
            "has_app_store": has_app_store,
            "has_mobile_meta": has_mobile_meta,
        }
