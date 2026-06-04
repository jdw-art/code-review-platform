from __future__ import annotations

from app.agent.protocol import parse_agent_response, retry_notice


def test_parse_agent_response_accepts_valid_tool_payload() -> None:
    kind, payload = parse_agent_response(
        '<tool>{"name":"read_file","args":{"path":"README.md","start":1,"end":20}}</tool>'
    )

    assert kind == "tool"
    assert payload == {
        "name": "read_file",
        "args": {"path": "README.md", "start": 1, "end": 20},
    }


def test_parse_agent_response_retries_on_empty_final() -> None:
    kind, payload = parse_agent_response("<final>   </final>")

    assert kind == "retry"
    assert "non-empty <final> answer" in payload


def test_parse_agent_response_retries_on_bare_text() -> None:
    kind, payload = parse_agent_response("I already checked the file for you")

    assert kind == "retry"
    assert "valid <tool> call or a <final> answer" in payload


def test_parse_agent_response_retries_on_xml_tool_variant() -> None:
    kind, payload = parse_agent_response('<tool name="read_file" path="README.md"></tool>')

    assert kind == "retry"
    assert "valid <tool> call or a <final> answer" in payload


def test_parse_agent_response_retries_on_mixed_tool_and_final() -> None:
    kind, payload = parse_agent_response(
        '<tool>{"name":"read_file","args":{"path":"README.md"}}</tool><final>done</final>'
    )

    assert kind == "retry"
    assert "exactly one top-level action" in payload


def test_parse_agent_response_accepts_repeated_identical_tool_before_final_explanation() -> None:
    kind, payload = parse_agent_response(
        '<tool>{"name":"read_file","args":{"path":"biz/api/__init__.py","start":1,"end":200}}</tool>'
        '<tool>{"name":"read_file","args":{"path":"biz/api/__init__.py","start":1,"end":200}}</tool>'
        "<final>我还没拿到文件内容，请先读取这个文件。</final>"
    )

    assert kind == "tool"
    assert payload == {
        "name": "read_file",
        "args": {"path": "biz/api/__init__.py", "start": 1, "end": 200},
    }


def test_parse_agent_response_retries_on_multiple_final_tags() -> None:
    kind, payload = parse_agent_response("<final>a</final><final>b</final>")

    assert kind == "retry"
    assert "exactly one top-level action" in payload


def test_parse_agent_response_retries_on_multiple_final_tags_with_whitespace() -> None:
    kind, payload = parse_agent_response("<final>a</final>\n  <final>b</final>")

    assert kind == "retry"
    assert "exactly one top-level action" in payload


def test_parse_agent_response_accepts_tool_payload_with_final_like_text_in_json() -> None:
    kind, payload = parse_agent_response(
        '<tool>{"name":"search_code","args":{"query":"<final></final>"}}</tool>'
    )

    assert kind == "tool"
    assert payload == {
        "name": "search_code",
        "args": {"query": "<final></final>"},
    }


def test_parse_agent_response_retries_on_text_outside_tags() -> None:
    kind, payload = parse_agent_response(
        'Need one more step <tool>{"name":"read_file","args":{"path":"README.md"}}</tool>'
    )

    assert kind == "retry"
    assert "outside the top-level tag" in payload


def test_retry_notice_mentions_read_only_online_protocol() -> None:
    payload = retry_notice("model returned malformed tool output")

    assert "write_file" not in payload
    assert "delegate" not in payload
    assert "shell" not in payload
    assert '<tool>{"name":"tool_name","args":{...}}</tool>' in payload
