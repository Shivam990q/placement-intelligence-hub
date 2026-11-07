import pytest
from packages.intelligence.deduplicator import Deduplicator

def test_canonicalize_url():
    raw_url = "https://www.amazon.jobs/en-gb/jobs/10513277/software-development-engineer-intern-may-2027-2-month-amazon-university-talent-acquisition?utm_source=chatgpt.com&utm_medium=referral&ref=xyz"
    clean_url = Deduplicator.canonicalize_url(raw_url)
    assert "utm_source" not in clean_url
    assert "utm_medium" not in clean_url
    assert "ref" not in clean_url
    assert clean_url.startswith("https://www.amazon.jobs/en-gb/jobs/10513277")

def test_normalize_title():
    t1 = "Software Development Engineer Intern - May 2027 (2 Month)"
    norm = Deduplicator.normalize_title(t1)
    assert norm == "sde intern"

    t2 = "LLM Post-Training Expert (GenOPS L1)"
    norm2 = Deduplicator.normalize_title(t2)
    assert "llm post training" in norm2

def test_evaluate_duplicate_candidate_url_match():
    opp_a = {
        "company": "Amazon",
        "title": "SDE Intern",
        "canonical_url_hash": "abc123hash"
    }
    opp_b = {
        "company": "Amazon",
        "title": "Software Development Engineer Internship",
        "canonical_url_hash": "abc123hash"
    }
    is_dup, reason, conf = Deduplicator.evaluate_duplicate_candidate(opp_a, opp_b)
    assert is_dup is True
    assert conf == 1.0

def test_evaluate_duplicate_candidate_fuzzy_match():
    opp_a = {
        "company": "Amazon",
        "title": "Software Development Engineer Intern",
        "locations": ["Bengaluru"],
        "canonical_url_hash": "hash1"
    }
    opp_b = {
        "company": "Amazon",
        "title": "Software Development Engineer Internship (May 2027)",
        "locations": ["Bengaluru"],
        "canonical_url_hash": "hash2"
    }
    is_dup, reason, conf = Deduplicator.evaluate_duplicate_candidate(opp_a, opp_b)
    assert is_dup is True
    assert conf >= 0.90
