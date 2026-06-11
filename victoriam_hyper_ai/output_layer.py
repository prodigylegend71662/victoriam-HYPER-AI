#!/usr/bin/env python3
"""Output layer that formats final research results."""

from typing import Any, Dict, List

from clustering_layer import ClusterRecord
from fact_layer import FactRecord
from source_layer import SourceDocument


def build_source_summary(documents: List[SourceDocument]) -> List[Dict[str, Any]]:
    summary: Dict[str, Dict[str, Any]] = {}
    for doc in documents:
        if doc.source not in summary:
            summary[doc.source] = {"source": doc.source, "tier": doc.tier, "count": 0}
        summary[doc.source]["count"] += 1
    return list(summary.values())


def format_output(
    query: str,
    clusters: List[ClusterRecord],
    facts: List[FactRecord],
    documents: List[SourceDocument],
    structured_answer: str,
) -> Dict[str, Any]:
    answer = structured_answer.strip()
    if not answer:
        answer = "No sufficiently relevant information could be found for this query."
    return {
        "query": query,
        "answer": answer,
    }
