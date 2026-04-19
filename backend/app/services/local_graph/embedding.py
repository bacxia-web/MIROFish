"""文本向量（OpenAI-compatible embeddings API）。"""

from __future__ import annotations

from typing import List, Optional

from openai import OpenAI

from ...config import Config


class EmbeddingService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or Config.EMBEDDING_API_KEY
        self.base_url = (base_url or Config.EMBEDDING_BASE_URL or '').rstrip('/')
        self.model = model or Config.EMBEDDING_MODEL_NAME
        if not self.api_key:
            raise ValueError('EMBEDDING_API_KEY 或 LLM_API_KEY 未配置')
        url = self.base_url
        if url and not url.endswith('/v1'):
            url = f'{url}/v1'
        self._client = OpenAI(api_key=self.api_key, base_url=url)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        # 多数兼容接口支持批量；单条失败时逐条重试
        try:
            resp = self._client.embeddings.create(model=self.model, input=texts)
            return [d.embedding for d in resp.data]
        except Exception:
            out: List[List[float]] = []
            for t in texts:
                resp = self._client.embeddings.create(model=self.model, input=t)
                out.append(resp.data[0].embedding)
            return out

    def embed_one(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]
