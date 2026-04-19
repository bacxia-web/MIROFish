"""
LLM客户端封装
统一使用OpenAI格式调用；支持多模型依次降级（额度/限流等自动换下一个）。
"""

import json
import re
from typing import Any, Dict, List, Optional, Sequence

from openai import APIStatusError, AuthenticationError, OpenAI, PermissionDeniedError

from ..config import Config
from .logger import get_logger
from .token_usage_service import record_llm_usage

_logger = get_logger('mirofish.llm')


def is_llm_quota_or_capacity_error(exc: BaseException) -> bool:
    """
    判断是否应换下一个模型重试（额度、限流、服务端繁忙、模型暂不可用等）。
    401/403 等同密钥或权限问题，不换模型重试。
    """
    msg = str(exc).lower()
    # 供应商会把额度不足包装成 403（如 AllocationQuota.FreeTierOnly），这类要允许切换模型
    if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
        if 'allocationquota.freetieronly' in msg or 'free tier' in msg or 'quota' in msg:
            return True
        return False
    if isinstance(exc, APIStatusError):
        code = exc.status_code
        if code == 401:
            return False
        if code == 403:
            if 'allocationquota.freetieronly' in msg or 'free tier' in msg or 'quota' in msg:
                return True
            return False
        # 400：可能是模型名无效或参数错误，换模型仍可能成功
        if code in (400, 402, 404, 408, 409, 422, 429, 500, 502, 503, 504):
            return True
        if code >= 500:
            return True
        return False
    keywords = (
        'quota',
        'rate limit',
        'throttl',
        'insufficient',
        '额度',
        '余额',
        'resource exhausted',
        'limit exceeded',
        'too many requests',
        'capacity',
        'billing',
        '欠费',
        'model not found',
        'does not exist',
        'unavailable',
        'overload',
        'server error',
        'timeout',
        'timed out',
    )
    return any(k in msg for k in keywords)


def chat_completions_with_model_fallback(
    client: OpenAI,
    models: Sequence[str],
    *,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict] = None,
) -> Any:
    """
    按 models 顺序调用 chat.completions.create，命中可重试类错误时自动换下一个模型。
    返回 SDK 的 ChatCompletion 对象。
    """
    last_exc: Optional[BaseException] = None
    models_list = list(models)
    if not models_list:
        raise ValueError('LLM_MODEL_CHAIN 为空，请配置 LLM_MODEL_FALLBACK_CHAIN 或 LLM_MODEL_NAME')

    for i, model in enumerate(models_list):
        kwargs: Dict[str, Any] = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
        }
        if max_tokens is not None:
            kwargs['max_tokens'] = max_tokens
        if (model or '').lower().startswith('qwen3'):
            kwargs['extra_body'] = {'enable_thinking': False}
        if response_format:
            kwargs['response_format'] = response_format
        try:
            return client.chat.completions.create(**kwargs)
        except BaseException as e:
            last_exc = e
            if i < len(models_list) - 1 and is_llm_quota_or_capacity_error(e):
                _logger.warning(
                    'LLM 模型 %s 调用失败，尝试下一个: %s',
                    model,
                    str(e)[:200],
                )
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError('LLM 无可用模型')


class LLMClient:
    """LLM客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        if model:
            self._models: List[str] = [model]
        else:
            self._models = list(Config.LLM_MODEL_CHAIN)
        if not self._models:
            raise ValueError('LLM_MODEL_CHAIN 为空')
        self.model = self._models[0]

        if not self.api_key:
            raise ValueError('LLM_API_KEY 未配置')

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        """
        发送聊天请求

        Returns:
            模型响应文本
        """
        response = chat_completions_with_model_fallback(
            self.client,
            self._models,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        try:
            usage = getattr(response, 'usage', None)
            prompt_tokens = int(getattr(usage, 'prompt_tokens', 0) or 0)
            completion_tokens = int(getattr(usage, 'completion_tokens', 0) or 0)
            total_tokens = int(getattr(usage, 'total_tokens', 0) or (prompt_tokens + completion_tokens))
            model_name = str(getattr(response, 'model', '') or '')
            record_llm_usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                model=model_name,
            )
        except Exception:
            # usage 统计不应影响主流程
            pass
        content = response.choices[0].message.content
        content = re.sub(r'<redacted_thinking>[\s\S]*?</redacted_thinking>', '', content).strip()
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={'type': 'json_object'},
        )
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f'LLM返回的JSON格式无效: {cleaned_response}')
