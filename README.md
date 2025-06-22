# ☀️ まいにち天気予報 LINE通知システム
## 概要
「まいにち天気予報」は、ユーザーがLINE上で設定した地域の天気予報を毎日自動で通知するLINEボットシステムです。シンプルな操作で地点を登録でき、登録後は手軽に最新の天気情報を確認できます。

## 主な機能
地点登録・変更: ユーザーはLINE上で地名を入力するだけで、天気予報を受け取りたい地域を簡単に設定できます。リッチメニューからも変更可能です。

デイリー自動通知: 設定された地域の天気予報を、毎日定刻に自動でプッシュ通知します。

リアルタイム天気予報: ユーザーが地名を入力すると、その時点での最新天気予報をすぐに返信します。

Flex Messageによるリッチな表示: LINEのFlex Messageを活用し、天気予報を視覚的に分かりやすく表示します。

## 技術スタック
言語: Python

Webフレームワーク: Flask

データベース: PostgreSQL (SQLAlchemy ORM)

LINE Messaging API: line-bot-sdk

天気情報API: Open-Meteo API

地理情報API: OpenWeatherMap Geocoding API

環境変数管理: python-dotenv

デプロイ: Render (Web Service, Cron Job, PostgreSQL)

開発効率化: AI生成ツール (企画・実装の要所で活用)

## 開発期間
1週間

##セットアップ手順 (ローカル環境)
### 1. リポジトリのクローン
git clone [GitHubリポジトリのURL]
cd [リポジトリ名]

### 2. 仮想環境の構築と依存関係のインストール
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\activate  # Windows PowerShell
pip install -r requirements.txt

### 3. 環境変数の設定
プロジェクトルートに .env ファイルを作成し、以下の情報を記述します。

LINE_CHANNEL_ACCESS_TOKEN="LINEチャネルアクセストークン"
LINE_CHANNEL_SECRET="LINEチャネルシークレット"
OPENWEATHER_API_KEY="OpenWeatherMap APIキー"
DATABASE_URL="PostgreSQLデータベースURL (例: postgresql://user:pass@host:port/dbname)"

LINE Messaging APIの各種キーは LINE Developersコンソール で取得してください。

OpenWeatherMap APIキーは OpenWeatherMap で取得してください。

データベースURLは、Renderなどのホスティングサービスで取得したものを設定します。

### 4. データベースの初期化
アプリケーション起動前に、データベースを初期化し、テーブルを作成します。

python -c "import database; database.init_db()"

### 5. リッチメニューの作成・設定
LINEボットのリッチメニューを設定します。rich_menu_image.png ファイルをプロジェクトルートに配置してください。

python create_rich_menu.py

### 6. アプリケーションの実行
flask run

ローカルでテストする場合、ngrok などを使ってWebhook URLを公開する必要があります。

### 7. デイリー通知のテスト実行 (オプション)
python daily_notifier.py

このスクリプトは通常、RenderのCron Jobとして設定されます。

## 使い方 (ユーザー向け)
### 友だち追加: 以下のリンクからボットを友だち追加してください！

### →　https://qr-official.line.me/sid/L/072jsvdr.png

地点設定: 初回メッセージまたはリッチメニューの「地点変更」から、通知を受け取りたい地名（例: 「東京」, 「大阪市」）を送信してください。

通知の受信: 設定後、毎日定刻にその地点の天気予報が自動でLINEに届きます。

リアルタイム検索: いつでも地名をメッセージとして送ると、現在の天気予報をすぐに確認できます。

デプロイ (Render)
本システムはRenderでのデプロイを想定しています。

Web Service: app.py を実行するWebサービスとしてデプロイします。

PostgreSQL: データベースとして使用します。

Cron Job: daily_notifier.py を実行するためのCron Jobを設定します。
デプロイ後、LINE DevelopersコンソールのWebhook URLをRenderで発行されたURLに設定することを忘れないでください。

## 開発における工夫点
複数APIの連携: Open-MeteoとOpenWeatherMapの2つのAPIを組み合わせることで、天気予報と地理情報の両方を正確に取得し、通知の信頼性を高めました。

ユーザーフレンドリーなUI/UX:

地名入力のみで緯度・経度を自動取得し、複雑な座標入力の手間を排除。

LINE Flex Messageで天気情報を視覚的に表示。

リッチメニューによる直感的な操作性向上。

効率的な開発: AI生成ツールを企画・実装フェーズで積極的に活用し、短期間での開発を実現しました。

###貢献について (Contributing)
本プロジェクトへの貢献を歓迎します。機能追加やバグ修正など、お気軽にご提案ください。