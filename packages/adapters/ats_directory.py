"""Curated Public ATS Board Directory.

Pre-configured directory of top technology companies and high-growth startups
that hire software engineers, interns, and AI specialists via public ATS APIs
(Greenhouse, Lever, Ashby).
"""

from __future__ import annotations

from typing import Dict, List

# Greenhouse Boards: accessed via https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
GREENHOUSE_BOARDS: List[str] = [
    "razorpaysoftwareprivatelimited",
    "swiggy",
    "cred",
    "postman",
    "browserstack",
    "meesho",
    "urbancompany",
    "inmobi",
    "phonepe",
    "hackerearth",
    "juspay",
    "slice",
    "zepto",
]

# Lever Boards: accessed via https://api.lever.co/v0/postings/{site}?mode=json
LEVER_BOARDS: List[str] = [
    "coinswitch",
    "groww",
    "clevertap",
    "jupiter",
    "khatabook",
    "atlassian",
]

# Ashby Boards: accessed via https://api.ashbyhq.com/posting-api/job-board/{organization}
ASHBY_BOARDS: List[str] = [
    "supabase",
    "vercel",
    "linear",
    "retool",
    "ramp",
    "deel",
    "cursor",
]
