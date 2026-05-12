#!/usr/bin/env python3
"""Phase 6 · 轻量 eval 框架。

对一组报告（产线 baseline / 某 flag 开启 / 全开 等不同 variant）打分并对比，
给出"是否塌质量了 / 塌在哪一项 / 大概多少"的可量化输出。

打分维度
--------
**规则型（不调 LLM，便宜可靠）**
- char_count           ：正文字数（仅参考，过短可能是塌的信号）
- citation_density     ：每千字含 `「…」` / `"…"` / `> …` 三种引用的次数
- digit_density        ：每千字数字 token 数（事实丰富的代理指标）
- section_count        ：二级标题数（结构完整度）
- avg_section_length   ：平均章节长度
- section_length_std   ：章节长度标准差（越大越不均衡）

**LLM-as-judge（4 个维度，0-10 分）**
- factual_richness     ：事实丰富度
- causal_depth         ：因果分析深度
- section_coherence    ：章节衔接连贯性
- citation_specificity ：引言生动度

用法
----

# 单 variant 打分（建立基准）
python backend/scripts/eval_report_quality.py \\
    --reports report_aaa report_bbb report_ccc \\
    --variant-label baseline \\
    --out exports/eval_baseline.json

# 两 variant 对比
python backend/scripts/eval_report_quality.py \\
    --baseline exports/eval_baseline.json \\
    --optimized exports/eval_optimized.json \\
    --out exports/eval_compare.md

# 不调 LLM judge 时（快速冒烟，只要规则型）
... --no-llm-judge
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from typing import Any, Dict, List, Optional, Tuple

# 加 backend 到 path 以便 import app.utils.llm_client（仅 LLM judge 时需要）
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_THIS_DIR, '..'))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


# ── 规则型打分 ────────────────────────────────────────────────────────

_RE_SECTION_H2 = re.compile(r'^\s*##\s+(.+?)\s*$', re.MULTILINE)
_RE_CHINESE_QUOTE = re.compile(r'「[^」]{2,100}」')
_RE_ASCII_QUOTE = re.compile(r'"[^"]{2,100}"')
_RE_BLOCKQUOTE = re.compile(r'^\s*>\s+\S', re.MULTILINE)
_RE_DIGIT_TOKEN = re.compile(r'\d+(?:[.,]\d+)?%?')


def rule_based_metrics(markdown: str) -> Dict[str, float]:
    if not markdown:
        return {
            "char_count": 0,
            "citation_density": 0,
            "digit_density": 0,
            "section_count": 0,
            "avg_section_length": 0,
            "section_length_std": 0,
        }
    char_count = len(markdown)
    citations = (
        len(_RE_CHINESE_QUOTE.findall(markdown))
        + len(_RE_ASCII_QUOTE.findall(markdown))
        + len(_RE_BLOCKQUOTE.findall(markdown))
    )
    digits = len(_RE_DIGIT_TOKEN.findall(markdown))
    per_kchar = max(char_count, 1) / 1000.0

    titles = _RE_SECTION_H2.findall(markdown)
    # 按 H2 分段
    sections = re.split(r'(?m)^\s*##\s+.+?\s*$', markdown)
    sections = [s.strip() for s in sections if s.strip()]
    if sections:
        lens = [len(s) for s in sections]
        avg_len = statistics.mean(lens)
        std_len = statistics.pstdev(lens) if len(lens) > 1 else 0.0
    else:
        avg_len = 0.0
        std_len = 0.0

    return {
        "char_count": char_count,
        "citation_density": round(citations / per_kchar, 2),
        "digit_density": round(digits / per_kchar, 2),
        "section_count": len(titles),
        "avg_section_length": round(avg_len, 1),
        "section_length_std": round(std_len, 1),
    }


# ── LLM-as-judge ─────────────────────────────────────────────────────

JUDGE_SYSTEM = """你是一个严苛的中文报告质量评审专家。
给定一份模拟预测报告，你要从 4 个维度各打 0-10 分（整数）：

1. factual_richness（事实丰富度）：
   - 引用了多少具体事实、人物、数据、场景？过于空洞的报告分低，证据扎实的分高。

2. causal_depth（因果分析深度）：
   - 是否回答了"为什么"，而不只是"是什么"？
   - 给出机制 / 触发条件 / 影响链路 = 高分；仅罗列现象 = 低分。

3. section_coherence（章节衔接）：
   - 各章节之间能否形成完整叙事？前后是否呼应？
   - 各自为政、跳跃 = 低分；环环相扣 = 高分。

4. citation_specificity（引言生动度）：
   - 是否有具体的引言或角色发言（如「某学生表示...」）？
   - 引用具体且有信息量 = 高分；只有干巴巴的描述 = 低分。

输出严格 JSON：
{
  "factual_richness": 7,
  "causal_depth": 6,
  "section_coherence": 8,
  "citation_specificity": 7,
  "rationale": "一段简短理由（不超过 150 字）"
}

