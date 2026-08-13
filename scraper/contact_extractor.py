import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Dict, List, Set, Any

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

CONTACT_PAGE_KEYWORDS = ['contact', 'about', 'team', 'connect', 'reach', 'support', 'get-in-touch']

class ContactExtractor:
    """Extracts contact info, social profiles, metadata, and subpages from HTML."""

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

        # mailto links
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            if href.lower().startswith('mailto:'):
                raw_email = href.split('mailto:')[-1].split('?')[0].strip()
                if cls.is_valid_email(raw_email):
                    emails.add(raw_email)

        # Regex search in raw text
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

            # Social links
            for domain, platform_name in SOCIAL_DOMAINS.items():
                if domain in href_lower:
                    socials[platform_name] = full_url

            # Contact subpages on same domain
            if urlparse(full_url).netloc == parsed_base.netloc:
                path = urlparse(full_url).path.lower()
                if any(kw in path for kw in CONTACT_PAGE_KEYWORDS):
                    contact_subpages.add(full_url)

        # 5. Extract Tech & App Store Indicators
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
            "has_app_store": has_app_store,
            "has_mobile_meta": has_mobile_meta,
        }
