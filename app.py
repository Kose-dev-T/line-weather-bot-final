import os
import requests
import json
from flask import Flask, request, abort, jsonify
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent, PostbackEvent
from datetime import datetime
from dotenv import load_dotenv
import database

# 環境変数の読み込み
load_dotenv()
app = Flask(__name__)
with app.app_context():
    database.init_db()

# 環境変数から設定を読み込み
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

handler = WebhookHandler(CHANNEL_SECRET)

# --- 天気情報取得関連の関数 ---
def get_coords_from_city(city_name):
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

def get_open_meteo_forecast_message_dict(lat, lon, city_name):
    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia%2FTokyo"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        today = data["daily"]
        date_str = datetime.strptime(today["time"][0], '%Y-%m-%d').strftime('%Y年%m月%d日')
        temp_max = today["temperature_2m_max"][0]
        temp_min = today["temperature_2m_min"][0]
        pop = today["precipitation_probability_max"][0]
        weather_codes = {0:"快晴",1:"晴れ",2:"一部曇",3:"曇り",45:"霧",48:"霧氷",51:"霧雨",53:"霧雨",55:"霧雨",56:"着氷性の霧雨",57:"着氷性の霧雨",61:"小雨",63:"雨",65:"大雨",66:"着氷性の雨",67:"着氷性の雨",71:"小雪",73:"雪",75:"大雪",77:"霧雪",80:"にわか雨",81:"にわか雨",82:"激しいにわか雨",85:"弱いしゅう雪",86:"強いしゅう雪",95:"雷雨",96:"雷雨と雹",99:"雷雨と雹"}
        weather = weather_codes.get(today["weather_code"][0], "不明")

        return {
            "type": "flex", "altText": f"{city_name}の天気予報",
            "contents": { "type": "bubble", "direction": 'ltr',
                "header": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "今日の天気予報", "weight": "bold", "size": "xl", "color": "#FFFFFF", "align": "center"}], "backgroundColor": "#5C6BC0", "paddingTop": "12px", "paddingBottom": "12px"},
                "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": [
                    {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": city_name, "size": "lg", "weight": "bold", "color": "#5C6BC0", "wrap": True}, {"type": "text", "text": date_str, "size": "sm", "color": "#AAAAAA"}]},
                    {"type": "separator", "margin": "md"},
                    {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [
                        {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "天気", "color": "#AAAAAA", "size": "sm", "flex": 2}, {"type": "text", "text": weather, "wrap": True, "color": "#666666", "size": "sm", "flex": 5}]},
                        {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "最高気温", "color": "#AAAAAA", "size": "sm", "flex": 2}, {"type": "text", "text": f"{temp_max}°C", "wrap": True, "color": "#666666", "size": "sm", "flex": 5}]},
                        {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "最低気温", "color": "#AAAAAA", "size": "sm", "flex": 2}, {"type": "text", "text": f"{temp_min}°C", "wrap": True, "color": "#666666", "size": "sm", "flex": 5}]},
                        {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "降水確率", "color": "#AAAAAA", "size": "sm", "flex": 2}, {"type": "text", "text": f"{pop}%", "wrap": True, "color": "#666666", "size": "sm", "flex": 5}]}
                    ]}
                ]}
            }
        }
    except Exception as e:
        print(f"Open-Meteo API Error: {e}")
        return {"type": "text", "text": "天気情報の取得に失敗しました。"}

# --- LINE Messaging APIとの通信を行う関数 ---
def send_line_message(token, messages, is_push=False, user_id=None):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    if is_push:
        url, body = "https://api.line.me/v2/bot/message/push", {"to": user_id, "messages": messages}
    else:
        url, body = "https://api.line.me/v2/bot/message/reply", {"replyToken": token, "messages": messages}
    
    try:
        encoded_body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        response = requests.post(url, headers=headers, data=encoded_body)
        print(f"LINE API Response Status: {response.status_code}")
        response.raise_for_status()
        print("LINEメッセージの送信に成功しました。")

    except requests.exceptions.RequestException as e:
        print("--- LINE送信エラー発生 ---")
        if e.response is not None:
            print(f"HTTPステータスコード: {e.response.status_code}")
            print(f"応答内容(text): {e.response.text}")
        print("--- エラー情報ここまで ---")

# --- Webhookの受付部分 ---
@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "ok"})
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- LINEイベントのハンドラ ---

@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id
    
    # 友達追加と同時に、ユーザーの状態を「地点入力を待っている状態」に設定
    database.set_user_state(user_id, 'waiting_for_location')
    
    # 地点登録を促すメッセージを送信
    reply_messages = [{"type": "text", "text": "友達追加ありがとうございます！\nこのアカウントは毎日0時にあなたの設定した地点の天気予報をお届けします。\n早速ですが、毎日の天気予報を通知する地点を教えてください！\n（例: 大阪市, 新宿区）"}]
    send_line_message(event.reply_token, reply_messages)

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    if event.postback.data == 'action=register_location':
        reply_messages = [{"type": "text", "text": "新しく通知を受け取りたい地点（例: 大阪市, 新宿区）を教えてください。"}]
        send_line_message(event.reply_token, reply_messages)
        database.set_user_state(user_id, 'waiting_for_location')

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
        coords = get_coords_from_city(user_message)
        if coords:
            forecast_message = get_open_meteo_forecast_message_dict(coords['lat'], coords['lon'], user_message)
            send_line_message(event.reply_token, [forecast_message])
        else:
            reply_message = {"type": "text", "text": "地名が見つかりませんでした。メニューの「登録地点を変更」から地点を登録するか、地名を入力して天気を検索できます。"}
            send_line_message(event.reply_token, [reply_message])

# --- アプリケーションの実行 ---
if __name__ == "__main__":
    app.run(port=5000)