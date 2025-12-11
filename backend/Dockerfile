FROM python:3.11-slim

WORKDIR /app

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージのインストール
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー（config.pyも含めるためビルドコンテキストはリポジトリルートにする）
COPY backend /app
COPY config.py /app/config.py

# 静的ファイルとメディアファイル用ディレクトリ
RUN mkdir -p /app/staticfiles /app/media

# 環境変数
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=kaizen_backend.settings
ENV PYTHONPATH=/app:$PYTHONPATH

# ポート公開
EXPOSE 8000

# 起動コマンド
CMD ["gunicorn", "kaizen_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
