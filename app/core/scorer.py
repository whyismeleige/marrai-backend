from dataclasses import dataclass

from app.core.parser import ParsedPage


@dataclass
class CategoryScore:
    score: int
    max_possible: int
    metrics: dict[str, int]
    findings: list[str]
    recommendations: list[str]


@dataclass
class ScoreResult:
    overall_score: int
    metadata: CategoryScore
    content_quality: CategoryScore
    structured_data: CategoryScore
    connectivity: CategoryScore
    technical_compliance: CategoryScore


def _score_title(title: str | None) -> tuple[int, list[str], list[str]]:
    if not title:
        return (
            0,
            ["Title tag is not present", "Title is not present in the website"],
            [
                "Title is required for your website",
                "Title is heavily important for AI Citations",
            ],
        )

    word_count = len(title.split())

    upper_limit = 15
    lower_limit = 5

    max_score = 30

    if word_count < lower_limit:
        score = round((word_count / lower_limit) * max_score)
        return (
            score,
            ["Title is too short"],
            [
                "Lengthen your Title of your website",
                "Make your Title descriptive and definitive",
            ],
        )
    elif lower_limit <= word_count <= upper_limit:
        return (max_score, ["Title is properly defined"], [])
    else:
        score = max(max_score - (word_count - upper_limit) * 2, 10)
        return (score, ["Title is too long"], ["Make the title short and consise."])


def _score_meta_description(
    description: str | None,
) -> tuple[int, list[str], list[str]]:
    if not description:
        return (
            0,
            [
                "Meta Description is not present",
                "Meta Description is not present in the website",
            ],
            [
                "Meta Description is required for your website",
                "Meta Description is heavily important for your citations",
            ],
        )

    word_count = len(description.split())

    upper_limit = 20
    lower_limit = 15

    max_score = 30

    if word_count < lower_limit:
        score = round((word_count / lower_limit) * max_score)
        return (
            score,
            ["Meta Description is too short"],
            [
                "Lengthen your Meta Description of your website.",
                "Make your Meta Description descriptive and definitive.",
            ],
        )
    elif lower_limit <= word_count <= upper_limit:
        return (max_score, ["Meta Description is properly defined"], [])
    else:
        score = max(max_score - (word_count - upper_limit) * 2, 10)
        return (
            score,
            ["Meta Description is too long"],
            ["Make the description short and consise."],
        )


def _score_canonical_url(canonical_url: str | None) -> tuple[int, list[str], list[str]]:
    if not canonical_url:
        return (
            0,
            ["Canonical URL is not present in your website"],
            [
                "Canonical URL is required for proper citation and indexing of your website."
            ],
        )
    else:
        return (20, ["Canonical URL is present in your website"], [])


def _score_meta_robots(meta_robots: str | None) -> tuple[int, list[str], list[str]]:
    POINTS = {
        "index": 10,
        "noindex": -10,
        "follow": 10,
        "nofollow": -10,
        "all": 20,
        "none": -20,
        "noarchive": -5,
        "nosnippet": -5,
    }

    score = 12

    directives = (
        [item.strip().lower() for item in meta_robots.split(",")] if meta_robots else []
    )

    for directive in directives:
        score += POINTS.get(directive, 0)

    score = max(0, min(score, 20))

    if score == 0:
        return (
            score,
            ["Meta robots heavily restricts AI/crawler access"],
            ["Remove restrictive directives like noindex/nofollow"],
        )
    elif 0 < score < 12:
        return (
            score,
            ["Meta robots contains restrictive directives"],
            ["Review and remove unneccessary restrictions"],
        )
    elif score == 12:
        return (
            score,
            ["Meta robots not explicitly optimized"],
            ["Consider setting to index, follow"],
        )
    elif 12 < score < 20:
        return (score, ["Meta robots is mostly permissive"], [])
    elif score == 20:
        return (score, ["Meta robots fully permits indexing and following"], [])


