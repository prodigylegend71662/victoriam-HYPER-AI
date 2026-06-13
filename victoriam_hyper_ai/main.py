#!/usr/bin/env python3
"""Main orchestration layer for VICTORIAM HYPER AI."""

from typing import Dict, Any

from victoriam_hyper_ai.clustering_layer import cluster_facts
from victoriam_hyper_ai.fact_layer import extract_facts
from victoriam_hyper_ai.math_wrapper import evaluate as evaluate_math
from victoriam_hyper_ai.output_layer import format_output
from victoriam_hyper_ai.router import route_query
from victoriam_hyper_ai.source_layer import collect_sources
from victoriam_hyper_ai.structure_layer import build_paragraph_answer


def run(query: str, include_youtube: bool = False) -> Dict[str, Any]:
    route = route_query(query)
    if route == "math":
        return {"query": query, "answer": evaluate_math(query), "route": "math"}

    documents = collect_sources(query, include_youtube=include_youtube)
    facts = extract_facts(documents, query)
    clusters = cluster_facts(facts)
    structured_answer = build_paragraph_answer(clusters, query)
    output = format_output(query=query, clusters=clusters, facts=facts, documents=documents, structured_answer=structured_answer)
    output["route"] = "research"
    return output


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
