from typing import Optional

import asyncio
from anyio.streams import text
from huggingface_hub import AsyncInferenceClient, InferenceClient
from langchain_core.embeddings import Embeddings

from app.conf.app_config import EmbeddingConfig, app_config


class HuggingFaceEndpointEmbeddings(Embeddings):
    """兼容自定义 endpoint URL 的 HuggingFace 推理端点 Embedding 客户端。

    langchain-huggingface>=1.2.2 的 HuggingFaceEndpointEmbeddings 不再支持
    直接传入 endpoint URL，因此使用 huggingface_hub.InferenceClient 自行封装。
    """

    def __init__(
        self,
        endpoint_url: str,
        model: Optional[str] = None,
        token: Optional[str] = None,
        model_kwargs: Optional[dict] = None,
    ):
        self.endpoint_url = endpoint_url
        self.model = model
        self.model_kwargs = model_kwargs or {}
        self.client = InferenceClient(model=endpoint_url, token=token)
        self.async_client = AsyncInferenceClient(model=endpoint_url, token=token)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # replace newlines, which can negatively affect performance.
        texts = [text.replace("\n", " ") for text in texts]
        responses = self.client.feature_extraction(text=texts, **self.model_kwargs)
        return responses.tolist()

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        # replace newlines, which can negatively affect performance.
        texts = [text.replace("\n", " ") for text in texts]
        responses = await self.async_client.feature_extraction(
            text=texts, **self.model_kwargs
        )
        return responses.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed_documents([text]))[0]


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.client: HuggingFaceEndpointEmbeddings | None = None
        self.config = config

    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"

    def init(self):
        self.client = HuggingFaceEndpointEmbeddings(
            endpoint_url=self._get_url(),
            model=self.config.model,
        )


embedding_client_manager = EmbeddingClientManager(app_config.embedding)

if __name__== '__main__':
    embedding_client_manager.init()
    client = embedding_client_manager.client

    async def test():
        text = "what  is deep learniing"
        query_result = await client.aembed_query(text)
        print(query_result[:3])

    asyncio.run(test())
