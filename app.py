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
import xml.etree.ElementTree as ET

load_dotenv()
app = Flask(__name__)
with app.app_context():
    database.init_db()

CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
handler = WebhookHandler(CHANNEL_SECRET)
AREA_DATA_CACHE = None

def get_area_data():
    global AREA_DATA_CACHE
    if AREA_DATA_CACHE is not None: return AREA_DATA_CACHE
    try:
        response = requests.get("https://weather.tsukumijima.net/primary_area.xml")
        response.raise_for_status()
        try: AREA_DATA_CACHE = ET.fromstring(response.content.decode('euc-jp'))
        except: AREA_DATA_CACHE = ET.fromstring(response.content.decode('utf-8'))
        print("地域・都市リストをキャッシュしました。")
        return AREA_DATA_CACHE
    except Exception as e:
        print(f"地域リストの取得エラー: {e}")
        return None

def create_quick_reply_dict(options):
    items = [{"type": "action", "action": {"type": "message", "label": opt, "text": opt}} for opt in options[:13]]
    return {"items": items}

def send_line_message(reply_token, messages):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    body = {"replyToken": reply_token, "messages": messages}
    try:
        response = requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, data=json.dumps(body, ensure_ascii=False).encode('utf-8'))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"LINE返信エラー: {e}\n応答内容: {e.response.text if e.response else 'N/A'}")

def get_livedoor_forecast_message_dict(city_id, city_name):
    api_url = f"https://weather.tsukumijima.net/api/forecast?city={city_id}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        today_forecast = data["forecasts"][0]
        weather = today_forecast["telop"]
        temp_max = today_forecast["temperature"]["max"]["celsius"] if today_forecast["temperature"]["max"] else "--"
        temp_min = today_forecast["temperature"]["min"]["celsius"] if today_forecast["temperature"]["min"] else "--"
        chance_of_rain = " / ".join(today_forecast["chanceOfRain"].values())
        return {
            "type": "flex", "altText": f"{city_name}の天気予報",
            "contents": { "type": "bubble", "direction": 'ltr',
                "header": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "今日の天気予報", "weight": "bold", "size": "xl", "color": "#FFFFFF", "align": "center"}], "backgroundColor": "#00B900", "paddingTop": "12px", "paddingBottom": "12px"},
                "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": [
                    {"type": "box", "layout": "vertical", "contents": [
                        {"type": "text", "text": city_name, "size": "lg", "weight": "bold", "color": "#00B900"},
                        {"type": "text", "text": today_forecast["date"], "size": "sm", "color": "#AAAAAA"}]},
                    {"type": "separator", "margin": "md"},
                    {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [
                        {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [
                            {"type": "text", "text": "天気", "color": "#AAAAAA", "size": "sm", "flex": 2},
                            {"type": "text", "text": weather, "wrap": True, "color": "#666666", "size": "sm", "flex": 5}]},
                        {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [
                            {"type": "text", "text": "最高気温", "color": "#AAAAAA", "size": "sm", "flex": 2},
                            {"type": "text", "text": f"{temp_max}°C", "wrap": True, "color": "#666666", "size": "sm", "flex": 5}]},
                        {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [
                            {"type": "text", "text": "最低気温", "color": "#AAAAAA", "size": "sm", "flex": 2},
                            {"type": "text", "text": f"{temp_min}°C", "wrap": True, "color": "#666666", "size": "sm", "flex": 5}]},
                        {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [
                            {"type": "text", "text": "降水確率", "color": "#AAAAAA", "size": "sm", "flex": 2},
                            {"type": "text", "text": chance_of_rain, "wrap": True, "color": "#666666", "size": "sm", "flex": 5}]}
                    ]}
                ]}
            }
        }
    except Exception as e:
        print(f"Livedoor Forecast API Error: {e}")
        return {"type": "text", "text": "天気情報の取得に失敗しました。"}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def start_location_flow(event, flow_type):
    user_id = event.source.user_id
    database.set_user_state(user_id, f'{flow_type}_waiting_for_pref')
    area_data = get_area_data()
    if not area_data:
        send_line_message(event.reply_token, [{"type": "text", "text": "地域情報の取得に失敗しました。"}])
        return
    pref_names = sorted(list(set([pref.get('title') for pref in area_data.findall('.//pref')])))
    quick_reply = create_quick_reply_dict(pref_names)
    send_line_message(event.reply_token, [{"type": "text", "text": "都道府県を選択してください。", "quickReply": quick_reply}])

@handler.add(FollowEvent)
def handle_follow(event):
    reply_messages = [{"type": "text", "text": "友達追加ありがとうございます！\n下の「地点の再設定/確認」メニューから、毎日の通知を受け取る地点を登録してください。"}]
    send_line_message(event.reply_token, reply_messages)

@handler.add(PostbackEvent)
def handle_postback(event):
    if event.postback.data == 'action=register_location':
        start_location_flow(event, 'register')
    elif event.postback.data == 'action=lookup_weather':
        start_location_flow(event, 'lookup')

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text
    user_state = database.get_user_state(user_id)
    
    area_data = get_area_data()
    if not area_data:
        send_line_message(event.reply_token, [{"type": "text", "text": "地域情報の取得に失敗しました。"}])
        return

    flow_type, current_step, step_data = None, None, None
    if user_state and '_waiting_for_' in user_state:
        flow_type, step_info = user_state.split('_waiting_for_')
        if ':' in step_info:
            current_step, step_data = step_info.split(':', 1)
        else:
            current_step = step_info

    if current_step == "pref":
        selected_pref = area_data.find(f".//pref[@title='{user_message}']")
        if selected_pref:
            city_names = [city.get('title') for city in selected_pref.findall('city')]
            quick_reply = create_quick_reply_dict(city_names)
            database.set_user_state(user_id, f'{flow_type}_waiting_for_city:{user_message}')
            send_line_message(event.reply_token, [{"type": "text", "text": "最後に都市名を選択してください。", "quickReply": quick_reply}])
        else:
            send_line_message(event.reply_token, [{"type": "text", "text": "ボタンから正しい都道府県名を選択してください。"}])
    
    elif current_step == "city":
        pref_name = step_data
        selected_city_element = area_data.find(f".//pref[@title='{pref_name}']/city[@title='{user_message}']")
        if selected_city_element is not None:
            city_id = selected_city_element.get('id')
            city_name = selected_city_element.get('title')
            
            if flow_type == 'register':
                database.set_user_location(user_id, city_name, city_id)
                send_line_message(event.reply_token, [{"type": "text", "text": f"地点を「{city_name}」に設定しました！"}])
            elif flow_type == 'lookup':
                forecast_message = get_livedoor_forecast_message_dict(city_id, city_name)
                database.set_user_state(user_id, 'normal')
                send_line_message(event.reply_token, [forecast_message])
        else:
            send_line_message(event.reply_token, [{"type": "text", "text": "ボタンから正しい都市名を選択してください。"}])
    
    elif user_message == "今日の天気":
        city_name, city_id = database.get_user_location(user_id)
        if city_id:
            forecast_message = get_livedoor_forecast_message_dict(city_id, city_name)
            send_line_message(event.reply_token, [forecast_message])
        else:
            start_location_flow(event, 'register')
    else:
        send_line_message(event.reply_token, [{"type": "text", "text": "下のメニューから操作を選択してください。"}])

if __name__ == "__main__":
    app.run(port=5000)
