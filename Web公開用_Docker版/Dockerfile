# Python 3.9 の軽量版イメージを使用
FROM python:3.9-slim

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

# 起動コマンド
CMD ["python", "app.py"]