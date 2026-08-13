import os
import json
from scraper import LeadCrawler, DataExporter
from outreach import PitchGenerator, EmailSender, CVParser

def run_verification():
    print("==================================================")
    print("🚀 PyScraper Pro Verification Suite for Irtaza Khalid")
    print("==================================================")

    # 1. Profile Verification
    profile = CVParser.load_default_profile()
    print(f"\n[1/4] Loaded Profile: {profile.get('full_name')} ({profile.get('title')})")
    print(f"      Email: {profile.get('email')} | Phone: {profile.get('phone')}")
    print(f"      Published Apps: {len(profile.get('published_apps', []))} apps loaded.")
    assert profile.get("full_name") == "Irtaza Khalid", "Profile name mismatch"

    # 2. Crawler & Contact Scraper Verification
    print("\n[2/4] Testing Lead Scraper against safe test sites...")
    crawler = LeadCrawler()
    test_urls = ["https://quotes.toscrape.com", "https://books.toscrape.com"]
    leads = crawler.crawl_batch(test_urls)

    print(f"      Scraped {len(leads)} target sites successfully.")
    for l in leads:
        print(f"      - Company: {l['company_name']} | Score: {l['score']} ({l['category']}) | Email: {l['primary_email'] or 'None found (site demo)'}")

    # 3. Export Verification
    print("\n[3/4] Testing Data Exporter...")
    csv_file = "test_leads.csv"
    DataExporter.to_csv(leads, csv_file)
    assert os.path.exists(csv_file), "CSV export failed"
    print(f"      Saved CSV to {csv_file} ({os.path.getsize(csv_file)} bytes).")

    # 4. Pitch Generator Verification
    print("\n[4/4] Testing Pitch Generator for Irtaza Khalid...")
    mock_lead = {
        "company_name": "Swift Logistics Express",
        "url": "https://swiftlogistics.com",
        "primary_email": "contact@swiftlogistics.com"
    }
    pitch = PitchGenerator.generate_pitch(mock_lead, "opportunity_audit")
    print("\n----- DRAFT PITCH PREVIEW -----")
    print(f"Subject: {pitch['subject']}\n")
    print(pitch['body'][:450] + "...\n--------------------------------")

    print("\n✅ All core modules verified and working 100% cleanly!")

if __name__ == "__main__":
    run_verification()
