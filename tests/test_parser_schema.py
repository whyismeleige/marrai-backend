import json
import pytest
from bs4 import BeautifulSoup

from app.core.parser import (
    FAQItem,
    _extract_schema,
    _extract_schema_types,
    _extract_faq_items,
    _build_faq_items,
)


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


@pytest.mark.parametrize(
    "node, expected",
    [
        ({"@type": "Article", "headline": "Some headline"}, ["Article"]),
        (
            {
                "@context": "https://schema.org",
                "@graph": [
                    {"@type": "Organization", "name": "Acme"},
                    {"@type": "WebSite", "url": "https://acme.com"},
                ],
            },
            ["Organization", "WebSite"],
        ),
        (
            {
                "@context": "https://schema.org",
                "@graph": [
                    {"@type": "Organization", "name": "Acme"},
                    {"@type": "WebSite", "url": "https://acme.com"},
                ],
            },
            ["Organization", "WebSite"],
        ),
        (
            [
                {
                    "@type": "WebPage",
                    "@context": "https://schema.org",
                    "@graph": [
                        {"@type": "Person", "name": "Rahul"},
                        {"@type": "WebSite", "url": "https://acme.com"},
                    ],
                },
                {
                    "@context": "https://schema.org",
                    "@graph": [
                        {"@type": "Organization", "name": "Acme"},
                        {"@type": "WebSite", "url": "https://acme.com"},
                    ],
                },
            ],
            ["WebPage", "Person", "WebSite", "Organization", "WebSite"],
        ),
        ({"headline": "Some headline"}, []),
        (
            {
                "@type": ["Article", "WebSite", "WebSite", "Organization"],
                "headline": "Some headline",
            },
            ["Article", "WebSite", "WebSite", "Organization"],
        ),
        ("Some Random string", []),
    ],
)
def test_extract_schema_types(node, expected):
    result = _extract_schema_types(node)
    assert result == expected


@pytest.mark.parametrize(
    "node, expected",
    [
        (
            {"name": "Question 1", "acceptedAnswer": {"text": "Answer 1"}},
            [FAQItem("Question 1", "Answer 1")],
        ),
        (
            {
                "name": "Question 1",
                "acceptedAnswer": [
                    {"text": "Answer 1"},
                    {"text": "Answer 2"},
                    {"text": "Answer 3"},
                ],
            },
            [FAQItem("Question 1", "Answer 1 Answer 2 Answer 3")],
        ),
        (
            {
                "name": "",
                "acceptedAnswer": [
                    {"text": "Answer 1"},
                    {"text": "Answer 2"},
                    {"text": "Answer 3"},
                ],
            },
            [],
        ),
        (
            {
                "name": "Question 1",
            },
            [],
        ),
        (
            {
                "name": "Question 1",
                "text": "Answer 1",
            },
            [FAQItem("Question 1", "Answer 1")],
        ),
        (
            [
                {
                    "name": "Question 1",
                    "text": "Answer 1",
                },
                {
                    "name": "Question 2",
                    "text": "Answer 2",
                },
            ],
            [FAQItem("Question 1", "Answer 1"), FAQItem("Question 2", "Answer 2")],
        ),
        (
            {"name": "Question 1", "text": "Answer 1", "acceptedAnswer": "Answer 2"},
            [FAQItem("Question 1", "Answer 2 Answer 1")],
        ),
    ],
)
def test_build_faq_items(node, expected):
    result = _build_faq_items(node)
    assert result == expected


