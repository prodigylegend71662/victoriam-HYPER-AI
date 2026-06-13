import math
import os
import re
import subprocess
import sys
from typing import Optional

SCRIPT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "mathtool", "mathtool.py")
)

NORMALIZATION_RULES = [
    (r"\bdivided by\b", "/"),
    (r"\bdivide\b", "/"),
    (r"\bmultiplied by\b", "*"),
    (r"\bmultiply by\b", "*"),
    (r"\btimes\b", "*"),
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"\bsquare root of\b", "sqrt "),
    (r"\bsquare root\b", "sqrt "),
    (r"\bsqrt\s*\(", "sqrt("),
    (r"\bsqrt\b", "sqrt"),
]

SIMPLE_EQUATION_PATTERN = re.compile(r"^\s*([a-zA-Z])\s*([+\-*/^])\s*([0-9.]+)\s*=\s*([0-9.]+)\s*$")
REVERSE_EQUATION_PATTERN = re.compile(r"^\s*([0-9.]+)\s*([+\-*/^])\s*([a-zA-Z])\s*=\s*([0-9.]+)\s*$")


def _normalize_expression(input_text: str) -> str:
    text = input_text.lower().strip()
    for pattern, replacement in NORMALIZATION_RULES:
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"[^0-9a-zA-Z+\-*/^().= ]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _solve_simple_linear_equation(expression: str) -> Optional[float]:
    normalized = expression.replace(" ", "")
    if match := SIMPLE_EQUATION_PATTERN.match(normalized):
        _, op, number, total = match.groups()
        number = float(number)
        total = float(total)
        if op == "+":
            return total - number
        if op == "-":
            return total + number
        if op == "*":
            return total / number if number != 0 else None
        if op == "/":
            return total * number
        if op == "^":
            return total ** (1 / number) if number != 0 else None

    if match := REVERSE_EQUATION_PATTERN.match(normalized):
        left, op, variable, total = match.groups()
        left = float(left)
        total = float(total)
        if op == "+":
            return total - left
        if op == "-":
            return total + left
        if op == "*":
            return total / left if left != 0 else None
        if op == "/":
            return total * left
        if op == "^":
            return math.pow(total, 1 / left) if left != 0 else None

    return None


def _run_math_script(expression: str) -> Optional[str]:
    if not os.path.exists(SCRIPT_PATH):
        return None

    try:
        process = subprocess.run(
            [sys.executable, SCRIPT_PATH],
            input=f"{expression}\n",
            capture_output=True,
            text=True,
            timeout=6,
        )
    except subprocess.SubprocessError:
        return None

    for line in process.stdout.splitlines():
        if "Answer:" in line:
            return line.split("Answer:", 1)[1].strip()

    return None


def evaluate(input_text: str) -> str:
    """Evaluate a math query, returning the result as a string."""
    normalized = _normalize_expression(input_text)

    if "sqrt" in normalized:
        match = re.search(r"sqrt\s*\(?\s*([0-9.]+)\s*\)?", normalized)
        if match:
            number = float(match.group(1))
            return str(math.sqrt(number))

    if "=" in normalized and re.search(r"[a-zA-Z]", normalized):
        solved = _solve_simple_linear_equation(normalized)
        if solved is not None:
            return str(solved)

    if "=" in normalized and not re.search(r"[a-zA-Z]", normalized):
        left, right = normalized.split("=", 1)
        if left and right:
            left_result = evaluate(left)
            right_result = evaluate(right)
            if left_result is not None and right_result is not None:
                return f"{left_result} = {right_result}"

    if normalized:
        result = _run_math_script(normalized)
        if result is not None:
            return result

    return "Could not evaluate the math expression."
