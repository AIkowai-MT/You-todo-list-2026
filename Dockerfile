FROM python:3.11-slim

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# RenderはPORT環境変数を自動設定するが、デフォルト値も用意
ENV PORT=8000

# Gunicornでサーバー起動
CMD gunicorn server:app --bind 0.0.0.0:$PORT
