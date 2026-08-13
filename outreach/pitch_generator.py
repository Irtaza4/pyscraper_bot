from typing import Dict, Any, List

EMAIL_TEMPLATES = {
    "opportunity_audit": {
        "name": "Mobile App Opportunity Audit (Recommended)",
        "subject": "Mobile App Idea for {{ company_name }} | Flutter Developer Intro",
        "body_template": """Hi {{ greeting_name }},

I came across {{ company_name }} ({{ url }}) while researching businesses in your space, and I was really impressed by your services.

I’m Irtaza Khalid, a Flutter & Cross-Platform Mobile Developer with hands-on experience building, publishing, and maintaining production iOS and Android apps on the Apple App Store and Google Play Store.

While reviewing your platform, I noticed that offering a dedicated iOS & Android mobile app could significantly boost your customer engagement, retention, and seamless booking/ordering experience.

Here are a few production mobile apps I have built and published live:
• JobSnap – On-Demand Marketplace App (App Store & Google Play)
• RideHoppy – Dual Ride-Sharing App Platform (App Store & Google Play)
• B2B Cabs – Corporate Employee Transportation & Tracking System

As a sole developer, I handle everything end-to-end — from UI design & Flutter code to backend integration, real-time tracking, push notifications, and App Store/Play Store deployment.

Would you be open to a quick 10-minute call next week to discuss how a custom mobile app could scale {{ company_name }}?

Best regards,

Irtaza Khalid
Flutter & Mobile App Developer
🌐 Portfolio: https://irtaza-dev.netlify.app
📧 Email: Irtazakhalidll@gmail.com
📱 Phone: +92 308 4221084
🔗 LinkedIn: https://linkedin.com/in/irtaza-khalid
💻 GitHub: https://github.com/Irtaza4
📸 Instagram: https://www.instagram.com/irtaza.codes?igsh=d25zeDNwOHc4bzV2&utm_source=qr
"""
    },
    "direct_developer": {
        "name": "Direct Freelance Developer Pitch",
        "subject": "Experienced Cross-Platform Mobile Developer available for {{ company_name }}",
        "body_template": """Hello {{ greeting_name }},

I'm reaching out to introduce myself — my name is Irtaza Khalid, a Flutter Developer specializing in high-performance iOS and Android mobile apps.

I build clean, scalable cross-platform apps using Flutter, Clean Architecture, Provider state management, and real-time backend integrations (Node.js, Firebase, WebSockets, Maps API).

Key Highlights of My Work & Portfolio:
• Published multi-role apps on Apple App Store & Google Play Store (JobSnap, RideHoppy, B2B Cabs).
• Deep expertise in real-time location tracking, foreground services, payment flows, and push notifications (FCM, OneSignal).
• Complete ownership: From UI concept & architecture to store approval.

🌐 Live Portfolio & Links:
• Portfolio Website: https://irtaza-dev.netlify.app
• LinkedIn: https://linkedin.com/in/irtaza-khalid
• GitHub: https://github.com/Irtaza4
• Instagram: https://www.instagram.com/irtaza.codes?igsh=d25zeDNwOHc4bzV2&utm_source=qr

If {{ company_name }} has upcoming mobile app projects or needs an experienced developer to build or upgrade an iOS/Android app, I'd love to connect!

I've attached my resume for your review. Let me know if you'd be available for a brief chat.

Best regards,

Irtaza Khalid
Flutter Developer | iOS & Android Apps
🌐 Portfolio: https://irtaza-dev.netlify.app
📧 Email: Irtazakhalidll@gmail.com
📱 Phone: +92 308 4221084
"""
    },
    "free_consultation": {
        "name": "Free 15-Min Mobile Strategy Call",
        "subject": "Quick mobile app question for {{ company_name }}",
        "body_template": """Hi {{ greeting_name }},

Hope you're having a great week!

My name is Irtaza Khalid, a Flutter Developer. I help businesses transform their web platforms and services into high-converting iOS & Android mobile apps.

I'd love to offer a complimentary 15-minute consultation to share ideas on how a custom mobile app could automate your workflows, reach mobile customers, and increase sales for {{ company_name }}.

Feel free to review my live portfolio and published apps (JobSnap, RideHoppy, B2B Cabs):
🌐 Portfolio Website: https://irtaza-dev.netlify.app
🔗 LinkedIn: https://linkedin.com/in/irtaza-khalid
💻 GitHub: https://github.com/Irtaza4
📸 Instagram: https://www.instagram.com/irtaza.codes?igsh=d25zeDNwOHc4bzV2&utm_source=qr

Are you available for a quick chat this Thursday or Friday?

Warm regards,

Irtaza Khalid
Flutter & Mobile Developer
🌐 Portfolio: https://irtaza-dev.netlify.app
📧 Email: Irtazakhalidll@gmail.com
📱 Phone: +92 308 4221084
"""
    }
}

class PitchGenerator:
    """Generates personalized email pitches for target lead companies & decision makers."""

    @staticmethod
    def list_template_keys() -> List[Dict[str, str]]:
        return [{"key": k, "name": v["name"]} for k, v in EMAIL_TEMPLATES.items()]

    @staticmethod
    def generate_pitch(lead: Dict[str, Any], template_key: str = "opportunity_audit") -> Dict[str, str]:
        template_info = EMAIL_TEMPLATES.get(template_key, EMAIL_TEMPLATES["opportunity_audit"])
        company_name = lead.get("company_name") or "Business"
        url = lead.get("url") or lead.get("domain") or "your website"

        dm_name = lead.get("decision_maker_name", "").strip()
        dm_role = lead.get("decision_maker_role", "Founder").strip()

        if dm_name:
            greeting_name = f"{dm_name} ({dm_role} at {company_name})"
        else:
            greeting_name = f"{company_name} Team"

        subject = template_info["subject"].replace("{{ company_name }}", company_name)
        body = template_info["body_template"].replace("{{ company_name }}", company_name).replace("{{ greeting_name }}", greeting_name).replace("{{ url }}", url)

        return {
            "subject": subject,
            "body": body,
            "to_email": lead.get("primary_email", ""),
            "company_name": company_name
        }
