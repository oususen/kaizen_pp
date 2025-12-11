# kaizen_db データベース移行手順

開発PCから本番PC（Docker環境）へのデータベース移行手順

## 前提条件
- 開発PCにmysqldumpがインストール済み
- 本番PCでDocker環境が稼働中（または起動可能）
- 開発PCから本番PCのAdminerにアクセス可能

---

## 準備: 本番PCのMySQLにkaizen_dbデータベースを作成

本番PCのDocker MySQLにまだkaizen_dbが存在しない場合は、まず作成する必要があります。

### 方法A: Adminerで作成（GUI）

1. **Adminerにアクセス**
   - 開発PCから本番PCのAdminerにアクセス
   - 例: `http://<本番PCのIP>:8080` または `http://localhost:8080`（本番PCで直接アクセスする場合）

2. **ログイン**
   - サーバー: `mysql` または `localhost`
   - ユーザー名: `root`
   - パスワード: `.env`ファイルの`MYSQL_ROOT_PASSWORD`の値
   - データベース: 空欄のまま（または選択しない）
   - 「ログイン」ボタンをクリック

3. **データベースを作成**
   - ログイン後、上部メニューの「データベースを作成する」または「Create database」をクリック
   - データベース名: `kaizen_db` と入力
   - 照合順序: `utf8mb4_unicode_ci` を選択（推奨）
   - 「保存」または「Save」ボタンをクリック

4. **作成確認**
   - 左サイドバーに `kaizen_db` が表示されることを確認

### 方法B: コマンドラインで作成

```bash
# 本番PCで実行
docker-compose -f docker-compose.prod.yml exec mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "CREATE DATABASE IF NOT EXISTS kaizen_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 確認
docker-compose -f docker-compose.prod.yml exec mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SHOW DATABASES;"
```

---

## 方法1: SQLダンプファイルを使用（推奨）

### ステップ1: 開発PCでデータをエクスポート

```bash
# 開発PCで実行
# パスワードを入力するプロンプトが表示されます
mysqldump -h 127.0.0.1 -P 3306 -u root -p kaizen_db > kaizen_db_backup.sql

# または、パスワードを直接指定（パスワードが空の場合は不要）
mysqldump -h 127.0.0.1 -P 3306 -u root kaizen_db > kaizen_db_backup.sql
```

バックアップファイルが作成されたことを確認：
```bash
dir kaizen_db_backup.sql
```

### ステップ2: バックアップファイルを本番PCに転送

開発PCと本番PCが同じネットワーク内にある場合：
- ネットワーク共有
- USBメモリ
- リモートデスクトップでコピー
などの方法でファイルを転送

### ステップ3: 本番PCでDockerコンテナを起動

```bash
# 本番PCで実行
cd kaizen_pp
docker-compose -f docker-compose.prod.yml up -d
```

### ステップ4: 本番PCのDockerコンテナにインポート

```bash
# 本番PCで実行
# kaizen_db_backup.sqlファイルがあるディレクトリで実行

# 方法A: docker cpとmysqlコマンドを使用
docker cp kaizen_db_backup.sql kaizen_mysql_prod:/tmp/kaizen_db_backup.sql
docker exec -i kaizen_mysql_prod mysql -u root -p${MYSQL_ROOT_PASSWORD} kaizen_db < /tmp/kaizen_db_backup.sql

# 方法B: パイプを使用（より簡単）
docker exec -i kaizen_mysql_prod mysql -u root -p${MYSQL_ROOT_PASSWORD} kaizen_db < kaizen_db_backup.sql
```

### ステップ5: インポート確認

```bash
# 本番PCで実行
docker-compose -f docker-compose.prod.yml exec mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} kaizen_db

# MySQLコンソールで以下を実行
SHOW TABLES;
SELECT COUNT(*) FROM proposals;  # データが入っているか確認
SELECT COUNT(*) FROM users;       # ユーザーデータの確認
exit
```

