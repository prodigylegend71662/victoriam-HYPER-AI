#!/usr/bin/env python3
"""Fact extraction layer that selects relevant, source-backed sentences."""

from dataclasses import dataclass, field
from typing import Dict, List, Set

from victoriam_hyper_ai.cleaning_layer import split_sentences, clean_text
from victoriam_hyper_ai.scoring_layer import extract_entities_from_text, score_fact
from victoriam_hyper_ai.source_layer import SourceDocument

def sentence_matches_query(sentence: str, query_tokens: Set[str], query_entities: Set[str]) -> bool:
    sentence_tokens = set(sentence.lower().split())
    if sentence_tokens & query_tokens:
        return True
    if query_entities and any(entity in sentence.lower() for entity in query_entities):
        return True
    return False


@dataclass
class FactRecord:
    sentence: str
    normalized: str
    sources: List[str] = field(default_factory=list)
    source_tiers: List[int] = field(default_factory=list)
    support: int = 0
    score: float = 0.0
    entities: List[str] = field(default_factory=list)


def normalize_sentence(sentence: str) -> str:
    return " ".join([token for token in sentence.lower().split()]).strip()


def is_meaningful_sentence(sentence: str) -> bool:
    tokens = sentence.split()
    if len(tokens) < 8:
        return False
    lower = sentence.lower()
    filler_phrases = ["click here", "learn more", "subscribe", "follow", "advertisement", "copyright"]
    return not any(phrase in lower for phrase in filler_phrases)


def extract_facts(documents: List[SourceDocument], query: str) -> List[FactRecord]:
    query_tokens = set(query.lower().split())
    query_entities = extract_entities_from_text(query)
    candidate_map: Dict[str, FactRecord] = {}

    for doc in documents:
        for sentence in split_sentences(doc.text):
            cleaned = clean_text(sentence)
            if not cleaned or not is_meaningful_sentence(cleaned):
                continue
            normalized = normalize_sentence(cleaned)
            if not normalized:
                continue
            if not sentence_matches_query(normalized, query_tokens, query_entities):
                continue
            record = candidate_map.get(normalized)
            if not record:
                record = FactRecord(sentence=cleaned, normalized=normalized, sources=[doc.source], source_tiers=[doc.tier])
                candidate_map[normalized] = record
            else:
                if doc.source not in record.sources:
                    record.sources.append(doc.source)
                record.source_tiers.append(doc.tier)

    facts: List[FactRecord] = []
    for record in candidate_map.values():
        record.support = len(set(record.sources))
        record.entities = [entity for entity in query_entities if entity in record.normalized]
        record.score = score_fact(record.sentence, query_tokens, set(record.entities), record.source_tiers, record.support)
        if record.score < 0.28:
            continue
        if max(record.source_tiers) >= 3 and record.support < 2:
            continue
        facts.append(record)

    facts.sort(key=lambda fact: (fact.score, fact.support), reverse=True)
    return facts
