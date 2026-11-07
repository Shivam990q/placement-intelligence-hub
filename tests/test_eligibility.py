import pytest
from packages.intelligence.eligibility import EligibilityAnalyzer

def test_batch_extraction():
    text = "Hiring for batch 2026 and 2027 passouts. Freshers also welcome."
    batches = EligibilityAnalyzer.extract_batches(text)
    assert "2026" in batches
    assert "2027" in batches
    assert "Freshers" in batches

def test_degree_extraction():
    text = "Eligibility: BE/B.Tech or MCA in Computer Science"
    degrees = EligibilityAnalyzer.extract_degrees(text)
    assert "B.Tech" in degrees
    assert "B.E." in degrees
    assert "MCA" in degrees

def test_target_match_ethara():
    title = "LLM Post-Training – GenOPS"
    desc = "Pure English only, AI response evaluation, SFT & RLHF validation."
    result = EligibilityAnalyzer.evaluate_target_match(title, desc, ["2026", "2027"])
    assert result["match_score"] == 1.0
    assert result["is_recommended"] is True

def test_target_match_sde_intern():
    title = "Software Development Engineer Intern"
    desc = "Amazon University 2027 batch internship. Strong DSA required."
    result = EligibilityAnalyzer.evaluate_target_match(title, desc, ["2027"])
    assert result["match_score"] >= 0.75
    assert result["is_recommended"] is True

