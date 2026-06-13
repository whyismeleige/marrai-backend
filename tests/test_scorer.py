import pytest
from app.core.scorer import (
    _score_title,
    _score_meta_description,
    _score_canonical_url,
    _score_meta_robots,
)


@pytest.mark.parametrize(
    "title, expected",
    [
        (
            None,
            (
                0,
                ["Title tag is not present", "Title is not present in the website"],
                [
                    "Title is required for your website",
                    "Title is heavily important for AI Citations",
                ],
            ),
        ),
        (
            "Word Count is 4",
            (
                24,
                ["Title is too short"],
                [
                    "Lengthen your Title of your website",
                    "Make your Title descriptive and definitive",
                ],
            ),
        ),
        ("Word Count is more than 5 words", (30, ["Title is properly defined"], [])),
        (
            "Title is really too long because it more than 15 words so the score is going down for this one",
            (20, ["Title is too long"], ["Make the title short and consise."]),
        ),
    ],
)
def test_score_title(title, expected):
    result = _score_title(title)
    assert result == expected


@pytest.mark.parametrize(
    "description, expected",
    [
        (
            None,
            (
                0,
                [
                    "Meta Description is not present",
                    "Meta Description is not present in the website",
                ],
                [
                    "Meta Description is required for your website",
                    "Meta Description is heavily important for your citations",
                ],
            ),
        ),
        (
            "Meta Description is too short",
            (
                10,
                ["Meta Description is too short"],
                [
                    "Lengthen your Meta Description of your website.",
                    "Make your Meta Description descriptive and definitive.",
                ],
            ),
        ),
        (
            "Meta Description is properly defined with well definitive description which is easily understandable by Crawlers and Bots",
            (30, ["Meta Description is properly defined"], []),
        ),
        (
            "Meta Description is really too long because it more than 20 words so the score is going down for this one because excessive content disposition.",
            (
                20,
                ["Meta Description is too long"],
                ["Make the description short and consise."],
            ),
        ),
    ],
)
def test_score_meta_description(description, expected):
    result = _score_meta_description(description)
    assert result == expected


@pytest.mark.parametrize(
    "canonical_url, expected",
    [
        (
            None,
            (
                0,
                ["Canonical URL is not present in your website"],
                [
                    "Canonical URL is required for proper citation and indexing of your website."
                ],
            ),
        ),
        (
            "",
            (
                0,
                ["Canonical URL is not present in your website"],
                [
                    "Canonical URL is required for proper citation and indexing of your website."
                ],
            ),
        ),
        (
            "https://example.com/about",
            (20, ["Canonical URL is present in your website"], []),
        ),
    ],
)
def test_score_canonical_url(canonical_url, expected):
    result = _score_canonical_url(canonical_url)
    assert result == expected


@pytest.mark.parametrize(
    "meta_robots, expected",
    [
        (
            None,
            (
                12,
                ["Meta robots not explicitly optimized"],
                ["Consider setting to index, follow"],
            ),
        ),
        (
            "INDEX, FOLLOW",
            (20, ["Meta robots fully permits indexing and following"], []),
        ),
        (
            "none",
            (
                0,
                ["Meta robots heavily restricts AI/crawler access"],
                ["Remove restrictive directives like noindex/nofollow"],
            ),
        ),
        (
            "noindex",
            (
                2,
                ["Meta robots contains restrictive directives"],
                ["Review and remove unneccessary restrictions"],
            ),
        ),
        (
            "all, none",
            (
                12,
                ["Meta robots not explicitly optimized"],
                ["Consider setting to index, follow"],
            ),
        ),
        (
            "max-snippet:-1",
            (
                12,
                ["Meta robots not explicitly optimized"],
                ["Consider setting to index, follow"],
            ),
        ),
    ],
)
def test_score_meta_robots(meta_robots, expected):
    result = _score_meta_robots(meta_robots)
    assert result == expected
