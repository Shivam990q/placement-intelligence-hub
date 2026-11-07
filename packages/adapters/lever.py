from typing import List, Dict, Any, Optional
import httpx
from packages.adapters.base import BaseSourceAdapter
from packages.schemas.opportunity import OpportunityCreate
from packages.intelligence.eligibility import EligibilityAnalyzer

class LeverAdapter(BaseSourceAdapter):
    """
    Adapter for Lever Postings API.
    Endpoint: https://api.lever.co/v0/postings/{company}
    """
    def __init__(self, company_slug: str, company_name: Optional[str] = None):
        self.company_slug = company_slug
        self.company_name = company_name or company_slug.capitalize()
        super().__init__(
            name=f"{self.company_name} (Lever)",
            slug=f"lever-{company_slug.lower()}",
            base_url=f"https://api.lever.co/v0/postings/{company_slug}?mode=json",
            check_interval_minutes=60
        )

    async def fetch_opportunities(self) -> List[OpportunityCreate]:
        opportunities: List[OpportunityCreate] = []
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(self.base_url)
                if resp.status_code == 200:
                    jobs = resp.json()
                    for j in jobs:
                        text_title = j.get("text", "")
                        if any(k in text_title.lower() for k in ["software", "engineer", "intern", "developer", "ai", "analyst"]):
                            job_id = str(j.get("id"))
                            location = j.get("categories", {}).get("location", "India / Remote")
                            description = j.get("descriptionPlain", "")
                            
                            batches = EligibilityAnalyzer.extract_batches(description)
                            degrees = EligibilityAnalyzer.extract_degrees(description)
                            branches = EligibilityAnalyzer.extract_branches(description)

                            opp = OpportunityCreate(
                                company=self.company_name,
                                title=text_title,
                                role_category="internship" if "intern" in text_title.lower() else "full_time",
                                locations=[location],
                                eligible_batches=batches or ["2026", "2027", "Freshers"],
                                eligible_degrees=degrees or ["B.Tech", "BE"],
                                eligible_branches=branches or ["CS", "IT"],
                                apply_url=j.get("hostedUrl", f"https://jobs.lever.co/{self.company_slug}/{job_id}"),
                                raw_description=description[:1500],
                                summary=f"{self.company_name} Opening: {text_title} located at {location}.",
                                external_id=job_id,
                                confidence_score=0.98,
                                verification_status="verified_official",
                                verification_evidence={"ats": "Lever Postings API", "company": self.company_slug, "id": job_id}
                            )
                            opportunities.append(opp)
        except Exception:
            pass

        return opportunities