只输出 JSON，不要其他文字。"""


def llm_judge_score(markdown: str, judge_model: Optional[str] = None) -> Dict[str, Any]:
    """调用 LLMClient 给报告打分。失败返回空 dict。"""
    if not markdown:
        return {}
    try:
        from app.utils.llm_client import LLMClient
        client = LLMClient(model=judge_model) if judge_model else LLMClient()
        # 报告太长时只取前 12000 字（避免 judge 自己也超长）
        excerpt = markdown[:12000]
        if len(markdown) > 12000:
            excerpt += "\n\n...[报告余下部分省略，请基于上文给分]"
        result = client.chat_json(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": excerpt},
            ],
            temperature=0.0,
            max_tokens=800,
        )
        # 规范化分数
        def _i(k):
            try:
                v = int(result.get(k, 0))
                return max(0, min(10, v))
            except Exception:
                return 0
        return {
            "factual_richness": _i("factual_richness"),
            "causal_depth": _i("causal_depth"),
            "section_coherence": _i("section_coherence"),
            "citation_specificity": _i("citation_specificity"),
            "rationale": str(result.get("rationale", ""))[:300],
        }
    except Exception as e:
        sys.stderr.write(f"[warn] LLM judge 失败: {e}\n")
        return {}


# ── 报告读取 ────────────────────────────────────────────────────────

def load_report(report_id_or_path: str) -> Tuple[str, Dict[str, Any]]:
    """支持两种输入：
    - 直接给 markdown 文件路径
    - 给 report_id，从 backend/uploads/reports/<report_id>/ 读取
    返回 (markdown_content, metadata_dict)。
    """
    if os.path.exists(report_id_or_path) and report_id_or_path.endswith(('.md', '.markdown')):
        with open(report_id_or_path, 'r', encoding='utf-8') as f:
            return f.read(), {"path": report_id_or_path}
    # report_id 模式
    rid = report_id_or_path
    # 尝试常见路径
    candidates = [
        os.path.join(_BACKEND_DIR, 'uploads', 'reports', rid),
        os.path.join(_BACKEND_DIR, '..', 'uploads', 'reports', rid),
        os.path.join(_BACKEND_DIR, 'demo_uploads', 'reports', rid),
    ]
    for base in candidates:
        if os.path.isdir(base):
            md_path = os.path.join(base, 'report.md')
            if not os.path.exists(md_path):
                # 其他可能命名
                for fn in os.listdir(base):
                    if fn.endswith('.md'):
                        md_path = os.path.join(base, fn)
                        break
            if os.path.exists(md_path):
                with open(md_path, 'r', encoding='utf-8') as f:
                    md = f.read()
                # 读 metadata json（含 optimization_flags）
                meta_path = os.path.join(base, 'report.json')
                meta = {"report_id": rid, "path": md_path}
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta.update(json.load(f))
                    except Exception:
                        pass
                return md, meta
    raise FileNotFoundError(f"找不到报告: {report_id_or_path}")


# ── 单 variant 打分 ─────────────────────────────────────────────────

def score_one_variant(
    report_inputs: List[str],
    variant_label: str,
    use_llm_judge: bool = True,
    judge_model: Optional[str] = None,
) -> Dict[str, Any]:
    per_report = []
    for ri in report_inputs:
        try:
            md, meta = load_report(ri)
        except Exception as e:
            sys.stderr.write(f"[skip] 读取失败 {ri}: {e}\n")
            continue
        item = {
            "input": ri,
            "metadata": {
                "report_id": meta.get("report_id"),
                "optimization_flags": meta.get("optimization_flags", {}),
            },
            "rules": rule_based_metrics(md),
        }
        if use_llm_judge:
            item["judge"] = llm_judge_score(md, judge_model=judge_model)
        per_report.append(item)

    # 聚合
    def _mean(field_path: List[str]) -> float:
        vals = []
        for r in per_report:
            cur: Any = r
            for k in field_path:
                if not isinstance(cur, dict) or k not in cur:
                    cur = None
                    break
                cur = cur[k]
            if isinstance(cur, (int, float)):
                vals.append(float(cur))
        return round(statistics.mean(vals), 2) if vals else 0.0

    aggregate = {
        "char_count": _mean(["rules", "char_count"]),
        "citation_density": _mean(["rules", "citation_density"]),
        "digit_density": _mean(["rules", "digit_density"]),
        "section_count": _mean(["rules", "section_count"]),
        "avg_section_length": _mean(["rules", "avg_section_length"]),
        "section_length_std": _mean(["rules", "section_length_std"]),
    }
    if use_llm_judge:
        aggregate.update({
            "factual_richness": _mean(["judge", "factual_richness"]),
            "causal_depth": _mean(["judge", "causal_depth"]),
            "section_coherence": _mean(["judge", "section_coherence"]),
            "citation_specificity": _mean(["judge", "citation_specificity"]),
        })
        # 综合分（4 个 judge 维度均值）
        judge_total = (
            aggregate["factual_richness"]
            + aggregate["causal_depth"]
            + aggregate["section_coherence"]
            + aggregate["citation_specificity"]
        ) / 4.0
        aggregate["judge_overall"] = round(judge_total, 2)
    return {
        "variant_label": variant_label,
        "n_reports": len(per_report),
        "per_report": per_report,
        "aggregate": aggregate,
    }


# ── 对比报告 ────────────────────────────────────────────────────────

def render_compare_md(baseline: Dict[str, Any], optimized: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"# 报告质量对比 · {baseline['variant_label']} vs {optimized['variant_label']}")
    lines.append("")
    lines.append(f"- baseline 报告数：{baseline['n_reports']}")
    lines.append(f"- optimized 报告数：{optimized['n_reports']}")
    lines.append("")

    bag = baseline["aggregate"]
    oag = optimized["aggregate"]

    def _diff_row(label: str, key: str, threshold_warn: float = 0.5):
        b = bag.get(key, 0)
        o = oag.get(key, 0)
        diff = round(o - b, 2)
        mark = ""
        if isinstance(b, (int, float)) and isinstance(o, (int, float)) and b != 0:
            # judge 分数：负差 > 阈值 → ⚠️
            if abs(diff) >= threshold_warn:
                mark = " ⚠️" if diff < 0 else " ✓"
        return f"| {label} | {b} | {o} | {diff:+} |{mark} |"

    lines.append("## LLM-as-judge 分数（0-10）")
    lines.append("")
    lines.append("| 维度 | baseline | optimized | Δ | 提示 |")
    lines.append("|---|---:|---:|---:|---|")
    for label, key in [
        ("事实丰富度", "factual_richness"),
        ("因果分析深度", "causal_depth"),
        ("章节衔接", "section_coherence"),
        ("引言生动度", "citation_specificity"),
        ("**judge 总均分**", "judge_overall"),
    ]:
        lines.append(_diff_row(label, key, threshold_warn=0.5))
    lines.append("")

    lines.append("## 规则型指标")
    lines.append("")
    lines.append("| 指标 | baseline | optimized | Δ | 提示 |")
    lines.append("|---|---:|---:|---:|---|")
    for label, key, thr in [
        ("字数", "char_count", 1000),
        ("引言密度 (per 1k)", "citation_density", 1.0),
        ("数字密度 (per 1k)", "digit_density", 2.0),
        ("章节数", "section_count", 1),
        ("平均章节长度", "avg_section_length", 500),
        ("章节长度标准差", "section_length_std", 200),
    ]:
        lines.append(_diff_row(label, key, threshold_warn=thr))
    lines.append("")

    # 风险点提取
    risks = []
    judge_total_diff = oag.get("judge_overall", 0) - bag.get("judge_overall", 0)
    if judge_total_diff <= -0.5:
        risks.append(f"⚠️ judge 总均分下降 {abs(judge_total_diff):.2f} 分（≥0.5 视为质量退化）")
    for label, key in [
        ("事实丰富度", "factual_richness"),
        ("引言生动度", "citation_specificity"),
        ("章节衔接", "section_coherence"),
    ]:
        if oag.get(key, 0) - bag.get(key, 0) <= -0.8:
            risks.append(f"⚠️ {label}明显塌（≥0.8 分）→ 可能是压缩太狠")
    if risks:
        lines.append("## 风险点")
        lines.append("")
        lines.extend(f"- {r}" for r in risks)
        lines.append("")
    else:
        lines.append("## 风险点")
        lines.append("")
        lines.append("- 未发现明显塌质量的维度（均在阈值内）")
        lines.append("")

    return "\n".join(lines) + "\n"


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="报告质量 eval 框架")
    # 单 variant 打分模式
    p.add_argument("--reports", nargs="+", help="要评估的 report_id 列表 或 .md 路径列表")
    p.add_argument("--variant-label", default="run", help="本次打分的 variant 标签")
    p.add_argument("--judge-model", default="", help="LLM judge 用哪个模型；空则用默认链")
    p.add_argument("--no-llm-judge", action="store_true", help="只做规则型打分，跳过 LLM judge（快速冒烟）")
    # 对比模式
    p.add_argument("--baseline", help="对比模式：baseline 分数 json 路径")
    p.add_argument("--optimized", help="对比模式：optimized 分数 json 路径")
    # 输出
    p.add_argument("--out", default="", help="输出路径（json 或 md）")
    args = p.parse_args()

    # 对比模式
    if args.baseline and args.optimized:
        with open(args.baseline, "r", encoding="utf-8") as f:
            bj = json.load(f)
        with open(args.optimized, "r", encoding="utf-8") as f:
            oj = json.load(f)
        md = render_compare_md(bj, oj)
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"✓ 对比报告 → {args.out}")
        else:
            sys.stdout.write(md)
        return 0

    # 单 variant 模式
    if not args.reports:
        print("ERROR: 单 variant 模式需要 --reports，或对比模式需要 --baseline + --optimized", file=sys.stderr)
        return 2

    result = score_one_variant(
        report_inputs=args.reports,
        variant_label=args.variant_label,
        use_llm_judge=not args.no_llm_judge,
        judge_model=args.judge_model or None,
    )
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✓ {args.variant_label} 打分结果 → {args.out}")
    else:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
