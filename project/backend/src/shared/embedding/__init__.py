"""이미지·텍스트 임베딩 (FashionCLIP, 512차원, L2 정규화). 슬라이스는 get_embedding_model() 로만 접근한다."""
import hashlib
import io
from functools import lru_cache
from typing import Protocol

import numpy as np

from common.entity import EMBEDDING_DIMENSION
from shared.config import EmbeddingMode, get_settings


class EmbeddingModel(Protocol):
    def embed_images(self, images: list[bytes]) -> list[list[float]]: ...
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


def normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector if norm == 0 else vector / norm


class FashionClipEmbeddingModel:
    def __init__(self, model_name: str) -> None:
        # torch 는 무겁기 때문에 실제 사용 시점에만 import
        import torch
        from transformers import CLIPModel, CLIPProcessor

        self._torch = torch
        self._model = CLIPModel.from_pretrained(model_name).eval()
        self._processor = CLIPProcessor.from_pretrained(model_name)

    def embed_images(self, images: list[bytes]) -> list[list[float]]:
        from PIL import Image

        pil_images = [Image.open(io.BytesIO(image)).convert("RGB") for image in images]
        with self._torch.no_grad():
            inputs = self._processor(images=pil_images, return_tensors="pt")
            features = self._projected(self._model.get_image_features(**inputs))
        return [normalize(row).tolist() for row in features.numpy()]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        with self._torch.no_grad():
            inputs = self._processor(text=texts, return_tensors="pt", padding=True, truncation=True)
            features = self._projected(self._model.get_text_features(**inputs))
        return [normalize(row).tolist() for row in features.numpy()]

    @staticmethod
    def _projected(output):
        # transformers 5.x 는 출력 객체(pooler_output = 512차원 투영값), 4.x 는 텐서를 돌려준다
        return output.pooler_output if hasattr(output, "pooler_output") else output


class FakeEmbeddingModel:
    """테스트용. 같은 입력 → 같은 벡터."""

    @staticmethod
    def _vector_from_bytes(data: bytes) -> list[float]:
        seed = int.from_bytes(hashlib.sha256(data).digest()[:8], "big")
        return normalize(np.random.default_rng(seed).standard_normal(EMBEDDING_DIMENSION)).tolist()

    def embed_images(self, images: list[bytes]) -> list[list[float]]:
        return [self._vector_from_bytes(image) for image in images]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_from_bytes(text.encode()) for text in texts]


@lru_cache
def get_embedding_model() -> EmbeddingModel:
    settings = get_settings()
    if settings.embedding_mode == EmbeddingMode.FAKE:
        return FakeEmbeddingModel()
    return FashionClipEmbeddingModel(settings.embedding_model_name)
