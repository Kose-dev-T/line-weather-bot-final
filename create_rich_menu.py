import os
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    RichMenuRequest, RichMenuArea, RichMenuBounds, PostbackAction, MessageAction
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
    print("2ボタンのリッチメニューを作成・登録します...")
    
    # 2つのボタン領域を定義
    rich_menu_to_create = RichMenuRequest(
        size={'width': 2500, 'height': 843},
        selected=False,
        name="two-button-menu",
        chat_bar_text="メニュー",
        areas=[
            # 左側のボタン: 今日の天気（登録地点）
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
                action=MessageAction(label="今日の天気", text="今日の天気")
            ),
            # 右側のボタン: 地点の再設定/確認
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
                action=PostbackAction(label="地点の再設定/確認", data="action=register_location")
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
        print("\n★★★ 新しいリッチメニューの更新が完了しました！ ★★★")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    if not CHANNEL_ACCESS_TOKEN:
        print("エラー: .envファイルにLINE_CHANNEL_ACCESS_TOKENが設定されていません。")
    elif not os.path.exists(RICH_MENU_IMAGE_PATH):
        print(f"エラー: 画像ファイル '{RICH_MENU_IMAGE_PATH}' が見つかりません。")
    else:
        create_rich_menu()
