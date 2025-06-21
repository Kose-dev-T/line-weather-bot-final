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

handler = WebhookHandler(CHANNEL_SECRET)

# ---【新方式】地域・都市データをプログラムに直接埋め込む ---
AREA_DATA = {
    "北海道": {"道北": ["稚内", "旭川", "留萌"], "道東": ["網走", "北見", "紋別", "根室", "釧路", "帯広"], "道央": ["札幌", "岩見沢", "倶知安"], "道南": ["室蘭", "浦河", "函館", "江差"]},
    "東北": {"青森県": ["青森", "むつ", "八戸"], "岩手県": ["盛岡", "宮古", "大船渡"], "宮城県": ["仙台", "白石"], "秋田県": ["秋田", "横手"], "山形県": ["山形", "米沢", "酒田", "新庄"], "福島県": ["福島", "小名浜", "若松"]},
    "関東": {"茨城県": ["水戸", "土浦"], "栃木県": ["宇都宮", "大田原"], "群馬県": ["前橋", "みなかみ"], "埼玉県": ["さいたま", "熊谷", "秩父"], "千葉県": ["千葉", "銚子", "館山"], "東京都": ["東京", "大島", "八丈島", "父島"], "神奈川県": ["横浜", "小田原"]},
    "甲信": {"新潟県": ["新潟", "長岡", "高田", "相川"], "山梨県": ["甲府", "河口湖"], "長野県": ["長野", "松本", "飯田"]},
    "北陸": {"富山県": ["富山", "伏木"], "石川県": ["金沢", "輪島"], "福井県": ["福井"]},
    "東海": {"愛知県": ["名古屋", "豊橋"], "岐阜県": ["岐阜", "高山"], "静岡県": ["静岡", "網代", "三島", "浜松"], "三重県": ["津"]},
    "近畿": {"大阪府": ["大阪"], "兵庫県": ["神戸", "豊岡"], "京都府": ["京都", "舞鶴"], "滋賀県": ["大津", "彦根"], "奈良県": ["奈良"], "和歌山県": ["和歌山"]},
    "中国": {"鳥取県": ["鳥取"], "島根県": ["松江", "浜田", "西郷"], "岡山県": ["岡山"], "広島県": ["広島"], "山口県": ["山口"]},
    "四国": {"徳島県": ["徳島"], "香川県": ["高松"], "愛媛県": ["松山"], "高知県": ["高知"]},
    "九州北部": {"福岡県": ["福岡", "八幡", "飯塚", "久留米"], "長崎県": ["長崎", "佐世保", "厳原"], "佐賀県": ["佐賀"], "熊本県": ["熊本", "阿蘇乙姫", "牛深"], "大分県": ["大分", "中津", "日田", "佐伯"]},
    "九州南部・奄美": {"宮崎県": ["宮崎", "延岡", "都城", "高千穂"], "鹿児島県": ["鹿児島", "鹿屋", "種子島", "名瀬"]},
    "沖縄": {"沖縄県": ["那覇", "名護", "久米島", "南大東", "宮古島", "石垣島", "与那国島"]}
}
CITY_CODE_MAP = {
    "稚内": "011000", "旭川": "012010", "留萌": "012020", "札幌": "016010", "岩見沢": "016020", "倶知安": "016030", "網走": "013010", "北見": "013020", "紋別": "013030", "根室": "014010", "釧路": "014020", "帯広": "014030", "室蘭": "015010", "浦河": "015020", "函館": "017010", "江差": "017020", "青森": "020010", "むつ": "020020", "八戸": "020030", "盛岡": "030010", "宮古": "030020", "大船渡": "030030", "仙台": "040010", "白石": "040020", "秋田": "050010", "横手": "050020", "山形": "060010", "米沢": "060020", "酒田": "060030", "新庄": "060040", "福島": "070010", "小名浜": "070020", "若松": "070030", "水戸": "080010", "土浦": "080020", "宇都宮": "090010", "大田原": "090020", "前橋": "100010", "みなかみ": "100020", "さいたま": "110010", "熊谷": "110020", "秩父": "110030", "千葉": "120010", "銚子": "120020", "館山": "120030", "東京": "130010", "大島": "130020", "八丈島": "130030", "父島": "130040", "横浜": "140010", "小田原": "140020", "新潟": "150010", "長岡": "150020", "高田": "150030", "相川": "150040", "甲府": "170010", "河口湖": "170020", "長野": "180010", "松本": "180020", "飯田": "180030", "富山": "160010", "伏木": "160020", "金沢": "190010", "輪島": "190020", "福井": "200010", "名古屋": "230010", "豊橋": "230020", "岐阜": "210010", "高山": "210020", "静岡": "220010", "網代": "220020", "三島": "220030", "浜松": "220040", "津": "240010", "大阪": "270000", "神戸": "280010", "豊岡": "280020", "京都": "260010", "舞鶴": "260020", "大津": "250010", "彦根": "250020", "奈良": "290010", "和歌山": "300010", "鳥取": "310010", "松江": "320010", "浜田": "320020", "西郷": "320030", "岡山": "330010", "広島": "340010", "山口": "350010", "徳島": "360010", "高松": "370010", "松山": "380010", "高知": "390010", "福岡": "400010", "八幡": "400020", "飯塚": "400030", "久留米": "400040", "長崎": "420010", "佐世保": "420020", "厳原": "420030", "佐賀": "410010", "熊本": "430010", "阿蘇乙姫": "430020", "牛深": "430030", "大分": "440010", "中津": "440020", "日田": "440030", "佐伯": "440040", "宮崎": "450010", "延岡": "450020", "都城": "450030", "高千穂": "450040", "鹿児島": "460010", "鹿屋": "460020", "種子島": "460030", "名瀬": "460040", "沖縄": "471010", "名護": "471020", "久米島": "471030", "南大東": "472000", "宮古島": "473000", "石垣島": "474010", "与那国島":"474020"
}
# --- 補助関数群 ---

