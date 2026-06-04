from scripts.verify_project_repo_agent_flow import (
    RoundExecutionResult,
    build_round_question,
    build_questions,
    classify_sse_payload,
    consume_sse_until_final,
    evaluate_prompt_assembled,
    validate_report_checks,
)


def test_build_questions_returns_three_linked_rounds() -> None:
    questions = build_questions()

    assert len(questions) == 3
    assert questions[0].startswith("这个仓库")
    assert "路由" in questions[1]
    assert "上一轮" in questions[2]


def test_build_round_question_reuses_previous_answer_paths() -> None:
    first_round = RoundExecutionResult(
        index=1,
        question="这个仓库的后端入口在哪里？",
        user_message={"id": 1},
        raw_sse_chunks=[],
        sse_events=[],
        run_record={},
        assistant_message={
            "content": "后端入口在 `api.py:1`，继续看 `biz/api/__init__.py:14`。"
        },
    )

    second_question = build_round_question(2, [first_round])
    third_question = build_round_question(3, [first_round])

    assert "api.py" in second_question
    assert "biz/api/__init__.py" in second_question
    assert "load_dotenv" not in second_question
    assert "conf/.env" not in second_question
    assert "路由是怎么注册进去的" in second_question
    assert "不要做全仓库泛搜" in second_question
    assert "api.py" in third_question


def test_classify_sse_payload_detects_required_event_types() -> None:
    payload = 'event: assistant_delta\ndata: {"delta":"hello"}\n\n'

    result = classify_sse_payload(payload)

    assert result["event"] == "assistant_delta"
    assert result["data"] == {"delta": "hello"}
    assert result["is_valid"] is True


def test_validate_report_checks_requires_all_acceptance_points() -> None:
    checks = {
        "has_final_output": True,
        "sse_format_ok": True,
        "tool_called": True,
        "prompt_assembled": True,
        "memory_updated": True,
        "multi_turn_continuity": True,
        "db_persisted": True,
    }

    errors = validate_report_checks(checks)

    assert errors == []


def test_validate_report_checks_reports_missing_items() -> None:
    checks = {
        "has_final_output": False,
        "sse_format_ok": True,
        "tool_called": False,
        "prompt_assembled": True,
        "memory_updated": False,
        "multi_turn_continuity": True,
        "db_persisted": False,
    }

    errors = validate_report_checks(checks)

    assert "缺少最终回答输出" in errors
    assert "未观察到真实工具调用" in errors
    assert "memory_state 未按预期更新" in errors
    assert "数据库落库结果不完整" in errors


def test_consume_sse_until_final_uses_incremental_stream_cursor(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size: int) -> bytes:
            del size
            return b"event: final_answer\ndata: {\"id\": 11}\n\n"

    def fake_urlopen(request, timeout=0):
        del timeout
        captured["url"] = request.full_url
        return FakeResponse()

    monkeypatch.setattr("scripts.verify_project_repo_agent_flow.urlopen", fake_urlopen)

    events = consume_sse_until_final(
        base_url="http://127.0.0.1:8000",
        project_id=4,
        session_id=9,
        access_token="token",
        after_message_id=7,
        baseline_event_id=10,
        timeout_seconds=5,
    )

    assert "after_event_id=10" in captured["url"]
    assert "after_message_id=7" in captured["url"]
    assert events[0]["event"] == "final_answer"


def test_evaluate_prompt_assembled_accepts_compressed_history_with_prior_round_evidence() -> None:
    round_results = [
        RoundExecutionResult(
            index=1,
            question="这个仓库的后端入口在哪里？",
            user_message={"id": 1},
            raw_sse_chunks=[],
            sse_events=[],
            run_record={
                "prompt_metadata": {
                    "prefix": "p",
                    "memory": "m",
                    "relevant_memory": "rm",
                    "history": "",
                    "current_request": "这个仓库的后端入口在哪里？",
                }
            },
            assistant_message={"content": "后端入口在 `api.py`，然后看 `biz/api/__init__.py`。"},
        ),
        RoundExecutionResult(
            index=2,
            question="入口初始化之后，路由是怎么注册进去的？",
            user_message={"id": 2},
            raw_sse_chunks=[],
            sse_events=[],
            run_record={
                "prompt_metadata": {
                    "prefix": "p",
                    "memory": "m",
                    "relevant_memory": "rm",
                    "history": (
                        "User: 这个仓库的后端入口在哪里？\n"
                        "Assistant: 后端入口在 `api.py`，然后看 `biz/api/__init__.py`。"
                    ),
                    "current_request": "入口初始化之后，路由是怎么注册进去的？",
                }
            },
            assistant_message={"content": "继续看 `biz/api/routes/__init__.py`。"},
        ),
        RoundExecutionResult(
            index=3,
            question="总结我应该先读哪几个文件。",
            user_message={"id": 3},
            raw_sse_chunks=[],
            sse_events=[],
            run_record={
                "prompt_metadata": {
                    "prefix": "p",
                    "memory": "m",
                    "relevant_memory": "rm",
                    "history": (
                        "User: 这个仓库的后端入口在哪里？\n"
                        "Assistant: 后端入口在 `api.py`，然后看 `biz/api/__init__.py`。\n"
                        "User: 入口初始化之后，路由是怎么注册进去的？\n"
                        "Assistant: 继续看 `biz/api/routes/__init__.py`。"
                    ),
                    "current_request": "总结我应该先读哪几个文件。",
                }
            },
            assistant_message={"content": "先读 api.py。"},
        ),
    ]

    assert evaluate_prompt_assembled(round_results) is True


def test_evaluate_prompt_assembled_rejects_missing_previous_round_history() -> None:
    round_results = [
        RoundExecutionResult(
            index=1,
            question="这个仓库的后端入口在哪里？",
            user_message={"id": 1},
            raw_sse_chunks=[],
            sse_events=[],
            run_record={
                "prompt_metadata": {
                    "prefix": "p",
                    "memory": "m",
                    "relevant_memory": "rm",
                    "history": "",
                    "current_request": "这个仓库的后端入口在哪里？",
                }
            },
            assistant_message={"content": "后端入口在 `api.py`。"},
        ),
        RoundExecutionResult(
            index=2,
            question="入口初始化之后，路由是怎么注册进去的？",
            user_message={"id": 2},
            raw_sse_chunks=[],
            sse_events=[],
            run_record={
                "prompt_metadata": {
                    "prefix": "p",
                    "memory": "m",
                    "relevant_memory": "rm",
                    "history": "Assistant tool call only",
                    "current_request": "入口初始化之后，路由是怎么注册进去的？",
                }
            },
            assistant_message={"content": "继续看 `biz/api/routes/__init__.py`。"},
        ),
    ]

    assert evaluate_prompt_assembled(round_results) is False
