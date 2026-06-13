from victoriam_hyper_ai.router import route_query
from victoriam_hyper_ai.math_wrapper import evaluate as evaluate_math


def test_math_routing():
    cases = [
        ("1+1", "math"),
        ("2*3", "math"),
        ("100 divided by 2", "math"),
        ("square root of 2", "math"),
        ("x + 2 = 5", "math"),
        ("what is canada", "research"),
        ("history of france", "research"),
    ]

    for text, expected in cases:
        assert route_query(text) == expected, f"{text} should route to {expected}"


def test_math_evaluate():
    cases = [
        ("1+1", "2"),
        ("2*3", "6"),
        ("100 divided by 2", "50.0"),
        ("square root of 2", str(2 ** 0.5)),
    ]

    for text, expected in cases:
        result = evaluate_math(text)
        assert expected in result, f"{text} should evaluate to {expected}, got {result}"


if __name__ == "__main__":
    test_math_routing()
    test_math_evaluate()
    print("All router tests passed.")
