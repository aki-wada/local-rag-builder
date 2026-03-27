# Local RAG Builder — 技術要望書

## 1. プロジェクト概要

### 1.1 背景

ローカル LLM チャットアプリ（Local LLM Workspace）に RAG（Retrieval-Augmented Generation）機能を導入するにあたり、**データの作成・管理**と**検索・参照**を明確に分離する必要がある。

従来はチャットアプリ内でブラウザ IndexedDB にデータを格納していたが、以下の課題があった：

- ブラウザ localStorage/IndexedDB のストレージ制約（5-10MB）
- 文書の前処理（OCR、チャンク戦略の調整）が困難
- データの永続性・可搬性が低い
- チャットアプリの責務が肥大化

### 1.2 目的

PDF・テキスト文書を取り込み、チャンク分割・Embedding 生成・ベクトル DB 保存までを行う**専用のデスクトップツール**を構築する。チャットアプリからは検索 API を介してデータを参照する。

### 1.3 ユーザー

- 放射線科医・医学研究者
- 大学教育関係者
- ローカル LLM を日常的に使用する技術者

### 1.4 運用環境

| 項目 | 仕様 |
|------|------|
| OS | macOS Sonoma（主）/ Linux |
| ネットワーク | **完全オフライン対応**（院内ネットワーク環境） |
| LLM バックエンド | Ollama / LM Studio / mlx-lm（ローカル） |
| Python | 3.11+ |
| ブラウザ | Streamlit UI はローカルホストで動作 |

---

## 2. 機能要件

### 2.1 文書取り込み

| ID | 要件 | 優先度 |
|----|------|--------|
| F-01 | PDF ファイルからテキストを抽出する（PyMuPDF） | 必須 |
| F-02 | スキャン PDF に対し OCR フォールバックを提供する（Ollama glm-ocr） | 高 |
| F-03 | TXT / MD / CSV ファイルからテキストを読み込む | 必須 |
| F-04 | 抽出テキストをページ単位でプレビュー表示する | 高 |
| F-05 | 抽出テキストを手動で編集してからチャンク化できる | 中 |

### 2.2 チャンク分割

| ID | 要件 | 優先度 |
|----|------|--------|
| F-10 | チャンクサイズ・オーバーラップ・最小サイズを UI から設定できる | 必須 |
| F-11 | 日本語（`。！？`）と英語（`. ! ?`）の文境界を考慮して分割する | 必須 |
| F-12 | パラグラフ → 文 → 単語の順にフォールバック分割する | 必須 |
| F-13 | チャンク分割結果をプレビュー表示する | 高 |

### 2.3 Embedding 生成

| ID | 要件 | 優先度 |
|----|------|--------|
| F-20 | Ollama `/api/embed`（qwen3-embedding 等）で Embedding を生成する | 必須 |
| F-21 | sentence-transformers（BAAI/bge-base-en-v1.5 等）で Embedding を生成する | 必須 |
| F-22 | コレクション作成時にバックエンドとモデルを選択できる | 必須 |
| F-23 | バッチ処理でプログレスバーを表示する | 高 |
| F-24 | 接続テスト（Embedding バックエンドの疎通確認）を実行できる | 中 |

### 2.4 ベクトル DB（ChromaDB）

| ID | 要件 | 優先度 |
|----|------|--------|
| F-30 | コレクションの作成・削除ができる | 必須 |
| F-31 | コレクションにチャンク + Embedding を追加できる | 必須 |
| F-32 | コレクション一覧（名前、チャンク数、モデル、説明）を表示する | 必須 |
| F-33 | コレクションのメタデータ（Embedding モデル、次元数、チャンク設定）を保存する | 必須 |
| F-34 | 個別文書の削除・再 Embedding ができる | 中 |

### 2.5 検索 API（チャットアプリ連携）

| ID | 要件 | 優先度 |
|----|------|--------|
| F-40 | GreenBook API 互換の `/api/search` エンドポイントを提供する | 必須 |
| F-41 | `/api/health` エンドポイントで稼働状況を返す | 必須 |
| F-42 | チャットアプリ側はバックエンド URL を変更するだけで接続できる | 必須 |
| F-43 | トークンバジェットに基づくコンテキスト量の制御を行う | 高 |

### 2.6 テスト検索

| ID | 要件 | 優先度 |
|----|------|--------|
| F-50 | Streamlit UI 上でクエリを入力してベクトル検索結果を確認できる | 高 |
| F-51 | スコア（類似度）、出典ページ、テキスト抜粋を表示する | 高 |

---

## 3. 非機能要件

