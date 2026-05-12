"""使用 LLM 按本体从文本块抽取实体与关系（替代 Zep 服务端抽取）。

Phase 3 增强：
- D3+D4：批处理多个 chunk 一次调用，单批失败时整批回退单块逐个抽取
- D5：known_entities 智能裁剪（纯子串匹配，只发本块文本里出现过的实体名）
- D15：system prompt 保持稳定字面，让 DashScope 隐式 prompt cache 生效
- usage_tags：单块路径打 chunk_extract_single，批路径打 chunk_extract_batch
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ...config import Config
from ...utils.llm_client import LLMClient
from ...utils.logger import get_logger
from ...utils.token_usage_service import usage_tags

logger = get_logger('mirofish.chunk_extractor')

SYSTEM = """你是知识图谱抽取器。根据给定的「本体定义」从「文本块」中抽取实体与关系。
你必须只输出合法 JSON，不要有其它文字。

输出格式：
{
  "entities": [
    {"name": "实体名（与原文一致或常用译名）", "entity_type": "本体中已有实体类型名", "summary": "一句摘要", "attributes": {}}
  ],
  "relations": [
    {"type": "本体中已有关系类型名", "source": "源实体 name", "target": "目标实体 name", "fact": "从原文概括的关系事实（中文短句）"}
  ]
}

规则：
- entity_type、relations[].type 必须来自本体中已声明的名称，不要编造新类型。
- 抽不到的留空数组。
- 关系两端的实体应出现在 entities 中；若原文仅一侧明确，不要强行造实体。
- 实体 name 尽量使用原文中的完整称谓/全名（如「贾雨村」而非仅「雨村」），除非原文只出现简称。
- 同名实体在整篇文档中必须保持类型一致。如果「已识别实体」中某人已被标记为具体类型（如 Official），即使当前块未提及其职位，也必须沿用该类型，不要降级为 Person 或 Organization。
- Person 和 Organization 是严格的兜底类型，仅用于确实无法归入任何具体类型的实体。
"""

SYSTEM_BATCH = """你是知识图谱抽取器。根据给定的「本体定义」从「多个文本块」中分别抽取实体与关系。
你必须只输出合法 JSON 数组，不要有其它文字。每个数组项对应一个文本块。

输出格式（按 chunk_index 升序）：
[
  {
    "chunk_index": 0,
    "entities": [
      {"name": "...", "entity_type": "...", "summary": "...", "attributes": {}}
    ],
    "relations": [
      {"type": "...", "source": "...", "target": "...", "fact": "..."}
    ]
  },
  {"chunk_index": 1, "entities": [...], "relations": [...]},
  ...
]

