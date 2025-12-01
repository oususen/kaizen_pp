# 改善提案システム - 本番環境デプロイ手順

## 前提条件

- Docker & Docker Compose がインストール済み
- Git がインストール済み
- ポート 80, 3306, 8000 が利用可能

## 本番PCでの初回セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/oususen/kaizen_pp.git
cd kaizen_pp
```

### 2. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集
nano .env
```

`.env`の内容:
```env
# Docker用 MySQL設定
MYSQL_ROOT_PASSWORD=your_secure_password_here
MYSQL_PASSWORD=kaizen_user_password

# アプリケーション用設定
PRIMARY_DB_HOST=mysql
PRIMARY_DB_PORT=3306
PRIMARY_DB_USER=root
PRIMARY_DB_PASSWORD=your_secure_password_here
PRIMARY_DB_NAME=kaizen_db
```

### 3. データベースのインポート（既存データがある場合）

```bash
# SQLダンプファイルを配置
mkdir -p mysql_init
cp /path/to/kaizen_db_backup.sql mysql_init/01-init.sql
```

### 4. 本番環境の起動

```bash
# 本番環境としてビルド&起動
docker-compose -f docker-compose.prod.yml up -d --build
```

### 5. ログの確認

```bash
# 全コンテナのログ
docker-compose -f docker-compose.prod.yml logs -f

# 特定サービスのログ
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f mysql
```

### 6. 動作確認

- フロントエンド: http://localhost
- バックエンドAPI: http://localhost:8000/api/

### 7. 管理者ユーザーの作成（必要な場合）

```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

## 更新手順

### コードの更新

```bash
# 最新コードを取得
git pull origin main

# コンテナを再ビルド&再起動
docker-compose -f docker-compose.prod.yml up -d --build

# 不要なイメージを削除
docker image prune -f
```

### データベースマイグレーション

```bash
# マイグレーション実行
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# マイグレーション状態確認
docker-compose -f docker-compose.prod.yml exec backend python manage.py showmigrations
```

## トラブルシューティング

### データベース接続エラー

```bash
# MySQLコンテナの状態確認
docker-compose -f docker-compose.prod.yml ps mysql

# MySQLに直接接続して確認
docker-compose -f docker-compose.prod.yml exec mysql mysql -u root -p kaizen_db
```

### 静的ファイルが表示されない

```bash
# 静的ファイルを再収集
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput --clear
```

### コンテナの再起動

```bash
# 全サービス再起動
docker-compose -f docker-compose.prod.yml restart

# 特定サービスのみ再起動
docker-compose -f docker-compose.prod.yml restart backend
```

### コンテナの停止と削除

```bash
# 停止
docker-compose -f docker-compose.prod.yml down

# 停止してボリュームも削除（注意：データベースのデータも削除されます）
docker-compose -f docker-compose.prod.yml down -v
```

## バックアップ

### データベースのバックアップ

```bash
# バックアップ作成
docker-compose -f docker-compose.prod.yml exec mysql mysqldump -u root -p kaizen_db > backup_$(date +%Y%m%d_%H%M%S).sql

# または
docker-compose -f docker-compose.prod.yml exec -T mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} kaizen_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### メディアファイルのバックアップ

```bash
# mediaディレクトリをtar.gzで圧縮
tar -czf media_backup_$(date +%Y%m%d_%H%M%S).tar.gz media/
```

## パフォーマンス監視

```bash
# コンテナのリソース使用状況
docker stats

# ログのサイズ確認
docker-compose -f docker-compose.prod.yml logs --tail=100 backend | wc -l
```

## セキュリティ

- `.env`ファイルは**絶対にGitにコミットしない**
- `MYSQL_ROOT_PASSWORD`は強力なパスワードに設定
- 本番環境では`DJANGO_DEBUG=False`に設定（docker-compose.prod.ymlで既に設定済み）
- 必要に応じてファイアウォールでポート制限

## 開発環境（オプション）

開発環境で動かす場合:

```bash
docker-compose up -d --build
```

開発環境では:
- フロントエンド: http://localhost:5173 (ホットリロード有効)
- バックエンド: http://localhost:8000 (自動リロード有効)
