"""质量指标：内存埋点 + 落盘 + 聚合 API。"""

from __future__ import annotations

import json
import os
import threading
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..config import Config
from ..models.project import ProjectManager
from .graph_quality import compute_graph_layer, graph_delta
from .local_graph.neo4j_store import Neo4jGraphStore
from ..utils.token_usage_service import snapshot_token_usage

_lock = threading.Lock()
# graph_id -> 检索调用统计
_search_stats: Dict[str, Dict[str, Any]] = {}
# (project_id, graph_id) -> 仿真侧指标
_sim_stats: Dict[str, Dict[str, Any]] = {}
# (project_id, graph_id, platform) -> 发帖重复统计
_post_stats: Dict[str, Dict[str, Any]] = {}

# 每个 graph_id 在内存中最多保留的空检索 query 条数（含重试后仍为空的上报）
_MAX_EMPTY_QUERY_SAMPLES = 400
# 写入 quality_metrics 时每图最多附带最近 N 条
_SNAPSHOT_EMPTY_QUERIES = 150


def _sim_key(project_id: str, graph_id: str) -> str:
    return f'{project_id}:{graph_id}'


def _post_key(project_id: str, graph_id: str, platform: str) -> str:
    return f'{project_id}:{graph_id}:{(platform or "unknown").strip().lower()}'


def _normalize_post_text(text: Any) -> str:
    s = str(text or '')
    s = ' '.join(s.split())
    return s.strip().lower()


def record_search_graph_metrics(
    graph_id: str, total_count: int, query: Optional[str] = None
) -> None:
    """记录 search_graph 调用；若最终 merged 结果仍为空，可选记下原始 query（供审计）。"""
    if not graph_id:
        return
    with _lock:
        s = _search_stats.setdefault(
            graph_id,
            {'calls': 0, 'result_hits_sum': 0, 'empty_calls': 0, 'empty_queries': []},
        )
        if 'empty_queries' not in s:
            s['empty_queries'] = []
        s['calls'] += 1
        s['result_hits_sum'] += int(total_count or 0)
        if not total_count:
            s['empty_calls'] += 1
            q = (query or '').strip()
            if q:
                eq: List[Dict[str, Any]] = s['empty_queries']
                if len(eq) < _MAX_EMPTY_QUERY_SAMPLES:
                    eq.append({
                        'query': q[:4000],
                        'at': datetime.now(timezone.utc).isoformat(),
                    })


def record_simulation_profile_metrics(
    project_id: str, graph_id: str, profiles: List[Any],
) -> None:
    if not project_id or not graph_id:
        return
    names: List[str] = []
    for p in profiles:
        if isinstance(p, dict):
            nm = (p.get('name') or p.get('user_id') or p.get('agent_id') or '').strip()
        else:
            nm = (
                str(getattr(p, 'name', None) or getattr(p, 'user_name', None) or '')
            ).strip()
        if nm:
            names.append(nm)
    c = Counter(names)
    dup_groups = sum(1 for _n, k in c.items() if k > 1)
    key = _sim_key(project_id, graph_id)
    with _lock:
        old = dict(_sim_stats.get(key) or {})
        old.update({
            'agent_count': len(profiles),
            'duplicate_display_name_groups': dup_groups,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        })
        _sim_stats[key] = old


def record_simulation_post_metrics(
    project_id: str,
    graph_id: str,
    platform: str,
    post_content: Any,
) -> None:
    """记录发帖重复统计：严格重复（归一化后文本完全一致）。"""
    if not project_id or not graph_id or not platform:
        return
    key = _post_key(project_id, graph_id, platform)
    norm = _normalize_post_text(post_content)
    with _lock:
        slot = _post_stats.setdefault(
            key,
            {
                'total_count': 0,
                'ignored_empty_posts': 0,
                'counts': {},
                'updated_at': None,
            },
        )
        if not norm:
            slot['ignored_empty_posts'] += 1
            slot['updated_at'] = datetime.now(timezone.utc).isoformat()
            return
        slot['total_count'] += 1
        c = slot['counts']
        c[norm] = int(c.get(norm, 0)) + 1
        slot['updated_at'] = datetime.now(timezone.utc).isoformat()


