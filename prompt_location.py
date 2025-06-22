import os
import requests
import json
from dotenv import load_dotenv
import database # database.py をインポート

load_dotenv()
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

def push_to_line(user_id, messages):
    """LINE Messaging APIを通じてプッシュメッセージを送信する関数"""
    headers = {"Content-Type": "application/json; charset=UTF-8", "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    body = {"to": user_id, "messages": messages}
    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(body, ensure_ascii=False).encode('utf-8'))
        response.raise_for_status()
        print(f"ユーザー({user_id})への通知が成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"ユーザー({user_id})へのLINE通知エラー: {e}")
        if e.response: print(f"応答内容: {e.response.text}")

def prompt_unregistered_users_for_location():
    print("地点未登録ユーザーへのメッセージ送信を開始します...")
    database.init_db() # データベース接続を初期化

    # 地点未登録のユーザーIDリストを取得
    unregistered_user_ids = database.get_users_without_location()

    if not unregistered_user_ids:
        print("地点未登録のユーザーは見つかりませんでした。")
        return

    message_content = {
        "type": "text",
        "text": "毎日の天気予報を通知するために、地点の再登録をお願いします。\n通知を受け取りたい地名（例: 大阪市, 新宿区）をメッセージで送ってください。"
    }

    for user_id in unregistered_user_ids:
        print(f"ユーザー({user_id})に地点登録を促すメッセージを送信中...")
        push_to_line(user_id, [message_content])
        # 必要であれば、ユーザーの状態を 'waiting_for_location' に設定することもできますが、
        # アプリケーションのメッセージハンドリングが地名入力を常に処理できるなら不要です。
        # database.set_user_state(user_id, 'waiting_for_location')


    print("地点未登録ユーザーへのメッセージ送信が完了しました。")

if __name__ == "__main__":
    if not CHANNEL_ACCESS_TOKEN:
        print("エラー: .envファイルにLINE_CHANNEL_ACCESS_TOKENが設定されていません。")
    else:
        prompt_unregistered_users_for_location()