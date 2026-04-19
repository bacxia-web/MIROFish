"""按项目与步骤聚合 LLM token 用量（后端统计，不依赖前端展示）。"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional

_lock = threading.Lock()
_thread_local = threading.local()

# project_id -> step_key -> counters
_usage_stats: Dict[str, Dict[str, Dict[str, Any]]] = {}


def _step_key(step: Optional[int]) -> str:
    try:
        s = int(step or 0)
    except Exception:
        s = 0
    return f"step{s}" if 1 <= s <= 5 else "step_unknown"


def set_usage_context(project_id: Optional[str], step: Optional[int]) -> None:
    _thread_local.project_id = (project_id or "").strip()
    _thread_local.step = int(step or 0) if step else 0


def clear_usage_context() -> None:
    _thread_local.project_id = ""
    _thread_local.step = 0


@contextmanager
def usage_context(project_id: Optional[str], step: Optional[int]) -> Iterator[None]:
    old_project = getattr(_thread_local, "project_id", "")
    old_step = getattr(_thread_local, "step", 0)
    set_usage_context(project_id, step)
    try:
        yield
    finally:
        _thread_local.project_id = old_project
        _thread_local.step = old_step


def record_llm_usage(
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    model: str = "",
) -> None:
    project_id = getattr(_thread_local, "project_id", "")
    step = getattr(_thread_local, "step", 0)
    if not project_id:
        return
    key = _step_key(step)
    with _lock:
        by_step = _usage_stats.setdefault(project_id, {})
        slot = by_step.setdefault(
            key,
            {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "calls": 0,
                "models": {},
                "updated_at": None,
            },
        )
        slot["prompt_tokens"] += int(prompt_tokens or 0)
        slot["completion_tokens"] += int(completion_tokens or 0)
        slot["total_tokens"] += int(total_tokens or 0)
        slot["calls"] += 1
        mm = slot.setdefault("models", {})
        m = (model or "").strip()
        if m:
            mm[m] = int(mm.get(m, 0)) + 1
        slot["updated_at"] = datetime.now(timezone.utc).isoformat()


def snapshot_token_usage(project_id: str) -> Dict[str, Any]:
    with _lock:
        data = json.loads(json.dumps(_usage_stats.get(project_id, {}), ensure_ascii=False))
    out: Dict[str, Any] = {"by_step": {}}
    for i in range(1, 6):
        out["by_step"][f"step{i}"] = data.get(
            f"step{i}",
            {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "calls": 0,
                "models": {},
                "updated_at": None,
            },
        )
    if data.get("step_unknown"):
        out["by_step"]["step_unknown"] = data["step_unknown"]
    return out
