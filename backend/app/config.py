"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: MiroFish/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=True)


def _zep_service_root(url: str) -> str:
    """规范化 Zep 服务根 URL（无尾部斜杠、去掉误写的 /api/v2）。"""
    u = (url or "").strip().rstrip("/")
    for suffix in ("/api/v2", "/api/v1"):
        if u.endswith(suffix):
            u = u[: -len(suffix)].rstrip("/")
    return u


def _sync_zep_local_env():
    """
    zep-cloud SDK 通过环境变量 ZEP_API_URL 指向自托管实例（会自动拼接 /api/v2）。
    OpenZep 安装脚本等使用 ZEP_BASE_URL，在此对齐到 ZEP_API_URL。
    """
    api = _zep_service_root(os.environ.get("ZEP_API_URL", ""))
    base = _zep_service_root(os.environ.get("ZEP_BASE_URL", ""))
    if api:
        os.environ["ZEP_API_URL"] = api
    elif base:
        os.environ["ZEP_API_URL"] = base


_sync_zep_local_env()


class Config:
    """Flask配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False
    
    # LLM配置（统一使用OpenAI格式）
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    # 依次尝试；遇到额度/限流等可切换错误时自动换下一个模型（见 llm_client.chat_completions_with_model_fallback）
    _LLM_MODEL_FALLBACK_DEFAULT = (
        'qwen3-32b,qwen3-coder-plus,qwen3-vl-flash-2025-10-15,qwen3-max-preview,qwen3-coder-flash'
    )
    _llm_chain_raw = os.environ.get('LLM_MODEL_FALLBACK_CHAIN', '').strip()
    if _llm_chain_raw:
        LLM_MODEL_CHAIN = [m.strip() for m in _llm_chain_raw.split(',') if m.strip()]
    else:
        LLM_MODEL_CHAIN = [
            m.strip() for m in _LLM_MODEL_FALLBACK_DEFAULT.split(',') if m.strip()
        ]
        # 未配置 FALLBACK_CHAIN 时，允许 LLM_MODEL_NAME 插到队首（兼容旧 .env）
        # 注意：类体里的 list 推导式对同级局部变量可见性与普通块不同，此处用显式循环
        _primary = os.environ.get('LLM_MODEL_NAME', '').strip()
        if _primary:
            _rest = []
            for _m in LLM_MODEL_CHAIN:
                if _m != _primary:
                    _rest.append(_m)
            LLM_MODEL_CHAIN = [_primary] + _rest
    LLM_MODEL_NAME = LLM_MODEL_CHAIN[0] if LLM_MODEL_CHAIN else 'gpt-4o-mini'
    
    # 图谱后端：zep = Zep Cloud/自托管 API（zep-cloud）；local = Neo4j + Qdrant（方案 B）
    GRAPH_BACKEND = os.environ.get('GRAPH_BACKEND', 'zep').strip().lower()
    
    # Zep 配置（GRAPH_BACKEND=zep 时必填；自托管时再设 ZEP_API_URL，见 README）
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    # 已规范化的自托管根 URL；未设置时由 zep-cloud 走 Zep Cloud
    ZEP_API_URL = os.environ.get('ZEP_API_URL')
    
    # 本地图谱（GRAPH_BACKEND=local）
    NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', '')
    QDRANT_URL = os.environ.get('QDRANT_URL', 'http://localhost:6333')
    QDRANT_COLLECTION_CHUNKS = os.environ.get('QDRANT_COLLECTION_CHUNKS', 'mirofish_chunks')
    # Embedding（与 LLM 同提供商时可只配 LLM_*）
    EMBEDDING_MODEL_NAME = os.environ.get('EMBEDDING_MODEL_NAME', 'text-embedding-3-small')
    EMBEDDING_API_KEY = os.environ.get('EMBEDDING_API_KEY') or os.environ.get('LLM_API_KEY')
    _emb_base = os.environ.get('EMBEDDING_BASE_URL')
    EMBEDDING_BASE_URL = _emb_base if _emb_base else os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS平台可用动作配置
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    # ── 上下文压缩 & 步骤裁剪开关 ────────────────────────────────────────
    # 主开关：是否启用 ReACT 历史压缩（true/false），默认关闭以兼容旧行为
    REPORT_CONTEXT_COMPRESSION_ENABLED = os.environ.get(
        'REPORT_CONTEXT_COMPRESSION_ENABLED', 'false'
    ).strip().lower() in ('1', 'true', 'yes', 'on')
    # 用于压缩 observation 的小模型；留空时复用 LLM_MODEL_CHAIN 的末位（一般是最便宜的）
    REPORT_COMPRESSOR_MODEL = os.environ.get('REPORT_COMPRESSOR_MODEL', '').strip()
    # 压缩后 observation 的目标 token 上限
    REPORT_COMPRESSOR_MAX_TOKENS = int(os.environ.get('REPORT_COMPRESSOR_MAX_TOKENS', '180'))
    # 是否保留"最后一次工具结果"原文不压缩（保证 Final Answer 能引用真实数据）
    REPORT_KEEP_LAST_TOOL_RAW = os.environ.get(
        'REPORT_KEEP_LAST_TOOL_RAW', 'true'
    ).strip().lower() in ('1', 'true', 'yes', 'on')
    # 步骤裁剪：动态降低 min_tool_calls；开启压缩后默认从 3 降到 1
    REPORT_MIN_TOOL_CALLS = int(os.environ.get('REPORT_MIN_TOOL_CALLS', '0'))  # 0 = 跟随是否开启压缩
    # 步骤裁剪：前置章节上下文从 4000 字截断改为 N 字摘要（0 关闭）
    REPORT_PREV_SECTION_BUDGET = int(os.environ.get('REPORT_PREV_SECTION_BUDGET', '0'))
    # token 统计 variant 标签（用于 A/B 对比），如 "baseline" / "optimized"
    REPORT_TOKEN_VARIANT_LABEL = os.environ.get(
        'REPORT_TOKEN_VARIANT_LABEL', ''
    ).strip()

    # ── Phase 1-5 独立 flags（D1）─────────────────────────────────────
    # 每个改动一个独立开关，默认全 false。生产先关，eval 建立基准后一个一个开。

    # Plan #4：interview 双重摘要去重
    INTERVIEW_DEDUP_ENABLED = os.environ.get(
        'INTERVIEW_DEDUP_ENABLED', 'false'
    ).strip().lower() in ('1', 'true', 'yes', 'on')

    # Plan #1：chunk_extractor 批处理
    CHUNK_EXTRACT_BATCH_ENABLED = os.environ.get(
        'CHUNK_EXTRACT_BATCH_ENABLED', 'false'
    ).strip().lower() in ('1', 'true', 'yes', 'on')
    CHUNK_EXTRACT_BATCH_SIZE = int(os.environ.get('CHUNK_EXTRACT_BATCH_SIZE', '3'))
    CHUNK_KNOWN_ENTITIES_TRIM_ENABLED = os.environ.get(
        'CHUNK_KNOWN_ENTITIES_TRIM_ENABLED', 'false'
    ).strip().lower() in ('1', 'true', 'yes', 'on')

    # Plan #2：profile_generator 按类型批生成
    PROFILE_BATCH_GEN_ENABLED = os.environ.get(
        'PROFILE_BATCH_GEN_ENABLED', 'false'
    ).strip().lower() in ('1', 'true', 'yes', 'on')
    PROFILE_BATCH_SIZE_INDIVIDUAL = int(os.environ.get('PROFILE_BATCH_SIZE_INDIVIDUAL', '5'))
    PROFILE_BATCH_SIZE_GROUP = int(os.environ.get('PROFILE_BATCH_SIZE_GROUP', '3'))

    # Plan #3：报告对话 RAG
    REPORT_CHAT_RAG_ENABLED = os.environ.get(
        'REPORT_CHAT_RAG_ENABLED', 'false'
    ).strip().lower() in ('1', 'true', 'yes', 'on')
    REPORT_CHAT_RAG_TOPK = int(os.environ.get('REPORT_CHAT_RAG_TOPK', '3'))

    # D15：prompt caching（隐式，依赖 Qwen DashScope / Anthropic prefix cache）
    PROMPT_CACHING_HINT_ENABLED = os.environ.get(
        'PROMPT_CACHING_HINT_ENABLED', 'true'
    ).strip().lower() in ('1', 'true', 'yes', 'on')

    @classmethod
    def get_optimization_flags(cls) -> dict:
        """D2：返回当前所有优化开关的快照，写入报告/profile 元数据。
        eval 框架据此知道一份数据是在什么配置下生成的。"""
        return {
            'report_context_compression': bool(cls.REPORT_CONTEXT_COMPRESSION_ENABLED),
            'report_prev_section_budget': int(cls.REPORT_PREV_SECTION_BUDGET or 0),
            'report_min_tool_calls': int(cls.REPORT_MIN_TOOL_CALLS or 0),
            'interview_dedup': bool(cls.INTERVIEW_DEDUP_ENABLED),
            'chunk_extract_batch': bool(cls.CHUNK_EXTRACT_BATCH_ENABLED),
            'chunk_extract_batch_size': int(cls.CHUNK_EXTRACT_BATCH_SIZE),
            'chunk_known_entities_trim': bool(cls.CHUNK_KNOWN_ENTITIES_TRIM_ENABLED),
            'profile_batch_gen': bool(cls.PROFILE_BATCH_GEN_ENABLED),
            'profile_batch_size_individual': int(cls.PROFILE_BATCH_SIZE_INDIVIDUAL),
            'profile_batch_size_group': int(cls.PROFILE_BATCH_SIZE_GROUP),
            'report_chat_rag': bool(cls.REPORT_CHAT_RAG_ENABLED),
            'report_chat_rag_topk': int(cls.REPORT_CHAT_RAG_TOPK),
            'prompt_caching_hint': bool(cls.PROMPT_CACHING_HINT_ENABLED),
            'variant_label': str(cls.REPORT_TOKEN_VARIANT_LABEL or ''),
        }
    
    @classmethod
    def is_local_graph(cls) -> bool:
        return cls.GRAPH_BACKEND == 'local'
    
    @classmethod
    def validate(cls):
        """验证必要配置。
        LLM_API_KEY 仅在图谱构建/模拟/报告生成时才真正需要；
        只读历史数据（浏览项目、查看图谱、阅读报告）完全不依赖 LLM，
        因此启动时不强制退出，仅记录警告。
        """
        if not cls.LLM_API_KEY:
            import warnings
            warnings.warn(
                "LLM_API_KEY 未配置，图谱构建/模拟/报告生成功能不可用，"
                "历史数据浏览不受影响。",
                RuntimeWarning,
                stacklevel=2,
            )
        return []  # 不阻断启动
    
    @classmethod
    def validate_local_graph(cls) -> list:
        """本地图谱模式下的依赖校验（用于 API /health 提示）"""
        errors = []
        if not cls.NEO4J_PASSWORD:
            errors.append("GRAPH_BACKEND=local 时需要 NEO4J_PASSWORD")
        if not cls.EMBEDDING_API_KEY:
            errors.append("GRAPH_BACKEND=local 时需要 EMBEDDING_API_KEY 或 LLM_API_KEY")
        return errors

