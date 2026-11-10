"""`tarnwick chat QUESTION [--files NAME...]`: ask a language model about
Tarnwick (Chapter 1).

Without files, the model has only what it learned in training, which
includes nothing about Tarnwick. With files, the named spreadsheets from
data/ are pasted into the request exactly as they are, the way a person
would paste them into a chatbot. Neither way gives the model what the files
mean, which is the point Chapter 1 makes.
"""

import textwrap
from pathlib import Path

from .llm import ask

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
WIDTH = 74

INSTRUCTIONS = ("You are an assistant answering questions about a company called "
                "Tarnwick Supply. Answer briefly, in plain sentences.")


def context(names):
    parts = []
    for name in names:
        path = DATA / name
        if not path.exists():
            raise FileNotFoundError(f"No file called {name} in data/")
        parts.append(f"File {name}:\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


def report(question, files=()):
    text = question if not files else (
        f"{context(files)}\n\nUsing the files above, answer this question: {question}")
    answer = ask(INSTRUCTIONS, text, max_output_tokens=1500)
    lines = []
    for para in answer.strip().split("\n"):
        lines += textwrap.wrap(para, WIDTH) or [""]
    return "\n".join(lines)
