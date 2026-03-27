"""
local-rag-builder — Streamlit UI
RAG データの作成・管理ツール (Phase 1 MVP)
"""
import streamlit as st

from lib.config import OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL, ST_MODEL
from lib.extract import extract_auto_from_bytes
from lib.chunk import create_chunks
from lib.embed import embed, get_embedding_dim
from lib.vectordb import (
    create_collection,
    add_chunks,
    list_collections,
    delete_collection,
    get_collection_stats,
)

st.set_page_config(page_title="Local RAG Builder", page_icon="📚", layout="wide")

# =================================================================
# Session state 初期化
# =================================================================
if "extracted_pages" not in st.session_state:
    st.session_state.extracted_pages = None
if "chunks" not in st.session_state:
    st.session_state.chunks = None
if "filename" not in st.session_state:
    st.session_state.filename = ""

# =================================================================
# Sidebar — コレクション管理
# =================================================================
with st.sidebar:
    st.title("📚 Local RAG Builder")
    st.caption("RAG データ作成・管理ツール")

    st.divider()

    # --- Embedding 設定 ---
    st.subheader("Embedding 設定")
    backend = st.selectbox(
        "バックエンド",
        ["ollama", "sentence-transformers"],
        index=0,
    )
    if backend == "ollama":
        embed_model = st.text_input("モデル名", value=OLLAMA_EMBED_MODEL)
        base_url = st.text_input("Ollama URL", value=OLLAMA_BASE_URL)
    else:
        embed_model = st.text_input("モデル名", value=ST_MODEL)
        base_url = OLLAMA_BASE_URL  # unused

    st.divider()

    # --- コレクション一覧 ---
    st.subheader("コレクション")
    collections = list_collections()
    if collections:
        for col in collections:
            with st.expander(f"📁 {col['name']} ({col['count']} chunks)"):
                st.caption(f"モデル: {col['embedding_model']}")
                st.caption(f"説明: {col['description'] or '—'}")
                if st.button(f"🗑 削除", key=f"del_{col['name']}"):
                    delete_collection(col["name"])
                    st.rerun()
    else:
        st.info("コレクションがありません")

# =================================================================
# Main — アップロード → 抽出 → チャンク → Embed → 保存
# =================================================================
st.header("文書を追加")

# --- Step 1: ファイルアップロード ---
uploaded = st.file_uploader(
    "PDF / TXT / MD / CSV ファイルを選択",
    type=["pdf", "txt", "md", "csv", "text"],
    accept_multiple_files=False,
)

if uploaded:
    if uploaded.name != st.session_state.filename:
        st.session_state.filename = uploaded.name
        st.session_state.extracted_pages = None
        st.session_state.chunks = None

    # --- Step 2: テキスト抽出 ---
    if st.session_state.extracted_pages is None:
        with st.spinner("テキストを抽出中..."):
            pages = extract_auto_from_bytes(uploaded.getvalue(), uploaded.name)
            st.session_state.extracted_pages = pages

    pages = st.session_state.extracted_pages
    total_chars = sum(len(p["text"]) for p in pages)
    non_empty = sum(1 for p in pages if p["text"].strip())
    st.success(f"抽出完了: {len(pages)} ページ / {non_empty} ページにテキスト / {total_chars:,} 文字")

    # 抽出テキストのプレビュー
    with st.expander("📄 抽出テキスト プレビュー", expanded=False):
        for p in pages[:20]:
            if p["text"].strip():
                st.markdown(f"**ページ {p['page']}**")
                st.text(p["text"][:500] + ("..." if len(p["text"]) > 500 else ""))
                st.divider()
        if len(pages) > 20:
            st.caption(f"... 他 {len(pages) - 20} ページ")

    # --- Step 3: チャンク分割 ---
    st.subheader("チャンク設定")
    col1, col2, col3 = st.columns(3)
    with col1:
        chunk_size = st.number_input("チャンクサイズ (tokens)", 100, 2000, 500, step=50)
    with col2:
        chunk_overlap = st.number_input("オーバーラップ (tokens)", 0, 500, 80, step=10)
    with col3:
        min_chunk = st.number_input("最小サイズ (tokens)", 10, 200, 50, step=10)

    if st.button("チャンク分割を実行"):
        with st.spinner("チャンク分割中..."):
            chunks = create_chunks(pages, chunk_size, chunk_overlap, min_chunk)
            st.session_state.chunks = chunks

    if st.session_state.chunks:
        chunks = st.session_state.chunks
        st.info(f"{len(chunks)} チャンクに分割されました")

        with st.expander("🔍 チャンク プレビュー", expanded=False):
            for i, c in enumerate(chunks[:30]):
                st.markdown(f"**{c['id']}** (p.{c['page']}, {len(c['text'])} chars)")
                st.text(c["text"][:300] + ("..." if len(c["text"]) > 300 else ""))
                st.divider()
            if len(chunks) > 30:
                st.caption(f"... 他 {len(chunks) - 30} チャンク")

        # --- Step 4: Embedding & 保存 ---
        st.subheader("コレクションに保存")
        col_name = st.text_input(
            "コレクション名",
            value=uploaded.name.rsplit(".", 1)[0].replace(" ", "_").lower(),
        )
        col_desc = st.text_input("説明 (任意)", value="")

        if st.button("Embedding を実行して保存", type="primary"):
            if not col_name.strip():
                st.error("コレクション名を入力してください")
            else:
                progress_bar = st.progress(0, text="Embedding 中...")
                status_text = st.empty()

                try:
                    # 次元数チェック
                    status_text.text("Embedding バックエンドに接続中...")
                    dim = get_embedding_dim(
                        backend=backend,
                        model=embed_model,
                        base_url=base_url,
                    )
                    status_text.text(f"次元数: {dim}")

                    # Embedding
                    texts = [c["text"] for c in chunks]

                    def on_progress(done: int, total: int) -> None:
                        progress_bar.progress(
                            done / total,
                            text=f"Embedding: {done}/{total} チャンク",
                        )

                    embeddings = embed(
                        texts,
                        backend=backend,
                        model=embed_model,
                        base_url=base_url,
                        on_progress=on_progress,
                    )

                    # コレクション作成 & 保存
                    status_text.text("ChromaDB に保存中...")
                    collection = create_collection(
                        name=col_name.strip(),
                        embedding_model=embed_model,
                        embedding_dim=dim,
                        description=col_desc,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                    add_chunks(collection, chunks, embeddings, source_file=uploaded.name)

                    progress_bar.progress(1.0, text="完了")
                    status_text.text("")
                    st.success(
                        f"コレクション「{col_name}」に {len(chunks)} チャンクを保存しました "
                        f"(モデル: {embed_model}, 次元: {dim})"
                    )
                    st.balloons()

                except Exception as e:
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"エラー: {e}")
