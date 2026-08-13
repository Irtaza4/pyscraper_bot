from typing import Dict, Any

APP_RELEVANT_KEYWORDS = [
    'booking', 'delivery', 'taxi', 'fleet', 'store', 'shop', 'ecommerce',
    'real estate', 'fitness', 'gym', 'clinic', 'hospital', 'salon', 'restaurant',
    'marketplace', 'service', 'logistic', 'transport', 'hotel', 'rental', 'job'
]

class LeadScorer:
    """Evaluates business suitability for App Development services outreach."""

    @staticmethod
    def calculate_score(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        score = 0
        reasons = []

        # 1. Contactability
        emails = extracted_data.get('emails', [])
        phones = extracted_data.get('phones', [])
        socials = extracted_data.get('socials', {})

        if emails:
            score += 25
            reasons.append("Email address available")
        else:
            reasons.append("No email address found")

        if phones:
            score += 10
            reasons.append("Phone number available")

        if socials:
            score += 10
            reasons.append(f"Social links found ({', '.join(socials.keys())})")

        # 2. App Opportunity Analysis
        has_app = extracted_data.get('has_app_store', False)
        if not has_app:
            score += 35
            reasons.append("No official iOS / Android app links detected (High Opportunity)")
        else:
            score += 5
            reasons.append("Has existing mobile app (Potential redesign or feature expansion opportunity)")

        # 3. Industry relevance
        text_content = (extracted_data.get('title', '') + " " + extracted_data.get('meta_description', '')).lower()
        matched_kw = [kw for kw in APP_RELEVANT_KEYWORDS if kw in text_content]
        if matched_kw:
            score += 20
            reasons.append(f"App-friendly industry keywords matched: {', '.join(matched_kw[:3])}")

        # Classification label
        if score >= 70:
            category = "Hot Lead 🔥"
        elif score >= 45:
            category = "Warm Lead ☀️"
        else:
            category = "Cold Lead ❄️"

        return {
            "score": min(score, 100),
            "category": category,
            "reasons": reasons
        }
