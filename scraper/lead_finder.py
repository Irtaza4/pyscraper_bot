import re
import base64
import urllib.parse
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
# pyrefly: ignore [missing-import]
import httpx
from bs4 import BeautifulSoup
from .fetcher import HTTPFetcher

EXCLUDED_DOMAINS = {
    # Search engines & major tech portals
    "google.com", "bing.com", "yahoo.com", "duckduckgo.com", "baidu.com", "yandex.com",
    "github.com", "gitlab.com", "apple.com", "microsoft.com", "play.google.com", "apps.apple.com",
    # Dictionaries, Encyclopedias & Info / Knowledge Bases
    "wikipedia.org", "wikimedia.org", "wiktionary.org", "cambridge.org", "dictionary.com",
    "merriam-webster.com", "britannica.com", "wikihow.com", "investopedia.com", "answers.com",
    "quora.com", "medium.com", "slideshare.net", "stackoverflow.com", "stackexchange.com",
    "geeksforgeeks.org", "w3schools.com", "tutorialspoint.com", "coursera.org", "udemy.com",
    # Social & Media Networks
    "facebook.com", "twitter.com", "x.com", "instagram.com", "linkedin.com", "youtube.com",
    "tiktok.com", "reddit.com", "pinterest.com", "tumblr.com", "imdb.com",
    # Aggregators, Listicles, Real Estate Platforms, Review Sites & Job Portals
    "yelp.com", "yellowpages.com", "tripadvisor.com", "glassdoor.com", "trustpilot.com",
    "clutch.co", "g2.com", "capterra.com", "topcv.vn", "indeed.com", "ziprecruiter.com",
    "monster.com", "crunchbase.com", "bloomberg.com", "forbes.com", "businessinsider.com",
    "reuters.com", "nytimes.com", "cnn.com", "bbc.com", "wsj.com", "booking.com", "expedia.com",
    "theguardian.com", "washingtonpost.com", "huffpost.com", "aeroleads.com", "jobstreet.com",
    "zillow.com", "realtor.com", "trulia.com", "redfin.com", "angi.com", "homeadvisor.com",
    "thumbtack.com", "starofservice.com", "apollo.io", "lusha.com", "zoominfo.com",
    "99acres.com", "magicbricks.com", "housing.com", "commonfloor.com", "squareyards.com", "nobroker.in",
    # General E-commerce Giants
    "amazon.com", "ebay.com", "walmart.com", "target.com", "aliexpress.com"
}

EXCLUDED_TLDS = (".edu", ".gov", ".mil", ".ac.uk", ".edu.vn", ".gov.vn", ".edu.au", ".edu.sg")

EXCLUDED_DOMAIN_KEYWORDS = (
    "dictionary", "wiktionary", "translation", "thesaurus", "vocab", "grammar",
    "meaning", "wikipedia", "encyclopedia", "tu-dien", "lingo", "tratu", "soha",
    "dict", "zim", "lingoland", "tutorial", "academic", "university", "college"
)

EXCLUDED_PATH_KEYWORDS = (
    "/wiki/", "/definition/", "/dict/", "/dictionary/", "/meaning/",
    "/article/", "/articles/", "/news/", "/blog/", "/blogs/", "/tag/",
    "/category/", "/forum/", "/thread/", "/search", "/find/", "/topics/",
    "/la-gi", "/what-is", "/guide/", "/learn/", "/course/", "/glossary/", "/history/",
    "/nghia-la-gi", "/tat-tan-tat"
)

COUNTRY_OPTIONS = {
    "🇺🇸 United States": "United States",
    "🇬🇧 United Kingdom": "United Kingdom",
    "🇦🇪 United Arab Emirates (Dubai)": "UAE Dubai",
    "🇨🇦 Canada": "Canada",
    "🇦🇺 Australia": "Australia",
    "🇩🇪 Germany": "Germany",
    "🇸🇦 Saudi Arabia": "Saudi Arabia",
    "🇵🇰 Pakistan": "Pakistan",
    "🌍 Global (All Countries)": "Global"
}

