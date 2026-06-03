# Pico Online Agent MVP Verification

## Commands

- `cd backend && pytest tests/unit/agent tests/unit/db/test_agent_models_schema.py tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`
- `cd frontend && npm test`
- `cd backend && python scripts/verify_pico_online_agent_flow.py`

## Check Results

- `PASS` 正常输出: 三轮 assistant message 均完成，run 状态为 completed，final_answer 非空。
- `PASS` 流式输出格式: 事件 sequence 单调递增，SSE 回放包含 id/event/data 三种字段。
- `PASS` 工具调用: 至少一轮出现 read_file 或 search 的 tool_result。
- `PASS` Prompt 组装: 每轮 prompt_metadata 都包含 section chars 元数据与完整 prompt 文本。
- `PASS` Memory 更新: session.memory_state 里保留 recent_files，task_summary 反映第三轮主题。
- `PASS` 多轮连贯: 第二轮 prompt 能看到第一轮，第三轮 prompt 能看到第二轮，最终回答显式引用上一轮。

## Conversation

### Turn 1

- User: 这个仓库的后端入口在哪里？
- Assistant: 后端入口在 `backend/app/main.py`，FastAPI 应用和 `api_router` 都从这里挂载。
- Stop reason: `final_answer_returned`
- Tool events: read_file
- Prompt chars: 1740

### Turn 2

- User: 刚才说到的入口和认证链路有什么关系？
- Assistant: 刚才提到的入口会把 `api_router` 接进应用，认证链路主要在 `backend/app/security/deps.py` 的 `get_current_user` 和 `require_permission`。
- Stop reason: `final_answer_returned`
- Tool events: search
- Prompt chars: 1791

### Turn 3

- User: 基于上一轮内容，总结我应该先读哪几个文件。
- Assistant: 基于上一轮内容，建议先读 `backend/app/main.py`、`backend/app/api/router.py` 和 `backend/app/security/deps.py`。上一轮我们已经确认了入口挂载和认证校验就在这几处汇合。
- Stop reason: `final_answer_returned`
- Tool events: read_file
- Prompt chars: 2159

## Final Memory

```json
{
  "working": {
    "task_summary": "基于上一轮内容，总结我应该先读哪几个文件。",
    "recent_files": [
      "backend/app/main.py",
      "backend/app/security/deps.py"
    ]
  },
  "episodic_notes": [],
  "file_summaries": {
    "backend/app/main.py": "from fastapi import FastAPI\nfrom app.api.router import api_router\n\napp = FastAPI()\napp.include_router(api_router, prefix=\"/api/v1\")",
    "backend/app/security/deps.py": "def get_current_user(...):\n    return user\n\ndef require_permission(permission_code: str):\n    return dependency"
  },
  "task": "",
  "files": [],
  "notes": [],
  "next_note_index": 0
}
```
