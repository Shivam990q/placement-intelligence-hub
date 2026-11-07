from typing import Dict, Any
from packages.intelligence.formatter import ContentFormatter

class WhatsAppPublisher:
    """
    Safe WhatsApp Distribution Helper.
    Generates exact copy-ready formatted text and tracks clipboard export events.
    Zero risk of personal WhatsApp account ban!
    """

    @classmethod
    def generate_copy_ready_payload(cls, opp: Dict[str, Any]) -> Dict[str, Any]:
        card_text = ContentFormatter.format_whatsapp_card(opp)
        return {
            "opportunity_id": opp.get("id"),
            "company": opp.get("company"),
            "title": opp.get("title"),
            "whatsapp_text": card_text,
            "char_count": len(card_text),
            "instructions": "Click copy and paste into your WhatsApp group ('2027 Batch Placement 1' / 'Group of Placements')."
        }
