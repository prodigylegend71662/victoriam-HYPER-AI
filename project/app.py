from flask import Flask, request, jsonify, render_template
import os
import sys

# Ensure parent workspace root is importable so local packages can be used
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

# Try to import victoriam_hyper_ai pipeline
try:
    import importlib
    vh_main = importlib.import_module('victoriam_hyper_ai.main')
except Exception:
    vh_main = None

SYSTEM_IDENTITY = {
    "name": "Victoriam Hyper AI",
    "type": "Structured research and article-generation engine",
    "purpose": "Convert user queries into clean, encyclopedia-style responses",
    "style": "Neutral, factual, structured paragraphs",
}

app = Flask(__name__, template_folder="templates", static_folder="static")


def fallback_response(text: str) -> str:
    """Simple fallback encyclopedia-style reply when the local engine is unavailable."""
    token = text.strip() or "The query"
    return f"{token.capitalize()} is a topic with notable aspects; specific details require a focused query. Please ask about a particular aspect or include clarifying parentheses for disambiguation."


def generate_response(text: str, system: dict | None = None) -> tuple[str, str, dict]:
    """Generate a response using victoriam_hyper_ai if available, otherwise use fallback logic.

    The local `victoriam_hyper_ai.run(query, system=...)` returns a dict with an `answer` string.
    """
    if not text or not isinstance(text, str):
        return "No sufficiently relevant information could be found for this query.", "other", system or SYSTEM_IDENTITY

    if vh_main is None:
        return fallback_response(text), "other", system or SYSTEM_IDENTITY

    try:
        try:
            result = vh_main.run(text, system=system)
        except TypeError:
            result = vh_main.run(text)

        if isinstance(result, dict):
            answer = result.get("answer") or result.get("structured_answer") or result.get("summary")
            route = result.get("route", "research")
            returned_system = result.get("system", system or SYSTEM_IDENTITY)
            if answer:
                return answer, route, returned_system
        return fallback_response(text), "other", system or SYSTEM_IDENTITY
    except Exception:
        return fallback_response(text), "other", system or SYSTEM_IDENTITY


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "")
    system = data.get("system") or SYSTEM_IDENTITY
    response, route, returned_system = generate_response(text, system=system)
    return jsonify({"result": response, "route": route, "system": returned_system})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
