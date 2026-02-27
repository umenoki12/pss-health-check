import os
import sys
from datetime import datetime, timezone  # ✨新規追加: サーバー側で正確な時間を記録するため
from flask import Flask, jsonify, send_from_directory, request, abort 
from flask_cors import CORS
from google.cloud import firestore

# --- 🔒 1. 各種トークンの設定（セキュア版） ---
# 管理者用（削除用）の合言葉
ADMIN_TOKEN = os.environ.get('PSS_ADMIN_TOKEN')
# ✨新規追加: エージェント（PC）からの送信用の合言葉
AGENT_TOKEN = os.environ.get('PSS_AGENT_TOKEN')

def check_admin_auth():
    """管理者の合言葉をチェックする関数"""
    token = request.headers.get('X-Admin-Token')
    if not ADMIN_TOKEN:
        abort(500, description="サーバー設定エラー: 管理者トークンが設定されていません。")
    if not token or token != ADMIN_TOKEN:
        abort(401, description="Unauthorized: 管理者認証が必要です。")

# ✨新規追加: エージェント用の合言葉をチェックする関数
def check_agent_auth():
    """エージェントからのデータ送信権限をチェックする関数"""
    token = request.headers.get('X-Agent-Token')
    if not AGENT_TOKEN:
        abort(500, description="サーバー設定エラー: エージェントトークンが設定されていません。")
    if not token or token != AGENT_TOKEN:
        abort(401, description="Unauthorized: エージェント認証が必要です。")
# ---------------------------------------------

if getattr(sys, 'frozen', False):
    # .exeの場合: 同じフォルダにある 'dist' フォルダを探す
    base_dir = os.path.dirname(sys.executable)
    dist_folder = os.path.join(base_dir, 'dist')
else:
    # スクリプト実行の場合
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. まず同じフォルダにある dist を探す (Dockerや配布パッケージ用)
    local_dist = os.path.join(base_dir, 'dist')
    # 2. なければ開発時の構造 (../frontend/dist) を探す
    dev_dist = os.path.abspath(os.path.join(base_dir, '..', 'frontend', 'dist'))
    
    if os.path.exists(local_dist):
        dist_folder = local_dist
    else:
        dist_folder = dev_dist

key_path = os.path.join(base_dir, 'agent-key.json')

if not os.path.exists(key_path):
    print(f"エラー: {key_path} が見つかりません。")
    sys.exit(1)

try:
    db = firestore.Client.from_service_account_json(key_path)
    print("Firestoreへの接続に成功しました。")
except Exception as e:
    print(f"Firestore接続エラー: {e}")
    sys.exit(1)

app = Flask(__name__, static_folder=dist_folder, static_url_path='')
CORS(app)

@app.route('/api/computers', methods=['GET'])
def get_computers():
    try:
        docs = db.collection('computers').stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            if 'last_seen' in data:
                data['last_seen'] = data['last_seen'].isoformat()
            results.append(data)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 🔒 2. 削除用APIを保護する ---
@app.route('/api/computers/<pc_id>', methods=['DELETE'])
def delete_computer(pc_id):
    check_admin_auth()
    try:
        db.collection('computers').document(pc_id).delete()
        return jsonify({"message": f"{pc_id} deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 🔒 3. データ受信用API（✨新規追加: エージェントからの通信受け口） ---

@app.route('/api/computers/<pc_id>', methods=['POST'])
def update_computer(pc_id):
    # 1. まずエージェントの合言葉をチェック（偽造データの送信を防ぐ）
    check_agent_auth()
    
    try:
        # 2. エージェントから送られてきた状態データ(JSON)を受け取る
        data = request.get_json()
        if not data:
            return jsonify({"error": "データが空です"}), 400
            
        # 3. ★ハッカー対策: 時間の偽装を防ぐため、受信した「サーバー側の現在時刻」を強制的に記録する
        data['last_seen'] = datetime.now(timezone.utc)
            
        # 4. サーバー側が責任を持ってFirestoreに書き込む
        db.collection('computers').document(pc_id).set(data, merge=True)
        
        return jsonify({"message": f"{pc_id} updated successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def serve():
    if os.path.exists(os.path.join(app.static_folder, 'index.html')):
        return send_from_directory(app.static_folder, 'index.html')
    else:
        return "エラー: dist/index.html が見つかりません。", 404

@app.route('/<path:path>')
def catch_all(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    print(f"Frontend folder: {dist_folder}")
    app.run(debug=True, host='0.0.0.0',port=5000)