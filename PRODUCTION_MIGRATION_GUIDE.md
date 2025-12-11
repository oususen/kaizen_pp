# 改善提案システム - 本番PC完全移行マニュアル

開発PCから本番PCへのアプリケーション完全移行手順書

---

## 目次
1. [前提条件](#前提条件)
2. [移行の全体フロー](#移行の全体フロー)
3. [ステップ1: 開発PCでの準備](#ステップ1-開発pcでの準備)
4. [ステップ2: 本番PCでの環境構築](#ステップ2-本番pcでの環境構築)
5. [ステップ3: データベースの移行](#ステップ3-データベースの移行)
6. [ステップ4: メディアファイルの移行](#ステップ4-メディアファイルの移行)
7. [ステップ5: 本番環境の起動と確認](#ステップ5-本番環境の起動と確認)
8. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

### 本番PCの要件
- **Docker Desktop** がインストール済み
- **Git** がインストール済み（オプション、ソースコード取得用）
- **ポート** 8503（フロントエンド）, 8083（バックエンド）が利用可能
- **ディスク容量**: 最低5GB以上の空き容量

### 開発PCの状況
- kaizen_dbデータベースにデータが存在
- mediaフォルダに画像などのファイルが存在（提案書の添付ファイルなど）
- IPアドレス: **10.0.1.194**

### 本番PCの状況
- IPアドレス: **10.0.1.232**
- **既存のDocker環境が稼働中**
  - Docker MySQL稼働中（既存アプリと共有）
  - Adminer稼働中：ポート **8082**
  - kaizen_dbデータベース作成済み＆データ移行済み

### 必要な情報
- 開発PCのMySQLパスワード
- **本番PCの既存MySQLのrootパスワード**（既存Dockerコンテナのパスワード）

---

## 移行の全体フロー

```
[開発PC]                          [本番PC]
   │                                 │
   ├─ 1. データエクスポート           │
   │   ├─ kaizen_db → SQLファイル    │
   │   └─ media/ → zipファイル       │
   │                                 │
   ├─ 2. ファイル転送 ────────────→  │
   │                                 │
   │                            ├─ 3. 環境構築
   │                            │   ├─ Gitクローン or ZIP展開
   │                            │   └─ .env設定
   │                                 │
   │                            ├─ 4. Dockerコンテナ起動
   │                                 │
   │                            ├─ 5. データインポート
   │                            │   ├─ kaizen_db
   │                            │   └─ media/
   │                                 │
   │                            ├─ 6. 動作確認
   │                                 │
   │                            └─ 完了！
```

---

## ステップ1: 開発PCでの準備

### 1-1. データベースのエクスポート

開発PCのkaizen_dbをSQLファイルにエクスポートします。

```bash
# コマンドプロンプトまたはPowerShellで実行
cd d:\kaizen_pp

# パスワードを入力するプロンプトが表示されます
mysqldump -h 127.0.0.1 -P 3306 -u root -p kaizen_db > kaizen_db_backup.sql
```

**確認**:
```bash
# Windowsの場合
powershell -Command "Get-Item kaizen_db_backup.sql | Select-Object Name, Length"
```

ファイルサイズが0より大きければOKです。

### 1-2. メディアファイルの圧縮（画像などがある場合）

```bash
cd d:\kaizen_pp

# Windowsの場合: 7-Zipまたは標準機能で圧縮
# PowerShellで圧縮する場合
powershell -Command "Compress-Archive -Path media -DestinationPath media_backup.zip -Force"
```

**確認**:
```bash
powershell -Command "Get-Item media_backup.zip"
```

### 1-3. 必要なファイルリスト

以下のファイル/フォルダを本番PCに転送する必要があります：

**必須ファイル**:
- `kaizen_db_backup.sql` - データベースバックアップ
- `media_backup.zip` または `media/` フォルダ - 画像などのメディアファイル

**オプション（Gitを使わない場合）**:
- `backend/` フォルダ - Djangoバックエンドコード
- `frontend/` フォルダ - Vue.jsフロントエンドコード
- `docker-compose.prod.yml` - Docker設定ファイル
- `.env.example` - 環境変数のテンプレート
- `requirements.txt` - Pythonパッケージリスト

---

## ステップ2: 本番PCでの環境構築

### 2-1. 方法A: Gitでソースコードを取得（推奨）

```bash
# 本番PCで実行
cd C:\
git clone https://github.com/oususen/kaizen_pp.git
cd kaizen_pp
```

### 2-2. 方法B: ZIPファイルで転送（Gitがない場合）

1. 開発PCでプロジェクト全体をZIP圧縮
2. 本番PCに転送（USBメモリ、ネットワーク共有など）
3. 本番PCで展開

```bash
# 例: C:\kaizen_pp に展開
cd C:\kaizen_pp
```

### 2-3. 環境変数ファイル（.env）の作成

```bash
# 本番PCで実行
cd C:\kaizen_pp

# .env.exampleをコピーして.envを作成
copy .env.example .env

# メモ帳などで.envを編集
notepad .env
```

**`.env`ファイルの内容**（本番PC用 - 既存MySQLに接続）:
```env
# 本番環境用設定（既存MySQLコンテナに接続）
PRIMARY_DB_HOST=mysql
PRIMARY_DB_PORT=3306
PRIMARY_DB_USER=root
PRIMARY_DB_PASSWORD=既存MySQLのrootパスワード  # ← 既存DockerのMySQLパスワードを入力
PRIMARY_DB_NAME=kaizen_db
```

**重要**:
- `PRIMARY_DB_HOST=mysql` は既存のMySQLコンテナ名です
- `PRIMARY_DB_PASSWORD` は既存のDocker MySQLのrootパスワードを入力してください
- 本番PCでは独自のMySQLコンテナは起動しません（既存のものを共有使用）

---

## ステップ3: データベースの移行（既に完了している場合はスキップ）

**注意**: 本番PCでは既に以下が完了しています：
- ✅ kaizen_dbデータベース作成済み
- ✅ データ移行済み

この場合は、このステップはスキップして[ステップ4](#ステップ4-メディアファイルの移行)に進んでください。

---

### データ移行がまだの場合の手順

### 3-1. 既存MySQLへの接続確認

本番PCの既存Adminer（ポート8082）にアクセスして確認:

```
http://10.0.1.232:8082
```

ログイン情報:
- サーバー: `mysql`
- ユーザー名: `root`
- パスワード: 既存MySQLのrootパスワード
- データベース: `kaizen_db`

### 3-2. データベースの作成（まだ作成していない場合）

Adminer（http://10.0.1.232:8082）で:
1. 「データベースを作成する」をクリック
2. データベース名: `kaizen_db`
3. 照合順序: `utf8mb4_unicode_ci`
4. 保存

### 3-3. データのインポート

既存MySQLコンテナにデータをインポート:

```bash
# 本番PCで実行
cd C:\kaizen_pp

# 既存MySQLコンテナ名を確認
docker ps | findstr mysql

# 既存MySQLコンテナにインポート（コンテナ名を適宜変更）
docker exec -i <既存MySQLコンテナ名> mysql -u root -p<既存MySQLパスワード> kaizen_db < kaizen_db_backup.sql
```

または、Adminer（http://10.0.1.232:8082）の「インポート」機能を使用。

---

## ステップ4: メディアファイルの移行

### 4-1. メディアファイルの転送と展開

```bash
# 本番PCで実行
cd C:\kaizen_pp

# ZIPファイルを展開（PowerShell）
powershell -Command "Expand-Archive -Path media_backup.zip -DestinationPath . -Force"
```

または、開発PCの `media/` フォルダを直接コピーして `C:\kaizen_pp\media\` に配置。

**確認**:
```bash
# mediaフォルダの存在確認
powershell -Command "Test-Path media"
# True が返ればOK

# ファイル数確認
powershell -Command "(Get-ChildItem -Path media -Recurse -File | Measure-Object).Count"
```

---

## ステップ5: 本番環境の起動と確認

### 5-1. すべてのDockerコンテナを起動

```bash
# 本番PCで実行
cd C:\kaizen_pp

# すべてのコンテナをビルド&起動
docker-compose -f docker-compose.prod.yml up -d --build
```

**ビルド時間**: 初回は5〜10分程度かかる場合があります。

### 5-2. コンテナの起動確認

```bash
docker-compose -f docker-compose.prod.yml ps
```

以下の3つのコンテナがすべて `Up` になっていればOK:
- `kaizen_mysql_prod`
- `kaizen_backend_prod`
- `kaizen_frontend_prod`

### 5-3. ログの確認

```bash
# すべてのログを確認
docker-compose -f docker-compose.prod.yml logs -f

# 特定のサービスのみ確認
docker-compose -f docker-compose.prod.yml logs -f backend
```

エラーがないか確認してください。`Ctrl + C` でログ表示を終了。

### 5-4. 動作確認

ブラウザで以下のURLにアクセス:

**本番PC上でアクセス:**
1. **フロントエンド**: http://localhost:8503
2. **バックエンドAPI**: http://localhost:8083/api/
3. **Adminer**: http://localhost:8082（既存のAdminer）

**開発PCから本番PCにアクセス:**
1. **フロントエンド**: http://10.0.1.232:8503
   - 改善提案システムのトップページが表示される
   - ログイン画面が表示される
2. **バックエンドAPI**: http://10.0.1.232:8083/api/
   - APIのエンドポイント一覧が表示される
3. **Adminer**: http://10.0.1.232:8082（既存のAdminer）
   - MySQLの管理画面が表示される

### 5-5. ログイン確認

開発PCで使用していたユーザーアカウントでログインできるか確認:

1. 本番PCで: http://localhost:8503
   または開発PCから: http://10.0.1.232:8503
2. ユーザー名とパスワードを入力してログイン
3. 提案一覧などのデータが正しく表示されるか確認

### 5-6. データ表示確認

- 提案一覧が表示されるか
- 部門情報が正しく表示されるか
- 添付画像が表示されるか
- 検索機能が動作するか
- 新規提案の作成ができるか

---

## 本番PC用の管理タスク

### 定期バックアップの設定

```bash
# 週次バックアップスクリプト（例: 毎週日曜日に手動実行）
cd C:\kaizen_pp\backups
docker exec kaizen_mysql_prod mysqldump -u root -p${MYSQL_ROOT_PASSWORD} kaizen_db > backup_%date:~0,4%%date:~5,2%%date:~8,2%.sql
```

### コンテナの停止と再起動

```bash
# 停止
docker-compose -f docker-compose.prod.yml down

# 再起動
docker-compose -f docker-compose.prod.yml up -d

# 特定サービスのみ再起動
docker-compose -f docker-compose.prod.yml restart backend
```

### ログの確認

```bash
# リアルタイムログ
docker-compose -f docker-compose.prod.yml logs -f

# 過去100行のログ
docker-compose -f docker-compose.prod.yml logs --tail=100

# 特定サービスのログ
docker-compose -f docker-compose.prod.yml logs -f mysql
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
```

### システムリソースの確認

```bash
# コンテナのCPU/メモリ使用状況
docker stats

# ディスク使用状況
docker system df
```

---

## トラブルシューティング

### エラー: Port 3306 already in use

**原因**: 本番PCで既にMySQLが起動している

**解決方法**:
1. 既存のMySQLを停止
2. または、`docker-compose.prod.yml` のポートを変更（例: `3307:3306`）

### エラー: Access denied for user 'root'

**原因**: `.env` のパスワードが間違っている

**解決方法**:
1. `.env` の `MYSQL_ROOT_PASSWORD` と `PRIMARY_DB_PASSWORD` を確認
2. 両方が同じ値になっているか確認
3. コンテナを再起動: `docker-compose -f docker-compose.prod.yml restart`

### エラー: 画像が表示されない

**原因**: `media/` フォルダが正しく配置されていない

**解決方法**:
```bash
# mediaフォルダの存在確認
powershell -Command "Test-Path C:\kaizen_pp\media"

# パーミッション確認（Linuxの場合）
ls -la media/

# コンテナ再起動
docker-compose -f docker-compose.prod.yml restart backend
```

### エラー: フロントエンドが表示されない

**原因**: フロントエンドのビルドが失敗している

**解決方法**:
```bash
# フロントエンドのログ確認
docker-compose -f docker-compose.prod.yml logs frontend

# 再ビルド
docker-compose -f docker-compose.prod.yml up -d --build frontend
```

### エラー: APIがつながらない (502 Bad Gateway)

**原因**: バックエンドが起動していない

**解決方法**:
```bash
# バックエンドのログ確認
docker-compose -f docker-compose.prod.yml logs backend

# マイグレーションの実行
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# バックエンド再起動
docker-compose -f docker-compose.prod.yml restart backend
```

### コンテナが起動しない

```bash
# すべてのコンテナを停止
docker-compose -f docker-compose.prod.yml down

# ボリュームを削除して再作成（注意: データが消えます）
docker-compose -f docker-compose.prod.yml down -v

# 再度起動
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## セキュリティチェックリスト

- [ ] `.env` ファイルに強力なパスワードを設定した
- [ ] `.env` ファイルはGitにコミットされていない
- [ ] 本番PCのファイアウォールが有効
- [ ] 不要なポートが外部に公開されていない
- [ ] 定期バックアップの運用計画がある
- [ ] 管理者アカウントのパスワードが強力

---

## ネットワークアクセス設定（オプション）

本番PCに他のPCからアクセスしたい場合:

### Windowsファイアウォールの設定

本番PC（10.0.1.232）で他のPCからアクセスを許可する場合:

1. Windows Defender ファイアウォールを開く
2. 「詳細設定」をクリック
3. 「受信の規則」→「新しい規則」
4. ポート 8503（フロントエンド）, 8083（バックエンド）を許可
   - ポート8082（Adminer）は既存アプリで既に許可済みの想定

### 他のPCからアクセス

**本番PCへのアクセス（IPアドレス: 10.0.1.232）:**

- フロントエンド: http://10.0.1.232:8503
- バックエンドAPI: http://10.0.1.232:8083/api/
- Adminer: http://10.0.1.232:8082（既存）

**開発PCへのアクセス（IPアドレス: 10.0.1.194）:**

- フロントエンド: http://10.0.1.194:8503
- バックエンドAPI: http://10.0.1.194:8083/api/
- Adminer: 開発PC環境に応じて設定

---

## 完了チェックリスト

移行が完了したら、以下を確認してください:

- [ ] すべてのDockerコンテナが起動している（`docker-compose ps`）
- [ ] http://localhost でフロントエンドが表示される
- [ ] ログインができる
- [ ] 提案一覧が表示される（データ件数が開発PCと同じ）
- [ ] 画像が正しく表示される
- [ ] 新規提案の作成ができる
- [ ] 検索機能が動作する
- [ ] バックアップファイルが保存されている

---

## サポート情報

問題が解決しない場合:

1. ログファイルを確認: `docker-compose -f docker-compose.prod.yml logs`
2. [DEPLOYMENT.md](DEPLOYMENT.md) の詳細手順を参照
3. [DATABASE_MIGRATION_GUIDE.md](DATABASE_MIGRATION_GUIDE.md) のデータベース移行手順を参照
4. GitHubリポジトリのIssuesで質問: https://github.com/oususen/kaizen_pp/issues

---

## 付録: よく使うコマンド集

### Docker関連

```bash
# コンテナ一覧
docker-compose -f docker-compose.prod.yml ps

# 起動
docker-compose -f docker-compose.prod.yml up -d

# 停止
docker-compose -f docker-compose.prod.yml down

# 再起動
docker-compose -f docker-compose.prod.yml restart

# ログ
docker-compose -f docker-compose.prod.yml logs -f

# コンテナに入る
docker-compose -f docker-compose.prod.yml exec backend bash
docker-compose -f docker-compose.prod.yml exec mysql bash
```

### Django管理コマンド

```bash
# マイグレーション
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 管理者ユーザー作成
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# 静的ファイル収集
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### データベース関連

```bash
# MySQLに接続
docker-compose -f docker-compose.prod.yml exec mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} kaizen_db

# バックアップ
docker exec kaizen_mysql_prod mysqldump -u root -p${MYSQL_ROOT_PASSWORD} kaizen_db > backup.sql

# リストア
docker exec -i kaizen_mysql_prod mysql -u root -p${MYSQL_ROOT_PASSWORD} kaizen_db < backup.sql
```

---

## 移行完了後の開発PCについて

本番PCへの移行が完了し、正常に動作確認できたら:

1. **開発PCは開発環境として継続使用可能**
   - 開発PCのデータはそのまま残しておく
   - 新機能の開発やテストに使用

2. **開発PCのバックアップを保持**
   - `kaizen_db_backup.sql` を安全な場所に保管
   - 念のため複数世代のバックアップを保持

3. **今後の運用**
   - 本番PC: 実運用環境
   - 開発PC: 開発・テスト環境
   - データの同期が必要な場合は、定期的にバックアップ&リストア

---

**移行作業、お疲れさまでした！**