规则：
- entity_type、relations[].type 必须来自本体中已声明的名称，不要编造新类型。
- 每个 chunk **独立判断**，不要让 chunk A 的内容污染 chunk B 的抽取。
- 抽不到的留空数组。
- 关系两端的实体应出现在 entities 中；若原文仅一侧明确，不要强行造实体。
- 实体 name 尽量使用原文中的完整称谓/全名（如「贾雨村」而非仅「雨村」），除非原文只出现简称。
- 同名实体在整篇文档中必须保持类型一致。如果「已识别实体」中某人已被标记为具体类型（如 Official），即使当前块未提及其职位，也必须沿用该类型，不要降级为 Person 或 Organization。
- Person 和 Organization 是严格的兜底类型，仅用于确实无法归入任何具体类型的实体。
"""


class ChunkOntologyExtractor:
    def __init__(self, llm: Optional[LLMClient] = None):
        self._llm = llm or LLMClient()

    # ── 工具方法 ─────────────────────────────────────────────────────
    def _compress_ontology(self, ontology: Dict[str, Any]) -> str:
        et = ontology.get('entity_types') or []
        ed = ontology.get('edge_types') or []
        lines = ['实体类型:']
        for e in et[:12]:
            lines.append(f"  - {e.get('name')}: {e.get('description', '')[:120]}")
        lines.append('关系类型:')
        for e in ed[:12]:
            lines.append(f"  - {e.get('name')}: {e.get('description', '')[:120]}")
        return '\n'.join(lines)

    def _format_known_entities(
        self,
        known: Dict[str, str],
        relevant_text: Optional[str] = None,
    ) -> str:
        """D5：若 relevant_text 提供，则只输出在文本里实际出现的实体名（纯子串匹配）。
        否则保留旧行为（输出最多 200 个）。
        """
        if not known:
            return ''
        # D5：智能裁剪
        if relevant_text is not None and bool(getattr(Config, 'CHUNK_KNOWN_ENTITIES_TRIM_ENABLED', False)):
            trimmed = {
                nm: et
                for nm, et in known.items()
                if nm and nm in relevant_text
            }
            if not trimmed:
                return ''
            items = list(trimmed.items())[:200]
        else:
            items = list(known.items())[:200]
        lines = ['\n已识别实体（请沿用这些类型，不要降级为兜底类型）:']
        for name, etype in items:
            lines.append(f'  - {name} → {etype}')
        return '\n'.join(lines)

    # ── 单块抽取（旧接口保留）────────────────────────────────────────
    def extract(
        self,
        chunk_text: str,
        ontology: Dict[str, Any],
        known_entities: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not (chunk_text or '').strip():
            return {'entities': [], 'relations': []}
        user = (
            self._compress_ontology(ontology)
            + self._format_known_entities(known_entities or {}, relevant_text=chunk_text)
            + '\n\n--- 文本块 ---\n'
            + chunk_text[:12000]
        )
        try:
            with usage_tags(category='chunk_extract_single'):
                data = self._llm.chat_json(
                    messages=[
                        {'role': 'system', 'content': SYSTEM},
                        {'role': 'user', 'content': user},
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                )
        except Exception as e:
            logger.warning(f'chunk_extract_single 失败: {str(e)[:80]}')
            return {'entities': [], 'relations': []}
        entities = data.get('entities') or []
        relations = data.get('relations') or []
        if not isinstance(entities, list):
            entities = []
        if not isinstance(relations, list):
            relations = []
        return {'entities': entities, 'relations': relations}

    # ── 批抽取（新接口）─────────────────────────────────────────────
    def extract_batch(
        self,
        chunks: List[str],
        ontology: Dict[str, Any],
        known_entities: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """对一组 chunk 一次性抽取，返回长度与 chunks 一致的结果列表。

        D4：任何失败 → 整批回退到单块逐个抽取（兼容兜底）。
        """
        if not chunks:
            return []
        # 全空或只剩一个非空时直接走单块
        non_empty = [c for c in chunks if (c or '').strip()]
        if len(non_empty) <= 1:
            return [self.extract(c, ontology, known_entities) for c in chunks]

        # known_entities 取所有 chunk 文本的并集做裁剪（一个 batch 共享 known 段）
        merged_text = '\n'.join(non_empty)

        ontology_block = self._compress_ontology(ontology)
        known_block = self._format_known_entities(known_entities or {}, relevant_text=merged_text)

        # 拼接 batch user message
        parts = [ontology_block, known_block, '\n\n--- 文本块（按 chunk_index 顺序）---']
        for idx, ch in enumerate(chunks):
            parts.append(f'\n[chunk_index={idx}]')
            parts.append((ch or '')[:12000])
        user = '\n'.join(parts)

        try:
            with usage_tags(category='chunk_extract_batch'):
                # 这里不能用 chat_json（响应是数组而非对象），用 chat 后手解
                raw = self._llm.chat(
                    messages=[
                        {'role': 'system', 'content': SYSTEM_BATCH},
                        {'role': 'user', 'content': user},
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                )
            # 尝试找到 [ ... ] 数组
            stripped = (raw or '').strip()
            arr_start = stripped.find('[')
            arr_end = stripped.rfind(']')
            if arr_start < 0 or arr_end < 0 or arr_end <= arr_start:
                raise ValueError('batch response 不含 JSON 数组')
            arr = json.loads(stripped[arr_start:arr_end + 1])
            if not isinstance(arr, list):
                raise ValueError('batch response 不是数组')

            # 按 chunk_index 回填结果，缺失的视为空
            results: List[Dict[str, Any]] = [{'entities': [], 'relations': []} for _ in chunks]
            for item in arr:
                if not isinstance(item, dict):
                    continue
                try:
                    idx = int(item.get('chunk_index', -1))
                except Exception:
                    idx = -1
                if 0 <= idx < len(chunks):
                    ents = item.get('entities') or []
                    rels = item.get('relations') or []
                    if not isinstance(ents, list):
                        ents = []
                    if not isinstance(rels, list):
                        rels = []
                    results[idx] = {'entities': ents, 'relations': rels}
            return results
        except Exception as e:
            # D4：整批回退到单块
            logger.warning(f'chunk_extract_batch 解析失败，整批回退单块: {str(e)[:120]}')
            return [self.extract(c, ontology, known_entities) for c in chunks]
