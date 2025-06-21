import os
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    RichMenuRequest, RichMenuArea, RichMenuBounds, PostbackAction
)
from linebot.v3.messaging import MessagingApiBlob
from dotenv import load_dotenv

load_dotenv()
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
line_bot_blob_api = MessagingApiBlob(api_client)

RICH_MENU_IMAGE_PATH = "rich_menu_image.png"

def create_rich_menu():
    print("リッチメニューを作成・登録します...")
    
    rich_menu_to_create = RichMenuRequest(
        size={'width': 2500, 'height': 843},
        selected=False,
        name="final-text-menu",
        chat_bar_text="メニュー",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=2500, height=843),
                action=PostbackAction(label="change_location", data="action=change_location")
            )
        ]
    )
    
    try:
        rich_menu_id_response = line_bot_api.create_rich_menu(rich_menu_request=rich_menu_to_create)
        rich_menu_id = rich_menu_id_response.rich_menu_id
        print(f"リッチメニューの骨組みを作成しました。ID: {rich_menu_id}")

        with open(RICH_MENU_IMAGE_PATH, 'rb') as f:
            image_data = f.read()
            line_bot_blob_api.set_rich_menu_image(rich_menu_id=rich_menu_id, body=image_data)
        print("画像をアップロードしました。")

        line_bot_api.set_default_rich_menu(rich_menu_id)
        print("デフォルトリッチメニューとして設定しました。")
        print("\n★★★ リッチメニューの更新が完了しました！ ★★★")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    if not CHANNEL_ACCESS_TOKEN:
        print("エラー: .envファイルにLINE_CHANNEL_ACCESS_TOKENが設定されていません。")
    elif not os.path.exists(RICH_MENU_IMAGE_PATH):
        print(f"エラー: 画像ファイル '{RICH_MENU_IMAGE_PATH}' が見つかりません。")
    else:
        create_rich_menu()