import pytest
from app.core.scorer import _score_title


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
