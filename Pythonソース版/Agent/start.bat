@echo off
echo PSS Agent を起動します...
echo 必要なライブラリを確認中...
pip install -r requirements.txt
cls
echo 監視を開始します (Ctrl+C で停止)
python agent.py
pause