def _snapshot_search(graph_id: str) -> Dict[str, Any]:
    with _lock:
        s = _search_stats.get(graph_id)
    if not s or not s.get('calls'):
        return {
            'search_graph_calls': 0,
            'search_graph_result_hits_sum': 0,
            'search_graph_empty_calls': 0,
            'search_graph_nonempty_calls': 0,
            'search_graph_avg_result_count': 0.0,
            'search_graph_avg_result_count_on_hit': None,
            'search_graph_empty_rate': 0.0,
            'search_graph_empty_queries': [],
            'search_graph_empty_queries_recorded': 0,
        }
    calls_n = int(s.get('calls') or 0)
    calls = max(calls_n, 1)
    hits = int(s.get('result_hits_sum') or 0)
    empty = int(s.get('empty_calls') or 0)
    nonempty = max(calls_n - empty, 0)
    # 空检索对 result_hits_sum 贡献为 0，故 hits 即「有结果」各次的命中条数之和
    avg_on_hit = round(hits / nonempty, 4) if nonempty else None
    eq = list(s.get('empty_queries') or [])
    tail = eq[-_SNAPSHOT_EMPTY_QUERIES:]
    return {
        'search_graph_calls': calls_n,
        'search_graph_result_hits_sum': hits,
        'search_graph_empty_calls': empty,
        'search_graph_nonempty_calls': nonempty,
        'search_graph_avg_result_count': round(hits / calls, 4),
        'search_graph_avg_result_count_on_hit': avg_on_hit,
        'search_graph_empty_rate': round(empty / calls, 4),
        'search_graph_empty_queries': tail,
        'search_graph_empty_queries_recorded': len(eq),
    }


def _sim_for_project(project_id: str, graph_id: Optional[str]) -> Dict[str, Any]:
    if not graph_id:
        return {}
    key = _sim_key(project_id, graph_id)
    prefix = f'{project_id}:{graph_id}:'
    with _lock:
        base = dict(_sim_stats.get(key) or {})
        by_platform: Dict[str, Any] = {}
        for full_key, stat in _post_stats.items():
            if not full_key.startswith(prefix):
                continue
            platform = full_key[len(prefix):]
            counts = dict(stat.get('counts') or {})
            total = int(stat.get('total_count') or 0)
            unique = len(counts)
            dup_groups = sum(1 for _k, v in counts.items() if int(v) > 1)
            max_repeat = max(counts.values()) if counts else 0
            by_platform[platform] = {
                'post_total_count': total,
                'post_unique_count': unique,
                'post_duplicate_count': max(total - unique, 0),
                'duplicate_post_groups': dup_groups,
                'max_repeat_count': int(max_repeat),
                'ignored_empty_posts': int(stat.get('ignored_empty_posts') or 0),
                'updated_at': stat.get('updated_at'),
            }
    if by_platform:
        base['post_metrics_by_platform'] = by_platform
    return base


def _quality_metrics_paths(project_id: str) -> Tuple[str, str]:
    base = ProjectManager._get_project_dir(project_id)
    full = os.path.join(base, 'quality_metrics.json')
    return base, full


def _retrieval_ab_eval_path(project_id: str) -> str:
    base, _ = _quality_metrics_paths(project_id)
    return os.path.join(base, 'retrieval_ab_eval.json')


