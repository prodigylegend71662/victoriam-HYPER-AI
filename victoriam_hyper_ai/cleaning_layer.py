import re
from typing import List


def remove_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def remove_citations(text: str) -> str:
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"\([^\)]*\b\d{4}\b[^\)]*\)", " ", text)
    text = re.sub(r"\([^\)]*\b(?:et al|vol\.|Vol\.|pp\.|p\.)[^\)]*\)", " ", text)
    return text


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    text = remove_html(text)
    text = remove_citations(text)
    text = normalize_whitespace(text)
    return text
