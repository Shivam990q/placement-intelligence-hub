import pytest
from packages.intelligence.formatter import ContentFormatter

def test_telegram_ethara_formatter():
    opp = {
        "company": "Ethara.AI",
        "title": "LLM Post-Training – GenOPS",
        "role_category": "genai_ops",
        "locations": ["Gurugram, Haryana"],
        "eligible_batches": ["2026", "2027"],
        "ctc_text": "₹6 LPA",
        "apply_url": "https://hrms.ethara.ai/careers",
        "requirements": ["Pure English Only", "Prompt evaluation"]
    }
    msg = ContentFormatter.format_telegram_markdown(opp)
    assert "TARGET ROLE ALERT — ETHARA.AI" in msg
    assert "Pure English Only" in msg
    assert "https://hrms.ethara.ai/careers" in msg

def test_whatsapp_card_formatter():
    opp = {
        "company": "Hevo Data",
        "title": "Associate Software Developer",
        "locations": ["Pune"],
        "eligible_batches": ["2026 & 2027"],
        "ctc_text": "6 - 8 LPA",
        "apply_url": "https://go.acciojob.com/pP8wXz",
        "requirements": ["BE/B.Tech", "CS, IT, EC & AI"]
    }
    card = ContentFormatter.format_whatsapp_card(opp)
    assert "*Company:* Hevo Data" in card
    assert "*Package / CTC:* 6 - 8 LPA" in card
    assert "https://go.acciojob.com/pP8wXz" in card
