"""
图谱相关API路由
采用项目上下文机制，服务端持久化状态
"""

import os
import time
import traceback
import threading
from dataclasses import asdict
from datetime import datetime
from flask import request, jsonify

from . import graph_bp
from ..config import Config
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..utils.locale import t, get_locale, set_locale
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus
from ..utils.token_usage_service import usage_context

# 获取日志器
logger = get_logger('mirofish.api')


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


# ============== 项目管理接口 ==============

@graph_bp.route('/project/<project_id>/quality-metrics', methods=['GET'])
def get_project_quality_metrics(project_id: str):
    """三层质量指标（API + 与 quality_metrics.json 同源）。"""
    from ..services.quality_metrics_service import get_quality_metrics_for_api

    project = ProjectManager.get_project(project_id)
    if not project:
        return jsonify({
            'success': False,
            'error': t('api.projectNotFound', id=project_id),
        }), 404
    data = get_quality_metrics_for_api(project_id)
    if not data:
        return jsonify({
            'success': True,
            'data': {'updated_at': None, 'graph': {}, 'simulation': {}, 'retrieval': {}},
        })
    return jsonify({'success': True, 'data': data})


@graph_bp.route('/project/<project_id>/disambiguation-merges', methods=['GET'])
def get_project_disambiguation_merges(project_id: str):
    """实体消歧合并明细（与 uploads/projects/<id>/disambiguation_merges.json 同源）。"""
    project = ProjectManager.get_project(project_id)
    if not project:
        return jsonify({
            'success': False,
            'error': t('api.projectNotFound', id=project_id),
        }), 404
    data = ProjectManager.get_disambiguation_report(project_id)
    if not data:
        return jsonify({
            'success': True,
            'data': None,
            'message': 'no_disambiguation_report',
        })
    return jsonify({'success': True, 'data': data})


@graph_bp.route('/project/<project_id>/disambiguation-pair-decisions', methods=['GET'])
def get_project_disambiguation_pair_decisions(project_id: str):
    """实体消歧逐对判断明细（含未合并/被拒绝）。"""
    project = ProjectManager.get_project(project_id)
    if not project:
        return jsonify({
            'success': False,
            'error': t('api.projectNotFound', id=project_id),
        }), 404
    data = ProjectManager.get_disambiguation_pair_decisions(project_id)
    if not data:
        return jsonify({
            'success': True,
            'data': None,
            'message': 'no_disambiguation_pair_decisions',
        })
    return jsonify({'success': True, 'data': data})


@graph_bp.route('/project/<project_id>/retrieval-ab-eval', methods=['GET'])
def get_project_retrieval_ab_eval(project_id: str):
    """A/B 检索空结果绝对值回放（与 retrieval_ab_eval.json 同源）。"""
    from ..services.quality_metrics_service import (
        load_retrieval_ab_eval_file,
        refresh_project_quality_metrics,
    )

    project = ProjectManager.get_project(project_id)
    if not project:
        return jsonify({
            'success': False,
            'error': t('api.projectNotFound', id=project_id),
        }), 404

    data = load_retrieval_ab_eval_file(project_id)
    if not data:
        try:
            refresh_project_quality_metrics(project_id)
        except Exception:
            pass
        data = load_retrieval_ab_eval_file(project_id)
    if not data:
        return jsonify({'success': True, 'data': None, 'message': 'no_retrieval_ab_eval'})
    return jsonify({'success': True, 'data': data})


@graph_bp.route('/project/<project_id>/retrieval-benchmark', methods=['GET'])
def get_project_retrieval_benchmark(project_id: str):
    """固定 query 回放结果（与 retrieval_benchmark.json 同源）。"""
    project = ProjectManager.get_project(project_id)
    if not project:
        return jsonify({
            'success': False,
            'error': t('api.projectNotFound', id=project_id),
        }), 404
    data = ProjectManager.get_retrieval_benchmark(project_id)
    if not data:
        return jsonify({'success': True, 'data': None, 'message': 'no_retrieval_benchmark'})
    return jsonify({'success': True, 'data': data})


