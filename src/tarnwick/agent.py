"""`tarnwick agent CUSTOMER MESSAGE`: a support agent with the knowledge
graph as its tools and its memory (Chapter 20).

Each step, the model sees the customer's message, the tools the MCP server
offers, and every step taken so far, and chooses one thing to do: call a
tool or reply. Tool calls go to the server through the protocol. The loop
stops at a reply, or after MAX_STEPS steps.

Nothing is carried from one conversation to the next except what the agent
wrote with record_contact. That is the agent's memory: support tickets in
the graph's own terms, checked before they were written.
"""

import json

from .llm import ask
from .mcp import Client

MAX_STEPS = 8
WIDTH = 74

INSTRUCTIONS = (
    "You are the customer support assistant for Tarnwick Supply, an "
    "outdoor gear retailer. You can call tools on Tarnwick's knowledge "
    "graph. Use them to find facts, and never state a fact about an "
    "order, a product or a policy that a tool has not given you. When a "
    "customer reports a problem with a product, record the contact with "
    "record_contact before you reply, so that a later conversation can "
    "find it. Choose one step at a time: call a tool, or reply to the "
    "customer when you have what you need. Keep replies brief and plain.")

ARGS = ("customer", "order", "sku", "problem", "summary")


def schema(names):
    return {"type": "object", "additionalProperties": False,
            "required": ["action", "tool", "arguments", "reply"],
            "properties": {
                "action": {"type": "string", "enum": ["call", "reply"]},
                "tool": {"type": "string", "enum": [*names, "none"]},
                "arguments": {"type": "object", "additionalProperties": False,
                              "required": list(ARGS),
                              "properties": {a: {"type": "string"} for a in ARGS}},
                "reply": {"type": "string"}}}


def describe(tool_list):
    return "\n".join(f"{t['name']}({', '.join(t['inputSchema']['required'])}): "
                     f"{t['description']}" for t in tool_list)


def prompt(tool_list, customer, message, steps):
    """What the model reads at each step."""
    done = "\n".join(
        f"{n}. called {s['tool']} {json.dumps(s['arguments'])}\n"
        f"   result: {s['result']}" for n, s in enumerate(steps, 1))
    return (f"Tools:\n{describe(tool_list)}\n\n"
            f"The customer is signed in as {customer}.\n"
            f"Customer: {message}\n\n"
            f"Steps so far:\n{done or 'none'}\n\n"
            "What is your next step?")


def run(customer, message):
    """The steps the agent took and its reply."""
    client = Client()
    try:
        tool_list = client.tools()
        names = [t["name"] for t in tool_list]
        need = {t["name"]: t["inputSchema"]["required"]
                for t in tool_list}
        steps = []
        for _ in range(MAX_STEPS):
            text = prompt(tool_list, customer, message, steps)
            choice = ask(INSTRUCTIONS, text, schema=schema(names),
                         max_output_tokens=1500)
            if choice["action"] == "reply" or choice["tool"] == "none":
                return steps, choice["reply"]
            tool = choice["tool"]
            args = {k: v for k, v in choice["arguments"].items()
                    if k in need[tool]}
            result, failed = client.call(tool, args)
            steps.append({"tool": tool, "arguments": args,
                          "result": result, "failed": failed})
        return steps, "(The agent stopped after the most steps allowed.)"
    finally:
        client.close()


def report(customer, message):
    from textwrap import wrap
    steps, reply = run(customer, message)
    out = []
    for n, s in enumerate(steps, 1):
        args = ", ".join(f"{k}={v}" for k, v in s["arguments"].items())
        out += wrap(f"{n}. {s['tool']}({args})", WIDTH, subsequent_indent="     ")
        for line in s["result"].split("\n"):
            out += wrap(line, WIDTH, initial_indent="   ", subsequent_indent="     ")
    out.append("")
    out.append("Reply:")
    for para in reply.strip().split("\n"):
        out += wrap(para, WIDTH, initial_indent="  ", subsequent_indent="  ") or [""]
    return "\n".join(out)
