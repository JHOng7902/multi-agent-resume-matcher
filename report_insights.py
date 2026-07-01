"""Turn the agents' free-form Markdown report into structured data for charts.

The Skill Matching agent and Final Report agent both emit predictable
"Matched / Partially matched / Missing skills" sections. This module parses
those into skill buckets and a numeric score so the UI can visualize them.
It is deliberately defensive: if a section is absent, its bucket is empty and
the UI falls back gracefully.
"""

import re

from utils import extract_match_score

_BULLET_RE = re.compile(r"^\s*(?:[-*•‣◦]|\d+[.)])\s+(.*)$")
_SKIP_ITEMS = {"none", "n/a", "na", "not mentioned", "none identified", "not applicable"}


def _clean_header(line: str) -> str:
    core = re.sub(r"^[#>\s]*", "", line)
    core = re.sub(r"^\s*\d+[.)]\s*", "", core)
    core = core.replace("*", "").replace("`", "").strip()
    return core.rstrip(":").strip()


def _header_category(line: str):
    """Return 'matched' | 'partial' | 'missing' if the line is a section header."""
    core = _clean_header(line).lower()
    if not core or len(core.split()) > 8:
        return None
    if "partial" in core and "match" in core:
        return "partial"
    if "missing" in core and ("skill" in core or len(core.split()) <= 3):
        return "missing"
    if "fully matched" in core:
        return "matched"
    if "matched" in core and "partial" not in core and "missing" not in core:
        return "matched"
    return None


def _clean_item(text: str) -> str:
    item = text.replace("*", "").replace("`", "").strip()
    item = re.split(r":\s+", item)[0].strip()          # drop "name: explanation"
    item = re.split(r"\s[-–—]\s", item)[0].strip()     # drop "name - explanation"
    item = re.split(r"\s*\(", item)[0].strip()         # drop parentheticals
    return item.strip(" .,;")


def parse_skill_buckets(text: str) -> dict:
    """Extract matched/partial/missing skill names from one Markdown blob."""
    buckets = {"matched": [], "partial": [], "missing": []}
    if not text:
        return buckets

    current = None
    for raw in text.splitlines():
        line = raw.rstrip()
        category = _header_category(line)
        if category is not None:
            current = category
            if ":" in line:  # inline list, e.g. "Missing skills: Selenium, CI/CD"
                after = line.split(":", 1)[1].strip()
                for part in re.split(r"[,;]|\band\b", after):
                    item = _clean_item(part)
                    if item and len(item) <= 60:
                        buckets[current].append(item)
            continue

        if current is None:
            continue
        stripped = line.strip()
        if not stripped:
            continue

        bullet = _BULLET_RE.match(line)
        if bullet:
            item = _clean_item(bullet.group(1))
            if item and len(item) <= 60:
                buckets[current].append(item)
        elif not buckets[current] and "," in stripped and len(stripped) <= 200 and not stripped.endswith("."):
            for part in stripped.split(","):
                item = _clean_item(part)
                if item and len(item) <= 60:
                    buckets[current].append(item)

    for key, items in buckets.items():
        seen = set()
        deduped = []
        for skill in items:
            low = skill.lower()
            if low in _SKIP_ITEMS or low in seen:
                continue
            seen.add(low)
            deduped.append(skill)
        buckets[key] = deduped[:20]
    return buckets


def suitability_label(score):
    if score is None:
        return "Not available"
    if score >= 80:
        return "Strong match"
    if score >= 60:
        return "Good match"
    if score >= 40:
        return "Moderate match"
    return "Low match"


def score_band(score):
    """Color band for the score gauge."""
    if score is None:
        return "#5f6f89"
    if score >= 80:
        return "#15934f"
    if score >= 60:
        return "#1f5edb"
    if score >= 40:
        return "#a36a13"
    return "#d6336c"


def build_report_insights(outputs: dict) -> dict:
    """Assemble score + skill buckets from the agent outputs, with fallbacks."""
    final_report = outputs.get("final_report", "") or ""
    skill_matching = outputs.get("skill_matching", "") or ""
    gap_analysis = outputs.get("gap_analysis", "") or ""

    score_str = extract_match_score(final_report) or extract_match_score(skill_matching)
    score = int(score_str.rstrip("%")) if score_str else None

    buckets = parse_skill_buckets(skill_matching)
    from_final = parse_skill_buckets(final_report)
    for key in ("matched", "partial", "missing"):
        if not buckets[key]:
            buckets[key] = from_final[key]
    if not buckets["missing"]:
        buckets["missing"] = parse_skill_buckets(gap_analysis)["missing"]

    counts = {key: len(value) for key, value in buckets.items()}
    return {
        "score": score,
        "suitability": suitability_label(score),
        "band": score_band(score),
        "buckets": buckets,
        "counts": counts,
        "total_skills": sum(counts.values()),
    }