def save_quality_metrics_file(project_id: str, payload: Dict[str, Any]) -> None:
    _, path = _quality_metrics_paths(project_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_retrieval_ab_eval_file(project_id: str, payload: Dict[str, Any]) -> None:
    path = _retrieval_ab_eval_path(project_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_quality_metrics_file(project_id: str) -> Optional[Dict[str, Any]]:
    _, path = _quality_metrics_paths(project_id)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_retrieval_ab_eval_file(project_id: str) -> Optional[Dict[str, Any]]:
    path = _retrieval_ab_eval_path(project_id)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def refresh_project_quality_metrics(project_id: str) -> Dict[str, Any]:
    project = ProjectManager.get_project(project_id)
    if not project:
        return {}

    graph_payload: Dict[str, Any] = {}
    delta: Dict[str, Any] = {}
    store: Optional[Neo4jGraphStore] = None
    if Config.is_local_graph() and not Config.validate_local_graph():
        try:
            store = Neo4jGraphStore()
        except Exception:
            store = None

    if store and project.graph_id_raw:
        try:
            graph_payload['raw'] = compute_graph_layer(store, project.graph_id_raw)
        except Exception:
            graph_payload['raw'] = {'graph_id': project.graph_id_raw, 'error': 'compute_failed'}
    gid_d = project.graph_id_disamb or project.graph_id
    if store and gid_d:
        try:
            graph_payload['disamb'] = compute_graph_layer(store, gid_d)
        except Exception:
            graph_payload['disamb'] = {'graph_id': gid_d, 'error': 'compute_failed'}
    if graph_payload.get('raw') and graph_payload.get('disamb') and 'error' not in graph_payload['raw']:
        try:
            delta = graph_delta(graph_payload['raw'], graph_payload['disamb'])
        except Exception:
            delta = {}

    retrieval_raw = _snapshot_search(project.graph_id_raw) if project.graph_id_raw else {}
    retrieval_dis = _snapshot_search(gid_d) if gid_d else {}

    sim_raw = _sim_for_project(project_id, project.graph_id_raw)
    sim_dis = _sim_for_project(project_id, gid_d)
    token_usage = snapshot_token_usage(project_id)
    retrieval_benchmark = ProjectManager.get_retrieval_benchmark(project_id)
    profile_diversity_eval = ProjectManager.get_profile_diversity_eval(project_id)
    disamb_pair_decisions = ProjectManager.get_disambiguation_pair_decisions(project_id)

    retrieval_ab_eval = None
    if project.graph_id_raw and gid_d:
        retrieval_ab_eval = {
            'project_id': project_id,
            'raw_graph_id': project.graph_id_raw,
            'disamb_graph_id': gid_d,
            'raw': {
                'search_graph_calls': int(retrieval_raw.get('search_graph_calls') or 0),
                'empty_calls': int(retrieval_raw.get('search_graph_empty_calls') or 0),
                'result_hits_sum': int(retrieval_raw.get('search_graph_result_hits_sum') or 0),
            },
            'disamb': {
                'search_graph_calls': int(retrieval_dis.get('search_graph_calls') or 0),
                'empty_calls': int(retrieval_dis.get('search_graph_empty_calls') or 0),
                'result_hits_sum': int(retrieval_dis.get('search_graph_result_hits_sum') or 0),
            },
            'delta_empty_calls': int(retrieval_raw.get('search_graph_empty_calls') or 0)
            - int(retrieval_dis.get('search_graph_empty_calls') or 0),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'workload_mode': 'natural_traffic',
        }
        save_retrieval_ab_eval_file(project_id, retrieval_ab_eval)

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        'updated_at': now,
        'project_id': project_id,
        'graph': {'by_variant': graph_payload, 'delta': delta},
        'simulation': {
            'by_variant': {
                'raw': sim_raw,
                'disamb': sim_dis,
            },
            'note': '每次准备仿真会按当前 graph_id 刷新对应列；双列对比需分别用 raw/disamb 各跑一次。',
        },
        'retrieval': {
            'by_variant': {
                'raw': retrieval_raw,
                'disamb': retrieval_dis,
            },
            'note': (
                '统计自最近一次聚合起至本次 refresh 之间的 search_graph 调用（按 graph_id 分桶）。'
                ' 空检索词见各 variant 下 search_graph_empty_queries（最终合并结果为 0 时的原始 query，'
                ' 每条含 at 时间；历史跑次若未升级后端则无此字段）。'
            ),
        },
        'retrieval_ab_eval': retrieval_ab_eval,
        'retrieval_benchmark': retrieval_benchmark,
        'disambiguation_pair_decisions': disamb_pair_decisions,
        'token_usage': token_usage,
    }
    if profile_diversity_eval:
        payload['simulation']['diversity_eval'] = profile_diversity_eval

    save_quality_metrics_file(project_id, payload)
    summary = {
        'updated_at': now,
        'node_count_disamb': (graph_payload.get('disamb') or {}).get('node_count'),
        'node_count_raw': (graph_payload.get('raw') or {}).get('node_count'),
    }
    project.quality_metrics = summary
    ProjectManager.save_project(project)
    return payload


def get_quality_metrics_for_api(project_id: str) -> Optional[Dict[str, Any]]:
    merged = load_quality_metrics_file(project_id)
    if merged:
        return merged
    if Config.is_local_graph():
        try:
            return refresh_project_quality_metrics(project_id)
        except Exception:
            return None
    return None
