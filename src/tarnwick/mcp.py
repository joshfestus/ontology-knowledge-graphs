"""`tarnwick mcp`: the Tarnwick tools as a Model Context Protocol server
(Chapter 20).

MCP is an open protocol for offering tools and data to language model
applications. This server speaks revision 2026-07-28 over stdio: one JSON-RPC
2.0 message per line on standard input and output. That revision is
stateless, so every request carries its protocol version and the client's
capabilities in `_meta`, and the server answers each request on its own.
It implements the three methods a tool server needs: `server/discover`,
`tools/list` and `tools/call`.

The client half, `Client`, starts the server as a subprocess and sends it
requests. The agent in agent.py uses it, so the agent reaches the graph only
through the protocol, as it would reach any other MCP server.
"""

import json
import subprocess
import sys

from . import tools

VERSION = "2026-07-28"
META = "io.modelcontextprotocol/"
SERVER_INFO = {"name": "tarnwick", "version": "1.0"}


def error(id_, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": id_, "error": err}


def result(id_, body):
    body = {"resultType": "complete", **body,
            "_meta": {META + "serverInfo": SERVER_INFO}}
    return {"jsonrpc": "2.0", "id": id_, "result": body}


def handle(msg):
    """The response to one request, or None for a notification."""
    if "id" not in msg:
        return None
    id_, params = msg["id"], msg.get("params") or {}
    meta = params.get("_meta") or {}
    needed = (META + "protocolVersion", META + "clientCapabilities")
    if not all(k in meta for k in needed):
        return error(id_, -32602,
                     "Invalid params: the request has no protocol _meta")
    if meta[META + "protocolVersion"] != VERSION:
        return error(id_, -32022, "Unsupported protocol version",
                     {"supported": [VERSION],
                      "requested": meta[META + "protocolVersion"]})
    method = msg.get("method")
    if method == "server/discover":
        return result(id_, {"supportedVersions": [VERSION],
                            "capabilities": {"tools": {}},
                            "instructions": "Tools for Tarnwick Supply's "
                                            "knowledge graph."})
    if method == "tools/list":
        return result(id_, {"tools": [
            {"name": n, "description": d, "inputSchema": s}
            for n, (d, s, _) in tools.TOOLS.items()]})
    if method == "tools/call":
        name = params.get("name")
        if name not in tools.TOOLS:
            return error(id_, -32602, f"Unknown tool: {name}")
        text, failed = tools.call(name, params.get("arguments") or {})
        return result(id_, {"content": [{"type": "text", "text": text}],
                            "isError": failed})
    return error(id_, -32601, f"Method not found: {method}")


def serve(stdin=sys.stdin, stdout=sys.stdout):
    """Answer requests line by line until standard input closes."""
    for line in stdin:
        if not line.strip():
            continue
        try:
            reply = handle(json.loads(line))
        except json.JSONDecodeError:
            reply = error(None, -32700, "Parse error")
        if reply is not None:
            stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            stdout.flush()


# ------------------------------------------------------------------ client

class Client:
    """Starts `tarnwick mcp` and sends it requests, one line each way."""

    def __init__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "tarnwick", "mcp"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.next_id = 0
        self.log = []

    def request(self, method, params=None):
        self.next_id += 1
        params = dict(params or {})
        params["_meta"] = {META + "protocolVersion": VERSION,
                           META + "clientInfo": {"name": "tarnwick-agent",
                                                 "version": "1.0"},
                           META + "clientCapabilities": {}}
        msg = {"jsonrpc": "2.0", "id": self.next_id, "method": method,
               "params": params}
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        reply = json.loads(self.proc.stdout.readline())
        self.log.append((msg, reply))
        return reply

    def tools(self):
        return self.request("tools/list")["result"]["tools"]

    def call(self, name, arguments):
        reply = self.request("tools/call", {"name": name, "arguments": arguments})
        if "error" in reply:
            return reply["error"]["message"], True
        r = reply["result"]
        return "\n".join(c["text"] for c in r["content"]), r.get("isError", False)

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=30)
        self.proc.stdout.close()


def demo():
    """Three requests to the server and its replies, as they cross the wire."""
    client = Client()
    try:
        client.request("server/discover")
        client.tools()
        client.call("customer_orders", {"customer": "C-0083"})
    finally:
        client.close()
    out = []
    for n, (msg, reply) in enumerate(client.log):
        out.append("-> " + json.dumps(_short(msg, keep_meta=n == 0)))
        out.append("<- " + json.dumps(_short(reply)))
    return "\n".join(_fold(line) for line in out)


def _short(msg, keep_meta=False):
    """A message with the long parts cut down, for printing."""
    msg = json.loads(json.dumps(msg))
    params = msg.get("params")
    if params and "_meta" in params and not keep_meta:
        params["_meta"] = "..."
    res = msg.get("result") or {}
    res.pop("_meta", None)
    if "tools" in res:
        res["tools"] = [{"name": t["name"], "...": "..."} for t in res["tools"]]
    for c in res.get("content", []):
        c["text"] = c["text"].split("\n")[0][:60] + " ..."
    return msg


def _fold(line, width=74):
    out = []
    while len(line) > width:
        cut = line.rfind(" ", 0, width)
        cut = width if cut <= 3 else cut
        out.append(line[:cut])
        line = "   " + line[cut:].lstrip()
    return "\n".join(out + [line])
