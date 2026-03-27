# Local RAG Builder — 開発計画

## 1. 開発方針

- **逐次開発**: Phase ごとに動作確認し、段階的に機能追加
- **greenbook-rag 参照**: 実証済みコードを適切に流用・汎用化
- **既存互換**: チャットアプリ側のコード変更なしで連携可能にする
- **最小構成**: 必要十分な機能から始め、過剰な抽象化を避ける

---

## 2. フェーズ構成

### Phase 1: コアパイプライン（MVP）✅ 完了

> PDF → テキスト抽出 → チャンク分割 → Embedding → ChromaDB 保存

| ファイル | 内容 | 状態 |
|---------|------|------|
| `lib/config.py` | パス・デフォルト設定 | ✅ |
| `lib/extract.py` | PDF/TXT/MD/CSV テキスト抽出 (PyMuPDF) | ✅ |
| `lib/chunk.py` | チャンク分割（日英混在・句読点境界対応） | ✅ |
| `lib/embed.py` | Ollama + sentence-transformers デュアル対応 | ✅ |
| `lib/vectordb.py` | ChromaDB コレクション CRUD | ✅ |
| `app.py` | Streamlit UI（アップロード→チャンク→Embed→保存） | ✅ |
| `requirements.txt` | 依存パッケージ | ✅ |

**検証方法:**
1. `streamlit run app.py` で起動
2. PDF をアップロード → テキスト抽出結果を確認
3. チャンク分割を実行 → チャンク数・内容を確認
4. Embedding 実行 → ChromaDB に保存完了を確認

---

### Phase 2: プレビュー・編集 + OCR

> 抽出テキストの品質確認・手動修正と、スキャン PDF 対応

| ファイル | 内容 | 依存 |
|---------|------|------|
| `app.py` 拡張 | ページ別テキスト編集 (`st.text_area`) | Phase 1 |
| `app.py` 拡張 | チャンク境界のビジュアルプレビュー | Phase 1 |
| `lib/ocr.py` | Ollama glm-ocr による OCR | Ollama + glm-ocr |

**OCR フロー:**
```
PDF ページ
  → PyMuPDF でテキスト抽出
  → テキスト量が閾値未満？
    → Yes: ページを画像レンダリング (300 DPI)
           → base64 エンコード
           → Ollama glm-ocr に送信
           → OCR テキストで補完
    → No: そのまま使用
```

**参照コード:**
- `greenbook-rag/01b_ocr_extract.py` — `render_page_to_base64()` + glm-ocr 呼び出しパターン

**検証方法:**
1. テキスト抽出不良の PDF（スキャン文書）をアップロード
2. OCR フォールバックが自動実行されることを確認
3. 手動編集 → チャンク化 → 編集内容が反映されることを確認

---

### Phase 3: 検索 API + テスト検索

> チャットアプリとの接続と、データ品質の確認手段

| ファイル | 内容 | 依存 |
|---------|------|------|
| `lib/search.py` | ベクトル検索 + トークンバジェット制御 | Phase 1 |
| `api_server.py` | FastAPI `/api/search`, `/api/health` (ポート 8322) | Phase 1 |
| `app.py` 拡張 | テスト検索パネル | Phase 1 |
| `start.command` | macOS ランチャー（API + Streamlit 同時起動） | Phase 3 |

**API 設計:**
```
POST /api/search
  ← { "question": "...", "top_k": N }
  → { "question", "chunks": [{id, page, text, score}], "chunks_used", "context" }

GET /api/health
  → { "status", "vectordb_chunks", "collections", "embedding_backend" }
```

**参照コード:**
- `greenbook-rag/query_core.py` — `search()`, `build_context_with_budget()`, `detect_language()`
- `greenbook-rag/05_webapp.py` — `/api/search` レスポンス形式

