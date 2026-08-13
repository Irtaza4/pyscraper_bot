import os
import json
import time
import pandas as pd
import streamlit as st

from scraper import LeadCrawler, DataExporter, LeadFinder, INDUSTRY_PRESETS
from outreach import CVParser, PitchGenerator, EmailSender

# Page Configuration
st.set_page_config(
    page_title="PyScraper Pro - Lead Scraper & Pitch Bot",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #4F46E5;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6B7280;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #1E1E2E;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #6366F1;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #A6ADC8;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "scraped_leads" not in st.session_state:
    st.session_state["scraped_leads"] = []
if "developer_profile" not in st.session_state:
    st.session_state["developer_profile"] = CVParser.load_default_profile()

profile = st.session_state["developer_profile"]
dev_name = profile.get("full_name", "Irtaza Khalid")
portfolio_url = profile.get("portfolio", "https://irtaza-dev.netlify.app")

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/flutter.png", width=64)
    st.title("PyScraper Pro")
    st.caption("Lead Scraper & Automated Email Outreach")

    st.divider()

    st.markdown("### 👨‍💻 Developer Profile")
    st.markdown(f"**Name:** {dev_name}")
    st.markdown(f"**Role:** {profile.get('title', 'Flutter Developer')}")
    st.markdown(f"**Email:** `{profile.get('email', 'Irtazakhalidll@gmail.com')}`")
    st.markdown(f"**Phone:** `{profile.get('phone', '+92 308 4221084')}`")
    st.markdown(f"🌐 [Portfolio Website]({portfolio_url})")

    st.divider()
    st.markdown("### 📱 Published Apps")
    for app in profile.get("published_apps", [])[:3]:
        st.markdown(f"• **{app['name']}** - *{app['tagline']}*")

# Main Header
st.markdown('<div class="main-header">🚀 PyScraper Pro - Lead Scraper & Outreach Bot</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">Find businesses needing App Development services, generate personalized pitches, and send cold emails directly as <b>{dev_name}</b>.</div>', unsafe_allow_html=True)

# Tabs Navigation
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 1. Lead Finder & Scraper",
    "✍️ 2. Pitch Generator",
    "📧 3. Email Outreach Campaign",
    "📊 4. Campaign Analytics & Logs"
])

