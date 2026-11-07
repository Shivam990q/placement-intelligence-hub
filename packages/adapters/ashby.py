from typing import List, Dict, Any, Optional
import httpx
from packages.adapters.base import BaseSourceAdapter
from packages.schemas.opportunity import OpportunityCreate
from packages.intelligence.eligibility import EligibilityAnalyzer

class AshbyAdapter(BaseSourceAdapter):
    """
    Adapter for Ashby Public Job Postings API.
    Endpoint: https://api.ashbyhq.com/posting-api/job-board/{company}
    """
    def __init__(self, company_slug: str, company_name: Optional[str] = None):
        self.company_slug = company_slug
        self.company_name = company_name or company_slug.capitalize()
        super().__init__(
            name=f"{self.company_name} (Ashby)",
            slug=f"ashby-{company_slug.lower()}",
            base_url=f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}",
            check_interval_minutes=60
        )

    async def fetch_opportunities(self) -> List[OpportunityCreate]:
        opportunities: List[OpportunityCreate] = []
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(self.base_url)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs = data.get("jobs", [])
                    for j in jobs:
                        title = j.get("title", "")
                        if any(k in title.lower() for k in ["software", "engineer", "intern", "developer", "ai", "machine"]):
                            job_id = str(j.get("id"))
                            location = j.get("location", "Remote / India")
                            desc = j.get("descriptionPlain", "")
                            
                            batches = EligibilityAnalyzer.extract_batches(desc)
                            degrees = EligibilityAnalyzer.extract_degrees(desc)
                            branches = EligibilityAnalyzer.extract_branches(desc)

                            opp = OpportunityCreate(
                                company=self.company_name,
                                title=title,
                                role_category="internship" if "intern" in title.lower() else "full_time",
                                locations=[location],
                                eligible_batches=batches or ["2026", "2027", "Freshers"],
                                eligible_degrees=degrees or ["B.Tech", "BE"],
                                eligible_branches=branches or ["CS", "IT"],
                                apply_url=j.get("jobUrl", f"https://jobs.ashbyhq.com/{self.company_slug}/{job_id}"),
                                raw_description=desc[:1500],
                                summary=f"{self.company_name} Role: {title} in {location}.",
                                external_id=job_id,
                                confidence_score=0.98,
                                verification_status="verified_official",
                                verification_evidence={"ats": "Ashby API", "company": self.company_slug, "id": job_id}
                            )
                            opportunities.append(opp)
        except Exception:
            pass

        return opportunities
