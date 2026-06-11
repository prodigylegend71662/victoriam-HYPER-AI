#!/usr/bin/env python3
"""
VICTORIAM HYPER AI
Hybrid research engine combining paragraph relevance, multi-source fusion,
entity-aware extraction, fact verification, and adaptive structured output.
"""

import requests
import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SOURCE_WEIGHTS = {"wikipedia": 1.0, "duckduckgo": 0.8, "openalex": 0.9}
MAX_SEARCH_TERMS = 8
MAX_PAGES = 40
MAX_FACTS = 80
MAX_SUMMARY_SENTENCES = 7
MAX_OUTPUT_CHARS = 3200
MIN_FACT_WORDS = 7
RELEVANCE_THRESHOLD = 0.08
ENTITY_WINDOW = 3


@dataclass
class Page:
    title: str
    text: str
    source: str
    url: str
    relevance: float = 0.0
    score: float = 0.0
    accepted: bool = False


@dataclass
class Fact:
    sentence: str
    sources: List[str] = field(default_factory=list)
    source_names: List[str] = field(default_factory=list)
    support: int = 0
    confidence: float = 0.0
    entities: List[str] = field(default_factory=list)


@dataclass
class GraphNode:
    entity: str
    type: str
    mentions: int = 0
    confidence: float = 0.0
    connected: List[str] = field(default_factory=list)


@dataclass
class ResearchAnalytics:
    pages_searched: int = 0
    pages_accepted: int = 0
    facts_extracted: int = 0
    entities_discovered: int = 0
    graph_nodes_created: int = 0
    source_distribution: Dict[str, int] = field(default_factory=dict)


# =========================================================
# NETWORK / SAFE IO
# =========================================================


def safe_get(url: str, timeout: int = 8) -> Optional[str]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        if response.status_code != 200:
            return None
        return response.text
    except requests.RequestException:
        return None


def safe_get_json(url: str, timeout: int = 8) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        if response.status_code != 200:
            return None
        return response.json()
    except (requests.RequestException, ValueError):
        return None


# =========================================================
# TEXT UTILITIES
# =========================================================


def normalize(text: str) -> str:
    if not isinstance(text, str):
        text = str(text) if text else ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def split_sentences(text: str) -> List[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def split_paragraphs(text: str) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    return [p for p in paragraphs if len(tokenize(p)) >= 8]


def normalize_sentence(sentence: str) -> str:
    return " ".join(tokenize(sentence))


def sentence_similarity(a: str, b: str) -> float:
    tokens_a = set(tokenize(a))
    tokens_b = set(tokenize(b))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))


