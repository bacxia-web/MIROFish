"""Neo4j：图谱元数据、实体、关系、文本块。"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

from ...config import Config


def _norm_name(name: str) -> str:
    return (name or '').strip().lower()


_FALLBACK_LABELS = frozenset({'Person', 'Organization', 'Entity'})


def _is_more_specific(new_label: str, old_label: str) -> bool:
    """new_label 是否比 old_label 更具体（具体类型 > 兜底类型）。"""
    if new_label == old_label:
        return False
    new_is_fb = new_label in _FALLBACK_LABELS
    old_is_fb = old_label in _FALLBACK_LABELS
    if not new_is_fb and old_is_fb:
        return True
    return False


@dataclass
class _NsNode:
    uuid_: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    primary_label: str = 'Entity'
    created_at: Optional[str] = None


@dataclass
class _NsEdge:
    uuid_: str
    name: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str
    attributes: Dict[str, Any]
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None


class Neo4jGraphStore:
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self._uri = uri or Config.NEO4J_URI
        self._user = user or Config.NEO4J_USER
        self._password = password or Config.NEO4J_PASSWORD
        if not self._password:
            raise ValueError('NEO4J_PASSWORD 未配置')
        self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))

    def close(self):
        self._driver.close()

    def _sess(self):
        return self._driver.session()

    def ensure_schema(self):
        with self._sess() as session:
            session.run(
                'CREATE CONSTRAINT mirofish_entity_uuid IF NOT EXISTS '
                'FOR (e:MEntity) REQUIRE e.uuid IS UNIQUE'
            )

    def create_graph(self, graph_id: str, name: str) -> str:
        self.ensure_schema()
        with self._sess() as session:
            session.run(
                """
                MERGE (g:MGraph {graph_id: $gid})
                ON CREATE SET g.name = $name, g.created_at = datetime()
                SET g.name = coalesce(g.name, $name)
                """,
                gid=graph_id,
                name=name,
            )
        return graph_id

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        payload = json.dumps(ontology, ensure_ascii=False)
        with self._sess() as session:
            session.run(
                """
                MATCH (g:MGraph {graph_id: $gid})
                SET g.ontology_json = $payload
                """,
                gid=graph_id,
                payload=payload,
            )

    def delete_graph(self, graph_id: str):
        with self._sess() as session:
            session.run(
                """
                MATCH (n)
                WHERE (n:MGraph OR n:MEntity OR n:MChunk) AND n.graph_id = $gid
                DETACH DELETE n
                """,
                gid=graph_id,
            )

    def merge_entity(
        self,
        graph_id: str,
        name: str,
        primary_label: str,
        summary: str,
        attributes: Optional[Dict[str, Any]] = None,
        cross_label_promotion: bool = True,
    ) -> str:
        attributes = attributes or {}
        nn = _norm_name(name)
        attrs_json = json.dumps(attributes, ensure_ascii=False)

        with self._sess() as session:
            # 1) 精确匹配：同 norm_name + 同 primary_label
            rec = session.run(
                """
                MATCH (:MGraph {graph_id: $gid})-[:HAS_ENTITY]->(e:MEntity {graph_id: $gid, norm_name: $nn, primary_label: $pl})
                RETURN e.uuid as uuid LIMIT 1
                """,
                gid=graph_id,
                nn=nn,
                pl=primary_label,
            ).single()
            if rec and rec.get('uuid'):
                return rec['uuid']

            # 2) 别名匹配（同 label）
            alias_rows = session.run(
                """
                MATCH (:MGraph {graph_id: $gid})-[:HAS_ENTITY]->(e:MEntity {graph_id: $gid, primary_label: $pl})
                WHERE e.aliases_json IS NOT NULL AND e.aliases_json <> ''
                RETURN e.uuid as uuid, e.aliases_json as aj
                """,
                gid=graph_id,
                pl=primary_label,
            )
            for r in alias_rows:
                aj = r.get('aj') or '[]'
                try:
                    alias_list = json.loads(aj)
                except Exception:
                    alias_list = []
                if not isinstance(alias_list, list):
                    continue
                for a in alias_list:
                    if _norm_name(str(a)) == nn:
                        return r['uuid']

            # 3) 跨标签类型提升（仅 enhanced 模式开启）
            if cross_label_promotion:
                cross = session.run(
                    """
                    MATCH (:MGraph {graph_id: $gid})-[:HAS_ENTITY]->(e:MEntity {graph_id: $gid, norm_name: $nn})
                    WHERE e.primary_label <> $pl
                    RETURN e.uuid as uuid, e.primary_label as pl, e.summary as sum
                    """,
                    gid=graph_id,
                    nn=nn,
                    pl=primary_label,
                )
                for cr in cross:
                    old_pl = cr.get('pl') or 'Entity'
                    existing_uuid = cr['uuid']
                    if _is_more_specific(primary_label, old_pl):
                        new_labels_json = json.dumps([primary_label, 'Entity'], ensure_ascii=False)
                        merged_summary = (cr.get('sum') or '')
                        if summary and summary not in merged_summary:
                            merged_summary = (merged_summary + ' ' + summary).strip()
                        session.run(
                            """
                            MATCH (e:MEntity {uuid: $eu, graph_id: $gid})
                            SET e.primary_label = $pl, e.labels_json = $lj, e.summary = $sum
                            """,
                            gid=graph_id,
                            eu=existing_uuid,
                            pl=primary_label,
                            lj=new_labels_json,
                            sum=merged_summary,
                        )
                        return existing_uuid
                    elif _is_more_specific(old_pl, primary_label):
                        if summary:
                            old_sum = cr.get('sum') or ''
                            if summary not in old_sum:
                                merged = (old_sum + ' ' + summary).strip()
                                session.run(
                                    'MATCH (e:MEntity {uuid: $eu, graph_id: $gid}) SET e.summary = $sum',
                                    gid=graph_id, eu=existing_uuid, sum=merged,
                                )
                        return existing_uuid

            # 4) 无匹配 → 新建节点
            nu = str(uuid.uuid4())
            lab_list = [primary_label, 'Entity']
            labels_json = json.dumps(lab_list, ensure_ascii=False)
            session.run(
                """
                MATCH (g:MGraph {graph_id: $gid})
                CREATE (e:MEntity {
                  graph_id: $gid, uuid: $nu, name: $name, norm_name: $nn, primary_label: $pl,
                  summary: $sum, attributes_json: $attrs, labels_json: $lj, aliases_json: $aliases
                })
                CREATE (g)-[:HAS_ENTITY]->(e)
                """,
                gid=graph_id,
                nu=nu,
                name=name.strip(),
                nn=nn,
                pl=primary_label,
                sum=summary or '',
                attrs=attrs_json,
                lj=labels_json,
                aliases='[]',
            )
            return nu

    def merge_duplicate_entities(
        self,
        graph_id: str,
        keep_uuid: str,
        remove_uuids: List[str],
        aliases: List[str],
        canonical_name: Optional[str] = None,
    ) -> None:
        """将 remove 的关联边迁移到 keep，合并别名后删除冗余节点。"""
        remove_uuids = [u for u in remove_uuids if u and u != keep_uuid]
        if not remove_uuids:
            return
        extra_norm = {_norm_name(a) for a in aliases if (a or '').strip()}
        with self._sess() as session:
            for ru in remove_uuids:
                row_nm = session.run(
                    """
                    MATCH (rm:MEntity {uuid: $ru, graph_id: $gid})
                    RETURN rm.name as name, coalesce(rm.aliases_json, '[]') as aj
                    """,
                    gid=graph_id,
                    ru=ru,
                ).single()
                if row_nm:
                    if row_nm.get('name'):
                        extra_norm.add(_norm_name(row_nm['name']))
                    try:
                        for x in json.loads(row_nm.get('aj') or '[]'):
                            extra_norm.add(_norm_name(str(x)))
                    except Exception:
                        pass
                session.run(
                    """
                    MATCH (a:MEntity {graph_id: $gid})-[r:REL]->(rm:MEntity {uuid: $ru, graph_id: $gid})
                    MATCH (keep:MEntity {uuid: $keep, graph_id: $gid})
                    WHERE a.uuid <> keep.uuid
                    CREATE (a)-[r2:REL {uuid: $newu, graph_id: $gid, rel_type: r.rel_type, fact: r.fact, name: coalesce(r.name, r.rel_type)}]->(keep)
                    DELETE r
                    """,
                    gid=graph_id,
                    ru=ru,
                    keep=keep_uuid,
                    newu=str(uuid.uuid4()),
                )
                session.run(
                    """
                    MATCH (rm:MEntity {uuid: $ru, graph_id: $gid})-[r:REL]->(b:MEntity {graph_id: $gid})
                    MATCH (keep:MEntity {uuid: $keep, graph_id: $gid})
                    WHERE b.uuid <> keep.uuid
                    CREATE (keep)-[r2:REL {uuid: $newu, graph_id: $gid, rel_type: r.rel_type, fact: r.fact, name: coalesce(r.name, r.rel_type)}]->(b)
                    DELETE r
                    """,
                    gid=graph_id,
                    ru=ru,
                    keep=keep_uuid,
                    newu=str(uuid.uuid4()),
                )
                session.run(
                    'MATCH (rm:MEntity {uuid: $ru, graph_id: $gid}) DETACH DELETE rm',
                    gid=graph_id,
                    ru=ru,
                )
            row = session.run(
                """
                MATCH (keep:MEntity {uuid: $keep, graph_id: $gid})
                RETURN coalesce(keep.aliases_json, '[]') as aj, keep.norm_name as nn
                """,
                gid=graph_id,
                keep=keep_uuid,
            ).single()
            existing: List[str] = []
            if row and row.get('aj'):
                try:
                    existing = json.loads(row['aj'])
                except Exception:
                    existing = []
            if not isinstance(existing, list):
                existing = []
            keep_nn = _norm_name(row['nn']) if row and row.get('nn') else ''
            merged_set = {keep_nn} if keep_nn else set()
            merged_set.update({_norm_name(str(x)) for x in existing if str(x).strip()})
            merged_set.update(extra_norm)
            merged_set.discard('')
            merged_list = sorted(merged_set)
            session.run(
                'MATCH (keep:MEntity {uuid: $keep, graph_id: $gid}) SET keep.aliases_json = $aj',
                gid=graph_id,
                keep=keep_uuid,
                aj=json.dumps(merged_list, ensure_ascii=False),
            )
            if canonical_name and canonical_name.strip():
                cn = canonical_name.strip()
                session.run(
                    """
                    MATCH (keep:MEntity {uuid: $keep, graph_id: $gid})
                    SET keep.name = $nm, keep.norm_name = $nn
                    """,
                    gid=graph_id,
                    keep=keep_uuid,
                    nm=cn,
                    nn=_norm_name(cn),
                )

    def copy_graph(self, src_graph_id: str, dst_graph_id: str, dst_name: str) -> Dict[str, str]:
        """
        将 src 的 MGraph 元数据、实体、关系、文本块复制到 dst（新 uuid 映射在实体上；chunk 保持相同 uuid 以便 Qdrant 向量复制）。
        返回 entity_old_to_new: {src_entity_uuid: dst_entity_uuid}
        """
        self.create_graph(dst_graph_id, dst_name)
        with self._sess() as session:
            row = session.run(
                'MATCH (g:MGraph {graph_id: $gid}) RETURN g.ontology_json as oj LIMIT 1',
                gid=src_graph_id,
            ).single()
            if row and row.get('oj'):
                session.run(
                    'MATCH (g:MGraph {graph_id: $gid}) SET g.ontology_json = $oj',
                    gid=dst_graph_id,
                    oj=row['oj'],
                )
        entity_map: Dict[str, str] = {}
        with self._sess() as session:
            ents = session.run(
                """
                MATCH (:MGraph {graph_id: $gid})-[:HAS_ENTITY]->(e:MEntity {graph_id: $gid})
                RETURN e
                """,
                gid=src_graph_id,
            )
            for rec in ents:
                n = rec['e']
                old_u = n['uuid']
                new_u = str(uuid.uuid4())
                entity_map[old_u] = new_u
                aj = n.get('aliases_json') or '[]'
                session.run(
                    """
                    MATCH (g:MGraph {graph_id: $dg})
                    CREATE (x:MEntity {
                      graph_id: $dg, uuid: $nu, name: $name, norm_name: $nn, primary_label: $pl,
                      summary: $sum, attributes_json: $attrs, labels_json: $lj, aliases_json: $aj
                    })
                    CREATE (g)-[:HAS_ENTITY]->(x)
                    """,
                    dg=dst_graph_id,
                    nu=new_u,
                    name=n.get('name') or '',
                    nn=n.get('norm_name') or _norm_name(n.get('name') or ''),
                    pl=n.get('primary_label') or 'Entity',
                    sum=n.get('summary') or '',
                    attrs=n.get('attributes_json') or '{}',
                    lj=n.get('labels_json') or '[]',
                    aj=aj,
                )
        with self._sess() as session:
            rels = session.run(
                """
                MATCH (s:MEntity {graph_id: $gid})-[r:REL]->(t:MEntity {graph_id: $gid})
                WHERE r.graph_id = $gid
                RETURN s.uuid as su, t.uuid as tu, r.rel_type as rt, r.fact as fact,
                       coalesce(r.name, r.rel_type) as nm
                """,
                gid=src_graph_id,
            )
            for rec in rels:
                su = entity_map.get(rec['su'])
                tu = entity_map.get(rec['tu'])
                if not su or not tu:
                    continue
                session.run(
                    """
                    MATCH (a:MEntity {uuid: $su, graph_id: $dg})
                    MATCH (b:MEntity {uuid: $tu, graph_id: $dg})
                    CREATE (a)-[r:REL {uuid: $ru, graph_id: $dg, rel_type: $rt, fact: $fact, name: $nm}]->(b)
                    """,
                    dg=dst_graph_id,
                    su=su,
                    tu=tu,
                    ru=str(uuid.uuid4()),
                    rt=rec['rt'] or 'RELATED_TO',
                    fact=rec.get('fact') or '',
                    nm=rec.get('nm') or rec.get('rt') or 'REL',
                )
        with self._sess() as session:
            chunks = session.run(
                """
                MATCH (:MGraph {graph_id: $gid})-[:HAS_CHUNK]->(c:MChunk {graph_id: $gid})
                RETURN c.uuid as cu, c.text as txt
                """,
                gid=src_graph_id,
            )
            for rec in chunks:
                cu = rec['cu']
                txt = rec.get('txt') or ''
                session.run(
                    """
                    MATCH (g:MGraph {graph_id: $dg})
                    CREATE (c:MChunk {graph_id: $dg, uuid: $cu, text: $txt, created_at: datetime()})
                    CREATE (g)-[:HAS_CHUNK]->(c)
                    """,
                    dg=dst_graph_id,
                    cu=cu,
                    txt=txt,
                )
        return entity_map

    def create_rel(
        self,
        graph_id: str,
        source_uuid: str,
        target_uuid: str,
        rel_type: str,
        fact: str,
    ):
        ru = str(uuid.uuid4())
        with self._sess() as session:
            session.run(
                """
                MATCH (s:MEntity {uuid: $su, graph_id: $gid})
                MATCH (t:MEntity {uuid: $tu, graph_id: $gid})
                CREATE (s)-[r:REL {uuid: $ru, graph_id: $gid, rel_type: $rt, fact: $fact, name: $rt}]->(t)
                """,
                gid=graph_id,
                su=source_uuid,
                tu=target_uuid,
                rt=rel_type,
                ru=ru,
                fact=fact or '',
            )

    def add_chunk(self, graph_id: str, text: str) -> str:
        """写入模拟记忆等纯文本块（含图谱外增量）。"""
        cid = str(uuid.uuid4())
        with self._sess() as session:
            session.run(
                """
                MATCH (g:MGraph {graph_id: $gid})
                CREATE (c:MChunk {graph_id: $gid, uuid: $cu, text: $text, created_at: datetime()})
                CREATE (g)-[:HAS_CHUNK]->(c)
                """,
                gid=graph_id,
                cu=cid,
                text=text or '',
            )
        return cid

    def ingest_chunk_with_extract(
        self,
        graph_id: str,
        chunk_text: str,
        extract_result: Dict[str, Any],
        cross_label_promotion: bool = True,
    ) -> str:
        """存储切块文本，并将抽取结果写入实体/边；返回 chunk uuid。"""
        chunk_uuid = str(uuid.uuid4())
        name_to_uuid: Dict[str, str] = {}
        entities = extract_result.get('entities') or []
        for ent in entities:
            if not isinstance(ent, dict):
                continue
            nm = (ent.get('name') or '').strip()
            et = (ent.get('entity_type') or 'Person').strip()
            if not nm:
                continue
            su = ent.get('summary') or ''
            attrs = ent.get('attributes') if isinstance(ent.get('attributes'), dict) else {}
            uid = self.merge_entity(graph_id, nm, et, su, attrs, cross_label_promotion=cross_label_promotion)
            name_to_uuid[nm.lower()] = uid
            name_to_uuid[nm] = uid

        for rel in extract_result.get('relations') or []:
            if not isinstance(rel, dict):
                continue
            st = (rel.get('source') or '').strip()
            tg = (rel.get('target') or '').strip()
            rt = (rel.get('type') or 'RELATED_TO').strip()
            fact = rel.get('fact') or ''
            su = name_to_uuid.get(st.lower()) or name_to_uuid.get(st)
            tu = name_to_uuid.get(tg.lower()) or name_to_uuid.get(tg)
            if su and tu:
                self.create_rel(graph_id, su, tu, rt, fact)

        with self._sess() as session:
            session.run(
                """
                MATCH (g:MGraph {graph_id: $gid})
                CREATE (c:MChunk {graph_id: $gid, uuid: $cu, text: $text, created_at: datetime()})
                CREATE (g)-[:HAS_CHUNK]->(c)
                """,
                gid=graph_id,
                cu=chunk_uuid,
                text=chunk_text or '',
            )
        return chunk_uuid

    def list_nodes_raw(self, graph_id: str) -> List[_NsNode]:
        out: List[_NsNode] = []
        with self._sess() as session:
            rows = session.run(
                """
                MATCH (:MGraph {graph_id: $gid})-[:HAS_ENTITY]->(e:MEntity)
                RETURN e
                """,
                gid=graph_id,
            )
            for r in rows:
                n = r['e']
                labels = []
                lj = n.get('labels_json')
                if lj:
                    try:
                        labels = json.loads(lj)
                    except Exception:
                        labels = [n.get('primary_label') or 'Entity', 'Entity']
                else:
                    pl = n.get('primary_label')
                    labels = [pl, 'Entity'] if pl else ['Entity']
                attrs = {}
                aj = n.get('attributes_json')
                if aj:
                    try:
                        attrs = json.loads(aj)
                    except Exception:
                        attrs = {}
                out.append(
                    _NsNode(
                        uuid_=n['uuid'],
                        name=n.get('name') or '',
                        labels=labels,
                        summary=n.get('summary') or '',
                        attributes=attrs,
                        primary_label=n.get('primary_label') or 'Entity',
                    )
                )
        return out

    def list_edges_raw(self, graph_id: str) -> List[_NsEdge]:
        out: List[_NsEdge] = []
        with self._sess() as session:
            rows = session.run(
                """
                MATCH (s:MEntity {graph_id: $gid})-[r:REL]->(t:MEntity {graph_id: $gid})
                WHERE r.graph_id = $gid
                RETURN r, s.uuid as su, t.uuid as tu
                """,
                gid=graph_id,
            )
            for r in rows:
                rel = r['r']
                out.append(
                    _NsEdge(
                        uuid_=rel.get('uuid') or '',
                        name=rel.get('name') or rel.get('rel_type') or '',
                        fact=rel.get('fact') or '',
                        source_node_uuid=r['su'],
                        target_node_uuid=r['tu'],
                        attributes={},
                    )
                )
        return out

    def edges_incident_to(self, node_uuid: str) -> List[_NsEdge]:
        """仅依赖节点 uuid（含 graph_id 属性）列出关联边。"""
        with self._sess() as session:
            rows = session.run(
                """
                MATCH (s:MEntity)-[r:REL]->(t:MEntity)
                WHERE s.uuid = $u OR t.uuid = $u
                RETURN r, s.uuid as su, t.uuid as tu
                """,
                u=node_uuid,
            )
            out: List[_NsEdge] = []
            for r in rows:
                rel = r['r']
                out.append(
                    _NsEdge(
                        uuid_=rel.get('uuid') or '',
                        name=rel.get('name') or rel.get('rel_type') or '',
                        fact=rel.get('fact') or '',
                        source_node_uuid=r['su'],
                        target_node_uuid=r['tu'],
                        attributes={},
                    )
                )
            return out

    def get_node_raw(self, node_uuid: str) -> Optional[_NsNode]:
        with self._sess() as session:
            row = session.run(
                'MATCH (e:MEntity {uuid: $u}) RETURN e LIMIT 1',
                u=node_uuid,
            ).single()
            if not row:
                return None
            n = row['e']
            labels = []
            lj = n.get('labels_json')
            if lj:
                try:
                    labels = json.loads(lj)
                except Exception:
                    labels = [n.get('primary_label') or 'Entity', 'Entity']
            else:
                pl = n.get('primary_label')
                labels = [pl, 'Entity'] if pl else ['Entity']
            attrs = {}
            aj = n.get('attributes_json')
            if aj:
                try:
                    attrs = json.loads(aj)
                except Exception:
                    attrs = {}
            return _NsNode(
                uuid_=n['uuid'],
                name=n.get('name') or '',
                labels=labels,
                summary=n.get('summary') or '',
                attributes=attrs,
                primary_label=n.get('primary_label') or 'Entity',
            )

    def list_chunk_texts(self, graph_id: str, limit: int = 2000) -> List[str]:
        with self._sess() as session:
            rows = session.run(
                """
                MATCH (c:MChunk {graph_id: $gid})
                RETURN c.text as t
                LIMIT $lim
                """,
                gid=graph_id,
                lim=limit,
            )
            return [r['t'] for r in rows if r.get('t')]
