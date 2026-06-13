import re
from typing import Literal

MathRoute = Literal["math", "research", "other"]

MATH_KEYWORDS = [
    "sqrt",
    "square root",
    "divide",
    "divided by",
    "multiply",
    "multiplied by",
    "times",
    "plus",
    "minus",
    "solve",
    "^",
    "power",
    "exponent",
]

MATH_OPERATOR_PATTERN = re.compile(r"\d+\s*[\+\-\*/\^]\s*\d+")
VARIABLE_OPERATOR_PATTERN = re.compile(r"\b[a-zA-Z]+\s*[\+\-\*/\^]\s*[a-zA-Z0-9]+\b")
EQUATION_PATTERN = re.compile(r"=")


def contains_math_keyword(text: str) -> bool:
    lower = text.lower()
    for token in MATH_KEYWORDS:
        if token in lower:
            return True
    return False


def route_query(text: str) -> MathRoute:
    """Classify the input as math, research, or other."""
    if not isinstance(text, str):
        return "other"

    query = text.strip()
    if not query:
        return "other"

    lower = query.lower()

    # Prioritize any clear math syntax or equation
    if MATH_OPERATOR_PATTERN.search(lower) or "^" in lower:
        return "math"
    if VARIABLE_OPERATOR_PATTERN.search(lower) or EQUATION_PATTERN.search(lower):
        return "math"

    # Keywords are a weaker signal, but still route to math if present.
    if contains_math_keyword(lower):
        return "math"

    return "research"