@pytest.mark.parametrize(
    "node, expected",
    [
        (
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "name": "Question 1",
                        "text": "Answer 1",
                    },
                    {
                        "name": "Question 2",
                        "text": "Answer 2",
                    },
                ],
            },
            [FAQItem("Question 1", "Answer 1"), FAQItem("Question 2", "Answer 2")],
        ),
        (
            [
                {
                    "@type": "FAQPage",
                },
                {
                    "@type": "FAQPage",
                    "mainEntity": [
                        {
                            "name": "Question 1",
                            "text": "Answer 1",
                        },
                        {
                            "name": "Question 2",
                            "text": "Answer 2",
                        },
                    ],
                },
            ],
            [FAQItem("Question 1", "Answer 1"), FAQItem("Question 2", "Answer 2")],
        ),
        (
            {
                "@context": "https://schema.org",
                "@graph": [
                    {"@type": "Organization", "name": "Acme"},
                    {"@type": "WebSite", "url": "https://acme.com"},
                    {
                        "@type": ["FAQPage", "WebPage"],
                        "mainEntity": [
                            {
                                "name": "Question 1",
                                "text": "Answer 1",
                            },
                            {
                                "name": "Question 2",
                                "text": "Answer 2",
                            },
                        ],
                    },
                ],
            },
            [FAQItem("Question 1", "Answer 1"), FAQItem("Question 2", "Answer 2")],
        ),
        ("Random String in form of Malformed JSON", []),
        (
            {
                "@context": "https://schema.org",
                "@graph": [
                    {"@type": "Organization", "name": "Acme"},
                    {"@type": "WebSite", "url": "https://acme.com"},
                    {
                        "@type": ["WebPage"],
                        "mainEntity": [
                            {
                                "name": "Question 1",
                                "text": "Answer 1",
                            },
                            {
                                "name": "Question 2",
                                "text": "Answer 2",
                            },
                        ],
                    },
                ],
            },
            [],
        ),
    ],
)
def test_extract_faq_items(node, expected):
    result = _extract_faq_items(node)
    assert result == expected


@pytest.mark.parametrize(
    "html, expected",
    [
        (
            """
        <html>
            <head>
                <script type="application/ld+json" >
                    {
                        "@type": "Article",
                        "headline": "Some headline"
                    }
                </script>
            </head>
        </html>
        """,
            (
                ['{"@type":"Article","headline":"Some headline"}'],
                ["Article"],
                [{"@type": "Article", "headline": "Some headline"}],
            ),
        ),
        (
            """
        <html>
            <head>
                <script type="application/ld+json">
            {
                "@type": "FAQPage"
            }
            </script>
            <script type="application/ld+json" >
            {
                "@context": "https://schema.org",
                "@graph": [
                    {"@type": ["Organization", "WebPage"], "name": "Acme"},
                    {"@type": "WebSite", "url": "https://acme.com"}
                ]
            }
            </script>
            </head>
            </html>
        """,
            (
                [
                    '{"@type":"FAQPage"}',
                    '{"@context":"https://schema.org","@graph":[{"@type":["Organization", "WebPage"],"name":"Acme"},{"@type":"WebSite","url":"https://acme.com"}]}',
                ],
                ["FAQPage", "Organization", "WebPage", "WebSite"],
                [
                    {
                        "@type": "FAQPage",
                    },
                    {
                        "@context": "https://schema.org",
                        "@graph": [
                            {"@type": ["Organization", "WebPage"], "name": "Acme"},
                            {"@type": "WebSite", "url": "https://acme.com"},
                        ],
                    },
                ],
            ),
        ),
        ("Random String in form of Malformed JSON", ([], [], [])),
        (
            """
        <html>
            <head>
            </head>
        </html>
        """,
            (
                [],
                [],
                [],
            ),
        ),
    ],
)
def test_extract_schema(html, expected):
    soup = make_soup(html)
    expected_schema_data, expected_schema_types, expected_json_data = expected 
    extracted_schema_data, extracted_schema_types, extracted_json_data = _extract_schema(soup)
    
    for i in range(len(expected_schema_data)):
        assert json.loads(extracted_schema_data[i]) == json.loads(expected_schema_data[i])
        
    assert set(extracted_schema_types) == set(expected_schema_types)
    assert extracted_json_data == expected_json_data
