"""实体消歧：候选对 → LLM 判定 → 传递闭包合并组 → Neo4j 执行。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ...utils.locale import t
from ...utils.llm_client import LLMClient
from .embedding import EmbeddingService
from .neo4j_store import Neo4jGraphStore, _NsEdge, _NsNode, _norm_name


def _tokens(text: str) -> Set[str]:
    if not text:
        return set()
    parts = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}', (text or '').lower())
    return {p for p in parts if len(p) >= 2}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 0.0
    u = a | b
    if not u:
        return 0.0
    return len(a & b) / len(u)


def _name_match_score(s1: str, s2: str) -> float:
    n1, n2 = (s1 or '').strip(), (s2 or '').strip()
    ln1, ln2 = n1.lower(), n2.lower()
    if not n1 or not n2:
        return 0.0
    if ln1 in ln2 or ln2 in ln1:
        return 0.95
    return SequenceMatcher(None, ln1, ln2).ratio()


class _UnionFind:
    def __init__(self):
        self._p: Dict[str, str] = {}

    def find(self, x: str) -> str:
        if x not in self._p:
            self._p[x] = x
        if self._p[x] != x:
            self._p[x] = self.find(self._p[x])
        return self._p[x]

    def union(self, a: str, b: str):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._p[rb] = ra


@dataclass
class DisambiguationMergeRecord:
    """单次合并组（传递闭包后写入 Neo4j 的一次 merge_duplicate_entities）。"""

    canonical_name: str
    kept_uuid: str
    keep_name_before: str
    removed_uuids: List[str]
    removed_names: List[str]
    primary_label: Optional[str] = None


@dataclass
class DisambiguationResult:
    merged_groups: int = 0
    removed_nodes: int = 0
    pair_decisions: int = 0
    merge_records: List[DisambiguationMergeRecord] = field(default_factory=list)
    pair_decision_details: List[Dict[str, Any]] = field(default_factory=list)
    precision_merge_rate: Optional[float] = None


class EntityDisambiguator:
    """在单张图（通常为 disamb 副本）上执行消歧。"""

    def __init__(
        self,
        neo: Optional[Neo4jGraphStore] = None,
        llm: Optional[LLMClient] = None,
        embedder: Optional[EmbeddingService] = None,
        embed_sim_threshold: float = 0.72,
        name_sim_threshold: float = 0.6,
        jaccard_threshold: float = 0.3,
        llm_confidence_threshold: float = 0.85,
    ):
        self.neo = neo or Neo4jGraphStore()
        self.llm = llm
        self.embedder = embedder
        self.embed_sim_threshold = embed_sim_threshold
        self.name_sim_threshold = name_sim_threshold
        self.jaccard_threshold = jaccard_threshold
        self.llm_confidence_threshold = llm_confidence_threshold

    def run(
        self,
        graph_id: str,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> DisambiguationResult:
        result = DisambiguationResult()
        nodes = self.neo.list_nodes_raw(graph_id)
        edges_by: Dict[str, List[_NsEdge]] = {}
        for e in self.neo.list_edges_raw(graph_id):
            edges_by.setdefault(e.source_node_uuid, []).append(e)
            edges_by.setdefault(e.target_node_uuid, []).append(e)

        by_label: Dict[str, List[_NsNode]] = {}
        for n in nodes:
            by_label.setdefault(n.primary_label or 'Entity', []).append(n)

        pair_decisions: List[Tuple[str, str, str, str]] = []
        seen: Set[Tuple[str, str]] = set()

        for _pl, group in by_label.items():
            if len(group) < 2:
                continue
            candidates: List[Tuple[_NsNode, _NsNode, float]] = []
            for i, a in enumerate(group):
                for b in group[i + 1 :]:
                    ua, ub = a.uuid_, b.uuid_
                    key = tuple(sorted((ua, ub)))
                    if key in seen:
                        continue
                    ns = _name_match_score(a.name, b.name)
                    jac = _jaccard(_tokens(a.summary), _tokens(b.summary))
                    ok_name = ns >= self.name_sim_threshold
                    ok_jac = jac >= self.jaccard_threshold
                    if not (ok_name or ok_jac):
                        continue
                    if self.embedder:
                        try:
                            t1 = f'{a.name}\n{a.summary or ""}'
                            t2 = f'{b.name}\n{b.summary or ""}'
                            v1 = self.embedder.embed_one(t1)
                            v2 = self.embedder.embed_one(t2)
                            dot = sum(x * y for x, y in zip(v1, v2))
                            n1 = sum(x * x for x in v1) ** 0.5
                            n2 = sum(x * x for x in v2) ** 0.5
                            cos = dot / (n1 * n2) if n1 and n2 else 0.0
                            if cos < self.embed_sim_threshold:
                                continue
                        except Exception:
                            pass
                    candidates.append((a, b, max(ns, jac)))
                    seen.add(key)

            if not candidates:
                continue
            candidates.sort(key=lambda x: -x[2])
            batch_size = 10
            for start in range(0, len(candidates), batch_size):
                batch = candidates[start : start + batch_size]
                llm_out = self._llm_batch(graph_id, batch, edges_by)
                result.pair_decisions += len(llm_out)
                # 逐条写明细（先按“未最终合并”记录，后续命中 union 条件时再回填）
                for item in llm_out:
                    idx = int(item.get('pair_index', -1))
                    if idx < 0 or idx >= len(batch):
                        result.pair_decision_details.append(
                            {
                                'pair_index': idx,
                                'entity_a': None,
                                'entity_b': None,
                                'same_entity': bool(item.get('same_entity')),
                                'confidence': float(item.get('confidence') or 0.0),
                                'canonical_name': (item.get('canonical_name') or '').strip(),
                                'final_merged': False,
                                'reject_reason': 'invalid_index',
                            }
                        )
                        continue
                    na, nb, _ = batch[idx]
                    same_entity = bool(item.get('same_entity'))
                    conf = float(item.get('confidence') or 0.0)
                    reject_reason = ''
                    if not same_entity:
                        reject_reason = 'same_entity_false'
                    elif conf < self.llm_confidence_threshold:
                        reject_reason = 'confidence_below_threshold'
                    result.pair_decision_details.append(
                        {
                            'pair_index': idx,
                            'entity_a': {
                                'uuid': na.uuid_,
                                'name': na.name,
                                'label': na.primary_label,
                            },
                            'entity_b': {
                                'uuid': nb.uuid_,
                                'name': nb.name,
                                'label': nb.primary_label,
                            },
                            'same_entity': same_entity,
                            'confidence': conf,
                            'canonical_name': (item.get('canonical_name') or '').strip(),
                            'final_merged': False,
                            'reject_reason': reject_reason,
                        }
                    )
                for item in llm_out:
                    if not item.get('same_entity'):
                        continue
                    conf = float(item.get('confidence') or 0.0)
                    if conf < self.llm_confidence_threshold:
                        continue
                    idx = int(item.get('pair_index', -1))
                    if idx < 0 or idx >= len(batch):
                        continue
                    na, nb, _ = batch[idx]
                    pair_decisions.append(
                        (
                            na.uuid_,
                            nb.uuid_,
                            (item.get('canonical_name') or na.name or nb.name).strip(),
                            str(item.get('confidence') or ''),
                        )
                    )

        if progress_callback:
            progress_callback(t('progress.disambMergingTransitive'), 0.92)

        uf = _UnionFind()
        for ua, ub, _, _ in pair_decisions:
            uf.union(ua, ub)

        merged_pairs: Set[Tuple[str, str]] = set()
        for ua, ub, _, _ in pair_decisions:
            merged_pairs.add(tuple(sorted((ua, ub))))
        for d in result.pair_decision_details:
            a = (d.get('entity_a') or {}).get('uuid')
            b = (d.get('entity_b') or {}).get('uuid')
            if not a or not b:
                continue
            if tuple(sorted((a, b))) in merged_pairs:
                d['final_merged'] = True
                d['reject_reason'] = ''

        involved: Set[str] = set()
        for ua, ub, _, _ in pair_decisions:
            involved.add(ua)
            involved.add(ub)
        root_to_members: Dict[str, Set[str]] = {}
        for u in involved:
            r = uf.find(u)
            root_to_members.setdefault(r, set()).add(u)

        for _root, members in root_to_members.items():
            uniq = list(members)
            if len(uniq) < 2:
                continue
            uuid_to_node = {n.uuid_: n for n in nodes}
            scored: List[Tuple[float, int, str, _NsNode]] = []
            for uid in uniq:
                n = uuid_to_node.get(uid)
                if not n:
                    continue
                scored.append((len(n.name or ''), len(n.summary or ''), uid, n))
            scored.sort(reverse=True)
            keep = scored[0][2]
            remove = [u for u in uniq if u != keep]
            alias_names: List[str] = []
            canonical = ''
            for ua, ub, cn, _c in pair_decisions:
                if ua in uniq and ub in uniq:
                    if cn:
                        canonical = cn
                    break
            if not canonical:
                canonical = uuid_to_node[keep].name
            for uid in uniq:
                if uid == keep:
                    continue
                nn = uuid_to_node.get(uid)
                if nn:
                    alias_names.append(nn.name)
            keep_node = uuid_to_node.get(keep)
            removed_names_list: List[str] = []
            for ru in remove:
                nn = uuid_to_node.get(ru)
                if nn and (nn.name or '').strip():
                    removed_names_list.append((nn.name or '').strip())
            result.merge_records.append(
                DisambiguationMergeRecord(
                    canonical_name=(canonical or '').strip(),
                    kept_uuid=keep,
                    keep_name_before=(keep_node.name or '').strip() if keep_node else '',
                    removed_uuids=list(remove),
                    removed_names=removed_names_list,
                    primary_label=(
                        (keep_node.primary_label or None) if keep_node else None
                    ),
                )
            )
            self.neo.merge_duplicate_entities(
                graph_id,
                keep,
                remove,
                alias_names,
                canonical_name=canonical,
            )
            result.merged_groups += 1
            result.removed_nodes += len(remove)

        if progress_callback:
            progress_callback(
                t(
                    'progress.disambCompleteSummary',
                    groups=result.merged_groups,
                    removed=result.removed_nodes,
                ),
                1.0,
            )
        if result.pair_decisions > 0:
            result.precision_merge_rate = round(
                len(pair_decisions) / result.pair_decisions, 4
            )
        else:
            result.precision_merge_rate = None
        return result

    def _facts_snippet(self, graph_id: str, uid: str, edges_by: Dict[str, List[_NsEdge]], nodes: Dict[str, _NsNode], limit: int = 3) -> List[str]:
        out: List[str] = []
        for e in edges_by.get(uid, [])[: limit * 2]:
            if len(out) >= limit:
                break
            oth = e.target_node_uuid if e.source_node_uuid == uid else e.source_node_uuid
            on = nodes.get(oth)
            tag = on.name if on else oth[:8]
            out.append(f"{tag}: {e.fact or e.name}"[:200])
        return out[:limit]

    def _llm_batch(
        self,
        graph_id: str,
        batch: List[Tuple[_NsNode, _NsNode, float]],
        edges_by: Dict[str, List[_NsEdge]],
    ) -> List[Dict[str, Any]]:
        nodes = {n.uuid_: n for n in self.neo.list_nodes_raw(graph_id)}
        lines = []
        for idx, (a, b, _s) in enumerate(batch):
            fa = self._facts_snippet(graph_id, a.uuid_, edges_by, nodes)
            fb = self._facts_snippet(graph_id, b.uuid_, edges_by, nodes)
            lines.append(
                f'{idx}. A: name="{a.name}", type={a.primary_label}, summary="{(a.summary or "")[:400]}" facts={fa}\n'
                f'   B: name="{b.name}", type={b.primary_label}, summary="{(b.summary or "")[:400]}" facts={fb}'
            )
        user = '实体对:\n' + '\n'.join(lines)
        system = """你是知识图谱消歧专家。判断每对实体是否指向同一真实世界对象（同一人、同一组织等）。
必须只输出 JSON 数组，无其它文字。每项格式:
{"pair_index": 0, "same_entity": true, "canonical_name": "规范中文名", "confidence": 0.92}
 same_entity 为 false 时 canonical_name 可为空。confidence 介于 0 到 1。"""

        if not self.llm:
            try:
                self.llm = LLMClient()
            except Exception:
                return []

        try:
            raw = self.llm.chat(
                messages=[
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                temperature=0.1,
                max_tokens=4096,
            )
            arr = json.loads(raw) if raw.strip().startswith('[') else json.loads(raw[raw.find('[') : raw.rfind(']') + 1])
        except Exception:
            try:
                data = self.llm.chat_json(
                    messages=[
                        {'role': 'system', 'content': system},
                        {'role': 'user', 'content': user},
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                )
                arr = data if isinstance(data, list) else data.get('results') or data.get('pairs') or []
            except Exception:
                return []
        if not isinstance(arr, list):
            return []
        out: List[Dict[str, Any]] = []
        for item in arr:
            if isinstance(item, dict):
                out.append(item)
        return out
