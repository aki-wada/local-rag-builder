"""
local-rag-builder — 設定
"""
import os
from pathlib import Path

# === Paths ===
PROJECT_ROOT = Path(__file__).parent.parent
DATA_HOME = Path(os.path.expanduser("~/.local-rag-builder"))
CHROMA_DIR = str(DATA_HOME / "vectordb")

# ディレクトリ作成
DATA_HOME.mkdir(parents=True, exist_ok=True)
(DATA_HOME / "vectordb").mkdir(parents=True, exist_ok=True)

# === Chunking ===
CHUNK_SIZE = 500          # 目標トークン数
CHUNK_OVERLAP = 80        # オーバーラップ（トークン数）
MIN_CHUNK_SIZE = 50       # 最小チャンクサイズ（トークン数）
CHARS_PER_TOKEN = 4       # 1 token ≈ 4 chars (英語基準)

# === Embedding ===
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_EMBED_MODEL = "qwen3-embedding"

ST_MODEL = "BAAI/bge-base-en-v1.5"  # sentence-transformers

EMBEDDING_BATCH_SIZE = 32

# === Search ===
TOP_K = 5
MAX_CONTEXT_TOKENS = 12000

# === API Server ===
API_PORT = 8322
