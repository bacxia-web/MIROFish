"""Plan #3 · 报告对话 RAG：把已生成的报告按二级标题切块，向量化入 Qdrant，
聊天时按 top-K 检索相关段落，替代"塞前 15000 字"的硬填充。

设计要点
--------
- D9：按 Markdown 二级标题 `## ...` 切段（语义边界自然）
- D11：异步建索引（不阻塞用户）
- D12：新建独立 collection `report_chunks`，与图谱 chunks 隔离
- 索引失败 / 检索为空 / RAG 关闭时 → fallback 到前 15000 字硬塞（旧行为）
- usage_tags：嵌入调用打 category="report_rag_embedding"，
  整体节省发生在主对话模型（不再需要把整份报告塞 prompt）
"""

from __future__ import annotations

import hashlib
import re
import threading
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from ..config import Config
from ..utils.logger import get_logger
from ..utils.token_usage_service import usage_tags
from .local_graph.embedding import EmbeddingService

logger = get_logger('mirofish.report_rag')


def _point_id(report_id: str, section_idx: int) -> int:
    h = hashlib.sha256(f'{report_id}:sec:{section_idx}'.encode()).digest()
    return int.from_bytes(h[:8], 'big', signed=False) % (2**63 - 1)


# 新建独立 collection（D12）
DEFAULT_COLLECTION = 'report_chunks'


