import re
import urllib.parse
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from .fetcher import HTTPFetcher

EXCLUDED_DOMAINS = {
    "google.com", "bing.com", "yahoo.com", "duckduckgo.com", "wikipedia.org",
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com", "youtube.com",
    "yelp.com", "yellowpages.com", "tripadvisor.com", "amazon.com", "ebay.com",
    "reddit.com", "pinterest.com", "glassdoor.com", "medium.com", "github.com",
    "apple.com", "play.google.com", "apps.apple.com", "trustpilot.com"
}

INDUSTRY_PRESETS = {
    "🚚 Logistics & Freight": "logistics company transport cargo website",
    "🚖 Taxi & Car Rental": "taxi service car rental company website",
    "🛍️ E-Commerce & Retail": "online store boutique retail website",
    "🏋️ Fitness & Gyms": "fitness center gym studio website",
    "🏠 Real Estate Agencies": "real estate agency property management website",
    "🍔 Restaurants & Food": "restaurant food delivery ordering website",
    "🩺 Clinics & Healthcare": "medical clinic wellness center website",
    "🧹 Cleaning & Home Services": "home cleaning repair services website"
}

class LeadFinder:
    """Automated Business URL discovery engine supporting multi-page search results (50+ leads)."""

    def __init__(self, fetcher: Optional[HTTPFetcher] = None):
        self.fetcher = fetcher or HTTPFetcher()

    def search_businesses(self, query: str, max_results: int = 50) -> List[Dict[str, str]]:
        """Search DuckDuckGo HTML with pagination to gather 40, 50, 100+ business leads."""
        discovered: List[Dict[str, str]] = []
        seen_domains = set()

        # Build search query variations if high count requested
        query_variations = [query]
        if max_results > 15:
            query_variations.append(f"{query} services")
            query_variations.append(f"top {query}")
            query_variations.append(f"local {query}")

        for q_var in query_variations:
            if len(discovered) >= max_results:
                break

            # Paginate through search result offsets (0, 30, 60, 90)
            offsets = [0, 30, 60] if max_results > 20 else [0]
            for offset in offsets:
                if len(discovered) >= max_results:
                    break

                encoded_query = urllib.parse.quote_plus(q_var)
                if offset == 0:
                    search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
                else:
                    search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}&s={offset}"

                html = self.fetcher.fetch(search_url)
                if not html:
                    continue

                soup = BeautifulSoup(html, "html.parser")

                for a_tag in soup.find_all("a", class_=re.compile(r"result__url|result__title|result__a")):
                    href = a_tag.get("href", "")
                    if "/l/?" in href and "uddg=" in href:
                        parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if "uddg" in parsed_qs:
                            actual_url = parsed_qs["uddg"][0]
                        else:
                            continue
                    elif href.startswith("http"):
                        actual_url = href
                    else:
                        continue

                    parsed = urllib.parse.urlparse(actual_url)
                    domain = parsed.netloc.lower().replace("www.", "")

                    if not domain or domain in EXCLUDED_DOMAINS or any(ex == domain for ex in EXCLUDED_DOMAINS):
                        continue

                    if domain in seen_domains:
                        continue

                    seen_domains.add(domain)
                    title = a_tag.get_text().strip()

                    discovered.append({
                        "company_name": domain.split(".")[0].capitalize(),
                        "url": f"{parsed.scheme}://{parsed.netloc}",
                        "domain": domain,
                        "snippet": title
                    })

                    if len(discovered) >= max_results:
                        break

        return discovered[:max_results]

    def auto_find_and_crawl(self, query: str, max_results: int = 30, crawler = None) -> List[Dict[str, Any]]:
        """Find business URLs by query and run deep lead contact extraction."""
        targets = self.search_businesses(query, max_results=max_results)
        if not targets:
            return []

        urls = [t["url"] for t in targets]
        if crawler is None:
            from .crawler import LeadCrawler
            crawler = LeadCrawler()

        return crawler.crawl_batch(urls)