| ID | 要件 | 詳細 |
|----|------|------|
| NF-01 | **完全ローカル動作** | 外部 API・クラウドサービスへの通信を行わない |
| NF-02 | **プライバシー** | PHI/PII を含む医療文書を扱うため、データは端末内に留める |
| NF-03 | **永続性** | ChromaDB のデータは `~/.local-rag-builder/vectordb/` に永続保存 |
| NF-04 | **可搬性** | オフライン環境へ `pip install --no-index` で導入可能 |
| NF-05 | **起動の簡便さ** | `.command` ファイルのダブルクリックで起動 |
| NF-06 | **日本語対応** | UI ラベル・チャンク分割・検索すべて日本語対応 |

---

## 4. 技術スタック

| レイヤー | 技術 | 選定理由 |
|---------|------|---------|
| UI | Streamlit | ワークスペース内で実績あり。ファイルアップロード・プログレスバー等が標準装備 |
| 検索 API | FastAPI + uvicorn | greenbook-rag で実績あり。チャットアプリとの互換性を維持 |
| PDF 抽出 | PyMuPDF (fitz) | 高速・軽量。greenbook-rag で実証済み |
| OCR | Ollama glm-ocr | ローカル動作。スキャン文書のテキスト化 |
| Embedding (1) | Ollama `/api/embed` | qwen3-embedding — 日本語対応、ローカル完結 |
| Embedding (2) | sentence-transformers | BAAI/bge-base-en-v1.5 — 英語文書に強い、greenbook-rag 実績 |
| Vector DB | ChromaDB | 軽量・永続化対応・Python ネイティブ。greenbook-rag で実証済み |
| Python | 3.11+ | ワークスペース標準 |

---

## 5. システム構成図

```
┌─────────────────────────────────────────────────┐
│  Local RAG Builder (本アプリ)                     │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ Streamlit │  │ FastAPI  │  │  ChromaDB      │ │
│  │ UI        │  │ :8322    │  │  (~/.local-    │ │
│  │ :8501     │  │          │  │   rag-builder/ │ │
│  │           │  │ /api/    │  │   vectordb/)   │ │
│  │ 文書管理   │→│ search   │←│                │ │
│  │ チャンク   │  │ /api/    │  │  コレクション   │ │
│  │ Embedding │  │ health   │  │  管理          │ │
│  └──────────┘  └────┬─────┘  └────────────────┘ │
└─────────────────────┼───────────────────────────┘
                      │ HTTP (localhost)
                      ▼
┌─────────────────────────────────────────────────┐
│  Local LLM Workspace (チャットアプリ)             │
│                                                   │
│  設定 > RAG > GreenBook URL                       │
│  → http://localhost:8322                          │
│                                                   │
│  ユーザーの質問                                    │
│    → POST /api/search → 関連チャンク取得           │
│    → コンテキストとして LLM に送信                  │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  Ollama / LM Studio / mlx-lm                     │
│  (Embedding 生成 & LLM 推論)                      │
└─────────────────────────────────────────────────┘
```

---

## 6. API 仕様

### 6.1 POST /api/search

チャットアプリからの検索リクエスト。GreenBook API 完全互換。

**Request:**
```json
{
  "question": "Chiari malformation の画像所見は？",
  "top_k": 5
}
```

**Response:**
```json
{
  "question": "Chiari malformation の画像所見は？",
  "chunks": [
    {
      "id": "chunk_00012",
      "page": 3,
      "text": "Chiari I Malformation\n= downward displacement of cerebellar tonsils...",
      "score": 0.847
    }
  ],
  "chunks_used": 3,
  "context": "【参照文書（RAG検索結果）】\n..."
}
```

### 6.2 GET /api/health

稼働確認エンドポイント。

**Response:**
```json
{
  "status": "ok",
  "vectordb_chunks": 1842,
  "collections": ["greenbook7", "radiology_manual"],
  "embedding_backend": "ollama"
}
```

---

## 7. データモデル

### 7.1 コレクション メタデータ

```python
collection.metadata = {
    "embedding_model": "qwen3-embedding",
    "embedding_dim": "1024",
    "chunk_size": "500",
    "chunk_overlap": "80",
    "description": "Radiology Review Manual 7th Edition",
    "created_at": "2026-03-27T12:00:00+00:00"
}
```

### 7.2 チャンク メタデータ

```python
chunk_metadata = {
    "source_file": "greenbook7.pdf",
    "page": 15,
    "chunk_index": 42,
    "text_preview": "Chiari I Malformation = downward displacement..."
}
```

---

## 8. 制約事項

| 制約 | 詳細 |
|------|------|
| 単一端末運用 | マルチユーザー・リモートアクセスは想定しない |
| Embedding モデル混在不可 | 1 コレクション = 1 Embedding モデル |
| コレクションサイズ | 数千〜数万チャンク規模を想定（数百万は非対応） |
| OCR 精度 | glm-ocr の精度に依存。完全な正確性は保証しない |
