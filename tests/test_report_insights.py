from report_insights import (
    build_report_insights,
    parse_skill_buckets,
    score_band,
    suitability_label,
)


SKILL_MATCHING_TEXT = """### Fully Matched Skills
- Manual testing: strong evidence in SE II role
- Regression testing
- UAT

### Partially Matched Skills
- SQL

### Missing Skills
- Selenium
- API testing
- Automation testing
"""


def test_parse_skill_buckets_reads_headers_and_bullets():
    buckets = parse_skill_buckets(SKILL_MATCHING_TEXT)

    assert buckets["matched"] == ["Manual testing", "Regression testing", "UAT"]
    assert buckets["partial"] == ["SQL"]
    assert buckets["missing"] == ["Selenium", "API testing", "Automation testing"]


def test_parse_skill_buckets_reads_inline_colon_list():
    buckets = parse_skill_buckets("Missing skills: Selenium, CI/CD and Docker")

    assert buckets["missing"] == ["Selenium", "CI/CD", "Docker"]


def test_parse_skill_buckets_skips_placeholder_items():
    buckets = parse_skill_buckets("## Missing Skills\n- None\n- N/A")

    assert buckets["missing"] == []


def test_build_report_insights_extracts_score_and_counts():
    outputs = {
        "final_report": "## Job Match Score\n**72%** solid alignment.",
        "skill_matching": SKILL_MATCHING_TEXT,
        "gap_analysis": "",
    }

    insights = build_report_insights(outputs)

    assert insights["score"] == 72
    assert insights["suitability"] == "Good match"
    assert insights["counts"] == {"matched": 3, "partial": 1, "missing": 3}
    assert insights["total_skills"] == 7


def test_build_report_insights_falls_back_to_final_report_for_skills():
    outputs = {
        "final_report": "## Matched Skills\n- Python\n\n## Missing Skills\n- Go",
        "skill_matching": "",
        "gap_analysis": "",
    }

    insights = build_report_insights(outputs)

    assert insights["counts"]["matched"] == 1
    assert insights["counts"]["missing"] == 1


def test_build_report_insights_handles_missing_score():
    insights = build_report_insights({"final_report": "No number here.", "skill_matching": ""})

    assert insights["score"] is None
    assert insights["suitability"] == "Not available"


def test_suitability_and_band_thresholds():
    assert suitability_label(85) == "Strong match"
    assert suitability_label(65) == "Good match"
    assert suitability_label(45) == "Moderate match"
    assert suitability_label(20) == "Low match"
    assert score_band(85) == "#15934f"
    assert score_band(20) == "#d6336c"
