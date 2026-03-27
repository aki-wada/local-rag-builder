"""
Embedding — Ollama / sentence-transformers デュアル対応
"""
from __future__ import annotations

from typing import Callable

import requests

from .config import (
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    ST_MODEL,
    EMBEDDING_BATCH_SIZE,
)

# sentence-transformers モデルのシングルトンキャッシュ
_st_model_cache: dict[str, object] = {}


def embed_ollama(
    texts: list[str],
    model: str = OLLAMA_EMBED_MODEL,
    base_url: str = OLLAMA_BASE_URL,
    batch_size: int = EMBEDDING_BATCH_SIZE,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[list[float]]:
    """Ollama /api/embed でバッチ Embedding。

    Returns:
        各テキストの埋め込みベクトルのリスト
    """
    all_embeddings: list[list[float]] = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch = texts[i: i + batch_size]
        resp = requests.post(
            f"{base_url}/api/embed",
            json={"model": model, "input": batch},
            timeout=120,
        )
        resp.raise_for_status()
        embeddings = resp.json().get("embeddings", [])
        all_embeddings.extend(embeddings)

        if on_progress:
            on_progress(min(i + batch_size, total), total)

    return all_embeddings


def embed_sentence_transformers(
    texts: list[str],
    model_name: str = ST_MODEL,
    batch_size: int = EMBEDDING_BATCH_SIZE,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[list[float]]:
    """sentence-transformers でバッチ Embedding。

    Returns:
        各テキストの埋め込みベクトルのリスト
    """
    from sentence_transformers import SentenceTransformer

    if model_name not in _st_model_cache:
        _st_model_cache[model_name] = SentenceTransformer(model_name)
    model = _st_model_cache[model_name]

    all_embeddings: list[list[float]] = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch = texts[i: i + batch_size]
        vecs = model.encode(batch, show_progress_bar=False).tolist()
        all_embeddings.extend(vecs)

        if on_progress:
            on_progress(min(i + batch_size, total), total)

    return all_embeddings


def embed(
    texts: list[str],
    backend: str = "ollama",
    model: str | None = None,
    base_url: str = OLLAMA_BASE_URL,
    batch_size: int = EMBEDDING_BATCH_SIZE,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[list[float]]:
    """統合 Embedding インターフェース。

    Args:
        backend: "ollama" or "sentence-transformers"
        model: モデル名（None ならデフォルト）
    """
    if backend == "ollama":
        return embed_ollama(
            texts,
            model=model or OLLAMA_EMBED_MODEL,
            base_url=base_url,
            batch_size=batch_size,
            on_progress=on_progress,
        )
    elif backend == "sentence-transformers":
        return embed_sentence_transformers(
            texts,
            model_name=model or ST_MODEL,
            batch_size=batch_size,
            on_progress=on_progress,
        )
    else:
        raise ValueError(f"Unknown embedding backend: {backend}")


def get_embedding_dim(
    backend: str = "ollama",
    model: str | None = None,
    base_url: str = OLLAMA_BASE_URL,
) -> int:
    """テスト Embedding を1件実行して次元数を返す。"""
    vecs = embed(["test"], backend=backend, model=model, base_url=base_url)
    return len(vecs[0])
