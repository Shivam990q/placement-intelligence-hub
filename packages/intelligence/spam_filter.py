"""Anti-Spam & Commercial Promotion Filter for Community Ingestion.

Automatically detects and drops course sales, webinar ads, discount coupons,
and commercial affiliate promotions (e.g. CampusMonk, Careerwill, paid course sellers)
so only 100% pure, verified job and internship links reach the placement hub.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Tuple


class CommercialSpamFilter:
    """Evaluates raw community posts to eliminate paid course promotions and ad clutter."""

    PROMOTION_PATTERNS = [
        # Discounts & Coupon Codes
        r"\b\d+%\s*(?:off|discount)\b",
        r"\bcoupon(?:\s*code)?\s*[:\-]?\s*[A-Z0-9_\-]{3,}\b",
        r"\bdiwali(?:\s*festival)?\s*(?:sale|learning\s*sale|offer)\b",
        r"\bfestive\s*(?:discount|offer|deal)\b",
        
        # Course & Coaching Sales
        r"\b(?:flat|get)\s*\d+%\s*off\b",
        r"\bcrash\s*course\b",
        r"\brecorded\s*learning\b",
        r"\bpaid\s*(?:batch|program|training)\b",
        r"\bcourse\s*(?:fee|price|discount)\b",
        r"\benrol(l)?\s*(?:now|fast|today)\b",
        r"\bbuy\s*(?:now|the\s*course)\b",
        r"\buse\s*code\s*[:\-]?\s*[A-Z0-9]+\b",
        
        # Urgency & Marketing Hype
        r"\bonly\s*(?:the\s*)?first\s*\d+\s*students\b",
        r"\bno\s*second\s*chance\s*after\b",
        r"\blimited\s*(?:seats|time\s*offer)\b",
        r"\bdon'?t\s*wait\s*for\s*the\s*perfect\s*opportunity\b",
        r"\bstop\s*scrolling\b",
        r"\bwebinar\s*link\b",
        r"\bjoin\s*the\s*\d+x\s*live\b",
        
        # Known Commercial LMS Stores & Course Platforms
        r"courses\.store/\d+",
        r"classplusapp\.com",
        r"graphy\.com",
        r"topmate\.io",
        r"cosmofeed\.com",
    ]

    COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PROMOTION_PATTERNS]

    @classmethod
    def evaluate_text(cls, text: str) -> Tuple[bool, float, list[str]]:
        """Analyzes text for commercial spam.

        Returns:
            Tuple[is_spam: bool, spam_score: float, matched_reasons: list[str]]
        """
        if not text:
            return False, 0.0, []

        matches = []
        for pattern in cls.COMPILED_PATTERNS:
            found = pattern.findall(text)
            if found:
                matches.append(found[0] if isinstance(found[0], str) else str(found[0]))

        # Calculate heuristic spam score
        # 1 match: warning (0.4)
        # 2 matches: likely spam (0.75)
        # 3+ matches: definite commercial ad (1.0)
        num_matches = len(matches)
        if num_matches == 0:
            score = 0.0
        elif num_matches == 1:
            score = 0.45
        elif num_matches == 2:
            score = 0.80
        else:
            score = min(1.0, 0.80 + (num_matches * 0.1))

        # Check if the post lacks actual job attributes while having promotional matches
        has_job_indicators = bool(
            re.search(r"\b(?:ctc|package|stipend|salary|role|job\s+title|location|apply\s+here)\b", text, re.IGNORECASE)
        )

        is_spam = score >= 0.75 or (score >= 0.45 and not has_job_indicators)

        return is_spam, round(score, 2), matches

