"""本地构图编排：切块 → LLM 抽取 → Neo4j + Qdrant。"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from ...utils.locale import t

from .chunk_extractor import ChunkOntologyExtractor
from .embedding import EmbeddingService
from .entity_disambiguator import DisambiguationResult, EntityDisambiguator
from .neo4j_store import Neo4jGraphStore
from .qdrant_index import QdrantChunkIndex


class LocalGraphBuilder:
    def __init__(
        self,
        neo: Optional[Neo4jGraphStore] = None,
        qd: Optional[QdrantChunkIndex] = None,
        embedder: Optional[EmbeddingService] = None,
        extractor: Optional[ChunkOntologyExtractor] = None,
    ):
        self.neo = neo or Neo4jGraphStore()
        self.qd = qd or QdrantChunkIndex()
        self.embedder = embedder or EmbeddingService()
        self.extractor = extractor or ChunkOntologyExtractor()

    def create_graph(self, name: str) -> str:
        gid = f'mirofish_{uuid.uuid4().hex[:16]}'
        self.neo.create_graph(gid, name)
        return gid

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        self.neo.set_ontology(graph_id, ontology)

    _FALLBACK_TYPES = {'Person', 'Organization', 'Entity'}

    def ingest_chunk(
        self,
        graph_id: str,
        chunk_text: str,
        ontology: Dict[str, Any],
        known_entities: Optional[Dict[str, str]] = None,
        enhanced: bool = True,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Tuple[str, Dict[str, str]]:
        """抽取并入库一个切块，返回 (chunk_uuid, 本次新增/更新的 entity_name→type 映射)。

        Args:
            enhanced: True 时传递 known_entities 上下文 + 跨标签类型提升；False 为旧逻辑对照组。
        """
        ctx = known_entities if enhanced else None
        extracted = self.extractor.extract(chunk_text, ontology, ctx)
        chunk_uuid = self.neo.ingest_chunk_with_extract(
            graph_id, chunk_text, extracted, cross_label_promotion=enhanced,
        )
        new_entities: Dict[str, str] = {}
        for ent in extracted.get('entities') or []:
            if isinstance(ent, dict):
                nm = (ent.get('name') or '').strip()
                et = (ent.get('entity_type') or '').strip()
                if nm and et:
                    new_entities[nm] = et
        try:
            vec = self.embedder.embed_one(chunk_text)
            self.qd.upsert_chunk(graph_id, chunk_uuid, chunk_text, vec)
        except Exception as ex:
            if progress_callback:
                progress_callback(t('progress.vectorIndexSkip', error=str(ex)), 0)
        return chunk_uuid, new_entities

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        ontology: Dict[str, Any],
        batch_size: int = 3,
        enhanced: bool = True,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        chunk_complete_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[str]:
        """顺序处理切块；返回 chunk uuid 列表。

        Args:
            enhanced: True 时启用跨块上下文 + 跨标签类型提升（实验组）；False 为旧逻辑（对照组）。
        """
        uuids: List[str] = []
        known_entities: Dict[str, str] = {}
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            cu, new_ents = self.ingest_chunk(
                graph_id, chunk, ontology, known_entities,
                enhanced=enhanced, progress_callback=progress_callback,
            )
            uuids.append(cu)
            if enhanced:
                for nm, et in new_ents.items():
                    existing = known_entities.get(nm, '')
                    if existing in self._FALLBACK_TYPES or not existing:
                        known_entities[nm] = et
                    elif et not in self._FALLBACK_TYPES:
                        known_entities[nm] = et
            if progress_callback and total:
                progress_callback(
                    t('progress.localIngestChunks', current=i + 1, total=total),
                    (i + 1) / total,
                )
            if chunk_complete_callback and total:
                chunk_complete_callback(i + 1, total)
        return uuids

    def build_raw_then_disambiguated(
        self,
        graph_name: str,
        chunks: List[str],
        ontology: Dict[str, Any],
        batch_size: int = 3,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        ontology_enhanced: Optional[Dict[str, Any]] = None,
        persist_project_graph_ids: Optional[Callable[[Dict[str, Any]], None]] = None,
        chunk_stream_hook: Optional[Callable[[], None]] = None,
    ) -> Tuple[str, str, DisambiguationResult]:
        """A/B 双管线构图——从本体开始完全分叉。

        - A（对照组）：原始本体 + 旧抽取(无跨块上下文) + 旧入库(无跨标签提升) + 不消歧。
        - B（实验组）：增强本体 + 新抽取(跨块上下文) + 新入库(跨标签提升) + 消歧。

        Args:
            ontology: 对照组本体（原始 prompt 生成）。
            ontology_enhanced: 实验组本体（增强 prompt 生成）；为 None 时 B 也用 ontology。

        返回 (graph_id_raw, graph_id_disamb, disamb_result)。
        """
        ont_b = ontology_enhanced if ontology_enhanced else ontology

        def _pcb(prefix: str, lo: float, hi: float):
            def cb(msg: str, ratio: float):
                if progress_callback:
                    progress_callback(f'[{prefix}] {msg}', lo + (hi - lo) * ratio)
            return cb

        def _chunk_hook() -> Optional[Callable[[int, int], None]]:
            if not chunk_stream_hook:
                return None

            def _inner(_ci: int, _tot: int) -> None:
                chunk_stream_hook()

            return _inner

        # --- A 路径（对照组）：原始本体 + 旧逻辑 ---
        raw_id = self.create_graph(f'{graph_name} (raw)')
        self.set_ontology(raw_id, ontology)
        if persist_project_graph_ids:
            persist_project_graph_ids(
                {
                    'graph_id_raw': raw_id,
                    'graph_id': raw_id,
                    'reset_experimental_branch': True,
                }
            )
        self.add_text_batches(
            raw_id,
            chunks,
            ontology,
            batch_size,
            enhanced=False,
            progress_callback=_pcb(t('progress.abControlShort'), 0.0, 0.45),
            chunk_complete_callback=_chunk_hook(),
        )

        # --- B 路径（实验组）：增强本体 + 新逻辑 + 消歧 ---
        dis_id = self.create_graph(f'{graph_name} (disambiguated)')
        self.set_ontology(dis_id, ont_b)
        if persist_project_graph_ids:
            persist_project_graph_ids(
                {
                    'graph_id_disamb': dis_id,
                    'graph_id': dis_id,
                }
            )
        self.add_text_batches(
            dis_id,
            chunks,
            ont_b,
            batch_size,
            enhanced=True,
            progress_callback=_pcb(t('progress.abTreatmentShort'), 0.45, 0.85),
            chunk_complete_callback=_chunk_hook(),
        )

        def _dcb(msg: str, ratio: float):
            if progress_callback:
                progress_callback(
                    f'[{t("progress.disambShort")}] {msg}', 0.85 + 0.14 * ratio
                )

        dis = EntityDisambiguator(neo=self.neo, embedder=self.embedder)
        dres = dis.run(dis_id, progress_callback=_dcb)

        return raw_id, dis_id, dres

    def delete_graph(self, graph_id: str):
        self.qd.delete_graph(graph_id)
        self.neo.delete_graph(graph_id)