def extract_entities(text: str, limit: int = 30) -> List[str]:
    candidates = re.findall(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", text)
    filtered = []
    stopwords = {
        "The", "A", "An", "In", "On", "Of", "And", "For", "With",
        "From", "To", "By", "At", "Or", "As", "Is", "Was", "Are"
    }
    for token in candidates:
        if token in stopwords:
            continue
        if len(token) < 4:
            continue
        if token.isupper():
            continue
        filtered.append(token)
    counted = Counter(filtered)
    return [item for item, _ in counted.most_common(limit)]


def detect_query_type(query: str) -> str:
    text = query.lower()
    if any(keyword in text for keyword in [" who ", " born ", " died ", " inventor", " president", " king", " queen", " author", " artist", "scientist", "actor", "leader"]):
        return "Person"
    if any(keyword in text for keyword in [" war ", " battle ", " revolution ", " invasion ", " treaty", " massacre", " uprising", " campaign", " coup"]):
        return "Historical Event"
    if any(keyword in text for keyword in [" university", " company", " corporation", " organization", " agency", " institute", " party", " foundation"]):
        return "Organization"
    if any(keyword in text for keyword in [" science", " technology", " physics", " chemistry", " biology", " algorithm", " machine learning", " quantum", " medicine", " AI", " software"]):
        return "Scientific Topic"
    if any(keyword in text for keyword in [" country", " nation", " state", " republic", " kingdom", " empire", " city", " region"]):
        return "Country"
    return "General"


def guess_section_titles(query_type: str) -> List[str]:
    templates = {
        "Country": ["Overview", "Geography", "Government", "Economy", "Modern Issues"],
        "Person": ["Overview", "Early Life", "Career", "Achievements", "Legacy"],
        "Historical Event": ["Background", "Causes", "Events", "Outcome", "Legacy"],
        "Organization": ["Overview", "History", "Structure", "Impact", "Current Status"],
        "Scientific Topic": ["Overview", "Key Concepts", "Applications", "Current Trends"],
        "General": ["Overview", "Key Details", "Context", "Impact"]
    }
    return templates.get(query_type, templates["General"])


def section_label(sentence: str, query_type: str) -> str:
    normalized = sentence.lower()
    if any(word in normalized for word in ["history", "formed", "founded", "established", "origin", "began", "created"]):
        return "History"
    if any(word in normalized for word in ["government", "leader", "policy", "administration", "state", "capital"]):
        return "Government"
    if any(word in normalized for word in ["economy", "market", "trade", "industry", "growth", "export"]):
        return "Economy"
    if any(word in normalized for word in ["career", "achievement", "award", "legacy", "notable", "known for"]):
        return "Achievements"
    if any(word in normalized for word in ["war", "conflict", "event", "battle", "campaign", "invasion"]):
        return "Events"
    if any(word in normalized for word in ["purpose", "because", "reason", "cause", "due to", "result"]):
        return "Causes"
    return "Overview"


def describe_confidence(value: float) -> str:
    if value >= 0.85:
        return "high"
    if value >= 0.6:
        return "medium"
    if value >= 0.35:
        return "low"
    return "weak"


# =========================================================
# SOURCE RETRIEVAL
# =========================================================


def wiki_search(query: str) -> List[str]:
    url = (
        "https://en.wikipedia.org/w/api.php"
        "?action=query&list=search&format=json"
        f"&srsearch={quote(query)}&srlimit=8"
    )
    data = safe_get_json(url)
    if not data:
        return []
    return [item.get("title", "") for item in data.get("query", {}).get("search", []) if item.get("title")]


def wiki_page(title: str) -> str:
    url = (
        "https://en.wikipedia.org/w/api.php"
        "?action=query&prop=extracts&explaintext=true&format=json"
        f"&titles={quote(title)}"
    )
    data = safe_get_json(url)
    if not data:
        return ""
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        extract = page.get("extract", "")
        return str(extract).strip() if extract else ""
    return ""


def ddg_search(query: str) -> List[Tuple[str, str]]:
    url = f"https://duckduckgo.com/html/?q={quote(query)}"
    html = safe_get(url)
    if not html:
        return []
    matches = re.findall(r"<a[^>]+class=\"result__a\"[^>]*>(.*?)</a>", html)
    titles = [re.sub(r"<[^>]+>", "", item).strip() for item in matches]
    return [(str(title), str(query)) for title in titles if title][:5]


def openalex_search(query: str) -> List[Tuple[str, str]]:
    url = f"https://api.openalex.org/works?search={quote(query)}&per-page=4"
    data = safe_get_json(url)
    if not data:
        return []
    works = data.get("results", [])
    output = []
    for item in works[:4]:
        title = str(item.get("display_name", "")).strip()
        abstract = item.get("abstract_inverted_index")
        if abstract and isinstance(abstract, dict):
            snippet = " ".join(abstract.keys())[:220]
        else:
            summary = item.get("summary", "")
            snippet = str(summary).strip() if isinstance(summary, str) else ""
        if not snippet:
            snippet = title
        output.append((title, str(snippet)[:250]))
    return output


def collect_pages(query: str, terms: List[str], analytics: ResearchAnalytics) -> List[Page]:
    pages: List[Page] = []
    seen = set()

    def add_page(title: str, text: str, source: str, url: str) -> None:
        normalized_title = title.lower().strip()
        if not text or normalized_title in seen:
            return
        seen.add(normalized_title)
        pages.append(Page(title=title, text=normalize(text), source=source, url=url))

    search_sources = ["wikipedia", "duckduckgo", "openalex"]
    for term in terms[:MAX_SEARCH_TERMS]:
        add_titles = []
        if "wikipedia" in search_sources:
            wiki_hits = wiki_search(term)
            analytics.pages_searched += len(wiki_hits)
            for title in wiki_hits[:6]:
                add_titles.append((title, "wikipedia", f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"))

        if "duckduckgo" in search_sources:
            ddg_hits = ddg_search(term)
            analytics.pages_searched += len(ddg_hits)
            for title, _ in ddg_hits:
                add_titles.append((title, "duckduckgo", f"https://duckduckgo.com/?q={quote(title)}"))

        if "openalex" in search_sources:
            openalex_hits = openalex_search(term)
            analytics.pages_searched += len(openalex_hits)
            for title, snippet in openalex_hits:
                add_page(title, snippet, "openalex", "https://openalex.org")

        for title, source, url in add_titles:
            if source == "wikipedia":
                text = wiki_page(title)
                add_page(title, text, source, url)
            else:
                snippet = title
                add_page(title, snippet, source, url)

        if len(pages) >= MAX_PAGES:
            break

    return pages


# =========================================================
# RANKING / RELEVANCE
# =========================================================


def paragraph_relevance(paragraph: str, query_tokens: set, entity_tokens: set) -> float:
    words = tokenize(paragraph)
    if len(words) < 8:
        return 0.0
    mentions = sum(1 for word in words if word in query_tokens or word in entity_tokens)
    if mentions == 0:
        return 0.0
    return mentions / len(words)


def page_relevance(page: Page, query_tokens: set, entity_tokens: set) -> float:
    paragraphs = split_paragraphs(page.text)
    if not paragraphs:
        return 0.0
    scores = [paragraph_relevance(p, query_tokens, entity_tokens) for p in paragraphs]
    average = sum(scores) / len(scores) if scores else 0.0
    title_bonus = 0.25 if any(token in page.title.lower() for token in query_tokens) else 0.0
    return average + title_bonus


def rank_pages(pages: List[Page], query_tokens: set, entity_tokens: set, analytics: ResearchAnalytics) -> List[Page]:
    for page in pages:
        relevance = page_relevance(page, query_tokens, entity_tokens)
        weight = SOURCE_WEIGHTS.get(page.source, 0.6)
        page.score = relevance * weight
        page.relevance = relevance
        page.accepted = relevance >= RELEVANCE_THRESHOLD
    accepted = [page for page in pages if page.accepted]
    accepted.sort(key=lambda p: p.score, reverse=True)
    analytics.pages_accepted = len(accepted)
    analytics.source_distribution = Counter(page.source for page in accepted)
    return accepted[:MAX_PAGES]


def expand_entities(query: str, pages: List[Page], analytics: ResearchAnalytics) -> List[str]:
    candidates = extract_entities(query)
    for page in pages[:10]:
        candidates.extend(extract_entities(page.text))
    counted = Counter(candidates)
    expansions = [item for item, _ in counted.most_common(MAX_SEARCH_TERMS) if item.lower() != query.lower()]
    analytics.entities_discovered = len(expansions)
    return expansions


# =========================================================
# FACT EXTRACTION / VERIFICATION
# =========================================================


def sentence_relevance(sentence: str, query_tokens: set, entity_tokens: set) -> float:
    words = tokenize(sentence)
    if len(words) < MIN_FACT_WORDS:
        return 0.0
    query_hits = sum(1 for word in words if word in query_tokens)
    entity_hits = sum(1 for word in words if word in entity_tokens)
    if query_hits == 0 and entity_hits == 0:
        return 0.0
    return (query_hits * 1.5 + entity_hits) / len(words)


def extract_facts(pages: List[Page], query_tokens: set, entity_tokens: set, analytics: ResearchAnalytics) -> List[Fact]:
    fact_map: Dict[str, Fact] = {}
    for page in pages:
        for sentence in split_sentences(page.text):
            text = normalize(sentence)
            if not text:
                continue
            score = sentence_relevance(text, query_tokens, entity_tokens)
            if score <= 0:
                continue
            norm = normalize_sentence(text)
            if len(norm.split()) < MIN_FACT_WORDS:
                continue
            if norm not in fact_map:
                fact_map[norm] = Fact(sentence=text, sources=[page.url], source_names=[page.source])
            else:
                fact_map[norm].sources.append(page.url)
                fact_map[norm].source_names.append(page.source)
    facts = list(fact_map.values())
    analytics.facts_extracted = len(facts)
    return facts


def deduplicate_facts(facts: List[Fact]) -> List[Fact]:
    unique: List[Fact] = []
    for fact in sorted(facts, key=lambda f: (-len(f.sources), -len(f.sentence))):
        if any(sentence_similarity(fact.sentence, existing.sentence) >= 0.7 for existing in unique):
            continue
        unique.append(fact)
        if len(unique) >= MAX_FACTS:
            break
    return unique


def verify_facts(facts: List[Fact], query_tokens: set, entity_tokens: set) -> List[Fact]:
    for fact in facts:
        fact.support = len(set(fact.source_names))
        entity_matches = [entity for entity in entity_tokens if entity in fact.sentence.lower()]
        base = min(1.0, 0.4 + 0.1 * fact.support)
        relevance_bonus = min(0.3, sum(1 for token in query_tokens if token in fact.sentence.lower()) * 0.02)
        entity_bonus = min(0.3, len(entity_matches) * 0.08)
        weight = Counter(fact.source_names)
        source_factor = min(1.0, sum(SOURCE_WEIGHTS.get(name, 0.6) * count for name, count in weight.items()) / 3)
        fact.confidence = min(1.0, base + relevance_bonus + entity_bonus) * source_factor
        fact.entities = entity_matches[:5]
    return sorted(facts, key=lambda f: (f.confidence, f.support, len(f.sources)), reverse=True)


# =========================================================
# KNOWLEDGE GRAPH
# =========================================================


def build_knowledge_graph(facts: List[Fact], analytics: ResearchAnalytics) -> List[GraphNode]:
    node_map: Dict[str, GraphNode] = {}
    edges: Dict[str, Counter] = defaultdict(Counter)
    for fact in facts[:MAX_FACTS]:
        entities = [entity for entity in fact.entities if len(entity) > 3]
        for entity in entities:
            if entity not in node_map:
                node_map[entity] = GraphNode(entity=entity, type="Entity", mentions=0, confidence=fact.confidence)
            node_map[entity].mentions += 1
            node_map[entity].confidence = max(node_map[entity].confidence, fact.confidence)
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                edges[entities[i]][entities[j]] += 1
                edges[entities[j]][entities[i]] += 1
    for entity, counter in edges.items():
        if entity in node_map:
            node_map[entity].connected = [other for other, _ in counter.most_common(5)]
    analytics.graph_nodes_created = len(node_map)
    return list(node_map.values())


# =========================================================
# SUMMARIZATION / STRUCTURING
# =========================================================


def paragraph_fusion(sentences: List[str]) -> str:
    paragraphs = []
    buffer: List[str] = []
    for sentence in sentences:
        buffer.append(sentence)
        if len(buffer) >= 3:
            paragraphs.append(" ".join(buffer))
            buffer = []
    if buffer:
        paragraphs.append(" ".join(buffer))
    result = "\n\n".join(paragraphs)
    return result[:MAX_OUTPUT_CHARS]


def summarize_facts(facts: List[Fact], query: str) -> str:
    top = [fact.sentence for fact in facts[:MAX_SUMMARY_SENTENCES]]
    return paragraph_fusion(top)


def build_sections(facts: List[Fact], query_type: str) -> List[Dict[str, str]]:
    sections: Dict[str, List[str]] = defaultdict(list)
    titles = guess_section_titles(query_type)
    for fact in facts:
        label = section_label(fact.sentence, query_type)
        sections[label].append(fact.sentence)
    output: List[Dict[str, str]] = []
    for title in titles:
        content_sentences = sections.get(title, [])
        if content_sentences:
            output.append({"title": title, "content": paragraph_fusion(content_sentences[:3])})
    if not output and facts:
        output.append({"title": "Overview", "content": paragraph_fusion([fact.sentence for fact in facts[:3]])})
    return output


def build_source_summary(pages: List[Page]) -> List[Dict[str, Any]]:
    counts = Counter(page.source for page in pages)
    return [{"source": source, "count": count, "weight": SOURCE_WEIGHTS.get(source, 0.6)} for source, count in counts.items()]


# =========================================================
# PIPELINE CONTROLLER
# =========================================================


def run(query: str, use_5w1h: bool = False) -> Dict[str, Any]:
    analytics = ResearchAnalytics()
    query_text = normalize(query)
    query_type = detect_query_type(query_text)
    query_tokens = set(tokenize(query_text))

    terms = [query_text] + [phrase for phrase in re.split(r"[,:;\-]", query_text) if phrase.strip()]
    terms = list(dict.fromkeys([term.strip() for term in terms if term.strip()]))[:MAX_SEARCH_TERMS]

    pages = collect_pages(query_text, terms, analytics)
    expansions = expand_entities(query_text, pages, analytics)
    expanded_terms = terms + expansions[:MAX_SEARCH_TERMS]

    pages = collect_pages(query_text, expanded_terms, analytics)
    entity_tokens = set(tokenize(" ".join(expansions)))

    ranked_pages = rank_pages(pages, query_tokens, entity_tokens, analytics)
    facts = extract_facts(ranked_pages, query_tokens, entity_tokens, analytics)
    facts = deduplicate_facts(facts)
    facts = verify_facts(facts, query_tokens, entity_tokens)

    if use_5w1h:
        facts = [fact for fact in facts if fact.confidence >= 0.2]

    graph = build_knowledge_graph(facts, analytics)
    summary = summarize_facts(facts, query_text)
    sections = build_sections(facts, query_type)
    source_summary = build_source_summary(ranked_pages)

    confidence_values = [fact.confidence for fact in facts] or [0.0]
    average_confidence = sum(confidence_values) / len(confidence_values)

    return {
        "query": query_text,
        "summary": summary,
        "sections": sections,
        "facts": [
            {
                "sentence": fact.sentence,
                "sources": fact.sources,
                "support": fact.support,
                "confidence": round(fact.confidence, 3),
                "entities": fact.entities,
            }
            for fact in facts[:MAX_FACTS]
        ],
        "sources": source_summary,
        "knowledge_graph": [
            {
                "entity": node.entity,
                "type": node.type,
                "mentions": node.mentions,
                "confidence": round(node.confidence, 3),
                "connected_entities": node.connected,
            }
            for node in graph
        ],
        "analytics": {
            "pages_searched": analytics.pages_searched,
            "pages_accepted": analytics.pages_accepted,
            "facts_extracted": analytics.facts_extracted,
            "entities_discovered": analytics.entities_discovered,
            "graph_nodes_created": analytics.graph_nodes_created,
            "source_distribution": dict(analytics.source_distribution),
        },
        "confidence": {
            "average": round(average_confidence, 3),
            "level": describe_confidence(average_confidence),
            "source_weights": SOURCE_WEIGHTS,
        },
        "error": False,
    }


# =========================================================
# COMMAND LINE / CHAT
# =========================================================


def chat() -> None:
    print("VICTORIAM HYPER AI")
    print("Type a query or /quit to exit.")
    while True:
        try:
            query = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not query:
            continue
        if query.lower() in {"/quit", "exit", "quit"}:
            break
        response = run(query)
        print("\n=== SUMMARY ===")
        print(response["summary"] or "No summary generated.")
        print("\n=== SECTIONS ===")
        for section in response["sections"]:
            print(f"\n{section['title']}:\n{section['content']}")
        print("\n=== SOURCE DISTRIBUTION ===")
        for source in response["sources"]:
            print(f"- {source['source']}: {source['count']} (weight {source['weight']})")
        print("\n=== CONFIDENCE ===")
        print(response["confidence"])
        print("\n=== ANALYTICS ===")
        print(response["analytics"])
        print()


if __name__ == "__main__":
    chat()
