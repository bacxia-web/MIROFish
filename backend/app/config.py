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
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
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
    
    @classmethod
    def is_local_graph(cls) -> bool:
        return cls.GRAPH_BACKEND == 'local'
    
    @classmethod
    def validate(cls):
        """验证必要配置（仅校验 LLM；ZEP 为可选，未配置时图谱构建接口会返回提示）"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置")
        return errors
    
    @classmethod
    def validate_local_graph(cls) -> list:
        """本地图谱模式下的依赖校验（用于 API /health 提示）"""
        errors = []
        if not cls.NEO4J_PASSWORD:
            errors.append("GRAPH_BACKEND=local 时需要 NEO4J_PASSWORD")
        if not cls.EMBEDDING_API_KEY:
            errors.append("GRAPH_BACKEND=local 时需要 EMBEDDING_API_KEY 或 LLM_API_KEY")
        return errors

