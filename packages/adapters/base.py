from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from packages.schemas.opportunity import OpportunityCreate

class BaseSourceAdapter(ABC):
    def __init__(self, name: str, slug: str, base_url: str, check_interval_minutes: int = 30):
        self.name = name
        self.slug = slug
        self.base_url = base_url
        self.check_interval_minutes = check_interval_minutes

    @abstractmethod
    async def fetch_opportunities(self) -> List[OpportunityCreate]:
        """
        Fetches listings from the source, normalizes into standard OpportunityCreate objects.
        """
        pass

    def __repr__(self) -> str:
        return f"<SourceAdapter: {self.name} ({self.slug})>"