@graph_bp.route('/project/<project_id>/profile-diversity-eval', methods=['GET'])
def get_project_profile_diversity_eval(project_id: str):
    """人设区分度评估（与 profile_diversity_eval.json 同源）。"""
    project = ProjectManager.get_project(project_id)
    if not project:
        return jsonify({
            'success': False,
            'error': t('api.projectNotFound', id=project_id),
        }), 404
    data = ProjectManager.get_profile_diversity_eval(project_id)
    if not data:
        return jsonify({'success': True, 'data': None, 'message': 'no_profile_diversity_eval'})
    return jsonify({'success': True, 'data': data})


@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """
    获取项目详情
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": t('api.projectNotFound', id=project_id)
        }), 404

    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/list', methods=['GET'])
def list_projects():
    """
    列出所有项目
    """
    limit = request.args.get('limit', 50, type=int)
    projects = ProjectManager.list_projects(limit=limit)
    
    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """
    删除项目
    """
    success = ProjectManager.delete_project(project_id)
    
    if not success:
        return jsonify({
            "success": False,
            "error": t('api.projectDeleteFailed', id=project_id)
        }), 404

    return jsonify({
        "success": True,
        "message": t('api.projectDeleted', id=project_id)
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
def reset_project(project_id: str):
    """
    重置项目状态（用于重新构建图谱）
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": t('api.projectNotFound', id=project_id)
        }), 404

    # 重置到本体已生成状态
    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED
    
    project.graph_id = None
    project.graph_id_raw = None
    project.graph_id_disamb = None
    project.graph_build_task_id = None
    project.quality_metrics = None
    project.error = None
    ProjectManager.save_project(project)
    
    return jsonify({
        "success": True,
        "message": t('api.projectReset', id=project_id),
        "data": project.to_dict()
    })


