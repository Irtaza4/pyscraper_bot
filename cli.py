import argparse
import sys
import pandas as pd
from scraper import LeadCrawler, DataExporter
from outreach import EmailSender, PitchGenerator

def main():
    parser = argparse.ArgumentParser(description="PyScraper Pro - Sole Developer Lead Scraper & Cold Email Bot")
    parser.add_argument("--url", help="Single target URL to scrape")
    parser.add_argument("--file", help="Path to text file containing target URLs (one per line)")
    parser.add_argument("--export", choices=["csv", "json", "excel"], default="csv", help="Export format")
    parser.add_argument("--out", default="leads_output.csv", help="Output file path")
    parser.add_argument("--subpages", type=int, default=3, help="Max contact subpages to scan per site")

    args = parser.parse_args()

    urls = []
    if args.url:
        urls.append(args.url)
    elif args.file:
        try:
            with open(args.file, "r") as f:
                urls = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"Error reading file {args.file}: {e}")
            sys.exit(1)
    else:
        print("Please provide a target URL with --url or a URL file with --file")
        parser.print_help()
        sys.exit(1)

    print(f"🚀 PyScraper Pro starting lead extraction for {len(urls)} target websites...")

    crawler = LeadCrawler()
    results = crawler.crawl_batch(urls, progress_callback=lambda cur, tot, u: print(f"[{cur}/{tot}] Crawling {u}..."))

    if args.export == "csv":
        DataExporter.to_csv(results, args.out)
    elif args.export == "json":
        DataExporter.to_json(results, args.out)
    elif args.export == "excel":
        DataExporter.to_excel(results, args.out)

    print(f"✅ Scraping completed! {len(results)} lead records saved to {args.out}")

if __name__ == "__main__":
    main()
