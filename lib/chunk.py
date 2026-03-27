"""
チャンク分割 — 日本語・英語混在対応
"""
from __future__ import annotations

import re

from .config import CHUNK_SIZE, CHUNK_OVERLAP, MIN_CHUNK_SIZE, CHARS_PER_TOKEN


def fallback_split(text: str, max_chars: int) -> list[str]:
    """テキストを再帰的に分割 (paragraph → line → sentence → space)"""
    if len(text) <= max_chars:
        return [text]

    # 日本語句読点も含むセパレータ
    separators = ["\n\n", "\n", "。", ". ", "！", "？", " "]
    for sep in separators:
        parts = text.split(sep)
        if len(parts) <= 1:
            continue

        chunks: list[str] = []
        current = ""
        for part in parts:
            candidate = current + sep + part if current else part
            if len(candidate) > max_chars and current:
                chunks.append(current.strip())
                current = part
            else:
                current = candidate

        if current.strip():
            chunks.append(current.strip())

        if len(chunks) > 1:
            result: list[str] = []
            for c in chunks:
                if len(c) > max_chars:
                    result.extend(fallback_split(c, max_chars))
                else:
                    result.append(c)
            return result

    return [text]


def create_chunks(
    pages: list[dict],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    min_chunk_size: int = MIN_CHUNK_SIZE,
) -> list[dict]:
    """ページ構造を考慮してチャンク分割。

    Args:
        pages: [{"page": int, "text": str}, ...]
        chunk_size: 目標トークン数
        chunk_overlap: オーバーラップ（トークン数）
        min_chunk_size: 最小チャンクサイズ（トークン数）

    Returns:
        [{"id": str, "page": int, "text": str}, ...]
    """
    max_chars = chunk_size * CHARS_PER_TOKEN
    overlap_chars = chunk_overlap * CHARS_PER_TOKEN
    min_chars = min_chunk_size * CHARS_PER_TOKEN

    chunks: list[dict] = []
    chunk_id = 0
    current_chunk = ""
    current_start_page = 1

    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"]
        if not text.strip():
            continue

        # パラグラフ単位で分割
        paragraphs = re.split(r"\n{2,}", text)

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # パラグラフが大きすぎる場合はフォールバック分割
            if len(para) > max_chars * 2:
                if current_chunk:
                    chunks.append({
                        "id": f"chunk_{chunk_id:05d}",
                        "page": current_start_page,
                        "text": current_chunk.strip(),
                    })
                    chunk_id += 1
                    current_chunk = ""

                sub_chunks = fallback_split(para, max_chars)
                for j, sc in enumerate(sub_chunks):
                    if j == len(sub_chunks) - 1:
                        current_chunk = sc
                        current_start_page = page_num
                    else:
                        chunks.append({
                            "id": f"chunk_{chunk_id:05d}",
                            "page": page_num,
                            "text": sc.strip(),
                        })
                        chunk_id += 1
                continue

            # 通常: バッファに追加
            if len(current_chunk) + len(para) + 2 > max_chars:
                if current_chunk:
                    chunks.append({
                        "id": f"chunk_{chunk_id:05d}",
                        "page": current_start_page,
                        "text": current_chunk.strip(),
                    })
                    chunk_id += 1
                    # オーバーラップ
                    if overlap_chars > 0 and len(current_chunk) > overlap_chars:
                        current_chunk = current_chunk[-overlap_chars:] + "\n\n" + para
                    else:
                        current_chunk = para
                    current_start_page = page_num
                else:
                    current_chunk = para
                    current_start_page = page_num
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                    current_start_page = page_num

    # 残りバッファ
    if current_chunk.strip():
        if len(current_chunk.strip()) < min_chars and chunks:
            chunks[-1]["text"] += "\n\n" + current_chunk.strip()
        else:
            chunks.append({
                "id": f"chunk_{chunk_id:05d}",
                "page": current_start_page,
                "text": current_chunk.strip(),
            })

    return chunks