# ============== 接口1：上传文件并生成本体 ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    """
    接口1：上传文件，分析生成本体定义
    
    请求方式：multipart/form-data
    
    参数：
        files: 上传的文件（PDF/MD/TXT），可多个
        simulation_requirement: 模拟需求描述（必填）
        project_name: 项目名称（可选）
        additional_context: 额外说明（可选）
        
    返回：
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "ontology": {
                    "entity_types": [...],
                    "edge_types": [...],
                    "analysis_summary": "..."
                },
                "files": [...],
                "total_text_length": 12345
            }
        }
    """
    try:
        logger.info("=== 开始生成本体定义 ===")
        
        # 获取参数
        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')
        
        logger.debug(f"项目名称: {project_name}")
        logger.debug(f"模拟需求: {simulation_requirement[:100]}...")
        
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationRequirement')
            }), 400
        
        # 获取上传的文件
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            return jsonify({
                "success": False,
                "error": t('api.requireFileUpload')
            }), 400
        
        # 创建项目
        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement
        logger.info(f"创建项目: {project.project_id}")
        
        # 保存文件并提取文本
        document_texts = []
        all_text = ""
        
        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # 保存文件到项目目录
                file_info = ProjectManager.save_file_to_project(
                    project.project_id, 
                    file, 
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"]
                })
                
                # 提取文本
                text = FileParser.extract_text(file_info["path"])
                text = TextProcessor.preprocess_text(text)
                document_texts.append(text)
                all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"
        
        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            return jsonify({
                "success": False,
                "error": t('api.noDocProcessed')
            }), 400
        
        # 保存提取的文本
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info(f"文本提取完成，共 {len(all_text)} 字符")
        
        # 生成本体
        logger.info("调用 LLM 生成本体定义...")
        generator = OntologyGenerator()
        with usage_context(project.project_id, 1):
            ontology = generator.generate(
                document_texts=document_texts,
                simulation_requirement=simulation_requirement,
                additional_context=additional_context if additional_context else None
            )
        
        # 保存本体到项目
        entity_count = len(ontology.get("entity_types", []))
        edge_count = len(ontology.get("edge_types", []))
        logger.info(f"本体生成完成: {entity_count} 个实体类型, {edge_count} 个关系类型")
        
        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", [])
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)
        logger.info(f"=== 本体生成完成 === 项目ID: {project.project_id}")
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "project_name": project.name,
                "ontology": project.ontology,
                "analysis_summary": project.analysis_summary,
                "files": project.files,
                "total_text_length": project.total_text_length
            }
        })
        
    except Exception as e:
        logger.exception("生成本体失败: %s", e)
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 接口2：构建图谱 ==============

@graph_bp.route('/build', methods=['POST'])
def build_graph():
    """
    接口2：根据project_id构建图谱
    
    请求（JSON）：
        {
            "project_id": "proj_xxxx",  // 必填，来自接口1
            "graph_name": "图谱名称",    // 可选
            "chunk_size": 500,          // 可选，默认500
            "chunk_overlap": 50         // 可选，默认50
        }
        
    返回：
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "task_id": "task_xxxx",
                "message": "图谱构建任务已启动"
            }
        }
    """
    try:
        logger.info("=== 开始构建图谱 ===")
        
        # 检查配置
        errors = []
        if Config.is_local_graph():
            errors.extend(Config.validate_local_graph())
        elif not Config.ZEP_API_KEY:
            errors.append("ZEP_API_KEY未配置（或将 GRAPH_BACKEND=local）")
        if errors:
            logger.error(f"配置错误: {errors}")
            return jsonify({
                "success": False,
                "error": t('api.configError', details="; ".join(errors))
            }), 500
        
        # 解析请求
        data = request.get_json() or {}
        project_id = data.get('project_id')
        logger.debug(f"请求参数: project_id={project_id}")
        
        if not project_id:
            return jsonify({
                "success": False,
                "error": t('api.requireProjectId')
            }), 400
        
        # 获取项目
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": t('api.projectNotFound', id=project_id)
            }), 404

        # 检查项目状态
        force = data.get('force', False)  # 强制重新构建
        
        if project.status == ProjectStatus.CREATED:
            return jsonify({
                "success": False,
                "error": t('api.ontologyNotGenerated')
            }), 400
        
        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error": t('api.graphBuilding'),
                "task_id": project.graph_build_task_id
            }), 400
        
        # 如果强制重建，重置状态
        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_id_raw = None
            project.graph_id_disamb = None
            project.graph_build_task_id = None
            project.quality_metrics = None
            project.error = None
        
        # 获取配置
        graph_name = data.get('graph_name', project.name or 'MiroFish Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)
        
        # 更新项目配置
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap
        
        # 获取提取的文本
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({
                "success": False,
                "error": t('api.textNotFound')
            }), 400
        
        # 获取本体
        ontology = project.ontology
        if not ontology:
            return jsonify({
                "success": False,
                "error": t('api.ontologyNotFound')
            }), 400
        
        # 创建异步任务
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"构建图谱: {graph_name}")
        logger.info(f"创建图谱构建任务: task_id={task_id}, project_id={project_id}")
        
        # 更新项目状态
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)
        
        # Capture locale before spawning background thread
        current_locale = get_locale()

        # 启动后台任务
        def build_task():
            set_locale(current_locale)
            build_logger = get_logger('mirofish.build')
            try:
                with usage_context(project_id, 1):
                    build_logger.info(f"[{task_id}] 开始构建图谱...")
                    task_manager.update_task(
                        task_id, 
                        status=TaskStatus.PROCESSING,
                        message=t('progress.initGraphService')
                    )
                
                    # 创建图谱构建服务
                    builder = GraphBuilderService()
                
                    # 分块
                    task_manager.update_task(
                        task_id,
                        message=t('progress.textChunking'),
                        progress=5
                    )
                    chunks = TextProcessor.split_text(
                        text, 
                        chunk_size=chunk_size, 
                        overlap=chunk_overlap
                    )
                    total_chunks = len(chunks)
                
                # 创建图谱（本地：raw+消歧双图；Zep：单图）
                task_manager.update_task(
                    task_id,
                    message=t(
                        'progress.creatingLocalGraph'
                        if Config.is_local_graph()
                        else 'progress.creatingZepGraph'
                    ),
                    progress=10
                )
                episode_uuids = []
                if Config.is_local_graph():
                    graph_stream_holder: dict = {'raw': None, 'disamb': None}
                    last_graph_stream_at = [0.0]

                    def persist_from_builder(update: dict) -> None:
                        proj = ProjectManager.get_project(project_id)
                        if not proj:
                            return
                        if update.get('reset_experimental_branch'):
                            proj.graph_id_disamb = None
                        if 'graph_id_raw' in update:
                            proj.graph_id_raw = update['graph_id_raw']
                            graph_stream_holder['raw'] = update['graph_id_raw']
                        if 'graph_id_disamb' in update:
                            proj.graph_id_disamb = update['graph_id_disamb']
                            graph_stream_holder['disamb'] = update['graph_id_disamb']
                        if 'graph_id' in update:
                            proj.graph_id = update['graph_id']
                        ProjectManager.save_project(proj)

                    def push_graph_stream_detail() -> None:
                        now = time.monotonic()
                        if now - last_graph_stream_at[0] < 0.65:
                            return
                        last_graph_stream_at[0] = now
                        stream: dict = {}
                        rid = graph_stream_holder.get('raw')
                        did = graph_stream_holder.get('disamb')
                        try:
                            if rid:
                                info = builder._get_graph_info(rid)
                                stream['control'] = {
                                    'graph_id': rid,
                                    'node_count': info.node_count,
                                    'edge_count': info.edge_count,
                                }
                            if did:
                                info = builder._get_graph_info(did)
                                stream['experimental'] = {
                                    'graph_id': did,
                                    'node_count': info.node_count,
                                    'edge_count': info.edge_count,
                                }
                        except Exception as ex:
                            build_logger.debug(f'[{task_id}] graph stream snapshot skip: {ex}')
                            return
                        if stream:
                            task_manager.update_task(
                                task_id,
                                progress_detail={'graph_stream': stream},
                            )

                    def local_progress(msg: str, progress_ratio: float):
                        progress = 15 + int(min(1.0, max(0.0, progress_ratio)) * 40)
                        task_manager.update_task(task_id, message=msg, progress=progress)
                        push_graph_stream_detail()

                    task_manager.update_task(
                        task_id,
                        message=t('progress.generatingEnhancedOntology'),
                        progress=12
                    )
                    ont_gen = OntologyGenerator()
                    with usage_context(project_id, 1):
                        ontology_enhanced = ont_gen.generate(
                            document_texts=[text],
                            simulation_requirement=project.simulation_requirement or '',
                            enhanced=True,
                        )

                    task_manager.update_task(
                        task_id,
                        message=t('progress.addingChunks', count=total_chunks),
                        progress=15
                    )
                    graph_id_raw, graph_id_disamb, dres = builder.build_local_raw_and_disambiguated(
                        graph_name,
                        chunks,
                        ontology,
                        batch_size=3,
                        progress_callback=local_progress,
                        ontology_enhanced=ontology_enhanced,
                        persist_project_graph_ids=persist_from_builder,
                        chunk_stream_hook=push_graph_stream_detail,
                    )
                    graph_id = graph_id_disamb
                    project.graph_id_raw = graph_id_raw
                    project.graph_id_disamb = graph_id_disamb
                    project.graph_id = graph_id_disamb
                    ProjectManager.save_project(project)
                    try:
                        ProjectManager.save_disambiguation_report(
                            project_id,
                            {
                                'graph_id_raw': graph_id_raw,
                                'graph_id_disamb': graph_id_disamb,
                                'generated_at': datetime.now().isoformat(),
                                'summary': {
                                    'merged_groups': dres.merged_groups,
                                    'removed_nodes': dres.removed_nodes,
                                    'pair_decisions': dres.pair_decisions,
                                },
                                'merges': [asdict(m) for m in dres.merge_records],
                            },
                        )
                        ProjectManager.save_disambiguation_pair_decisions(
                            project_id,
                            {
                                'graph_id_raw': graph_id_raw,
                                'graph_id_disamb': graph_id_disamb,
                                'generated_at': datetime.now().isoformat(),
                                'summary': {
                                    'pair_decisions': dres.pair_decisions,
                                    'merged_groups': dres.merged_groups,
                                    'precision_merge_rate': dres.precision_merge_rate,
                                    'final_merged_count': int(
                                        sum(
                                            1
                                            for d in (dres.pair_decision_details or [])
                                            if d.get('final_merged')
                                        )
                                    ),
                                },
                                'pair_decision_details': dres.pair_decision_details,
                            },
                        )
                    except Exception as rep_err:
                        build_logger.warning(
                            f'[{task_id}] 消歧合并明细落盘跳过: {rep_err}'
                        )
                else:
                    graph_id = builder.create_graph(name=graph_name)
                    project.graph_id_raw = graph_id
                    project.graph_id_disamb = graph_id
                    project.graph_id = graph_id
                    ProjectManager.save_project(project)

                    task_manager.update_task(
                        task_id,
                        message=t('progress.settingOntology'),
                        progress=15
                    )
                    builder.set_ontology(graph_id, ontology)

                    def add_progress_callback(msg, progress_ratio):
                        progress = 15 + int(progress_ratio * 40)
                        task_manager.update_task(
                            task_id,
                            message=msg,
                            progress=progress
                        )

                    task_manager.update_task(
                        task_id,
                        message=t('progress.addingChunks', count=total_chunks),
                        progress=15
                    )

                    episode_uuids = builder.add_text_batches(
                        graph_id,
                        chunks,
                        batch_size=3,
                        progress_callback=add_progress_callback,
                        ontology=ontology,
                    )
                
                # 本地模式已在构建回调中完成写入；Zep 模式需轮询 episode 处理状态
                task_manager.update_task(
                    task_id,
                    message=t(
                        'progress.localGraphFinalize'
                        if Config.is_local_graph()
                        else 'progress.waitingZepProcess'
                    ),
                    progress=55
                )
                
                def wait_progress_callback(msg, progress_ratio):
                    progress = 55 + int(progress_ratio * 35)  # 55% - 90%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                builder._wait_for_episodes(episode_uuids, wait_progress_callback)
                
                # 获取图谱数据
                task_manager.update_task(
                    task_id,
                    message=t('progress.fetchingGraphData'),
                    progress=95
                )
                graph_data = builder.get_graph_data(graph_id)
                
                # 更新项目状态
                project.status = ProjectStatus.GRAPH_COMPLETED
                ProjectManager.save_project(project)
                
                node_count = graph_data.get("node_count", 0)
                edge_count = graph_data.get("edge_count", 0)
                build_logger.info(f"[{task_id}] 图谱构建完成: graph_id={graph_id}, 节点={node_count}, 边={edge_count}")

                # 构建后评估闭环（固定 query 回放 + 人设区分度）
                try:
                    if Config.is_local_graph() and project.graph_id_raw and project.graph_id_disamb:
                        from ..services.disambiguation_eval_service import (
                            DisambiguationEvalService,
                        )

                        eval_service = DisambiguationEvalService()
                        eval_service.run_post_build_evaluations(
                            project_id=project_id,
                            graph_id_raw=project.graph_id_raw,
                            graph_id_disamb=project.graph_id_disamb,
                            ontology=project.ontology or {},
                            simulation_requirement=project.simulation_requirement or '',
                            query_count=30,
                        )
                except Exception as eval_err:
                    build_logger.warning(f"[{task_id}] 评估闭环执行跳过: {eval_err}")

                try:
                    from ..services.quality_metrics_service import refresh_project_quality_metrics

                    refresh_project_quality_metrics(project_id)
                except Exception as qe:
                    build_logger.warning(f"[{task_id}] 质量指标刷新跳过: {qe}")
                
                # 完成
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message=t('progress.graphBuildComplete'),
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "graph_id_raw": project.graph_id_raw,
                        "graph_id_disamb": project.graph_id_disamb,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks
                    }
                )
                
            except Exception as e:
                # 更新项目状态为失败
                build_logger.error(f"[{task_id}] 图谱构建失败: {str(e)}")
                build_logger.debug(traceback.format_exc())
                
                project.status = ProjectStatus.FAILED
                project.error = str(e)
                ProjectManager.save_project(project)
                
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=t('progress.buildFailed', error=str(e)),
                    error=traceback.format_exc()
                )
        
        # 启动后台线程
        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": t('api.graphBuildStarted', taskId=task_id)
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 任务查询接口 ==============

@graph_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """
    查询任务状态
    """
    task = TaskManager().get_task(task_id)
    
    if not task:
        return jsonify({
            "success": False,
            "error": t('api.taskNotFound', id=task_id)
        }), 404
    
    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


@graph_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """
    列出所有任务
    """
    tasks = TaskManager().list_tasks()
    
    return jsonify({
        "success": True,
        "data": [t.to_dict() for t in tasks],
        "count": len(tasks)
    })


# ============== 图谱数据接口 ==============

def _load_static_graph(graph_id: str) -> dict | None:
    """
    Fallback：从预先导出的静态 JSON 文件加载图谱数据。
    文件路径：uploads/graphs/<graph_id>.json
    （Railway 部署时 Dockerfile 会把 demo_uploads/ 复制到 uploads/）
    """
    import json as _json
    candidates = [
        os.path.join(Config.UPLOAD_FOLDER, 'graphs', f'{graph_id}.json'),
        os.path.join(os.path.dirname(Config.UPLOAD_FOLDER), 'demo_uploads', 'graphs', f'{graph_id}.json'),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = _json.load(f)
                logger.info(f"[static-fallback] 从静态文件加载图谱: {path}")
                return data
            except Exception as ex:
                logger.warning(f"[static-fallback] 读取失败 {path}: {ex}")
    return None


@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """
    获取图谱数据（节点和边）。
    优先从 Zep / Neo4j 实时拉取；若不可用则 fallback 到预导出的静态 JSON。
    """
    # ── 先尝试实时后端 ──────────────────────────────────────────────────────
    backend_available = True
    if Config.is_local_graph():
        if Config.validate_local_graph():
            backend_available = False
    elif not Config.ZEP_API_KEY:
        backend_available = False

    if backend_available:
        try:
            builder = GraphBuilderService()
            graph_data = builder.get_graph_data(graph_id)
            return jsonify({"success": True, "data": graph_data})
        except Exception as e:
            logger.warning(f"实时图谱加载失败，尝试 fallback: {e}")

    # ── Fallback：静态 JSON ──────────────────────────────────────────────────
    static_data = _load_static_graph(graph_id)
    if static_data:
        return jsonify({"success": True, "data": static_data, "source": "static"})

    # ── 两种途径都失败 ───────────────────────────────────────────────────────
    if not backend_available:
        reason = (
            t('api.zepApiKeyMissing')
            if not Config.ZEP_API_KEY
            else "本地图谱配置不完整"
        )
        return jsonify({"success": False, "error": reason}), 500

    return jsonify({
        "success": False,
        "error": "图谱数据暂不可用（实时后端不可达，且未找到预导出的静态数据）",
        "graph_id": graph_id,
    }), 500


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """
    删除Zep图谱
    """
    try:
        if Config.is_local_graph():
            le = Config.validate_local_graph()
            if le:
                return jsonify({"success": False, "error": "; ".join(le)}), 500
        elif not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": t('api.zepApiKeyMissing')
            }), 500
        
        builder = GraphBuilderService()
        builder.delete_graph(graph_id)
        
        return jsonify({
            "success": True,
            "message": t('api.graphDeleted', id=graph_id)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
