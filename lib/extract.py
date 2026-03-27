"""
テキスト抽出 — PDF (PyMuPDF), TXT, MD, CSV
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import fitz  # PyMuPDF


def clean_text(text: str) -> str:
    """抽出テキストの基本クリーニング"""
    if not text:
        return ""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def extract_pdf(file_path: str | Path) -> list[dict]:
    """PDF からページ単位でテキストを抽出。

    Returns:
        [{"page": int (1-based), "text": str}, ...]
    """
    doc = fitz.open(str(file_path))
    pages = []
    for i, page in enumerate(doc):
        text = clean_text(page.get_text("text"))
        pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


def extract_pdf_from_bytes(data: bytes, filename: str = "upload.pdf") -> list[dict]:
    """バイト列からPDFテキストを抽出（Streamlit file_uploader 用）"""
    doc = fitz.open(stream=data, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        text = clean_text(page.get_text("text"))
        pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


def extract_text_file(file_path: str | Path) -> str:
    """TXT / MD ファイルからテキストを読み込む"""
    return clean_text(Path(file_path).read_text(encoding="utf-8"))


def extract_text_from_bytes(data: bytes) -> str:
    """バイト列からテキストを読み込む（Streamlit file_uploader 用）"""
    return clean_text(data.decode("utf-8", errors="replace"))


def extract_csv(file_path: str | Path) -> str:
    """CSV ファイルを行単位のテキストに変換"""
    text = Path(file_path).read_text(encoding="utf-8")
    return _csv_to_text(text)


def extract_csv_from_bytes(data: bytes) -> str:
    """バイト列からCSVテキストを読み込む"""
    text = data.decode("utf-8", errors="replace")
    return _csv_to_text(text)


def _csv_to_text(csv_text: str) -> str:
    """CSV 文字列を読みやすいテキストに変換"""
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    if not rows:
        return ""
    header = rows[0]
    lines = []
    for row in rows[1:]:
        parts = [f"{h}: {v}" for h, v in zip(header, row) if v.strip()]
        if parts:
            lines.append(" | ".join(parts))
    return clean_text("\n".join(lines))


def extract_auto(file_path: str | Path) -> list[dict]:
    """拡張子に基づいて自動抽出。PDF はページ単位、他は単一ページとして返す。"""
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    elif suffix == ".csv":
        text = extract_csv(path)
        return [{"page": 1, "text": text}]
    else:  # .txt, .md, etc.
        text = extract_text_file(path)
        return [{"page": 1, "text": text}]


def extract_auto_from_bytes(data: bytes, filename: str) -> list[dict]:
    """バイト列 + ファイル名から自動抽出（Streamlit 用）"""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_from_bytes(data, filename)
    elif suffix == ".csv":
        text = extract_csv_from_bytes(data)
        return [{"page": 1, "text": text}]
    else:
        text = extract_text_from_bytes(data)
        return [{"page": 1, "text": text}]
