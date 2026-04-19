"""基于 Neo4j 的图谱质量统计（单 graph_id）。"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict

from .local_graph.neo4j_store import Neo4jGraphStore


def compute_graph_layer(neo: Neo4jGraphStore, graph_id: str) -> Dict[str, Any]:
    nodes = neo.list_nodes_raw(graph_id)
    edges = neo.list_edges_raw(graph_id)
    degree: Dict[str, int] = defaultdict(int)
    for e in edges:
        degree[e.source_node_uuid] += 1
        degree[e.target_node_uuid] += 1
    n_entity = len(nodes)
    isolated = sum(1 for n in nodes if degree.get(n.uuid_, 0) == 0)
    total_deg = sum(degree.get(n.uuid_, 0) for n in nodes)
    avg_degree = (total_deg / n_entity) if n_entity else 0.0
    iso_ratio = (isolated / n_entity) if n_entity else 0.0

    pair_type_counts: Dict[tuple, int] = defaultdict(int)
    for e in edges:
        a, b = sorted([e.source_node_uuid, e.target_node_uuid])
        key = (a, b, e.name or 'REL')
        pair_type_counts[key] += 1
    multi_edge_pairs = sum(1 for c in pair_type_counts.values() if c > 1)

    alias_total = _alias_list_total(neo, graph_id)

    return {
        'graph_id': graph_id,
        'node_count': n_entity,
        'edge_count': len(edges),
        'entity_node_count': n_entity,
        'isolated_node_ratio': round(iso_ratio, 6),
        'avg_degree': round(avg_degree, 4),
        'multi_edge_pair_count': multi_edge_pairs,
        'alias_count_total': alias_total,
    }


def _alias_list_total(neo: Neo4jGraphStore, graph_id: str) -> int:
    total = 0
    try:
        with neo._sess() as session:
            for r in session.run(
                """
                MATCH (:MGraph {graph_id: $gid})-[:HAS_ENTITY]->(e:MEntity {graph_id: $gid})
                WHERE e.aliases_json IS NOT NULL AND e.aliases_json NOT IN ['', '[]']
                RETURN e.aliases_json as aj
                """,
                gid=graph_id,
            ):
                try:
                    arr = json.loads(r['aj'])
                    if isinstance(arr, list):
                        total += len(arr)
                except Exception:
                    pass
    except Exception:
        pass
    return total


def graph_delta(raw_metrics: Dict[str, Any], disamb_metrics: Dict[str, Any]) -> Dict[str, Any]:
    rn = max(raw_metrics.get('node_count') or 0, 1)
    re = max(raw_metrics.get('edge_count') or 0, 1)
    dn = disamb_metrics.get('node_count') or 0
    de = disamb_metrics.get('edge_count') or 0
    return {
        'node_reduction_ratio': round(1.0 - dn / rn, 6),
        'edge_reduction_ratio': round(1.0 - de / re, 6),
    }
