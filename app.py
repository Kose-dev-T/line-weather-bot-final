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

load_dotenv()
app = Flask(__name__)
with app.app_context():
    database.init_db()

CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

handler = WebhookHandler(CHANNEL_SECRET)

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
            "type": "flex", "altText": f"{city_name}の天気予報 (JMAデータ)",
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

# app.py のこの関数を置き換えてください
def send_line_message(token, messages, is_push=False, user_id=None):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    if is_push:
        url, body = "https://api.line.me/v2/bot/message/push", {"to": user_id, "messages": messages}
    else:
        url, body = "https://api.line.me/v2/bot/message/reply", {"replyToken": token, "messages": messages}
    
    try:
        # bodyをUTF-8でエンコード
        encoded_body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        
        response = requests.post(url, headers=headers, data=encoded_body)
        
        # raise_for_status() の前にステータスコードを出力
        print(f"LINE API Response Status: {response.status_code}")
        
        response.raise_for_status()
        print("LINEメッセージの送信に成功しました。")

    except requests.exceptions.RequestException as e:
        # エラー発生時に、リクエストとレスポンスの詳細を出力
        print("--- LINE送信エラー発生 ---")
        print(f"エラータイプ: {type(e)}")
        print(f"エラー詳細: {e}")
        if e.response is not None:
            print(f"HTTPステータスコード: {e.response.status_code}")
            print(f"応答ヘッダー: {e.response.headers}")
            print(f"応答内容(text): {e.response.text}")
        if e.request is not None:
            print(f"リクエストURL: {e.request.url}")
            print(f"リクエストヘッダー: {e.request.headers}")
            # リクエストボディはバイト列なのでデコードして表示
            print(f"リクエストボディ: {e.request.body.decode('utf-8') if e.request.body else 'N/A'}")
        print("--- エラー情報ここまで ---")

    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
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
    reply_messages = [{"type": "text", "text": "友達追加ありがとうございます！\n下のメニューから「通知地点の変更」をタップして、毎日の通知を受け取る地点を登録してください。"}]
    send_line_message(event.reply_token, reply_messages)

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    if event.postback.data == 'action=register_location':
        database.set_user_state(user_id, 'waiting_for_location')
        reply_messages = [{"type": "text", "text": "通知を受け取りたい地名（例: 大阪市, 近江八幡市）を教えてください。"}]
        send_line_message(event.reply_token, reply_messages)

@handler.add(MessageEvent, message=TextMessageContent)
# app.pyのこの関数を、以下のテスト用コードに丸ごと置き換えてください

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # --- ここから診断用テストコード ---
    # このテストのため、一時的に単純なオウム返しボットにします。
    try:
        user_id = event.source.user_id
        user_message = event.message.text
        print(f"診断テスト：ユーザー({user_id})からメッセージ受信: {user_message}")

        # 受け取ったメッセージをそのまま返信します
        reply_messages = [{"type": "text", "text": f"テスト応答: {user_message}"}]
        
        # 以前に修正した詳細ログ出力機能付きの関数で返信を試みます
        send_line_message(event.reply_token, reply_messages)

    except Exception as e:
        print(f"診断テスト中にエラーが発生: {e}")
    # --- 診断用テストコードここまで ---


    # 元のコードはテストのため一時的にコメントアウトします
    # user_id = event.source.user_id
    # user_message = event.message.text
    # user_state = database.get_user_state(user_id)
    # 
    # if user_state == 'waiting_for_location':
    #     coords = get_coords_from_city(user_message)
    #     if coords:
    #         database.set_user_location(user_id, user_message, coords['lat'], coords['lon'])
    #         reply_message = {"type": "text", "text": f"地点を「{user_message}」に設定しました！"}
    #     else:
    #         reply_message = {"type": "text", "text": f"「{user_message}」が見つかりませんでした。日本の市町村名などで入力してください。"}
    #     send_line_message(event.reply_token, [reply_message])
    # else:
    #     coords = get_coords_from_city(user_message)
    #     if coords:
    #         forecast_message = get_open_meteo_forecast_message_dict(coords['lat'], coords['lon'], user_message)
    #         send_line_message(event.reply_token, [forecast_message])
    #     else:
    #         reply_message = {"type": "text", "text": "地名が見つかりませんでした。メニューの「通知地点の変更」から地点を登録するか、地名を入力して天気を検索できます。"}
    #         send_line_message(event.reply_token, [reply_message])
if __name__ == "__main__":
    app.run(port=5000)
