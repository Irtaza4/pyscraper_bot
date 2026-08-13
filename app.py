import os
import json
import time
import pandas as pd
import streamlit as st

from scraper import LeadCrawler, DataExporter, LeadFinder, COUNTRY_OPTIONS, ROLE_OPTIONS, INDUSTRY_PRESETS
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
    already_sent_count = len(EmailSender.get_already_sent_emails())
    st.markdown(f"🛡️ **Deduplication Active**: `{already_sent_count}` previous emails logged & blocked from re-sending.")

    st.divider()
    st.markdown("### 📱 Published Apps")
    for app in profile.get("published_apps", [])[:3]:
        st.markdown(f"• **{app['name']}** - *{app['tagline']}*")

# Main Header
st.markdown('<div class="main-header">🚀 PyScraper Pro - Lead Scraper & Outreach Bot</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">Find 100+ business leads & decision makers, generate personalized pitches, and send bulk cold emails directly as <b>{dev_name}</b>.</div>', unsafe_allow_html=True)

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
    st.write("Auto-discover target companies & decision makers (CEOs/Founders) by Country & Industry.")

    scrape_mode = st.radio(
        "Choose Lead Discovery Method:",
        options=["🎯 Auto-Discover Businesses by Country & Industry", "📝 Manual URL List Input"],
        horizontal=True
    )

    if scrape_mode == "🎯 Auto-Discover Businesses by Country & Industry":
        r1, r2, r3, r4, r5 = st.columns([1.4, 1.1, 1.1, 1.1, 1])

        with r1:
            selected_preset_name = st.selectbox(
                "Target Industry Category:",
                options=list(INDUSTRY_PRESETS.keys())
            )
            default_query = INDUSTRY_PRESETS[selected_preset_name]

        with r2:
            selected_country_label = st.selectbox(
                "Target Country:",
                options=list(COUNTRY_OPTIONS.keys()),
                index=0
            )
            target_country = COUNTRY_OPTIONS[selected_country_label]

        with r3:
            selected_role_label = st.selectbox(
                "Target Decision Maker Role:",
                options=list(ROLE_OPTIONS.keys()),
                index=0
            )
            target_role = ROLE_OPTIONS[selected_role_label]

        with r4:
            freshness_label = st.selectbox(
                "Lead Age / Freshness:",
                options=["🌟 All Leads (New & Old)", "🆕 Newly Launched First", "🏛️ Established First"],
                index=0,
                help="Search and prioritize both newly launched businesses and established companies."
            )

        with r5:
            max_leads = st.slider("Max Leads Target", min_value=10, max_value=100, step=10, value=100, help="Discovers up to 100 potential leads per run!")

        custom_search_kw = st.text_input(
            "Custom Search Keywords (Optional):",
            value=f"{default_query}",
            help="Clean search query used to discover company websites."
        )

        start_auto_search = st.button("🚀 Auto-Discover 100 Potential Leads", type="primary", use_container_width=True)

        if start_auto_search:
            status_box = st.empty()
            progress_bar = st.progress(0)

            status_box.info(f"🔎 Searching web for up to {max_leads} potential business targets ({freshness_label}) in {selected_country_label}...")
            finder = LeadFinder()
            discovered = finder.search_businesses(query=custom_search_kw, country=target_country, role=target_role, max_results=max_leads)

            if freshness_label == "🆕 Newly Launched First":
                discovered.sort(key=lambda d: 0 if d.get("age_category") == "🆕 Newly Launched" else 1)
            elif freshness_label == "🏛️ Established First":
                discovered.sort(key=lambda d: 0 if d.get("age_category") == "🏛️ Established" else 1)

            if not discovered:
                st.warning("No business websites found for this query. Try adjusting country or keywords.")
            else:
                status_box.success(f"Found {len(discovered)} potential business websites ({freshness_label})! Starting deep contact & decision-maker extraction...")
                urls_to_crawl = [d["url"] for d in discovered]

                crawler = LeadCrawler()
                def auto_progress_cb(current, total, url):
                    progress_bar.progress(current / total)
                    status_box.text(f"Scraping ({current}/{total}): {url}")

                raw_results = crawler.crawl_batch(urls_to_crawl, progress_callback=auto_progress_cb)

                # Deduplicate against previous campaigns
                deduped_results = EmailSender.filter_already_sent(raw_results)
                st.session_state["scraped_leads"] = deduped_results

                status_box.text(f"✅ Scraping completed! Extracted {len(deduped_results)} new leads ({len(raw_results) - len(deduped_results)} previously emailed leads excluded).")
                st.success(f"Successfully scraped {len(deduped_results)} unique business targets ready for outreach!")

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

                raw_results = crawler.crawl_batch(url_list, progress_callback=progress_cb)
                deduped_results = EmailSender.filter_already_sent(raw_results)
                st.session_state["scraped_leads"] = deduped_results

                status_text.text(f"✅ Scraping completed! Extracted {len(deduped_results)} leads.")
                st.success(f"Successfully scraped {len(deduped_results)} business targets!")

    # Display Scraped Data
    if st.session_state["scraped_leads"]:
        leads_df = pd.DataFrame(st.session_state["scraped_leads"])

        st.subheader(f"Extracted Business Leads ({len(leads_df)})")

        # Metrics overview
        m1, m2, m3, m4, m5 = st.columns(5)
        total_leads = len(leads_df)
        with_email = len(leads_df[leads_df["primary_email"].astype(bool)]) if "primary_email" in leads_df.columns else 0
        explorium_ver = len(leads_df[leads_df["explorium_verified"] == True]) if "explorium_verified" in leads_df.columns else 0
        hot_leads = len(leads_df[leads_df["category"].str.contains("Hot", na=False)]) if "category" in leads_df.columns else 0
        no_apps = len(leads_df[leads_df["has_app"] == False]) if "has_app" in leads_df.columns else 0

        m1.metric("Total Websites", total_leads)
        m2.metric("Valid Emails Found", with_email)
        m3.metric("✨ Explorium Verified", explorium_ver)
        m4.metric("Hot Leads 🔥", hot_leads)
        m5.metric("No Mobile App", no_apps)

        cols_to_show = [c for c in ["company_name", "age_category", "decision_maker_name", "decision_maker_role", "primary_email", "primary_phone", "employee_count", "revenue_range", "funding_total", "category", "score", "url"] if c in leads_df.columns]
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

    pitch_mode = st.radio("Select Pitch Source:", ["🤖 Auto Scraped Leads", "🔗 Manual Website URL Pitching"], horizontal=True)

    if pitch_mode == "🔗 Manual Website URL Pitching":
        manual_url_input = st.text_input("Enter Target Business Website URL:", value="https://www.dubaitaxi.ae", help="Paste any company website URL to audit and pitch.")
        manual_dm_name = st.text_input("Decision Maker / Recipient Name (Optional):", value="Founder / Hiring Manager")
        
        if st.button("⚡ Audit Website & Generate Groq AI Pitch", type="primary", use_container_width=True):
            with st.spinner("🔍 Crawling website & Groq AI (Llama 3.3 70B) auditing digital pain points..."):
                from scraper.crawler import LeadCrawler
                from scraper.groq_client import GroqClient
                crawler = LeadCrawler()
                groq = GroqClient()

                crawl_res = crawler.crawl_domain(manual_url_input)
                scraped_text = crawl_res.get("snippet", "")
                
                audit = groq.audit_manual_url(scraped_text, manual_url_input)
                manual_lead = {
                    "company_name": audit.get("company_name", "Target Business"),
                    "domain": manual_url_input.replace("https://", "").replace("http://", "").split("/")[0],
                    "decision_maker_name": manual_dm_name,
                    "pain_points": audit.get("pain_points", []),
                    "primary_email": crawl_res.get("primary_email", "")
                }
                dev_prof = {"name": dev_name, "role": dev_role, "portfolio": portfolio_url}
                ai_pitch = groq.generate_personalized_cold_email(manual_lead, dev_prof, selected_template_key)
                st.session_state["manual_ai_pitch"] = ai_pitch
                st.session_state["manual_audit"] = audit

        if "manual_audit" in st.session_state:
            aud = st.session_state["manual_audit"]
            st.success(f"✅ Website Audit Complete for **{aud.get('company_name')}**!")
            if aud.get("pain_points"):
                st.markdown("**Detected Digital Gaps & Pitch Angles:**")
                for pp in aud.get("pain_points", []):
                    st.caption(f"• {pp}")

        if "manual_ai_pitch" in st.session_state:
            pitch = st.session_state["manual_ai_pitch"]
            st.subheader("Subject Line:")
            st.code(pitch["subject"], language="text")

            st.subheader("Email Body Preview:")
            st.text_area("Email Content:", value=pitch["body"], height=380)

    else:
        use_groq_ai = st.toggle("⚡ Use Groq AI (Llama 3.3 70B) Hyper-Personalized Pitch Generator", value=True)

        if st.session_state["scraped_leads"]:
            leads_with_email = [l for l in st.session_state["scraped_leads"] if l.get("primary_email")]
            if leads_with_email:
                selected_lead_company = st.selectbox(
                    "Preview Pitch for Lead:",
                    options=[l["company_name"] for l in leads_with_email]
                )
                target_lead = next(l for l in leads_with_email if l["company_name"] == selected_lead_company)

                if use_groq_ai:
                    if st.button("🤖 Generate 1-to-1 Groq AI Personal Pitch", type="primary", use_container_width=True):
                        with st.spinner("⚡ Groq AI (Llama 3.3 70B) is writing customized outreach pitch..."):
                            from scraper.groq_client import GroqClient
                            groq = GroqClient()
                            dev_prof = {"name": dev_name, "role": dev_role, "portfolio": portfolio_url}
                            ai_pitch = groq.generate_personalized_cold_email(target_lead, dev_prof, selected_template_key)
                            st.session_state["current_ai_pitch"] = ai_pitch

                    pitch = st.session_state.get("current_ai_pitch") or PitchGenerator.generate_pitch(target_lead, selected_template_key)
                else:
                    pitch = PitchGenerator.generate_pitch(target_lead, selected_template_key)

                st.subheader("Subject Line:")
                st.code(pitch["subject"], language="text")

                st.subheader("Email Body Preview:")
                st.text_area("Email Content:", value=pitch["body"], height=380)
            else:
                st.info("No leads with valid emails found in your current scraped list. Scrape or discover new leads in Tab 1.")
        else:
            sample_lead = {"company_name": "Acme Retail Services", "url": "https://acmeretail.com", "primary_email": "contact@acmeretail.com", "decision_maker_name": "John Smith", "decision_maker_role": "CEO"}
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

        raw_leads_with_email = [l for l in st.session_state["scraped_leads"] if l.get("primary_email")]
        leads_to_mail = EmailSender.filter_already_sent(raw_leads_with_email)

        excluded_count = len(raw_leads_with_email) - len(leads_to_mail)
        if excluded_count > 0:
            st.warning(f"🛡️ **Deduplication**: Excluded {excluded_count} lead(s) that received emails in past campaigns.")

        st.info(f"Target Leads Ready for Outreach: **{len(leads_to_mail)}**")

        delay_between_mails = st.slider("Delay Between Emails (Seconds):", 1, 30, 2, help="Fast bulk dispatch! Default is 2 seconds.")

        launch_campaign = st.button("🚀 Launch Batch Cold Outreach", type="primary", use_container_width=True)

        if launch_campaign:
            if not gmail_app_password:
                st.error("Please provide your Gmail App Password.")
            elif not leads_to_mail:
                st.error("No new valid leads with emails available. (All leads have either received an email or have no email). Please discover new leads in Tab 1!")
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