---

## 方法2: Adminerを使用（小規模データベース向け）

### ステップ1: 開発PCのAdminerでエクスポート

1. 開発PCのAdminerにアクセス（例: http://localhost:8080）
2. ログイン（サーバー: 127.0.0.1, ユーザー: root, データベース: kaizen_db）
3. 左メニューで「kaizen_db」を選択
4. 上部メニューの「エクスポート」をクリック
5. 出力形式: SQL
6. データベース: kaizen_db を選択
7. 「エクスポート」ボタンをクリックしてファイルをダウンロード

### ステップ2: 本番PCのAdminerでインポート

1. 本番PCのAdminerにアクセス（例: http://本番PCのIP:8080）
   - または、開発PCから本番PCのAdminerにアクセス
2. ログイン（サーバー: localhost または mysql, ユーザー: root）
3. 左メニューで「kaizen_db」を選択
4. 上部メニューの「インポート」をクリック
5. ファイルを選択ボタンでダウンロードしたSQLファイルを選択
6. 「実行」ボタンをクリック

**注意**: 大きなデータベースの場合、PHPのアップロードサイズ制限により失敗する可能性があります。その場合は方法1を使用してください。

---

## 方法3: ネットワーク越しに直接移行（開発PCから本番PCのMySQLに直接アクセス可能な場合）

### 前提条件
- 本番PCのMySQLポート3306が開発PCからアクセス可能
- 本番PCのDocker MySQLコンテナが起動中

### 手順

```bash
# 開発PCで実行
# 開発PCからエクスポートして本番PCに直接インポート
mysqldump -h 127.0.0.1 -u root -p kaizen_db | mysql -h <本番PCのIP> -P 3306 -u root -p kaizen_db

# または、2ステップに分ける
mysqldump -h 127.0.0.1 -u root -p kaizen_db > kaizen_db_backup.sql
mysql -h <本番PCのIP> -P 3306 -u root -p kaizen_db < kaizen_db_backup.sql
```

---

## トラブルシューティング

### エラー: Access denied for user 'root'

**原因**: パスワードが正しくない

**解決方法**:
- `.env`ファイルの`MYSQL_ROOT_PASSWORD`を確認
- `-p`オプションでパスワードを入力

### エラー: Got packet bigger than 'max_allowed_packet'

**原因**: MySQLのパケットサイズ制限

**解決方法**:
```bash
# 本番PCのDockerコンテナで実行
docker exec -i kaizen_mysql_prod mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SET GLOBAL max_allowed_packet=1073741824;"
```

### インポート後にバックエンドが起動しない

**原因**: データベースマイグレーションの不一致

**解決方法**:
```bash
# 本番PCで実行
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
docker-compose -f docker-compose.prod.yml restart backend
```

### テーブルが見つからない

**原因**: データベースが空の状態でインポートされなかった

**解決方法**:
1. SQLダンプファイルの中身を確認（`CREATE TABLE`文があるか）
2. インポートコマンドを再実行
3. エラーメッセージを確認

---

## バックアップのベストプラクティス

### 定期バックアップスクリプト

```bash
# 本番PCで実行（週次バックアップなど）
docker exec kaizen_mysql_prod mysqldump -u root -p${MYSQL_ROOT_PASSWORD} kaizen_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### バックアップの保存場所
- 別のドライブやNASに保存
- クラウドストレージ（Google Drive、OneDriveなど）
- 少なくとも3世代分のバックアップを保持

---

## 補足: 本番PC Dockerコンテナの管理

### Dockerコンテナの状態確認
```bash
docker-compose -f docker-compose.prod.yml ps
```

### ログの確認
```bash
docker-compose -f docker-compose.prod.yml logs -f mysql
```

### MySQLコンテナに直接接続
```bash
docker-compose -f docker-compose.prod.yml exec mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} kaizen_db
```
