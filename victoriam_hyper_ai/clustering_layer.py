#!/usr/bin/env python3
"""Clustering layer for grouping facts into semantic clusters."""

from dataclasses import dataclass, field
from typing import Dict, List

from victoriam_hyper_ai.fact_layer import FactRecord

CATEGORY_KEYWORDS = {
    "Politics": ["government", "political", "election", "policy", "state", "president", "minister", "law", "parliament"],
    "History": ["history", "historic", "war", "treaty", "revolution", "founded", "established", "origin", "ancient", "empire"],
    "Science": ["science", "research", "technology", "study", "algorithm", "physics", "biology", "chemistry", "medical", "innovation"],
    "Culture": ["culture", "art", "music", "film", "literature", "society", "media", "tradition", "language"],
    "Sports": ["sport", "team", "league", "championship", "athlete", "coach", "season", "match"],
}


@dataclass
class ClusterRecord:
    cluster: str
    facts: List[FactRecord] = field(default_factory=list)
    score: float = 0.0


def tokenize(text: str) -> List[str]:
    return [token for token in text.lower().split() if token.isalnum()]


def sentence_similarity(a: str, b: str) -> float:
    tokens_a = set(tokenize(a))
    tokens_b = set(tokenize(b))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def detect_cluster_label(sentence: str) -> str:
    text = sentence.lower()
    for label, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return label
    return "General"


def cluster_facts(facts: List[FactRecord]) -> List[ClusterRecord]:
    clusters: Dict[str, ClusterRecord] = {}
    for fact in facts:
        label = detect_cluster_label(fact.sentence)
        cluster = clusters.setdefault(label, ClusterRecord(cluster=label))
        if any(sentence_similarity(fact.sentence, existing.sentence) >= 0.7 for existing in cluster.facts):
            continue
        cluster.facts.append(fact)

    for cluster in clusters.values():
        cluster.score = sum(fact.score for fact in cluster.facts) / max(1, len(cluster.facts))
    sorted_clusters = sorted(clusters.values(), key=lambda item: item.score, reverse=True)
    if not sorted_clusters:
        sorted_clusters.append(ClusterRecord(cluster="General", facts=[]))
    return sorted_clusters
