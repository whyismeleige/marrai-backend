from dataclasses import dataclass


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

    if word_count < 5:
        score = round((word_count / 5) * 30)
        return (
            score,
            ["Title is too short"],
            [
                "Lengthen your Title of your website",
                "Make your Title descriptive and definitive",
            ],
        )
    elif 5 <= word_count <= 15:
        return (30, ["Title is properly defined"], [])
    else:
        score = max(30 - (word_count - 15) * 2, 10)
        return (score, ["Title is too long"], ["Make the title short and consise."])
