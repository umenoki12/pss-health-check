# 変更点1: サポート中の新しいPython 3.11 にアップデート
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコンテナ内にコピー
COPY requirements.txt .
COPY app.py .
COPY agent-key.json .
COPY dist ./dist

# ライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# ポート5000を開放
EXPOSE 5000

# 変更点2: 開発用(python app.py)ではなく、本番用(Gunicorn)で起動する
# app:app は「app.py の中にある app というFlaskインスタンスを動かす」という意味です
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]