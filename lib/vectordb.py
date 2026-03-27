"""
ChromaDB 操作 — コレクション CRUD
"""
from __future__ import annotations

from datetime import datetime, timezone

import chromadb

from .config import CHROMA_DIR


def get_client() -> chromadb.ClientAPI:
    """ChromaDB PersistentClient を返す。"""
    return chromadb.PersistentClient(path=CHROMA_DIR)


def create_collection(
    name: str,
    embedding_model: str,
    embedding_dim: int,
    description: str = "",
    chunk_size: int = 500,
    chunk_overlap: int = 80,
) -> chromadb.Collection:
    """新規コレクション作成。同名があれば削除して再作成。"""
    client = get_client()
    try:
        client.delete_collection(name)
    except Exception:
        pass

    collection = client.create_collection(
        name=name,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": embedding_model,
            "embedding_dim": str(embedding_dim),
            "chunk_size": str(chunk_size),
            "chunk_overlap": str(chunk_overlap),
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return collection


def get_collection(name: str) -> chromadb.Collection:
    """既存コレクションを取得。"""
    client = get_client()
    return client.get_collection(name)


def add_chunks(
    collection: chromadb.Collection,
    chunks: list[dict],
    embeddings: list[list[float]],
    source_file: str = "",
) -> None:
    """チャンクと Embedding をコレクションに追加。"""
    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "source_file": source_file,
            "page": c.get("page", 0),
            "chunk_index": i,
            "text_preview": c["text"][:200],
        }
        for i, c in enumerate(chunks)
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def list_collections() -> list[dict]:
    """全コレクションのサマリーを返す。"""
    client = get_client()
    results = []
    for col in client.list_collections():
        meta = col.metadata or {}
        results.append({
            "name": col.name,
            "count": col.count(),
            "embedding_model": meta.get("embedding_model", ""),
            "description": meta.get("description", ""),
            "created_at": meta.get("created_at", ""),
        })
    return results


def delete_collection(name: str) -> None:
    """コレクション削除。"""
    client = get_client()
    client.delete_collection(name)


def get_collection_stats(name: str) -> dict:
    """コレクションの統計情報。"""
    col = get_collection(name)
    meta = col.metadata or {}
    return {
        "name": name,
        "count": col.count(),
        "embedding_model": meta.get("embedding_model", ""),
        "embedding_dim": meta.get("embedding_dim", ""),
        "chunk_size": meta.get("chunk_size", ""),
        "chunk_overlap": meta.get("chunk_overlap", ""),
        "description": meta.get("description", ""),
        "created_at": meta.get("created_at", ""),
    }
