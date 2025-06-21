import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import math
from sqlalchemy import create_engine, text
import xml.etree.ElementTree as ET

# --- 初期設定 ---
load_dotenv()

# --- データベース設定と関数を、このファイル内に直接定義 ---
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
engine = create_engine(DATABASE_URL) if DATABASE_URL else None

def init_db():
    if not engine:
        print("データベースURLが設定されていないため、初期化をスキップします。")
        return
    with engine.connect() as connection:
        connection.execute(text('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                state TEXT,
                city_name TEXT,
                city_id TEXT
            )
        '''))
        connection.commit()

def get_all_users_with_location():
    if not engine: return []
    with engine.connect() as connection:
        result = connection.execute(text("SELECT user_id, city_name, city_id FROM users WHERE city_id IS NOT NULL")).fetchall()
        return result

# --- 天気予報・通知用の補助関数 ---
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
CITY_LIST_CACHE = None

def get_livedoor_cities():
    """livedoor互換APIの都市リストとID、緯度経度を取得・キャッシュする関数"""
    global CITY_LIST_CACHE
    if CITY_LIST_CACHE is not None:
        return CITY_LIST_CACHE
    
    # 実際には外部ファイルから読み込むか、より多くの都市を網羅するのが望ましい
    LIVEDOOR_CITY_LIST = [
        {"id": "016010", "name": "札幌", "lat": 43.064, "lon": 141.347},
        {"id": "040010", "name": "仙台", "lat": 38.268, "lon": 140.872},
        {"id": "130010", "name": "東京", "lat": 35.689, "lon": 139.692},
        {"id": "140010", "name": "横浜", "lat": 35.448, "lon": 139.642},
        {"id": "230010", "name": "名古屋", "lat": 35.181, "lon": 136.906},
        {"id": "250010", "name": "大津", "lat": 35.004, "lon": 135.869},
        {"id": "250020", "name": "彦根", "lat": 35.274, "lon": 136.259},
        {"id": "260010", "name": "京都", "lat": 35.021, "lon": 135.754},
        {"id": "270000", "name": "大阪", "lat": 34.686, "lon": 135.520},
        {"id": "280010", "name": "神戸", "lat": 34.694, "lon": 135.195},
        {"id": "340010", "name": "広島", "lat": 34.396, "lon": 132.459},
        {"id": "400010", "name": "福岡", "lat": 33.591, "lon": 130.401},
        {"id": "471010", "name": "那覇", "lat": 26.212, "lon": 127.681}
    ]
    CITY_LIST_CACHE = LIVEDOOR_CITY_LIST
    print("主要都市リストをキャッシュしました。")
    return LIVEDOOR_CITY_LIST

def haversine(lat1, lon1, lat2, lon2):
    """2点間の距離を計算する関数"""
    R = 6371 # km
    dLat, dLon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_closest_city_id(user_input_city):
    """ユーザー入力の地名に最も近い、予報可能な都市のIDを返す"""
    try:
        geo_api_url = f"http://api.openweathermap.org/geo/1.0/direct?q={user_input_city},JP&limit=1&appid={OPENWEATHER_API_KEY}"
        geo_res = requests.get(geo_api_url)
        geo_res.raise_for_status()
        geo_data = geo_res.json()
        if not geo_data: return None
        
        user_lat, user_lon = geo_data[0]['lat'], geo_data[0]['lon']
        all_cities = get_livedoor_cities()
        if not all_cities: return None
        
        closest_city = min(all_cities, key=lambda city: haversine(user_lat, user_lon, city["lat"], city["lon"]))
        
        if closest_city:
            print(f"'{user_input_city}'に最も近い都市として'{closest_city['name']}' (ID: {closest_city['id']}) を選択しました。")
            return closest_city['id']
        return None
    except Exception as e:
        print(f"Error in get_closest_city_id: {e}")
        return None

def get_livedoor_forecast_message_dict(city_id, city_name_from_db):
    """指定された都市IDの天気予報を取得する関数"""
    api_url = f"https://weather.tsukumijima.net/api/forecast?city={city_id}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        today_forecast = data["forecasts"][0]
        # 表示名はAPIから取得したものではなく、ユーザーが登録した地名を使う
        city_name_to_display = city_name_from_db 
        weather = today_forecast["telop"]
        temp_max_obj = today_forecast["temperature"]["max"]
        temp_min_obj = today_forecast["temperature"]["min"]
        temp_max = temp_max_obj["celsius"] if temp_max_obj else "--"
        temp_min = temp_min_obj["celsius"] if temp_min_obj else "--"
        chance_of_rain = " / ".join(today_forecast["chanceOfRain"].values())

        flex_message = {
            "type": "flex", "altText": f"{city_name_to_display}の天気予報",
            "contents": {
                "type": "bubble", "direction": 'ltr',
                "header": {"type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": "今日の天気予報", "weight": "bold", "size": "xl", "color": "#FFFFFF", "align": "center"}
                ], "backgroundColor": "#00B900", "paddingTop": "12px", "paddingBottom": "12px"},
                "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": [
                    {"type": "box", "layout": "vertical", "contents": [
                        {"type": "text", "text": city_name_to_display, "size": "lg", "weight": "bold", "color": "#00B900"},
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

def push_to_line(user_id, messages):
    """requestsを使って、LINEにプッシュ通知を送信する関数"""
    headers = {"Content-Type": "application/json; charset=UTF-8", "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    body = {"to": user_id, "messages": messages}
    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(body, ensure_ascii=False).encode('utf-8'))
        response.raise_for_status()
        print(f"ユーザー({user_id})への通知が成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"ユーザー({user_id})へのLINE通知エラー: {e}")
        if e.response: print(f"応答内容: {e.response.text}")

# --- メインの処理 ---
def send_daily_forecasts():
    """登録ユーザー全員に天気予報を通知するメイン関数"""
    print("デイリー通知の送信を開始します...")
    init_db()
    users = get_all_users_with_location()
    
    if not users:
        print("通知対象のユーザーが見つかりませんでした。")
        return
    
    for user in users:
        user_id, city_name, city_id_from_db = user
        print(f"登録地「{city_name}」({user_id})の天気予報を送信中...")
        
        closest_city_id = get_closest_city_id(city_name)
        if closest_city_id:
            forecast_message = get_livedoor_forecast_message_dict(closest_city_id, city_name)
            push_to_line(user_id, [forecast_message])
        else:
            print(f"「{city_name}」の都市IDが見つからなかったため、送信をスキップします。")
            error_message = {"type": "text", "text": f"ご登録の地点「{city_name}」の天気情報が見つかりませんでした。お手数ですが、メニューから地点を再登録してください。"}
            push_to_line(user_id, [error_message])
            
    print("デイリー通知の送信が完了しました。")

if __name__ == "__main__":
    if not all([CHANNEL_ACCESS_TOKEN, OPENWEATHER_API_KEY]):
        print("エラー: .envファイルにCHANNEL_ACCESS_TOKENとOPENWEATHER_API_KEYが設定されていません。")
    else:
        send_daily_forecasts()
