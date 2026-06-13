#!/usr/bin/env python3
"""Structure layer that converts clusters into a coherent paragraph answer."""

import re
from dataclasses import dataclass
from typing import List, Set

from victoriam_hyper_ai.clustering_layer import ClusterRecord

QUESTION_WORDS = ["what", "who", "when", "where", "why", "how", "does", "do", "is", "are", "was", "were"]
STOPWORDS = {
    "in", "on", "at", "by", "for", "to", "from", "with", "and", "or", "not", "of", "the", "a", "an",
    "its", "that", "this", "these", "those", "as", "under", "about",
}
CONTROVERSY_KEYWORDS = [
    "controvers", "legal", "lawsuit", "investigation", "security", "breach", "critic", "criticism", "dispute",
    "accusation", "allegation", "regulation", "complaint", "penalty", "fine", "litigation", "settlement", "violation"
]


@dataclass
class QueryBranch:
    label: str
    include_phrases: List[str]
    exclude_phrases: List[str]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def tokenize(text: str) -> Set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def extract_entity_terms(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    phrases: List[str] = []
    parenthesized = re.findall(r"[^\n()]+\([^\n()]+\)", text)
    for phrase in parenthesized:
        phrases.append(phrase.strip())
    remainder = text
    for phrase in parenthesized:
        remainder = remainder.replace(phrase, " ")
    capitalized = re.findall(
        r"(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)|WW[0-9]+|[A-Z]{2,}|[0-9]+(?:st|nd|rd|th)?",
        remainder,
    )
    for token in capitalized:
        token = token.strip()
        if token:
            phrases.append(token)
    if not phrases:
        terms = [token for token in re.findall(r"[a-z0-9]+", text) if token not in STOPWORDS]
        phrases.extend(terms)
    return phrases


def parse_boolean_query(query: str) -> List[QueryBranch]:
    query = query.strip()
    if not query:
        return []
    branches: List[QueryBranch] = []
    or_segments = [segment.strip() for segment in re.split(r"(?i)\s+OR\s+", query) if segment.strip()]
    for segment in or_segments:
        tokens = re.split(r"(?i)\s+(AND|NOT)\s+", segment)
        include_phrases: List[str] = []
        exclude_phrases: List[str] = []
        current_op = "AND"
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            upper = token.upper()
            if upper in {"AND", "NOT"}:
                current_op = upper
                continue
            if current_op == "NOT":
                exclude_phrases.append(token)
            else:
                include_phrases.append(token)
            current_op = "AND"
        if (
            (not include_phrases)
            or (
                len(include_phrases) == 1
                and " " in include_phrases[0]
                and not re.search(r"(?i)\b(AND|NOT)\b", segment)
                and re.search(r"(?i)\b(in|during|of|between|for|on|at|with)\b", segment)
            )
        ):
            extracted = extract_entity_terms(segment)
            if extracted:
                include_phrases = extracted
        if not include_phrases:
            continue
        branches.append(QueryBranch(label=segment, include_phrases=include_phrases, exclude_phrases=exclude_phrases))
    return branches


def phrase_matches_sentence(sentence: str, phrase: str) -> bool:
    normalized_sentence = normalize_text(sentence)
    normalized_phrase = normalize_text(phrase)
    if normalized_phrase in normalized_sentence:
        return True
    if "(" in phrase and ")" in phrase:
        core, _, qualifier = phrase.partition("(")
        qualifier = qualifier.rstrip(")").strip()
        core_tokens = tokenize(normalize_text(core))
        qualifier_tokens = tokenize(normalize_text(qualifier))
        sentence_tokens = tokenize(normalized_sentence)
        if core_tokens and qualifier_tokens and core_tokens.issubset(sentence_tokens) and qualifier_tokens.issubset(sentence_tokens):
            return True
    sentence_tokens = tokenize(normalized_sentence)
    phrase_tokens = tokenize(normalized_phrase)
    if not phrase_tokens:
        return False
    return phrase_tokens.issubset(sentence_tokens)


def fact_matches_branch(sentence: str, branch: QueryBranch) -> bool:
    if branch.exclude_phrases and any(phrase_matches_sentence(sentence, phrase) for phrase in branch.exclude_phrases):
        return False
    return all(phrase_matches_sentence(sentence, phrase) for phrase in branch.include_phrases)


def build_branch_paragraph(branch: QueryBranch, sentences: List[str], is_multi_branch: bool) -> str:
    if not sentences:
        return ""
    if is_multi_branch:
        return " ".join(sentences)
    return " ".join(sentences)


def format_exclusion_paragraph(branches: List[QueryBranch]) -> str:
    exclusions: List[str] = []
    for branch in branches:
        for phrase in branch.exclude_phrases:
            if phrase not in exclusions:
                exclusions.append(phrase)
    if not exclusions:
        return ""
    if len(exclusions) == 1:
        return f"This summary excludes {exclusions[0]} to preserve focus on the selected topic."
    return "This summary excludes " + ", ".join(exclusions[:-1]) + " and " + exclusions[-1] + " to preserve focus on the selected topic."


def build_paragraph_answer(clusters: List[ClusterRecord], query: str, max_sentences: int = 4) -> str:
    branches = parse_boolean_query(query)
    if not branches:
        return "No sufficiently relevant information could be found for this query."

    paragraphs: List[str] = []
    is_multi_branch = len(branches) > 1
    for branch in branches:
        matched_sentences: List[str] = []
        for cluster in clusters:
            for fact in cluster.facts:
                sentence = fact.sentence.strip()
                if not sentence or sentence in matched_sentences:
                    continue
                if fact_matches_branch(sentence, branch):
                    matched_sentences.append(sentence)
                if len(matched_sentences) >= max_sentences:
                    break
            if len(matched_sentences) >= max_sentences:
                break
        if matched_sentences:
            paragraph = build_branch_paragraph(branch, matched_sentences, is_multi_branch)
            paragraphs.append(paragraph)

    exclusion = format_exclusion_paragraph(branches)
    if exclusion and paragraphs:
        paragraphs.append(exclusion)

    if not paragraphs:
        return "No sufficiently relevant information could be found for this query."

    answer = "\n\n".join(paragraphs).strip()
    answer = re.sub(r"[ \t]+", " ", answer)
    answer = re.sub(r"\n\s*\n+", "\n\n", answer)
    return answer.strip()
