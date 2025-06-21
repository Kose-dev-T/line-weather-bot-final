import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import database

load_dotenv()
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

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

def push_to_line(user_id, messages):
    headers = {"Content-Type": "application/json; charset=UTF-8", "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    body = {"to": user_id, "messages": messages}
    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(body, ensure_ascii=False).encode('utf-8'))
        response.raise_for_status()
        print(f"ユーザー({user_id})への通知が成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"ユーザー({user_id})へのLINE通知エラー: {e}")
        if e.response: print(f"応答内容: {e.response.text}")

def send_daily_forecasts():
    print("デイリー通知の送信を開始します...")
    database.init_db()
    users = database.get_all_users_with_location()
    
    if not users:
        print("通知対象のユーザーが見つかりませんでした。")
    
    for user in users:
        user_id, city_name, lat, lon = user
        print(f"登録地「{city_name}」({user_id})の天気予報を送信中...")
        
        if lat is not None and lon is not None:
            forecast_message = get_open_meteo_forecast_message_dict(lat, lon, city_name)
            push_to_line(user_id, [forecast_message])
        else:
            print(f"「{city_name}」の座標がDBにないため、送信をスキップします。")
            
    print("デイリー通知の送信が完了しました。")

if __name__ == "__main__":
    if not all([CHANNEL_ACCESS_TOKEN, OPENWEATHER_API_KEY]):
        print("エラー: .envファイルに必要なキーが設定されていません。")
    else:
        send_daily_forecasts()
