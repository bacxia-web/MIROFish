"""
统一创建 zep_cloud.Zep 客户端。

自托管时在 .env 中设置 ZEP_API_URL（或 OpenZep 常用的 ZEP_BASE_URL），
无需改代码；详见 README「Zep 本地化」。
"""

from __future__ import annotations

from typing import Optional

from zep_cloud.client import Zep

from ..config import Config


def create_zep_client(api_key: Optional[str] = None) -> Zep:
    """使用当前配置创建 Zep 客户端（Zep Cloud 或自托管端点）。"""
    key = api_key if api_key is not None else Config.ZEP_API_KEY
    if not key:
        raise ValueError("ZEP_API_KEY 未配置")
    return Zep(api_key=key)
