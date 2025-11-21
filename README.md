# 改善提案ワークフロー（Django + Vue3）

改善提案の登録・レビュー・承認を行うシステムです。バックエンドは Django REST + MySQL、フロントは Vite + Vue3 で動作します。ERP_jp と同じ JWT ログイン/リフレッシュ API 互換を持たせています。

## ディレクトリ構成

- `backend/` : Django プロジェクト（kaizen_backend）とアプリ `proposals`
- `frontend/` : Vue3 (Vite) SPA
- `proposal_images/` : 登録済み提案の画像置き場
- `requirements.txt` : Python 依存
- `frontend/.env` : API ベースURL（既定 `/api`、Vite 開発サーバで `/api` を 8001 にプロキシ）

## バックエンドの起動（API）

前提: Python 3.10+ / MySQL。
ルートディレクトリに `.env` ファイルを作成し、以下の環境変数を設定してください（`config.py` がこれを読み込みます）。

```ini
PRIMARY_DB_HOST=localhost
PRIMARY_DB_PORT=3306
PRIMARY_DB_USER=root
PRIMARY_DB_PASSWORD=your_password
PRIMARY_DB_NAME=kaizen_db
```

起動手順:

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r ..\requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8001
```

主なエンドポイント（プレフィックス `/api/`）:
- `user/get_token/` : JWT 発行（username/password）
- `user/refresh_token/` : リフレッシュ
- `user/info/` : ログインユーザ情報
- `improvement-proposals/` : 改善提案 CRUD
- `improvement-proposals/<id>/approve/` : 段階承認
- `departments/`, `employees/`, `employees/me/`

管理画面: `http://localhost:8001/admin/`（必要なら `createsuperuser` で管理者を作成）。

## フロントエンドの起動（SPA）

前提: Node.js 20+ 推奨。Vite 開発サーバはポート 5000 で起動し、`/api` へのリクエストをバックエンド（8001）にプロキシします。

```bash
cd frontend
cp .env.example .env   # 既定で /api を使用
npm install
npm run dev -- --host  # http://localhost:5000
```

ビルド: `npm run build`（`dist/` を生成）、ローカルプレビュー: `npm run preview`。

## 認証の流れ（ERP互換）

- フロントは `user/get_token/` で JWT を取得し、localStorage に保存。
- API 呼び出しは Authorization: Bearer を自動付与、401 時は `user/refresh_token/` で再取得。
- `user/info/` でプロフィールを読み込み、`/login` でログイン画面にリダイレクト。

## よくある設定ポイント

- **CORS/CSRF**: `backend/kaizen_backend/settings.py` の `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` に必要なオリジンを追加してください。
- **DB接続**: `config.py` を直接編集せず、ルートディレクトリの `.env` に `PRIMARY_DB_...` の変数を定義してください。

必要に応じて `requirements.txt` や `VITE_API_BASE` を環境に合わせて変更してください。
