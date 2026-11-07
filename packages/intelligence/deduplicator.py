import hashlib
import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from typing import Optional, Tuple, Dict, Any

try:
    from rapidfuzz import fuzz
except ImportError:
    # Graceful fallback if rapidfuzz is not yet loaded
    class fuzz:
        @staticmethod
        def token_set_ratio(s1: str, s2: str) -> float:
            set1 = set(s1.lower().split())
            set2 = set(s2.lower().split())
            if not set1 or not set2:
                return 0.0
            intersection = set1.intersection(set2)
            return (len(intersection) / max(len(set1), len(set2))) * 100.0

class Deduplicator:
    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "ref", "referer", "referrer", "source", "fbclid", "gclid", "token", "session"
    }

    @classmethod
    def canonicalize_url(cls, raw_url: str) -> str:
        """Strips tracking query params, fragments, and standardizes URL for bit-exact comparison."""
        if not raw_url:
            return ""
        parsed = urlparse(raw_url.strip())
        # Filter query params
        filtered_query = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False)
            if k.lower() not in cls.TRACKING_PARAMS
        ]
        # Rebuild URL with sorted query parameters and stripped trailing slash
        clean_path = parsed.path.rstrip("/")
        clean_query = urlencode(sorted(filtered_query))
        clean_url = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            clean_path,
            "",
            clean_query,
            ""
        ))
        return clean_url

    @classmethod
    def hash_url(cls, canonical_url: str) -> str:
        return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()

    @classmethod
    def hash_content(cls, company: str, title: str, description: Optional[str]) -> str:
        content_str = f"{company.strip().lower()}||{title.strip().lower()}||{(description or '').strip()[:500]}"
        return hashlib.sha256(content_str.encode("utf-8")).hexdigest()

    @classmethod
    def normalize_title(cls, title: str) -> str:
        """
        Normalizes job titles:
        e.g. 'Software Development Engineer Intern - May 2027 (2 Month)' -> 'sde intern'
        """
        text = title.lower()
        # Common title replacements
        replacements = [
            (r"\bsoftware development engineer\b", "sde"),
            (r"\bsoftware engineer\b", "sde"),
            (r"\bassociate software engineer\b", "associate sde"),
            (r"\binternship\b", "intern"),
            (r"\bllm post[- ]training\b", "llm post training"),
            (r"\bgenops\b", "genops"),
            (r"\bquality assurance\b", "qa"),
            (r"\bquality control\b", "qc"),
        ]
        for pattern, repl in replacements:
            text = re.sub(pattern, repl, text)
        
        # Remove parenthetical years/months (e.g. '(May 2027)', '2026/2027')
        text = re.sub(r"\(.*?\)", "", text)
        # Remove months and years
        text = re.sub(r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b", "", text)
        text = re.sub(r"\b202[0-9]\b", "", text)
        # Remove non-alphanumeric except spaces
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        # Collapse multiple spaces
        text = " ".join(text.split())
        return text

    @classmethod
    def calculate_similarity(cls, title_a: str, title_b: str) -> float:
        norm_a = cls.normalize_title(title_a)
        norm_b = cls.normalize_title(title_b)
        return fuzz.token_set_ratio(norm_a, norm_b)

    @classmethod
    def evaluate_duplicate_candidate(
        cls,
        new_opp: Dict[str, Any],
        existing_opp: Dict[str, Any]
    ) -> Tuple[bool, str, float]:
        """
        Evaluates whether a new candidate is an exact duplicate, an update, or a different position.
        Returns: (is_duplicate: bool, reason: str, confidence: float)
        """
        # Exact URL Hash Match
        if new_opp.get("canonical_url_hash") and new_opp.get("canonical_url_hash") == existing_opp.get("canonical_url_hash"):
            return True, "EXACT_CANONICAL_URL_MATCH", 1.0

        # Exact External ATS ID Match under same company
        if new_opp.get("external_id") and new_opp.get("company", "").lower() == existing_opp.get("company", "").lower():
            if str(new_opp.get("external_id")).strip() == str(existing_opp.get("external_id")).strip():
                return True, "EXACT_ATS_EXTERNAL_ID_MATCH", 1.0

        # Title & Company Fuzzy Match
        company_a = new_opp.get("company", "").strip().lower()
        company_b = existing_opp.get("company", "").strip().lower()
        if company_a == company_b:
            similarity = cls.calculate_similarity(new_opp.get("title", ""), existing_opp.get("title", ""))
            if similarity >= 92.0:
                # Check location overlap
                locs_a = set(l.lower() for l in new_opp.get("locations", []))
                locs_b = set(l.lower() for l in existing_opp.get("locations", []))
                if not locs_a or not locs_b or locs_a.intersection(locs_b):
                    return True, f"HIGH_TITLE_SIMILARITY_MATCH ({similarity:.1f}%)", similarity / 100.0

        return False, "DISTINCT_OPPORTUNITY", 0.0
