import os
import requests
import json
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent, PostbackEvent
from datetime import datetime
from dotenv import load_dotenv
import database

# --- 初期設定 ---
load_dotenv()
app = Flask(__name__)

with app.app_context():
    database.init_db()

CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

handler = WebhookHandler(CHANNEL_SECRET)

# --- 補助関数群 ---
def get_coords_from_city(city_name):
    """地名から緯度と経度を取得する関数"""
    api_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name},JP&limit=1&appid={OPENWEATHER_API_KEY}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        if data:
            return {"lat": data[0]["lat"], "lon": data[0]["lon"]}
        return None
    except Exception as e:
        print(f"Geocoding API Error: {e}")
        return None

def send_line_message(reply_token, messages):
    """requestsを使って、LINEにメッセージを返信する関数"""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    body = {"replyToken": reply_token, "messages": messages}
    try:
        response = requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, data=json.dumps(body, ensure_ascii=False).encode('utf-8'))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"LINE返信エラー: {e}\n応答内容: {e.response.text if e.response else 'N/A'}")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(FollowEvent)
def handle_follow(event):
    reply_messages = [{"type": "text", "text": "友達追加ありがとうございます！\n下のメニューから「地点変更」をタップして、毎日の通知を受け取る地点を登録してください。"}]
    send_line_message(event.reply_token, reply_messages)

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    if event.postback.data == 'action=register_location':
        database.set_user_state(user_id, 'waiting_for_location')
        reply_messages = [{"type": "text", "text": "通知を受け取りたい地名（例: 大阪市, 近江八幡市）を教えてください。"}]
        send_line_message(event.reply_token, reply_messages)

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text
    user_state = database.get_user_state(user_id)
    
    if user_state == 'waiting_for_location':
        coords = get_coords_from_city(user_message)
        if coords:
            database.set_user_location(user_id, user_message, coords['lat'], coords['lon'])
            reply_message = {"type": "text", "text": f"地点を「{user_message}」に設定しました！"}
        else:
            reply_message = {"type": "text", "text": f"「{user_message}」が見つかりませんでした。日本の市町村名などで入力してください。"}
        send_line_message(event.reply_token, [reply_message])
    else:
        reply_message = {"type": "text", "text": "メニューの「地点変更」から、通知先を設定してください。"}
        send_line_message(event.reply_token, [reply_message])

if __name__ == "__main__":
    app.run(port=5000)