def _score_metadata(page: ParsedPage) -> CategoryScore:
    title_score, title_findings, title_recs = _score_title(page.title)
    desc_score, desc_findings, desc_recs = _score_meta_description(
        page.meta_description
    )
    canon_score, canon_findings, canon_recs = _score_canonical_url(page.canonical_url)
    robots_score, robots_findings, robots_recs = _score_meta_robots(page.meta_robots)

    findings = []
    findings.extend(title_findings)
    findings.extend(desc_findings)
    findings.extend(canon_findings)
    findings.extend(robots_findings)

    recommendations = []
    recommendations.extend(title_recs)
    recommendations.extend(desc_recs)
    recommendations.extend(canon_recs)
    recommendations.extend(robots_recs)

    metrics = {
        "title": title_score,
        "meta_description": desc_score,
        "canonical_url": canon_score,
        "meta_robots": robots_score,
    }

    return CategoryScore(
        score=title_score + desc_score + canon_score + robots_score,
        max_possible=100,
        metrics=metrics,
        findings=findings,
        recommendations=recommendations,
    )

def _score_word_count(word_count: int) -> tuple[int, list[str], list[str]]:
    upper_limit = 2500
    lower_limit = 800

    max_score = 20

    if word_count < lower_limit:
        score = round((word_count / lower_limit) * max_score)
        return (
            score,
            ["Body Content is too short"],
            [
                "Lengthen your Content of your website",
                "Make your Content of your website descriptive and definitive",
            ],
        )
    elif lower_limit <= word_count <= upper_limit:
        return (max_score, ["Body Content of your website is of correct length"], [])
    else:
        score = max(max_score - (word_count - upper_limit) * 2, 7)
        return (
            score,
            ["Body Content of your website is too long."],
            [
                "Make your website content specific and properly defined",
                "Long Content is often classified as spam by AI Retrieval systems",
            ],
        )

def _score_headings(headings: list[dict[str, str]]) -> tuple[int, list[str], list[str]]:
    tags = [list(h.keys())[0] for h in headings]
    
    texts = [list(h.values())[0] for h in headings]
    
    h1_count = tags.count("h1")
    
    tag_set = set(tags)
    
    heading_word_counts = [len(t.split()) for t in texts]
    
    average_heading_word_count = sum(heading_word_counts) / len(heading_word_counts) if heading_word_counts else 0
    
    total_score = 0
    findings = []
    recommendations = []
    
    if h1_count == 1:
        total_score += 10
        findings.extend(["Page has a single well-defined H1 heading"])
        recommendations.extend([])
    elif h1_count > 1:
        total_score += 5
        findings.extend(["Page has multiple H1 headings"])
        recommendations.extend(["Use only one H1 heading per page for clear topic signaling"])
    else:
        findings.extend(["Page has no H1 heading"])
        recommendations.extend(["Add a single descriptive H1 heading to define the page topic"])
    
    if len(headings) >= 3:
        total_score += 10
        findings.extend(["Page has sufficient heading structure"])
        recommendations.extend([])
    elif 0 < len(headings) <= 2:
        total_score += 5
        findings.extend(["Page has minimal heading structure"])
        recommendations.extend(["Add more headings to break content into scannable sections"])
    else:
        findings.extend(["Page has no headings"])
        recommendations.extend(["Add headings (H1-H3) to structure your content for AI retrieval"])
    
    if "h1" in tag_set and "h2" in tag_set:
        total_score += 10
        findings.extend(["Page has adequate heading hierarchy"])
        recommendations.extend([])
    elif "h1" in tag_set:
        total_score += 5
        findings.extend(["Page lacks H2 hierarchy"])
        recommendations.extend(["Add H2 headings to create content sections for better chunking"])
    else: 
        findings.extend(["Page has no heading hierarchy"])
        recommendations.extend(["Add H1 and H2 headings to establish content structure"])
    
    if 5 <= average_heading_word_count <= 10:
        total_score += 10
        findings.extend(["Headings are well-defined and descriptive"])
        recommendations.extend([])
    elif 1 <= average_heading_word_count < 5:
        total_score += 5
        findings.extend(["Headings are too brief"])
        recommendations.extend(["Make headings more descriptive (aim for 5-10 words)"])
    else:
        findings.extend(["Headings are too long or empty"])
        recommendations.extend(["Keep headings concise and focused (5-10 words)"])
        
    return (total_score, findings, recommendations)
        
    
    