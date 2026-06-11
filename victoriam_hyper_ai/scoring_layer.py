#!/usr/bin/env python3
"""Scoring layer for keyword, entity, tier, and agreement scoring."""

import re
from typing import List, Set

from source_layer import TIER_WEIGHTS


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def keyword_overlap(sentence_tokens: Set[str], query_tokens: Set[str]) -> float:
    if not query_tokens:
        return 0.0
    return len(sentence_tokens & query_tokens) / len(query_tokens)


def entity_overlap(sentence_tokens: Set[str], entity_tokens: Set[str]) -> float:
    if not entity_tokens:
        return 0.0
    return len(sentence_tokens & entity_tokens) / len(entity_tokens)


def cross_source_agreement(support_count: int) -> float:
    return min(0.3, 0.08 * support_count)


def max_tier_weight(source_tiers: List[int]) -> float:
    if not source_tiers:
        return TIER_WEIGHTS[4]
    return max(TIER_WEIGHTS.get(tier, 0.2) for tier in source_tiers)


def extract_entities_from_text(text: str) -> Set[str]:
    matches = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
    entities = {match.lower() for match in matches if len(match) > 3}
    return entities


def score_fact(sentence: str, query_tokens: Set[str], entity_tokens: Set[str], source_tiers: List[int], support_count: int) -> float:
    sentence_tokens = set(tokenize(sentence))
    keyword_score = keyword_overlap(sentence_tokens, query_tokens)
    entity_score = entity_overlap(sentence_tokens, entity_tokens)
    tier_score = max_tier_weight(source_tiers)
    agreement = cross_source_agreement(support_count)
    score = 0.4 * keyword_score + 0.25 * entity_score + 0.25 * tier_score + agreement
    return min(score, 1.0)
