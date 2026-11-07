import re
from typing import List, Dict, Any, Tuple
from packages.core.config import settings

class EligibilityAnalyzer:
    BATCH_PATTERNS = [
        (r"\b202[5-9]\b", lambda m: m.group(0)),
        (r"\b(?:batch|graduating|passout)\s*(?:of|in)?\s*(202[5-9])\b", lambda m: m.group(1)),
        (r"\bfreshers?\b", lambda m: "Freshers"),
    ]

    DEGREE_PATTERNS = [
        (r"\bb\.?\s*tech\b", "B.Tech"),
        (r"\bb\.?\s*e\b", "B.E."),
        (r"\bm\.?\s*tech\b", "M.Tech"),
        (r"\bmca\b", "MCA"),
        (r"\bbca\b", "BCA"),
        (r"\bbsc\b", "B.Sc"),
    ]

    BRANCH_PATTERNS = [
        (r"\bcomputer\s*science\b|\bcse?\b", "CS"),
        (r"\binformation\s*technology\b|\bit\b", "IT"),
        (r"\belectronics\b|\bece?\b", "EC"),
        (r"\bartificial\s*intelligence\b|\bai\b|\bdata\s*science\b", "AI/DS"),
    ]

    @classmethod
    def extract_batches(cls, text: str) -> List[str]:
        found_batches = set()
        text_lower = text.lower()
        for pattern, extractor in cls.BATCH_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                val = extractor(match)
                if val:
                    found_batches.add(val)
        return sorted(list(found_batches))

    @classmethod
    def extract_degrees(cls, text: str) -> List[str]:
        found_degrees = set()
        text_lower = text.lower()
        for pattern, deg in cls.DEGREE_PATTERNS:
            if re.search(pattern, text_lower):
                found_degrees.add(deg)
        return sorted(list(found_degrees))

    @classmethod
    def extract_branches(cls, text: str) -> List[str]:
        found_branches = set()
        text_lower = text.lower()
        for pattern, branch in cls.BRANCH_PATTERNS:
            if re.search(pattern, text_lower):
                found_branches.add(branch)
        return sorted(list(found_branches))

    @classmethod
    def evaluate_target_match(
        cls,
        title: str,
        description: str,
        eligible_batches: List[str]
    ) -> Dict[str, Any]:
        """
        Calculates alignment with target student profile:
        Target: Batch 2026/2027, CS/IT, SDE / Intern / LLM GenOPS
        """
        score = 0.0
        reasons = []

        # 1. Batch Match (35%)
        matches_batch = False
        target_batches = set(settings.TARGET_BATCHES)
        if any(b in target_batches for b in eligible_batches) or "Freshers" in eligible_batches:
            score += 0.35
            matches_batch = True
            reasons.append(f"Eligible Batch Match: {', '.join(eligible_batches)}")
        elif not eligible_batches:
            # Not specified -> neutral review
            score += 0.15
            reasons.append("Batch unspecified (Open to all or needs manual review)")

        # 2. Target Role Match (40%)
        combined_text = f"{title} {description}".lower()
        role_hits = [kw for kw in settings.TARGET_ROLES_KEYWORDS if kw.lower() in combined_text]
        if role_hits:
            score += 0.40
            reasons.append(f"Target Role Match: {', '.join(set(role_hits[:3]))}")

        # 3. Dedicated Priority Boost for Ethara LLM GenOPS
        if "llm" in combined_text and ("genops" in combined_text or "post-training" in combined_text or "post training" in combined_text):
            score = 1.0
            reasons.append("🔥 CRITICAL TARGET ROLE: Ethara / GenOPS Post-Training Match!")

        # 4. Freshness & High signal
        score = min(1.0, score + 0.25)

        return {
            "match_score": round(score, 2),
            "is_recommended": score >= 0.65,
            "reasons": reasons
        }
