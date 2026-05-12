#!/usr/bin/env python3
"""Token 用量 A/B 对比工具。

用法
----

1) 跑 baseline（关闭压缩，等价旧行为）：

    REPORT_CONTEXT_COMPRESSION_ENABLED=false \\
    REPORT_TOKEN_VARIANT_LABEL=baseline \\
        python -m backend.scripts.run_xxx ...   # 触发一次完整报告生成
    # 在报告结束时调用：
    #   from backend.app.utils.token_usage_service import dump_snapshot_to_file
    #   dump_snapshot_to_file(project_id, "exports/usage_baseline.json")

2) 跑 optimized（开启压缩 + 步骤裁剪）：

    REPORT_CONTEXT_COMPRESSION_ENABLED=true \\
    REPORT_PREV_SECTION_BUDGET=500 \\
    REPORT_MIN_TOOL_CALLS=1 \\
    REPORT_TOKEN_VARIANT_LABEL=optimized \\
        python -m backend.scripts.run_xxx ...
    # 同样 dump_snapshot_to_file(project_id, "exports/usage_optimized.json")

3) 对比：

    python backend/scripts/compare_token_usage.py \\
        --baseline exports/usage_baseline.json \\
        --optimized exports/usage_optimized.json \\
        --out exports/token_savings.md

也支持单文件模式（同一进程跑两遍、靠 variant 标签区分）：

    python backend/scripts/compare_token_usage.py --single exports/usage_run.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional, Tuple


def _load(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _zero() -> Dict[str, int]:
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}


def _add(dst: Dict[str, int], src: Dict[str, Any]) -> None:
    dst["prompt_tokens"] += int(src.get("prompt_tokens", 0) or 0)
    dst["completion_tokens"] += int(src.get("completion_tokens", 0) or 0)
    dst["total_tokens"] += int(src.get("total_tokens", 0) or 0)
    dst["calls"] += int(src.get("calls", 0) or 0)


def _extract_variant(
    snap: Dict[str, Any],
    variant_label: Optional[str] = None,
) -> Tuple[Dict[str, int], Dict[str, Dict[str, int]], Dict[str, Dict[str, int]]]:
    """从 detailed snapshot 抽出指定 variant 的总量、按 step 和按 category 的细分。

    若 variant_label 为 None，则求和所有 variant（向后兼容 legacy snapshot）。
    """
    total = _zero()
    by_step: Dict[str, Dict[str, int]] = {}
    by_category: Dict[str, Dict[str, int]] = {}

    detailed = snap.get("by_step_detailed")
    if detailed:
        for step_key, variants in detailed.items():
            for v, cats in variants.items():
                if variant_label and v != variant_label:
                    continue
                for cat, counter in cats.items():
                    _add(total, counter)
                    _add(by_step.setdefault(step_key, _zero()), counter)
                    _add(by_category.setdefault(cat, _zero()), counter)
        return total, by_step, by_category

    # legacy snapshot
    legacy = snap.get("by_step") or snap.get("legacy_by_step") or {}
    for step_key, counter in legacy.items():
        _add(total, counter)
        _add(by_step.setdefault(step_key, _zero()), counter)
    return total, by_step, by_category


def _pct(base: int, opt: int) -> str:
    if base == 0:
        return "—"
    delta = (base - opt) / base * 100.0
    sign = "" if delta >= 0 else ""
    return f"{sign}{delta:+.1f}%"


def _row(label: str, base: Dict[str, int], opt: Dict[str, int]) -> str:
    b_total = base.get("total_tokens", 0)
    o_total = opt.get("total_tokens", 0)
    return (
        f"| {label} | {b_total:>10,} | {o_total:>10,} | "
        f"{b_total - o_total:>+10,} | {_pct(b_total, o_total):>7} | "
        f"{base.get('calls', 0):>5} → {opt.get('calls', 0):<5} |"
    )


def render_markdown(
    baseline_total: Dict[str, int],
    baseline_step: Dict[str, Dict[str, int]],
    baseline_cat: Dict[str, Dict[str, int]],
    opt_total: Dict[str, int],
    opt_step: Dict[str, Dict[str, int]],
    opt_cat: Dict[str, Dict[str, int]],
    baseline_path: str,
    opt_path: str,
) -> str:
    lines = []
    lines.append("# Token 用量对比 · baseline vs optimized")
    lines.append("")
    lines.append(f"- baseline 快照：`{baseline_path}`")
    lines.append(f"- optimized 快照：`{opt_path}`")
    lines.append("")
    lines.append("## 总量")
    lines.append("")
    lines.append("| 指标 | baseline | optimized | Δ tokens | 节省 | calls |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    lines.append(_row("prompt", {"total_tokens": baseline_total["prompt_tokens"], "calls": baseline_total["calls"]},
                       {"total_tokens": opt_total["prompt_tokens"], "calls": opt_total["calls"]}))
    lines.append(_row("completion", {"total_tokens": baseline_total["completion_tokens"], "calls": baseline_total["calls"]},
                       {"total_tokens": opt_total["completion_tokens"], "calls": opt_total["calls"]}))
    lines.append(_row("**total**", baseline_total, opt_total))
    lines.append("")

    if baseline_step or opt_step:
        lines.append("## 按 step")
        lines.append("")
        lines.append("| step | baseline total | optimized total | Δ | 节省 | calls |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        all_steps = sorted(set(baseline_step.keys()) | set(opt_step.keys()))
        for s in all_steps:
            b = baseline_step.get(s, _zero())
            o = opt_step.get(s, _zero())
            lines.append(_row(s, b, o))
        lines.append("")

    if baseline_cat or opt_cat:
        lines.append("## 按 category")
        lines.append("")
        lines.append("| category | baseline total | optimized total | Δ | 节省 | calls |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        all_cats = sorted(set(baseline_cat.keys()) | set(opt_cat.keys()))
        for c in all_cats:
            b = baseline_cat.get(c, _zero())
            o = opt_cat.get(c, _zero())
            lines.append(_row(c, b, o))
        lines.append("")
        lines.append(
            "> 说明：`section_main` 是主模型 ReACT 推理；`section_compressor` 是开启压缩后用便宜小模型做的压缩调用；"
            "`outline` 是大纲规划；`default` 是没打标的旧调用（兼容口径）。"
        )
        lines.append("")

    # 结论
    b_t = baseline_total["total_tokens"]
    o_t = opt_total["total_tokens"]
    if b_t > 0:
        saved = b_t - o_t
        pct = saved / b_t * 100.0
        lines.append("## 结论")
        lines.append("")
        lines.append(f"- 节省 token：**{saved:+,}**（{pct:+.1f}%）")
        lines.append(f"- prompt 端节省：{baseline_total['prompt_tokens'] - opt_total['prompt_tokens']:+,}")
        lines.append(f"- completion 端节省：{baseline_total['completion_tokens'] - opt_total['completion_tokens']:+,}")
        if "section_compressor" in opt_cat:
            comp = opt_cat["section_compressor"]["total_tokens"]
            lines.append(
                f"- 其中压缩器自身消耗：{comp:,}（占 optimized 总量 {comp / max(o_t, 1) * 100:.1f}%）"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="对比 token 用量快照")
    p.add_argument("--baseline", help="baseline 快照 json 路径")
    p.add_argument("--optimized", help="optimized 快照 json 路径")
    p.add_argument(
        "--single",
        help="单文件模式：同一份 detailed snapshot 中按 variant 标签区分 baseline vs optimized",
    )
    p.add_argument("--baseline-label", default="baseline", help="单文件模式下 baseline 的 variant 名")
    p.add_argument("--optimized-label", default="optimized", help="单文件模式下 optimized 的 variant 名")
    p.add_argument("--out", default="", help="输出 Markdown 路径，留空则打到 stdout")
    args = p.parse_args()

    if args.single:
        snap = _load(args.single)
        b_total, b_step, b_cat = _extract_variant(snap, args.baseline_label)
        o_total, o_step, o_cat = _extract_variant(snap, args.optimized_label)
        baseline_path = f"{args.single}#{args.baseline_label}"
        opt_path = f"{args.single}#{args.optimized_label}"
    else:
        if not (args.baseline and args.optimized):
            print("ERROR: 需要 --baseline + --optimized，或者 --single", file=sys.stderr)
            return 2
        b_snap = _load(args.baseline)
        o_snap = _load(args.optimized)
        b_total, b_step, b_cat = _extract_variant(b_snap, None)
        o_total, o_step, o_cat = _extract_variant(o_snap, None)
        baseline_path = args.baseline
        opt_path = args.optimized

    md = render_markdown(b_total, b_step, b_cat, o_total, o_step, o_cat, baseline_path, opt_path)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"✓ 报告已写入 {args.out}")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