**検証方法:**
1. `python api_server.py` で API サーバー起動
2. `curl -X POST http://localhost:8322/api/search -H 'Content-Type: application/json' -d '{"question":"test","top_k":3}'`
3. チャットアプリ → 設定 → RAG → GreenBook URL を `http://localhost:8322` に変更
4. 質問 → RAG コンテキストが応答に反映されることを確認

---

### Phase 4: コレクション管理

> 長期運用に必要な管理機能

| ファイル | 内容 | 依存 |
|---------|------|------|
| `app.py` 拡張 | コレクション詳細画面 | Phase 1 |
| `lib/vectordb.py` 拡張 | 文書単位の削除・再 Embedding | Phase 1 |

**機能:**
- コレクション一覧（チャンク数、モデル、文書リスト、作成日）
- 文書の個別削除（source_file でフィルタして該当チャンクを削除）
- コレクションの説明・メタデータ編集
- 別モデルでの再 Embedding（コレクション再構築）

**検証方法:**
1. 複数文書を同一コレクションに追加
2. 1 文書を削除 → チャンク数が減少することを確認
3. 再 Embedding → 新しいモデルのメタデータに更新されることを確認

---

## 3. プロジェクト構成（最終形）

```
local-rag-builder/
  app.py                  # Streamlit メイン UI
  api_server.py           # FastAPI 検索 API（Phase 3）
  start.command           # macOS ランチャー（Phase 3）
  lib/
    __init__.py
    config.py             # 設定
    extract.py            # テキスト抽出
    ocr.py                # OCR（Phase 2）
    chunk.py              # チャンク分割
    embed.py              # Embedding
    vectordb.py           # ChromaDB CRUD
    search.py             # 検索ロジック（Phase 3）
  docs/
    REQUIREMENTS.md       # 技術要望書（本書の対）
    DEVELOPMENT_PLAN.md   # 開発計画（本書）
  mockup.html             # UI モックアップ
  requirements.txt        # 依存パッケージ
  .gitignore
```

**データ保存先（リポジトリ外）:**
```
~/.local-rag-builder/
  vectordb/               # ChromaDB 永続ストレージ
```

---

## 4. 依存パッケージ

```
streamlit>=1.30.0           # UI
fastapi>=0.100.0            # 検索 API
uvicorn>=0.20.0             # ASGI サーバー
chromadb>=0.4.0             # ベクトル DB
PyMuPDF>=1.24.0             # PDF テキスト抽出
sentence-transformers>=2.2.0 # Embedding (バックエンド 2)
requests>=2.31.0            # Ollama API 呼び出し
tqdm>=4.60.0                # プログレス表示
```

---

## 5. greenbook-rag との関係

| 観点 | greenbook-rag | local-rag-builder |
|------|---------------|-------------------|
| 目的 | 特定書籍 (GreenBook 7th) 専用 RAG | 汎用的な文書 RAG データ作成 |
| UI | CLI + 簡易 Web (Jinja2) | Streamlit（対話的操作） |
| Embedding | sentence-transformers 固定 | Ollama / sentence-transformers 選択可 |
| 文書 | 1 冊の PDF | 複数ファイル・複数コレクション |
| API | `/api/search` (ポート 8321) | `/api/search` (ポート 8322)、互換形式 |
| 共存 | 独立して稼働可能 | 独立して稼働可能 |

両プロジェクトは**独立して並行稼働**できる。チャットアプリ側で接続先 URL を切り替えるだけで使い分け可能。

---

## 6. リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| Ollama 未起動時の Embedding 失敗 | ユーザーが原因を特定しにくい | 接続テスト機能 + 明確なエラーメッセージ |
| 大容量 PDF（1000+ ページ）の処理時間 | UI がフリーズして見える | プログレスバー + バッチ処理 |
| Embedding 次元不一致 | 検索結果が返らない | コレクションにモデル情報を保存し、不一致時に警告 |
| ChromaDB データ破損 | コレクション消失 | `~/.local-rag-builder/vectordb/` を定期バックアップ（手動） |
| スキャン PDF の OCR 精度 | チャンク品質が低下 | Phase 2 で手動編集機能を提供 |
