#!/usr/bin/env python3
"""Main orchestration layer for VICTORIAM HYPER AI."""

from typing import Dict, Any

from clustering_layer import cluster_facts
from fact_layer import extract_facts
from output_layer import format_output
from source_layer import collect_sources
from structure_layer import build_paragraph_answer


def run(query: str, include_youtube: bool = False) -> Dict[str, Any]:
    documents = collect_sources(query, include_youtube=include_youtube)
    facts = extract_facts(documents, query)
    clusters = cluster_facts(facts)
    structured_answer = build_paragraph_answer(clusters, query)
    return format_output(query=query, clusters=clusters, facts=facts, documents=documents, structured_answer=structured_answer)


def chat() -> None:
    print("VICTORIAM HYPER AI")
    print("Enter a research query or /quit to exit.")
    while True:
        query = input("> ").strip()
        if not query:
            continue
        if query.lower() in {"/quit", "quit", "exit"}:
            break
        try:
            response = run(query)
            print(response["answer"])
        except Exception as error:
            print(f"Error: {error}")


if __name__ == "__main__":
    chat()
