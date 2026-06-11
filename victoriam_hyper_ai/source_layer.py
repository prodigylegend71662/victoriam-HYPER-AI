#!/usr/bin/env python3
"""Source layer for multi-source collection and tiered source weighting."""

import re
from dataclasses import dataclass
from typing import List, Optional, Set
from urllib.parse import quote

import requests

from cleaning_layer import clean_text

SOURCE_TIERS = {
    "wikipedia": 1,
    "wikidata": 1,
    "openalex": 2,
    "semantic_scholar": 2,
    "youtube": 3,
    "stackoverflow": 3,
    "mdn": 3,
    "duckduckgo": 4,
}

TIER_WEIGHTS = {
    1: 1.0,
    2: 0.7,
    3: 0.45,
    4: 0.2,
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


@dataclass
class SourceDocument:
    title: str
    text: str
    source: str
    url: str
    tier: int


def safe_get(url: str, timeout: int = 8) -> Optional[str]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        if response.status_code != 200:
            return None
        return response.text
    except requests.RequestException:
        return None


def safe_get_json(url: str, timeout: int = 8) -> Optional[dict]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        if response.status_code != 200:
            return None
        return response.json()
    except (requests.RequestException, ValueError):
        return None


def fetch_wikipedia(query: str) -> List[SourceDocument]:
    results: List[SourceDocument] = []
    search_url = (
        "https://en.wikipedia.org/w/api.php"
        "?action=query&list=search&format=json"
        f"&srsearch={quote(query)}&srlimit=5"
    )
    data = safe_get_json(search_url)
    if not data:
        return results

    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        if not title:
            continue
        page_url = (
            "https://en.wikipedia.org/w/api.php"
            "?action=query&prop=extracts&explaintext=true&format=json"
            f"&titles={quote(title)}"
        )
        page_data = safe_get_json(page_url)
        if not page_data:
            continue
        pages = page_data.get("query", {}).get("pages", {})
        for page in pages.values():
            extract = page.get("extract", "") or ""
            cleaned = clean_text(extract)
            if cleaned:
                results.append(SourceDocument(title=title, text=cleaned, source="wikipedia", url=f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}", tier=SOURCE_TIERS["wikipedia"]))
            break
    return results


def tokenize_text(text: str) -> Set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def is_document_relevant(doc: SourceDocument, query: str) -> bool:
    query_tokens = tokenize_text(query)
    if not query_tokens:
        return False
    doc_tokens = tokenize_text(f"{doc.title} {doc.text}")
    return bool(query_tokens & doc_tokens)


def fetch_wikidata(query: str) -> List[SourceDocument]:
    results: List[SourceDocument] = []
    search_url = (
        "https://www.wikidata.org/w/api.php"
        "?action=wbsearchentities&format=json&language=en"
        f"&search={quote(query)}&limit=4"
    )
    data = safe_get_json(search_url)
    if not data:
        return results

    for item in data.get("search", []):
        label = item.get("label", "")
        description = item.get("description", "")
        entity_id = item.get("id", "")
        if not label or not entity_id:
            continue
        text = clean_text(f"{label}. {description}")
        if text:
            results.append(SourceDocument(title=label, text=text, source="wikidata", url=f"https://www.wikidata.org/wiki/{quote(entity_id)}", tier=SOURCE_TIERS["wikidata"]))
    return results


def fetch_openalex(query: str) -> List[SourceDocument]:
    results: List[SourceDocument] = []
    api_url = f"https://api.openalex.org/works?search={quote(query)}&per-page=4"
    data = safe_get_json(api_url)
    if not data:
        return results
    for item in data.get("results", [])[:4]:
        title = item.get("display_name", "")
        abstract = item.get("abstract_inverted_index")
        snippet = ""
        if isinstance(abstract, dict):
            snippet = " ".join(abstract.keys())[:240]
        else:
            snippet = item.get("summary", "") or item.get("biblio", "") or ""
        if not isinstance(snippet, str):
            snippet = str(snippet)
        text = clean_text(f"{title}. {snippet}")
        if title and text:
            results.append(SourceDocument(title=title, text=text, source="openalex", url="https://openalex.org", tier=SOURCE_TIERS["openalex"]))
    return results


def fetch_semantic_scholar(query: str) -> List[SourceDocument]:
    results: List[SourceDocument] = []
    api_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote(query)}&limit=3&fields=title,abstract,url"
    data = safe_get_json(api_url)
    if not data:
        return results
    for item in data.get("data", [])[:3]:
        title = item.get("title", "")
        abstract = item.get("abstract", "")
        url = item.get("url", "https://www.semanticscholar.org")
        if not title:
            continue
        text = clean_text(f"{title}. {abstract}")
        if text:
            results.append(SourceDocument(title=title, text=text, source="semantic_scholar", url=url, tier=SOURCE_TIERS["semantic_scholar"]))
    return results


def fetch_duckduckgo(query: str) -> List[SourceDocument]:
    results: List[SourceDocument] = []
    page = safe_get(f"https://duckduckgo.com/html/?q={quote(query)}")
    if not page:
        return results
    snippets = re.findall(r"<a[^>]+class=\"result__a\"[^>]*>(.*?)</a>", page)
    for snippet in snippets[:5]:
        title = re.sub(r"<[^>]+>", "", snippet).strip()
        if title:
            text = clean_text(title)
            results.append(SourceDocument(title=title, text=text, source="duckduckgo", url=f"https://duckduckgo.com/?q={quote(title)}", tier=SOURCE_TIERS["duckduckgo"]))
    return results


def fetch_youtube_transcripts(query: str) -> List[SourceDocument]:
    return []


def collect_sources(query: str, include_youtube: bool = False) -> List[SourceDocument]:
    documents: List[SourceDocument] = []
    documents.extend(fetch_wikipedia(query))
    documents.extend(fetch_wikidata(query))
    documents.extend(fetch_openalex(query))
    documents.extend(fetch_semantic_scholar(query))
    if include_youtube:
        documents.extend(fetch_youtube_transcripts(query))
    unique = {}
    for doc in documents:
        key = (doc.title.lower().strip(), doc.source)
        if key not in unique and doc.text:
            unique[key] = doc
    filtered = [doc for doc in unique.values() if is_document_relevant(doc, query)]
    return filtered