def create_quick_reply_dict(options):
    """選択肢のリストからQuickReplyのJSON辞書を作成する"""
    items = [{"type": "action", "action": {"type": "message", "label": opt, "text": opt}} for opt in options[:13]]
    return {"items": items}

def reply_to_line(reply_token, messages):
    """requestsを使って、LINEにメッセージを返信する関数"""
    headers = {"Content-Type": "application/json; charset=UTF-8", "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    body = {"replyToken": reply_token, "messages": messages}
    try:
        response = requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, data=json.dumps(body, ensure_ascii=False).encode('utf-8'))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"LINE返信エラー: {e}\n応答内容: {e.response.text if e.response else 'N/A'}")

def get_livedoor_forecast_message_dict(city_id, city_name):
    """指定された都市IDの天気予報を取得し、Flex MessageのJSON辞書を返す"""
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

        return {
            "type": "flex", "altText": f"{city_name}の天気予報",
            "contents": {
                "type": "bubble", "direction": 'ltr',
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
        print(f"Forecast API Error: {e}")
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
    database.set_user_state(user_id, f'{flow_type}_waiting_for_area')
    area_names = list(AREA_DATA.keys())
    quick_reply = create_quick_reply_dict(area_names)
    reply_to_line(event.reply_token, [{"type": "text", "text": "エリアを選択してください。", "quickReply": quick_reply}])

@handler.add(FollowEvent)
def handle_follow(event):
    reply_to_line(event.reply_token, [{"type": "text", "text": "友達追加ありがとうございます！\n下の「地点の再設定/確認」メニューから、毎日の通知を受け取る地点を登録してください。"}])

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

    flow_type, current_step, step_data = None, None, None
    if user_state and '_waiting_for_' in user_state:
        parts = user_state.split('_waiting_for_')
        flow_type = parts[0]
        step_info = parts[1]
        if ':' in step_info:
            current_step, step_data = step_info.split(':', 1)
        else:
            current_step = step_info

    if current_step == "area":
        if user_message in AREA_DATA:
            pref_names = list(AREA_DATA[user_message].keys())
            quick_reply = create_quick_reply_dict(pref_names)
            database.set_user_state(user_id, f'{flow_type}_waiting_for_pref:{user_message}')
            reply_to_line(event.reply_token, [{"type": "text", "text": "都道府県を選択してください。", "quickReply": quick_reply}])
        else:
            reply_to_line(event.reply_token, [{"type": "text", "text": "ボタンから正しいエリア名を選択してください。"}])
    
    elif current_step == "pref":
        area_name = step_data
        if user_message in AREA_DATA.get(area_name, {}):
            cities = AREA_DATA[area_name][user_message]
            quick_reply = create_quick_reply_dict(cities if isinstance(cities, list) else [cities])
            database.set_user_state(user_id, f'{flow_type}_waiting_for_city:{area_name}:{user_message}')
            reply_to_line(event.reply_token, [{"type": "text", "text": "最後に都市名を選択してください。", "quickReply": quick_reply}])
        else:
            reply_to_line(event.reply_token, [{"type": "text", "text": "ボタンから正しい都道府県名を選択してください。"}])

    elif current_step == "city":
        area_name, pref_name = step_data.split(':')
        city_name = user_message
        city_id = CITY_CODE_MAP.get(city_name)
        
        if city_id:
            if flow_type == 'register':
                database.set_user_location(user_id, city_name, city_id)
                reply_to_line(event.reply_token, [{"type": "text", "text": f"地点を「{city_name}」に設定しました！"}])
            elif flow_type == 'lookup':
                forecast_message = get_livedoor_forecast_message_dict(city_id, city_name)
                database.set_user_state(user_id, 'normal')
                reply_to_line(event.reply_token, [forecast_message])
        else:
            reply_to_line(event.reply_token, [{"type": "text", "text": "ボタンから正しい都市名を選択してください。"}])
    
    elif user_message == "今日の天気":
        city_name, city_id = database.get_user_location(user_id)
        if city_id:
            forecast_message = get_livedoor_forecast_message_dict(city_id, city_name)
            reply_to_line(event.reply_token, [forecast_message])
        else:
            reply_messages = [{"type": "text", "text": "地点が未登録です。先に地点を登録してください。"}]
            start_location_flow(event, 'register')
    else:
        reply_to_line(event.reply_token, [{"type": "text", "text": "下のメニューから操作を選択してください。"}])

if __name__ == "__main__":
    app.run(port=5000)
