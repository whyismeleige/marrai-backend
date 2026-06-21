from dataclasses import dataclass
from typing import Counter

import numpy

from app.core.chunker import TextChunk
from app.core.embedder import ChunkEmbedding


@dataclass
class ChunkSemanticScore:
    heading: str
    section_position: int
    alignment_score: int
    finding: str | None
    recommendation: str | None


@dataclass
class PageSemanticScore:
    url: str
    overall_score: int
    section_scores: list[ChunkSemanticScore]
    finding: str | None
    recommendation: str | None


@dataclass
class SemanticScoreResult:
    overall_score: int
    page_scores: list[PageSemanticScore]
    top_findings: list[str]
    top_recommendations: list[str]


def score_individual_chunk(
    chunk_embedding: tuple[TextChunk, ChunkEmbedding],
) -> ChunkSemanticScore:
    text_chunk, embedding = chunk_embedding

    alignment_score = float(
        numpy.dot(embedding.heading_embedding, embedding.content_embedding)
    )

    alignment_score_int = round(alignment_score * 100)

    finding = None
    recommendation = None

    if alignment_score_int > 70:
        finding = f"Section '{text_chunk.heading}' is semantically coherent and retrieval-ready"
    elif 30 < alignment_score_int <= 70:
        finding = (
            f"Section '{text_chunk.heading}' partially drifts from its stated topic"
        )
        recommendation = f"Rewrite content under '{text_chunk.heading}' to more directly address the heading topic"
    else:
        finding = f"Section '{text_chunk.heading}' is semantically misaligned with its heading"
        recommendation = f"Either rewrite the content or change the heading to match what the section actually covers"

    return ChunkSemanticScore(
        heading=text_chunk.heading,
        section_position=text_chunk.section_position,
        alignment_score=alignment_score_int,
        finding=finding,
        recommendation=recommendation,
    )


def score_chunks(
    url: str, chunk_embeddings: list[tuple[TextChunk, ChunkEmbedding]]
) -> PageSemanticScore:
    section_scores: list[ChunkSemanticScore] = []

    total_score = 0
    finding = None
    recommendation = None

    for chunk_embedding in chunk_embeddings:
        chunk_semantic_score = score_individual_chunk(chunk_embedding)
        total_score += chunk_semantic_score.alignment_score
        section_scores.append(chunk_semantic_score)

    overall_score = round(total_score / len(section_scores)) if section_scores else 0

    if overall_score > 70:
        finding = "Page is semantically coherent and well-structured for AI retrieval"
    elif 40 <= overall_score <= 70:
        finding = (
            "Page has moderate semantic coherence — some sections need realignment"
        )
        recommendation = (
            "Review sections with low alignment scores and rewrite to match headings"
        )
    else:
        finding = "Page has poor semantic coherence — AI retrieval will be unreliable"
        recommendation = (
            "Conduct a full content audit — headings and content are broadly misaligned"
        )

    return PageSemanticScore(
        url=url,
        overall_score=overall_score,
        section_scores=section_scores,
        finding=finding,
        recommendation=recommendation,
    )


def score_semantic(page_scores: list[PageSemanticScore]) -> SemanticScoreResult:
    scores = [page_score.overall_score for page_score in page_scores]

    all_findings = []
    all_recommendations = []

    for page in page_scores:
        if page.finding:
            all_findings.append(page.finding)
        if page.recommendation:
            all_recommendations.append(page.recommendation)

    top_findings = [finding for finding, _ in Counter(all_findings).most_common(5)]
    top_recommendations = [
        recommendation
        for recommendation, _ in Counter(all_recommendations).most_common(5)
    ]

    return SemanticScoreResult(
        overall_score=round(sum(scores) / len(scores)) if scores else 0,
        page_scores=page_scores,
        top_findings=top_findings,
        top_recommendations=top_recommendations,
    )
