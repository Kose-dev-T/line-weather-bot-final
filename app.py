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

# --- 初期設定 ---
load_dotenv()
app = Flask(__name__)

with app.app_context():
    database.init_db()

CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

handler = WebhookHandler(CHANNEL_SECRET)

# --- グローバル変数 ---
AREA_DATA_CACHE = None

# --- 補助関数群 ---
def get_area_data():
    """livedoor互換APIの都市リストXMLを取得・キャッシュする関数"""
    global AREA_DATA_CACHE
    if AREA_DATA_CACHE is not None:
        return AREA_DATA_CACHE
    try:
        response = requests.get("https://weather.tsukumijima.net/primary_area.xml")
        response.raise_for_status()
        try:
            AREA_DATA_CACHE = ET.fromstring(response.content.decode('euc-jp'))
        except Exception:
            AREA_DATA_CACHE = ET.fromstring(response.content.decode('utf-8'))
        print("--- [INFO] 地域・都市リストをダウンロード・キャッシュしました。 ---")
        return AREA_DATA_CACHE
    except Exception as e:
        print(f"--- [ERROR] 地域・都市リストの取得に失敗しました: {e} ---")
        return None

def create_quick_reply_dict(options):
    """【修正】選択肢のリストからQuickReplyのJSON辞書を作成する"""
    if len(options) > 13:
        options = options[:13]
    
    items = []
    for opt in options:
        if opt:
            items.append({
                "type": "action",
                "action": {
                    "type": "message",
                    "label": opt,
                    "text": opt
                }
            })
    return {"items": items}

def reply_to_line(reply_token, messages):
    """【修正】requestsを直接使い、LINEにメッセージを返信する関数"""
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    body = {"replyToken": reply_token, "messages": messages}
    try:
        response = requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, data=json.dumps(body, ensure_ascii=False).encode('utf-8'))
        response.raise_for_status()
        print("LINEへの返信が成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"LINE返信エラー: {e}\n応答内容: {e.response.text if e.response else 'N/A'}")


def push_to_line(user_id, messages):
    """requestsを直接使い、LINEにプッシュ通知を送信する関数"""
    headers = {"Content-Type": "application/json; charset=UTF-8", "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    body = {"to": user_id, "messages": messages}
    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(body, ensure_ascii=False).encode('utf-8'))
        response.raise_for_status()
        print(f"ユーザー({user_id})への通知が成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"ユーザー({user_id})へのLINE通知エラー: {e}")
        if e.response: print(f"応答内容: {e.response.text}")


def get_livedoor_forecast_message_dict(city_id, city_name):
    """指定された都市IDの天気予報を取得する関数"""
    api_url = f"https://weather.tsukumijima.net/api/forecast?city={city_id}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        today_forecast = data["forecasts"][0]
        weather = today_forecast["telop"]
        temp_max_obj = today_forecast["temperature"]["max"]
        temp_min_obj = today_forecast["temperature"]["min"]
        temp_max = temp_max_obj["celsius"] if temp_max_obj else "--"
        temp_min = temp_min_obj["celsius"] if temp_min_obj else "--"
        chance_of_rain = " / ".join(today_forecast["chanceOfRain"].values())

        flex_message = {
            "type": "flex", "altText": f"{city_name}の天気予報",
            "contents": {
                "type": "bubble", "direction": 'ltr',
                "header": {"type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": "今日の天気予報", "weight": "bold", "size": "xl", "color": "#FFFFFF", "align": "center"}
                ], "backgroundColor": "#00B900", "paddingTop": "12px", "paddingBottom": "12px"},
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
        return flex_message
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
    """地点選択フローを開始する関数"""
    user_id = event.source.user_id
    database.set_user_state(user_id, f'{flow_type}_waiting_for_pref')
    
    area_data = get_area_data()
    if not area_data:
        reply_to_line(event.reply_token, [{"type": "text", "text": "地域情報の取得に失敗しました。"}])
        return
        
    # XMLから都道府県名のリストを作成
    pref_names = sorted(list(set([pref.get('title') for pref in area_data.findall('.//pref')])))
    quick_reply = create_quick_reply_dict(pref_names)
    
    reply_messages = [{"type": "text", "text": "都道府県を選択してください。", "quickReply": quick_reply}]
    reply_to_line(event.reply_token, reply_messages)

@handler.add(FollowEvent)
def handle_follow(event):
    reply_messages = [{"type": "text", "text": "友達追加ありがとうございます！\n下の「地点の再設定/確認」メニューから、毎日の通知を受け取る地点を登録してください。"}]
    reply_to_line(event.reply_token, reply_messages)

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
        reply_to_line(event.reply_token, [{"type": "text", "text": "地域情報の取得に失敗しました。"}])
        return

    flow_type, current_step, step_data = None, None, None
    if user_state and ('_waiting_for_' in user_state):
        flow_type, current_step = user_state.split('_waiting_for_')
        if ':' in current_step:
            current_step, step_data = current_step.split(':')

    if current_step == "pref":
        selected_pref = area_data.find(f".//pref[@title='{user_message}']")
        if selected_pref:
            city_names = [city.get('title') for city in selected_pref.findall('city')]
            quick_reply = create_quick_reply_dict(city_names)
            database.set_user_state(user_id, f'{flow_type}_waiting_for_city:{user_message}')
            reply_to_line(event.reply_token, [{"type": "text", "text": "最後に都市名を選択してください。", "quickReply": quick_reply}])
        else:
            reply_to_line(event.reply_token, [{"type": "text", "text": "ボタンから正しい都道府県名を選択してください。"}])
    
    elif current_step == "city":
        pref_name = step_data
        selected_city_element = area_data.find(f".//pref[@title='{pref_name}']/city[@title='{user_message}']")
        if selected_city_element is not None:
            city_id = selected_city_element.get('id')
            city_name = selected_city_element.get('title')
            
            if flow_type == 'register':
                database.set_user_location(user_id, city_name, city_id)
                reply_to_line(event.reply_token, [{"type": "text", "text": f"地点を「{city_name}」に設定しました！"}])
            elif flow_type == 'lookup':
                forecast_message = get_livedoor_forecast_message_dict(city_id, city_name)
                database.set_user_state(user_id, 'normal') # 状態をリセット
                reply_to_line(event.reply_token, [forecast_message])
        else:
            reply_to_line(event.reply_token, [{"type": "text", "text": "ボタンから正しい都市名を選択してください。"}])
    
    elif user_message == "今日の天気":
        city_name, city_id = database.get_user_location(user_id)
        if city_id:
            forecast_message = get_livedoor_forecast_message_dict(city_id, city_name)
            reply_to_line(event.reply_token, [forecast_message])
        else:
            # 地点が未登録の場合、登録フローを開始する
            event.postback = type('obj', (object,), {'data' : 'action=register_location'})
            start_location_flow(event, 'register')
    else:
        reply_to_line(event.reply_token, [{"type": "text", "text": "下のメニューから操作を選択してください。"}])

if __name__ == "__main__":
    app.run(port=5000)
