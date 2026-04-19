"""Qdrant：文本块向量检索。"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from ...config import Config


def _point_id(graph_id: str, chunk_uuid: str) -> int:
    h = hashlib.sha256(f'{graph_id}:{chunk_uuid}'.encode()).digest()
    return int.from_bytes(h[:8], 'big', signed=False) % (2**63 - 1)


class QdrantChunkIndex:
    def __init__(
        self,
        url: Optional[str] = None,
        collection: Optional[str] = None,
    ):
        self._url = url or Config.QDRANT_URL
        self._collection = collection or Config.QDRANT_COLLECTION_CHUNKS
        self._client = QdrantClient(url=self._url)

    def ensure_collection(self, vector_size: int):
        cols = self._client.get_collections().collections
        names = {c.name for c in cols}
        if self._collection not in names:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
            )

    def upsert_chunk(
        self,
        graph_id: str,
        chunk_uuid: str,
        text: str,
        vector: List[float],
    ):
        self.ensure_collection(len(vector))
        pid = _point_id(graph_id, chunk_uuid)
        payload: Dict[str, Any] = {
            'graph_id': graph_id,
            'chunk_uuid': chunk_uuid,
            'text': text or '',
        }
        self._client.upsert(
            collection_name=self._collection,
            points=[qm.PointStruct(id=pid, vector=vector, payload=payload)],
        )

    def search(self, graph_id: str, query_vector: List[float], limit: int = 15) -> List[Dict[str, Any]]:
        try:
            self.ensure_collection(len(query_vector))
        except Exception:
            return []
        try:
            res = self._client.search(
                collection_name=self._collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=qm.Filter(
                    must=[qm.FieldCondition(key='graph_id', match=qm.MatchValue(value=graph_id))]
                ),
            )
        except Exception:
            return []
        out = []
        for hit in res:
            pl = hit.payload or {}
            out.append({'text': pl.get('text', ''), 'score': hit.score})
        return out

    def delete_graph(self, graph_id: str):
        try:
            self._client.delete(
                collection_name=self._collection,
                points_selector=qm.FilterSelector(
                    filter=qm.Filter(
                        must=[qm.FieldCondition(key='graph_id', match=qm.MatchValue(value=graph_id))]
                    )
                ),
            )
        except Exception:
            pass

    def copy_vectors_between_graphs(self, src_graph_id: str, dst_graph_id: str) -> int:
        """将 src 图下所有 chunk 向量复制为 dst 图（相同 chunk_uuid，不同 graph_id 对应不同 point id）。"""
        filt = qm.Filter(
            must=[qm.FieldCondition(key='graph_id', match=qm.MatchValue(value=src_graph_id))]
        )
        n = 0
        offset = None
        while True:
            res = self._client.scroll(
                collection_name=self._collection,
                scroll_filter=filt,
                limit=128,
                offset=offset,
                with_vectors=True,
            )
            points, offset = res
            if not points:
                break
            for pt in points:
                pl = pt.payload or {}
                cu = pl.get('chunk_uuid')
                text = pl.get('text') or ''
                vec = pt.vector
                if cu and vec is not None:
                    self.upsert_chunk(dst_graph_id, str(cu), text, vec)
                    n += 1
            if offset is None:
                break
        return n
