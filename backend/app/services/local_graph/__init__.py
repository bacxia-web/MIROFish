"""本地图谱后端：Neo4j（图结构）+ Qdrant（块向量）+ LLM 切块抽取。

注意：不要在包初始化时导入 local_graph_builder / entity_disambiguator，
否则与「from .local_graph.local_graph_builder import …」并发加载时会触发
importlib 重入 KeyError（app.services.local_graph）。
"""

from .chunk_extractor import ChunkOntologyExtractor
from .embedding import EmbeddingService
from .neo4j_store import Neo4jGraphStore
from .qdrant_index import QdrantChunkIndex

__all__ = [
    'Neo4jGraphStore',
    'QdrantChunkIndex',
    'EmbeddingService',
    'ChunkOntologyExtractor',
    'LocalGraphBuilder',
    'EntityDisambiguator',
    'DisambiguationResult',
]


def __getattr__(name: str):
    if name == 'LocalGraphBuilder':
        from .local_graph_builder import LocalGraphBuilder

        return LocalGraphBuilder
    if name == 'EntityDisambiguator':
        from .entity_disambiguator import EntityDisambiguator

        return EntityDisambiguator
    if name == 'DisambiguationResult':
        from .entity_disambiguator import DisambiguationResult

        return DisambiguationResult
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
