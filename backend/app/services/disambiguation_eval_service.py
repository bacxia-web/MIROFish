"""消歧评估：固定 query 回放 + 人设区分度。"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from statistics import median
from typing import Any, Dict, List, Optional

from ..models.project import ProjectManager
from ..utils.llm_client import LLMClient
from .local_graph.embedding import EmbeddingService
from .local_graph.neo4j_store import Neo4jGraphStore
from .simulation_manager import SimulationManager
from .zep_tools import ZepToolsService


def _norm(v: List[float]) -> float:
    return sum(x * x for x in v) ** 0.5


def _cosine(a: List[float], b: List[float]) -> float:
    na = _norm(a)
    nb = _norm(b)
    if not na or not nb:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def _percentile(sorted_vals: List[float], p: float) -> Optional[float]:
    if not sorted_vals:
        return None
    if p <= 0:
        return sorted_vals[0]
    if p >= 1:
        return sorted_vals[-1]
    idx = int(round((len(sorted_vals) - 1) * p))
    idx = max(0, min(idx, len(sorted_vals) - 1))
    return sorted_vals[idx]


class DisambiguationEvalService:
    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        neo: Optional[Neo4jGraphStore] = None,
        embedder: Optional[EmbeddingService] = None,
        sim_manager: Optional[SimulationManager] = None,
    ):
        self.llm = llm or LLMClient()
        self.neo = neo or Neo4jGraphStore()
        self.embedder = embedder or EmbeddingService()
        self.sim_manager = sim_manager or SimulationManager()
        self.zep_tools = ZepToolsService()

    def run_post_build_evaluations(
        self,
        project_id: str,
        graph_id_raw: str,
        graph_id_disamb: str,
        ontology: Dict[str, Any],
        simulation_requirement: str,
        query_count: int = 30,
    ) -> Dict[str, Any]:
        retrieval_benchmark = self.run_retrieval_benchmark(
            project_id=project_id,
            graph_id_raw=graph_id_raw,
            graph_id_disamb=graph_id_disamb,
            ontology=ontology,
            simulation_requirement=simulation_requirement,
            query_count=query_count,
        )
        profile_diversity = self.run_profile_diversity_eval(
            project_id=project_id,
            graph_id_raw=graph_id_raw,
            graph_id_disamb=graph_id_disamb,
        )
        return {
            "retrieval_benchmark": retrieval_benchmark,
            "profile_diversity_eval": profile_diversity,
        }

    def run_retrieval_benchmark(
        self,
        project_id: str,
        graph_id_raw: str,
        graph_id_disamb: str,
        ontology: Dict[str, Any],
        simulation_requirement: str,
        query_count: int = 30,
    ) -> Dict[str, Any]:
        queries = self._select_queries_from_ontology(
            graph_id_raw=graph_id_raw,
            ontology=ontology,
            simulation_requirement=simulation_requirement,
            query_count=query_count,
        )
        details: List[Dict[str, Any]] = []
        for q in queries:
            raw_res = self.zep_tools.search_graph(
                graph_id=graph_id_raw, query=q, limit=10, scope="both"
            )
            dis_res = self.zep_tools.search_graph(
                graph_id=graph_id_disamb, query=q, limit=10, scope="both"
            )
            details.append(
                {
                    "query": q,
                    "raw_hits": int(raw_res.total_count or 0),
                    "disamb_hits": int(dis_res.total_count or 0),
                    "raw_empty": int((raw_res.total_count or 0) == 0),
                    "disamb_empty": int((dis_res.total_count or 0) == 0),
                }
            )

        n = len(details)
        raw_nonempty = sum(1 for d in details if not d["raw_empty"])
        dis_nonempty = sum(1 for d in details if not d["disamb_empty"])
        raw_hits_sum = sum(int(d["raw_hits"]) for d in details)
        dis_hits_sum = sum(int(d["disamb_hits"]) for d in details)
        payload = {
            "project_id": project_id,
            "graph_id_raw": graph_id_raw,
            "graph_id_disamb": graph_id_disamb,
            "query_count": n,
            "queries": queries,
            "details": details,
            "summary": {
                "raw_nonempty_rate": round(raw_nonempty / n, 4) if n else 0.0,
                "disamb_nonempty_rate": round(dis_nonempty / n, 4) if n else 0.0,
                "raw_avg_hits": round(raw_hits_sum / n, 4) if n else 0.0,
                "disamb_avg_hits": round(dis_hits_sum / n, 4) if n else 0.0,
                "raw_avg_hits_on_nonempty": (
                    round(raw_hits_sum / raw_nonempty, 4) if raw_nonempty else None
                ),
                "disamb_avg_hits_on_nonempty": (
                    round(dis_hits_sum / dis_nonempty, 4) if dis_nonempty else None
                ),
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        ProjectManager.save_retrieval_benchmark(project_id, payload)
        return payload

    def _select_queries_from_ontology(
        self,
        graph_id_raw: str,
        ontology: Dict[str, Any],
        simulation_requirement: str,
        query_count: int,
    ) -> List[str]:
        candidate_names: List[str] = []
        try:
            nodes = self.neo.list_nodes_raw(graph_id_raw)
            seen = set()
            for n in nodes:
                nm = (n.name or "").strip()
                if nm and nm not in seen:
                    seen.add(nm)
                    candidate_names.append(nm)
                if len(candidate_names) >= 200:
                    break
        except Exception:
            candidate_names = []

        system_prompt = (
            "你是图谱检索评测专家。请从候选实体名中挑选最有代表性的查询词，"
            "返回 JSON: {\"queries\": [\"...\", ...]}，不要解释。"
        )
        user_prompt = (
            f"目标数量: {query_count}\n"
            f"模拟需求: {simulation_requirement}\n"
            f"本体(JSON): {json.dumps(ontology, ensure_ascii=False)[:5000]}\n"
            f"候选实体名(JSON): {json.dumps(candidate_names, ensure_ascii=False)[:8000]}"
        )
        try:
            data = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
            )
            arr = data.get("queries") if isinstance(data, dict) else data
            if isinstance(arr, list):
                out: List[str] = []
                seen_q = set()
                for x in arr:
                    q = str(x or "").strip()
                    if not q or q in seen_q:
                        continue
                    seen_q.add(q)
                    out.append(q[:120])
                    if len(out) >= query_count:
                        break
                if out:
                    return out
        except Exception:
            pass

        if candidate_names:
            return candidate_names[:query_count]
        entity_types = ontology.get("entity_types") or []
        out = []
        for et in entity_types:
            name = (et.get("name") if isinstance(et, dict) else str(et or "")).strip()
            if name:
                out.append(name)
        return out[:query_count]

    def run_profile_diversity_eval(
        self, project_id: str, graph_id_raw: str, graph_id_disamb: str
    ) -> Dict[str, Any]:
        sims = self.sim_manager.list_simulations(project_id=project_id)
        raw_sim = self._pick_sim(sims, graph_id_raw)
        dis_sim = self._pick_sim(sims, graph_id_disamb)

        raw_profiles = self._load_profiles_texts(raw_sim["simulation_id"]) if raw_sim else []
        dis_profiles = (
            self._load_profiles_texts(dis_sim["simulation_id"]) if dis_sim else []
        )
        raw_metrics = self._profile_cosine_metrics(raw_profiles)
        dis_metrics = self._profile_cosine_metrics(dis_profiles)
        payload = {
            "project_id": project_id,
            "graph_id_raw": graph_id_raw,
            "graph_id_disamb": graph_id_disamb,
            "raw": {
                "simulation_id": (raw_sim or {}).get("simulation_id"),
                **raw_metrics,
            },
            "disamb": {
                "simulation_id": (dis_sim or {}).get("simulation_id"),
                **dis_metrics,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        ProjectManager.save_profile_diversity_eval(project_id, payload)
        return payload

    def _pick_sim(self, sims: List[Any], graph_id: str) -> Optional[Dict[str, Any]]:
        cands = [s for s in sims if getattr(s, "graph_id", None) == graph_id]
        if not cands:
            return None
        cands.sort(key=lambda s: getattr(s, "created_at", ""), reverse=True)
        top = cands[0]
        return {
            "simulation_id": top.simulation_id,
            "created_at": top.created_at,
            "graph_id": top.graph_id,
        }

    def _load_profiles_texts(self, simulation_id: str) -> List[str]:
        sim_dir = self.sim_manager._get_simulation_dir(simulation_id)  # noqa: SLF001
        texts: List[str] = []

        reddit_path = os.path.join(sim_dir, "reddit_profiles.json")
        if os.path.isfile(reddit_path):
            try:
                with open(reddit_path, "r", encoding="utf-8") as f:
                    arr = json.load(f)
                for p in arr if isinstance(arr, list) else []:
                    if isinstance(p, dict):
                        t = " | ".join(
                            [
                                str(p.get("name") or ""),
                                str(p.get("bio") or ""),
                                str(p.get("persona") or ""),
                            ]
                        ).strip()
                        if t:
                            texts.append(t[:5000])
            except Exception:
                pass

        twitter_csv = os.path.join(sim_dir, "twitter_profiles.csv")
        if os.path.isfile(twitter_csv):
            try:
                with open(twitter_csv, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        t = " | ".join(
                            [
                                str(row.get("name") or ""),
                                str(row.get("bio") or ""),
                                str(row.get("persona") or ""),
                            ]
                        ).strip()
                        if t:
                            texts.append(t[:5000])
            except Exception:
                pass
        return texts

    def _profile_cosine_metrics(self, texts: List[str]) -> Dict[str, Any]:
        n = len(texts)
        if n < 2:
            return {
                "profile_count": n,
                "pair_count": 0,
                "cosine_median": None,
                "cosine_p90": None,
            }
        vecs = self.embedder.embed_texts(texts)
        sims: List[float] = []
        for i in range(len(vecs)):
            for j in range(i + 1, len(vecs)):
                sims.append(_cosine(vecs[i], vecs[j]))
        sims.sort()
        return {
            "profile_count": n,
            "pair_count": len(sims),
            "cosine_median": round(float(median(sims)), 4) if sims else None,
            "cosine_p90": (
                round(float(_percentile(sims, 0.9)), 4)
                if _percentile(sims, 0.9) is not None
                else None
            ),
        }

