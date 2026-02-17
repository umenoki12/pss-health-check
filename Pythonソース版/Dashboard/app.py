import os
import sys
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from google.cloud import firestore

# --- 1. distフォルダの場所を賢く探す設定 ---
if getattr(sys, 'frozen', False):
    # .exeの場合
    base_dir = os.path.dirname(sys.executable)
    dist_folder = os.path.join(base_dir, 'dist')
else:
    # Pythonスクリプトとして実行する場合
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # まず、同じフォルダに 'dist' があるか確認 (配布用パッケージ/Docker用)
    local_dist = os.path.join(base_dir, 'dist')
    # なければ、開発環境用のパス (../frontend/dist) を確認
    dev_dist = os.path.abspath(os.path.join(base_dir, '..', 'frontend', 'dist'))
    
    if os.path.exists(local_dist):
        dist_folder = local_dist
    else:
        dist_folder = dev_dist

# キーファイルのパス設定
key_path = os.path.join(base_dir, 'agent-key.json')

if not os.path.exists(key_path):
    print(f"エラー: {key_path} が見つかりません。")
    # Dockerなどでログが見えるように強制終了せず進める場合もありますが、
    # DBがないと動かないのでexitします
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
                # datetime型を文字列に変換
                data['last_seen'] = data['last_seen'].isoformat()
            results.append(data)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 削除用API
@app.route('/api/computers/<pc_id>', methods=['DELETE'])
def delete_computer(pc_id):
    try:
        # 指定されたIDのドキュメントをFirestoreから削除
        db.collection('computers').document(pc_id).delete()
        return jsonify({"message": f"{pc_id} deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def serve():
    if os.path.exists(os.path.join(app.static_folder, 'index.html')):
        return send_from_directory(app.static_folder, 'index.html')
    else:
        return f"エラー: {dist_folder} に index.html が見つかりません。<br>現在の参照パス: {dist_folder}", 404

@app.route('/<path:path>')
def catch_all(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    print(f"Frontend folder: {dist_folder}")
    # --- 2. サーバー公開用に host='0.0.0.0' を追加 ---
    app.run(debug=True, host='0.0.0.0', port=5000)