# ==================== TAB 1: LEAD FINDER & SCRAPER ====================
with tab1:
    st.header("🔍 Lead Finder & Contact Scraper")
    st.write("Auto-discover target companies by industry/location OR enter custom website URLs to extract emails, phone numbers, and score app opportunity.")

    scrape_mode = st.radio(
        "Choose Lead Discovery Method:",
        options=["🎯 Auto-Discover Businesses by Search/Industry", "📝 Manual URL List Input"],
        horizontal=True
    )

    if scrape_mode == "🎯 Auto-Discover Businesses by Search/Industry":
        c1, c2, c3 = st.columns([1.5, 1, 1])

        with c1:
            selected_preset_name = st.selectbox(
                "Target Industry Category:",
                options=list(INDUSTRY_PRESETS.keys())
            )
            default_query = INDUSTRY_PRESETS[selected_preset_name]

        with c2:
            country_location = st.text_input("Target Location/Country:", value="USA", help="e.g. USA, UK, UAE, Pakistan, Canada")

        with c3:
            max_leads = st.slider("Max Leads to Find", min_value=5, max_value=100, step=5, value=30, help="Up to 100 leads per batch!")

        custom_search_kw = st.text_input(
            "Custom Search Keywords (Optional):",
            value=f"{default_query} in {country_location}",
            help="Full search query used to discover company websites."
        )

        start_auto_search = st.button("🚀 Auto-Discover & Scrape Business Leads", type="primary", use_container_width=True)

        if start_auto_search:
            status_box = st.empty()
            progress_bar = st.progress(0)

            status_box.info(f"🔎 Searching web across multi-page results for '{custom_search_kw}' (Target: {max_leads} leads)...")
            finder = LeadFinder()
            discovered = finder.search_businesses(custom_search_kw, max_results=max_leads)

            if not discovered:
                st.warning("No business websites found for this query. Try adjusting location or keywords.")
            else:
                status_box.success(f"Found {len(discovered)} target business websites! Starting deep contact extraction...")
                urls_to_crawl = [d["url"] for d in discovered]

                crawler = LeadCrawler()
                def auto_progress_cb(current, total, url):
                    progress_bar.progress(current / total)
                    status_box.text(f"Scraping ({current}/{total}): {url}")

                results = crawler.crawl_batch(urls_to_crawl, progress_callback=auto_progress_cb)
                st.session_state["scraped_leads"] = results
                status_box.text(f"✅ Scraping completed! Extracted {len(results)} leads.")
                st.success(f"Successfully scraped {len(results)} business targets!")

    else:
        col_input, col_config = st.columns([2, 1])

        with col_input:
            default_urls = "https://quotes.toscrape.com\nhttps://books.toscrape.com"
            urls_input = st.text_area(
                "Target URLs (one per line):",
                value=default_urls,
                height=160,
                help="Paste website homepages or directory links to scan."
            )

        with col_config:
            max_subpages = st.slider("Scan Subpages (Contact/About)", 1, 5, 3)
            delay_req = st.slider("Request Delay (sec)", 0.5, 3.0, 1.0)
            start_scrape = st.button("🚀 Start Lead Scraping", type="primary", use_container_width=True)

        if start_scrape:
            url_list = [u.strip() for u in urls_input.split("\n") if u.strip()]
            if not url_list:
                st.warning("Please enter at least one target URL.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()

                crawler = LeadCrawler()
                crawler.fetcher.delay_between_requests = delay_req

                def progress_cb(current, total, url):
                    progress_bar.progress(current / total)
                    status_text.text(f"Scraping ({current}/{total}): {url}")

                results = crawler.crawl_batch(url_list, progress_callback=progress_cb)
                st.session_state["scraped_leads"] = results

                status_text.text(f"✅ Scraping completed! Extracted {len(results)} leads.")
                st.success(f"Successfully scraped {len(results)} business targets!")

    # Display Scraped Data
    if st.session_state["scraped_leads"]:
        leads_df = pd.DataFrame(st.session_state["scraped_leads"])

        st.subheader(f"Extracted Business Leads ({len(leads_df)})")

        # Metrics overview
        m1, m2, m3, m4 = st.columns(4)
        total_leads = len(leads_df)
        with_email = len(leads_df[leads_df["primary_email"].astype(bool)]) if "primary_email" in leads_df.columns else 0
        hot_leads = len(leads_df[leads_df["category"].str.contains("Hot", na=False)]) if "category" in leads_df.columns else 0
        no_apps = len(leads_df[leads_df["has_app"] == False]) if "has_app" in leads_df.columns else 0

        m1.metric("Total Websites", total_leads)
        m2.metric("Valid Emails Found", with_email)
        m3.metric("Hot Leads 🔥", hot_leads)
        m4.metric("No Existing Mobile App", no_apps)

        cols_to_show = [c for c in ["company_name", "primary_email", "primary_phone", "category", "score", "url", "reasons"] if c in leads_df.columns]
        st.dataframe(leads_df[cols_to_show], use_container_width=True)

        # Export Buttons
        c1, c2, c3 = st.columns(3)
        csv_data = leads_df.to_csv(index=False).encode('utf-8')
        json_data = leads_df.to_json(orient="records", indent=2)

        c1.download_button("📥 Download CSV Lead Sheet", csv_data, "scraped_leads.csv", "text/csv", use_container_width=True)
        c2.download_button("📥 Download JSON Data", json_data, "scraped_leads.json", "application/json", use_container_width=True)


# ==================== TAB 2: PITCH GENERATOR ====================
with tab2:
    st.header("✍️ Personalized Pitch Generator")
    st.write(f"Draft customized cold email pitches positioning **{dev_name}** as a sole Flutter Developer.")
    st.info(f"🌐 Portfolio Link included in email footer: **{portfolio_url}**")

    template_options = PitchGenerator.list_template_keys()
    selected_template_key = st.selectbox(
        "Choose Email Pitch Strategy:",
        options=[t["key"] for t in template_options],
        format_func=lambda k: next(t["name"] for t in template_options if t["key"] == k)
    )

    if st.session_state["scraped_leads"]:
        leads_with_email = [l for l in st.session_state["scraped_leads"] if l.get("primary_email")]
        if leads_with_email:
            selected_lead_company = st.selectbox(
                "Preview Pitch for Lead:",
                options=[l["company_name"] for l in leads_with_email]
            )
            target_lead = next(l for l in leads_with_email if l["company_name"] == selected_lead_company)

            pitch = PitchGenerator.generate_pitch(target_lead, selected_template_key)

            st.subheader("Subject Line:")
            st.code(pitch["subject"], language="text")

            st.subheader("Email Body Preview:")
            st.text_area("Email Content:", value=pitch["body"], height=380)
        else:
            st.info("No leads with valid emails found in your current scraped list. Scrape or discover new leads in Tab 1.")
    else:
        # Sample Preview
        sample_lead = {"company_name": "Acme Retail Services", "url": "https://acmeretail.com", "primary_email": "contact@acmeretail.com"}
        pitch = PitchGenerator.generate_pitch(sample_lead, selected_template_key)
        st.subheader("Sample Subject Line:")
        st.code(pitch["subject"], language="text")
        st.subheader("Sample Email Body:")
        st.text_area("Sample Content:", value=pitch["body"], height=380)


# ==================== TAB 3: EMAIL OUTREACH CAMPAIGN ====================
with tab3:
    st.header("📧 Automated Email Outreach Campaign")
    st.write(f"Send cold emails directly from your Gmail account (`{profile.get('email')}`) via Gmail SMTP.")

    col_smtp, col_campaign = st.columns([1, 1])

    with col_smtp:
        st.subheader("1. SMTP Email Credentials")
        sender_email = st.text_input("Sender Email:", value=profile.get("email", "Irtazakhalidll@gmail.com"))
        gmail_app_password = st.text_input(
            "Gmail App Password:",
            type="password",
            help="Generate a 16-character App Password from your Google Account -> Security -> App Passwords."
        )

        st.caption("🔒 Credentials are only stored temporarily in your local session.")

        if st.button("🔌 Test SMTP Connection"):
            if not gmail_app_password:
                st.error("Please enter your Gmail App Password.")
            else:
                sender = EmailSender(sender_email=sender_email, sender_password=gmail_app_password)
                res = sender.test_connection()
                if res["success"]:
                    st.success(res["message"])
                else:
                    st.error(res["message"])

        st.divider()
        st.subheader("2. Attachment & Test Dispatch")
        uploaded_cv = st.file_uploader("Upload CV Attachment (PDF):", type=["pdf"])

        test_to_email = st.text_input("Send Test Email To:", value=sender_email)
        if st.button("🧪 Send Test Email to Myself"):
            if not gmail_app_password:
                st.error("Please enter your Gmail App Password first.")
            else:
                sender = EmailSender(sender_email=sender_email, sender_password=gmail_app_password)
                sample_lead = {"company_name": "Test Company", "url": "https://example.com", "primary_email": test_to_email}
                pitch = PitchGenerator.generate_pitch(sample_lead, selected_template_key)

                temp_cv_path = None
                if uploaded_cv:
                    temp_cv_path = os.path.join("/tmp", uploaded_cv.name)
                    with open(temp_cv_path, "wb") as f:
                        f.write(uploaded_cv.getbuffer())

                res = sender.send_single_email(test_to_email, pitch["subject"], pitch["body"], temp_cv_path)
                if res["success"]:
                    st.success(f"Test email sent successfully to {test_to_email}!")
                else:
                    st.error(res["message"])

    with col_campaign:
        st.subheader("3. Launch Batch Outreach Campaign")

        leads_to_mail = [l for l in st.session_state["scraped_leads"] if l.get("primary_email")]
        st.info(f"Target Leads Ready for Outreach: **{len(leads_to_mail)}**")

        delay_between_mails = st.slider("Delay Between Emails (Seconds):", 10, 120, 30, help="Prevents spam rate limits.")

        launch_campaign = st.button("🚀 Launch Batch Cold Outreach", type="primary", use_container_width=True)

        if launch_campaign:
            if not gmail_app_password:
                st.error("Please provide your Gmail App Password.")
            elif not leads_to_mail:
                st.error("No valid leads with emails available. Please discover or scrape leads in Tab 1 first.")
            else:
                sender = EmailSender(sender_email=sender_email, sender_password=gmail_app_password)

                temp_cv_path = None
                if uploaded_cv:
                    temp_cv_path = os.path.join("/tmp", uploaded_cv.name)
                    with open(temp_cv_path, "wb") as f:
                        f.write(uploaded_cv.getbuffer())

                campaign_items = []
                for l in leads_to_mail:
                    p = PitchGenerator.generate_pitch(l, selected_template_key)
                    campaign_items.append(p)

                camp_progress = st.progress(0)
                camp_status = st.empty()

                def camp_cb(curr, total, email, success):
                    camp_progress.progress(curr / total)
                    status_icon = "✅" if success else "❌"
                    camp_status.text(f"({curr}/{total}) {status_icon} Dispatched to {email}")

                results = sender.send_campaign(campaign_items, delay_seconds=delay_between_mails, cv_attachment_path=temp_cv_path, progress_callback=camp_cb)
                st.success(f"Campaign completed! Dispatched emails to {len(results)} leads.")


# ==================== TAB 4: ANALYTICS & LOGS ====================
with tab4:
    st.header("📊 Outreach Campaign History & Logs")
    logs_df = EmailSender.get_logs()

    if not logs_df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Emails Dispatched", len(logs_df))
        c2.metric("Successful Deliveries", len(logs_df[logs_df["status"] == "Success"]))
        c3.metric("Failed Deliveries", len(logs_df[logs_df["status"] != "Success"]))

        st.subheader("Sent Mail Log Table")
        st.dataframe(logs_df, use_container_width=True)
    else:
        st.info("No outreach emails sent yet. Launch a campaign in Tab 3 to view delivery history.")
