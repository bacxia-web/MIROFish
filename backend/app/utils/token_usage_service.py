"""按项目与步骤聚合 LLM token 用量（后端统计，不依赖前端展示）。

v2 扩展：
- 在原 step_key 维度上新增 variant（如 baseline/optimized）与 category（如 section_main、
  section_compressor、outline、disamb、interview）两层标签，便于 A/B 对比上下文压缩与步骤
  裁剪带来的实际 token 节省。
- snapshot_token_usage 保持旧返回 shape（跨 variant/category 求和），新增
  snapshot_token_usage_detailed 暴露完整三维分布。
- dump_snapshot_to_file / load_snapshot_from_file 用于跨进程或离线对比。
"""

from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional

_lock = threading.Lock()
_thread_local = threading.local()

# project_id -> step_key -> variant -> category -> counters
_usage_stats: Dict[str, Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]] = {}

_DEFAULT_VARIANT = "default"
_DEFAULT_CATEGORY = "default"


def _step_key(step: Optional[int]) -> str:
    try:
        s = int(step or 0)
    except Exception:
        s = 0
    return f"step{s}" if 1 <= s <= 5 else "step_unknown"


def _empty_counter() -> Dict[str, Any]:
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "calls": 0,
        "models": {},
        "updated_at": None,
    }


def _merge_counter(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
    dst["prompt_tokens"] = int(dst.get("prompt_tokens", 0)) + int(src.get("prompt_tokens", 0) or 0)
    dst["completion_tokens"] = int(dst.get("completion_tokens", 0)) + int(src.get("completion_tokens", 0) or 0)
    dst["total_tokens"] = int(dst.get("total_tokens", 0)) + int(src.get("total_tokens", 0) or 0)
    dst["calls"] = int(dst.get("calls", 0)) + int(src.get("calls", 0) or 0)
    src_models = src.get("models") or {}
    dst_models = dst.setdefault("models", {})
    for m, c in src_models.items():
        dst_models[m] = int(dst_models.get(m, 0)) + int(c or 0)
    su = src.get("updated_at")
    du = dst.get("updated_at")
    if su and (not du or su > du):
        dst["updated_at"] = su


# ── 上下文设置 ─────────────────────────────────────────────────────────────

def set_usage_context(project_id: Optional[str], step: Optional[int]) -> None:
    _thread_local.project_id = (project_id or "").strip()
    _thread_local.step = int(step or 0) if step else 0


def clear_usage_context() -> None:
    _thread_local.project_id = ""
    _thread_local.step = 0


def set_usage_tags(variant: Optional[str] = None, category: Optional[str] = None) -> None:
    if variant is not None:
        _thread_local.variant = (variant or "").strip() or _DEFAULT_VARIANT
    if category is not None:
        _thread_local.category = (category or "").strip() or _DEFAULT_CATEGORY


def _current_variant() -> str:
    return getattr(_thread_local, "variant", "") or os.environ.get(
        "REPORT_TOKEN_VARIANT_LABEL", _DEFAULT_VARIANT
    ) or _DEFAULT_VARIANT


def _current_category() -> str:
    return getattr(_thread_local, "category", "") or _DEFAULT_CATEGORY


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


@contextmanager
def usage_tags(variant: Optional[str] = None, category: Optional[str] = None) -> Iterator[None]:
    old_variant = getattr(_thread_local, "variant", "")
    old_category = getattr(_thread_local, "category", "")
    if variant is not None:
        _thread_local.variant = (variant or "").strip() or _DEFAULT_VARIANT
    if category is not None:
        _thread_local.category = (category or "").strip() or _DEFAULT_CATEGORY
    try:
        yield
    finally:
        _thread_local.variant = old_variant
        _thread_local.category = old_category


# ── 记录 ─────────────────────────────────────────────────────────────────

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
    step_key = _step_key(step)
    variant = _current_variant()
    category = _current_category()
    with _lock:
        by_step = _usage_stats.setdefault(project_id, {})
        by_variant = by_step.setdefault(step_key, {})
        by_cat = by_variant.setdefault(variant, {})
        slot = by_cat.setdefault(category, _empty_counter())
        slot["prompt_tokens"] += int(prompt_tokens or 0)
        slot["completion_tokens"] += int(completion_tokens or 0)
        slot["total_tokens"] += int(total_tokens or 0)
        slot["calls"] += 1
        mm = slot.setdefault("models", {})
        m = (model or "").strip()
        if m:
            mm[m] = int(mm.get(m, 0)) + 1
        slot["updated_at"] = datetime.now(timezone.utc).isoformat()


# ── 快照 ─────────────────────────────────────────────────────────────────

def _flatten_step(step_data: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, Any]:
    """跨 variant/category 求和，返回旧版 shape，保证向后兼容。"""
    merged = _empty_counter()
    for variant_data in step_data.values():
        for cat_counter in variant_data.values():
            _merge_counter(merged, cat_counter)
    return merged


def snapshot_token_usage(project_id: str) -> Dict[str, Any]:
    """旧版接口：按 step 求和，跨所有 variant/category。"""
    with _lock:
        raw = json.loads(json.dumps(_usage_stats.get(project_id, {}), ensure_ascii=False))
    out: Dict[str, Any] = {"by_step": {}}
    for i in range(1, 6):
        key = f"step{i}"
        out["by_step"][key] = _flatten_step(raw.get(key, {})) if raw.get(key) else _empty_counter()
    if raw.get("step_unknown"):
        out["by_step"]["step_unknown"] = _flatten_step(raw["step_unknown"])
    return out


def snapshot_token_usage_detailed(project_id: str) -> Dict[str, Any]:
    """新版接口：保留 variant/category 三维分布；同时给出按 variant 汇总。"""
    with _lock:
        raw = json.loads(json.dumps(_usage_stats.get(project_id, {}), ensure_ascii=False))

    by_step_detailed: Dict[str, Any] = {}
    by_variant_summary: Dict[str, Dict[str, Any]] = {}

    for step_key, variant_map in raw.items():
        by_step_detailed[step_key] = {}
        for variant, cat_map in variant_map.items():
            by_step_detailed[step_key][variant] = {}
            variant_total = by_variant_summary.setdefault(variant, _empty_counter())
            for category, counter in cat_map.items():
                by_step_detailed[step_key][variant][category] = counter
                _merge_counter(variant_total, counter)

    return {
        "project_id": project_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "by_step_detailed": by_step_detailed,
        "by_variant_summary": by_variant_summary,
        "legacy_by_step": snapshot_token_usage(project_id)["by_step"],
    }


def dump_snapshot_to_file(project_id: str, path: str, *, detailed: bool = True) -> str:
    snap = snapshot_token_usage_detailed(project_id) if detailed else snapshot_token_usage(project_id)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    return path


def load_snapshot_from_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def reset_project_usage(project_id: str) -> None:
    """清空指定项目的累计统计（用于 A/B 对比前的归零）。"""
    with _lock:
        _usage_stats.pop(project_id, None)
