from flask import Flask, request, jsonify, render_template
import os
import sys

# Ensure parent workspace root is importable so local packages can be used
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

# Try to import victoriam_hyper_ai pipeline
PACKAGE_DIR = os.path.join(ROOT, 'victoriam_hyper_ai')
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)
try:
    import importlib
    vh_main = importlib.import_module('main')
except Exception:
    vh_main = None

app = Flask(__name__, template_folder="templates", static_folder="static")


def fallback_response(text: str) -> str:
    """Simple fallback encyclopedia-style reply when the local engine is unavailable."""
    token = text.strip() or "The query"
    return f"{token.capitalize()} is a topic with notable aspects; specific details require a focused query. Please ask about a particular aspect or include clarifying parentheses for disambiguation."


def generate_response(text: str) -> str:
    """Generate a response using victoriam_hyper_ai if available, otherwise use fallback logic.

    The local `victoriam_hyper_ai.run(query)` returns a dict with an `answer` string.
    """
    if not text or not isinstance(text, str):
        return "No sufficiently relevant information could be found for this query."

    if vh_main is None:
        return fallback_response(text)

    try:
        result = vh_main.run(text)
        if isinstance(result, dict):
            # prefer 'answer' then 'structured_answer' then 'summary'
            answer = result.get("answer") or result.get("structured_answer") or result.get("summary")
            if answer:
                return answer
        # if unexpected result, fall back
        return fallback_response(text)
    except Exception:
        return fallback_response(text)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "")
    response = generate_response(text)
    return jsonify({"result": response})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