class ReportRAGIndex:
    """报告向量索引 + 检索。线程安全。"""

    _build_locks: Dict[str, threading.Lock] = {}
    _global_lock = threading.Lock()

    def __init__(
        self,
        embedder: Optional[EmbeddingService] = None,
        url: Optional[str] = None,
        collection: Optional[str] = None,
    ):
        self._embedder = embedder or EmbeddingService()
        self._url = url or Config.QDRANT_URL
        self._collection = collection or DEFAULT_COLLECTION
        self._client = QdrantClient(url=self._url)

    # ── 切块 ───────────────────────────────────────────────────────
    @staticmethod
    def split_by_h2(markdown_content: str) -> List[Dict[str, Any]]:
        """D9：按 `## ` 二级标题切段。每段附带前后兄弟章节标题作为 metadata。"""
        if not markdown_content:
            return []
        # 以 `^## ` 为切点（也兼容 `^# `，但优先二级；retreating fallback 为整体一段）
        lines = markdown_content.splitlines(keepends=True)
        chunks: List[Dict[str, Any]] = []
        cur_title = ""
        cur_buf: List[str] = []

        def flush():
            if cur_buf and (''.join(cur_buf)).strip():
                chunks.append({
                    "section_title": cur_title or "（无标题）",
                    "text": ''.join(cur_buf).strip(),
                })

        h_re = re.compile(r'^\s*##\s+(.+?)\s*$')
        for line in lines:
            m = h_re.match(line)
            if m:
                flush()
                cur_title = m.group(1).strip()
                cur_buf = [line]
            else:
                cur_buf.append(line)
        flush()

        if not chunks:
            # 没有任何二级标题 → 当整体一段
            chunks = [{"section_title": "全文", "text": markdown_content.strip()}]
        # 附 metadata: prev / next sibling titles
        for i, ch in enumerate(chunks):
            ch["section_index"] = i
            ch["prev_section_title"] = chunks[i - 1]["section_title"] if i > 0 else ""
            ch["next_section_title"] = chunks[i + 1]["section_title"] if i + 1 < len(chunks) else ""
        return chunks

    # ── 建索引 ─────────────────────────────────────────────────────
    def _ensure_collection(self, vector_size: int):
        try:
            cols = self._client.get_collections().collections
            names = {c.name for c in cols}
            if self._collection not in names:
                self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
                )
        except Exception as e:
            logger.warning(f"ensure_collection 失败: {e}")

    def build(self, report_id: str, markdown_content: str) -> int:
        """同步建索引，返回入库段数。失败 → 返回 0（调用方自行 fallback）。"""
        if not report_id or not markdown_content:
            return 0
        chunks = self.split_by_h2(markdown_content)
        if not chunks:
            return 0
        try:
            # 先批量 embed
            texts = [f"# {c['section_title']}\n\n{c['text']}" for c in chunks]
            with usage_tags(category='report_rag_embedding'):
                vectors = self._embedder.embed_texts(texts)
            if not vectors or len(vectors) != len(texts):
                logger.warning(f"embed 数量不匹配 {len(vectors) if vectors else 0} vs {len(texts)}")
                return 0
            self._ensure_collection(len(vectors[0]))

            # 删旧 → 写新（避免重生成时残留）
            self.delete(report_id)
            points = []
            for i, (ch, vec) in enumerate(zip(chunks, vectors)):
                payload = {
                    "report_id": report_id,
                    "section_index": ch["section_index"],
                    "section_title": ch["section_title"],
                    "prev_section_title": ch["prev_section_title"],
                    "next_section_title": ch["next_section_title"],
                    "text": ch["text"],
                }
                points.append(qm.PointStruct(
                    id=_point_id(report_id, i),
                    vector=vec,
                    payload=payload,
                ))
            self._client.upsert(collection_name=self._collection, points=points)
            return len(points)
        except Exception as e:
            logger.warning(f"report RAG 建索引失败 report_id={report_id}: {e}")
            return 0

    def build_async(self, report_id: str, markdown_content: str) -> None:
        """D11：异步建索引，立即返回，不阻塞用户。"""
        with self._global_lock:
            if report_id in self._build_locks and self._build_locks[report_id].locked():
                logger.info(f"report_id={report_id} 已在建索引，跳过重复触发")
                return
            self._build_locks[report_id] = threading.Lock()

        def _worker():
            lock = self._build_locks.get(report_id)
            if lock is None:
                return
            with lock:
                try:
                    n = self.build(report_id, markdown_content)
                    logger.info(f"[opt] report RAG 索引完成 report_id={report_id} 段数={n}")
                except Exception as e:
                    logger.warning(f"异步建索引异常 {report_id}: {e}")

        t = threading.Thread(target=_worker, daemon=True, name=f"report_rag_build_{report_id[:8]}")
        t.start()

    # ── 检索 ───────────────────────────────────────────────────────
    def query(self, report_id: str, user_msg: str, k: int = 3) -> List[Dict[str, Any]]:
        if not user_msg or not report_id:
            return []
        try:
            with usage_tags(category='report_rag_embedding'):
                vec = self._embedder.embed_one(user_msg)
            self._ensure_collection(len(vec))
            res = self._client.search(
                collection_name=self._collection,
                query_vector=vec,
                limit=max(1, k),
                query_filter=qm.Filter(
                    must=[qm.FieldCondition(key='report_id', match=qm.MatchValue(value=report_id))]
                ),
            )
            out = []
            for hit in res:
                pl = hit.payload or {}
                out.append({
                    "score": hit.score,
                    "section_title": pl.get("section_title", ""),
                    "section_index": pl.get("section_index", -1),
                    "text": pl.get("text", ""),
                    "prev_section_title": pl.get("prev_section_title", ""),
                    "next_section_title": pl.get("next_section_title", ""),
                })
            return out
        except Exception as e:
            logger.warning(f"report RAG 检索失败 report_id={report_id}: {e}")
            return []

    def delete(self, report_id: str) -> None:
        try:
            self._client.delete(
                collection_name=self._collection,
                points_selector=qm.FilterSelector(
                    filter=qm.Filter(
                        must=[qm.FieldCondition(key='report_id', match=qm.MatchValue(value=report_id))]
                    )
                ),
            )
        except Exception:
            pass


# 单例（避免反复连 Qdrant）
_INSTANCE: Optional[ReportRAGIndex] = None
_INSTANCE_LOCK = threading.Lock()


def get_report_rag() -> ReportRAGIndex:
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = ReportRAGIndex()
        return _INSTANCE
