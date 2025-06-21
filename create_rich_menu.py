import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
RICH_MENU_IMAGE_PATH = "rich_menu_image.png"

def create_rich_menu():
    print("シンプルなリッチメニューを作成・登録します...")

    rich_menu_body = {
        "size": {"width": 2500, "height": 843},
        "selected": False,
        "name": "simple-location-menu-v2",
        "chatBarText": "地点の変更はこちらから",
        "areas": [
            {
                "bounds": {"x": 0, "y": 0, "width": 2500, "height": 843},
                "action": {"type": "postback", "label": "地点変更", "data": "action=register_location"}
            }
        ]
    }
    create_url = "https://api.line.me/v2/bot/richmenu"
    headers = {"Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}", "Content-Type": "application/json"}
    try:
        # 既に同じ名前のメニューがあれば削除
        menu_list_res = requests.get("https://api.line.me/v2/bot/richmenu/list", headers=headers)
        for menu in menu_list_res.json().get('richmenus', []):
            if menu.get('name') == rich_menu_body['name']:
                delete_url = f"https://api.line.me/v2/bot/richmenu/{menu['richMenuId']}"
                requests.delete(delete_url, headers=headers)
                print(f"古いメニュー(ID: {menu['richMenuId']})を削除しました。")

        # 新しいメニューを作成
        response = requests.post(create_url, headers=headers, data=json.dumps(rich_menu_body))
        response.raise_for_status()
        rich_menu_id = response.json().get('richMenuId')
        print(f"リッチメニューの骨組みを作成しました。ID: {rich_menu_id}")

        upload_url = f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content"
        headers_img = {"Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}", "Content-Type": "image/png"}
        with open(RICH_MENU_IMAGE_PATH, 'rb') as f:
            response_img = requests.post(upload_url, headers=headers_img, data=f)
            response_img.raise_for_status()
        print("画像をアップロードしました。")

        set_default_url = "https://api.line.me/v2/bot/user/all/richmenu/" + rich_menu_id
        headers_set = {"Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
        response_set = requests.post(set_default_url, headers=headers_set)
        response_set.raise_for_status()
        print("デフォルトリッチメニューとして設定しました。")

    except requests.exceptions.RequestException as e:
        print(f"エラーが発生しました: {e}\n応答内容: {e.response.text}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    if not CHANNEL_ACCESS_TOKEN:
        print("エラー: .envファイルにLINE_CHANNEL_ACCESS_TOKENが設定されていません。")
    elif not os.path.exists(RICH_MENU_IMAGE_PATH):
        print(f"エラー: 画像ファイル '{RICH_MENU_IMAGE_PATH}' が見つかりません。")
    else:
        create_rich_menu()
