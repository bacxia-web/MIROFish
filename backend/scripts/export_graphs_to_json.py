#!/usr/bin/env python3
"""
将本地 Neo4j 中的图谱数据导出为静态 JSON 文件，
供 Railway 等无法访问本地数据库的环境通过 fallback 机制展示图谱。

用法（在 MiroFish 项目根目录下运行）：
    python backend/scripts/export_graphs_to_json.py

导出结果：
    backend/demo_uploads/graphs/<graph_id>.json   ← 每个图谱一个文件
    backend/demo_uploads/graphs/_index.json        ← 所有已导出的 graph_id 列表

完成后把整个 demo_uploads/ commit 到 Git 推送，
Railway 部署时 Dockerfile 会把 demo_uploads 复制到 uploads/，
后端 fallback 机制就能从 uploads/graphs/<graph_id>.json 直接返回数据。
"""

import json
import os
import sys
import traceback

# 确保能 import backend 包
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, BACKEND_DIR)

# 加载 .env（与项目一致）
from dotenv import load_dotenv
_env_path = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(_env_path):
    load_dotenv(_env_path, override=True)
    print(f"✅ 已加载 .env: {_env_path}")

# 导出目录
DEMO_UPLOADS = os.path.join(BACKEND_DIR, 'demo_uploads')
GRAPHS_DIR = os.path.join(DEMO_UPLOADS, 'graphs')
PROJECTS_DIR = os.path.join(DEMO_UPLOADS, 'projects')
os.makedirs(GRAPHS_DIR, exist_ok=True)


def load_project(project_dir: str) -> dict | None:
    """读取单个项目的 project.json"""
    pjson = os.path.join(project_dir, 'project.json')
    if not os.path.exists(pjson):
        return None
    with open(pjson, 'r', encoding='utf-8') as f:
        return json.load(f)


def collect_graph_ids() -> list[tuple[str, str]]:
    """
    扫描 demo_uploads/projects/ 下所有项目，
    收集 status=graph_completed 的 graph_id_raw 和 graph_id_disamb。
    返回 [(graph_id, project_id), ...] 列表（去重）
    """
    results = []
    seen = set()
    if not os.path.exists(PROJECTS_DIR):
        print(f"❌ 找不到项目目录: {PROJECTS_DIR}")
        return results

    for proj_id in os.listdir(PROJECTS_DIR):
        proj_dir = os.path.join(PROJECTS_DIR, proj_id)
        if not os.path.isdir(proj_dir):
            continue
        proj = load_project(proj_dir)
        if not proj:
            continue
        status = proj.get('status', '')
        if status != 'graph_completed':
            continue
        for key in ('graph_id_raw', 'graph_id_disamb'):
            gid = proj.get(key)
            if gid and gid not in seen:
                seen.add(gid)
                results.append((gid, proj_id))

    print(f"\n📋 找到 {len(results)} 个图谱 ID（来自 graph_completed 项目）")
    return results


def export_single_graph(graph_id: str, builder) -> dict | None:
    """从 Neo4j 导出单个图谱数据，返回 dict 或 None（失败时）"""
    try:
        data = builder.get_graph_data(graph_id)
        return data
    except Exception as e:
        print(f"   ⚠️  get_graph_data({graph_id}) 失败: {e}")
        return None


def main():
    from app.config import Config

    backend_mode = Config.GRAPH_BACKEND
    print(f"\n🔧 GRAPH_BACKEND = {backend_mode}")

    if backend_mode != 'local':
        print("⚠️  GRAPH_BACKEND 不是 local，请在 .env 里设置 GRAPH_BACKEND=local 后再运行。")
        sys.exit(1)

    # 验证 Neo4j 配置
    errors = Config.validate_local_graph()
    if errors:
        print("❌ 配置错误：")
        for e in errors:
            print(f"   - {e}")
        sys.exit(1)

    from app.services.graph_builder import GraphBuilderService
    builder = GraphBuilderService()

    # 确认连接 Neo4j
    try:
        builder._local_builder.neo._sess()
        print(f"✅ Neo4j 连接成功: {Config.NEO4J_URI}")
    except Exception as e:
        print(f"❌ Neo4j 连接失败: {e}")
        sys.exit(1)

    graph_ids = collect_graph_ids()
    if not graph_ids:
        print("没有找到可导出的图谱，退出。")
        return

    exported = []
    failed = []

    for i, (gid, proj_id) in enumerate(graph_ids, 1):
        out_path = os.path.join(GRAPHS_DIR, f'{gid}.json')

        # 已存在则跳过（加 --force 参数可强制重导）
        if os.path.exists(out_path) and '--force' not in sys.argv:
            print(f"[{i}/{len(graph_ids)}] ⏭️  跳过（已存在）: {gid}")
            exported.append(gid)
            continue

        print(f"[{i}/{len(graph_ids)}] 📤 导出 {gid}  (来自项目 {proj_id})")
        data = export_single_graph(gid, builder)

        if data is None:
            print(f"   ❌ 导出失败，跳过")
            failed.append(gid)
            continue

        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        node_count = data.get('node_count', len(data.get('nodes', [])))
        edge_count = data.get('edge_count', len(data.get('edges', [])))
        print(f"   ✅ 已保存  节点={node_count}  边={edge_count}  → {out_path}")
        exported.append(gid)

    # 写索引文件
    index_path = os.path.join(GRAPHS_DIR, '_index.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({"exported": exported, "failed": failed}, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ 导出完成：{len(exported)} 成功 / {len(failed)} 失败")
    if failed:
        print(f"❌ 失败的 graph_id：{failed}")
    print(f"\n下一步：")
    print(f"  git add backend/demo_uploads/graphs/")
    print(f"  git commit -m 'feat: add static graph JSON for Railway fallback'")
    print(f"  git push bacxia main")
    print(f"{'='*50}\n")


if __name__ == '__main__':
    main()
