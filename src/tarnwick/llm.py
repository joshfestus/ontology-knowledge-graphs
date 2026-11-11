"""Calling a language model, for Chapters 1, 16 and 18 to 22.

Any service that speaks the OpenAI API works, including a free model run on
your own computer: set TARNWICK_LLM_BASE_URL to its address and
TARNWICK_LLM_MODEL to its name. The book's printed results came from
OpenAI's gpt-5.6-luna.

Three habits keep the results honest and the cost known.

Every answer is saved in llm-cache/, keyed by the model, the instructions
and the input, and the same request is never sent twice. The companion
files ship with the cache, so a reader can reproduce every printed result
without an account or any cost.

Every call's cost is worked out from the token counts the service reports
and added to llm-cache/spend.json.

A budget, TARNWICK_LLM_BUDGET dollars (1.00 unless set), is never exceeded:
before each call, the most it could cost is added to what has been spent,
and the call is refused if that would pass the budget.
"""

import hashlib
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "llm-cache"
LEDGER = CACHE / "spend.json"
KEY_FILE = Path.home() / ".config" / "tarnwick" / "openai.env"
DEFAULT_MODEL = "gpt-5.6-luna"

# US dollars per million tokens: (input, cached input, output). Checked on
# OpenAI's model pages, 10 November 2026.
PRICES = {"gpt-5.6-luna": (0.20, 0.02, 1.20)}


class BudgetExceeded(Exception):
    pass


def model_name():
    return os.environ.get("TARNWICK_LLM_MODEL", DEFAULT_MODEL)


def budget():
    return float(os.environ.get("TARNWICK_LLM_BUDGET", "1.00"))


def api_key():
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    if KEY_FILE.exists():
        for line in KEY_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def spent():
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))["total_usd"]
    return 0.0


def record(cost, model, usage):
    data = {"total_usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0}
    if LEDGER.exists():
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
    data["total_usd"] = round(data["total_usd"] + cost, 6)
    data["calls"] += 1
    data["input_tokens"] += usage["input_tokens"]
    data["output_tokens"] += usage["output_tokens"]
    data["model"] = model
    LEDGER.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def cost_of(model, input_tokens, cached_tokens, output_tokens):
    if model not in PRICES:
        return 0.0          # a local model costs nothing
    inp, cached, out = PRICES[model]
    return ((input_tokens - cached_tokens) * inp + cached_tokens * cached
            + output_tokens * out) / 1_000_000


def key_for(model, instructions, text, schema, max_output_tokens, run=1):
    parts = [model, instructions, text, schema, max_output_tokens]
    if run != 1:
        parts.append(f"run {run}")      # a repeat of the same request
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def ask(instructions, text, schema=None, max_output_tokens=1200, effort="low",
        run=1, details=False):
    """The model's answer to `text`, following `instructions`.

    With a JSON schema, the answer is parsed JSON that fits it; otherwise
    it is plain text. A saved answer is returned without calling anyone.
    A run number above 1 asks the same question again as a separate
    request, to see how much the answers move. With details, the saved
    record comes back too: tokens, cost and seconds taken."""
    model = model_name()
    CACHE.mkdir(exist_ok=True)
    key = key_for(model, instructions, text, schema, max_output_tokens, run)
    path = CACHE / f"{key}.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        return (saved["answer"], saved) if details else saved["answer"]

    # the most this call could cost: every input word a token, at most
    # max_output_tokens back
    worst = cost_of(model, (len(instructions) + len(text)) // 2, 0, max_output_tokens)
    if spent() + worst > budget():
        raise BudgetExceeded(
            f"This call could cost up to ${worst:.4f}, and ${spent():.4f} of the "
            f"${budget():.2f} budget is spent. Raise TARNWICK_LLM_BUDGET to continue.")

    from openai import OpenAI
    client = OpenAI(api_key=api_key() or "not-needed",
                    base_url=os.environ.get("TARNWICK_LLM_BASE_URL") or None)
    request = {"model": model, "instructions": instructions, "input": text,
               "max_output_tokens": max_output_tokens, "store": False}
    if model in PRICES:
        request["reasoning"] = {"effort": effort}
    if schema is not None:
        request["text"] = {"format": {"type": "json_schema", "name": "answer",
                                      "schema": schema, "strict": True}}
    started = time.monotonic()
    response = client.responses.create(**request)
    seconds = time.monotonic() - started
    usage = response.usage
    cached = getattr(usage.input_tokens_details, "cached_tokens", 0) or 0
    cost = cost_of(model, usage.input_tokens, cached, usage.output_tokens)
    record(cost, model, {"input_tokens": usage.input_tokens,
                         "output_tokens": usage.output_tokens})
    answer = response.output_text
    if schema is not None:
        answer = json.loads(answer)
    saved = {"model": model, "instructions": instructions,
             "input": text, "answer": answer,
             "input_tokens": usage.input_tokens,
             "cached_tokens": cached,
             "output_tokens": usage.output_tokens,
             "cost_usd": round(cost, 6), "seconds": round(seconds, 2)}
    if run != 1:
        saved["run"] = run
    path.write_text(json.dumps(saved, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return (answer, saved) if details else answer


def spend_report():
    s = spent()
    return f"Spent ${s:.4f} of the ${budget():.2f} budget on {model_name()}."
