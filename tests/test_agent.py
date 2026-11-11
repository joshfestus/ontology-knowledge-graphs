"""Chapter 20: the graph's tools, the MCP server and the agent. Model
answers come from llm-cache/, so these tests call no model and cost
nothing."""

import json

import pytest

from tarnwick import agent, mcp, tools

FIRST = ("Hi. My sleeping mat keeps going flat at night and I have had it for "
         "a while. What can I do?")
SECOND = ("Hello again. Last time I asked about my sleeping mat. What did you "
          "tell me I could do, and which order was it on?")


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("TARNWICK_LLM_BUDGET", "0")
    monkeypatch.setenv("TARNWICK_MEMORY", str(tmp_path / "memory.ttl"))
    return tmp_path


def test_the_write_checks():
    assert tools.contact_problems("C-0083", "O-00077", "TW-S202", "deflation", "ok") == []
    assert tools.contact_problems("C-0083", "O-00537", "TW-T202", "leak", "ok") == [
        "Product TW-T202 is not on order O-00537."]
    found = tools.contact_problems("C-0083", "O-00077", "TW-S202", "it went flat", "ok")
    assert found[0].startswith("it went flat is not a problem type")
    assert tools.contact_problems("C-9999", "O-00077", "TW-S202", "deflation", "")[:2] == [
        "There is no customer C-9999.", "Order O-00077 was not placed by C-9999."]


def test_a_contact_becomes_a_ticket_in_memory(sandbox):
    text, failed = tools.call("record_contact", {
        "customer": "C-0083", "order": "O-00077", "sku": "TW-S202",
        "problem": "deflation", "summary": "Offered the recall remedy."})
    assert not failed and "ticket:A-001" in text
    assert "A-001 (agent memory)" in tools.customer_history("C-0083")


def test_the_server_follows_the_protocol():
    ok = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
          "io.modelcontextprotocol/clientCapabilities": {}}
    r = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "server/discover",
                    "params": {"_meta": ok}})
    assert r["result"]["supportedVersions"] == ["2026-07-28"]
    assert r["result"]["resultType"] == "complete"
    r = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert r["error"]["code"] == -32602
    old = dict(ok, **{"io.modelcontextprotocol/protocolVersion": "2025-11-25"})
    r = mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list",
                    "params": {"_meta": old}})
    assert r["error"]["code"] == -32022
    assert mcp.handle({"jsonrpc": "2.0", "method": "notifications/x"}) is None


def test_the_client_talks_to_a_real_server():
    client = mcp.Client()
    try:
        names = [t["name"] for t in client.tools()]
        text, failed = client.call("product_facts", {"sku": "TW-S202"})
    finally:
        client.close()
    assert names == list(tools.TOOLS)
    assert not failed and "recalled" in text
    json.dumps(client.log)


def test_the_second_conversation_remembers_the_first():
    first_steps, _ = agent.run("C-0083", FIRST)
    assert [s["failed"] for s in first_steps if s["tool"] == "record_contact"] == [True, False]
    _, reply = agent.run("C-0083", SECOND)
    assert "O-00077" in reply and "refund" in reply
