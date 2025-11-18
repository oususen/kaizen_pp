# 改善提案ワークフロー（Django + Vue）

要件定義に基づき、改善提案を登録・多段階で承認できる Web アプリケーションを Django REST API と Vue（Vite）で構築しました。  
バックエンドは組織階層/提案/承認ステータスを管理し、フロントエンドは提案登録フォームと承認 UI を提供します。

## ディレクトリ構成

```
backend/        Django プロジェクト (kaizen_backend) と API アプリ (proposals)
frontend/       Vue 3 (Vite) ベースの SPA
requirements.txt  Python 依存ライブラリ
frontend/.env.example  API エンドポイント設定例
```

## 1. バックエンド（Django REST）

### 1.1 セットアップ

```bash
cd backend
python -m venv venv        # 既存環境があれば省略
venv\Scripts\activate
pip install -r ..\requirements.txt
python manage.py migrate
```

### 1.2 開発サーバー

```bash
python manage.py runserver 0.0.0.0:8000
```

エンドポイント例

- `GET /api/departments/` … 組織一覧
- `GET/POST /api/proposals/` … 提案の一覧/作成（`stage`/`status` クエリで絞り込み）
- `POST /api/proposals/<id>/approve/` … 指定ステージの承認/差し戻し（`stage`, `status`, `comment`, `score`）

### 1.3 管理画面

```bash
python manage.py createsuperuser
python manage.py runserver
```

`http://localhost:8000/admin/` から部門マスタや提案レコードを GUI で操作できます。

## 2. フロントエンド（Vue 3 + Vite）

### 2.1 必要条件

Vite 7 系は **Node.js 20.19 以上**（もしくは 22.12 以上）が必須です。  
現状 Node 18 でも `npm run dev` は動作しますが、`npm run build` は失敗します。ビルドを行う場合は Node をアップデートしてください。

### 2.2 セットアップ

```bash
cd frontend
cp .env.example .env    # API の URL を必要に応じて変更
npm install
npm run dev             # http://localhost:5173
```

画面上では

- 提案登録フォーム
- ステージ/ステータスで絞り込める一覧
- 各ステージの承認入力フォーム（課長/部長段階では 3 つの採点項目付き）

を利用できます。API ベース URL を変更したい場合は `.env` の `VITE_API_BASE` を編集してください。

## 3. 補足

- CORS 設定は `http://localhost:5173` を許可済みです。別ホストでフロントを動かす場合は `backend/kaizen_backend/settings.py` の `CORS_ALLOWED_ORIGINS` を編集してください。
- SQLite を同梱しています。MySQL/PostgreSQL などへ変更する際は `DATABASES` 設定を差し替えてください。
- 既存の Streamlit 実装（`kaizenteian.py` など）は残してあります。必要に応じて削除/連携してください。

以上で Django + Vue 構成の改善提案アプリを起動できます。質問や追加要望があればお知らせください。
# kaizen_pp
