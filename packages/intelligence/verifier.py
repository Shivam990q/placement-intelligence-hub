from urllib.parse import urlparse
from typing import Dict, Any, Tuple
import httpx

class SourceVerifier:
    OFFICIAL_ATS_DOMAINS = {
        "boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com",
        "jobs.smartrecruiters.com", "apply.workable.com", "myworkdayjobs.com",
        "amazon.jobs", "careers.google.com", "careers.microsoft.com",
        "hrms.ethara.ai", "ethara.ai"
    }

    TRUSTED_AGGREGATORS = {
        "acciojob.com", "unstop.com", "internshala.com", "wellfound.com", "linkedin.com"
    }

    SUSPICIOUS_DOMAINS = {
        "bit.ly", "tinyurl.com", "t.co", "cutt.ly", "shorturl.at"
    }

    @classmethod
    def evaluate_url_authority(cls, apply_url: str) -> Tuple[str, Dict[str, Any]]:
        """
        Determines if the application link is an official company ATS,
        a trusted aggregator, or requires manual review.
        """
        try:
            parsed = urlparse(apply_url)
            netloc = parsed.netloc.lower()
            
            # Check Official ATS
            if any(netloc == domain or netloc.endswith("." + domain) for domain in cls.OFFICIAL_ATS_DOMAINS):
                return "verified_official", {
                    "is_official_domain": True,
                    "domain": netloc,
                    "risk_level": "LOW",
                    "note": "Official corporate career portal or ATS link"
                }

            # Check Trusted Aggregator
            if any(netloc == domain or netloc.endswith("." + domain) for domain in cls.TRUSTED_AGGREGATORS):
                return "verified_secondary", {
                    "is_official_domain": False,
                    "domain": netloc,
                    "risk_level": "LOW",
                    "note": "Verified aggregator or job board"
                }

            # Check Link Shorteners / Suspicious
            if netloc in cls.SUSPICIOUS_DOMAINS:
                return "unverified", {
                    "is_official_domain": False,
                    "domain": netloc,
                    "risk_level": "MEDIUM",
                    "note": "Shortened URL detected; needs expansion/manual check"
                }

            return "unverified", {
                "is_official_domain": False,
                "domain": netloc,
                "risk_level": "NEUTRAL",
                "note": "Custom corporate or educational domain"
            }
        except Exception as e:
            return "unverified", {
                "is_official_domain": False,
                "error": str(e),
                "risk_level": "HIGH"
            }

    @classmethod
    async def check_live_status(cls, url: str, timeout_seconds: float = 5.0) -> bool:
        """Lightweight HEAD/GET probe to verify link is live."""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
                resp = await client.head(url)
                if resp.status_code in (200, 301, 302, 307, 308):
                    return True
                # Some servers reject HEAD; fallback to GET with range
                resp = await client.get(url, headers={"Range": "bytes=0-100"})
                return resp.status_code in (200, 206, 301, 302, 307, 308)
        except Exception:
            return False
