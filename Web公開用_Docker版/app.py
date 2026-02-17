import os
import sys
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from google.cloud import firestore

if getattr(sys, 'frozen', False):
    # .exeの場合: 同じフォルダにある 'dist' フォルダを探す
    base_dir = os.path.dirname(sys.executable)
    dist_folder = os.path.join(base_dir, 'dist')
else:
    # 開発中の場合: 親フォルダの frontend/dist を探す
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_folder = os.path.abspath(os.path.join(base_dir, '..', 'frontend', 'dist'))

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
        return "エラー: dist/index.html が見つかりません。", 404

@app.route('/<path:path>')
def catch_all(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    print(f"Frontend folder: {dist_folder}")
    app.run(debug=True, port=5000)