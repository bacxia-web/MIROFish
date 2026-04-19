"""使用 LLM 按本体从文本块抽取实体与关系（替代 Zep 服务端抽取）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...utils.llm_client import LLMClient

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


class ChunkOntologyExtractor:
    def __init__(self, llm: Optional[LLMClient] = None):
        self._llm = llm or LLMClient()

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

    def _format_known_entities(self, known: Dict[str, str]) -> str:
        if not known:
            return ''
        lines = ['\n已识别实体（请沿用这些类型，不要降级为兜底类型）:']
        for name, etype in list(known.items())[:200]:
            lines.append(f'  - {name} → {etype}')
        return '\n'.join(lines)

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
            + self._format_known_entities(known_entities or {})
            + '\n\n--- 文本块 ---\n'
            + chunk_text[:12000]
        )
        try:
            data = self._llm.chat_json(
                messages=[
                    {'role': 'system', 'content': SYSTEM},
                    {'role': 'user', 'content': user},
                ],
                temperature=0.1,
                max_tokens=4096,
            )
        except Exception:
            return {'entities': [], 'relations': []}
        entities = data.get('entities') or []
        relations = data.get('relations') or []
        if not isinstance(entities, list):
            entities = []
        if not isinstance(relations, list):
            relations = []
        return {'entities': entities, 'relations': relations}
