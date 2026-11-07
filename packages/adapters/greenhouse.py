from typing import List, Dict, Any, Optional
import httpx
from packages.adapters.base import BaseSourceAdapter
from packages.schemas.opportunity import OpportunityCreate
from packages.intelligence.eligibility import EligibilityAnalyzer

class GreenhouseAdapter(BaseSourceAdapter):
    """
    Adapter for Greenhouse Public Job Board API.
    Endpoint: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
    """
    def __init__(self, board_token: str, company_name: Optional[str] = None):
        self.board_token = board_token
        self.company_name = company_name or board_token.capitalize()
        super().__init__(
            name=f"{self.company_name} (Greenhouse)",
            slug=f"greenhouse-{board_token.lower()}",
            base_url=f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true",
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
                        # Filter for engineering, software, tech, intern
                        if any(k in title.lower() for k in ["software", "engineer", "developer", "intern", "data", "ai", "product"]):
                            job_id = str(j.get("id"))
                            location = j.get("location", {}).get("name", "Remote / India")
                            content = j.get("content", "")
                            
                            batches = EligibilityAnalyzer.extract_batches(content)
                            degrees = EligibilityAnalyzer.extract_degrees(content)
                            branches = EligibilityAnalyzer.extract_branches(content)

                            opp = OpportunityCreate(
                                company=self.company_name,
                                title=title,
                                role_category="internship" if "intern" in title.lower() else "full_time",
                                locations=[location],
                                eligible_batches=batches or ["2026", "2027", "Freshers"],
                                eligible_degrees=degrees or ["B.Tech", "BE", "MCA"],
                                eligible_branches=branches or ["CS", "IT", "Circuit"],
                                apply_url=j.get("absolute_url") or f"https://boards.greenhouse.io/{self.board_token}/jobs/{job_id}",
                                raw_description=content[:1500],
                                summary=f"{self.company_name} Tech Opportunity: {title} in {location}.",
                                external_id=job_id,
                                confidence_score=0.99,
                                verification_status="verified_official",
                                verification_evidence={"ats": "Greenhouse API", "board": self.board_token, "id": job_id}
                            )
                            opportunities.append(opp)
        except Exception:
            pass

        return opportunities