ROLE_OPTIONS = {
    "👔 CEOs / Founders / Business Owners": "CEO Founder Owner",
    "👨‍💼 Managing Directors / Executives": "Managing Director Executive",
    "🌐 General Business Websites": "company website"
}

INDUSTRY_PRESETS = {
    "🚚 Logistics & Freight": "freight logistics provider",
    "🚖 Taxi & Car Rental": "taxi cab car rental service",
    "🛍️ E-Commerce & Retail": "online store boutique shop",
    "🏋️ Fitness & Gyms": "fitness gym studio wellness",
    "🏠 Real Estate Agencies": "real estate brokerage property",
    "🍔 Restaurants & Food": "restaurant catering dining",
    "🩺 Clinics & Healthcare": "medical clinic dental practice",
    "🧹 Cleaning & Home Services": "cleaning services maid residential"
}

class LeadFinder:
    """Automated Business & Decision-Maker discovery engine with multi-engine web search."""

    def __init__(self, fetcher: Optional[HTTPFetcher] = None):
        self.fetcher = fetcher or HTTPFetcher()

    @staticmethod
    def get_niche_tokens(query: str) -> set:
        query_lower = query.lower()
        tokens = set()

        if 'real estate' in query_lower or 'property' in query_lower:
            tokens.update(['real estate', 'realty', 'realtor', 'property', 'brokerage', 'housing', 'estate agency', 'realestate'])
        elif 'taxi' in query_lower or 'car rental' in query_lower:
            tokens.update(['taxi', 'cab', 'car rental', 'limo', 'driver', 'ride', 'fleet', 'transport', 'transfer'])
        elif 'logistics' in query_lower or 'freight' in query_lower or 'shipping' in query_lower:
            tokens.update(['logistics', 'freight', 'shipping', 'trucking', 'supply chain', '3pl', 'cargo', 'warehouse', 'courier'])
        elif 'fitness' in query_lower or 'gym' in query_lower:
            tokens.update(['fitness', 'gym', 'workout', 'training studio', 'crossfit', 'wellness', 'health club'])
        elif 'clean' in query_lower or 'maid' in query_lower:
            tokens.update(['cleaning', 'maid', 'janitorial', 'housekeeping', 'carpet clean', 'residential clean', 'commercial clean'])
        elif 'clinic' in query_lower or 'dental' in query_lower or 'health' in query_lower:
            tokens.update(['clinic', 'dental', 'doctor', 'medical', 'healthcare', 'practice', 'patient', 'surgery'])
        elif 'restaurant' in query_lower or 'food' in query_lower:
            tokens.update(['restaurant', 'catering', 'dining', 'bistro', 'food delivery', 'eatery'])
        elif 'store' in query_lower or 'retail' in query_lower or 'ecommerce' in query_lower or 'shop' in query_lower:
            tokens.update(['store', 'boutique', 'shop', 'retail', 'e-commerce', 'apparel', 'fashion'])
        else:
            STOP_WORDS = {'company', 'companies', 'website', 'service', 'services', 'best', 'top', 'local', 'real', 'good', 'near', 'online', 'official', 'site', 'list', 'find', 'get'}
            words = re.findall(r'\b[a-z]{4,}\b', query_lower)
            tokens = {w for w in words if w not in STOP_WORDS}

        return tokens

    @staticmethod
    def detect_business_age(text: str) -> str:
        text_lower = text.lower()

        # 1. New / Fresh Business Indicators
        new_patterns = [
            r'\b(?:est\.?|established|founded)\s*(?:in\s*)?(?:202[4-6])\b',
            r'\b(?:now open|grand opening|newly opened|new location|just launched|launched in 202[4-6])\b',
            r'\b202[4-6]\s*(?:new|opening|launch)\b'
        ]
        if any(re.search(p, text_lower) for p in new_patterns):
            return "🆕 Newly Launched"

        # 2. Established Business Indicators
        established_patterns = [
            r'\b(?:est\.?|established|founded|serving since|since)\s*(?:in\s*)?(?:19\d{2}|200\d|201\d|202[0-3])\b',
            r'\b(?:over|\d+\+?)\s*(?:years|decades)\s*(?:of experience|in business|serving)\b',
            r'\b(?:family[- ]owned since|serving the community since)\b'
        ]
        if any(re.search(p, text_lower) for p in established_patterns):
            return "🏛️ Established"

        return "⭐ Active Business"

    @classmethod
    def is_niche_relevant(cls, text: str, domain: str, tokens: set) -> bool:
        if not tokens:
            return True
        full_str = f"{text} {domain}".lower()
        return any(token in full_str for token in tokens)

    @staticmethod
    def is_excluded_target(url: str, domain: str) -> bool:
        domain = domain.lower()
        if any(domain.endswith(tld) for tld in EXCLUDED_TLDS):
            return True

        if any(kw in domain for kw in EXCLUDED_DOMAIN_KEYWORDS):
            return True

        for ex in EXCLUDED_DOMAINS:
            if domain == ex or domain.endswith("." + ex):
                return True

        path = urllib.parse.urlparse(url).path.lower()
        if any(kw in path for kw in EXCLUDED_PATH_KEYWORDS):
            return True

        return False

    @staticmethod
    def decode_bing_url(bing_href: str) -> Optional[str]:
        try:
            if "u=" in bing_href:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(bing_href).query)
                if "u" in qs:
                    raw_u = qs["u"][0]
                    if raw_u.startswith("a1"):
                        b64_str = raw_u[2:]
                        b64_str += '=' * (-len(b64_str) % 4)
                        return base64.b64decode(b64_str).decode('utf-8', errors='ignore')
        except Exception:
            pass
        return None

    def search_bing(self, search_query: str, first_offset: int = 1, niche_tokens: Optional[set] = None) -> List[Dict[str, str]]:
        encoded = urllib.parse.quote_plus(search_query)
        url = f"https://www.bing.com/search?q={encoded}&setlang=en-US&cc=US&mkt=en-US&first={first_offset}"

        try:
            headers = self.fetcher.get_random_headers()
            headers["Accept-Language"] = "en-US,en;q=0.9"
            with httpx.Client(timeout=6.0, follow_redirects=True, verify=False) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code != 200:
                    return []
                html = resp.text
        except Exception:
            return []

        soup = BeautifulSoup(html, "html.parser")
        results = []

        for li in soup.select("li.b_algo"):
            a_tag = li.select_one("h2 a")
            if not a_tag or not a_tag.get("href"):
                continue

            href = a_tag["href"]
            target_url = self.decode_bing_url(href) or href

            if not target_url.startswith("http"):
                continue

            parsed = urllib.parse.urlparse(target_url)
            domain = parsed.netloc.lower().replace("www.", "")

            if not domain or self.is_excluded_target(target_url, domain):
                continue

            title = a_tag.get_text().strip()
            p_tag = li.select_one(".b_caption p")
            snippet_text = p_tag.get_text().strip() if p_tag else ""
            full_text = f"{title} {snippet_text}"

            if niche_tokens and not self.is_niche_relevant(title, domain, niche_tokens):
                continue

            age_category = self.detect_business_age(full_text)

            results.append({
                "company_name": domain.split(".")[0].capitalize(),
                "url": f"{parsed.scheme}://{parsed.netloc}",
                "domain": domain,
                "snippet": title,
                "age_category": age_category
            })

        return results

    def search_businesses(self, query: str, country: str = "United States", role: str = "", max_results: int = 100) -> List[Dict[str, str]]:
        """Search businesses concurrently across Explorium 60,000+ business database and multi-engine web search."""
        discovered: List[Dict[str, str]] = []
        seen_domains = set()

        COUNTRY_ISO_MAP = {
            "United States": "US",
            "United Kingdom": "GB",
            "UAE Dubai": "AE",
            "Canada": "CA",
            "Australia": "AU",
            "Germany": "DE",
            "Saudi Arabia": "SA",
            "Pakistan": "PK",
            "Global": ""
        }

        clean_country = country if country != "Global" else ""
        clean_query = query.replace("website", "").replace("company", "").strip()

        niche_tokens = self.get_niche_tokens(clean_query)

        # 1. Expand Query with Groq AI for country-specific commercial terms
        from .groq_client import GroqClient
        groq = GroqClient()
        ai_terms = groq.expand_niche_search_keywords(clean_query, country)

        # 2. Query Serper.dev Official Google Organic & Google Places API (2,500 Free Searches + Cached)
        from .serper_client import SerperClient
        serper = SerperClient()
        serper_leads = serper.search_google_organic(clean_query, country, max_results=max_results)
        serper_places = serper.search_google_places(clean_query, country, max_results=20)
        
        for lead in serper_leads + serper_places:
            dom = lead["domain"]
            if dom not in seen_domains and not self.is_excluded_target(lead["url"], dom):
                seen_domains.add(dom)
                discovered.append(lead)

        # 2.5 Query RapidAPI Google Search Master
        if len(discovered) < max_results:
            from .google_rapid_client import GoogleRapidClient
            rapid_google = GoogleRapidClient()
            google_leads = rapid_google.search_google_businesses(clean_query, country, max_results=max_results - len(discovered))
            gmaps_leads = rapid_google.search_google_maps_leads(clean_query, location=country, max_results=20)
            
            for lead in google_leads + gmaps_leads:
                dom = lead["domain"]
                if dom not in seen_domains and not self.is_excluded_target(lead["url"], dom):
                    seen_domains.add(dom)
                    discovered.append(lead)

        # 3. Query Explorium Global Database (60,000+ verified businesses)
        if len(discovered) < max_results:
            country_iso = COUNTRY_ISO_MAP.get(country, "")
            primary_kw = list(niche_tokens)[0] if niche_tokens else clean_query.split()[0]
            kw_list = [primary_kw]

            from .explorium_client import ExploriumClient
            explorium = ExploriumClient()
            explorium_leads = explorium.search_businesses_by_country_and_niche(country_iso, kw_list, max_results=max_results - len(discovered))

            for lead in explorium_leads:
                dom = lead["domain"]
                if dom not in seen_domains and not self.is_excluded_target(lead["url"], dom):
                    seen_domains.add(dom)
                    discovered.append(lead)

        # 4. Query Multi-Engine Web Discovery to reach max target
        if len(discovered) < max_results:
            query_variations = [
                f'{clean_query} "contact us" {clean_country}'.strip(),
                f'{clean_query} "now open" OR "grand opening" OR "startup" {clean_country}'.strip(),
                f'{clean_query} "established" OR "founded" {clean_country}'.strip(),
                f'{clean_query} "services" {clean_country}'.strip(),
                f'{clean_query} official site {clean_country}'.strip()
            ]
            for term in ai_terms:
                query_variations.append(f'{term} {clean_country}'.strip())

            if role and "CEO" in role:
                query_variations.append(f'{clean_query} founder OR CEO OR owner {clean_country}'.strip())

            tasks = []
            offsets = [1, 11, 21, 31, 41, 51, 61] if max_results > 30 else [1, 11, 21]
            for q_var in query_variations:
                for off in offsets:
                    tasks.append((q_var, off))

            with ThreadPoolExecutor(max_workers=12) as executor:
                future_to_task = {executor.submit(self.search_bing, q_var, off, niche_tokens): (q_var, off) for q_var, off in tasks}
                for future in as_completed(future_to_task):
                    try:
                        res_items = future.result()
                        for item in res_items:
                            dom = item["domain"]
                            if dom not in seen_domains:
                                seen_domains.add(dom)
                                discovered.append(item)
                                if len(discovered) >= max_results:
                                    break
                    except Exception:
                        pass

                    if len(discovered) >= max_results:
                        break

        return discovered[:max_results]


