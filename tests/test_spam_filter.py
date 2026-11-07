from packages.intelligence.spam_filter import CommercialSpamFilter
from packages.adapters.community import CommunitySubmissionAdapter


def test_campus_monk_course_ad_filtered():
    # Real ad copied from user screenshot
    promotional_ad = (
        "🔥 15% OFF. Just 5 Students. One Crazy Opportunity!\n"
        "This Diwali, don't just burst crackers... BURST YOUR PLACEMENT GOALS!\n"
        "💥 Flat 15% OFF on CampusMonk courses.\n"
        "Coupon Code: DIWALI15\n"
        "⚡ NEW SANKALP 10.0 - 2027 https://campusmonk1234.netlify.app/\n"
        "NEW TCS LIVE SANKALP BATCH https://bfwhv.courses.store/915181"
    )

    is_spam, score, reasons = CommercialSpamFilter.evaluate_text(promotional_ad)
    assert is_spam is True
    assert score >= 0.75
    assert len(reasons) >= 2

    # Verify adapter returns None for this ad
    result = CommunitySubmissionAdapter.parse_raw_text_submission(promotional_ad)
    assert result is None


def test_genuine_job_post_not_filtered():
    genuine_post = (
        "🔥 Hevo Freshers Hiring\n"
        "• Role: Associate Software Developer\n"
        "• Eligibility: BE/B.Tech\n"
        "• Eligible branches: CS, IT, EC & AI\n"
        "• Eligible batches: 2026 & 2027\n"
        "• Location: Pune\n"
        "• CTC: 6 - 8 LPA\n"
        "👉 Apply here: https://go.acciojob.com/pP8wXz"
    )

    is_spam, score, reasons = CommercialSpamFilter.evaluate_text(genuine_post)
    assert is_spam is False
    assert score < 0.5

    result = CommunitySubmissionAdapter.parse_raw_text_submission(genuine_post)
    assert result is not None
    assert result.company == "Hevo Data"
    assert "2026" in result.eligible_batches

